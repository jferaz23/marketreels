"""What the pipeline tracks. Edit these lists to change what shows up in the feed."""

INDICES = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^DJI": "Dow", "^RUT": "Russell 2000"}
FUTURES = {"ES=F": "S&P futures", "NQ=F": "Nasdaq futures", "YM=F": "Dow futures"}
VOLATILITY = {"^VIX": "VIX"}
# Yahoo quotes these Treasury yields in percent (4.25 = 4.25%).
YIELDS = {"^IRX": "3-month", "^FVX": "5-year", "^TNX": "10-year", "^TYX": "30-year"}
ASSETS = {"DX-Y.NYB": "US dollar", "CL=F": "Crude oil", "GC=F": "Gold", "BTC-USD": "Bitcoin"}
GLOBAL = {
    "^STOXX50E": "Euro Stoxx 50", "^FTSE": "UK FTSE 100", "^GDAXI": "Germany DAX",
    "^N225": "Japan Nikkei", "^HSI": "Hong Kong", "000001.SS": "Shanghai", "^BSESN": "India Sensex",
}
SECTORS = {
    "XLK": "Tech", "XLC": "Comm. Services", "XLY": "Discretionary", "XLF": "Financials",
    "XLI": "Industrials", "XLE": "Energy", "XLB": "Materials", "XLV": "Healthcare",
    "XLP": "Staples", "XLU": "Utilities", "XLRE": "Real Estate",
}
CYCLICAL = {"XLK", "XLY", "XLF", "XLI", "XLB", "XLC"}
DEFENSIVE = {"XLU", "XLP", "XLV"}

# Large, liquid US stocks used for movers and stock spotlights. Second value = names to match in headlines.
WATCHLIST = {
    "AAPL": ("Apple", ["Apple", "iPhone"]), "MSFT": ("Microsoft", ["Microsoft"]), "NVDA": ("Nvidia", ["Nvidia"]),
    "AMZN": ("Amazon", ["Amazon", "AWS"]), "GOOGL": ("Alphabet", ["Alphabet", "Google"]), "META": ("Meta", ["Meta", "Facebook", "Instagram"]),
    "TSLA": ("Tesla", ["Tesla", "Musk"]), "AVGO": ("Broadcom", ["Broadcom"]), "BRK-B": ("Berkshire Hathaway", ["Berkshire", "Buffett"]),
    "JPM": ("JPMorgan", ["JPMorgan", "Jamie Dimon"]), "LLY": ("Eli Lilly", ["Eli Lilly", "Lilly"]), "V": ("Visa", ["Visa"]),
    "MA": ("Mastercard", ["Mastercard"]), "UNH": ("UnitedHealth", ["UnitedHealth"]), "XOM": ("Exxon Mobil", ["Exxon"]),
    "COST": ("Costco", ["Costco"]), "WMT": ("Walmart", ["Walmart"]), "HD": ("Home Depot", ["Home Depot"]),
    "PG": ("Procter & Gamble", ["Procter"]), "JNJ": ("Johnson & Johnson", ["Johnson & Johnson", "J&J"]),
    "NFLX": ("Netflix", ["Netflix"]), "AMD": ("AMD", ["AMD", "Advanced Micro"]), "CRM": ("Salesforce", ["Salesforce"]),
    "ORCL": ("Oracle", ["Oracle"]), "BAC": ("Bank of America", ["Bank of America"]), "GS": ("Goldman Sachs", ["Goldman"]),
    "KO": ("Coca-Cola", ["Coca-Cola", "Coke"]), "PEP": ("PepsiCo", ["PepsiCo", "Pepsi"]), "DIS": ("Disney", ["Disney"]),
    "INTC": ("Intel", ["Intel"]), "MU": ("Micron", ["Micron"]), "PLTR": ("Palantir", ["Palantir"]),
    "UBER": ("Uber", ["Uber"]), "COIN": ("Coinbase", ["Coinbase"]), "CAT": ("Caterpillar", ["Caterpillar"]),
    "BA": ("Boeing", ["Boeing"]), "NKE": ("Nike", ["Nike"]), "SBUX": ("Starbucks", ["Starbucks"]),
    "MCD": ("McDonald's", ["McDonald"]), "PFE": ("Pfizer", ["Pfizer"]), "MRK": ("Merck", ["Merck"]),
    "ADBE": ("Adobe", ["Adobe"]), "QCOM": ("Qualcomm", ["Qualcomm"]), "TSM": ("TSMC", ["TSMC", "Taiwan Semiconductor"]),
    "SHOP": ("Shopify", ["Shopify"]), "ABNB": ("Airbnb", ["Airbnb"]), "GE": ("GE Aerospace", ["GE Aerospace"]),
    "LMT": ("Lockheed Martin", ["Lockheed"]), "CVX": ("Chevron", ["Chevron"]), "T": ("AT&T", ["AT&T"]),
}

