// Vercel serverless function: live quotes relayed from Yahoo Finance (free, no key).
// Browsers can't call Yahoo directly (no CORS), so the app asks this function instead.
// Vercel's CDN caches each response for 20s, so the app polling every 30s costs almost nothing,
// and the Hobby plan pauses rather than bills if limits were ever hit.
const SPARK = "https://query1.finance.yahoo.com/v7/finance/spark";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const SYMBOL = /^[A-Z0-9^=.\-]{1,15}$/;

async function batch(symbols) {
  try {
    const url = `${SPARK}?symbols=${encodeURIComponent(symbols.join(","))}&range=1d&interval=1d`;
    const r = await fetch(url, { headers: { "User-Agent": UA } });
    if (!r.ok) return [];
    const j = await r.json();
    return j?.spark?.result || [];
  } catch {
    return [];
  }
}

export default async function handler(req, res) {
  const symbols = [...new Set(String(req.query.s || "").toUpperCase().split(",").filter((s) => SYMBOL.test(s)))].slice(0, 120);
  if (!symbols.length) return res.status(400).json({ error: "Pass symbols as ?s=AAPL,MSFT" });

  const parts = [];
  for (let i = 0; i < symbols.length; i += 20) parts.push(symbols.slice(i, i + 20));
  const results = (await Promise.all(parts.map(batch))).flat();

  const quotes = {};
  for (const r of results) {
    const m = r?.response?.[0]?.meta;
    const price = m?.regularMarketPrice;
    const prev = m?.chartPreviousClose ?? m?.previousClose;
    if (price == null) continue;
    quotes[r.symbol] = { price, prev: prev ?? null, chg: prev ? (price / prev - 1) * 100 : null, time: m.regularMarketTime, type: m.instrumentType };
  }
  res.setHeader("Cache-Control", "public, s-maxage=20, stale-while-revalidate=60");
  return res.status(200).json({ generated_at: new Date().toISOString(), source: "yahoo-live", quotes });
}
