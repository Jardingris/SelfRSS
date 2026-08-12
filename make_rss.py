#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import requests

from selfrss.errors import ExtractionError
from selfrss.denfami import collect_denfami
from selfrss.gamewatch import collect_gamewatch
from selfrss.gamewith import collect_gamewith
from selfrss.generator import write_feed_files
from selfrss.http import HttpClient, RobotsDenied


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate unofficial PC game RSS feeds from GAME Watch, GameWith, "
            "and Denfaminicogamer."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=Path("site"))
    parser.add_argument("--base-url", help="Published GitHub Pages base URL")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--deployment-id", help="Run-specific marker deployed with feeds")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    minimum = args.limit
    built_at = datetime.now(timezone.utc)
    try:
        client = HttpClient()
        gamewatch_articles = collect_gamewatch(client, args.limit, minimum)
        gamewith_articles = collect_gamewith(client, args.limit, minimum)
        denfami_articles = collect_denfami(client, args.limit, minimum)
        counts = write_feed_files(
            gamewatch_articles,
            gamewith_articles,
            denfami_articles,
            args.output_dir,
            args.base_url,
            built_at,
            minimum,
            args.deployment_id,
        )
    except (ExtractionError, RobotsDenied, requests.RequestException, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    for source, articles in (
        ("GAME Watch", gamewatch_articles),
        ("GameWith", gamewith_articles),
        ("Denfami", denfami_articles),
    ):
        print(f"[{source}]")
        for article in articles[:5]:
            timestamp = article.published or article.listed_at
            displayed_at = timestamp.isoformat() if timestamp else "datetime unavailable"
            print(f"{displayed_at} | {article.title}")
            print(article.url)
        print()
    print(f"GAME Watch: {counts['GAME Watch']} items")
    print(f"GameWith: {counts['GameWith']} items")
    print(f"Denfami: {counts['Denfami']} items")
    print("RSS parse: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
