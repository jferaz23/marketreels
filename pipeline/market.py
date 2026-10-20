"""Price data and company fundamentals from Yahoo Finance (via yfinance, free, no key)."""
import logging
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

from config import ASSETS, FUTURES, GLOBAL, INDICES, SECTORS, VOLATILITY, WATCHLIST, YIELDS

log = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")


def _clean(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _pct(a, b):
    return None if not a or b is None else (b / a - 1) * 100


def _overlay_live(vals, dates, idx_dates, live):
    """Make the latest point match Yahoo's live quote (correct previous close, even across futures rolls)."""
    if not live or live.get("price") is None:
        return vals, dates, None
    day = datetime.fromtimestamp(live["time"], ET).date() if live.get("time") else None
    last_day = idx_dates[-1].date() if idx_dates else None
    if day and last_day and day > last_day:  # history hasn't caught up with today's session yet
        vals = vals + [live["price"]]
        dates = dates + [f"{day:%b} {day.day}"]
    else:
        vals = vals[:-1] + [live["price"]]
    return vals, dates, live.get("prev")


def fetch_quotes(live=None):
    """Returns {symbol: quote} for every tracked symbol with ~6 months of daily closes.

    live: optional {symbol: quote} from quotes.fetch_live; when present it sets the last price and previous close."""
    live = live or {}
    groups = [INDICES, FUTURES, VOLATILITY, YIELDS, ASSETS, GLOBAL, SECTORS, {k: v[0] for k, v in WATCHLIST.items()}]
    names = {sym: name for g in groups for sym, name in g.items()}
    symbols = list(names)
    data = None
    for attempt in range(3):
        try:
            data = yf.download(symbols, period="6mo", interval="1d", auto_adjust=True, group_by="ticker",
                               progress=False, threads=True)
            if data is not None and not data.empty:
                break
        except Exception as e:  # network hiccups / rate limits
            log.warning("download attempt %d failed: %s", attempt + 1, e)
        time.sleep(5 * (attempt + 1))
    if data is None or data.empty:
        raise RuntimeError("Could not download market data from Yahoo Finance")

    quotes = {}
    for sym in symbols:
        try:
            closes = data[sym]["Close"].dropna()
        except KeyError:
            continue
        if len(closes) < 3:
            continue
        vals = [round(float(x), 4) for x in closes.tolist()]
        dates = [f"{d:%b} {d.day}" for d in closes.index]
        vals, dates, live_prev = _overlay_live(vals, dates, list(closes.index), live.get(sym))
        last, prev = vals[-1], (live_prev or vals[-2])
        q3 = vals[-63:]
        quotes[sym] = {
            "symbol": sym,
            "name": names[sym],
            "last": last,
            "prev": prev,
            "chg1d": _pct(prev, last),
            "chg5d": _pct(vals[-6] if len(vals) > 5 else vals[0], last),
            "chg1m": _pct(vals[-22] if len(vals) > 21 else vals[0], last),
            "chg3m": _pct(q3[0], last),
            "hi3m": max(q3),
            "lo3m": min(q3),
            "series": q3,
            "dates": dates[-63:],
            "series6m": vals,
            "dates6m": dates,
            "asof": (datetime.fromtimestamp(live[sym]["time"], ET).strftime("%Y-%m-%d")
                     if live.get(sym, {}).get("time") else closes.index[-1].strftime("%Y-%m-%d")),
        }
    log.info("quotes: %d of %d symbols", len(quotes), len(symbols))
    return quotes


def fetch_fundamentals(symbol):
    """Company profile + key ratios. Every field may be missing; callers must handle None."""
    t = yf.Ticker(symbol)
    try:
        info = t.info or {}
    except Exception as e:
        log.warning("info failed for %s: %s", symbol, e)
        info = {}
    price = _clean(info.get("currentPrice") or info.get("regularMarketPrice"))
    div_rate = _clean(info.get("dividendRate"))
    f = {
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName") or WATCHLIST.get(symbol, (symbol,))[0],
        "long_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "summary": info.get("longBusinessSummary"),
        "price": price,
        "market_cap": _clean(info.get("marketCap")),
        "trailing_pe": _clean(info.get("trailingPE")),
        "forward_pe": _clean(info.get("forwardPE")),
        "forward_eps": _clean(info.get("forwardEps")),
        "revenue_growth": _clean(info.get("revenueGrowth")),
        "earnings_growth": _clean(info.get("earningsGrowth")),
        "profit_margin": _clean(info.get("profitMargins")),
        "gross_margin": _clean(info.get("grossMargins")),
        "free_cash_flow": _clean(info.get("freeCashflow")),
        "debt_to_equity": _clean(info.get("debtToEquity")),
        # Computed from the rate: Yahoo's dividendYield field has switched units over time.
        "dividend_yield": (div_rate / price * 100) if div_rate and price else None,
        "high52": _clean(info.get("fiftyTwoWeekHigh")),
        "low52": _clean(info.get("fiftyTwoWeekLow")),
        "rec_key": info.get("recommendationKey"),
        "analysts": info.get("numberOfAnalystOpinions"),
        "target_mean": _clean(info.get("targetMeanPrice")),
        "beta": _clean(info.get("beta")),
        "next_earnings": None,
    }
    try:
        cal = t.calendar or {}
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates:
            f["next_earnings"] = str(dates[0])
    except Exception:
        pass
    return f
