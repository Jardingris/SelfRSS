from collections.abc import Sequence
from datetime import datetime
from email.utils import format_datetime
import xml.etree.ElementTree as ET

from selfrss.models import Article


ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM_NS)


def render_rss(
    channel_title: str,
    channel_url: str,
    channel_description: str,
    articles: Sequence[Article],
    self_url: str | None,
    built_at: datetime,
) -> bytes:
    if built_at.tzinfo is None:
        raise ValueError("built_at must include timezone")

    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = channel_title
    ET.SubElement(channel, "link").text = channel_url
    ET.SubElement(channel, "description").text = channel_description
    ET.SubElement(channel, "language").text = "ja"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(built_at)
    if self_url:
        ET.SubElement(
            channel,
            f"{{{ATOM_NS}}}link",
            {
                "href": self_url,
                "rel": "self",
                "type": "application/rss+xml",
            },
        )

    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article.title
        ET.SubElement(item, "link").text = article.url
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = article.url
        if article.published is not None:
            if article.published.tzinfo is None:
                raise ValueError("article published datetime must include timezone")
            ET.SubElement(item, "pubDate").text = format_datetime(article.published)
        if article.description:
            ET.SubElement(item, "description").text = article.description

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
