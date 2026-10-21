"""Phone alerts for big moves in your PA stocks, sent through ntfy.sh (free push notifications, no account).

Run by .github/workflows/alerts.yml every ~10 minutes in market hours. Settings come from the repo:
  NTFY_TOPIC  (secret)    your private ntfy topic; subscribe to it in the ntfy app
  PA_TICKERS  (variable)  e.g. "AAPL,NVDA,META"
  ALERT_PCT   (variable)  move size that triggers an alert, default 3 (%)
  APP_URL     (variable)  opened when you tap the notification
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

from quotes import fetch_live  # noqa: E402

ET = ZoneInfo("America/New_York")


def send(topic, title, body, up, click):
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST", headers={
        "Title": title, "Tags": "chart_with_upwards_trend" if up else "chart_with_downwards_trend",
        "Priority": "4", **({"Click": click} if click else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def main():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    tickers = sorted({t.strip().upper() for t in os.environ.get("PA_TICKERS", "").split(",") if t.strip()})
    if not topic or not tickers:
        print("alerts not configured: set the NTFY_TOPIC secret and PA_TICKERS variable")
        return
    step = float(os.environ.get("ALERT_PCT") or 3)
    click = os.environ.get("APP_URL", "").strip()
    state_path = Path(os.environ.get("ALERT_STATE", ".alert-state/state.json"))
    today = datetime.now(ET).date().isoformat()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    if state.get("date") != today:
        state = {"date": today, "sent": {}}

    quotes = fetch_live(tickers + ["^GSPC"])
    spx = quotes.get("^GSPC", {}).get("chg")
    sent = 0
    for sym in tickers:
        q = quotes.get(sym)
        if not q or q.get("chg") is None or not q.get("time"):
            continue
        if datetime.fromtimestamp(q["time"], ET).date().isoformat() != today:
            continue  # yesterday's move (pre-market or a holiday): already old news
        level = int(abs(q["chg"]) // step)
        key = f"{sym}:{'up' if q['chg'] > 0 else 'down'}"
        if level < 1 or level <= state["sent"].get(key, 0):
            continue
        body = (f"{sym} is at ${q['price']:,.2f}, {q['chg']:+.2f}% from yesterday's close of ${q['prev']:,.2f}."
                + (f" S&P 500: {spx:+.2f}%." if spx is not None else ""))
        try:
            send(topic, f"{sym} {q['chg']:+.1f}% today", body, q["chg"] > 0, click)
            state["sent"][key] = level
            sent += 1
        except Exception as e:
            print(f"ntfy send failed: {type(e).__name__}")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    print(f"checked {len(tickers)} stocks, sent {sent} alert(s)")


if __name__ == "__main__":
    main()
