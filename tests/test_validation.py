from datetime import datetime, timedelta, timezone
import unittest

from selfrss.errors import ExtractionError
from selfrss.models import Article
from selfrss.validation import validate_article_freshness


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


class ArticleFreshnessTests(unittest.TestCase):
    def test_accepts_recent_timezone_aware_article(self) -> None:
        articles = [
            Article(
                "recent",
                "https://example.com/1",
                NOW - timedelta(hours=1),
            ),
            Article("unknown", "https://example.com/2"),
        ]

        validate_article_freshness(articles, now=NOW)

    def test_rejects_feed_with_no_known_datetime(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "known datetime"):
            validate_article_freshness(
                [Article("unknown", "https://example.com/1")],
                now=NOW,
            )

    def test_rejects_latest_article_older_than_fourteen_days(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "older than 14 days"):
            validate_article_freshness(
                [
                    Article(
                        "old",
                        "https://example.com/1",
                        NOW - timedelta(days=15),
                    )
                ],
                now=NOW,
            )

    def test_rejects_latest_article_more_than_day_in_future(self) -> None:
        with self.assertRaisesRegex(ExtractionError, "future"):
            validate_article_freshness(
                [
                    Article(
                        "future",
                        "https://example.com/1",
                        NOW + timedelta(hours=25),
                    )
                ],
                now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
