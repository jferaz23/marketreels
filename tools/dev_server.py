"""Local preview with live prices: serves the site and mimics the Vercel functions in api/.

    python tools/dev_server.py [port]      # then open http://localhost:8000
"""
import json
import sys
import urllib.parse
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from quotes import SPARK, UA  # noqa: E402


def spark(symbols, intraday):
    out = {}
    for i in range(0, len(symbols), 20):
        url = SPARK + "?" + urllib.parse.urlencode({"symbols": ",".join(symbols[i:i + 20]), "range": "1d", "interval": "5m" if intraday else "1d"})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                data = json.load(r)
        except Exception:
            continue
        for res in (data.get("spark") or {}).get("result") or []:
            resp = (res.get("response") or [{}])[0]
            m = resp.get("meta") or {}
            price, prev = m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")
            if price is None:
                continue
            q = {"price": price, "prev": prev, "chg": (price / prev - 1) * 100 if prev else None, "time": m.get("regularMarketTime"),
                 "type": m.get("instrumentType"), "name": m.get("shortName") or m.get("longName")}
            if intraday:
                pts = [p for p in ((resp.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [] if p is not None]
                step = max(1, len(pts) // 60)
                q["points"] = pts[::step][:59] + pts[-1:]
            out[res["symbol"]] = q
    return out


def news(sym):
    url = "https://query1.finance.yahoo.com/v1/finance/search?" + urllib.parse.urlencode({"q": sym, "quotesCount": 0, "newsCount": 8})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            items = json.load(r).get("news") or []
    except Exception:
        items = []
    return [{"title": n["title"], "publisher": n.get("publisher"), "url": n.get("link"), "time": n.get("providerPublishTime")} for n in items]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        s = q.get("s", [""])[0].upper()
        if url.path.rstrip("/") == "/api/quotes":
            body = {"source": "yahoo-live", "generated_at": None, "quotes": spark([x for x in s.split(",") if x][:120], q.get("spark") == ["1"])}
        elif url.path.rstrip("/") == "/api/news":
            body = {"symbol": s, "news": news(s)}
        else:
            return super().do_GET()
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"MarketReels on http://localhost:{port} (live quotes at /api/quotes, news at /api/news)")
    ThreadingHTTPServer(("", port), partial(Handler, directory=str(ROOT))).serve_forever()
