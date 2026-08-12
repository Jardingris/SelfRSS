from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urljoin
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from selfrss.errors import ExtractionError
from selfrss.models import Article, ParsedPage
from selfrss.urls import normalize_article_url, require_https_origin


DENFAMI_HOST = "news.denfaminicogamer.jp"
DENFAMI_URL = "https://news.denfaminicogamer.jp/tag/steam"
DENFAMI_ROBOTS_URL = "https://news.denfaminicogamer.jp/robots.txt"
JST = timezone(timedelta(hours=9))
MAX_PAGES = 10
EXPECTED_PAGE_SIZE = 20
PAGE_PATH_PATTERN = re.compile(r"^/tag/steam/page/[1-9]\d*/?$")


def _clean_text(element: object) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def parse_denfami_page(html: str, page_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select("section.articleContent.row.related > ul.gridList")
    if len(containers) != 1:
        raise ExtractionError("Denfami Steam tag container must appear exactly once")

    articles: list[Article] = []
    for card in containers[0].find_all("li", recursive=False):
        link = card.select_one(":scope > a.flxBox[href]")
        title = card.select_one(".textBox .title")
        if link is None or title is None or not _clean_text(title):
            raise ExtractionError("Denfami card is missing title or URL")

        url = normalize_article_url(link["href"], page_url)
        try:
            require_https_origin(url, DENFAMI_HOST)
        except ValueError:
            raise ExtractionError(f"Denfami card has unexpected host: {url}")

        time_element = card.select_one("time[datetime]")
        if time_element is None:
            raise ExtractionError("Denfami card is missing listed date")
        try:
            listed_at = datetime.strptime(
                time_element["datetime"], "%Y-%m-%d"
            ).replace(tzinfo=JST)
        except ValueError as error:
            raise ExtractionError("Denfami card has invalid listed date") from error

        articles.append(
            Article(
                title=_clean_text(title),
                url=url,
                listed_at=listed_at,
            )
        )
    if not articles:
        raise ExtractionError("Denfami Steam tag container has no articles")

    next_links = soup.select("div.pageNav > a.nextPostsLink[href]")
    if len(next_links) > 1:
        raise ExtractionError("Denfami pagination next link must appear at most once")
    next_url = urljoin(page_url, next_links[0]["href"]) if next_links else None
    return ParsedPage(tuple(articles), next_url)


def collect_denfami(client: object, limit: int = 40, minimum: int = 30) -> list[Article]:
    articles: list[Article] = []
    seen_articles: set[str] = set()
    seen_pages: set[str] = set()
    page_url: str | None = DENFAMI_URL
    page_count = 0

    while page_url and len(articles) < limit:
        page_count += 1
        if page_count > MAX_PAGES:
            raise ExtractionError(f"Denfami pagination exceeds {MAX_PAGES} pages")
        if page_url in seen_pages:
            raise ExtractionError("Denfami pagination loop detected")
        try:
            require_https_origin(page_url, DENFAMI_HOST)
        except ValueError:
            raise ExtractionError("Denfami pagination has unexpected host")
        parts = urlsplit(page_url)
        if page_url != DENFAMI_URL and (
            PAGE_PATH_PATTERN.fullmatch(parts.path) is None
            or parts.query
            or parts.fragment
        ):
            raise ExtractionError("Denfami pagination has unexpected path")
        seen_pages.add(page_url)
        client.ensure_robots_allowed(DENFAMI_ROBOTS_URL, page_url)
        page = parse_denfami_page(client.get_text(page_url), page_url)
        if limit >= EXPECTED_PAGE_SIZE and len(page.articles) != EXPECTED_PAGE_SIZE:
            raise ExtractionError(
                f"Denfami page article count {len(page.articles)} is not "
                f"{EXPECTED_PAGE_SIZE}"
            )
        for article in page.articles:
            if article.url in seen_articles:
                continue
            seen_articles.add(article.url)
            articles.append(article)
            if len(articles) == limit:
                break
        page_url = page.next_url

    if len(articles) < minimum:
        raise ExtractionError(
            f"Denfami article count {len(articles)} is below minimum {minimum}"
        )
    articles.sort(key=lambda article: article.listed_at, reverse=True)
    return articles
