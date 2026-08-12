from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from selfrss.gamewatch import collect_gamewatch
from selfrss.gamewith import collect_gamewith
from selfrss.denfami import collect_denfami
from selfrss.generator import write_feed_files
from selfrss.http import HttpClient


@unittest.skipUnless(os.environ.get("SELFRSS_LIVE") == "1", "live test disabled")
class LiveSiteTests(unittest.TestCase):
    def test_live_pages_match_generated_feed_heads(self) -> None:
        client = HttpClient()
        gamewatch = collect_gamewatch(client, limit=40, minimum=40)
        gamewith = collect_gamewith(client, limit=40, minimum=40)
        denfami = collect_denfami(client, limit=40, minimum=40)
        self.assertEqual(
            gamewatch,
            sorted(
                gamewatch,
                key=lambda article: article.listed_at,
                reverse=True,
            ),
        )
        self.assertEqual(
            gamewith,
            sorted(gamewith, key=lambda article: article.published, reverse=True),
        )
        self.assertEqual(
            denfami,
            sorted(denfami, key=lambda article: article.listed_at, reverse=True),
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_feed_files(
                gamewatch,
                gamewith,
                denfami,
                output,
                "https://example.github.io/SelfRSS/",
                built_at=datetime.now(timezone.utc),
                minimum=40,
            )
            comparisons = (
                ("GAME Watch", gamewatch, output / "gamewatch-pc.xml"),
                ("GameWith", gamewith, output / "gamewith-pc.xml"),
                ("Denfami", denfami, output / "denfami-steam.xml"),
            )
            for source, articles, feed_path in comparisons:
                items = ET.parse(feed_path).getroot().findall("channel/item")
                self.assertEqual(len(items), 40)
                self.assertEqual(items[0].findtext("title"), articles[0].title)
                self.assertEqual(items[0].findtext("link"), articles[0].url)
                print(f"[{source}]")
                for article in articles[:5]:
                    timestamp = article.published or article.listed_at
                    displayed_at = timestamp.isoformat() if timestamp else "unknown"
                    print(f"{displayed_at} | {article.title}")
                    print(article.url)


if __name__ == "__main__":
    unittest.main()
