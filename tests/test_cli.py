from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import ANY, patch

import make_rss


class CliTests(unittest.TestCase):
    def test_help_documents_public_arguments(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parents[1] / "make_rss.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--output-dir", result.stdout)
        self.assertIn("--base-url", result.stdout)
        self.assertIn("--limit", result.stdout)
        self.assertIn("--deployment-id", result.stdout)

    @patch("make_rss.write_feed_files")
    @patch("make_rss.collect_denfami")
    @patch("make_rss.collect_gamewith")
    @patch("make_rss.collect_gamewatch")
    def test_limit_is_also_the_required_minimum(
        self,
        collect_gamewatch,
        collect_gamewith,
        collect_denfami,
        write_feed_files,
    ) -> None:
        collect_gamewatch.return_value = []
        collect_gamewith.return_value = []
        collect_denfami.return_value = []
        write_feed_files.return_value = {
            "GAME Watch": 40,
            "GameWith": 40,
            "Denfami": 40,
        }

        with patch.object(sys, "argv", ["make_rss.py", "--limit", "40"]):
            result = make_rss.main()

        self.assertEqual(result, 0)
        collect_gamewatch.assert_called_once_with(ANY, 40, 40)
        collect_gamewith.assert_called_once_with(ANY, 40, 40)
        collect_denfami.assert_called_once_with(ANY, 40, 40)


if __name__ == "__main__":
    unittest.main()
