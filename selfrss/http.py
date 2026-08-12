from urllib import robotparser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENT = "PersonalPCGameRSS/1.0 (+GitHub Pages feed generator)"
TIMEOUT = (5, 20)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class RobotsDenied(RuntimeError):
    pass


class UnsafeRedirect(RuntimeError):
    pass


class HttpClient:
    def __init__(self) -> None:
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            allowed_methods=frozenset({"GET"}),
            status_forcelist=(500, 502, 503, 504),
            backoff_factor=0.1,
            backoff_max=5,
            respect_retry_after_header=False,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._robots: dict[str, robotparser.RobotFileParser] = {}

    def get_response(self, url: str) -> requests.Response:
        response = self.session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=True,
        )
        if response.is_redirect or response.is_permanent_redirect:
            response.close()
            raise UnsafeRedirect(f"redirect is not allowed for fixed source URL: {url}")
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_RESPONSE_BYTES:
            response.close()
            raise RuntimeError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_RESPONSE_BYTES:
                response.close()
                raise RuntimeError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
        response._content = bytes(content)
        response._content_consumed = True
        return response

    def get_text(self, url: str) -> str:
        response = self.get_response(url)
        content_type = response.headers.get("Content-Type", "")
        if "charset=" not in content_type.lower():
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def ensure_robots_allowed(self, robots_url: str, target_url: str) -> None:
        rules = self._robots.get(robots_url)
        if rules is None:
            rules = robotparser.RobotFileParser()
            rules.set_url(robots_url)
            rules.parse(self.get_text(robots_url).splitlines())
            self._robots[robots_url] = rules
        if not rules.can_fetch(USER_AGENT, target_url):
            raise RobotsDenied(f"robots.txt disallows {target_url}")
