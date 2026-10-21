"""Phone alerts for big moves, sent through ntfy.sh (free push notifications, no account).

Two kinds, run by .github/workflows/alerts.yml every ~10 minutes in market hours:
  - Your PA stocks, at a lower threshold (default ±3%).
  - Big moves in big stocks: the large caps in config.WATCHLIST, at a higher threshold (default ±5%).
Settings come from the repo:
  NTFY_TOPIC     (secret)    your private ntfy topic; subscribe to it in the ntfy app
  PA_TICKERS     (variable)  e.g. "AAPL,NVDA,META"
  ALERT_PCT      (variable)  PA move that triggers an alert, default 3 (%)
  BIG_ALERT_PCT  (variable)  big-stock move that triggers an alert, default 5 (%); 0 turns these off
  APP_URL        (variable)  opened when you tap the notification
Each stock alerts once per step per day (3%, then 6%, ...), remembered in ALERT_STATE between runs.
Nothing about your stocks is printed, because Actions logs on a public repo are public.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import WATCHLIST  # noqa: E402
from quotes import fetch_live  # noqa: E402

ET = ZoneInfo("America/New_York")


def send(topic, title, body, up, click):
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST", headers={
        "Title": title, "Tags": "chart_with_upwards_trend" if up else "chart_with_downwards_trend",
        "Priority": "4", **({"Click": click} if click else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def _pct(name, default):
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return default


def main():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("alerts not configured: set the NTFY_TOPIC secret")
        return
    mine = sorted({t.strip().upper() for t in os.environ.get("PA_TICKERS", "").split(",") if t.strip()})
    pa_step, big_step = _pct("ALERT_PCT", 3), _pct("BIG_ALERT_PCT", 5)
    big = [s for s in WATCHLIST if s not in mine] if big_step > 0 else []
    if not mine and not big:
        print("nothing to watch: set PA_TICKERS or BIG_ALERT_PCT")
        return
    click = os.environ.get("APP_URL", "").strip()
    state_path = Path(os.environ.get("ALERT_STATE", ".alert-state/state.json"))
    today = datetime.now(ET).date().isoformat()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    if state.get("date") != today:
        state = {"date": today, "sent": {}}

    quotes = fetch_live(mine + big + ["^GSPC"])
    spx = quotes.get("^GSPC", {}).get("chg")
    sent = 0
    for group, symbols, step in (("pa", mine, pa_step), ("big", big, big_step)):
        for sym in symbols:
            q = quotes.get(sym)
            if not q or q.get("chg") is None or not q.get("time"):
                continue
            if datetime.fromtimestamp(q["time"], ET).date().isoformat() != today:
                continue  # yesterday's move (pre-market or a holiday): already old news
            level = int(abs(q["chg"]) // step)
            key = f"{sym}:{'up' if q['chg'] > 0 else 'down'}"
            if level < 1 or level <= state["sent"].get(key, 0):
                continue
            name = WATCHLIST.get(sym, (sym,))[0]
            title = f"{sym} {q['chg']:+.1f}% today" if group == "pa" else f"Big mover: {name} ({sym}) {q['chg']:+.1f}%"
            body = (f"{name if name != sym else sym} is at ${q['price']:,.2f}, {q['chg']:+.2f}% from yesterday's close of ${q['prev']:,.2f}."
                    + (f" S&P 500: {spx:+.2f}%." if spx is not None else ""))
            try:
                send(topic, title, body, q["chg"] > 0, click)
                state["sent"][key] = level
                sent += 1
            except Exception as e:
                print(f"ntfy send failed: {type(e).__name__}")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    print(f"checked {len(mine)} PA + {len(big)} large-cap stocks, sent {sent} alert(s)")


if __name__ == "__main__":
    main()
