"""Real finance video clips for the feed, from news outlets' public YouTube channels (free RSS, no key).

Writes data/videos.json. Keeps recent, market-relevant, short clips (Shorts first), skips live streams and
long shows. The app plays them in YouTube's embedded player.

    python pipeline/videos.py
"""
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from news import MARKET_WORDS, match_tickers, match_topic  # noqa: E402

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "videos.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

# (name, channel id, relevance bonus). Markets-first channels get a bonus; general news channels must earn it.
CHANNELS = [
    ("Bloomberg Television", "UCIALMKvObZNtJ6AmdCLP7Lg", 4),
    ("CNBC Television", "UCrp_UI8XtuYfpiqluWLD7Lw", 4),
    ("Yahoo Finance", "UCEAZeUIeJs0IjQiqTCdVSIg", 4),
    ("CNBC", "UCvJJ_dzjViJCoLf5uKUTwoA", 3),
    ("Financial Times", "UCoUxsWakJucWg46KW5RsvPw", 2),
    ("Wall Street Journal", "UCK7tptUDHh-RYDsdxO1-5QQ", 1),
    ("Bloomberg Originals", "UCUMZ7gohGI9HcU9VNsr2FJQ", 1),
    ("Reuters", "UChqUTb7kYRX8-EiaN3XFrSQ", 0),
    ("Fox Business", "UCCXoCcu9Rp7NPbTzIvogpZg", 0),
    ("The Economist", "UC0p5jTq6Xx_DosDFxVXnWaQ", 0),
    ("Patrick Boyle", "UCASM0cgfkJxQ1ICmRilfHLw", 3),
]
MAX_AGE_H = 60
MAX_SECONDS = 12 * 60
SKIP_TITLE = re.compile(r"\bLIVE\b|livestream|streaming now|full episode|full show|podcast|\bwatch live\b|\bpanel\b|"
                        r"\bhour \d|\(\d{1,2}/\d{1,2}/\d{2,4}\)|\bsurveillance\b|\bdaybreak\b|the close\b|"
                        r"market domination|morning brief|opening bid|catalysts\b|wealth!", re.I)
# GitHub's servers usually get no length from YouTube; the app then skips anything long or live as it loads.
UA_COOKIE = {"Cookie": "CONSENT=YES+cb; SOCS=CAI"}


def _meta(vid):
    """Shorts? length? live? Missing info stays None (YouTube can throttle these pages)."""
    out = {"shorts": None, "seconds": None, "live": False}
    try:
        r = requests.head(f"https://www.youtube.com/shorts/{vid}", headers=UA, allow_redirects=False, timeout=12)
        out["shorts"] = r.status_code == 200
    except requests.RequestException:
        pass
    try:
        html = requests.get(f"https://www.youtube.com/watch?v={vid}", headers={**UA, **UA_COOKIE}, timeout=15).text
        m = re.search(r'"lengthSeconds":"(\d+)"', html)
        out["seconds"] = int(m.group(1)) if m else None
        out["live"] = '"isLiveContent":true' in html or '"isLive":true' in html
    except requests.RequestException:
        pass
    return out


def fetch_videos(limit=36):
    now = time.time()
    cands, seen = [], set()
    for name, cid, bonus in CHANNELS:
        try:
            r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", headers=UA, timeout=20)
            r.raise_for_status()
            entries = feedparser.parse(r.content).entries
        except Exception as e:
            log.warning("feed %s failed: %s", name, e)
            continue
        for e in entries:
            vid, title = e.get("yt_videoid"), (e.get("title") or "").strip()
            # "Topic A; Topic B; Topic C" titles are full-length shows, not clips.
            if not vid or vid in seen or SKIP_TITLE.search(title) or title.count(";") >= 2:
                continue
            ts = e.get("published_parsed")
            age_h = (now - time.mktime(ts) + time.timezone) / 3600 if ts else 99
            if age_h > MAX_AGE_H:
                continue
            desc = (e.get("summary") or "").strip()
            text = f"{title} {desc[:300]}"
            low = text.lower()
            relevance = bonus + sum(w for k, w in MARKET_WORDS.items() if re.search(r"\b" + re.escape(k) + r"\b", low))
            tickers = match_tickers(text)
            relevance += 2 * len(tickers)
            if relevance < 4:
                continue
            seen.add(vid)
            cands.append({"vid": vid, "title": title, "channel": name, "desc": desc[:400], "age_h": round(age_h, 1),
                          "published": datetime.fromtimestamp(time.mktime(ts) - time.timezone, tz=timezone.utc).isoformat() if ts else None,
                          "tickers": tickers, "topic": (match_topic(text) or {}).get("id"), "relevance": relevance})
    cands.sort(key=lambda c: c["relevance"] - c["age_h"] / 8, reverse=True)
    cands = cands[: limit * 2]
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = list(pool.map(lambda c: _meta(c["vid"]), cands))
    out = []
    for c, m in zip(cands, metas):
        if m["live"] or (m["seconds"] is not None and (m["seconds"] == 0 or m["seconds"] > MAX_SECONDS)):
            continue
        c.update(m)
        # Shorts and short clips rank higher, the TikTok-style format.
        c["score"] = round(c["relevance"] - c["age_h"] / 8 + (3 if m["shorts"] else 0)
                           + (1.5 if (m["seconds"] or 999) <= 300 else 0), 2)
        out.append(c)
    out.sort(key=lambda c: c["score"], reverse=True)
    known = sum(1 for c in out if c["seconds"] is not None)
    log.info("videos: %d kept from %d candidates (%d Shorts, %d with known length)", len(out[:limit]), len(cands),
             sum(1 for c in out[:limit] if c["shorts"]), known)
    return out[:limit]


def to_reels(videos):
    reels = []
    for v in videos:
        reels.append({
            "id": f"yt-{v['vid']}", "category": "video", "tag": v["channel"], "title": v["title"],
            "date": (v["published"] or "")[:10], "ts": v["published"], "priority": 5, "kind": "video",
            "video": {"id": v["vid"], "shorts": bool(v["shorts"]), "seconds": v["seconds"], "channel": v["channel"]},
            "ticker": v["tickers"][0] if v["tickers"] else None, "tickers": v["tickers"], "topic": v["topic"],
            "summary": v["desc"], "score": v["score"],
            "sources": [{"title": f"{v['channel']} on YouTube", "url": f"https://www.youtube.com/watch?v={v['vid']}"}],
        })
    return reels


def build():
    vids = fetch_videos()
    if not vids and OUT.exists():
        log.warning("no videos fetched; keeping the previous videos.json")
        return json.loads(OUT.read_text(encoding="utf-8"))
    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reels": to_reels(vids)}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    d = build()
    for r in d["reels"][:12]:
        v = r["video"]
        print(f"{r['score']:5}  {'SHORT' if v['shorts'] else '     '} {str(v['seconds']).rjust(4)}s  {v['channel'][:18].ljust(18)} {r['title'][:70]}")
