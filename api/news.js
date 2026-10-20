// Vercel serverless function: latest headlines for one ticker, from Yahoo Finance search (free, no key).
//   /api/news?s=AAPL
const SEARCH = "https://query1.finance.yahoo.com/v1/finance/search";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const SYMBOL = /^[A-Z0-9^=.\-]{1,15}$/;

export default async function handler(req, res) {
  const sym = String(req.query.s || "").toUpperCase();
  if (!SYMBOL.test(sym)) return res.status(400).json({ error: "Pass a symbol as ?s=AAPL" });
  let news = [];
  try {
    const r = await fetch(`${SEARCH}?q=${encodeURIComponent(sym)}&quotesCount=0&newsCount=8`, { headers: { "User-Agent": UA } });
    if (r.ok) {
      const j = await r.json();
      news = (j.news || []).map((n) => ({ title: n.title, publisher: n.publisher, url: n.link, time: n.providerPublishTime }));
    }
  } catch { /* return an empty list */ }
  res.setHeader("Cache-Control", "public, s-maxage=300, stale-while-revalidate=600");
  return res.status(200).json({ symbol: sym, news });
}
