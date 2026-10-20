"""Official US economic data: FRED's public CSV first, then the BLS public API (both free, no key).

FRED sometimes times out from GitHub's servers, so the BLS API covers CPI, core CPI, unemployment and
payrolls, and the last good readings (data/macro_cache.json) fill anything still missing."""
import csv
import io
import json
import logging
import time
from datetime import date
from pathlib import Path

import requests

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (compatible; MarketReels/1.0)"}
# Last good readings. The data changes monthly, so a cached copy beats no economy reel when FRED is slow.
CACHE = Path(__file__).resolve().parent.parent / "data" / "macro_cache.json"
SERIES = {
    "CPIAUCSL": "CPI (all items)",
    "CPILFESL": "Core CPI",
    "UNRATE": "Unemployment rate",
    "PAYEMS": "Nonfarm payrolls",
    "DFF": "Fed funds rate",
    "A191RL1Q225SBEA": "Real GDP growth",
}


def _series(sid, start):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"
    for attempt in range(2):  # short: the BLS API is the backup when FRED is slow
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 1:
                raise
            log.info("FRED %s attempt %d failed (%s); retrying", sid, attempt + 1, e)
            time.sleep(5 * (attempt + 1))
    rows = []
    for row in csv.DictReader(io.StringIO(r.text)):
        v = row.get(sid)
        d = row.get("observation_date") or row.get("DATE")
        if v and v != "." and d:
            rows.append((d, float(v)))
    return rows


def _yoy(rows):
    out = []
    for i in range(12, len(rows)):
        out.append((rows[i][0], (rows[i][1] / rows[i - 12][1] - 1) * 100))
    return out


def fetch_macro():
    """Returns a dict of the latest readings plus short histories, or {} if FRED is unreachable."""
    start = f"{date.today().year - 6}-01-01"
    try:
        cpi = _series("CPIAUCSL", start)
        core = _series("CPILFESL", start)
        unrate = _series("UNRATE", start)
        payems = _series("PAYEMS", start)
        dff = _series("DFF", f"{date.today().year - 1}-01-01")
        gdp = _series("A191RL1Q225SBEA", start)
    except Exception as e:
        log.warning("FRED unavailable (%s); trying BLS", e)
        return _from_bls()
    cpi_yoy, core_yoy = _yoy(cpi), _yoy(core)
    jobs = [(payems[i][0], payems[i][1] - payems[i - 1][1]) for i in range(1, len(payems))]
    m = {
        "cpi_yoy": cpi_yoy[-1], "cpi_yoy_prev": cpi_yoy[-2],
        "core_yoy": core_yoy[-1], "core_yoy_prev": core_yoy[-2],
        "unrate": unrate[-1], "unrate_prev": unrate[-2],
        "payrolls": jobs[-1], "payrolls_prev": jobs[-2],
        "fed_funds": dff[-1],
        "gdp": gdp[-1], "gdp_prev": gdp[-2],
        "cpi_hist": cpi_yoy[-60:],
        "unrate_hist": unrate[-60:],
    }
    log.info("macro: CPI %.1f%% (%s), unemployment %.1f%%", m["cpi_yoy"][1], m["cpi_yoy"][0], m["unrate"][1])
    CACHE.write_text(json.dumps(m), encoding="utf-8")
    return m


BLS = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_SERIES = {"CUUR0000SA0": "cpi", "CUUR0000SA0L1E": "core", "LNS14000000": "unrate", "CES0000000001": "payems"}


def _from_bls():
    """CPI, core CPI, unemployment and payrolls from BLS; other fields from the cache."""
    cached = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    try:
        year = date.today().year
        r = requests.post(BLS, json={"seriesid": list(BLS_SERIES), "startyear": str(year - 6), "endyear": str(year)},
                          headers=UA, timeout=45)
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(body.get("message"))
        series = {}
        for s in body["Results"]["series"]:
            rows = [(f"{d['year']}-{d['period'][1:]}-01", float(d["value"])) for d in s["data"]
                    if d["period"].startswith("M") and d["period"] != "M13" and d["value"] not in ("-", "")]
            series[BLS_SERIES[s["seriesID"]]] = sorted(rows)
    except Exception as e:
        if cached:
            log.warning("BLS unavailable too (%s); using cached readings", e)
            return cached
        log.warning("BLS unavailable: %s", e)
        return {}
    cpi_yoy, core_yoy = _yoy(series["cpi"]), _yoy(series["core"])
    pay = series["payems"]
    jobs = [(pay[i][0], pay[i][1] - pay[i - 1][1]) for i in range(1, len(pay))]
    m = {**cached,
         "cpi_yoy": cpi_yoy[-1], "cpi_yoy_prev": cpi_yoy[-2], "core_yoy": core_yoy[-1], "core_yoy_prev": core_yoy[-2],
         "unrate": series["unrate"][-1], "unrate_prev": series["unrate"][-2],
         "payrolls": jobs[-1], "payrolls_prev": jobs[-2], "cpi_hist": cpi_yoy[-60:], "unrate_hist": series["unrate"][-60:]}
    if "fed_funds" not in m or "gdp" not in m:
        log.warning("BLS has no fed funds / GDP and there's no cache; economy reel will be skipped")
        return {}
    log.info("macro (BLS): CPI %.1f%% (%s), unemployment %.1f%%", m["cpi_yoy"][1], m["cpi_yoy"][0], m["unrate"][1])
    CACHE.write_text(json.dumps(m), encoding="utf-8")
    return m
