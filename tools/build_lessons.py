"""Builds data/lessons.json: the evergreen "Learn" library woven into the feed.

Edit or add lessons here, then run:  python tools/build_lessons.py
Scene kinds: title, text, number, stats, chart, bars, bullets, quiz (see README).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "lessons.json"


def quiz(question, options, answer, explain):
    return {"kind": "quiz", "question": question, "options": options, "answer": answer, "explain": explain}


def bond_price(coupon_pct, yield_pct, years=10, face=100.0):
    c, y = coupon_pct / 100 * face, yield_pct / 100
    return sum(c / (1 + y) ** t for t in range(1, years + 1)) + face / (1 + y) ** years


compound = [round(10_000 * 1.07 ** n) for n in range(31)]
dca_prices = [50, 45, 40, 35, 40, 45, 50, 55, 50, 60]
dca_shares = sum(100 / p for p in dca_prices)

LESSONS = [
    {
        "id": "learn-fed-rates", "tag": "Macro 101", "title": "How the Fed moves the whole market",
        "summary": "The Federal Reserve sets short-term interest rates. Those rates ripple into mortgages, corporate borrowing, the dollar and stock valuations.",
        "scenes": [
            {"kind": "title", "headline": "One meeting can move **every** asset on Earth.", "body": "Here's how the Federal Reserve does it, in 60 seconds."},
            {"kind": "text", "headline": "The Fed's two jobs", "body": "Congress gave the Fed a **dual mandate**: maximum employment and stable prices. It aims for about **2% inflation** over time."},
            {"kind": "bullets", "headline": "Its main lever: the fed funds rate", "items": [
                "The FOMC meets **8 times a year** to set a target for overnight bank lending rates",
                "Raise rates → borrowing gets pricier → spending and inflation cool",
                "Cut rates → money gets cheaper → growth (and risk-taking) picks up"]},
            {"kind": "text", "headline": "Why stocks care", "body": "A stock is worth its future profits, **discounted** back to today. Higher rates shrink what those future dollars are worth, which hits fast-growing tech stocks hardest.\n\nThat's why markets hang on every word from the Fed Chair."},
            quiz("If the Fed unexpectedly raises rates, what usually happens to long-duration growth stocks?",
                 ["They tend to rise", "They tend to fall", "No effect", "Only bonds are affected"], 1,
                 "Higher rates reduce the present value of profits far in the future, and growth stocks earn most of theirs far in the future."),
        ],
        "sources": [{"title": "Federal Reserve: Monetary policy", "url": "https://www.federalreserve.gov/monetarypolicy.htm"}],
    },
    {
        "id": "learn-cpi", "tag": "Macro 101", "title": "CPI: the inflation report Wall Street fears",
        "summary": "The Consumer Price Index measures how fast prices rise. Hot readings raise the odds of higher rates.",
        "scenes": [
            {"kind": "title", "headline": "Why one number at 8:30 a.m. can tank the market", "body": "Meet CPI, the Consumer Price Index."},
            {"kind": "text", "headline": "What CPI measures", "body": "Each month the **Bureau of Labor Statistics** prices a basket of goods and services that households buy: rent, food, gas, cars, haircuts, and more."},
            {"kind": "bullets", "headline": "Headline vs. core", "items": [
                "**Headline CPI** includes everything",
                "**Core CPI** strips out food and energy, which swing wildly",
                "Markets usually focus on core, since it shows the underlying trend",
                "The Fed's favorite gauge is a cousin: **PCE** inflation"]},
            {"kind": "text", "headline": "The market reaction", "body": "What moves stocks is the **surprise** versus forecasts, not the number itself. A hotter-than-expected print can push yields up and stocks down in minutes."},
            quiz("Which CPI measure removes food and energy prices?", ["Headline CPI", "Core CPI", "PPI", "GDP deflator"], 1,
                 "Core CPI excludes volatile food and energy, so it shows the stickier underlying trend."),
        ],
        "sources": [{"title": "BLS: Consumer Price Index", "url": "https://www.bls.gov/cpi/"}],
    },
    {
        "id": "learn-yield-curve", "tag": "Macro 101", "title": "The yield curve, explained",
        "summary": "The yield curve plots Treasury yields across maturities. When short rates exceed long rates (an inversion), it has often signaled a slowdown ahead.",
        "scenes": [
            {"kind": "title", "headline": "The recession signal economists watch most", "body": "It's called the yield curve. Here's how to read it."},
            {"kind": "bars", "headline": "A normal curve slopes **up**", "unit": "%", "mode": "positive",
             "items": [{"label": "3-month", "value": 3.0, "display": "3.0%"}, {"label": "2-year", "value": 3.4, "display": "3.4%"}, {"label": "10-year", "value": 4.2, "display": "4.2%"}, {"label": "30-year", "value": 4.6, "display": "4.6%"}],
             "body": "Illustrative. Lenders normally demand more interest to lock money up for longer."},
            {"kind": "bars", "headline": "An inverted curve slopes **down**", "unit": "%", "mode": "positive",
             "items": [{"label": "3-month", "value": 5.4, "display": "5.4%"}, {"label": "2-year", "value": 4.9, "display": "4.9%"}, {"label": "10-year", "value": 4.1, "display": "4.1%"}, {"label": "30-year", "value": 4.2, "display": "4.2%"}],
             "body": "Illustrative. Short rates are high (a tight Fed) while long rates are lower, because investors expect rate cuts and slower growth later."},
            {"kind": "text", "headline": "Signal, not a guarantee", "body": "Inversions have come before most US recessions since the 1960s. But the long 2022–2024 inversion was a reminder that timing is unreliable and false alarms happen."},
            quiz("An 'inverted' yield curve means…", ["Long-term yields are above short-term yields", "Short-term yields are above long-term yields", "All yields are negative", "Stocks yield more than bonds"], 1,
                 "Inversion means short rates exceed long rates, the opposite of the normal upward slope."),
        ],
        "sources": [{"title": "US Treasury: daily yield curve rates", "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"}],
    },
    {
        "id": "learn-bond-math", "tag": "Bonds", "title": "Why bond prices fall when yields rise",
        "summary": "Existing bonds pay a fixed coupon. When new bonds pay more, old ones must get cheaper to compete.",
        "scenes": [
            {"kind": "title", "headline": "Bonds have a seesaw built in", "body": "When yields go up, prices go down. Here's why."},
            {"kind": "text", "headline": "Picture this", "body": "You own a 10-year bond paying **4%**. Next week, new bonds start paying **6%**. Nobody will pay full price for your 4% bond anymore, so its price drops until its total return matches 6%."},
            {"kind": "chart", "headline": "Price of a 10-year, 4% bond", "label": "Market yield 2% → 7%", "last": f"${bond_price(4, 7):.0f}",
             "change": round((bond_price(4, 7) / bond_price(4, 2) - 1) * 100, 1),
             "points": [round(bond_price(4, y / 4), 2) for y in range(8, 29)], "dates": ["2% yield", "7% yield"],
             "note": f"At a 2% yield it's worth **${bond_price(4, 2):.0f}**. At 4% it's worth exactly $100. At 7% it falls to **${bond_price(4, 7):.0f}**."},
            {"kind": "text", "headline": "Why stock traders care", "body": "The 10-year Treasury yield is the market's \"risk-free rate.\" When it jumps, stocks must offer more return to compete, so prices often fall. **Watch the 10-year.**"},
            quiz("A bond pays a 3% coupon. Market yields rise to 5%. Its price will…", ["Rise above $100", "Stay at $100", "Fall below $100", "Double"], 2,
                 "Its fixed 3% coupon is now less attractive than new 5% bonds, so its price must fall to compensate buyers."),
        ],
        "sources": [{"title": "Investor.gov: Bonds", "url": "https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds"}],
    },
    {
        "id": "learn-pe-ratio", "tag": "Valuation", "title": "The P/E ratio in 60 seconds",
        "summary": "Price-to-earnings tells you how many dollars investors pay for each dollar of a company's annual profit.",
        "scenes": [
            {"kind": "title", "headline": "Is a $500 stock expensive?", "body": "You can't tell from the price alone. You need the **P/E ratio**."},
            {"kind": "number", "headline": "Price ÷ Earnings per share", "value": "25×", "caption": "$100 share price ÷ $4 of yearly profit per share"},
            {"kind": "bullets", "headline": "How to read it", "items": [
                "High P/E = investors expect fast growth (or it's overhyped)",
                "Low P/E = slow growth, high risk, or a bargain",
                "Compare within the same industry, since banks and software differ a lot",
                "**Forward P/E** uses next year's expected earnings"]},
            {"kind": "text", "headline": "The catch", "body": "P/E breaks when earnings are tiny or negative. For young, unprofitable companies investors use price-to-sales or other measures instead."},
            quiz("Stock A trades at $60 with $3 EPS. What's its P/E?", ["3", "18", "20", "180"], 2, "$60 ÷ $3 = 20. Investors pay $20 for each $1 of annual profit."),
        ],
        "sources": [{"title": "Investopedia: P/E ratio", "url": "https://www.investopedia.com/terms/p/price-earningsratio.asp"}],
    },
    {
        "id": "learn-earnings", "tag": "Stocks 101", "title": "Earnings season: beats, misses & guidance",
        "summary": "Four times a year companies report results. The stock reacts to results versus expectations, and above all to guidance.",
        "scenes": [
            {"kind": "title", "headline": "Why a stock can **drop** after a great quarter", "body": "Earnings season, decoded."},
            {"kind": "bullets", "headline": "What gets reported", "items": [
                "**Revenue**: total sales",
                "**EPS**: profit per share",
                "**Margins**: how much of each sale becomes profit",
                "**Guidance**: what management expects next"]},
            {"kind": "text", "headline": "It's all about expectations", "body": "Analysts publish estimates beforehand. Beating them is good, but if the market quietly expected a **bigger** beat (the \"whisper number\"), the stock can still fall."},
            {"kind": "text", "headline": "Guidance is king", "body": "Stocks are priced on the future. A company that beats this quarter but **lowers its outlook** often sells off hard, while a miss with raised guidance can rally."},
            quiz("A company beats EPS estimates but cuts next quarter's guidance. The stock most likely…", ["Soars", "Falls", "Doesn't move", "Gets delisted"], 1,
                 "Markets look forward. Weaker guidance lowers expected future profits, which usually outweighs a past beat."),
        ],
        "sources": [{"title": "Investopedia: Earnings season", "url": "https://www.investopedia.com/terms/e/earningsseason.asp"}],
    },
    {
        "id": "learn-sp500", "tag": "Markets 101", "title": "What the S&P 500 really is",
        "summary": "The S&P 500 tracks about 500 large US companies, weighted by market value, so the biggest names dominate.",
        "scenes": [
            {"kind": "title", "headline": "\"The market was up today.\" Which market?", "body": "Usually, the **S&P 500**."},
            {"kind": "text", "headline": "500 of America's largest companies", "body": "A committee picks large, profitable US firms across all sectors. It's the most-used benchmark for US stocks."},
            {"kind": "text", "headline": "Weighted by size", "body": "It's **market-cap weighted**: a $3 trillion company moves the index far more than a $30 billion one. Lately the top 10 stocks make up **more than a third** of the whole index."},
            {"kind": "bullets", "headline": "Know the big three", "items": [
                "**S&P 500**: broad large-cap benchmark",
                "**Nasdaq Composite**: tech-heavy, growth-focused",
                "**Dow Jones**: just 30 blue chips, weighted by share *price* (an old quirk)"]},
            quiz("Why can a handful of tech stocks drive most of the S&P 500's move?", ["It's equal-weighted", "It's weighted by market cap", "It only holds tech", "It's price-weighted"], 1,
                 "Bigger companies get bigger weights, so a few giants can dominate daily moves."),
        ],
        "sources": [{"title": "S&P Dow Jones Indices: S&P 500", "url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/"}],
    },
    {
        "id": "learn-vix", "tag": "Markets 101", "title": "The VIX: Wall Street's fear gauge",
        "summary": "The VIX uses options prices to estimate how much traders expect the S&P 500 to swing over the next 30 days.",
        "scenes": [
            {"kind": "title", "headline": "There's an index for **fear**", "body": "It's called the VIX."},
            {"kind": "text", "headline": "How it works", "body": "When traders rush to buy protection (put options), option prices rise. The VIX turns those prices into **expected volatility** for the next 30 days."},
            {"kind": "bars", "headline": "Rough rules of thumb", "unit": "", "mode": "positive",
             "items": [{"label": "Calm", "value": 13, "display": "~12–15"}, {"label": "Normal", "value": 19, "display": "~16–20"}, {"label": "Nervous", "value": 26, "display": "~21–30"}, {"label": "Panic", "value": 40, "display": "30+"}]},
            {"kind": "text", "headline": "Read it backwards", "body": "The VIX usually **rises when stocks fall**. Spikes often happen near market bottoms, when fear peaks. Contrarians sometimes call it a signal to get greedy."},
            quiz("The S&P 500 drops sharply. The VIX usually…", ["Falls", "Rises", "Stays flat", "Stops trading"], 1, "Falling stocks drive demand for protection, which pushes option prices and the VIX higher."),
        ],
        "sources": [{"title": "Cboe: VIX Index", "url": "https://www.cboe.com/tradable_products/vix/"}],
    },
    {
        "id": "learn-dollar", "tag": "Global", "title": "The US dollar and your stocks",
        "summary": "A strong dollar makes US exports pricier and shrinks foreign profits when converted back, which matters for multinationals.",
        "scenes": [
            {"kind": "title", "headline": "A strong dollar isn't always good news", "body": "Here's how currencies hit stock prices."},
            {"kind": "text", "headline": "Meet the DXY", "body": "The **US Dollar Index** measures the dollar against six major currencies, mostly the euro, plus the yen, pound and others."},
            {"kind": "bullets", "headline": "When the dollar rises…", "items": [
                "US companies' **foreign sales** convert back into fewer dollars",
                "US exports get pricier abroad",
                "Emerging markets with dollar debt feel squeezed",
                "Commodities priced in dollars (like oil and gold) often dip"]},
            {"kind": "text", "headline": "Who wins?", "body": "Importers and US travelers abroad. And when the dollar **weakens**, big multinationals like Apple or Coca-Cola often get a boost to reported earnings."},
            quiz("A sharply stronger dollar tends to hurt which companies most?", ["Purely domestic retailers", "US multinationals with big overseas sales", "US importers", "Foreign tourists"], 1,
                 "Overseas revenue converts back into fewer dollars, so reported earnings shrink."),
        ],
        "sources": [{"title": "Investopedia: US Dollar Index", "url": "https://www.investopedia.com/terms/u/usdx.asp"}],
    },
    {
        "id": "learn-oil", "tag": "Global", "title": "How oil prices ripple through the economy",
        "summary": "Oil feeds into transport, manufacturing and consumer budgets. Spikes act like a tax on consumers and can lift inflation.",
        "scenes": [
            {"kind": "title", "headline": "A barrel of oil touches almost everything", "body": "From your gas tank to grocery prices."},
            {"kind": "bullets", "headline": "When oil spikes", "items": [
                "[up]Energy stocks[/up] usually rise",
                "[down]Airlines, truckers, cruise lines[/down] get squeezed",
                "Consumers spend more on gas and less elsewhere",
                "Inflation ticks up, so the Fed stays cautious"]},
            {"kind": "text", "headline": "Who sets the price?", "body": "Global supply and demand: **OPEC+** output decisions, US shale production, Chinese demand, and geopolitical risk in places like the Middle East and Russia."},
            {"kind": "text", "headline": "Two benchmarks", "body": "**WTI** (US crude, priced in Cushing, Oklahoma) and **Brent** (the North Sea global benchmark). They usually move together."},
            quiz("Oil jumps 20% on a supply shock. Which sector is most likely to benefit?", ["Airlines", "Energy producers", "Cruise lines", "Trucking"], 1, "Producers sell their oil at higher prices; transport companies pay more for fuel."),
        ],
        "sources": [{"title": "EIA: What drives crude oil prices", "url": "https://www.eia.gov/finance/markets/crudeoil/"}],
    },
    {
        "id": "learn-jobs-report", "tag": "Macro 101", "title": "The jobs report: the first Friday ritual",
        "summary": "The monthly Employment Situation report shows payroll growth, unemployment and wages, which are key inputs for the Fed.",
        "scenes": [
            {"kind": "title", "headline": "First Friday of the month, 8:30 a.m. ET", "body": "The jobs report drops, and markets move."},
            {"kind": "bullets", "headline": "What's inside", "items": [
                "**Nonfarm payrolls**: jobs added or lost",
                "**Unemployment rate**: share of the labor force looking for work",
                "**Average hourly earnings**: wage growth, a clue to inflation"]},
            {"kind": "text", "headline": "Good news can be bad news", "body": "A blowout jobs number shows a strong economy. But it can also mean the Fed keeps rates **higher for longer**, so stocks sometimes fall on \"good\" news."},
            {"kind": "text", "headline": "Watch the revisions", "body": "Prior months get revised as more data arrives. Big downward revisions can matter as much as the headline."},
            quiz("Why might stocks fall on a much stronger-than-expected jobs report?", ["Strong jobs always hurt profits", "It may mean the Fed keeps rates high", "Unemployment rises", "Wages fall"], 1,
                 "A hot labor market can keep inflation pressure up, delaying rate cuts that markets were hoping for."),
        ],
        "sources": [{"title": "BLS: Employment Situation", "url": "https://www.bls.gov/news.release/empsit.toc.htm"}],
    },
    {
        "id": "learn-gdp", "tag": "Macro 101", "title": "GDP & recessions, explained",
        "summary": "GDP measures the total output of the economy. Recessions are broad, lasting declines in activity, officially dated by the NBER.",
        "scenes": [
            {"kind": "title", "headline": "What actually counts as a recession?", "body": "It's not as simple as you've heard."},
            {"kind": "text", "headline": "GDP = the economy's scoreboard", "body": "Gross Domestic Product is the value of everything produced in the US. It's reported **quarterly** and annualized. About **two-thirds** is consumer spending."},
            {"kind": "text", "headline": "The rule of thumb", "body": "Two straight quarters of shrinking GDP is a popular shorthand for a recession, but it's **not** the official definition."},
            {"kind": "text", "headline": "The official call", "body": "In the US, a committee at the **National Bureau of Economic Research** declares recessions by looking at jobs, income, spending and production, often months after the fact."},
            quiz("Who officially dates US recessions?", ["The Federal Reserve", "The White House", "The NBER", "The stock market"], 2, "The National Bureau of Economic Research's Business Cycle Dating Committee makes the call."),
        ],
        "sources": [{"title": "NBER: Business cycle dating", "url": "https://www.nber.org/research/business-cycle-dating"}],
    },
    {
        "id": "learn-sectors", "tag": "Markets 101", "title": "Cyclical vs. defensive stocks",
        "summary": "Some sectors boom and bust with the economy; others hold up because people buy their products no matter what.",
        "scenes": [
            {"kind": "title", "headline": "Why some stocks hold up in a recession", "body": "Cyclical vs. defensive, in one minute."},
            {"kind": "bullets", "headline": "Cyclical: ride the economy", "items": [
                "Consumer discretionary (cars, travel, retail)", "Industrials & materials", "Financials", "Energy"]},
            {"kind": "bullets", "headline": "Defensive: steady demand", "style": "pros", "items": [
                "Consumer staples (food, toothpaste)", "Utilities", "Healthcare"]},
            {"kind": "text", "headline": "Sector rotation", "body": "Investors shift money between these groups as they change their view of the economy. When defensives lead while the market falls, it's often a **risk-off** signal."},
            quiz("Which sector is typically considered defensive?", ["Airlines", "Utilities", "Semiconductors", "Homebuilders"], 1, "People pay electric and water bills in good times and bad, so utilities' earnings are steadier."),
        ],
        "sources": [{"title": "Investopedia: Cyclical vs. non-cyclical stocks", "url": "https://www.investopedia.com/articles/investing/060315/cyclical-versus-noncyclical-stocks.asp"}],
    },
    {
        "id": "learn-compounding", "tag": "Investing", "title": "Compounding: the 8th wonder",
        "summary": "Returns that earn their own returns grow exponentially. Time in the market is the biggest lever.",
        "scenes": [
            {"kind": "title", "headline": "$10,000. 7% a year. Do nothing.", "body": "What happens after 30 years?"},
            {"kind": "chart", "headline": "Growth of $10,000 at 7%/yr", "label": "Years 0 → 30", "last": f"${compound[-1]:,}",
             "change": round((compound[-1] / compound[0] - 1) * 100, 0), "points": compound, "dates": ["Year 0", "Year 30"],
             "note": f"It's about **${compound[10]:,}** after 10 years and **${compound[20]:,}** after 20, then the curve bends sharply upward."},
            {"kind": "text", "headline": "The Rule of 72", "body": "Divide 72 by your annual return to estimate years to double. At 7%, money doubles roughly every **10 years**. At 10%, every **7**."},
            {"kind": "text", "headline": "The lesson", "body": "Starting early matters more than picking the perfect stock. Fees and taxes compound too, **against** you."},
            quiz("Using the Rule of 72, how long does money take to double at 9% a year?", ["4 years", "8 years", "12 years", "18 years"], 1, "72 ÷ 9 = 8 years."),
        ],
        "sources": [{"title": "Investor.gov: Compound interest calculator", "url": "https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator"}],
    },
    {
        "id": "learn-etfs", "tag": "Investing", "title": "Index funds & ETFs",
        "summary": "ETFs let you buy a whole basket of stocks in one trade, cheaply and with instant diversification.",
        "scenes": [
            {"kind": "title", "headline": "Own 500 companies with one click", "body": "That's what an index ETF does."},
            {"kind": "text", "headline": "What's an ETF?", "body": "An **exchange-traded fund** holds a basket of assets and trades like a single stock. An S&P 500 ETF owns every company in the index."},
            {"kind": "bullets", "headline": "Why investors love them", "style": "pros", "items": [
                "Instant diversification: one bad stock can't sink you",
                "Very low fees (some under 0.05% a year)", "Trade any time the market is open"]},
            {"kind": "text", "headline": "The tough truth", "body": "Over long periods, most actively managed funds **trail** their index benchmark after fees. That's the case for passive investing."},
            quiz("The main benefit of a broad index ETF is…", ["Guaranteed returns", "Diversification at low cost", "Avoiding all losses", "Beating the market"], 1, "You spread risk across many companies for a small fee, but you still ride market ups and downs."),
        ],
        "sources": [{"title": "Investor.gov: ETFs", "url": "https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-0"}],
    },
    {
        "id": "learn-dividends-buybacks", "tag": "Stocks 101", "title": "Dividends vs. buybacks",
        "summary": "Two ways companies return cash to shareholders: paying it out directly, or shrinking the share count.",
        "scenes": [
            {"kind": "title", "headline": "A company made a profit. Now what?", "body": "Two ways to hand the cash back to you."},
            {"kind": "text", "headline": "Dividends", "body": "Cash paid directly to shareholders, usually **quarterly**. The **dividend yield** = annual dividend ÷ share price. A $100 stock paying $3 a year yields 3%."},
            {"kind": "text", "headline": "Buybacks", "body": "The company buys its own shares and retires them. Fewer shares means each remaining share owns a bigger slice, so **EPS rises** even if profit doesn't."},
            {"kind": "bullets", "headline": "Watch out for", "style": "cons", "items": [
                "Very high yields can signal a dividend cut is coming",
                "Buybacks at sky-high prices can destroy value",
                "Borrowing to fund either one can weaken the balance sheet"]},
            quiz("A $50 stock pays $2 per year in dividends. Its yield is…", ["2%", "4%", "25%", "50%"], 1, "$2 ÷ $50 = 4%."),
        ],
        "sources": [{"title": "Investor.gov: Dividends", "url": "https://www.investor.gov/introduction-investing/investing-basics/glossary/dividend"}],
    },
    {
        "id": "learn-fcf", "tag": "Valuation", "title": "Free cash flow: the number pros trust",
        "summary": "Free cash flow is the cash a business generates after paying to maintain and grow its assets. It's harder to fudge than earnings.",
        "scenes": [
            {"kind": "title", "headline": "Profits are an opinion. Cash is a fact.", "body": "Meet free cash flow."},
            {"kind": "number", "headline": "The formula", "value": "OCF − CapEx", "caption": "Operating cash flow minus capital expenditures"},
            {"kind": "text", "headline": "Why it matters", "body": "Accounting earnings involve judgment calls. FCF is the actual cash left over, which pays dividends, buybacks, acquisitions and debt."},
            {"kind": "text", "headline": "FCF yield", "body": "FCF ÷ market cap. A 5% FCF yield means the business generates cash equal to 5% of its price each year, a handy way to compare valuations."},
            quiz("A company has $10B operating cash flow and $4B capex. Its free cash flow is…", ["$14B", "$6B", "$4B", "$2.5B"], 1, "$10B − $4B = $6B of free cash flow."),
        ],
        "sources": [{"title": "Investopedia: Free cash flow", "url": "https://www.investopedia.com/terms/f/freecashflow.asp"}],
    },
    {
        "id": "learn-moats", "tag": "Stocks 101", "title": "Economic moats: why great companies stay great",
        "summary": "A moat is a durable competitive advantage that protects profits from competitors.",
        "scenes": [
            {"kind": "title", "headline": "Warren Buffett's favorite word: **moat**", "body": "What makes a business hard to beat?"},
            {"kind": "bullets", "headline": "The 5 classic moats", "items": [
                "**Network effects**: more users make it more valuable (Visa, marketplaces)",
                "**Switching costs**: painful to leave (enterprise software)",
                "**Brand / intangibles**: patents, licenses, loyalty",
                "**Cost advantage**: cheapest producer at scale (Costco)",
                "**Efficient scale**: niche markets that only support a few players"]},
            {"kind": "text", "headline": "Why it matters for stocks", "body": "Wide-moat companies can keep high returns on capital for decades. That's why investors often pay premium valuations for them."},
            quiz("A business software tool that's painful for customers to replace has which moat?", ["Network effect", "Switching costs", "Cost advantage", "Efficient scale"], 1, "Retraining staff and migrating data makes customers reluctant to leave."),
        ],
        "sources": [{"title": "Morningstar: Economic moats", "url": "https://www.morningstar.com/stocks/what-is-economic-moat"}],
    },
    {
        "id": "learn-risk-on-off", "tag": "Markets 101", "title": "Risk-on vs. risk-off",
        "summary": "Markets swing between appetite for risk and a rush to safety. Spotting which mode you're in explains a lot of daily moves.",
        "scenes": [
            {"kind": "title", "headline": "Why does everything move together some days?", "body": "Markets have two moods."},
            {"kind": "bullets", "headline": "Risk-on 🟢", "style": "pros", "items": ["Stocks up, especially tech and small caps", "High-yield bonds and crypto rally", "VIX falls"]},
            {"kind": "bullets", "headline": "Risk-off 🔴", "style": "cons", "items": ["Stocks fall, defensives outperform", "Treasuries, gold, yen and the dollar often rise", "VIX spikes"]},
            {"kind": "text", "headline": "Use it", "body": "When stocks drop, check the rest: if bonds and gold rally and the VIX jumps, it's a broad flight to safety, not just one company's bad news."},
            quiz("Which asset tends to rise on a risk-off day?", ["Small-cap stocks", "Bitcoin", "US Treasuries", "Junk bonds"], 2, "Investors flee to safe havens like Treasuries, pushing their prices up and yields down."),
        ],
        "sources": [{"title": "Investopedia: Risk-on risk-off", "url": "https://www.investopedia.com/terms/r/risk-on-risk-off.asp"}],
    },
    {
        "id": "learn-short-selling", "tag": "Stocks 101", "title": "Short selling & short squeezes",
        "summary": "Shorting is betting a stock will fall. When shorts rush to cover, prices can spike violently.",
        "scenes": [
            {"kind": "title", "headline": "How do you profit when a stock **falls**?", "body": "You short it. Here's how that works and how it backfires."},
            {"kind": "bullets", "headline": "Short selling, step by step", "items": [
                "Borrow shares from a broker and sell them at $100",
                "Wait for the price to drop to $70",
                "Buy them back and return them, keeping $30"]},
            {"kind": "text", "headline": "The danger", "body": "A stock can only fall to $0, but it can rise **without limit**. Short sellers face theoretically unlimited losses."},
            {"kind": "text", "headline": "The squeeze", "body": "If a heavily shorted stock jumps, shorts scramble to buy back shares, which pushes the price even higher. GameStop in January 2021 is the famous example."},
            quiz("What's the maximum loss on a short position?", ["The share price", "Zero", "Theoretically unlimited", "Half the price"], 2, "There's no ceiling on how high a stock can rise, so losses on a short have no hard limit."),
        ],
        "sources": [{"title": "Investor.gov: Short sales", "url": "https://www.investor.gov/introduction-investing/investing-basics/glossary/short-sale"}],
    },
    {
        "id": "learn-market-cap", "tag": "Stocks 101", "title": "Share price vs. market cap",
        "summary": "A high share price doesn't make a company big. Market cap, price times shares outstanding, does.",
        "scenes": [
            {"kind": "title", "headline": "Is a $900 stock 'bigger' than a $90 one?", "body": "Not necessarily."},
            {"kind": "number", "headline": "Market cap", "value": "Price × Shares", "caption": "The total value the market puts on a company"},
            {"kind": "stats", "headline": "Example", "items": [
                {"label": "Company A", "value": "$900", "note": "100M shares → $90B"},
                {"label": "Company B", "value": "$90", "note": "5B shares → $450B"}],
             "body": "Company B is **5× bigger** despite a share price one-tenth as high."},
            {"kind": "text", "headline": "Stock splits change nothing", "body": "A 10-for-1 split turns one $900 share into ten $90 shares. The company's value is identical; it just looks cheaper."},
            quiz("After a 4-for-1 stock split, a company's market cap…", ["Quadruples", "Falls by 75%", "Stays the same", "Doubles"], 2, "There are 4× the shares at ¼ the price, so the total value is unchanged."),
        ],
        "sources": [{"title": "Investor.gov: Market capitalization", "url": "https://www.investor.gov/introduction-investing/investing-basics/glossary/market-capitalization"}],
    },
    {
        "id": "learn-corrections", "tag": "Markets 101", "title": "Corrections, bear markets & bull markets",
        "summary": "Market drawdowns have names based on how far prices fall from a recent peak.",
        "scenes": [
            {"kind": "title", "headline": "Stocks are down 12%. Is it a crash?", "body": "Here's the official lingo."},
            {"kind": "bars", "headline": "Drop from recent peak", "unit": "%",
             "items": [{"label": "Pullback", "value": -5, "display": "−5%"}, {"label": "Correction", "value": -10, "display": "−10%"}, {"label": "Bear market", "value": -20, "display": "−20%"}]},
            {"kind": "text", "headline": "And a bull market?", "body": "A rise of **20% or more** from a recent low. Historically, bull markets have lasted much longer than bear markets."},
            {"kind": "text", "headline": "Perspective", "body": "Corrections are normal; the S&P 500 has seen one every year or two on average. Selling in a panic often locks in losses right before recoveries."},
            quiz("The S&P 500 falls 22% from its high. That's a…", ["Pullback", "Correction", "Bear market", "Bull market"], 2, "A decline of 20% or more from a peak is the common definition of a bear market."),
        ],
        "sources": [{"title": "Investopedia: Bear market", "url": "https://www.investopedia.com/terms/b/bearmarket.asp"}],
    },
    {
        "id": "learn-candlesticks", "tag": "Charts", "title": "How to read a candlestick",
        "summary": "Each candle shows four prices for a period: open, high, low and close.",
        "scenes": [
            {"kind": "title", "headline": "Those red and green bars? They're candlesticks.", "body": "Each one tells a story about a trading day."},
            {"kind": "bullets", "headline": "Anatomy of a candle", "items": [
                "**Body**: the range between open and close",
                "**Green** = closed higher than it opened; **red** = closed lower",
                "**Wicks**: the day's high and low"]},
            {"kind": "text", "headline": "Reading the wicks", "body": "A long lower wick means sellers pushed the price down but buyers fought it back, a possible sign of support. A long upper wick shows rejection at higher prices."},
            {"kind": "text", "headline": "Keep it in context", "body": "Candle patterns are clues, not crystal balls. Volume and the bigger trend matter more than any single candle."},
            quiz("A green candle means the price…", ["Closed above the open", "Closed below the open", "Hit a record high", "Had high volume"], 0, "Green (or hollow) candles close higher than they opened for that period."),
        ],
        "sources": [{"title": "Investopedia: Candlestick charts", "url": "https://www.investopedia.com/trading/candlestick-charting-what-is-it/"}],
    },
    {
        "id": "learn-tariffs", "tag": "Global", "title": "Tariffs & trade wars, explained",
        "summary": "Tariffs are taxes on imports. They can protect domestic industries but raise costs and invite retaliation.",
        "scenes": [
            {"kind": "title", "headline": "Who actually pays a tariff?", "body": "Spoiler: usually not the foreign country."},
            {"kind": "text", "headline": "What it is", "body": "A tariff is a **tax on imported goods**, paid by the importing company when goods cross the border. Costs are often passed on to customers."},
            {"kind": "bullets", "headline": "Market effects", "items": [
                "Companies with global supply chains face higher costs and margin pressure",
                "Some domestic producers gain pricing power",
                "Retaliation can hit exporters (farm goods, chips, aircraft)",
                "Uncertainty itself can weigh on business investment"]},
            {"kind": "text", "headline": "What to watch", "body": "Which countries and products are targeted, exemptions, and how companies talk about tariff costs on earnings calls."},
            quiz("A US tariff on imported steel is paid directly by…", ["The foreign government", "The US company importing the steel", "US taxpayers via income tax", "The Federal Reserve"], 1, "The importer pays the duty at the border, then often passes some of the cost on."),
        ],
        "sources": [{"title": "Investopedia: Tariffs", "url": "https://www.investopedia.com/terms/t/tariff.asp"}],
    },
    {
        "id": "learn-dca", "tag": "Investing", "title": "Dollar-cost averaging",
        "summary": "Investing a fixed amount on a schedule buys more shares when prices are low and fewer when high.",
        "scenes": [
            {"kind": "title", "headline": "Don't know when to buy? Don't pick.", "body": "Dollar-cost averaging takes timing off the table."},
            {"kind": "chart", "headline": "$100 a month into a bumpy stock", "label": "Price over 10 months", "last": "$60", "change": 20.0,
             "points": dca_prices, "dates": ["Month 1", "Month 10"],
             "note": f"$1,000 invested buys **{dca_shares:.1f} shares**, an average cost of **${1000 / dca_shares:.2f}**, below the ${sum(dca_prices) / len(dca_prices):.2f} average price, because you bought more shares when it was cheap."},
            {"kind": "text", "headline": "Why it works for humans", "body": "It removes the urge to time the market and turns dips into automatic bargains. It's how most people invest through workplace retirement plans."},
            quiz("With dollar-cost averaging, when the price drops you…", ["Buy fewer shares", "Buy more shares with the same dollars", "Stop investing", "Sell everything"], 1, "A fixed dollar amount buys more shares at lower prices."),
        ],
        "sources": [{"title": "FINRA: Dollar-cost averaging", "url": "https://www.finra.org/investors/insights/dollar-cost-averaging"}],
    },
]


# Per lesson: illustration + a fill-in-the-blank "key takeaway" (Imprint-style recall), inserted before the quiz.
EXTRAS = {
    "learn-fed-rates": ("fed", "Higher interest rates shrink the value of ___ profits, which hits growth stocks hardest.", ["future", "past", "foreign"], 0),
    "learn-cpi": ("basket", "Markets react to the ___ versus forecasts, not the inflation number itself.", ["surprise", "average", "headline"], 0),
    "learn-yield-curve": ("bonds", "When short-term yields are above long-term yields, the curve is ___.", ["inverted", "steep", "flat-lined"], 0),
    "learn-bond-math": ("bonds", "When market yields rise, existing bond prices ___.", ["fall", "rise", "don't change"], 0),
    "learn-pe-ratio": ("magnifier", "P/E tells you how many dollars investors pay for each $1 of ___.", ["earnings", "revenue", "debt"], 0),
    "learn-earnings": ("chart", "Because stocks are priced on the future, ___ often matters more than last quarter's results.", ["guidance", "dividends", "the logo"], 0),
    "learn-sp500": ("chart", "The S&P 500 is weighted by ___, so the biggest companies move it most.", ["market cap", "share price", "age"], 0),
    "learn-vix": ("shield", "The VIX usually ___ when stocks fall.", ["rises", "falls", "stays flat"], 0),
    "learn-dollar": ("coins", "A stronger dollar shrinks the ___ profits of US multinationals.", ["overseas", "domestic", "pretax"], 0),
    "learn-oil": ("oil", "Higher oil prices help ___ but hurt airlines and truckers.", ["energy producers", "cruise lines", "retailers"], 0),
    "learn-jobs-report": ("jobs", "A very hot jobs report can hurt stocks if it keeps the Fed's rates ___.", ["higher for longer", "at zero", "negative"], 0),
    "learn-gdp": ("factory", "About two-thirds of US GDP comes from ___ spending.", ["consumer", "government", "export"], 0),
    "learn-sectors": ("shield", "Utilities, staples and healthcare are ___ sectors that hold up in downturns.", ["defensive", "cyclical", "speculative"], 0),
    "learn-compounding": ("rocket", "By the Rule of 72, money earning 7% a year doubles about every ___ years.", ["10", "5", "20"], 0),
    "learn-etfs": ("basket", "An index ETF gives you instant ___ at a very low cost.", ["diversification", "guaranteed returns", "leverage"], 0),
    "learn-dividends-buybacks": ("coins", "Buybacks reduce the share count, which raises ___ per share.", ["earnings", "debt", "revenue"], 0),
    "learn-fcf": ("coins", "Free cash flow = operating cash flow minus ___.", ["capital expenditures", "dividends", "taxes"], 0),
    "learn-moats": ("shield", "A durable competitive advantage that protects profits is called a ___.", ["moat", "hedge", "float"], 0),
    "learn-risk-on-off": ("globe", "On risk-off days, investors flee to safe havens like ___.", ["Treasuries", "small caps", "crypto"], 0),
    "learn-short-selling": ("rocket", "A short seller profits when the stock price ___.", ["falls", "rises", "splits"], 0),
    "learn-market-cap": ("magnifier", "Market cap = share price × ___.", ["shares outstanding", "earnings", "dividends"], 0),
    "learn-corrections": ("chart", "A drop of 20% or more from a peak is called a ___ market.", ["bear", "bull", "flat"], 0),
    "learn-candlesticks": ("chart", "A green candle means the price closed ___ than it opened.", ["higher", "lower", "the same"], 0),
    "learn-tariffs": ("ship", "A tariff is a tax on ___ goods.", ["imported", "exported", "luxury"], 0),
    "learn-dca": ("calendar", "Dollar-cost averaging buys ___ shares when prices are low.", ["more", "fewer", "no"], 0),
}

# Imprint-style courses: short chapters in a deliberate order, with progress tracked in the app.
COURSES = [
    {"id": "macro", "title": "How the Economy Moves Markets", "art": "fed", "hue": 268,
     "desc": "The Fed, inflation, jobs and growth: the forces behind every big market day.",
     "lessons": ["learn-fed-rates", "learn-cpi", "learn-jobs-report", "learn-gdp", "learn-yield-curve"]},
    {"id": "stocks", "title": "Stocks 101", "art": "chart", "hue": 212,
     "desc": "What you actually own, how indices work and why prices move.",
     "lessons": ["learn-sp500", "learn-market-cap", "learn-earnings", "learn-dividends-buybacks", "learn-short-selling", "learn-candlesticks"]},
    {"id": "valuation", "title": "Valuing a Company", "art": "magnifier", "hue": 150,
     "desc": "Tell a great business from a great stock: P/E, cash flow and moats.",
     "lessons": ["learn-pe-ratio", "learn-fcf", "learn-moats", "learn-sectors"]},
    {"id": "global", "title": "Global Markets & Money", "art": "globe", "hue": 32,
     "desc": "Bonds, the dollar, oil and trade: how the world connects to Wall Street.",
     "lessons": ["learn-bond-math", "learn-dollar", "learn-oil", "learn-tariffs", "learn-risk-on-off", "learn-vix"]},
    {"id": "investing", "title": "Investing for the Long Run", "art": "rocket", "hue": 188,
     "desc": "Compounding, index funds and riding out the drops.",
     "lessons": ["learn-compounding", "learn-etfs", "learn-dca", "learn-corrections"]},
]


if __name__ == "__main__":
    for lesson in LESSONS:
        lesson.setdefault("category", "learn")
        art, text, options, answer = EXTRAS[lesson["id"]]
        lesson["art"] = art
        lesson["scenes"].insert(len(lesson["scenes"]) - 1, {"kind": "blank", "text": text, "options": options, "answer": answer})
    ids = {lesson["id"] for lesson in LESSONS}
    assert all(i in ids for c in COURSES for i in c["lessons"]), "course references a missing lesson"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"courses": COURSES, "reels": LESSONS}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(LESSONS)} lessons in {len(COURSES)} courses to {OUT}")
