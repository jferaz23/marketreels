"""Market-implied odds for each upcoming FOMC decision, from 30-day fed funds futures (CME ZQ contracts).

Same idea as CME FedWatch. A ZQ contract settles at 100 minus the month's average effective fed funds rate,
so a meeting month's price blends the rate before and after the decision. Anchoring on a neighboring month
with no meeting gives the rate on the other side, and the difference is the expected move. Expected moves are
split into 25 bp steps (e.g. +6 bp = 24% chance of +25, 76% hold) and chained meeting to meeting.
The app does the same math live in assets/app.js (fedOdds); keep the two in step.
"""
import calendar
from datetime import date

MONTH_CODES = "FGHJKMNQUVXZ"


def zq_symbol(y, m):
    return f"ZQ{MONTH_CODES[m - 1]}{str(y)[2:]}.CBT"


def zq_symbols(today, months=10):
    out, y, m = [], today.year, today.month
    for _ in range(months):
        out.append(zq_symbol(y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _shift(y, m, k):
    m0 = y * 12 + (m - 1) + k
    return m0 // 12, m0 % 12 + 1


def fed_odds(meetings, prices, target_high):
    """meetings: upcoming decision dates (ISO, sorted). prices: {zq symbol: price}. target_high: current top of range (%).

    Returns [{date, pre, post, change_bp, moves: {bp: prob}, dist: [(upper_bound_bp, prob)], hold, hike, cut}]."""
    meet_months = {(int(d[:4]), int(d[5:7])) for d in meetings}

    def avg(y, m):
        p = prices.get(zq_symbol(y, m))
        return 100 - p if p else None

    out, prev_post = [], None
    for d_iso in meetings:
        y, m, d = (int(x) for x in d_iso.split("-"))
        n = calendar.monthrange(y, m)[1]
        a = avg(y, m)
        if a is None:
            break
        nxt, prv = _shift(y, m, 1), _shift(y, m, -1)
        next_free = nxt not in meet_months and avg(*nxt) is not None
        prev_free = prv not in meet_months and avg(*prv) is not None
        after = n - d  # days at the new rate (it takes effect the day after the decision)
        if next_free and (after < 1 or prev_post is None or not prev_free):
            post = avg(*nxt)
            pre = (a * n - post * after) / d
        elif prev_free and after >= 1:
            pre = avg(*prv)
            post = (a * n - pre * d) / after
        elif prev_post is not None and after >= 1:
            pre = prev_post
            post = (a * n - pre * d) / after
        else:
            break
        out.append({"date": d_iso, "pre": round(pre, 4), "post": round(post, 4), "change_bp": round((post - pre) * 100, 1)})
        prev_post = post

    dist = {round(target_high * 100): 1.0}
    for o in out:
        steps = o["change_bp"] / 25
        k = int(steps // 1)
        p = steps - k
        moves = {25 * k: 1 - p, 25 * (k + 1): p}
        moves = {bp: pr for bp, pr in moves.items() if pr > 1e-6}
        new = {}
        for lvl, pr in dist.items():
            for bp, mp in moves.items():
                new[lvl + bp] = new.get(lvl + bp, 0) + pr * mp
        dist = new
        o["moves"] = {str(bp): round(pr, 4) for bp, pr in moves.items()}
        o["hold"] = round(moves.get(0, 0), 4)
        o["hike"] = round(sum(pr for bp, pr in moves.items() if bp > 0), 4)
        o["cut"] = round(sum(pr for bp, pr in moves.items() if bp < 0), 4)
        o["dist"] = [(lvl, round(pr, 4)) for lvl, pr in sorted(dist.items()) if pr >= 0.005]
    return out


def describe(o):
    """'Hold 83% · Hike 17%' for one meeting."""
    parts = [(o["hold"], "Hold"), (o["hike"], "Hike"), (o["cut"], "Cut")]
    return " · ".join(f"{label} {p * 100:.0f}%" for p, label in sorted(parts, reverse=True) if p >= 0.005)


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from quotes import fetch_live

    today = date.today()
    cal = json.loads((Path(__file__).resolve().parent.parent / "data" / "calendar.json").read_text(encoding="utf-8"))
    meetings = [m["date"] for m in cal["fomc_schedule"] if m["date"] >= today.isoformat()]
    q = fetch_live(zq_symbols(today))
    res = cal["fed"]["last"]["result"]
    for o in fed_odds(meetings, {s: v["price"] for s, v in q.items()}, res["high"]):
        top = max(o["dist"], key=lambda x: x[1])
        print(o["date"], f"{o['change_bp']:+.1f} bp", describe(o), f"| most likely top of range {top[0] / 100:.2f}% ({top[1] * 100:.0f}%)")
