from __future__ import annotations

import argparse
import json
import mimetypes
import platform
import subprocess
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar, TypedDict
from urllib.parse import urlparse

from .providers.dart import DartApiError, MissingDartApiKey
from .providers.dart_http import DartTransportError
from .web_state import BrowserState, WebPaths, build_state, fill_financials_state, refresh_state

UI_DIR = Path(__file__).with_name("ui")


@dataclass(frozen=True, slots=True)
class ServerSettings:
    host: str
    port: int
    paths: WebPaths
    top_n: int
    open_browser: bool


class ErrorPayload(TypedDict):
    error: str


class AppHandler(BaseHTTPRequestHandler):
    paths: ClassVar[WebPaths]
    top_n: ClassVar[int]

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path in {
            "/",
            "/index.html",
            "/api/state",
            "/assets/styles.css",
            "/assets/components.css",
            "/assets/responsive.css",
            "/assets/app.js",
        }:
            self.send_response(200)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._send_json(200, build_state(self.paths))
            return
        if path in {"/", "/index.html"}:
            self._send_file(UI_DIR / "index.html")
            return
        assets = {
            "/assets/styles.css": UI_DIR / "styles.css",
            "/assets/components.css": UI_DIR / "components.css",
            "/assets/responsive.css": UI_DIR / "responsive.css",
            "/assets/app.js": UI_DIR / "app.js",
        }
        if path in assets:
            self._send_file(assets[path])
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/refresh":
            self._send_json(200, refresh_state(self.paths, self.top_n))
            return
        if path == "/api/financials":
            try:
                self._send_json(200, fill_financials_state(self.paths))
            except MissingDartApiKey:
                self._send_json(400, {"error": "DART_API_KEY 환경변수가 필요합니다."})
            except (DartApiError, DartTransportError) as exc:
                self._send_json(502, {"error": str(exc)})
            return
        self._send_json(404, {"error": "not found"})

    def _send_json(self, status: int, payload: BrowserState | ErrorPayload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: str) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def _handler(settings: ServerSettings) -> type[AppHandler]:
    AppHandler.paths = settings.paths
    AppHandler.top_n = settings.top_n
    return AppHandler


def _open_browser(url: str) -> None:
    if platform.system() == "Darwin":
        try:
            subprocess.Popen(["open", "-a", "Google Chrome", url])
            return
        except OSError:
            webbrowser.open(url)
            return
    try:
        webbrowser.get("chrome").open(url)
    except webbrowser.Error:
        webbrowser.open(url)


def serve(settings: ServerSettings) -> None:
    url = f"http://{settings.host}:{settings.port}"
    with ThreadingHTTPServer((settings.host, settings.port), _handler(settings)) as server:
        print(f"Public Hurdle UI: {url}")
        if settings.open_browser:
            _open_browser(url)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(prog="hurdle-web", description="Public Hurdle local browser UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--universe", type=Path, default=Path("data/kr_top100.csv"))
    parser.add_argument("--pool", type=Path, default=Path("data/kr_pool.csv"))
    parser.add_argument("--config", type=Path, default=Path("config/semiconductor.yaml"))
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    serve(
        ServerSettings(
            host=args.host,
            port=args.port,
            paths=WebPaths(universe=args.universe, pool=args.pool, config=args.config),
            top_n=args.top,
            open_browser=not args.no_open,
        )
    )


if __name__ == "__main__":
    main()
