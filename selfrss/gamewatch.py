from dataclasses import replace
from datetime import datetime, timezone, timedelta
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from selfrss.errors import ExtractionError
from selfrss.models import Article, ParsedPage
from selfrss.urls import normalize_article_url, require_https_origin


GAMEWATCH_HOST = "game.watch.impress.co.jp"
GAMEWATCH_URL = "https://game.watch.impress.co.jp/category/pc/pc/"
GAMEWATCH_RDF_URL = "https://game.watch.impress.co.jp/data/rss/1.0/gmw/feed.rdf"
GAMEWATCH_ROBOTS_URL = "https://game.watch.impress.co.jp/robots.txt"
DATE_PATTERN = re.compile(r"^\((\d{4})/(\d{1,2})/(\d{1,2})\)$")
JST = timezone(timedelta(hours=9))
MAX_PAGES = 10

def _clean_text(element: object) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def parse_gamewatch_page(html: str, page_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select("section.list div.article.list.wrap > ul.list-02")
    if len(containers) != 1:
        raise ExtractionError("GAME Watch category container must appear exactly once")

    articles: list[Article] = []
    for card in containers[0].find_all("li", class_="item", recursive=False):
        classes = set(card.get("class", []))
        if {"ad", "native"}.issubset(classes):
            continue
        title_link = card.select_one("p.title > a[href]")
        if title_link is None or not _clean_text(title_link):
            raise ExtractionError("GAME Watch card is missing title")

        url = normalize_article_url(title_link["href"], page_url)
        try:
            require_https_origin(url, GAMEWATCH_HOST)
        except ValueError:
            raise ExtractionError(f"GAME Watch card has unexpected host: {url}")

        date_element = card.select_one("p.date")
        date_text = _clean_text(date_element) if date_element else ""
        match = DATE_PATTERN.fullmatch(date_text)
        if match is None:
            raise ExtractionError("GAME Watch card is missing a valid listed date")
        try:
            listed_at = datetime(*(int(value) for value in match.groups()), tzinfo=JST)
        except ValueError as error:
            raise ExtractionError("GAME Watch card has invalid listed date") from error

        outline = card.select_one("p.outline")
        description = _clean_text(outline) if outline else None
        articles.append(
            Article(
                title=_clean_text(title_link),
                url=url,
                description=description or None,
                listed_at=listed_at,
            )
        )

    if not articles:
        raise ExtractionError("GAME Watch category container has no articles")

    next_link = soup.select_one('head link[rel="next"][href]')
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return ParsedPage(tuple(articles), next_url)


def parse_gamewatch_rdf(xml: str) -> dict[str, datetime]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ExtractionError("GAME Watch RDF is not valid XML") from error

    namespaces = {
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    dates: dict[str, datetime] = {}
    for item in root.findall("rss:item", namespaces):
        link = item.findtext("rss:link", namespaces=namespaces)
        date_text = item.findtext("dc:date", namespaces=namespaces)
        if not link or not date_text:
            continue
        try:
            published = datetime.fromisoformat(date_text)
        except ValueError as error:
            raise ExtractionError("GAME Watch RDF has invalid dc:date") from error
        if published.tzinfo is None:
            raise ExtractionError("GAME Watch RDF dc:date must include timezone")
        dates[normalize_article_url(link, link)] = published
    return dates


def collect_gamewatch(client: object, limit: int = 40, minimum: int = 30) -> list[Article]:
    client.ensure_robots_allowed(GAMEWATCH_ROBOTS_URL, GAMEWATCH_RDF_URL)
    rdf_dates = parse_gamewatch_rdf(client.get_text(GAMEWATCH_RDF_URL))
    articles: list[Article] = []
    seen_articles: set[str] = set()
    seen_pages: set[str] = set()
    page_url: str | None = GAMEWATCH_URL
    page_count = 0

    while page_url and len(articles) < limit:
        page_count += 1
        if page_count > MAX_PAGES:
            raise ExtractionError(f"GAME Watch pagination exceeds {MAX_PAGES} pages")
        if page_url in seen_pages:
            raise ExtractionError("GAME Watch pagination loop detected")
        try:
            require_https_origin(page_url, GAMEWATCH_HOST)
        except ValueError:
            raise ExtractionError("GAME Watch pagination has unexpected host")
        seen_pages.add(page_url)
        client.ensure_robots_allowed(GAMEWATCH_ROBOTS_URL, page_url)
        page = parse_gamewatch_page(client.get_text(page_url), page_url)
        for article in page.articles:
            if article.url in seen_articles:
                continue
            seen_articles.add(article.url)
            published = rdf_dates.get(article.url)
            articles.append(replace(article, published=published))
            if len(articles) == limit:
                break
        page_url = page.next_url

    if len(articles) < minimum:
        raise ExtractionError(
            f"GAME Watch article count {len(articles)} is below minimum {minimum}"
        )
    articles.sort(
        key=lambda article: article.listed_at or datetime.min.replace(tzinfo=JST),
        reverse=True,
    )
    return articles
