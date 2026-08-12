from datetime import datetime
import unittest

import requests

from selfrss.models import Article
from selfrss.public_verify import verify_public_site
from selfrss.rss import render_rss


class FakeResponse:
    def __init__(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.content = body
        self.headers = {"Content-Type": content_type}
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses

    def get(self, url: str, timeout: tuple[int, int]) -> FakeResponse:
        del timeout
        return self.responses[url]


def make_feed(host: str, count: int) -> bytes:
    articles = [
        Article(
            title=f"Article {number}",
            url=f"https://{host}/article/{number}",
            published=datetime.fromisoformat("2026-08-12T09:00:00+09:00"),
        )
        for number in range(count)
    ]
    return render_rss(
        channel_title="Test feed",
        channel_url=f"https://{host}/",
        channel_description="Test feed",
        articles=articles,
        self_url="https://jardingris.github.io/SelfRSS/test.xml",
        built_at=datetime.fromisoformat("2026-08-12T09:00:00+09:00"),
    )


class PublicVerifyTests(unittest.TestCase):
    def test_verifies_index_and_all_public_feeds(self) -> None:
        base = "https://jardingris.github.io/SelfRSS/"
        session = FakeSession(
            {
                base: FakeResponse(b"<!doctype html>", "text/html; charset=utf-8"),
                f"{base}deployment.txt?deployment=12345-2": FakeResponse(b"12345-2\n", "text/plain"),
                f"{base}gamewatch-pc.xml?deployment=12345-2": FakeResponse(
                    make_feed("game.watch.impress.co.jp", 40),
                    "application/xml",
                ),
                f"{base}gamewith-pc.xml?deployment=12345-2": FakeResponse(
                    make_feed("gamewith.jp", 40),
                    "application/rss+xml; charset=utf-8",
                ),
                f"{base}denfami-steam.xml?deployment=12345-2": FakeResponse(
                    make_feed("news.denfaminicogamer.jp", 40),
                    "application/xml",
                ),
            }
        )

        result = verify_public_site(
            base,
            minimum=40,
            expected_deployment_id="12345-2",
            session=session,
        )

        self.assertEqual(result["gamewatch-pc.xml"], 40)
        self.assertEqual(result["gamewith-pc.xml"], 40)
        self.assertEqual(result["denfami-steam.xml"], 40)

    def test_rejects_html_served_for_feed(self) -> None:
        base = "https://jardingris.github.io/SelfRSS/"
        session = FakeSession(
            {
                base: FakeResponse(b"<!doctype html>", "text/html"),
                f"{base}deployment.txt?deployment=12345-2": FakeResponse(b"12345-2\n", "text/plain"),
                f"{base}gamewatch-pc.xml?deployment=12345-2": FakeResponse(b"not xml", "text/html"),
                f"{base}gamewith-pc.xml?deployment=12345-2": FakeResponse(
                    make_feed("gamewith.jp", 40),
                    "application/xml",
                ),
            }
        )

        with self.assertRaisesRegex(RuntimeError, "Content-Type"):
            verify_public_site(
                base,
                minimum=40,
                expected_deployment_id="12345-2",
                session=session,
            )

    def test_rejects_stale_deployment_marker(self) -> None:
        base = "https://jardingris.github.io/SelfRSS/"
        session = FakeSession(
            {
                base: FakeResponse(b"<!doctype html>", "text/html"),
                f"{base}deployment.txt?deployment=current-run": FakeResponse(b"old-run\n", "text/plain"),
            }
        )

        with self.assertRaisesRegex(RuntimeError, "deployment marker"):
            verify_public_site(
                base,
                minimum=40,
                expected_deployment_id="current-run",
                session=session,
            )

    def test_requires_https_base_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            verify_public_site("http://example.test/", minimum=40, session=FakeSession({}))


if __name__ == "__main__":
    unittest.main()
