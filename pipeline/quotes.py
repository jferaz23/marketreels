"""Near-real-time quotes from Yahoo Finance's spark endpoint (free, no key), written to data/quotes.json.

GitHub Actions runs this every ~15 minutes in market hours so the GitHub Pages build stays fresh.
build_feed.py also uses it: Yahoo's live quote has the correct previous close, which daily history gets
wrong for futures around contract rolls. Standard library only, so it runs without installing anything.

    python pipeline/quotes.py
"""
import json
import logging
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ASSETS, DASHBOARD_EXTRA, FUTURES, GLOBAL, INDICES, SECTORS, VOLATILITY, WATCHLIST, YIELDS  # noqa: E402

log = logging.getLogger(__name__)
SPARK = "https://query1.finance.yahoo.com/v7/finance/spark"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
OUT = Path(__file__).resolve().parent.parent / "data" / "quotes.json"
ALL_SYMBOLS = [*INDICES, *FUTURES, *VOLATILITY, *YIELDS, *ASSETS, *GLOBAL, *SECTORS, *WATCHLIST, *DASHBOARD_EXTRA]


def fetch_live(symbols=ALL_SYMBOLS, chunk=20):
    """Returns {symbol: {price, prev, chg, time, type}} for every symbol Yahoo answered."""
    out = {}
    for i in range(0, len(symbols), chunk):
        part = symbols[i:i + chunk]
        url = SPARK + "?" + urllib.parse.urlencode({"symbols": ",".join(part), "range": "1d", "interval": "1d"})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                data = json.load(r)
        except Exception as e:  # one failed batch shouldn't lose the rest
            log.warning("spark batch %d failed: %s", i // chunk, e)
            continue
        for res in (data.get("spark") or {}).get("result") or []:
            try:
                m = res["response"][0]["meta"]
            except (KeyError, IndexError, TypeError):
                continue
            price = m.get("regularMarketPrice")
            prev = m.get("chartPreviousClose") or m.get("previousClose")
            if price is None:
                continue
            out[res["symbol"]] = {
                "price": round(price, 4),
                "prev": round(prev, 4) if prev else None,
                "chg": round((price / prev - 1) * 100, 3) if prev else None,
                "time": m.get("regularMarketTime"),
                "type": m.get("instrumentType"),
            }
    log.info("live quotes: %d of %d symbols", len(out), len(symbols))
    return out


def write(quotes, path=OUT):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "source": "yahoo", "quotes": quotes}, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    q = fetch_live()
    if not q:
        sys.exit("no quotes fetched; leaving the previous quotes.json in place")
    write(q)
    print(f"wrote {len(q)} quotes to {OUT}")
