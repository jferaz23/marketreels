"""Local preview with live prices: serves the site and mimics Vercel's /api/quotes endpoint.

    python tools/dev_server.py [port]      # then open http://localhost:8000
"""
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from quotes import fetch_live  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path.rstrip("/") != "/api/quotes":
            return super().do_GET()
        symbols = [s for s in parse_qs(url.query).get("s", [""])[0].upper().split(",") if s][:120]
        body = json.dumps({"source": "yahoo-live", "generated_at": None, "quotes": fetch_live(symbols)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"MarketReels on http://localhost:{port} (live quotes at /api/quotes)")
    ThreadingHTTPServer(("", port), partial(Handler, directory=str(ROOT))).serve_forever()