# Free RSS feeds (no paywalls). Weight is a relevance bonus applied to that feed's headlines.
NEWS_FEEDS = [
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", 2),
    ("CNBC Markets", "https://www.cnbc.com/id/15839069/device/rss/rss.html", 3),
    ("CNBC Economy", "https://www.cnbc.com/id/20910258/device/rss/rss.html", 3),
    ("CNBC Earnings", "https://www.cnbc.com/id/15839135/device/rss/rss.html", 3),
    ("CNBC World", "https://www.cnbc.com/id/100727362/device/rss/rss.html", 1),
    ("Investing.com", "https://www.investing.com/rss/news_25.rss", 2),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", 0),
    ("The Guardian", "https://www.theguardian.com/business/rss", 0),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml", 1),
]

# Topic detection for news reels: keywords -> why-it-matters explainer and the related lesson.
TOPICS = [
    {"id": "fed", "keys": ["fed ", "federal reserve", "powell", "fomc", "rate cut", "rate hike", "interest rate"],
     "why": "Fed policy sets the price of money. Rate expectations move bond yields, the dollar and stock valuations, especially for growth stocks.",
     "lesson": "learn-fed-rates", "media": "federal reserve building", "category": "macro"},
    {"id": "inflation", "keys": ["inflation", "cpi", "consumer price", "pce", "prices rose", "price index"],
     "why": "Inflation drives the Fed's next move. Hotter readings usually push yields up and pressure stock prices.",
     "lesson": "learn-cpi", "media": "grocery store shopping", "category": "macro"},
    {"id": "jobs", "keys": ["jobs report", "payroll", "unemployment", "jobless", "labor market", "hiring", "layoffs"],
     "why": "The job market shows how strong the economy is, and it's half of the Fed's mandate.",
     "lesson": "learn-jobs-report", "media": "office workers city", "category": "macro"},
    {"id": "growth", "keys": ["gdp", "recession", "economy", "economic growth", "consumer spending", "retail sales"],
     "why": "Economic growth drives corporate profits. Signs of a slowdown can push investors toward defensive stocks and bonds.",
     "lesson": "learn-gdp", "media": "city skyline aerial", "category": "macro"},
    {"id": "trade", "keys": ["tariff", "trade war", "trade deal", "export", "import", "sanction"],
     "why": "Trade policy changes costs for companies with global supply chains and can trigger retaliation against US exporters.",
     "lesson": "learn-tariffs", "media": "shipping containers port", "category": "macro"},
    {"id": "oil", "keys": ["oil", "opec", "crude", "gasoline", "energy prices", "natural gas"],
     "why": "Energy prices feed into inflation and consumer budgets, while lifting energy producers' profits.",
     "lesson": "learn-oil", "media": "oil rig ocean", "category": "macro"},
    {"id": "bonds", "keys": ["treasury", "yields", "bond market", "10-year", "debt ceiling", "deficit"],
     "why": "Treasury yields are the market's benchmark 'risk-free' rate. When they jump, stocks have to work harder to compete.",
     "lesson": "learn-bond-math", "media": "us capitol building", "category": "macro"},
    {"id": "earnings", "keys": ["earnings", "revenue", "quarterly results", "profit", "guidance", "outlook", "beats", "misses"],
     "why": "Earnings are what stock prices ultimately follow. The market reacts to results versus expectations, and above all to guidance.",
     "lesson": "learn-earnings", "media": "stock market trading screen", "category": "news"},
    {"id": "china", "keys": ["china", "beijing", "yuan", "hong kong", "xi jinping"],
     "why": "China is a huge market and supplier for US companies, so its economy and policy decisions ripple into US stocks.",
     "lesson": "learn-tariffs", "media": "shanghai skyline night", "category": "macro"},
    {"id": "ai", "keys": [" ai ", "artificial intelligence", "chip", "semiconductor", "data center", "gpu"],
     "why": "AI spending has been one of the market's biggest themes, so chip and cloud news can move the heaviest stocks in the index.",
     "lesson": "learn-sp500", "media": "data center servers", "category": "news"},
    {"id": "crypto", "keys": ["bitcoin", "crypto", "ethereum", "stablecoin"],
     "why": "Crypto often trades as a high-risk asset, so its swings can be a read on investors' appetite for risk.",
     "lesson": "learn-risk-on-off", "media": "bitcoin cryptocurrency", "category": "news"},
    {"id": "dollar", "keys": ["dollar", "currency", "yen", "euro"],
     "why": "Currency moves change what US multinationals earn abroad and what imports cost at home.",
     "lesson": "learn-dollar", "media": "currency exchange money", "category": "macro"},
]

# Headlines with these words are usually off-topic for a markets feed.
NEWS_BLOCKLIST = ["horoscope", "recipe", "celebrity", "football", "soccer", "nfl", "nba", "premier league", "royal", "podcast:", "quiz:", "watch live", "pictures:", "in pictures"]
