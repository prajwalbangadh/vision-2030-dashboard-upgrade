from __future__ import annotations

import http.server
import socketserver
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
SITE_DIR = Path(__file__).resolve().parent


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    with ReusableTCPServer((HOST, PORT), handler) as server:
        url = f"http://{HOST}:{PORT}/briefing.html"
        print(f"Serving Vision 2030 static site from: {SITE_DIR}")
        print(f"Open: {url}")
        print("Press Ctrl+C to stop the server.")
        webbrowser.open(url)
        server.serve_forever()


if __name__ == "__main__":
    import os

    os.chdir(SITE_DIR)
    main()
