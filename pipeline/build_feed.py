"""Builds data/feed.json (today's reels), data/quotes.json (latest prices), data/calendar.json (Fed, economic
releases, earnings, elections) and data/curve.json (Treasury yield curve) from free data only. No paid APIs.

    python pipeline/build_feed.py              # auto-detects pre-market / midday / close from US Eastern time
    python pipeline/build_feed.py --slot close # force a slot

Optional environment variable: PEXELS_API_KEY (free key, video backgrounds).
"""
import argparse
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calendar_events  # noqa: E402
from fed_odds import fed_odds  # noqa: E402
from config import ASSETS, INDICES, VOLATILITY, WATCHLIST  # noqa: E402
from macro import fetch_macro  # noqa: E402
from market import fetch_fundamentals, fetch_quotes  # noqa: E402
from media import Media  # noqa: E402
from news import fetch_news  # noqa: E402
from quotes import fetch_live, write as write_quotes  # noqa: E402
from reels import live_tag  # noqa: E402
from reels import ReelWriter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "data" / "feed.json"
LESSONS = ROOT / "data" / "lessons.json"
KEEP_DAYS = 4
MAX_REELS = 90
ET = ZoneInfo("America/New_York")

log = logging.getLogger("build_feed")


def detect_slot(now):
    if now.weekday() >= 5:
        return "weekend"
    minutes = now.hour * 60 + now.minute
    if minutes < 9 * 60 + 30:
        return "premarket"
    if minutes < 16 * 60:
        return "midday"
    return "close"


def pick_spotlights(quotes, today, n):
    """Today's biggest mover plus a daily rotation through the watchlist, so every name gets a turn."""
    syms = [s for s in WATCHLIST if s in quotes and quotes[s]["chg1d"] is not None]
    movers = sorted(syms, key=lambda s: abs(quotes[s]["chg1d"]), reverse=True)
    day = today.toordinal()
    rotation = [syms[(day * 7 + k * 11) % len(syms)] for k in range(n)]
    out = []
    for s in [movers[0]] + rotation + movers[1:]:
        if s not in out:
            out.append(s)
    return out[:n]


def tape(quotes):
    order = list(INDICES) + list(VOLATILITY) + ["^TNX"] + list(ASSETS) + ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]
    out = []
    for s in order:
        q = quotes.get(s)
        if not q:
            continue
        if s == "^TNX":
            out.append({"label": "10Y", "value": f"{q['last']:.2f}%", "change": round(q["chg1d"] or 0, 2), **live_tag(s)})
        else:
            v = q["last"]
            out.append({"label": s.lstrip("^") if s in WATCHLIST else q["name"], "value": f"{v:,.2f}" if v < 1000 else f"{v:,.0f}",
                        "change": round(q["chg1d"] or 0, 2), **live_tag(s)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=["premarket", "midday", "close", "weekend"])
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    now = datetime.now(ET)
    today = now.date()
    slot = args.slot or detect_slot(now)
    log.info("building %s feed for %s", slot, today)

    live_quotes = fetch_live()
    quotes = fetch_quotes(live_quotes)
    if live_quotes:
        write_quotes(live_quotes)
    news = fetch_news()
    macro = fetch_macro()
    lesson_titles = {}
    if LESSONS.exists():
        lesson_titles = {r["id"]: r["title"] for r in json.loads(LESSONS.read_text(encoding="utf-8"))["reels"]}

    try:
        calendar = calendar_events.build(today)
    except Exception as e:  # the calendar is a bonus; never lose the feed over it
        log.warning("calendar failed: %s", e)
        calendar = json.loads(calendar_events.OUT.read_text(encoding="utf-8")) if calendar_events.OUT.exists() else {}
    curve = json.loads(calendar_events.CURVE_OUT.read_text(encoding="utf-8")) if calendar_events.CURVE_OUT.exists() else {}

    odds = []
    try:
        upcoming = [m["date"] for m in calendar.get("fomc_schedule", []) if m["date"] >= today.isoformat()]
        top = ((calendar.get("fed") or {}).get("last") or {}).get("result", {}).get("high")
        if upcoming and top:
            odds = fed_odds(upcoming, {s: v["price"] for s, v in live_quotes.items() if s.startswith("ZQ")}, top)
    except Exception as e:
        log.warning("fed odds failed: %s", e)

    ctx = {"date": today.isoformat(), "slot": slot, "ts": now.isoformat(timespec="seconds"), "quotes": quotes,
           "news": news, "macro": macro, "lesson_titles": lesson_titles, "calendar": calendar, "curve": curve, "fed_odds": odds}

    spot_syms = pick_spotlights(quotes, today, 2)
    fundamentals = {}
    for s in spot_syms:
        try:
            fundamentals[s] = fetch_fundamentals(s)
        except Exception as e:  # one bad ticker shouldn't sink the run
            log.warning("fundamentals failed for %s: %s", s, e)

    w = ReelWriter(ctx)
    if slot == "premarket":
        w.premarket()
        w.headlines()
        w.world()
    else:
        w.recap()
        w.movers()
        w.headlines()
        w.rates()
        w.commodities()
        w.world()
    w.economy()
    w.fed_watch()
    if slot == "weekend" or (today.weekday() == 0 and slot == "premarket"):
        w.week_ahead()
    if slot == "weekend" or today.weekday() == 4:
        w.week_review()
    w.news_stories(n=6)
    spots = [s for s in spot_syms if s in fundamentals]
    for i, s in enumerate(spots):
        reason = (f"It moved {quotes[s]['chg1d']:+.1f}% {'today' if slot != 'premarket' else 'in the last session'}, one of the biggest moves among large caps."
                  if i == 0 and s == spot_syms[0] else "Today's pick from our rotation of large US companies.")
        w.spotlight(fundamentals[s], quotes[s], reason, 4 + i)

    fresh = w.out
    Media().decorate(fresh)
    for r in fresh:
        r.pop("media_query", None)

    # Keep recent reels from earlier runs so the feed has depth.
    old = []
    if FEED.exists():
        try:
            old = json.loads(FEED.read_text(encoding="utf-8")).get("reels", [])
        except json.JSONDecodeError:
            log.warning("existing feed.json unreadable; starting fresh")
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    # A later edition of the same reel on the same day (e.g. the close recap after the midday one) replaces it.
    edition = lambda rid: re.sub(r"^(\d{4}-\d{2}-\d{2})-(premarket|midday|close|weekend)-", r"\1-", rid)
    fresh_keys = {edition(r["id"]) for r in fresh}
    keep = [r for r in old if r.get("date", "") >= cutoff and edition(r["id"]) not in fresh_keys and not r.get("sample")]
    reels = fresh + keep
    reels.sort(key=lambda r: (r.get("ts", ""), -r.get("priority", 50)), reverse=True)
    seen_editions = set()
    reels = [r for r in reels if not (edition(r["id"]) in seen_editions or seen_editions.add(edition(r["id"])))]  # newest copy wins
    reels = reels[:MAX_REELS]

    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps({
        "generated_at": now.isoformat(timespec="seconds"),
        "slot": slot,
        "tape": tape(quotes),
        "reels": reels,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("wrote %d reels (%d new) to %s", len(reels), len(fresh), FEED)


if __name__ == "__main__":
    main()
