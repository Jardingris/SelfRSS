from datetime import datetime
import unittest

from selfrss.errors import ExtractionError
from selfrss.denfami import parse_denfami_page


DENFAMI_HTML = """
<html><body>
  <section class="articleContent row related">
    <h3 class="contentHeader">Steamに関する記事一覧</h3>
    <ul class="gridList">
      <li>
        <a class="flxBox" href="/news/260813c?utm_source=rss">
          <div class="textBox">
            <span class="title">Steam新作 &amp; 特集</span>
            <time datetime="2026-8-13">2026年8月13日 公開</time>
          </div>
        </a>
      </li>
    </ul>
  </section>
  <div class="pageNav">
    <a class="nextPostsLink" href="/tag/steam/page/2"></a>
  </div>
  <section class="articleContent ranking">
    <ul class="gridList"><li><a href="/news/not-steam">対象外</a></li></ul>
  </section>
</body></html>
"""


class DenfamiParserTests(unittest.TestCase):
    def test_extracts_only_steam_tag_cards(self) -> None:
        page = parse_denfami_page(
            DENFAMI_HTML,
            "https://news.denfaminicogamer.jp/tag/steam",
        )

        self.assertEqual(len(page.articles), 1)
        self.assertEqual(page.articles[0].title, "Steam新作 & 特集")
        self.assertEqual(
            page.articles[0].url,
            "https://news.denfaminicogamer.jp/news/260813c",
        )
        self.assertIsNone(page.articles[0].published)
        self.assertEqual(
            page.articles[0].listed_at,
            datetime.fromisoformat("2026-08-13T00:00:00+09:00"),
        )
        self.assertEqual(
            page.next_url,
            "https://news.denfaminicogamer.jp/tag/steam/page/2",
        )

    def test_rejects_missing_steam_tag_container(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "container"):
            parse_denfami_page(
                "<html><body><section class='ranking'></section></body></html>",
                "https://news.denfaminicogamer.jp/tag/steam",
            )

    def test_rejects_card_without_title(self) -> None:
        broken = DENFAMI_HTML.replace(
            '<span class="title">Steam新作 &amp; 特集</span>',
            "",
        )

        with self.assertRaisesRegex(ExtractionError, "title or URL"):
            parse_denfami_page(
                broken,
                "https://news.denfaminicogamer.jp/tag/steam",
            )

    def test_rejects_card_without_listed_date(self) -> None:
        broken = DENFAMI_HTML.replace(
            '<time datetime="2026-8-13">2026年8月13日 公開</time>',
            "",
        )

        with self.assertRaisesRegex(ExtractionError, "listed date"):
            parse_denfami_page(
                broken,
                "https://news.denfaminicogamer.jp/tag/steam",
            )

    def test_rejects_unknown_external_card_host(self) -> None:
        broken = DENFAMI_HTML.replace(
            "/news/260813c?utm_source=rss",
            "https://example.com/news/260813c",
        )

        with self.assertRaisesRegex(ExtractionError, "unexpected host"):
            parse_denfami_page(
                broken,
                "https://news.denfaminicogamer.jp/tag/steam",
            )


if __name__ == "__main__":
    unittest.main()
