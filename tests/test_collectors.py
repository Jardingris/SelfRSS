from datetime import datetime
import unittest

from selfrss.errors import ExtractionError
from selfrss.denfami import DENFAMI_URL, collect_denfami
from selfrss.gamewatch import GAMEWATCH_RDF_URL, GAMEWATCH_URL, collect_gamewatch
from selfrss.gamewith import GAMEWITH_URL, collect_gamewith


def gamewatch_page(items: list[tuple[str, str]], next_href: str | None = None) -> str:
    next_tag = f'<link rel="next" href="{next_href}">' if next_href else ""
    cards = "".join(
        f"""
        <li class="item"><p class="title"><a href="{url}">{title}</a></p>
        <p class="outline">概要</p><p class="date">(2026/8/12)</p></li>
        """
        for title, url in items
    )
    return f"<html><head>{next_tag}</head><body><section class='list'><div class='article list wrap'><ul class='list-02'>{cards}</ul></div></section></body></html>"


def gamewith_page(items: list[tuple[str, str]], next_href: str | None = None) -> str:
    cards = "".join(
        f"""
        <li class="article-news-list_item"><a href="{url}">
        <div class="_title">{title}</div>
        <time datetime="2026-08-12T10:00+09:00">日時</time></a></li>
        """
        for title, url in items
    )
    pager = (
        f"<div class='gdb-paging-wrap'><li class='gdb-paging_item--next'><a href='{next_href}'>next</a></li></div>"
        if next_href
        else ""
    )
    return f"<ul class='article-news-list'>{cards}</ul>{pager}"


def denfami_page(
    items: list[tuple[str, str, str]],
    next_href: str | None = None,
) -> str:
    cards = "".join(
        f"""
        <li><a class="flxBox" href="{url}"><div class="textBox">
        <span class="title">{title}</span><time datetime="{listed}">日付</time>
        </div></a></li>
        """
        for title, url, listed in items
    )
    pager = (
        f"<div class='pageNav'><a class='nextPostsLink' href='{next_href}'></a></div>"
        if next_href
        else ""
    )
    return (
        "<section class='articleContent row related'><ul class='gridList'>"
        f"{cards}</ul></section>{pager}"
    )


RDF = """<rdf:RDF xmlns="http://purl.org/rss/1.0/"
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
 <item><link>https://game.watch.impress.co.jp/docs/news/1.html</link><dc:date>2026-08-12T09:00:00+09:00</dc:date></item>
 <item><link>https://game.watch.impress.co.jp/docs/news/3.html</link><dc:date>2026-08-12T07:00:00+09:00</dc:date></item>
</rdf:RDF>"""


class FakeClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested: list[str] = []
        self.robots_checked: list[str] = []

    def ensure_robots_allowed(self, robots_url: str, target_url: str) -> None:
        del robots_url
        self.robots_checked.append(target_url)

    def get_text(self, url: str) -> str:
        self.requested.append(url)
        return self.responses[url]


