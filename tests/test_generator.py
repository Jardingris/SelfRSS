from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from selfrss.errors import ExtractionError
from selfrss.generator import write_feed_files
from selfrss.models import Article


NOW = datetime.fromisoformat("2026-08-12T12:00:00+09:00")


class GeneratorTests(unittest.TestCase):
    def test_writes_all_validated_feed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            counts = write_feed_files(
                [Article("GW", "https://game.watch.impress.co.jp/docs/news/1.html", NOW)],
                [Article("GameWith", "https://gamewith.jp/gamedb/1", NOW)],
                [
                    Article(
                        "Denfami",
                        "https://news.denfaminicogamer.jp/news/1",
                        listed_at=NOW,
                    )
                ],
                output,
                "https://owner.github.io/SelfRSS/",
                built_at=NOW,
                minimum=1,
                deployment_id="12345-2",
            )

            self.assertEqual(
                counts,
                {"GAME Watch": 1, "GameWith": 1, "Denfami": 1},
            )
            self.assertIn(
                b"https://owner.github.io/SelfRSS/gamewatch-pc.xml",
                (output / "gamewatch-pc.xml").read_bytes(),
            )
            self.assertTrue((output / "gamewith-pc.xml").is_file())
            denfami = (output / "denfami-steam.xml").read_bytes()
            self.assertIn(
                b"https://owner.github.io/SelfRSS/denfami-steam.xml",
                denfami,
            )
            self.assertNotIn(b"<pubDate>", denfami)
            self.assertEqual((output / "deployment.txt").read_text(), "12345-2\n")

    def test_keeps_all_existing_files_when_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            gamewatch = output / "gamewatch-pc.xml"
            gamewith = output / "gamewith-pc.xml"
            denfami = output / "denfami-steam.xml"
            gamewatch.write_bytes(b"old-gamewatch")
            gamewith.write_bytes(b"old-gamewith")
            denfami.write_bytes(b"old-denfami")

            with self.assertRaises(ExtractionError):
                write_feed_files(
                    [
                        Article(
                            "GW",
                            "https://game.watch.impress.co.jp/docs/news/1.html",
                            NOW,
                        )
                    ],
                    [],
                    [],
                    output,
                    None,
                    built_at=NOW,
                    minimum=1,
                )

            self.assertEqual(gamewatch.read_bytes(), b"old-gamewatch")
            self.assertEqual(gamewith.read_bytes(), b"old-gamewith")
            self.assertEqual(denfami.read_bytes(), b"old-denfami")


if __name__ == "__main__":
    unittest.main()
