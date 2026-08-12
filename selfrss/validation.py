from collections.abc import Sequence
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from selfrss.errors import ExtractionError
from selfrss.models import Article
from selfrss.urls import require_https_origin


def validate_article_freshness(
    articles: Sequence[Article],
    now: datetime,
) -> None:
    if now.tzinfo is None:
        raise ValueError("now must include timezone")
    published = [article.published for article in articles if article.published is not None]
    if not published:
        raise ExtractionError("feed has no article with a known datetime")
    if any(value.tzinfo is None for value in published):
        raise ExtractionError("article datetime must include timezone")

    latest = max(published)
    if latest < now - timedelta(days=14):
        raise ExtractionError("latest article is older than 14 days")
    if latest > now + timedelta(hours=24):
        raise ExtractionError("latest article datetime is too far in the future")


def validate_rss(
    xml: bytes,
    expected_host: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ExtractionError("RSS is not valid XML") from error
    if root.tag != "rss" or root.attrib.get("version") != "2.0":
        raise ExtractionError("RSS root must declare version 2.0")

    channel = root.find("channel")
    if channel is None:
        raise ExtractionError("RSS channel is missing")
    for name in ("title", "link", "description", "language", "lastBuildDate"):
        if not (channel.findtext(name) or "").strip():
            raise ExtractionError(f"RSS channel/{name} is missing")

    items = channel.findall("item")
    if len(items) < minimum:
        raise ExtractionError(f"RSS item count {len(items)} is below minimum {minimum}")
    if maximum is not None and len(items) > maximum:
        raise ExtractionError(f"RSS item count {len(items)} exceeds maximum {maximum}")

    seen: set[str] = set()
    for item in items:
        if item.find("description") is not None:
            raise ExtractionError("RSS item description is not allowed")
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        if not title or not link or not guid:
            raise ExtractionError("RSS item is missing title, link, or guid")
        try:
            require_https_origin(link, expected_host)
        except ValueError:
            raise ExtractionError(f"RSS item has unexpected URL: {link}")
        if guid != link:
            raise ExtractionError("RSS item guid must equal link")
        if link in seen:
            raise ExtractionError(f"RSS contains duplicate URL: {link}")
        seen.add(link)
    return len(items)