class CollectorTests(unittest.TestCase):
    def test_denfami_follows_next_link_deduplicates_and_sorts(self) -> None:
        page2 = "https://news.denfaminicogamer.jp/tag/steam/page/2"
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(
                    [
                        ("二", "/news/2", "2026-8-11"),
                        ("一", "/news/1", "2026-8-12"),
                    ],
                    "/tag/steam/page/2",
                ),
                page2: denfami_page(
                    [
                        ("二", "/news/2", "2026-8-11"),
                        ("三", "/news/3", "2026-8-10"),
                    ]
                ),
            }
        )

        articles = collect_denfami(client, limit=3, minimum=3)

        self.assertEqual([article.title for article in articles], ["一", "二", "三"])
        self.assertEqual(client.requested, [DENFAMI_URL, page2])
        self.assertEqual(client.robots_checked, [DENFAMI_URL, page2])

    def test_denfami_rejects_too_few_articles(self) -> None:
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(
                    [("一", "/news/1", "2026-8-12")]
                )
            }
        )

        with self.assertRaisesRegex(ExtractionError, "minimum"):
            collect_denfami(client, limit=2, minimum=2)

    def test_denfami_rejects_pagination_loop(self) -> None:
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(
                    [("一", "/news/1", "2026-8-12")],
                    "/tag/steam",
                )
            }
        )

        with self.assertRaisesRegex(ExtractionError, "loop"):
            collect_denfami(client, limit=2, minimum=2)

    def test_denfami_rejects_external_pagination_host(self) -> None:
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(
                    [("一", "/news/1", "2026-8-12")],
                    "https://example.com/tag/steam/page/2",
                )
            }
        )

        with self.assertRaisesRegex(ExtractionError, "pagination.*host"):
            collect_denfami(client, limit=2, minimum=2)

    def test_denfami_rejects_same_host_non_steam_pagination_path(self) -> None:
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(
                    [("一", "/news/1", "2026-8-12")],
                    "/tag/switch2/page/2",
                )
            }
        )

        with self.assertRaisesRegex(ExtractionError, "pagination.*path"):
            collect_denfami(client, limit=2, minimum=2)

    def test_denfami_rejects_incomplete_full_page_instead_of_backfilling(self) -> None:
        page2 = "https://news.denfaminicogamer.jp/tag/steam/page/2"
        page1_items = [
            (f"記事{number}", f"/news/{number}", "2026-8-12")
            for number in range(19)
        ]
        page2_items = [
            (f"記事{number}", f"/news/{number}", "2026-8-11")
            for number in range(19, 40)
        ]
        client = FakeClient(
            {
                DENFAMI_URL: denfami_page(page1_items, "/tag/steam/page/2"),
                page2: denfami_page(page2_items),
            }
        )

        with self.assertRaisesRegex(ExtractionError, "page article count"):
            collect_denfami(client, limit=40, minimum=40)

    def test_gamewatch_merges_rdf_dates_and_deduplicates_pages(self) -> None:
        page2 = "https://game.watch.impress.co.jp/category/pc/pc/index2.html"
        client = FakeClient(
            {
                GAMEWATCH_RDF_URL: RDF,
                GAMEWATCH_URL: gamewatch_page(
                    [("一", "/docs/news/1.html"), ("二", "/docs/news/2.html")],
                    "index2.html",
                ),
                page2: gamewatch_page(
                    [("二", "/docs/news/2.html"), ("三", "/docs/news/3.html")]
                ),
            }
        )

        articles = collect_gamewatch(client, limit=3, minimum=3)

        self.assertEqual([article.title for article in articles], ["一", "二", "三"])
        self.assertEqual(
            articles[0].published,
            datetime.fromisoformat("2026-08-12T09:00:00+09:00"),
        )
        self.assertIsNone(articles[1].published)
        self.assertEqual(client.robots_checked, [GAMEWATCH_RDF_URL, GAMEWATCH_URL, page2])

    def test_gamewith_follows_real_next_link_and_deduplicates(self) -> None:
        page2 = "https://gamewith.jp/pc/news?p=2"
        client = FakeClient(
            {
                GAMEWITH_URL: gamewith_page(
                    [("一", "/gamedb/1"), ("二", "/gamedb/2")],
                    "/pc/news?p=2",
                ),
                page2: gamewith_page(
                    [("二", "/gamedb/2"), ("三", "/gamedb/3")]
                ),
            }
        )

        articles = collect_gamewith(client, limit=3, minimum=3)

        self.assertEqual([article.title for article in articles], ["一", "二", "三"])
        self.assertEqual(client.robots_checked, [GAMEWITH_URL, page2])

    def test_gamewith_skips_landing_page_card_and_keeps_collecting(self) -> None:
        page2 = "https://gamewith.jp/pc/news?p=2"
        client = FakeClient(
            {
                GAMEWITH_URL: gamewith_page(
                    [
                        ("キャンペーン", "https://lp.gamewith.jp/NTE/vtuber_vol3"),
                        ("一", "/gamedb/1"),
                    ],
                    "/pc/news?p=2",
                ),
                page2: gamewith_page([("二", "/gamedb/2")]),
            }
        )

        try:
            articles = collect_gamewith(client, limit=2, minimum=2)
        except ExtractionError as error:
            self.fail(f"known landing-page card was not skipped: {error}")

        self.assertEqual([article.title for article in articles], ["一", "二"])
        self.assertEqual(client.requested, [GAMEWITH_URL, page2])

    def test_rejects_too_few_articles(self) -> None:
        client = FakeClient({GAMEWITH_URL: gamewith_page([("一", "/gamedb/1")])})

        with self.assertRaisesRegex(ExtractionError, "minimum"):
            collect_gamewith(client, limit=3, minimum=2)

    def test_rejects_pagination_loop(self) -> None:
        client = FakeClient(
            {
                GAMEWITH_URL: gamewith_page(
                    [("一", "/gamedb/1")],
                    "/pc/news",
                )
            }
        )

        with self.assertRaisesRegex(ExtractionError, "loop"):
            collect_gamewith(client, limit=3, minimum=2)

    def test_gamewith_sorts_articles_by_published_datetime(self) -> None:
        html = gamewith_page([("一", "/gamedb/1"), ("二", "/gamedb/2")])
        html = html.replace(
            'datetime="2026-08-12T10:00+09:00"',
            'datetime="2026-08-12T09:00+09:00"',
            1,
        )
        client = FakeClient({GAMEWITH_URL: html})

        articles = collect_gamewith(client, limit=2, minimum=2)

        self.assertEqual([article.title for article in articles], ["二", "一"])


if __name__ == "__main__":
    unittest.main()
