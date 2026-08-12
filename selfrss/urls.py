from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


TRACKING_QUERY_KEYS = {
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def require_https_origin(url: str, expected_host: str) -> None:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != expected_host
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
    ):
        raise ValueError(f"URL must use the approved HTTPS origin: {url}")


def normalize_article_url(url: str, base_url: str) -> str:
    absolute = urljoin(base_url, url)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("article URL must use HTTP or HTTPS")

    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in TRACKING_QUERY_KEYS:
            continue
        if key.lower() == "ref" and value.lower() == "rss":
            continue
        query.append((key, value))

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path,
            urlencode(query, doseq=True),
            "",
        )
    )
