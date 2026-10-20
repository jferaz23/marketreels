# MarketReels

TikTok-style reels for learning the US stock market: daily market recaps, macro and global events, news explainers and stock ideas, plus Imprint-style courses on finance fundamentals. It installs on your phone like an app and is **100% free**: no paid APIs, no API keys required, no subscriptions.

## What's in it

| Tab | What it is |
|---|---|
| **For You** | Full-screen reels you swipe through. Scenes auto-advance like stories; tap right/left to skip, hold to pause, turn on narration to listen hands-free. Ranked by your ratings, with lessons mixed in. |
| **Dashboard** | Live board: US indexes, index futures, Treasury yields + the official yield curve (2s10s, 3m10y), commodities, the dollar and major currencies, crypto, global markets and S&P sectors, with intraday mini charts. Tap a row for its chart and headlines. |
| **PA** | Your own stocks with live daily moves. Add shares and cost to see value, today's P&L and total gain. Shows upcoming earnings and the latest headlines on your names. Saved on your device. |
| **Calendar** | FOMC meetings with each decision once announced, US and global data releases (actual vs. consensus), large-company earnings, the midterms, market holidays and options expiration. |
| **Scroll** | The same content as a normal free-scrolling feed of cards, to read at your own pace. Pull down to refresh. |
| **Markets / Macro / News / Stock Ideas** | Today's reels by section. |
| **Learn** | 5 courses, 25 two-minute chapters, each with a fill-in-the-blank takeaway and a quiz. Progress is tracked. |
| **Saved** | Anything you bookmarked. |

On every reel and card:
- **👍 / 😐 / 👎**: rate it. For You and Scroll re-rank around your ratings, and dislikes disappear. Tap the progress pill (top right) to see **Your taste** and copy your ratings as JSON.
- **Ask**: opens Claude with the reel and your question filled in (see below). Free.
- Daily goal (5 reels), day streak 🔥 and XP ⚡ from quizzes.

**Experience level** (Settings): *Experienced* (default) leads with market updates, skips beginner explainer scenes and shows a lesson only every ~6 reels. *New to markets* explains everything.

## Live prices

The pill at the left of the ticker tape shows how fresh prices are: **● Live**, **N min ago**, **Pre-market**, **After hours** or **Closed**. Tap it to refresh. Prices on the tape, today's number tiles, chart labels and stock chips (`$NVDA`) update in place. Reels from earlier days keep their original numbers.

| Hosting | How fresh | How |
|---|---|---|
| **Vercel** (recommended) | Live: a few seconds behind the market (Yahoo; futures about 10 minutes) | `api/quotes.js` relays Yahoo Finance; the app polls every 30s while open |
| **GitHub Pages** | About every 15 minutes in market hours | The *Refresh quotes* workflow rewrites `data/quotes.json` and redeploys |

The narrative text in a reel (for example "S&P 500 is up 0.4%") is written when the reel is generated: before the open, at midday and after the close. When newer reels exist, a **✨ New reels** button appears.

## Ask Claude (free)

**Ask** shows suggested questions plus a text box. Asking opens Claude (claude.ai, or the Claude app on your phone) with the reel's content and your question filled in, using your own Claude account. The app contains no API key and no server for this, so a question can never cost you anything. The question is also copied to your clipboard in case the prefill doesn't load.

## How it works

```
GitHub Actions (free on public repos)                Your phone
  Update feed: 3×/weekday + Saturday                   index.html + assets/app.js
   pipeline/build_feed.py                              reads data/feed.json, data/lessons.json
    ├─ Yahoo Finance prices + live quotes              live prices: api/quotes (Vercel)
    ├─ FRED economic data (public CSV), BLS API as backup
    ├─ Calendar: Federal Reserve (FOMC dates + statements),
    │   Nasdaq economic & earnings calendars, US Treasury yield curve                   or data/quotes.json (Pages)
    ├─ Free RSS news: CNBC, BBC, Guardian,
    │   Investing.com, Federal Reserve
    └─ writes data/feed.json + quotes.json → commit → deploy
  Refresh quotes: every 15 min in market hours (Pages only)
```

The app is plain HTML/CSS/JS with no build step and no dependencies.

## Cost: free

| Piece | Cost |
|---|---|
| GitHub repo, Actions, Pages | Free for public repos |
| Vercel Hobby plan | Free. If usage limits were ever exceeded, Vercel pauses the project instead of billing you. This app uses a tiny fraction of the limits. |
| Market data, live quotes, news, economic data | Free, no keys, no paywalled sources |
| Ask Claude | Free, using your own Claude account |
| Pexels video backgrounds (optional) | Free API key |

## Set up

### 1. GitHub
The repository is public so Actions and Pages stay free. In **Settings → Pages**, *Source* must be **GitHub Actions**. Then go to **Actions → Update feed → Run workflow** for the first build.

The site is at `https://<username>.github.io/<repo>/`.

### 2. Optional: Vercel for live prices (about 3 minutes, free)
1. At vercel.com, sign up with GitHub on the **Hobby** plan (no card needed) → **Add New → Project** → import this repo → **Deploy**. Leave all build settings empty.
2. In GitHub: **Settings → Secrets and variables → Actions → Variables** → add `HOSTING` = `vercel`. This turns off the GitHub Pages jobs; Actions keeps refreshing the reels, and Vercel redeploys on each feed commit.
3. Use the Vercel URL on your phone.

### 3. Optional: video backgrounds
Get a free key at pexels.com/api and add it as the repository **secret** `PEXELS_API_KEY`.

### 4. Install on your phone
- **iPhone:** open the site in Safari → Share → **Add to Home Screen**.
- **Android:** open it in Chrome → ⋮ → **Install app**.

## Customize
- **Stocks, sectors, news feeds, topics:** `pipeline/config.py`
- **Reel templates and wording:** `pipeline/reels.py`
- **Courses and lessons:** `tools/build_lessons.py`, then run `python tools/build_lessons.py`
- **Schedules:** `.github/workflows/*.yml` (times are UTC)

Run locally:
```bash
pip install -r pipeline/requirements.txt
python pipeline/build_feed.py
python tools/dev_server.py
```
Then open http://localhost:8000 (live prices included).

## Notes
- Yahoo Finance data is unofficial and may occasionally lag or be unavailable. The app then falls back to the last saved prices and says how old they are.
- Stock ideas are data-driven educational write-ups with a bull and a bear case. They are not recommendations.
- GitHub pauses scheduled workflows in repos with no activity for 60 days. If that happens, click **Enable workflow** on the Actions tab.
- Your ratings, progress and saved reels live in your phone's browser storage. Clearing site data resets them.
