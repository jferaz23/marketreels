"""Turns market data, news and macro readings into reels. Works with no AI and no API keys.

Every reel is a dict the app renders directly; see README for the scene schema.
"""
import hashlib
import re
from datetime import date, timedelta

from config import CYCLICAL, DEFENSIVE, FUTURES, GLOBAL, INDICES, SECTORS, TOPICS, WATCHLIST, YIELDS

TOPIC_TAGS = {"fed": "Fed Watch", "inflation": "Inflation", "jobs": "Jobs", "growth": "Economy", "trade": "Trade",
              "oil": "Energy", "bonds": "Bonds", "earnings": "Earnings", "china": "Global", "ai": "Tech & AI",
              "crypto": "Crypto", "dollar": "Currencies"}
TOPIC_ART = {"fed": "fed", "inflation": "basket", "jobs": "jobs", "growth": "factory", "trade": "ship", "oil": "oil",
             "bonds": "bonds", "earnings": "chart", "china": "globe", "ai": "chip", "crypto": "coins", "dollar": "coins"}


# ---------- formatting ----------
def signed(c, d=1):
    if c is None:
        return "—"
    return f"{0:.{d}f}%" if round(c, d) == 0 else f"{c:+.{d}f}%"


def tone(c, text):
    if c is None or round(c, 1) == 0:
        return text
    return f"[up]{text}[/up]" if c > 0 else f"[down]{text}[/down]"


def nice_date(iso):
    try:
        d = __import__("datetime").date.fromisoformat(str(iso)[:10])
        return f"{d:%a, %b} {d.day}"
    except ValueError:
        return str(iso)


def money(v, d=2):
    return "—" if v is None else f"${v:,.{d}f}"


def big_money(v):
    if v is None:
        return "—"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(v) >= div:
            return f"${v / div:.1f}{unit}"
    return f"${v:,.0f}"


SECTOR_RISKS = {
    "Technology": "Tech moves fast: competitors, new platforms or a slowdown in corporate IT spending can erode growth",
    "Healthcare": "Drug-pricing rules, trial failures and patent expirations can hit healthcare profits quickly",
    "Financial Services": "Banks and lenders suffer when the economy slows and borrowers default",
    "Energy": "Profits swing with oil and gas prices, which the company can't control",
    "Consumer Cyclical": "Discretionary spending is the first thing consumers cut in a downturn",
    "Consumer Defensive": "Steady, but slow: limited growth can mean the stock lags in strong markets",
    "Communication Services": "Advertising budgets shrink in slowdowns, and regulators are watching big platforms",
    "Industrials": "Orders tend to dry up when the economic cycle turns",
    "Utilities": "Heavy borrowers whose stocks often fall when interest rates rise",
    "Real Estate": "Higher interest rates raise borrowing costs and pressure property values",
    "Basic Materials": "Commodity prices and global demand drive results",
}


def level(sym, v):
    if v is None:
        return "—"
    if sym in WATCHLIST:
        return f"${v:,.2f}"
    if sym in YIELDS:
        return f"{v:.2f}%"
    if sym in ("BTC-USD", "GC=F") or v >= 1000:
        return f"{v:,.0f}" if sym not in ("BTC-USD", "GC=F") else f"${v:,.0f}"
    if sym == "CL=F":
        return f"${v:.2f}"
    return f"{v:,.2f}"


def live_tag(sym):
    """Marks a number the app can refresh with live quotes: symbol + how to format it."""
    kind = ("yield" if sym in YIELDS else "usd" if sym in WATCHLIST or sym == "CL=F" else
            "usd0" if sym in ("BTC-USD", "GC=F") else "num")
    return {"sym": sym, "fmt": kind}


def bp(q):
    return (q["last"] - q["prev"]) * 100


def move_verb(c, live=False):
    if c is None:
        return "is flat"
    a = abs(c)
    if live:
        return f"is {'up' if c > 0 else 'down'} {a:.1f}%" if a >= 0.05 else "is flat"
    if a < 0.05:
        return "ends flat"
    if c > 0:
        return f"{'surges' if a >= 1.5 else 'jumps' if a >= 0.8 else 'rises' if a >= 0.3 else 'edges up'} {a:.1f}%"
    return f"{'tumbles' if a >= 1.5 else 'drops' if a >= 0.8 else 'slips' if a >= 0.3 else 'dips'} {a:.1f}%"


def clock(t):
    """'08:30' -> '8:30a', '14:00' -> '2:00p'"""
    try:
        h, m = (int(x) for x in str(t).split(":")[:2])
    except (TypeError, ValueError):
        return None
    return f"{h % 12 or 12}:{m:02d}{'a' if h < 12 else 'p'}"


def stable_choice(seed, items):
    return items[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(items)]


def shuffled_quiz(seed, correct, wrong):
    opts = [correct] + [w for w in wrong if w != correct][:3]
    opts.sort(key=lambda o: hashlib.md5((seed + o).encode()).hexdigest())
    return opts, opts.index(correct)


