"""Headlines from free RSS feeds, scored for relevance to US markets."""
import calendar
import html
import logging
import re
import time
from datetime import datetime, timezone

import feedparser
import requests

from config import NEWS_BLOCKLIST, NEWS_FEEDS, TOPICS, WATCHLIST

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (compatible; MarketReels/1.0; educational news digest)"}

MARKET_WORDS = {
    "stock": 2, "stocks": 2, "market": 2, "wall street": 3, "s&p": 3, "nasdaq": 3, "dow": 2, "investor": 1,
    "shares": 2, "earnings": 2, "fed": 3, "rate": 2, "inflation": 3, "treasury": 2, "yield": 2, "economy": 2,
    "tariff": 2, "oil": 1, "dollar": 1, "bank": 1, "recession": 3, "jobs": 2, "gdp": 3, "bond": 2, "ipo": 2,
    "merger": 2, "acquisition": 2, "deal": 1, "profit": 1, "revenue": 1, "guidance": 2, "chip": 1, "ai": 1,
}


def _strip(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _image(entry):
    for key in ("media_content", "media_thumbnail"):
        items = entry.get(key) or []
        best = None
        for m in items:
            url, w = m.get("url"), int(m.get("width") or 0)
            if url and (best is None or w > best[1]):
                best = (url, w)
        if best:
            # BBC serves resizable images; ask for a larger rendition.
            return re.sub(r"/standard/\d+/", "/standard/976/", best[0])
    for enc in entry.get("enclosures") or []:
        if str(enc.get("type", "")).startswith("image"):
            return enc.get("href")
    return None


def match_tickers(text):
    found = []
    for sym, (_, aliases) in WATCHLIST.items():
        for a in aliases:
            if re.search(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])", text):
                found.append(sym)
                break
    return found


def match_topic(text):
    low = f" {text.lower()} "
    best, score = None, 0
    for t in TOPICS:
        s = sum(low.count(k) for k in t["keys"])
        if s > score:
            best, score = t, s
    return best


def fetch_news(max_age_hours=36, limit=40):
    items, seen = [], set()
    now = time.time()
    for source, url, weight in NEWS_FEEDS:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        except Exception as e:
            log.warning("feed %s failed: %s", source, e)
            continue
        for e in feed.entries:
            title = _strip(e.get("title"))
            link = e.get("link")
            if not title or not link:
                continue
            key = re.sub(r"\W+", "", title.lower())[:60]
            if key in seen:
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            epoch = calendar.timegm(ts) if ts else now
            age_h = (now - epoch) / 3600
            if age_h > max_age_hours:
                continue
            summary = _strip(e.get("summary") or e.get("description"))
            text = f"{title} {summary}"
            low = text.lower()
            if any(b in low for b in NEWS_BLOCKLIST):
                continue
            relevance = sum(w for k, w in MARKET_WORDS.items() if re.search(r"\b" + re.escape(k) + r"\b", low))
            tickers = match_tickers(text)
            relevance += 2 * len(tickers) + weight
            if source.startswith("Federal Reserve"):
                relevance += 3 if any(k in low for k in ("fomc", "monetary policy", "rate", "statement")) else -4
            if relevance < 4:
                continue
            seen.add(key)
            items.append({
                "title": title,
                "summary": summary[:600],
                "url": link,
                "source": source.split(" ")[0] if source.startswith("CNBC") else source,
                "published": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(),
                "age_hours": round(age_h, 1),
                "image": _image(e),
                "tickers": tickers,
                "topic": (match_topic(text) or {}).get("id"),
                # Fresh, relevant stories first.
                "score": relevance - age_h / 6,
            })
    items.sort(key=lambda x: x["score"], reverse=True)
    log.info("news: %d relevant headlines", len(items))
    return items[:limit]
