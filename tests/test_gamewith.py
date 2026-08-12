from datetime import datetime
import unittest

from selfrss.gamewith import ExtractionError, parse_gamewith_page


GAMEWITH_HTML = """
<html><body>
  <ul class="article-news-list is-first-page">
    <li class="article-news-list_item u-my-m">
      <a class="media _inner" href="/gamedb/18014/articles/61757?utm_medium=rss">
        <div class="article-news-list_item-body">
          <div class="_title">採掘から工場経営まで！</div>
          <div class="_last-update">
            <time class="_time" datetime="2026-08-12T02:30+09:00">2026年8月12日02:30</time>
          </div>
        </div>
      </a>
    </li>
  </ul>
  <div class="gdb-paging-wrap"><ul class="gdb-paging">
    <li class="gdb-paging_item gdb-paging_item--next"><a href="/pc/news?p=2">next</a></li>
  </ul></div>
  <h2>PCメニュー</h2><a href="/pc/article/show/999">対象外</a>
</body></html>
"""


class GameWithParserTests(unittest.TestCase):
    def test_extracts_only_news_list_cards(self) -> None:
        page = parse_gamewith_page(GAMEWITH_HTML, "https://gamewith.jp/pc/news")

        self.assertEqual(len(page.articles), 1)
        self.assertEqual(page.articles[0].title, "採掘から工場経営まで！")
        self.assertEqual(
            page.articles[0].url,
            "https://gamewith.jp/gamedb/18014/articles/61757",
        )
        self.assertEqual(
            page.articles[0].published,
            datetime.fromisoformat("2026-08-12T02:30+09:00"),
        )
        self.assertIsNone(page.articles[0].description)
        self.assertEqual(page.next_url, "https://gamewith.jp/pc/news?p=2")

    def test_rejects_missing_news_container(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "container"):
            parse_gamewith_page("<html></html>", "https://gamewith.jp/pc/news")

    def test_rejects_card_without_datetime(self) -> None:
        broken = """
        <ul class="article-news-list">
          <li class="article-news-list_item">
            <a href="/gamedb/1"><div class="_title">記事</div></a>
          </li>
        </ul>
        """

        with self.assertRaisesRegex(ExtractionError, "datetime"):
            parse_gamewith_page(broken, "https://gamewith.jp/pc/news")


if __name__ == "__main__":
    unittest.main()
