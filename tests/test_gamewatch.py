from datetime import datetime
import unittest

from selfrss.gamewatch import ExtractionError, parse_gamewatch_page, parse_gamewatch_rdf


GAMEWATCH_HTML = """
<html><head><link rel="next" href="index2.html"></head><body>
  <section class="latest"><a href="/docs/news/999.html">対象外</a></section>
  <section class="list"><div class="article list wrap"><ul class="list-02">
    <li class="item ad native"></li>
    <li class="item news">
      <div class="image"><a href="/docs/news/123.html"><img></a></div>
      <div class="text">
        <p class="title"><a href="/docs/news/123.html?utm_source=x">PC記事 &amp; 特集</a></p>
        <p class="outline">短い概要 &amp; 説明</p>
        <p class="date">(2026/8/12)</p>
      </div>
    </li>
  </ul></div></section>
</body></html>
"""

GAMEWATCH_RDF = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns="http://purl.org/rss/1.0/"
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
  <item rdf:about="https://game.watch.impress.co.jp/docs/news/123.html?ref=rss">
    <link>https://game.watch.impress.co.jp/docs/news/123.html</link>
    <dc:date>2026-08-12T10:09:17+09:00</dc:date>
  </item>
</rdf:RDF>
"""


class GameWatchParserTests(unittest.TestCase):
    def test_extracts_only_category_list_cards(self) -> None:
        page = parse_gamewatch_page(
            GAMEWATCH_HTML,
            "https://game.watch.impress.co.jp/category/pc/pc/",
        )

        self.assertEqual(len(page.articles), 1)
        self.assertEqual(page.articles[0].title, "PC記事 & 特集")
        self.assertEqual(
            page.articles[0].url,
            "https://game.watch.impress.co.jp/docs/news/123.html",
        )
        self.assertIsNone(page.articles[0].published)
        self.assertEqual(
            page.articles[0].listed_at,
            datetime.fromisoformat("2026-08-12T00:00:00+09:00"),
        )
        self.assertEqual(
            page.next_url,
            "https://game.watch.impress.co.jp/category/pc/pc/index2.html",
        )

    def test_parses_official_rdf_dates_by_canonical_url(self) -> None:
        dates = parse_gamewatch_rdf(GAMEWATCH_RDF)

        self.assertEqual(
            dates["https://game.watch.impress.co.jp/docs/news/123.html"],
            datetime.fromisoformat("2026-08-12T10:09:17+09:00"),
        )

    def test_rejects_missing_category_container(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "container"):
            parse_gamewatch_page(
                "<html><body><section class='latest'></section></body></html>",
                "https://game.watch.impress.co.jp/category/pc/pc/",
            )

    def test_rejects_card_without_title(self) -> None:
        broken = """
        <section class="list"><div class="article list wrap"><ul class="list-02">
          <li class="item"><p class="date">(2026/8/12)</p></li>
        </ul></div></section>
        """

        with self.assertRaisesRegex(ExtractionError, "title"):
            parse_gamewatch_page(
                broken,
                "https://game.watch.impress.co.jp/category/pc/pc/",
            )


if __name__ == "__main__":
    unittest.main()
