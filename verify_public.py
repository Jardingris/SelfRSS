#!/usr/bin/env python3
import argparse
import sys
import time

import requests

from selfrss.errors import ExtractionError
from selfrss.public_verify import verify_public_site


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="公開済みRSSを検証する")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--minimum", type=int, default=30)
    parser.add_argument("--deployment-id")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    args = parser.parse_args()
    if args.minimum < 1 or args.attempts < 1 or args.retry_delay < 0:
        parser.error("minimum/attempts must be positive and retry-delay non-negative")
    return args


def main() -> int:
    args = parse_args()
    for attempt in range(1, args.attempts + 1):
        try:
            counts = verify_public_site(
                args.base_url,
                minimum=args.minimum,
                expected_deployment_id=args.deployment_id,
            )
        except (ExtractionError, OSError, RuntimeError, ValueError, requests.RequestException) as error:
            if attempt == args.attempts:
                print(f"Public verification failed: {error}", file=sys.stderr)
                return 1
            print(f"Attempt {attempt}/{args.attempts} failed: {error}")
            time.sleep(args.retry_delay)
            continue

        print("Public verification: OK")
        for filename, count in counts.items():
            print(f"{filename}: HTTP 200, XML OK, {count} items")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
