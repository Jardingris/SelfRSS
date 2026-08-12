from pathlib import Path
import unittest

from bs4 import BeautifulSoup


class SiteIndexTests(unittest.TestCase):
    def test_index_discourages_discovery_and_does_not_link_feeds(self) -> None:
        index = Path(__file__).parents[1] / "site" / "index.html"
        soup = BeautifulSoup(index.read_text(), "html.parser")

        robots = soup.select_one('meta[name="robots"]')
        self.assertIsNotNone(robots)
        self.assertEqual(robots.get("content"), "noindex,nofollow")
        self.assertEqual(soup.select('a[href$=".xml"]'), [])
        self.assertNotIn("gamewatch-pc.xml", index.read_text())
        self.assertNotIn("gamewith-pc.xml", index.read_text())
        self.assertNotIn("denfami-steam.xml", index.read_text())


if __name__ == "__main__":
    unittest.main()
