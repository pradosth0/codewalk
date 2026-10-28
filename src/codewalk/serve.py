"""A small static file server for an output folder (steps.json + index.html)."""

from __future__ import annotations

import os
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Union


class _Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - signature fixed by stdlib
        pass


def make_server(directory: Union[str, os.PathLike], host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Create (but do not start) a server for `directory`; port 0 picks a free port."""
    handler = partial(_Handler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def server_url(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"


def serve(directory: Union[str, os.PathLike], host: str = "127.0.0.1", port: int = 8731, open_browser: bool = False) -> None:
    """Serve `directory` until interrupted."""
    with make_server(directory, host, port) as httpd:
        url = server_url(httpd)
        print(f"serving {os.path.abspath(directory)} at {url} (Ctrl-C to stop)", file=sys.stderr, flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
