from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from selfrss.errors import ExtractionError
from selfrss.models import Article, ParsedPage
from selfrss.urls import normalize_article_url, require_https_origin


GAMEWITH_HOST = "gamewith.jp"
GAMEWITH_URL = "https://gamewith.jp/pc/news"
GAMEWITH_ROBOTS_URL = "https://gamewith.jp/robots.txt"
MAX_PAGES = 10


def _clean_text(element: object) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def parse_gamewith_page(html: str, page_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select("ul.article-news-list")
    if len(containers) != 1:
        raise ExtractionError("GameWith news container must appear exactly once")

    articles: list[Article] = []
    cards = containers[0].find_all("li", class_="article-news-list_item", recursive=False)
    for card in cards:
        link = card.find("a", href=True, recursive=False)
        title_element = card.select_one("._title")
        if link is None or title_element is None or not _clean_text(title_element):
            raise ExtractionError("GameWith card is missing title or URL")

        url = normalize_article_url(link["href"], page_url)
        try:
            require_https_origin(url, GAMEWITH_HOST)
        except ValueError:
            raise ExtractionError(f"GameWith card has unexpected host: {url}")

        time_element = card.select_one("time[datetime]")
        if time_element is None:
            raise ExtractionError("GameWith card is missing datetime")
        try:
            published = datetime.fromisoformat(time_element["datetime"])
        except ValueError as error:
            raise ExtractionError("GameWith card has invalid datetime") from error
        if published.tzinfo is None:
            raise ExtractionError("GameWith card datetime must include timezone")

        articles.append(
            Article(
                title=_clean_text(title_element),
                url=url,
                published=published,
            )
        )

    if not articles:
        raise ExtractionError("GameWith news container has no articles")

    next_link = soup.select_one(".gdb-paging-wrap .gdb-paging_item--next > a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return ParsedPage(tuple(articles), next_url)


def collect_gamewith(client: object, limit: int = 40, minimum: int = 30) -> list[Article]:
    articles: list[Article] = []
    seen_articles: set[str] = set()
    seen_pages: set[str] = set()
    page_url: str | None = GAMEWITH_URL
    page_count = 0

    while page_url and len(articles) < limit:
        page_count += 1
        if page_count > MAX_PAGES:
            raise ExtractionError(f"GameWith pagination exceeds {MAX_PAGES} pages")
        if page_url in seen_pages:
            raise ExtractionError("GameWith pagination loop detected")
        try:
            require_https_origin(page_url, GAMEWITH_HOST)
        except ValueError:
            raise ExtractionError("GameWith pagination has unexpected host")
        seen_pages.add(page_url)
        client.ensure_robots_allowed(GAMEWITH_ROBOTS_URL, page_url)
        page = parse_gamewith_page(client.get_text(page_url), page_url)
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
            f"GameWith article count {len(articles)} is below minimum {minimum}"
        )
    articles.sort(key=lambda article: article.published, reverse=True)
    return articles
