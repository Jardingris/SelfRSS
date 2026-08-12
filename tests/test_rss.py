from datetime import datetime
from email.utils import parsedate_to_datetime
import unittest
import xml.etree.ElementTree as ET

from selfrss.errors import ExtractionError
from selfrss.models import Article
from selfrss.rss import ATOM_NS, render_rss
from selfrss.validation import validate_rss


class RssTests(unittest.TestCase):
    def setUp(self) -> None:
        self.articles = [
            Article(
                title='A & B <特集>',
                url="https://example.com/article/1",
                published=datetime.fromisoformat("2026-08-12T10:09:17+09:00"),
            ),
            Article(
                title="日時なし",
                url="https://example.com/article/2",
            ),
        ]

    def test_renders_valid_rss_without_item_descriptions(self) -> None:
        xml = render_rss(
            channel_title="PC Game RSS",
            channel_url="https://example.com/source",
            channel_description="非公式フィード",
            articles=self.articles,
            self_url="https://owner.github.io/SelfRSS/feed.xml",
            built_at=datetime.fromisoformat("2026-08-12T11:00:00+09:00"),
        )
        root = ET.fromstring(xml)
        channel = root.find("channel")
        self.assertIsNotNone(channel)
        assert channel is not None
        self.assertEqual(channel.findtext("title"), "PC Game RSS")
        self.assertEqual(channel.findtext("link"), "https://example.com/source")
        self.assertEqual(channel.findtext("language"), "ja")
        atom_link = channel.find(f"{{{ATOM_NS}}}link")
        self.assertEqual(atom_link.attrib["rel"], "self")
        self.assertEqual(atom_link.attrib["type"], "application/rss+xml")

        items = channel.findall("item")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].findtext("title"), 'A & B <特集>')
        self.assertIsNone(items[0].find("description"))
        self.assertEqual(items[0].findtext("guid"), self.articles[0].url)
        self.assertEqual(items[0].find("guid").attrib["isPermaLink"], "true")
        self.assertEqual(
            parsedate_to_datetime(items[0].findtext("pubDate")),
            self.articles[0].published,
        )
        self.assertIsNone(items[1].find("description"))
        self.assertIsNone(items[1].find("pubDate"))
        self.assertEqual(validate_rss(xml, expected_host="example.com", minimum=2), 2)

    def test_validation_rejects_item_description(self) -> None:
        xml = b"""<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0"><channel>
          <title>PC Game RSS</title>
          <link>https://example.com/source</link>
          <description>channel description</description>
          <language>ja</language>
          <lastBuildDate>Wed, 12 Aug 2026 11:00:00 +0900</lastBuildDate>
          <item>
            <title>article</title>
            <link>https://example.com/article/1</link>
            <guid isPermaLink="true">https://example.com/article/1</guid>
            <description>copied outline</description>
          </item>
        </channel></rss>"""

        with self.assertRaisesRegex(ExtractionError, "description"):
            validate_rss(xml, expected_host="example.com", minimum=1)

    def test_omits_atom_self_when_base_url_is_unknown(self) -> None:
        xml = render_rss(
            "title",
            "https://example.com/source",
            "description",
            self.articles,
            None,
            datetime.fromisoformat("2026-08-12T11:00:00+09:00"),
        )

        channel = ET.fromstring(xml).find("channel")
        self.assertIsNone(channel.find(f"{{{ATOM_NS}}}link"))

    def test_validation_rejects_duplicate_item_urls(self) -> None:
        duplicate = [self.articles[0], self.articles[0]]
        xml = render_rss(
            "title",
            "https://example.com/source",
            "description",
            duplicate,
            None,
            datetime.fromisoformat("2026-08-12T11:00:00+09:00"),
        )

        with self.assertRaisesRegex(ExtractionError, "duplicate"):
            validate_rss(xml, expected_host="example.com", minimum=2)

    def test_validation_rejects_more_than_maximum(self) -> None:
        xml = render_rss(
            "title",
            "https://example.com/source",
            "description",
            self.articles,
            None,
            datetime.fromisoformat("2026-08-12T11:00:00+09:00"),
        )

        with self.assertRaisesRegex(ExtractionError, "maximum"):
            validate_rss(
                xml,
                expected_host="example.com",
                minimum=1,
                maximum=1,
            )


if __name__ == "__main__":
    unittest.main()
