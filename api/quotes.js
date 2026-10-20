// Vercel serverless function: live quotes relayed from Yahoo Finance (free, no key).
// Browsers can't call Yahoo directly (no CORS), so the app asks this function instead.
//   /api/quotes?s=AAPL,^GSPC            latest price + previous close
//   /api/quotes?s=AAPL,^GSPC&spark=1    also today's intraday points (5-minute) for mini charts
// Vercel's CDN caches each response for 20s, so the app polling every 30s costs almost nothing,
// and the Hobby plan pauses rather than bills if limits were ever hit.
const SPARK = "https://query1.finance.yahoo.com/v7/finance/spark";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const SYMBOL = /^[A-Z0-9^=.\-]{1,15}$/;
const MAX_POINTS = 60;

async function batch(symbols, intraday) {
  try {
    const url = `${SPARK}?symbols=${encodeURIComponent(symbols.join(","))}&range=1d&interval=${intraday ? "5m" : "1d"}`;
    const r = await fetch(url, { headers: { "User-Agent": UA } });
    if (!r.ok) return [];
    const j = await r.json();
    return j?.spark?.result || [];
  } catch {
    return [];
  }
}

function downsample(points) {
  const clean = points.filter((p) => p != null);
  if (clean.length <= MAX_POINTS) return clean;
  const step = clean.length / MAX_POINTS;
  const out = [];
  for (let i = 0; i < MAX_POINTS - 1; i++) out.push(clean[Math.floor(i * step)]);
  out.push(clean[clean.length - 1]);
  return out;
}

export default async function handler(req, res) {
  const symbols = [...new Set(String(req.query.s || "").toUpperCase().split(",").filter((s) => SYMBOL.test(s)))].slice(0, 120);
  if (!symbols.length) return res.status(400).json({ error: "Pass symbols as ?s=AAPL,MSFT" });
  const intraday = req.query.spark === "1";

  const parts = [];
  for (let i = 0; i < symbols.length; i += 20) parts.push(symbols.slice(i, i + 20));
  const results = (await Promise.all(parts.map((p) => batch(p, intraday)))).flat();

  const quotes = {};
  for (const r of results) {
    const resp = r?.response?.[0];
    const m = resp?.meta;
    const price = m?.regularMarketPrice;
    const prev = m?.chartPreviousClose ?? m?.previousClose;
    if (price == null) continue;
    const q = { price, prev: prev ?? null, chg: prev ? (price / prev - 1) * 100 : null, time: m.regularMarketTime, type: m.instrumentType, name: m.shortName || m.longName || null };
    if (intraday) q.points = downsample(resp?.indicators?.quote?.[0]?.close || []).map((v) => Math.round(v * 10000) / 10000);
    quotes[r.symbol] = q;
  }
  res.setHeader("Cache-Control", "public, s-maxage=20, stale-while-revalidate=60");
  return res.status(200).json({ generated_at: new Date().toISOString(), source: "yahoo-live", quotes });
}
