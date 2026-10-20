"""Official US economic data from FRED (St. Louis Fed). Uses the public CSV download, so no API key."""
import csv
import io
import logging
from datetime import date

import requests

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (compatible; MarketReels/1.0)"}
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
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
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
        log.warning("FRED unavailable: %s", e)
        return {}
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
    return m