def chart_scene(q, headline, note=None, label=None, long=False):
    pts = q["series6m"] if long else q["series"]
    dates = q["dates6m"] if long else q["dates"]
    chg = (pts[-1] / pts[0] - 1) * 100 if pts and pts[0] else None
    # Downsample so the SVG path stays small.
    step = max(1, len(pts) // 64)
    return {"kind": "chart", "headline": headline, "label": label or f"{q['name']} · {'6 months' if long else '3 months'}",
            **live_tag(q["symbol"]), "first": round(pts[0], 4),
            "last": level(q["symbol"], q["last"]), "change": round(chg, 2) if chg is not None else None,
            "points": [round(p, 2) for p in pts[::step]] + ([round(pts[-1], 2)] if (len(pts) - 1) % step else []),
            "dates": [dates[0], dates[-1]], "note": note}


def first_sentences(text, n=2, max_len=260):
    parts = re.split(r"(?<=[.!?])\s+", text or "")
    out = ""
    for p in parts[:n]:
        if len(out) + len(p) > max_len and out:
            break
        out = (out + " " + p).strip()
    return out[:max_len].rstrip() + ("…" if len(out) > max_len else "")


class ReelWriter:
    def __init__(self, ctx):
        self.ctx = ctx
        self.q = ctx["quotes"]
        self.date = ctx["date"]
        self.slot = ctx["slot"]
        self.ts = ctx["ts"]
        self.lessons = ctx.get("lesson_titles", {})
        self.out = []

    def add(self, key, category, tag, title, scenes, priority, **kw):
        scenes = [s for s in scenes if s]
        if len(scenes) < 2:
            return None
        r = {"id": f"{self.date}-{self.slot}-{key}", "category": category, "tag": tag, "title": title,
             "date": self.date, "ts": self.ts, "priority": priority, "scenes": scenes}
        r.update({k: v for k, v in kw.items() if v is not None})
        self.out.append(r)
        return r

    def session_label(self):
        asof = self.q.get("^GSPC", {}).get("asof")
        live = self.slot == "midday" and asof == self.date
        if live:
            return "so far today", True
        return ("today" if asof == self.date else "in the last session"), False

    # ---------- market recap ----------
    def recap(self):
        sp = self.q.get("^GSPC")
        if not sp:
            return
        when, live = self.session_label()
        idx = [self.q[s] for s in INDICES if s in self.q]
        others = ", ".join(f"the {i['name']} {tone(i['chg1d'], signed(i['chg1d']))}" for i in idx[1:])
        sectors = sorted((self.q[s] for s in SECTORS if s in self.q), key=lambda x: x["chg1d"] or 0, reverse=True)
        from_high = (sp["last"] / sp["hi3m"] - 1) * 100
        trend = ("sitting right at its 3-month high" if from_high > -0.3 else
                 f"{abs(from_high):.1f}% below its 3-month high")
        scenes = [
            {"kind": "title", "eyebrow": "Midday check-in" if live else "Market close",
             "headline": f"S&P 500 {move_verb(sp['chg1d'], live)}",
             "body": f"Here's how the market moved {when}: {others}."},
            {"kind": "stats", "headline": "The scoreboard",
             "items": [{"label": i["name"], "value": level(i["symbol"], i["last"]), "change": i["chg1d"], **live_tag(i["symbol"])} for i in idx]},
            chart_scene(sp, "The bigger picture", f"Zooming out, the S&P 500 is {tone(sp['chg3m'], signed(sp['chg3m']))} over three months, {trend}."),
        ]
        if sectors:
            scenes.append({"kind": "bars", "headline": "Where the money moved",
                           "items": [{"label": SECTORS[s["symbol"]], "value": round(s["chg1d"] or 0, 2)} for s in sectors]})
            best, worst = sectors[0], sectors[-1]
            cyc = [self.q[s]["chg1d"] or 0 for s in CYCLICAL if s in self.q]
            dfn = [self.q[s]["chg1d"] or 0 for s in DEFENSIVE if s in self.q]
            gap = (sum(cyc) / len(cyc)) - (sum(dfn) / len(dfn)) if cyc and dfn else 0
            up_day = (sp["chg1d"] or 0) >= 0
            if gap > 0.25:
                mood = ("**Risk-on**: economically sensitive sectors like tech and financials beat defensive ones, a sign investors felt confident."
                        if up_day else "Cyclical sectors fell **less** than defensive ones, so investors weren't running for safety despite the dip.")
            elif gap < -0.25:
                mood = ("**Risk-off**: defensive sectors like utilities, staples and healthcare held up best, a sign investors were cautious."
                        if not up_day else "A **defensive tilt**: the market rose, but steadier sectors like healthcare and utilities led the way. Investors bought, but cautiously.")
            else:
                mood = "No clear risk-on or risk-off tilt: cyclical and defensive sectors moved about the same."
            scenes.append({"kind": "text", "headline": f"{SECTORS[best['symbol']]} led, {SECTORS[worst['symbol']]} lagged",
                           "body": f"{SECTORS[best['symbol']]} {tone(best['chg1d'], signed(best['chg1d']))} vs. {SECTORS[worst['symbol']]} {tone(worst['chg1d'], signed(worst['chg1d']))}.\n\n{mood}"})
            opts, ans = shuffled_quiz(self.date + "sector", SECTORS[best["symbol"]],
                                      [SECTORS[s["symbol"]] for s in sectors[1:]][::3])
            scenes.append({"kind": "quiz", "question": f"Pop quiz: which sector led the market {when}?", "options": opts,
                           "answer": ans, "explain": f"{SECTORS[best['symbol']]} gained {signed(best['chg1d'])}, the best of all 11 S&P sectors."})
        results = self.today_calendar_scene(results=True) if self.slot in ("close", "midday") else None
        if results:
            scenes.insert(min(4, len(scenes)), results)
        cross = [s for s in ("^TNX", "^VIX", "CL=F", "DX-Y.NYB", "GC=F", "BTC-USD") if s in self.q]
        if cross:
            items = []
            for s in cross:
                qq = self.q[s]
                if s == "^TNX":
                    items.append({"label": "10-yr yield", "value": level(s, qq["last"]), "note": f"{bp(qq):+.0f} bp", **live_tag(s)})
                else:
                    items.append({"label": qq["name"], "value": level(s, qq["last"]), "change": qq["chg1d"], **live_tag(s)})
            scenes.insert(3, {"kind": "stats", "headline": "Beyond stocks", "items": items})
        self.add("recap", "markets", "Midday" if live else "Market Close",
                 f"S&P 500 {move_verb(sp['chg1d'], live)} {when}", scenes, 1, art="chart",
                 media_query="stock market trading screen",
                 summary="A data-driven recap of US indices, sectors and cross-asset moves.",
                 sources=[{"title": "Yahoo Finance: S&P 500", "url": "https://finance.yahoo.com/quote/%5EGSPC/"}])

    def premarket(self):
        fut = [self.q[s] for s in FUTURES if s in self.q]
        if not fut:
            return
        es = fut[0]
        news = self.ctx["news"][:3]
        scenes = [
            {"kind": "title", "eyebrow": "Before the bell",
             "headline": f"Futures point {'higher' if (es['chg1d'] or 0) > 0.1 else 'lower' if (es['chg1d'] or 0) < -0.1 else 'to a flat open'}",
             "body": "Stock futures trade nearly around the clock, so they hint at how the market may open at 9:30 a.m. ET."},
            {"kind": "stats", "headline": "Futures right now",
             "items": [{"label": f["name"], "value": level(f["symbol"], f["last"]), "change": f["chg1d"], **live_tag(f["symbol"])} for f in fut]
             + ([{"label": "10-yr yield", "value": level("^TNX", self.q["^TNX"]["last"]), "note": f"{bp(self.q['^TNX']):+.0f} bp", **live_tag("^TNX")}] if "^TNX" in self.q else [])},
            {"kind": "bullets", "headline": "On traders' radar", "items": [n["title"] for n in news]} if news else None,
            self.today_calendar_scene(),
            {"kind": "text", "headline": "How to read futures", "basic": True,
             "body": "Futures are contracts on where an index will trade later. A move of a few tenths of a percent overnight is normal; moves above **1%** usually mean big news broke."},
        ]
        self.add("premarket", "markets", "Pre-Market", scenes[0]["headline"], scenes, 1, art="bell",
                 media_query="new york city morning",
                 sources=[{"title": n["title"], "url": n["url"]} for n in news])

    def week_review(self):
        idx = [self.q[s] for s in INDICES if s in self.q]
        sectors = sorted((self.q[s] for s in SECTORS if s in self.q), key=lambda x: x["chg5d"] or 0, reverse=True)
        if not idx or not sectors:
            return
        sp = self.q["^GSPC"]
        scenes = [
            {"kind": "title", "eyebrow": "Week in review", "headline": f"The S&P 500 {'gained' if (sp['chg5d'] or 0) >= 0 else 'lost'} {abs(sp['chg5d'] or 0):.1f}% this week",
             "body": "Five trading days, 60 seconds. Here's the recap."},
            {"kind": "bars", "headline": "The week by index", "items": [{"label": i["name"], "value": round(i["chg5d"] or 0, 2)} for i in idx]},
            {"kind": "bars", "headline": "The week by sector", "items": [{"label": SECTORS[s["symbol"]], "value": round(s["chg5d"] or 0, 2)} for s in sectors]},
            {"kind": "text", "headline": "Zoom out", "body": f"Over the past month the S&P 500 is {tone(sp['chg1m'], signed(sp['chg1m']))}. Weekly swings feel big, but long-term investors focus on the trend."},
        ]
        self.add("week", "markets", "Week in Review", scenes[0]["headline"], scenes, 2, art="calendar")

    # ---------- movers ----------
    def movers(self):
        stocks = [self.q[s] for s in WATCHLIST if s in self.q and self.q[s]["chg1d"] is not None]
        if len(stocks) < 8:
            return
        stocks.sort(key=lambda x: x["chg1d"], reverse=True)
        gainers, losers = stocks[:4], stocks[-4:]
        top = sorted(stocks, key=lambda x: abs(x["chg1d"]), reverse=True)[:2]
        when, live = self.session_label()
        scenes = [
            {"kind": "title", "eyebrow": "Biggest movers",
             "headline": f"{WATCHLIST[top[0]['symbol']][0]} {'soars' if top[0]['chg1d'] > 0 else 'sinks'} {abs(top[0]['chg1d']):.1f}%",
             "body": f"The biggest moves among {len(stocks)} of America's largest companies {when}."},
            {"kind": "bars", "headline": "Top gainers & losers",
             "items": [{"label": s["symbol"], "value": round(s["chg1d"], 2)} for s in gainers + losers]},
        ]
        for s in top:
            sym = s["symbol"]
            story = next((n for n in self.ctx["news"] if sym in n["tickers"]), None)
            body = (f"Likely catalyst in the headlines: **{story['title']}**" if story else
                    "No single headline explains it. Moves like this often come from analyst rating changes, sector news or big funds repositioning.")
            scenes.append(chart_scene(s, f"{WATCHLIST[sym][0]} ({sym}) {tone(s['chg1d'], signed(s['chg1d']))}", body))
        opts, ans = shuffled_quiz(self.date + "mover", top[0]["symbol"], [x["symbol"] for x in stocks[4:-4:6]])
        scenes.append({"kind": "quiz", "question": f"Which of these stocks moved the most {when}?", "options": opts, "answer": ans,
                       "explain": f"{WATCHLIST[top[0]['symbol']][0]} moved {signed(top[0]['chg1d'])}. Single stocks swing far more than the index, which is one reason diversification matters."})
        sources = [{"title": n["title"], "url": n["url"]} for n in self.ctx["news"] if set(n["tickers"]) & {t["symbol"] for t in top}][:3]
        self.add("movers", "markets", "Movers", scenes[0]["headline"], scenes, 2, art="rocket", ticker=top[0]["symbol"],
                 media_query="stock market chart screen", sources=sources or None)

    # ---------- macro ----------
    def rates(self):
        ys = [self.q[s] for s in YIELDS if s in self.q]
        if "^TNX" not in self.q or len(ys) < 3:
            return
        ten = self.q["^TNX"]
        short = self.q.get("^IRX")
        spread = (ten["last"] - short["last"]) if short else None
        inverted = spread is not None and spread < 0
        m_bp = (ten["last"] - ten["series"][-22]) * 100 if len(ten["series"]) > 22 else None
        scenes = [
            {"kind": "title", "eyebrow": "Rates watch", "headline": f"10-year Treasury yield: {ten['last']:.2f}%",
             "body": f"That's {bp(ten):+.0f} basis points on the day" + (f" and {m_bp:+.0f} bp over the past month." if m_bp is not None else ".") + " (100 bp = 1 percentage point.)"},
            {"kind": "bars", "headline": "Today's yield curve", "mode": "positive",
             "items": [{"label": y["name"], "value": round(y["last"], 2), "display": f"{y['last']:.2f}%"} for y in ys],
             "body": ("The curve is **inverted**: short-term rates are above long-term ones." if inverted else
                      "The curve slopes **upward**: longer loans pay more, which is the normal shape.") +
                     (f" The 10-year minus 3-month spread is {spread:+.2f} points." if spread is not None else "")},
            self.curve_scene(),
            chart_scene(ten, "The 10-year's path", "Rising yields raise borrowing costs for mortgages and companies, and make bonds more competitive with stocks."),
            {"kind": "quiz", "question": "Based on today's numbers, is the yield curve (10-year minus 3-month) inverted?",
             "options": ["Yes, it's inverted", "No, it's upward sloping"], "answer": 0 if inverted else 1,
             "explain": f"The 10-year is at {ten['last']:.2f}% vs. {short['last']:.2f}% for 3-month bills." if short else ""},
        ]
        if not short:
            scenes.pop()
        self.add("rates", "macro", "Rates", f"10-year yield at {ten['last']:.2f}% ({bp(ten):+.0f} bp)", scenes, 6, art="bonds",
                 media_query="bank building columns",
                 sources=[{"title": "US Treasury: daily yield curve rates", "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"}],
                 related=self.lessons.get("learn-yield-curve"))

    def commodities(self):
        syms = [s for s in ("CL=F", "GC=F", "DX-Y.NYB", "BTC-USD") if s in self.q]
        if len(syms) < 3:
            return
        biggest = max((self.q[s] for s in syms), key=lambda x: abs(x["chg1d"] or 0))
        notes = {"CL=F": "Oil feeds straight into gas prices and inflation, and drives energy stocks.",
                 "GC=F": "Gold is a classic safe haven that often rises when investors are nervous or real interest rates fall.",
                 "DX-Y.NYB": "A stronger dollar shrinks the overseas profits of US multinationals when they're converted back.",
                 "BTC-USD": "Bitcoin often trades like a high-risk asset, so big moves can signal shifts in risk appetite."}
        scenes = [
            {"kind": "title", "eyebrow": "Oil, gold, dollar & crypto",
             "headline": f"{biggest['name']} {'leads' if (biggest['chg1d'] or 0) > 0 else 'slides'} with a {abs(biggest['chg1d'] or 0):.1f}% move",
             "body": "Assets outside the stock market often explain what stocks are doing."},
            {"kind": "stats", "headline": "Today's moves", "items": [{"label": self.q[s]["name"], "value": level(s, self.q[s]["last"]), "change": self.q[s]["chg1d"], **live_tag(s)} for s in syms]},
            chart_scene(biggest, f"{biggest['name']}: 3-month trend", notes[biggest["symbol"]]),
        ]
        self.add("assets", "macro", "Commodities", scenes[0]["headline"], scenes, 8, art="oil" if biggest["symbol"] == "CL=F" else "coins",
                 media_query="gold bars" if biggest["symbol"] == "GC=F" else "oil refinery" if biggest["symbol"] == "CL=F" else "currency money")

    def world(self):
        gl = sorted((self.q[s] for s in GLOBAL if s in self.q), key=lambda x: x["chg1d"] or 0, reverse=True)
        if len(gl) < 4:
            return
        best, worst = gl[0], gl[-1]
        scenes = [
            {"kind": "title", "eyebrow": "Around the world", "headline": f"{best['name']} leads global markets, {worst['name']} lags",
             "body": "US stocks don't trade in a vacuum. Here's how major markets abroad finished their latest session."},
            {"kind": "bars", "headline": "Latest session", "items": [{"label": g["name"], "value": round(g["chg1d"] or 0, 2)} for g in gl]},
            {"kind": "text", "headline": "Why it matters for the US", "basic": True,
             "body": "Asia trades first, then Europe, then the US. A sell-off overseas can set the mood for Wall Street's open, and big US companies earn a large share of their sales abroad."},
        ]
        self.add("world", "macro", "Global Markets", scenes[0]["headline"], scenes, 7, art="globe", media_query="world map city lights")

    def economy(self):
        m = self.ctx.get("macro") or {}
        if not m:
            return
        cpi, cpi_prev = m["cpi_yoy"], m["cpi_yoy_prev"]
        core = m["core_yoy"]
        un, un_prev = m["unrate"], m["unrate_prev"]
        jobs = m["payrolls"]
        gdp = m["gdp"]
        above = cpi[1] > 2
        month = lambda d: __import__("datetime").date.fromisoformat(d).strftime("%b %Y")
        scenes = [
            {"kind": "title", "eyebrow": "Economy dashboard",
             "headline": f"Inflation {cpi[1]:.1f}%, unemployment {un[1]:.1f}%",
             "body": f"The latest official US data, from the St. Louis Fed's FRED database. Inflation is {'above' if above else 'at or below'} the Fed's 2% goal."},
            {"kind": "stats", "headline": "Latest readings", "items": [
                {"label": "CPI inflation (YoY)", "value": f"{cpi[1]:.1f}%", "note": f"{month(cpi[0])} · prev {cpi_prev[1]:.1f}%"},
                {"label": "Core CPI (YoY)", "value": f"{core[1]:.1f}%", "note": f"{month(core[0])}"},
                {"label": "Unemployment", "value": f"{un[1]:.1f}%", "note": f"{month(un[0])} · prev {un_prev[1]:.1f}%"},
                {"label": "Jobs added", "value": f"{jobs[1]:+,.0f}K", "note": month(jobs[0])},
                {"label": "Fed funds rate", "value": f"{m['fed_funds'][1]:.2f}%", "note": "effective rate"},
                {"label": "Real GDP growth", "value": f"{gdp[1]:+.1f}%", "note": f"annualized, {gdp[0][:7]}"},
            ]},
            {"kind": "chart", "headline": "Inflation over 5 years", "label": "CPI, year over year",
             "last": f"{cpi[1]:.1f}%", "change": None, "points": [round(v, 2) for _, v in m["cpi_hist"]],
             "dates": [month(m["cpi_hist"][0][0]), month(m["cpi_hist"][-1][0])],
             "note": f"The Fed aims for about 2%. Inflation is {abs(cpi[1] - 2):.1f} points {'above' if above else 'below'} that target."},
            {"kind": "chart", "headline": "Unemployment over 5 years", "label": "Unemployment rate",
             "last": f"{un[1]:.1f}%", "change": None, "points": [v for _, v in m["unrate_hist"]],
             "dates": [month(m["unrate_hist"][0][0]), month(m["unrate_hist"][-1][0])],
             "note": "A rising unemployment rate is one of the clearest early signs of a slowing economy."},
            {"kind": "quiz", "question": "Based on the latest CPI, is inflation above or below the Fed's 2% target?",
             "options": ["Above 2%", "Below 2%"], "answer": 0 if above else 1,
             "explain": f"CPI inflation is {cpi[1]:.1f}% a year. The Fed officially targets 2% on a related measure, PCE inflation."},
        ]
        r = self.add("economy", "macro", "Economy", scenes[0]["headline"], scenes, 5, art="factory",
                     media_query="busy city street people",
                     sources=[{"title": "FRED: Consumer Price Index", "url": "https://fred.stlouisfed.org/series/CPIAUCSL"},
                              {"title": "FRED: Unemployment rate", "url": "https://fred.stlouisfed.org/series/UNRATE"}])
        if r:
            r["id"] = f"{self.date}-economy"  # once per day, not per run

    # ---------- news ----------
    def headlines(self):
        news = self.ctx["news"][:6]
        if len(news) < 3:
            return
        self.add("headlines", "news", "Headlines", "The stories moving markets", [
            {"kind": "title", "eyebrow": "In 60 seconds", "headline": "The stories moving markets right now",
             "body": f"{len(news)} headlines from free news sources, ranked by how much they matter to US investors."},
            {"kind": "bullets", "headline": "Top stories", "items": [n["title"] for n in news[:3]]},
            {"kind": "bullets", "headline": "Also on the radar", "items": [n["title"] for n in news[3:6]]} if len(news) > 3 else None,
        ], 3, art="news", media_query="newspaper", sources=[{"title": n["title"], "url": n["url"]} for n in news])

    def news_stories(self, n=6, skip_urls=()):
        topics = {t["id"]: t for t in TOPICS}
        count = 0
        for i, item in enumerate(self.ctx["news"]):
            if count >= n:
                break
            if item["url"] in skip_urls:
                continue
            topic = topics.get(item["topic"])
            mins = int(item["age_hours"] * 60)
            ago = f"{mins} min ago" if mins < 60 else f"{int(item['age_hours'])}h ago"
            scenes = [{"kind": "title", "eyebrow": f"{item['source']} · {ago}", "headline": item["title"],
                       "body": first_sentences(item["summary"], 1, 200) if item["summary"] and item["summary"] != item["title"] else None}]
            rest = item["summary"][len(scenes[0]["body"] or ""):].strip() if item["summary"] else ""
            if len(rest) > 60:
                scenes.append({"kind": "text", "headline": "The details", "body": first_sentences(rest, 2, 280)})
            for sym in item["tickers"][:1]:
                if sym in self.q:
                    s = self.q[sym]
                    scenes.append(chart_scene(s, f"{WATCHLIST[sym][0]} ({sym}) {tone(s['chg1d'], signed(s['chg1d']))} on the day",
                                              f"Over three months the stock is {tone(s['chg3m'], signed(s['chg3m']))}."))
            why = topic["why"] if topic else "Big headlines can shift expectations for profits, interest rates or the economy, which is what ultimately moves stock prices."
            lesson = self.lessons.get(topic["lesson"]) if topic else None
            scenes.append({"kind": "text", "headline": "Why it matters", "basic": True,
                           "body": why + (f"\n\nGo deeper: **{lesson}** in the Learn tab." if lesson else "")})
            bg = {"type": "image", "src": item["image"]} if item.get("image") else None
            key = "news-" + hashlib.md5(item["url"].encode()).hexdigest()[:8]
            r = self.add(key, (topic or {}).get("category", "news"), TOPIC_TAGS.get(item["topic"], "Top Story"), item["title"],
                         scenes, 10 + i, art=TOPIC_ART.get(item["topic"], "news"), bg=bg,
                         ticker=item["tickers"][0] if item["tickers"] else None,
                         media_query=(topic or {}).get("media"),
                         sources=[{"title": f"{item['source']}: {item['title']}", "url": item["url"]}])
            if r:
                count += 1

    # ---------- stock ideas ----------
    def spotlight(self, f, q, reason, priority):
        sym = f["symbol"]
        name = WATCHLIST.get(sym, (f["name"],))[0]
        price = f["price"] or q["last"]
        bull, bear = [], []
        rg, pm, fpe = f["revenue_growth"], f["profit_margin"], f["forward_pe"]
        upside = (f["target_mean"] / price - 1) * 100 if f["target_mean"] and price else None
        if rg is not None and rg > 0.10:
            bull.append(f"Fast growth: revenue up **{rg * 100:.0f}%** from a year ago")
        if pm is not None and pm > 0.2:
            bull.append(f"Very profitable: keeps **{pm * 100:.0f}¢** of profit from every $1 of sales")
        if f["free_cash_flow"] and f["free_cash_flow"] > 0:
            bull.append(f"Generates {big_money(f['free_cash_flow'])} of free cash flow a year")
        if f["rec_key"] in ("buy", "strong_buy") and (f["analysts"] or 0) >= 5:
            bull.append(f"{f['analysts']} Wall Street analysts cover it, with a consensus of **{f['rec_key'].replace('_', ' ')}**")
        if upside is not None and upside > 10:
            bull.append(f"Average analyst price target of {money(f['target_mean'])} is {upside:.0f}% above today's price")
        if f["high52"] and price >= f["high52"] * 0.93:
            bull.append("Strong momentum: trading near its 52-week high")
        if f["dividend_yield"] and f["dividend_yield"] >= 2:
            bull.append(f"Pays a {f['dividend_yield']:.1f}% dividend yield")
        if fpe is not None and fpe > 35:
            bear.append(f"Pricey: **{fpe:.0f}×** next year's expected earnings leaves little room for disappointment")
        if rg is not None and rg <= -0.01:
            bear.append(f"Revenue is shrinking: down {abs(rg) * 100:.0f}% from a year ago")
        elif rg is not None and rg < 0.03:
            bear.append("Sales have stalled: revenue is roughly flat versus a year ago")
        if pm is not None and pm < 0:
            bear.append("Not profitable yet, so it depends on growth continuing")
        if f["debt_to_equity"] and f["debt_to_equity"] > 150:
            bear.append(f"Heavy debt: debt is {f['debt_to_equity'] / 100:.1f}× shareholder equity")
        if upside is not None and upside < 0:
            bear.append("Already trading above the average analyst price target")
        if f["low52"] and price <= f["low52"] * 1.1:
            bear.append("Weak trend: trading near its 52-week low")
        if (q["chg3m"] or 0) < -15:
            bear.append(f"Down {abs(q['chg3m']):.0f}% in three months, so the market has doubts")
        if f["beta"] and f["beta"] > 1.5:
            bear.append(f"Volatile: historically moves about {f['beta']:.1f}× as much as the market")
        if fpe is not None and 22 < fpe <= 35:
            bear.append(f"Valuation premium: {fpe:.0f}× forward earnings vs. the market's long-run average in the mid-to-high teens")
        six = (q["series6m"][-1] / q["series6m"][0] - 1) * 100 if q.get("series6m") else 0
        if six > 30:
            bear.append(f"After a {six:.0f}% run in six months, expectations are high and any stumble could hurt")
        if SECTOR_RISKS.get(f.get("sector")):
            bear.append(SECTOR_RISKS[f["sector"]])
        if not bear:
            bear.append("Single-stock risk: one bad earnings report or headline can knock any stock down 10%+")
        if not bull:
            bull.append("A large, established company that institutional investors already own")

        stats = [
            {"label": "Share price", "value": money(price), "change": q["chg1d"], **live_tag(sym)},
            {"label": "Market cap", "value": big_money(f["market_cap"])},
            {"label": "Forward P/E", "value": f"{fpe:.1f}×" if fpe else "—"},
            {"label": "Revenue growth", "value": (signed(rg * 100, 0) if rg is not None else "—"), "note": "year over year"},
            {"label": "Profit margin", "value": f"{pm * 100:.0f}%" if pm is not None else "—"},
            {"label": "52-week range", "value": f"{money(f['low52'], 0)}–{money(f['high52'], 0)}" if f["low52"] and f["high52"] else "—"},
        ]
        what = first_sentences(f["summary"], 2, 280) if f.get("summary") else f"{name} is a {f.get('industry') or 'large US'} company."
        scenes = [
            {"kind": "title", "eyebrow": f"Stock spotlight · {sym}", "headline": f"Should {name} be on your watchlist?",
             "body": f"{reason} Here's the bull case, the bear case and the numbers. You decide."},
            {"kind": "text", "headline": "What the company does", "body": what + (f"\n\nSector: **{f['sector']}**" if f.get("sector") else "")},
            {"kind": "stats", "headline": "The numbers", "items": stats},
            chart_scene(q, f"{sym} over 6 months", label=f"{name} · 6 months", long=True),
            {"kind": "bullets", "headline": "🐂 The bull case", "style": "pros", "items": bull[:4]},
            {"kind": "bullets", "headline": "🐻 The bear case", "style": "cons", "items": bear[:4]},
        ]
        if f.get("next_earnings"):
            scenes.append({"kind": "text", "headline": "What to watch next",
                           "body": f"Next earnings report expected around **{nice_date(f['next_earnings'])}**. Watch revenue growth, margins and especially guidance, since that's what moves the stock."})
        if f["forward_eps"] and f["forward_eps"] > 0 and price:
            pe = price / f["forward_eps"]
            correct = f"About {pe:.0f}×"
            opts, ans = shuffled_quiz(self.date + sym, correct, [f"About {pe * k:.0f}×" for k in (0.5, 1.6, 2.4)])
            scenes.append({"kind": "quiz", "question": f"{sym} trades at {money(price)} and analysts expect {money(f['forward_eps'])} of earnings per share next year. What's its forward P/E?",
                           "options": opts, "answer": ans, "explain": f"{money(price)} ÷ {money(f['forward_eps'])} ≈ {pe:.1f}. Investors pay about ${pe:.0f} for each $1 of expected profit."})
        self.add(f"idea-{sym.lower()}", "ideas", "Stock Spotlight", f"{name} ({sym}): bull vs. bear", scenes, priority,
                 ticker=sym, art="magnifier", disclaimer=True, media_query="modern office technology",
                 summary="A data-driven profile built from public figures. Educational only, not a recommendation.",
                 sources=[{"title": f"Yahoo Finance: {sym}", "url": f"https://finance.yahoo.com/quote/{sym}/"},
                          {"title": f"SEC filings: {name}", "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={name.replace(' ', '+')}&type=10-K"}])

    def curve_scene(self):
        c = self.ctx.get("curve") or {}
        p, wk = c.get("points") or {}, (c.get("week_ago") or {}).get("points") or {}
        if not p.get("2Y") or not p.get("10Y"):
            return None
        s2_10 = (p["10Y"] - p["2Y"]) * 100
        s3m_10 = (p["10Y"] - p["3M"]) * 100 if p.get("3M") else None

        def wk_bp(k):
            return f"{(p[k] - wk[k]) * 100:+.0f} bp w/w" if wk.get(k) and p.get(k) else None

        return {"kind": "stats", "headline": f"Official curve · Treasury, {nice_date(c['date'])}", "items": [
            {"label": "2-year", "value": f"{p['2Y']:.2f}%", "note": wk_bp("2Y")},
            {"label": "10-year", "value": f"{p['10Y']:.2f}%", "note": wk_bp("10Y")},
            {"label": "2s10s spread", "value": f"{s2_10:+.0f} bp", "note": "inverted" if s2_10 < 0 else "positive slope"},
            {"label": "3m10y spread", "value": f"{s3m_10:+.0f} bp" if s3m_10 is not None else "—", "note": "the Fed's favorite recession signal"}]}

    # ---------- calendar-driven reels ----------
    def _events(self, day, min_imp=2):
        evs = (self.ctx.get("calendar") or {}).get("events", [])
        return [e for e in evs if e["date"] == day and e.get("importance", 0) >= min_imp]

    def _earnings(self, day, n=6):
        return [e for e in (self.ctx.get("calendar") or {}).get("earnings", []) if e["date"] == day][:n]

    def _event_line(self, e):
        t = clock(e.get("time"))
        head = f"{t} · {e['title']}" if t else e["title"]
        if e.get("actual"):
            return head + f": **{e['actual']}**" + (f" (est. {e['consensus']})" if e.get("consensus") else "")
        if e.get("consensus"):
            return head + f" (est. {e['consensus']}, prior {e.get('previous') or '—'})"
        return head + (f" (prior {e['previous']})" if e.get("previous") else "")

    def _earnings_line(self, items):
        pre = [e["symbol"] for e in items if e.get("when") == "pre"]
        post = [e["symbol"] for e in items if e.get("when") == "post"]
        other = [e["symbol"] for e in items if e.get("when") not in ("pre", "post")]
        parts = ([f"before the open: {', '.join(pre)}"] if pre else []) + ([f"after the close: {', '.join(post)}"] if post else []) \
            + ([", ".join(other)] if other else [])
        return "Earnings " + "; ".join(parts) if parts else None

    def today_calendar_scene(self, results=False):
        evs = self._events(self.date)
        lines = [self._event_line(e) for e in evs[:6]]
        earn = self._earnings_line(self._earnings(self.date, 8))
        if earn:
            lines.append(earn)
        if not lines:
            return None
        return {"kind": "bullets", "headline": "Today's data, actual vs. estimate" if results else "On today's calendar", "items": lines}

    def fed_watch(self):
        cal_ = self.ctx.get("calendar") or {}
        fed = cal_.get("fed") or {}
        nxt, last = fed.get("next"), fed.get("last")
        today = date.fromisoformat(self.date)
        curve = (self.ctx.get("curve") or {}).get("points", {})
        res = (last or {}).get("result") or {}
        rng = f"{res['low']:.2f}–{res['high']:.2f}%" if res else None
        # Decision reel: the day of and the two days after a meeting.
        if last and 0 <= (today - date.fromisoformat(last["date"])).days <= 2:
            verb = {"cut": "cuts", "hike": "raises", "hold": "holds"}.get(res.get("action"), "decides")
            scenes = [
                {"kind": "title", "eyebrow": f"FOMC decision · {nice_date(last['date'])}",
                 "headline": f"Fed {verb} rates: {last['actual']}",
                 "body": "The Federal Open Market Committee's statement is out."
                         + (f" Dissent: {res['dissents']}." if res.get("dissents") else " The vote was unanimous.")},
                {"kind": "stats", "headline": "Where policy stands", "items": [
                    {"label": "Fed funds target", "value": rng or "—"},
                    {"label": "Change", "value": f"{res.get('change_bp', 0):+d} bp" if res else "—"},
                    {"label": "2-yr Treasury", "value": f"{curve['2Y']:.2f}%" if curve.get("2Y") else "—", "note": "market's rate expectations"},
                    {"label": "10-yr Treasury", "value": f"{curve['10Y']:.2f}%" if curve.get("10Y") else "—"}]},
                {"kind": "text", "headline": "What markets watch now",
                 "body": "The press conference at 2:30 pm ET, the minutes three weeks later, and whether the 2-year yield moves "
                         "above or below the new target range, which shows if traders expect the next move to go the other way."},
            ]
            r = self.add("fed-decision", "macro", "Fed Decision", scenes[0]["headline"], scenes, 0, art="fed",
                         sources=[{"title": "FOMC statement", "url": last.get("url")}])
            if r:
                r["id"] = f"fed-{last['date']}"  # one reel per meeting
        # Preview reel: within 10 days of the next meeting.
        if nxt and 0 <= (date.fromisoformat(nxt["date"]) - today).days <= 10:
            days = (date.fromisoformat(nxt["date"]) - today).days
            when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
            # The headline releases the Fed weighs most, newest reading of each.
            headline = ["CPI", "Core CPI", "Core PCE Price Index", "PCE Price Index", "Nonfarm Payrolls", "Unemployment Rate", "GDP", "Retail Sales", "PPI"]
            since = (last or {}).get("date") or (today - timedelta(days=45)).isoformat()
            pool = [e for e in cal_.get("events", []) if e.get("actual") and since < e["date"] <= self.date]
            recent = [e for name in headline for e in sorted((x for x in pool if x["title"] == name), key=lambda x: x["date"])[-1:]]
            spread = curve["2Y"] - res["high"] if curve.get("2Y") and res else None
            if spread is None:
                read = "Watch the 2-year Treasury yield into the meeting: it's the market's best read on the next move."
            elif spread > 0.15:
                read = "The 2-year yield tracks where traders expect policy to go. It's **above** the top of the target range, which leans toward a hike or a longer hold."
            elif spread < -0.15:
                read = "The 2-year yield tracks where traders expect policy to go. It's **below** the target range, which leans toward cuts ahead."
            else:
                read = "The 2-year yield tracks where traders expect policy to go. It's close to the current range, which points to no change."
            macro = self.ctx.get("macro") or {}
            scenes = [
                {"kind": "title", "eyebrow": f"Fed watch · {nice_date(nxt['date'])}",
                 "headline": f"The Fed decides {when}",
                 "body": f"Statement at 2:00 pm ET on {nice_date(nxt['date'])}, press conference at 2:30."
                         + (" This meeting includes new projections and the dot plot." if "projections" in nxt["title"] else "")},
                {"kind": "stats", "headline": "The setup", "items": [
                    {"label": "Current target", "value": rng or "—"},
                    {"label": "Last move", "value": ((last or {}).get("actual") or "—").split(" to ")[0], "note": nice_date(last["date"]) if last else None},
                    {"label": "2-yr Treasury", "value": f"{curve['2Y']:.2f}%" if curve.get("2Y") else "—",
                     "note": f"{spread * 100:+.0f} bp vs. top of range" if spread is not None else None},
                    {"label": "Core CPI", "value": f"{macro['core_yoy'][1]:.1f}%" if macro.get("core_yoy") else "—", "note": "year over year"}]},
                {"kind": "bullets", "headline": "Data the Fed has seen since its last meeting",
                 "items": [f"{nice_date(e['date']).split(',')[1].strip()} · " + self._event_line({**e, "time": None}) for e in recent[-5:]]} if recent else None,
                self.odds_scene(nxt["date"]),
                {"kind": "text", "headline": "Read the 2-year", "body": read},
            ]
            self.add("fed-watch", "macro", "Fed Watch", scenes[0]["headline"], scenes, 1, art="fed",
                     sources=[{"title": "Federal Reserve: FOMC calendar", "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"}])

    def odds_scene(self, meeting):
        odds = self.ctx.get("fed_odds") or []
        o = next((x for x in odds if x["date"] == meeting), None)
        if not o:
            return None
        items = [{"label": label, "value": round(o[key] * 100, 1), "display": f"{o[key] * 100:.0f}%"}
                 for key, label in (("cut", "Cut"), ("hold", "Hold"), ("hike", "Hike")) if o[key] >= 0.005]
        path = " → ".join(f"{nice_date(x['date']).split(',')[1].strip()}: {x['post']:.2f}%" for x in odds[:4])
        return {"kind": "bars", "headline": "What futures are pricing", "mode": "positive", "items": items,
                "body": f"From 30-day fed funds futures, CME FedWatch-style. Implied effective rate after each meeting: {path}."}

    def week_ahead(self):
        cal_ = self.ctx.get("calendar") or {}
        today = date.fromisoformat(self.date)
        start = today + timedelta(days=7 - today.weekday()) if today.weekday() >= 5 else today - timedelta(days=today.weekday())
        lo, hi = start.isoformat(), (start + timedelta(days=4)).isoformat()
        big = [e for e in cal_.get("events", []) if lo <= e["date"] <= hi and e.get("importance", 0) >= 3]
        earn = sorted((e for e in cal_.get("earnings", []) if lo <= e["date"] <= hi), key=lambda e: -e.get("cap", 0))[:8]
        other = [e for e in cal_.get("events", []) if e.get("category") in ("politics", "market") and e.get("importance", 0) >= 2
                 and lo <= e["date"] <= hi]
        if not big and not earn:
            return
        day = lambda d: nice_date(d).split(",")[0]
        when = lambda e: "pre-market" if e.get("when") == "pre" else "after close" if e.get("when") == "post" else "time TBA"
        scenes = [
            {"kind": "title", "eyebrow": f"Week ahead · {nice_date(lo)}", "headline": "The week's market-moving events",
             "body": f"{len(big)} major releases and {len(earn)} of the biggest earnings reports on deck."},
            {"kind": "bullets", "headline": "Key data & the Fed", "items": [f"{day(e['date'])} " + self._event_line(e) for e in big[:6]]} if big else None,
            {"kind": "bullets", "headline": "Biggest earnings",
             "items": [f"{day(e['date'])} · **{e['symbol']}** {e['name'][:26]} ({when(e)}, est. EPS {e.get('eps_est') or '—'})" for e in earn[:6]]} if earn else None,
            {"kind": "bullets", "headline": "Also this week", "items": [f"{nice_date(e['date'])}: {e['title']}" for e in other[:4]]} if other else None,
        ]
        r = self.add("week-ahead", "macro", "Week Ahead", scenes[0]["headline"], scenes, 1, art="calendar")
        if r:
            r["id"] = f"week-ahead-{lo}"
