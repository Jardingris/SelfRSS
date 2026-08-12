from collections.abc import Mapping
from urllib.parse import quote, urlsplit

import requests

from selfrss.http import HttpClient, TIMEOUT
from selfrss.urls import require_https_origin
from selfrss.validation import validate_rss


FEEDS: Mapping[str, str] = {
    "gamewatch-pc.xml": "game.watch.impress.co.jp",
    "gamewith-pc.xml": "gamewith.jp",
    "denfami-steam.xml": "news.denfaminicogamer.jp",
}
XML_CONTENT_TYPES = ("application/xml", "application/rss+xml", "text/xml")


def verify_public_site(
    base_url: str,
    minimum: int,
    expected_deployment_id: str | None = None,
    session: requests.Session | None = None,
) -> dict[str, int]:
    parts = urlsplit(base_url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("public base URL must use HTTPS")
    require_https_origin(base_url, parts.hostname)
    if parts.query or parts.fragment:
        raise ValueError("public base URL must not contain a query or fragment")
    normalized_base = base_url.rstrip("/") + "/"
    cache_buster = (
        f"?deployment={quote(expected_deployment_id, safe='')}"
        if expected_deployment_id is not None
        else ""
    )

    safe_client = HttpClient() if session is None else None

    def get(url: str):
        if safe_client is not None:
            return safe_client.get_response(url)
        return session.get(url, timeout=TIMEOUT)

    index = get(normalized_base)
    index.raise_for_status()
    index_type = index.headers.get("Content-Type", "").lower()
    if "text/html" not in index_type:
        raise RuntimeError(f"unexpected index Content-Type: {index_type or '(missing)'}")

    if expected_deployment_id is not None:
        marker = get(f"{normalized_base}deployment.txt{cache_buster}")
        marker.raise_for_status()
        if marker.content.decode("utf-8").strip() != expected_deployment_id:
            raise RuntimeError("public deployment marker does not match this run")

    counts: dict[str, int] = {}
    for filename, article_host in FEEDS.items():
        response = get(f"{normalized_base}{filename}{cache_buster}")
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if not any(allowed in content_type for allowed in XML_CONTENT_TYPES):
            raise RuntimeError(
                f"unexpected Content-Type for {filename}: {content_type or '(missing)'}"
            )
        counts[filename] = validate_rss(
            response.content,
            expected_host=article_host,
            minimum=minimum,
            maximum=minimum,
        )
    return counts
