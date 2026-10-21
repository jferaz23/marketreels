"""Market calendar: FOMC meetings + decisions, economic releases, big earnings, elections, holidays, opex.

Writes data/calendar.json (events) and data/curve.json (official Treasury yield curve). All free, no keys:
  - FOMC dates: federalreserve.gov calendar page; decisions parsed from each FOMC statement
  - Economic releases + earnings: Nasdaq's public calendar API (actual / consensus / previous)
  - Yield curve: US Treasury daily par yield curve CSV
  - Elections, NYSE holidays, options expiration: computed / listed below
If a source is down, events from the previous calendar.json are kept so the calendar never goes blank.
"""
import calendar as cal
import csv
import io
import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from config import WATCHLIST

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "calendar.json"
CURVE_OUT = ROOT / "data" / "curve.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
NASDAQ = {**UA, "Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}
FED = "https://www.federalreserve.gov"

# Elections and other dated events worth knowing. Add your own here.
FIXED_EVENTS = [
    {"date": "2026-11-03", "title": "US midterm elections", "category": "politics", "importance": 3,
     "note": "All 435 House seats and about a third of the Senate. Control of Congress shapes taxes, spending and regulation."},
    {"date": "2028-11-07", "title": "US presidential election", "category": "politics", "importance": 3},
]

# US economic releases worth tracking (Nasdaq event names, matched by prefix). 3 = market-moving, 2 = notable.
US_EVENTS = {
    3: ["Fed Interest Rate Decision", "FOMC Statement", "FOMC Press Conference", "Fed Chair", "Nonfarm Payrolls", "Unemployment Rate",
        "CPI", "Core CPI", "PCE Price Index", "Core PCE Price Index", "GDP", "Retail Sales", "PPI", "Core PPI"],
    2: ["FOMC Meeting Minutes", "Beige Book", "Initial Jobless Claims", "ISM Manufacturing PMI", "ISM Non-Manufacturing PMI", "ISM Services PMI",
        "JOLTs Job Openings", "JOLTS", "Michigan Consumer Sentiment", "Michigan Inflation Expectations", "CB Consumer Confidence",
        "Durable Goods Orders", "Core Durable Goods Orders", "Philadelphia Fed Manufacturing Index", "NY Empire State Manufacturing Index",
        "Existing Home Sales", "New Home Sales", "Building Permits", "Housing Starts", "Pending Home Sales", "ADP Nonfarm Employment Change",
        "Average Hourly Earnings", "Crude Oil Inventories", "10-Year Note Auction", "30-Year Bond Auction", "Trade Balance",
        "Industrial Production", "Personal Spending", "Personal Income", "Core Retail Sales", "S&P Global Manufacturing PMI",
        "S&P Global Services PMI", "Employment Cost Index"],
}
GLOBAL_EVENTS = {  # (country, name prefix) -> importance
    ("Euro Zone", "Deposit Facility Rate"): 3, ("Euro Zone", "ECB Interest Rate Decision"): 3, ("Euro Zone", "ECB Press Conference"): 2,
    ("Euro Zone", "CPI"): 2, ("Euro Zone", "GDP"): 2, ("Japan", "BoJ Interest Rate Decision"): 3, ("Japan", "Interest Rate Decision"): 3,
    ("United Kingdom", "BoE Interest Rate Decision"): 3, ("United Kingdom", "Interest Rate Decision"): 3, ("United Kingdom", "CPI"): 2,
    ("China", "GDP"): 2, ("China", "CPI"): 2, ("China", "Industrial Production"): 2, ("Canada", "BoC Interest Rate Decision"): 2,
}
CATEGORY_WORDS = [("fed", ["Fed", "FOMC", "Beige Book"]), ("inflation", ["CPI", "PCE", "PPI", "Inflation", "Price"]),
                  ("jobs", ["Payroll", "Unemployment", "Jobless", "JOLT", "Employment", "Hourly Earnings"]),
                  ("growth", ["GDP", "Retail", "ISM", "PMI", "Industrial", "Durable", "Personal", "Trade", "Philadelphia", "Empire"]),
                  ("consumer", ["Michigan", "Consumer Confidence"]), ("housing", ["Home", "Housing", "Building"]),
                  ("bonds", ["Auction"]), ("energy", ["Crude", "Oil"])]


def _get(url, headers=UA, timeout=25, tries=3):
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == tries - 1:
                raise
            log.info("retry %s (%s)", url[:70], e)
            time.sleep(3 * (attempt + 1))


def _clean(v):
    v = re.sub(r"&nbsp;|\s+", " ", str(v or "")).strip()
    return v or None


SKIP_EVENTS = re.compile(r"Index, n\.?s\.?a|Index, s\.?a|n\.s\.a|^(Core )?CPI Index|Pending Home Sales Index|GDPNow|Sales Index$")


def _category(name):
    if name.startswith("Fed") or "FOMC" in name or "Beige Book" in name:
        return "fed"
    for cat_id, words in CATEGORY_WORDS:
        if cat_id == "fed":
            continue
        if any(w.lower() in name.lower() for w in words):
            return cat_id
    return "data"


# ---------- FOMC ----------
def _frac(s):
    """'3-3/4' -> 3.75, '4' -> 4.0, '1/4' -> 0.25"""
    s = s.strip()
    m = re.match(r"(?:(\d+)-)?(\d+)/(\d+)$", s)
    if m:
        whole, num, den = m.groups()
        return int(whole or 0) + int(num) / int(den)
    return float(s) if re.match(r"\d+(\.\d+)?$", s) else None


def fomc_meetings():
    """[{start, end, statement_url, sep}] for every meeting on the Fed's calendar page."""
    html = _get(f"{FED}/monetarypolicy/fomccalendars.htm").text
    out = []
    for ym in re.finditer(r"(\d{4}) FOMC Meetings", html):
        year = int(ym.group(1))
        nxt = html.find("FOMC Meetings", ym.end())
        seg = html[ym.end(): nxt if nxt > 0 else len(html)]
        rows = re.split(r'class="[^"]*\bfomc-meeting\b[^_"]*"', seg)[1:]
        for row in rows:
            mon = re.search(r'fomc-meeting__month[^>]*>(.*?)</div>', row, re.S)
            day = re.search(r'fomc-meeting__date[^>]*>(.*?)</div>', row, re.S)
            if not mon or not day:
                continue
            month_txt = re.sub(r"<[^>]+>", "", mon.group(1)).strip()
            days_txt = re.sub(r"<[^>]+>", "", day.group(1)).strip()
            sep = "*" in days_txt
            nums = re.findall(r"\d+", days_txt)
            months = [m for m in re.split(r"[/\-]", month_txt) if m]
            if not nums or not months:
                continue
            try:
                m1 = list(cal.month_name).index(months[0].strip()) if len(months[0]) > 3 else list(cal.month_abbr).index(months[0][:3])
                m2 = (list(cal.month_name).index(months[-1].strip()) if len(months[-1]) > 3 else list(cal.month_abbr).index(months[-1][:3]))
            except ValueError:
                continue
            start = date(year, m1, int(nums[0]))
            end = date(year, m2 if len(months) > 1 else m1, int(nums[-1]))
            if end < start:
                end = date(year, m2, int(nums[-1]))
            link = re.search(r'href="(/newsevents/pressreleases/monetary\d{8}a\.htm)"', row)
            out.append({"start": start.isoformat(), "end": end.isoformat(), "sep": sep,
                        "statement_url": FED + link.group(1) if link else None})
    out.sort(key=lambda m: m["start"])
    log.info("fomc: %d meetings on the Fed calendar", len(out))
    return out


def _span(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    return f"{a:%b} {a.day}–{b.day}" if a.month == b.month else f"{a:%b} {a.day}–{b:%b} {b.day}"


def fomc_decision(url):
    """Parse an FOMC statement: action + target range."""
    raw = _get(url).content.decode("utf-8", "ignore").replace("–", "-").replace("‑", "-").replace("&#8211;", "-")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
    # "maintain the target range ... at 3-1/2 to 3-3/4 percent" or "lower the target range ... by 1/4 percentage point to 3-1/4 to 3-1/2 percent"
    rng = re.search(r"target range for the federal funds rate (?:by ([\d\-/]+) percentage points? )?(?:at|to) ([\d\-/]+) to ([\d\-/]+) percent", text)
    act = re.search(r"decided to (lower|raise|maintain|reduce|increase)", text)
    dissent = re.search(r"Voting against (?:the|this) action (?:was|were) ([^.]+)\.", text)
    if not rng:
        return None
    by, lo, hi = (_frac(rng.group(1)) if rng.group(1) else 0), _frac(rng.group(2)), _frac(rng.group(3))
    action = {"lower": "cut", "reduce": "cut", "raise": "hike", "increase": "hike", "maintain": "hold"}.get(act.group(1) if act else "", "hold")
    change = 0 if action == "hold" else round(by * 100) * (-1 if action == "cut" else 1)
    return {"action": action, "low": lo, "high": hi, "change_bp": change, "dissents": dissent.group(1).strip() if dissent else None}


def fomc_events(today):
    events, last = [], None
    meetings = fomc_meetings()
    for m in meetings:
        end = date.fromisoformat(m["end"])
        ev = {"date": m["end"], "time": "14:00", "title": "FOMC rate decision" + (" + projections" if m["sep"] else ""),
              "category": "fed", "importance": 3, "url": m["statement_url"] or f"{FED}/monetarypolicy/fomccalendars.htm",
              "note": f"Meeting {_span(m['start'], m['end'])}. Statement 2:00 pm ET, press conference 2:30 pm."
                      + (" Includes the dot plot (Summary of Economic Projections)." if m["sep"] else "")}
        if end <= today and m["statement_url"] and end.year >= today.year - 1:
            try:
                d = fomc_decision(m["statement_url"])
            except Exception as e:
                log.warning("statement %s failed: %s", m["statement_url"], e)
                d = None
            if d:
                rng = f"{d['low']:.2f}–{d['high']:.2f}%"
                ev["actual"] = (f"Held at {rng}" if d["action"] == "hold" else
                                f"{'Cut' if d['action'] == 'cut' else 'Raised'} {abs(d['change_bp'])} bp to {rng}")
                ev["result"] = d
                if d["dissents"]:
                    ev["note"] = f"Dissent: {d['dissents']}."
                last = {**ev}
        if end >= today - timedelta(days=200):
            events.append(ev)
    upcoming = next((e for e in events if e["date"] >= today.isoformat()), None)
    return events, {"last": last, "next": upcoming}


# ---------- Nasdaq economic + earnings calendars ----------
def _us_importance(name):
    for level, names in US_EVENTS.items():
        if any(name == n or name.startswith(n + " ") or name.startswith(n + "(") for n in names):
            return level
    return 0


def econ_events(start, end):
    merged = {}
    d = start
    while d <= end:
        if d.weekday() < 5:
            try:
                rows = (_get(f"https://api.nasdaq.com/api/calendar/economicevents?date={d.isoformat()}", NASDAQ).json().get("data") or {}).get("rows") or []
            except Exception as e:
                log.warning("nasdaq econ %s failed: %s", d, e)
                rows = []
            for r in rows:
                name, country = _clean(r.get("eventName")) or "", r.get("country")
                if country == "United States":
                    imp = _us_importance(name)
                else:
                    imp = next((v for (c, p), v in GLOBAL_EVENTS.items() if c == country and name.startswith(p)), 0)
                if imp < 2 or name.startswith(("Fed Interest Rate Decision", "FOMC Statement", "FOMC Press Conference")) or SKIP_EVENTS.search(name):  # FOMC comes from the Fed itself
                    continue
                key = (d.isoformat(), country, name)
                ev = merged.setdefault(key, {
                    "date": d.isoformat(), "time": _clean(r.get("gmt")), "title": name if country == "United States" else f"{country}: {name}",
                    "category": "global" if country != "United States" else _category(name), "importance": imp,
                    "actual": [], "consensus": [], "previous": [],
                })
                for k in ("actual", "consensus", "previous"):
                    v = _clean(r.get(k))
                    if v:
                        ev[k].append(v)
            time.sleep(0.4)
        d += timedelta(days=1)
    out = []
    for ev in merged.values():
        for k in ("actual", "consensus", "previous"):
            ev[k] = " · ".join(dict.fromkeys(ev[k])) or None
        out.append(ev)
    log.info("econ: %d events", len(out))
    return out


def _cap(s):
    try:
        return float(re.sub(r"[^\d.]", "", s or ""))
    except ValueError:
        return 0


def earnings_events(start, end, min_cap=20e9):
    out = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            try:
                rows = (_get(f"https://api.nasdaq.com/api/calendar/earnings?date={d.isoformat()}", NASDAQ).json().get("data") or {}).get("rows") or []
            except Exception as e:
                log.warning("nasdaq earnings %s failed: %s", d, e)
                rows = []
            for r in rows:
                sym = (r.get("symbol") or "").strip()
                cap = _cap(r.get("marketCap"))
                if not sym or (cap < min_cap and sym not in WATCHLIST):
                    continue
                when = {"time-pre-market": "pre", "time-after-hours": "post"}.get(r.get("time"))
                out.append({"date": d.isoformat(), "symbol": sym, "name": (_clean(r.get("name")) or sym).replace(", Inc.", "").replace(" Inc.", ""),
                            "when": when, "eps_est": _clean(r.get("epsForecast")), "eps_last_year": _clean(r.get("lastYearEPS")),
                            "cap": cap})
            time.sleep(0.4)
        d += timedelta(days=1)
    out.sort(key=lambda e: (e["date"], -e["cap"]))
    log.info("earnings: %d reports from large companies", len(out))
    return out


# ---------- computed market dates ----------
def _nth_weekday(y, m, weekday, n):
    d = date(y, m, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(y, m, weekday):
    d = date(y, m, cal.monthrange(y, m)[1])
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return date(y, month, ((h + l - 7 * m + 114) % 31) + 1)


def market_dates(start, end):
    out = []
    for y in range(start.year, end.year + 1):
        holidays = {
            "New Year's Day": _observed(date(y, 1, 1)), "Martin Luther King Jr. Day": _nth_weekday(y, 1, 0, 3),
            "Presidents' Day": _nth_weekday(y, 2, 0, 3), "Good Friday": _easter(y) - timedelta(days=2),
            "Memorial Day": _last_weekday(y, 5, 0), "Juneteenth": _observed(date(y, 6, 19)),
            "Independence Day": _observed(date(y, 7, 4)), "Labor Day": _nth_weekday(y, 9, 0, 1),
            "Thanksgiving": _nth_weekday(y, 11, 3, 4), "Christmas": _observed(date(y, 12, 25)),
        }
        for name, d in holidays.items():
            out.append({"date": d.isoformat(), "title": f"Market holiday: {name} (NYSE & Nasdaq closed)", "category": "market", "importance": 2})
        out.append({"date": (holidays["Thanksgiving"] + timedelta(days=1)).isoformat(), "title": "Early close: 1:00 pm ET (day after Thanksgiving)", "category": "market", "importance": 1})
        if date(y, 12, 24).weekday() < 5 and date(y, 12, 24) != holidays["Christmas"]:
            out.append({"date": f"{y}-12-24", "title": "Early close: 1:00 pm ET (Christmas Eve)", "category": "market", "importance": 1})
        for m in range(1, 13):
            d = _nth_weekday(y, m, 4, 3)
            quad = m in (3, 6, 9, 12)
            out.append({"date": d.isoformat(), "title": "Quad witching: quarterly options & futures expiration" if quad else "Monthly options expiration",
                        "category": "market", "importance": 2 if quad else 1,
                        "note": "Big expirations can mean heavy volume and choppy moves into the close." if quad else None})
    return [e for e in out if start.isoformat() <= e["date"] <= end.isoformat()]


# ---------- Treasury curve ----------
def treasury_curve(today):
    url = (f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{today.year}/all"
           f"?type=daily_treasury_yield_curve&field_tdr_date_value={today.year}&page&_format=csv")
    rows = list(csv.DictReader(io.StringIO(_get(url).text)))
    if not rows:
        return None
    keep = ["1 Mo", "3 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]

    def pts(r):
        return {k.replace(" Mo", "M").replace(" Yr", "Y"): float(r[k]) for k in keep if r.get(k) not in (None, "", "N/A")}

    latest, week, month = rows[0], rows[min(5, len(rows) - 1)], rows[min(21, len(rows) - 1)]
    fmt = lambda s: datetime.strptime(s, "%m/%d/%Y").date().isoformat()
    return {"date": fmt(latest["Date"]), "points": pts(latest),
            "week_ago": {"date": fmt(week["Date"]), "points": pts(week)},
            "month_ago": {"date": fmt(month["Date"]), "points": pts(month)}}


def effr():
    r = _get("https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json").json()["refRates"][0]
    return {"date": r["effectiveDate"], "rate": r["percentRate"], "low": r.get("targetRateFrom"), "high": r.get("targetRateTo")}


def build(today):
    """Fetch everything; keep previous data for any source that fails. Returns the calendar dict."""
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    prev_events = prev.get("events", [])
    lo, hi = today - timedelta(days=10), today + timedelta(days=21)

    try:
        fomc, fed = fomc_events(today)
    except Exception as e:
        log.warning("FOMC calendar unavailable: %s", e)
        fomc, fed = [e for e in prev_events if e.get("category") == "fed" and e.get("title", "").startswith("FOMC")], prev.get("fed", {})
    econ = econ_events(today - timedelta(days=7), today + timedelta(days=14))
    if not econ:
        econ = [e for e in prev_events if e.get("source") == "econ"]
    for e in econ:
        e["source"] = "econ"
    earnings = earnings_events(today - timedelta(days=3), today + timedelta(days=14))
    if not earnings:
        earnings = prev.get("earnings", [])

    try:
        fed = {**fed, "effr": effr()}
    except Exception as e:
        log.warning("EFFR unavailable: %s", e)
        if prev.get("fed", {}).get("effr"):
            fed = {**fed, "effr": prev["fed"]["effr"]}
    events = [e for e in fomc if lo.isoformat() <= e["date"] <= (today + timedelta(days=120)).isoformat()]
    events += econ + market_dates(lo, today + timedelta(days=60))
    events += [{**e} for e in FIXED_EVENTS if lo.isoformat() <= e["date"] <= (today + timedelta(days=400)).isoformat()]
    events.sort(key=lambda e: (e["date"], e.get("time") or "99", -e.get("importance", 0)))

    cal_out = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "fed": fed,
               "fomc_schedule": [{"date": e["date"], "sep": "projections" in e["title"], "actual": e.get("actual")} for e in fomc],
               "events": events, "earnings": earnings}
    OUT.write_text(json.dumps(cal_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    try:
        curve = treasury_curve(today)
        if curve:
            CURVE_OUT.write_text(json.dumps(curve, separators=(",", ":")), encoding="utf-8")
            log.info("curve: %s 2Y %.2f 10Y %.2f", curve["date"], curve["points"].get("2Y", 0), curve["points"].get("10Y", 0))
    except Exception as e:
        log.warning("Treasury curve unavailable: %s", e)
    log.info("calendar: %d events, %d earnings, next FOMC %s", len(events), len(earnings), (fed.get("next") or {}).get("date"))
    return cal_out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build(date.today())
