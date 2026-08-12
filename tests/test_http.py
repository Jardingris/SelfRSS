from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

import requests

from selfrss.http import HttpClient, RobotsDenied, UnsafeRedirect


class LocalHandler(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}

    def do_GET(self) -> None:
        self.counts[self.path] = self.counts.get(self.path, 0) + 1
        if self.path == "/retry" and self.counts[self.path] < 3:
            self.send_response(503)
            self.end_headers()
            return
        if self.path == "/retry":
            body = "成功".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/robots.txt":
            body = b"User-agent: *\nDisallow: /blocked\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/empty-robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            return
        if self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            return
        if self.path == "/rate-limited":
            self.send_response(429)
            self.send_header("Retry-After", "120")
            self.end_headers()
            return
        if self.path == "/cross-origin":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/private")
            self.end_headers()
            return
        if self.path == "/same-origin":
            self.send_response(302)
            self.send_header("Location", "/blocked/article")
            self.end_headers()
            return
        if self.path == "/too-large":
            self.send_response(200)
            self.send_header("Content-Length", str(6 * 1024 * 1024))
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class HttpClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self) -> None:
        LocalHandler.counts.clear()
        self.client = HttpClient()

    def test_retries_transient_status_twice(self) -> None:
        self.assertEqual(self.client.get_text(f"{self.base_url}/retry"), "成功")
        self.assertEqual(LocalHandler.counts["/retry"], 3)

    def test_does_not_retry_client_error(self) -> None:
        with self.assertRaises(requests.HTTPError):
            self.client.get_text(f"{self.base_url}/missing")
        self.assertEqual(LocalHandler.counts["/missing"], 1)

    def test_does_not_retry_rate_limit(self) -> None:
        with self.assertRaises(requests.HTTPError):
            self.client.get_text(f"{self.base_url}/rate-limited")
        self.assertEqual(LocalHandler.counts["/rate-limited"], 1)

    def test_enforces_robots_disallow(self) -> None:
        self.client.ensure_robots_allowed(
            f"{self.base_url}/robots.txt",
            f"{self.base_url}/allowed",
        )
        with self.assertRaises(RobotsDenied):
            self.client.ensure_robots_allowed(
                f"{self.base_url}/robots.txt",
                f"{self.base_url}/blocked/article",
            )
        self.assertEqual(LocalHandler.counts["/robots.txt"], 1)

    def test_empty_robots_file_does_not_deny_public_page(self) -> None:
        self.client.ensure_robots_allowed(
            f"{self.base_url}/empty-robots.txt",
            f"{self.base_url}/public",
        )

    def test_rejects_redirect_to_different_origin(self) -> None:
        with self.assertRaisesRegex(UnsafeRedirect, "redirect is not allowed"):
            self.client.get_text(f"{self.base_url}/cross-origin")

    def test_rejects_same_origin_redirect_before_new_path_fetch(self) -> None:
        with self.assertRaisesRegex(UnsafeRedirect, "redirect is not allowed"):
            self.client.get_text(f"{self.base_url}/same-origin")
        self.assertNotIn("/blocked/article", LocalHandler.counts)

    def test_rejects_response_larger_than_limit(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            self.client.get_text(f"{self.base_url}/too-large")


if __name__ == "__main__":
    unittest.main()
