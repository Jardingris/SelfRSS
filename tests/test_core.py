import unittest

from selfrss.urls import normalize_article_url, require_https_origin


class NormalizeArticleUrlTests(unittest.TestCase):
    def test_resolves_relative_url_and_removes_known_tracking(self) -> None:
        actual = normalize_article_url(
            "/docs/news/123.html?utm_source=x&ref=rss&id=7#section",
            "https://game.watch.impress.co.jp/category/pc/pc/",
        )

        self.assertEqual(
            actual,
            "https://game.watch.impress.co.jp/docs/news/123.html?id=7",
        )

    def test_preserves_meaningful_query_and_non_rss_ref(self) -> None:
        actual = normalize_article_url(
            "https://gamewith.jp/pc/news?p=2&ref=category",
            "https://gamewith.jp/pc/news",
        )

        self.assertEqual(
            actual,
            "https://gamewith.jp/pc/news?p=2&ref=category",
        )

    def test_rejects_non_http_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTP"):
            normalize_article_url("javascript:alert(1)", "https://example.com/")

    def test_requires_exact_https_origin(self) -> None:
        require_https_origin("https://example.com/path", "example.com")
        for unsafe in (
            "http://example.com/path",
            "https://user@example.com/path",
            "https://example.com:8443/path",
        ):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(ValueError):
                    require_https_origin(unsafe, "example.com")


if __name__ == "__main__":
    unittest.main()
