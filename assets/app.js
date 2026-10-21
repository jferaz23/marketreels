/* MarketReels: a swipeable, TikTok-style feed of market lessons, plus a free-scroll reader and Imprint-style courses.
   No build step and no dependencies, so it can be served straight from GitHub Pages or Vercel. */
(() => {
  'use strict';

  const CATEGORIES = {
    markets: { label: 'Markets', hue: 212 },
    macro: { label: 'Macro', hue: 268 },
    news: { label: 'News', hue: 32 },
    ideas: { label: 'Ideas', hue: 150 },
    learn: { label: 'Learn', hue: 188 },
    video: { label: 'Video', hue: 350 },
  };
  const TABS = [
    { id: 'foryou', label: 'For You' },
    { id: 'watch', label: 'Watch' },
    { id: 'board', label: 'Dashboard' },
    { id: 'pa', label: 'PA' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'scroll', label: 'Scroll' },
    { id: 'markets', label: 'Markets' },
    { id: 'macro', label: 'Macro' },
    { id: 'news', label: 'News' },
    { id: 'ideas', label: 'Stock Ideas' },
    { id: 'learn', label: 'Learn' },
    { id: 'saved', label: 'Saved' },
  ];
  const DAILY_GOAL = 5;
  const IDEAS_DISCLAIMER = 'Educational only, not financial advice. Do your own research.';

  // ---------- storage (every access guarded: private mode can throw) ----------
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem('mr:' + key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem('mr:' + key, JSON.stringify(value)); } catch { /* storage unavailable */ }
    },
  };

  const state = {
    feed: null,
    lessons: [],
    courses: [],
    list: [],
    tab: store.get('tab', 'foryou'),
    course: null,
    ratings: store.get('ratings', {}),
    savedReels: store.get('savedReels', {}),
    seen: new Set(store.get('seen', [])),
    completed: new Set(store.get('completed', [])),
    answered: store.get('answered', {}),
    daily: store.get('daily', {}),
    sound: store.get('sound', false),
    autoplay: store.get('autoplay', true),
    rate: store.get('rate', 1.05),
    xp: store.get('xp', 0),
    level: store.get('level', 'pro'), // 'pro' = experienced (skips beginner explainers), 'new' = everything
    pa: store.get('pa', []), // [{sym, shares, cost, added}]
    alertPct: store.get('alertPct', 3),
    alertNotify: store.get('alertNotify', false),
    alertLog: store.get('alertLog', []),
    paSort: store.get('paSort', 'move'),
    calFilter: 'all',
    calendar: null,
    videos: [],
    curve: null,
    player: null,
  };
  const visibleScenes = (reel) => (reel.scenes || []).filter((s) => !(state.level === 'pro' && s.basic));

  const $ = (sel, root = document) => root.querySelector(sel);
  const feedEl = $('#feed');

  // ---------- helpers ----------
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // **text** -> highlighted, [up]text[/up] / [down]text[/down] -> colored
  const rich = (s) => esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<span class="hl">$1</span>')
    .replace(/\[up\](.+?)\[\/up\]/g, '<span class="up">$1</span>')
    .replace(/\[down\](.+?)\[\/down\]/g, '<span class="down">$1</span>');
  const plain = (s) => String(s ?? '').replace(/\*\*|\[\/?(up|down)\]/g, '');
  const pct = (c, digits = 2) => (c == null || isNaN(c) ? '—' : (Number(c.toFixed(digits)) === 0 ? (0).toFixed(digits) : (c > 0 ? '+' : '') + Number(c).toFixed(digits)) + '%');
  const dirClass = (c) => (c == null || Math.abs(c) < 0.005 ? '' : c > 0 ? 'up' : 'down');
  const arrow = (c) => (c == null || Math.abs(c) < 0.005 ? '•' : c > 0 ? '▲' : '▼');
  const todayKey = () => new Date().toLocaleDateString('en-CA');

  function relDate(iso) {
    if (!iso) return '';
    const d = new Date(iso + (iso.length === 10 ? 'T12:00:00' : ''));
    const days = Math.round((new Date(new Date().toDateString()) - new Date(d.toDateString())) / 86400000);
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), 2000);
  }

  function hashStr(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  // ---------- illustrations (Imprint-style spot art, tinted by category) ----------
  const ART = {
    chart: '<rect class="d" x="24" y="64" width="14" height="30" rx="3"/><rect class="d" x="44" y="52" width="14" height="42" rx="3"/><rect class="p" x="64" y="40" width="14" height="54" rx="3"/><rect class="p" x="84" y="28" width="14" height="66" rx="3"/><path class="s" d="M22 74 L48 56 L66 62 L96 30"/><path class="s" d="M84 30 H97 V43"/>',
    fed: '<path class="p" d="M60 18 L100 40 H20 Z"/><rect class="w" x="22" y="40" width="76" height="6" rx="2"/><rect class="d" x="28" y="50" width="9" height="34" rx="2"/><rect class="d" x="44" y="50" width="9" height="34" rx="2"/><rect class="d" x="67" y="50" width="9" height="34" rx="2"/><rect class="d" x="83" y="50" width="9" height="34" rx="2"/><rect class="w" x="18" y="86" width="84" height="8" rx="2"/><circle class="w" cx="60" cy="33" r="4"/>',
    bonds: '<path class="d" d="M60 70 L72 94 H48 Z"/><rect class="w" x="14" y="62" width="92" height="7" rx="3.5" transform="rotate(-14 60 66)"/><circle class="p" cx="26" cy="64" r="13"/><text x="26" y="69" text-anchor="middle" class="t">%</text><circle class="u" cx="94" cy="40" r="11"/><text x="94" y="45" text-anchor="middle" class="t">$</text>',
    globe: '<circle class="p" cx="60" cy="60" r="34"/><path class="s" d="M60 26 C44 40 44 80 60 94 C76 80 76 40 60 26 Z"/><path class="s" d="M27 52 H93 M27 68 H93"/><circle class="w" cx="90" cy="30" r="5"/>',
    oil: '<rect class="p" x="34" y="34" width="44" height="58" rx="8"/><rect class="w" x="34" y="48" width="44" height="5" opacity=".7"/><rect class="w" x="34" y="74" width="44" height="5" opacity=".7"/><path class="w" d="M92 24 C92 24 82 38 82 44 A10 10 0 0 0 102 44 C102 38 92 24 92 24 Z"/>',
    jobs: '<rect class="p" x="22" y="40" width="76" height="52" rx="8"/><path class="s" d="M46 40 V32 a6 6 0 0 1 6 -6 h16 a6 6 0 0 1 6 6 V40"/><rect class="w" x="22" y="60" width="76" height="5" opacity=".7"/><rect class="w" x="54" y="56" width="12" height="13" rx="3"/>',
    factory: '<path class="p" d="M18 94 V58 L40 70 V58 L62 70 V58 L84 70 V40 H98 V94 Z"/><rect class="d" x="88" y="22" width="8" height="18" rx="2"/><circle class="w" cx="96" cy="16" r="5" opacity=".6"/><circle class="w" cx="104" cy="10" r="3.5" opacity=".4"/><rect class="w" x="28" y="78" width="10" height="9" rx="2"/><rect class="w" x="50" y="78" width="10" height="9" rx="2"/><rect class="w" x="72" y="78" width="10" height="9" rx="2"/>',
    basket: '<path class="s" d="M16 30 H28 L38 76 H90 L100 44 H32"/><path class="p" d="M33 46 H97 L89 72 H39 Z"/><circle class="w" cx="44" cy="88" r="6"/><circle class="w" cx="84" cy="88" r="6"/>',
    coins: '<ellipse class="d" cx="44" cy="84" rx="24" ry="8"/><rect class="d" x="20" y="64" width="48" height="20"/><ellipse class="p" cx="44" cy="64" rx="24" ry="8"/><circle class="p" cx="80" cy="50" r="24"/><circle class="s" cx="80" cy="50" r="17"/><text x="80" y="58" text-anchor="middle" class="t big">$</text>',
    chip: '<rect class="p" x="34" y="34" width="52" height="52" rx="8"/><rect class="w" x="46" y="46" width="28" height="28" rx="4" opacity=".85"/><path class="s" d="M46 22 V34 M60 22 V34 M74 22 V34 M46 86 V98 M60 86 V98 M74 86 V98 M22 46 H34 M22 60 H34 M22 74 H34 M86 46 H98 M86 60 H98 M86 74 H98"/>',
    news: '<rect class="p" x="20" y="26" width="72" height="70" rx="8"/><rect class="d" x="92" y="40" width="10" height="56" rx="4"/><rect class="w" x="30" y="36" width="52" height="9" rx="2"/><rect class="w" x="30" y="52" width="24" height="20" rx="2" opacity=".8"/><rect class="w" x="60" y="52" width="22" height="4" rx="2" opacity=".7"/><rect class="w" x="60" y="60" width="22" height="4" rx="2" opacity=".7"/><rect class="w" x="60" y="68" width="16" height="4" rx="2" opacity=".7"/><rect class="w" x="30" y="80" width="52" height="4" rx="2" opacity=".7"/>',
    magnifier: '<path class="s sp" d="M18 84 L36 66 L50 74 L74 46"/><circle class="d" cx="62" cy="52" r="26"/><circle class="s" cx="62" cy="52" r="26"/><path class="s" d="M81 71 L100 90" style="stroke-width:9"/><path class="s sp" d="M46 60 L56 50 L64 56 L76 42"/>',
    rocket: '<path class="p" d="M60 16 C78 30 80 56 74 78 H46 C40 56 42 30 60 16 Z"/><circle class="w" cx="60" cy="46" r="8"/><path class="d" d="M46 64 L32 84 L46 80 Z M74 64 L88 84 L74 80 Z"/><path class="u" d="M50 80 Q60 106 70 80 Z"/>',
    ship: '<path class="p" d="M16 74 H104 L94 92 H26 Z"/><rect class="u" x="28" y="56" width="16" height="16" rx="2"/><rect class="w" x="46" y="56" width="16" height="16" rx="2" opacity=".85"/><rect class="r" x="64" y="56" width="16" height="16" rx="2"/><rect class="w" x="46" y="40" width="16" height="14" rx="2" opacity=".6"/><rect class="d" x="84" y="44" width="10" height="28" rx="2"/><path class="s" d="M14 102 Q24 96 34 102 T54 102 T74 102 T94 102"/>',
    bell: '<path class="p" d="M60 22 C42 22 34 38 34 54 V72 L26 82 H94 L86 72 V54 C86 38 78 22 60 22 Z"/><circle class="w" cx="60" cy="92" r="7"/><path class="s" d="M98 32 Q106 44 100 58 M22 32 Q14 44 20 58"/>',
    calendar: '<rect class="p" x="22" y="28" width="76" height="66" rx="10"/><rect class="w" x="22" y="28" width="76" height="16" rx="8" opacity=".9"/><path class="s" d="M40 20 V34 M80 20 V34"/><circle class="w" cx="42" cy="60" r="4"/><circle class="w" cx="60" cy="60" r="4"/><circle class="w" cx="78" cy="60" r="4"/><circle class="w" cx="42" cy="78" r="4"/><circle class="u" cx="60" cy="78" r="6"/>',
    shield: '<path class="p" d="M60 18 L94 30 V56 C94 78 78 92 60 100 C42 92 26 78 26 56 V30 Z"/><path class="s" d="M44 58 L56 70 L78 46" style="stroke-width:7"/>',
  };
  const artSVG = (key, cls = '') => ART[key]
    ? `<svg class="art ${cls}" viewBox="0 0 120 120" aria-hidden="true"><circle class="bgc" cx="60" cy="60" r="56"/>${ART[key]}</svg>` : '';

  const RATE_ICONS = {
    1: '<svg viewBox="0 0 24 24"><path d="M7 10v11H3V10z"/><path d="M7 10l4-8a3 3 0 0 1 3 3v4h5.5a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.1 21H7"/></svg>',
    0: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><path d="M8 15h8"/><path d="M9 9.5h.01M15 9.5h.01"/></svg>',
    '-1': '<svg viewBox="0 0 24 24"><path d="M17 14V3h4v11z"/><path d="M17 14l-4 8a3 3 0 0 1-3-3v-4H4.5a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.9 3H17"/></svg>',
  };
  const RATE_LABELS = { 1: 'Like', 0: 'Neutral', '-1': 'Dislike' };

  // ---------- personalization ----------
  function rateReel(reel, value) {
    const prev = state.ratings[reel.id]?.v;
    if (prev === value) delete state.ratings[reel.id];
    else state.ratings[reel.id] = { v: value, cat: reel.category, tag: reel.tag || '', ticker: reel.ticker || '', title: plain(reel.title).slice(0, 90), t: Date.now() };
    store.set('ratings', state.ratings);
    return state.ratings[reel.id]?.v;
  }

  function tasteProfile() {
    const agg = { cat: {}, tag: {}, ticker: {} };
    Object.values(state.ratings).forEach((r) => {
      [['cat', r.cat], ['tag', r.tag], ['ticker', r.ticker]].forEach(([k, val]) => {
        if (!val) return;
        const a = (agg[k][val] ||= { sum: 0, n: 0, likes: 0, neutral: 0, dislikes: 0 });
        a.sum += r.v; a.n += 1;
        if (r.v > 0) a.likes++; else if (r.v < 0) a.dislikes++; else a.neutral++;
      });
    });
    return agg;
  }

  // Smoothed average rating (-1..1); a single vote only nudges, many votes decide.
  function prefScore(reel, profile) {
    const s = (a) => (a ? a.sum / (a.n + 2) : 0);
    return s(profile.cat[reel.category]) * 1 + s(profile.tag[reel.tag]) * 1.2 + (reel.ticker ? s(profile.ticker[reel.ticker]) * 0.8 : 0);
  }

  const disliked = (r) => state.ratings[r.id]?.v === -1;

  // ---------- data ----------
  async function fetchJSON(url) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(url + ' ' + res.status);
    return res.json();
  }

  async function load() {
    feedEl.innerHTML = '<div class="loading"><div><div class="spinner"></div>Loading reels…</div></div>';
    const [feed, lessons, videos] = await Promise.allSettled([fetchJSON('data/feed.json'), fetchJSON('data/lessons.json'), fetchJSON('data/videos.json')]);
    state.videos = videos.status === 'fulfilled' ? (videos.value.reels || []).filter((r) => r.video) : [];
    state.feed = feed.status === 'fulfilled' ? feed.value : { reels: [], tape: [] };
    state.lessons = lessons.status === 'fulfilled' ? (lessons.value.reels || []) : [];
    state.courses = lessons.status === 'fulfilled' ? (lessons.value.courses || []) : [];
    state.lessons.forEach((r) => { r.category = 'learn'; });
    live.feedMs = Date.parse(state.feed.generated_at) || 0;
    live.symbols = collectSymbols().join(',');
    refreshQuotes();
    renderTape(state.feed.tape || []);
    renderTabs();
    renderStats();
    const deep = location.hash.match(/r=([^&]+)/);
    const tabLink = location.hash.match(/^#(board|pa|calendar)$/); // e.g. alert notifications open #pa
    if (tabLink) setTab(tabLink[1], false);
    // One-tap import: #pa=AAPL,NVDA adds those tickers to PA on this device.
    const paLink = location.hash.match(/^#pa=([A-Za-z0-9.^=,\-]+)$/);
    if (paLink) {
      const have = new Set(state.pa.map((h) => h.sym));
      const added = [...new Set(paLink[1].toUpperCase().split(',').filter((s) => /^[A-Z0-9^=.\-]{1,12}$/.test(s) && !have.has(s)))];
      added.forEach((sym, i) => state.pa.push({ sym, shares: null, cost: null, added: Date.now() + i }));
      paSave();
      history.replaceState(null, '', location.pathname + '#pa');
      setTab('pa', false);
      setTimeout(() => toast(added.length ? `Added ${added.join(', ')} to PA` : 'Those stocks are already in PA'), 600);
    }
    if (deep) {
      const id = decodeURIComponent(deep[1]);
      if (!buildList(state.tab).some((r) => r.id === id)) setTab('foryou', false);
      renderFeed(id);
    } else {
      renderFeed();
    }
  }

  function orderedLessons() {
    // Unfinished lessons first; rotate daily so the mix stays fresh.
    const day = new Date().toDateString();
    const lessons = state.lessons.slice().sort((a, b) => hashStr(day + a.id) - hashStr(day + b.id));
    const done = (r) => state.completed.has(r.id) || state.seen.has(r.id);
    return [...lessons.filter((r) => !done(r)), ...lessons.filter(done)];
  }

  function personalMix() {
    // Real video clips first, with data reels (real numbers) between them and an occasional lesson.
    const profile = tasteProfile();
    const pro = state.level === 'pro';
    const data = (state.feed?.reels || [])
      .filter((r) => !disliked(r) && !(pro && /-news-/.test(r.id))) // template news stories: News tab only
      .map((r, i) => ({ r, k: i + (state.seen.has(r.id) ? 40 : 0) - prefScore(r, profile) * 12 }))
      .sort((a, b) => a.k - b.k)
      .map((x) => x.r);
    const vids = rankVideos();
    const lessons = orderedLessons().filter((r) => !disliked(r));
    const learnPref = profile.cat.learn ? profile.cat.learn.sum / (profile.cat.learn.n + 2) : 0;
    const every = pro ? Math.max(6, Math.round(9 - learnPref * 3)) : Math.max(3, Math.round(4 - learnPref * 2));
    const pattern = vids.length ? (pro ? ['v', 'v', 'd'] : ['d', 'v']) : ['d'];
    const out = [];
    let vi = 0, di = 0, li = 0, step = 0;
    while ((vi < vids.length || di < data.length) && out.length < 90) {
      const want = pattern[step++ % pattern.length];
      if (want === 'v' && vi < vids.length) out.push(vids[vi++]);
      else if (di < data.length) out.push(data[di++]);
      else out.push(vids[vi++]);
      if (out.length % every === 0 && li < lessons.length) out.push(lessons[li++]);
    }
    while (li < lessons.length && out.length < 90) out.push(lessons[li++]);
    return out;
  }

  function buildList(tab) {
    if (tab === 'saved') return Object.values(state.savedReels).sort((a, b) => (b._savedAt || 0) - (a._savedAt || 0));
    if (tab === 'learn') {
      const c = state.courses.find((x) => x.id === state.course);
      return c ? c.lessons.map((id) => state.lessons.find((l) => l.id === id)).filter(Boolean) : [];
    }
    if (tab === 'foryou' || tab === 'scroll') return personalMix();
    if (tab === 'watch') return rankVideos();
    return (state.feed?.reels || []).filter((r) => r.category === tab && !disliked(r));
  }

  // ---------- chrome ----------
  function setTab(id, render = true) {
    state.tab = id;
    store.set('tab', id);
    renderTabs();
    if (render) renderFeed();
  }

  function renderTabs() {
    const nav = $('#tabs');
    nav.innerHTML = TABS.map((t) => {
      const label = t.id === 'learn' && state.tab === 'learn' && state.course ? '‹ Courses' : t.label;
      return `<button class="tab" role="tab" data-tab="${t.id}" aria-selected="${t.id === state.tab}">${label}</button>`;
    }).join('');
    nav.onclick = (e) => {
      const b = e.target.closest('.tab');
      if (!b) return;
      if (b.dataset.tab === 'learn' && state.tab === 'learn' && state.course) state.course = null;
      else if (b.dataset.tab !== 'learn') state.course = null;
      setTab(b.dataset.tab);
      nav.querySelector(`[data-tab="${b.dataset.tab}"]`)?.scrollIntoView({ inline: 'center', behavior: 'smooth', block: 'nearest' });
    };
  }

  function renderTape(items) {
    const track = $('#tapeTrack');
    if (!items.length) { $('#tape').hidden = true; return; }
    const html = items.map((t) => {
      const q = t.sym ? liveFor(t.sym, null) : null;
      const value = q ? (t.fmt === 'yield' ? fmtLive('yield', q.price) : q.price < 1000 ? q.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : Math.round(q.price).toLocaleString('en-US')) : t.value;
      const chg = q ? q.chg : t.change;
      return `<span class="tape-item"><b>${esc(t.label)}</b>${esc(value)} <span class="${dirClass(chg)}">${arrow(chg)} ${pct(chg)}</span></span>`;
    }).join('');
    track.innerHTML = html + html;
    track.style.animationDuration = Math.max(30, items.length * 5) + 's';
  }

  // ---------- streaks, daily goal, XP ----------
  function streak() {
    const d = new Date();
    let n = 0;
    if ((state.daily[todayKey()] || 0) < DAILY_GOAL) d.setDate(d.getDate() - 1); // today still in progress
    while ((state.daily[d.toLocaleDateString('en-CA')] || 0) >= DAILY_GOAL) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }

  function renderStats(bump) {
    const done = Math.min(DAILY_GOAL, state.daily[todayKey()] || 0);
    const el = $('#xp');
    const circ = 2 * Math.PI * 8;
    el.innerHTML = `<span class="goal" title="Daily goal: ${DAILY_GOAL} reels"><svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" class="goal-bg"/><circle cx="10" cy="10" r="8" class="goal-fg" stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - done / DAILY_GOAL)}"/></svg><b>${done}/${DAILY_GOAL}</b></span>
      <span title="Day streak">🔥 <b>${streak()}</b></span><span title="XP from quizzes">⚡ <b>${state.xp}</b></span>`;
    if (bump) { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); }
  }

  function countCompletion(reel) {
    const key = 'c:' + reel.id;
    if (state.seen.has(key)) return;
    state.seen.add(key);
    store.set('seen', [...state.seen].slice(-3000));
    const t = todayKey();
    const before = state.daily[t] || 0;
    state.daily[t] = before + 1;
    // Keep ~3 months of history.
    const keys = Object.keys(state.daily).sort();
    keys.slice(0, Math.max(0, keys.length - 100)).forEach((k) => delete state.daily[k]);
    store.set('daily', state.daily);
    if (reel.category === 'learn') {
      state.completed.add(reel.id);
      store.set('completed', [...state.completed]);
      const course = state.courses.find((c) => c.lessons.includes(reel.id));
      if (course && course.lessons.every((id) => state.completed.has(id))) setTimeout(() => toast(`🎓 Course complete: ${course.title}`), 400);
    }
    if (before + 1 === DAILY_GOAL) setTimeout(() => toast(`🔥 Daily goal hit! ${streak()}-day streak`), 900);
    renderStats(true);
  }

  function addXP(n) {
    state.xp += n;
    store.set('xp', state.xp);
    renderStats(true);
    toast(`+${n} XP ⚡`);
  }

  // ---------- live prices + refresh ----------
  // Prices come from api/quotes (Vercel relay to Yahoo, ~real time) or, on GitHub Pages, from data/quotes.json,
  // which GitHub Actions refreshes every ~15 minutes in market hours. Today's numbers in reels update in place.
  const live = { quotes: {}, source: null, fetchedAt: 0, generatedAt: 0, api: undefined, timer: 0, busy: false, symbols: '' };
  const ET_TZ = 'America/New_York';
  const etDate = (ts) => new Date(ts * 1000).toLocaleDateString('en-CA', { timeZone: ET_TZ });
  const etTime = (ts) => new Date(ts * 1000).toLocaleTimeString('en-US', { timeZone: ET_TZ, hour: 'numeric', minute: '2-digit' });
  const etDay = (ts) => new Date(ts * 1000).toLocaleDateString('en-US', { timeZone: ET_TZ, weekday: 'short' });

  function marketPhase() {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: ET_TZ, weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' })
      .formatToParts(new Date()).map((x) => [x.type, x.value]));
    if (p.weekday === 'Sat' || p.weekday === 'Sun') return 'closed';
    const m = Number(p.hour) * 60 + Number(p.minute);
    return m < 240 ? 'closed' : m < 570 ? 'pre' : m < 960 ? 'open' : m < 1200 ? 'after' : 'closed';
  }

  function fmtLive(fmt, v) {
    if (v == null) return '—';
    if (fmt === 'yield') return v.toFixed(2) + '%';
    if (fmt === 'usd') return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (fmt === 'usd0') return '$' + Math.round(v).toLocaleString('en-US');
    return v >= 1000 ? Math.round(v).toLocaleString('en-US') : v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // A live quote applies to a number only if it's from the same trading day as the reel, and only if the
  // price snapshot isn't older than the feed itself (a stale quotes file must never overwrite fresher numbers).
  function liveFor(sym, date) {
    const q = live.quotes[sym];
    if (!q || q.price == null || !q.time) return null;
    if (date && etDate(q.time) !== date) return null;
    if (live.generatedAt && live.feedMs && live.generatedAt < live.feedMs - 5 * 60e3) return null;
    return q;
  }

  function paintLive(el) {
    const { sym, fmt, kind, date } = el.dataset;
    const q = liveFor(sym, kind === 'chip' ? null : date);
    if (!q) return;
    el.classList.add('is-live');
    if (kind === 'tile') {
      el.querySelector('.v').textContent = fmtLive(fmt, q.price);
      if (fmt === 'yield' && q.prev != null) {
        const n = el.querySelector('.n') || el.appendChild(Object.assign(document.createElement('div'), { className: 'n' }));
        n.textContent = `${(q.price - q.prev) * 100 >= 0 ? '+' : ''}${((q.price - q.prev) * 100).toFixed(0)} bp`;
      } else if (q.chg != null) {
        const c = el.querySelector('.c') || el.insertBefore(Object.assign(document.createElement('div'), { className: 'c' }), el.querySelector('.n'));
        c.className = 'c ' + dirClass(q.chg);
        c.textContent = `${arrow(q.chg)} ${pct(q.chg)}`;
      }
    } else if (kind === 'chart') {
      el.querySelector('.chart-last').textContent = fmtLive(fmt, q.price);
      const first = Number(el.dataset.first);
      if (first) {
        const chg = (q.price / first - 1) * 100;
        const c = el.querySelector('.chart-chg');
        c.className = 'chart-chg ' + dirClass(chg);
        c.textContent = pct(chg);
      }
    } else if (kind === 'chip') {
      el.innerHTML = `$${esc(sym)} <span class="${dirClass(q.chg)}">${fmtLive('usd', q.price)} ${arrow(q.chg)}${pct(q.chg, 1)}</span>`;
    }
  }

  function collectSymbols() {
    const s = new Set();
    (state.feed?.tape || []).forEach((t) => t.sym && s.add(t.sym));
    state.pa.forEach((h) => s.add(h.sym));
    (state.feed?.reels || []).forEach((r) => {
      if (r.ticker) s.add(r.ticker);
      (r.scenes || []).forEach((sc) => { if (sc.sym) s.add(sc.sym); (sc.items || []).forEach((i) => i.sym && s.add(i.sym)); });
    });
    return [...s].sort().slice(0, 120);
  }

  function quoteInterval() {
    const phase = marketPhase();
    if (live.api) return phase === 'open' ? 30e3 : phase === 'closed' ? 600e3 : 60e3;
    return phase === 'open' || phase === 'pre' || phase === 'after' ? 120e3 : 600e3;
  }

  async function refreshQuotes(manual) {
    if (live.busy) return;
    live.busy = true;
    $('#livePill')?.classList.add('spin');
    let data = null;
    try {
      if (live.api !== false) {
        try {
          const r = await fetch('api/quotes?s=' + encodeURIComponent(live.symbols || collectSymbols().join(',')), { cache: 'no-store' });
          const j = r.ok && (r.headers.get('content-type') || '').includes('json') ? await r.json() : null;
          if (j && j.quotes && Object.keys(j.quotes).length) { data = j; live.api = true; live.source = 'live'; } else live.api = false;
        } catch { live.api = false; }
      }
      if (!data) {
        try {
          const r = await fetch('data/quotes.json', { cache: 'no-cache' });
          if (r.ok) { data = await r.json(); live.source = 'file'; }
        } catch { /* offline: keep what we have */ }
      }
      if (data?.quotes) {
        Object.assign(live.quotes, data.quotes);
        live.fetchedAt = Date.now();
        live.generatedAt = Date.parse(data.generated_at) || Date.now();
        renderTape(state.feed?.tape || []);
        document.querySelectorAll('[data-sym]').forEach(paintLive);
        checkAlerts();
        if (manual) toast(`Prices updated · ${liveStatus().text}`);
      } else if (manual) toast('Offline: showing saved prices');
    } finally {
      live.busy = false;
      $('#livePill')?.classList.remove('spin');
      renderLiveStatus();
      clearTimeout(live.timer);
      if (!document.hidden) live.timer = setTimeout(() => refreshQuotes(), quoteInterval());
    }
  }

  function liveStatus() {
    const ref = live.quotes['^GSPC'] || live.quotes.SPY || Object.values(live.quotes)[0];
    if (!ref?.time) return { cls: 'off', text: 'Prices from feed' };
    const phase = marketPhase();
    const age = (Date.now() / 1000 - ref.time) / 60;
    const at = `${etTime(ref.time)} ET`;
    const dayAt = etDate(ref.time) === etDate(Date.now() / 1000) ? at : `${etDay(ref.time)} close`;
    if (phase === 'open') {
      if (age < 5) return { cls: 'live', text: `Live · ${at}` };
      if (age < 90) return { cls: 'delayed', text: `${Math.round(age)} min ago · ${at}` };
      return { cls: 'closed', text: `Closed · ${dayAt}` }; // market holiday
    }
    if (phase === 'pre') return { cls: 'closed', text: `Pre-market · ${dayAt}` };
    if (phase === 'after') return { cls: 'closed', text: `After hours · close ${at}` };
    return { cls: 'closed', text: `Closed · ${dayAt}` };
  }

  function renderLiveStatus() {
    const pill = $('#livePill');
    if (!pill) return;
    const s = liveStatus();
    pill.className = 'live-pill ' + s.cls + (live.busy ? ' spin' : '');
    pill.querySelector('span').textContent = s.text;
    pill.title = live.source === 'live' ? 'Live prices (tap to refresh)' : live.source === 'file' ? 'Prices refresh about every 15 minutes (tap to refresh)' : 'Tap to refresh';
  }

  // New reels: check feed.json periodically and offer to load it instead of yanking the feed mid-reel.
  let pendingFeed = null, feedCheckedAt = Date.now();
  async function checkFeed(applyNow) {
    feedCheckedAt = Date.now();
    try {
      const f = await fetchJSON('data/feed.json');
      if (f.generated_at && f.generated_at !== state.feed?.generated_at) {
        pendingFeed = f;
        if (applyNow) applyPendingFeed();
        else $('#newPill').hidden = false;
        return true;
      }
    } catch { /* offline */ }
    return false;
  }

  function applyPendingFeed() {
    if (!pendingFeed) return;
    state.feed = pendingFeed;
    pendingFeed = null;
    live.feedMs = Date.parse(state.feed.generated_at) || 0;
    live.symbols = collectSymbols().join(',');
    $('#newPill').hidden = true;
    renderTape(state.feed.tape || []);
    renderFeed();
    toast('✨ New reels loaded');
  }

  async function refreshAll(manual) {
    await Promise.all([refreshQuotes(manual), checkFeed(!feedEl.querySelector('.reel[data-idx]'))]);
  }

  $('#livePill').addEventListener('click', () => refreshAll(true));
  $('#newPill').addEventListener('click', applyPendingFeed);
  setInterval(() => { if (!document.hidden && Date.now() - feedCheckedAt > 10 * 60e3) checkFeed(false); }, 60e3);
  setInterval(renderLiveStatus, 30e3);

  // Pull to refresh on the free-scrolling pages (Scroll, Courses).
  (() => {
    let startY = null, dy = 0;
    const ptr = $('#ptr');
    feedEl.addEventListener('touchstart', (e) => { startY = feedEl.classList.contains('free') && feedEl.scrollTop <= 0 ? e.touches[0].clientY : null; dy = 0; }, { passive: true });
    feedEl.addEventListener('touchmove', (e) => {
      if (startY == null) return;
      dy = e.touches[0].clientY - startY;
      if (dy <= 0) { ptr.style.opacity = 0; return; }
      ptr.style.opacity = Math.min(1, dy / 90);
      ptr.style.transform = `translate(-50%, ${Math.min(dy / 2, 60)}px)`;
      ptr.textContent = dy > 110 ? '↻ Release to refresh' : '↓ Pull to refresh';
    }, { passive: true });
    feedEl.addEventListener('touchend', async () => {
      if (startY == null) return;
      const go = dy > 110;
      startY = null;
      if (!go) { ptr.style.opacity = 0; return; }
      ptr.textContent = '↻ Refreshing…';
      await Promise.all([refreshQuotes(true), checkFeed(true)]);
      ptr.style.opacity = 0;
    });
  })();

  // ---------- Dashboard, PA and Calendar pages ----------
  // Live tables use api/quotes?spark=1 (intraday points for mini charts); without the Vercel function they fall
  // back to data/quotes.json prices (no mini charts).
  const BOARD = [
    { title: 'US indexes', rows: [['^GSPC', 'S&P 500'], ['^IXIC', 'Nasdaq Composite'], ['^NDX', 'Nasdaq-100'], ['^DJI', 'Dow Jones'], ['^RUT', 'Russell 2000'], ['^MID', 'S&P MidCap 400'], ['^VIX', 'VIX (volatility)']] },
    { title: 'Index futures', rows: [['ES=F', 'S&P 500 futures'], ['NQ=F', 'Nasdaq-100 futures'], ['YM=F', 'Dow futures'], ['RTY=F', 'Russell 2000 futures']] },
    { title: 'Treasury yields', kind: 'yields', rows: [['^IRX', '3-month', 'yield'], ['^FVX', '5-year', 'yield'], ['^TNX', '10-year', 'yield'], ['^TYX', '30-year', 'yield']] },
    { title: 'Commodities', rows: [['GC=F', 'Gold', 'usd'], ['SI=F', 'Silver', 'usd'], ['HG=F', 'Copper', 'usd'], ['CL=F', 'WTI crude oil', 'usd'], ['BZ=F', 'Brent crude oil', 'usd'], ['NG=F', 'Natural gas', 'usd']] },
    { title: 'US dollar & currencies', rows: [['DX-Y.NYB', 'US Dollar Index (DXY)'], ['EURUSD=X', 'EUR/USD', 'fx'], ['JPY=X', 'USD/JPY', 'fx'], ['GBPUSD=X', 'GBP/USD', 'fx'], ['CNY=X', 'USD/CNY', 'fx'], ['MXN=X', 'USD/MXN', 'fx']] },
    { title: 'Crypto', rows: [['BTC-USD', 'Bitcoin', 'usd0'], ['ETH-USD', 'Ethereum', 'usd'], ['SOL-USD', 'Solana', 'usd']] },
    { title: 'Global markets', rows: [['^STOXX50E', 'Euro Stoxx 50'], ['^GDAXI', 'Germany DAX'], ['^FTSE', 'UK FTSE 100'], ['^N225', 'Japan Nikkei 225'], ['^HSI', 'Hong Kong Hang Seng'], ['000001.SS', 'Shanghai Composite'], ['^BSESN', 'India Sensex']] },
    { title: 'S&P 500 sectors', kind: 'sectors', rows: [['XLK', 'Tech'], ['XLC', 'Comm. Services'], ['XLY', 'Discretionary'], ['XLF', 'Financials'], ['XLI', 'Industrials'], ['XLE', 'Energy'], ['XLB', 'Materials'], ['XLV', 'Healthcare'], ['XLP', 'Staples'], ['XLU', 'Utilities'], ['XLRE', 'Real Estate']] },
  ];
  let pageTimer = 0;
  const pageQuotes = {};

  const fmtPx = (fmt, v, type) => {
    if (v == null) return '—';
    if (fmt === 'fx') return v.toFixed(v < 20 ? 4 : 2);
    if (fmt === 'yield') return v.toFixed(3) + '%';
    if (fmt === 'usd0') return '$' + Math.round(v).toLocaleString('en-US');
    if (fmt === 'usd' || type === 'EQUITY' || type === 'ETF') return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  const shortName = (n) => String(n || '').replace(/,? (Inc|Corp|Corporation|Incorporated|Company|Co|Ltd|plc|PLC|Holdings|Group)\.?$/i, '').replace(/,$/, '');
  const signedNum = (v, d = 2) => (v == null ? '' : (v >= 0 ? '+' : '−') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));

  function sparkSVG(points, prev, w = 74, h = 28) {
    const pts = (points || []).filter((v) => v != null);
    if (pts.length < 2) return `<svg class="spark" viewBox="0 0 ${w} ${h}"></svg>`;
    const all = prev != null ? [...pts, prev] : pts;
    const min = Math.min(...all), max = Math.max(...all), span = max - min || 1;
    const x = (i) => (i / (pts.length - 1)) * w, y = (v) => 2 + (1 - (v - min) / span) * (h - 4);
    const d = pts.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join('');
    const up = pts[pts.length - 1] >= (prev ?? pts[0]);
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true">${prev != null ? `<line x1="0" x2="${w}" y1="${y(prev).toFixed(1)}" y2="${y(prev).toFixed(1)}" class="spark-base"/>` : ''}<path d="${d}" class="${up ? 'up' : 'down'}"/></svg>`;
  }

  async function fetchPageQuotes(symbols) {
    if (!symbols.length) return {};
    let got = null;
    if (live.api !== false) {
      try {
        const r = await fetch('api/quotes?spark=1&s=' + encodeURIComponent(symbols.join(',')), { cache: 'no-store' });
        const j = r.ok && (r.headers.get('content-type') || '').includes('json') ? await r.json() : null;
        if (j?.quotes) { got = j.quotes; live.api = true; }
      } catch { /* fall through */ }
    }
    if (!got) {
      if (!Object.keys(live.quotes).length) await refreshQuotes();
      got = Object.fromEntries(symbols.filter((s) => live.quotes[s]).map((s) => [s, live.quotes[s]]));
    }
    Object.assign(pageQuotes, got);
    checkAlerts();
    // Keep the tape and reels in sync with the fresher prices.
    for (const [s, q] of Object.entries(got)) live.quotes[s] = { ...live.quotes[s], ...q };
    renderLiveStatus();
    return got;
  }

  function schedulePage(fn) {
    clearTimeout(pageTimer);
    pageTimer = setTimeout(() => { if (!document.hidden && ['board', 'pa'].includes(state.tab)) fn(); }, live.api ? 30e3 : 120e3);
  }

  async function loadSideData() {
    if (state.calendar && state.curve) return;
    const [c, v] = await Promise.allSettled([fetchJSON('data/calendar.json'), fetchJSON('data/curve.json')]);
    state.calendar = c.status === 'fulfilled' ? c.value : { events: [], earnings: [], fed: {} };
    state.curve = v.status === 'fulfilled' ? v.value : null;
  }

  function quoteRow(sym, name, fmt, extra = '') {
    const q = pageQuotes[sym] || live.quotes[sym];
    const isYield = fmt === 'yield';
    const chgTxt = !q ? '—' : isYield ? (q.prev != null ? `${signedNum((q.price - q.prev) * 100, 1)} bp` : '—') : pct(q.chg);
    const absDigits = fmt === 'fx' && q?.price < 20 ? 4 : q?.price > 1000 ? 0 : 2;
    const abs = q && q.prev != null && !isYield ? signedNum(q.price - q.prev, absDigits) : '';
    return `<button class="qrow" data-sym="${esc(sym)}" data-name="${esc(name)}" data-fmt="${esc(fmt || '')}">
      <span class="q-name"><b>${esc(shortName(name))}</b><small>${esc(sym.replace('^', ''))}</small></span>
      ${sparkSVG(q?.points, q?.prev)}
      <span class="q-px">${q ? fmtPx(fmt, q.price, q.type) : '—'}</span>
      <span class="q-chg ${q ? dirClass(isYield ? q.price - q.prev : q.chg) : ''}">${chgTxt}<small>${abs}</small></span>
      ${extra ? `<span class="q-extra">${extra.replace(/^ · /, '')}</span>` : ''}</button>`;
  }

  function fedCard() {
    const fed = state.calendar?.fed || {};
    const last = fed.last, nxt = fed.next;
    const res = last?.result;
    const days = nxt ? Math.round((new Date(nxt.date + 'T00:00:00') - new Date(new Date().toDateString())) / 86400000) : null;
    return `<section class="dash-card fed-card"><div class="dash-head"><h2>Federal Reserve</h2>${state.tab === 'calendar' ? '' : '<button class="linkbtn" data-go="calendar">Calendar ›</button>'}</div>
      <div class="fed-grid">
        <div><small>Target range</small><b>${res ? `${res.low.toFixed(2)}–${res.high.toFixed(2)}%` : '—'}</b></div>
        <div><small>Last move</small><b>${last ? esc((last.actual || '').split(' to ')[0]) : '—'}</b><em>${last ? esc(relDate(last.date)) : ''}</em></div>
        <div><small>Next decision</small><b>${nxt ? esc(new Date(nxt.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })) : '—'}</b><em>${days != null ? (days <= 0 ? 'today, 2:00 pm ET' : `in ${days} day${days === 1 ? '' : 's'}`) : ''}</em></div>
      </div>${oddsLine()}</section>`;
  }

  function curveCard() {
    const c = state.curve;
    if (!c?.points) return '';
    const order = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y'].filter((k) => c.points[k] != null);
    const wk = c.week_ago?.points || {};
    const vals = order.map((k) => c.points[k]).concat(order.map((k) => wk[k]).filter((v) => v != null));
    const min = Math.min(...vals) - 0.05, max = Math.max(...vals) + 0.05;
    const W = 320, H = 110, x = (i) => 12 + (i / (order.length - 1)) * (W - 24), y = (v) => 8 + (1 - (v - min) / (max - min)) * (H - 26);
    const line = (src) => order.map((k, i) => (src[k] == null ? '' : `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(src[k]).toFixed(1)}`)).join('');
    const p = c.points;
    const s210 = p['2Y'] != null && p['10Y'] != null ? (p['10Y'] - p['2Y']) * 100 : null;
    const s3m10 = p['3M'] != null && p['10Y'] != null ? (p['10Y'] - p['3M']) * 100 : null;
    const wkbp = (k) => (wk[k] != null && p[k] != null ? `${signedNum((p[k] - wk[k]) * 100, 0)} bp w/w` : '');
    return `<section class="dash-card"><div class="dash-head"><h2>Yield curve</h2><small>US Treasury · ${esc(relDate(c.date))}</small></div>
      <svg class="curve" viewBox="0 0 ${W} ${H}">
        <path d="${line(wk)}" class="curve-wk"/><path d="${line(p)}" class="curve-now"/>
        ${order.map((k, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(p[k]).toFixed(1)}" r="2.6" class="curve-dot"/><text x="${x(i).toFixed(1)}" y="${H - 3}" text-anchor="middle">${k}</text>`).join('')}
      </svg>
      <div class="curve-legend"><span><i class="now"></i>Today</span><span><i class="wk"></i>Week ago</span></div>
      <div class="fed-grid">
        <div><small>2-year</small><b>${p['2Y']?.toFixed(2) ?? '—'}%</b><em>${wkbp('2Y')}</em></div>
        <div><small>2s10s</small><b class="${s210 < 0 ? 'down' : ''}">${s210 != null ? signedNum(s210, 0) + ' bp' : '—'}</b><em>${s210 < 0 ? 'inverted' : 'normal slope'}</em></div>
        <div><small>3m10y</small><b class="${s3m10 < 0 ? 'down' : ''}">${s3m10 != null ? signedNum(s3m10, 0) + ' bp' : '—'}</b><em>${s3m10 < 0 ? 'inverted' : 'normal slope'}</em></div>
      </div></section>`;
  }

  async function renderBoard() {
    feedEl.classList.add('free');
    const page = document.createElement('div');
    page.className = 'page';
    feedEl.appendChild(page);
    const draw = () => {
      if (state.tab !== 'board') return;
      const sectorRows = (sec) => [...sec.rows].sort((a, b) => ((pageQuotes[b[0]]?.chg ?? -99) - (pageQuotes[a[0]]?.chg ?? -99)));
      page.innerHTML = `<div class="page-head"><h1>Dashboard</h1><p>${esc(liveStatus().text)} · tap any row for the intraday chart and news.</p></div>
        ${state.calendar ? fedCard() : ''}
        ${BOARD.map((sec) => `<section class="dash-card"><div class="dash-head"><h2>${sec.title}</h2>${sec.kind === 'yields' ? '<small>change in bp</small>' : ''}</div>
          ${(sec.kind === 'sectors' ? sectorRows(sec) : sec.rows).map(([s, n, f]) => quoteRow(s, n, f)).join('')}</section>
          ${sec.kind === 'yields' ? curveCard() : ''}`).join('')}
        <p class="fineprint">Prices from Yahoo Finance, a few seconds to ~10 minutes delayed (futures). Treasury curve: end of day.</p>`;
    };
    if (Object.keys(pageQuotes).length) draw();
    else page.innerHTML = '<div class="loading"><div><div class="spinner"></div>Loading markets…</div></div>';
    const tick = async () => {
      await Promise.all([fetchPageQuotes([...BOARD.flatMap((s) => s.rows.map((r) => r[0])), ...zqSymbols()]), loadSideData()]);
      const y = feedEl.scrollTop;
      draw();
      feedEl.scrollTop = y;
      schedulePage(tick);
    };
    tick();
    page.addEventListener('click', onPageClick);
  }

  // ---------- PA: personal stocks ----------
  const paSave = () => { store.set('pa', state.pa); live.symbols = collectSymbols().join(','); };

  function paTotals() {
    let value = 0, day = 0, cost = 0, hasShares = false, up = 0, down = 0;
    state.pa.forEach((h) => {
      const q = pageQuotes[h.sym] || live.quotes[h.sym];
      if (!q) return;
      if (q.chg > 0) up++; else if (q.chg < 0) down++;
      if (h.shares) {
        hasShares = true;
        value += h.shares * q.price;
        if (q.prev != null) day += h.shares * (q.price - q.prev);
        if (h.cost) cost += h.shares * h.cost;
      }
    });
    return { value, day, cost, hasShares, up, down };
  }

  function nextEarnings(sym) {
    const today = todayKey();
    return (state.calendar?.earnings || []).find((e) => e.symbol === sym && e.date >= today);
  }

  async function renderPA() {
    feedEl.classList.add('free');
    const page = document.createElement('div');
    page.className = 'page';
    feedEl.appendChild(page);
    const newsBox = document.createElement('div');
    const draw = () => {
      if (state.tab !== 'pa') return;
      const t = paTotals();
      const rows = [...state.pa];
      if (state.paSort === 'move') rows.sort((a, b) => Math.abs(pageQuotes[b.sym]?.chg ?? 0) - Math.abs(pageQuotes[a.sym]?.chg ?? 0));
      if (state.paSort === 'az') rows.sort((a, b) => a.sym.localeCompare(b.sym));
      const dayPct = t.value - t.day ? (t.day / (t.value - t.day)) * 100 : 0;
      page.innerHTML = `<div class="page-head"><h1>PA</h1><p>Your stocks, live. Saved on this device only. Add shares to see your P&L.</p></div>
        <section class="dash-card pa-summary">
          ${t.hasShares ? `<div class="fed-grid">
            <div><small>Value</small><b>$${Math.round(t.value).toLocaleString('en-US')}</b></div>
            <div><small>Today</small><b class="${dirClass(t.day)}">${signedNum(t.day, 0).replace(/^([+−])/, '$1$')}</b><em class="${dirClass(dayPct)}">${pct(dayPct)}</em></div>
            <div><small>Total gain</small><b class="${dirClass(t.value - t.cost)}">${t.cost ? signedNum(t.value - t.cost, 0).replace(/^([+−])/, '$1$') : '—'}</b><em>${t.cost ? pct((t.value / t.cost - 1) * 100) : 'add cost basis'}</em></div></div>`
          : `<div class="fed-grid"><div><small>Stocks</small><b>${state.pa.length}</b></div><div><small>Up today</small><b class="up">${t.up}</b></div><div><small>Down today</small><b class="down">${t.down}</b></div></div>`}
          <form class="pa-add" id="paAdd"><input id="paSym" maxlength="12" autocomplete="off" autocapitalize="characters" placeholder="Add a ticker, e.g. AAPL"><button>Add</button></form>
          ${!state.pa.length ? `<div class="pa-suggest">${['SPY', 'QQQ', 'AAPL', 'NVDA', 'MSFT', 'AMZN'].map((s) => `<button data-add="${s}">+ ${s}</button>`).join('')}</div>` : ''}
        </section>
        ${state.pa.length ? `<section class="dash-card"><div class="dash-head"><h2>Holdings & watchlist</h2>
          <div class="seg-ctl">${[['move', 'Movers'], ['az', 'A–Z'], ['added', 'Added']].map(([k, l]) => `<button data-sort="${k}" class="${state.paSort === k ? 'on' : ''}">${l}</button>`).join('')}</div></div>
          ${rows.map((h) => {
            const q = pageQuotes[h.sym];
            const e = nextEarnings(h.sym);
            const pos = h.shares && q ? ` · ${h.shares} sh · $${Math.round(h.shares * q.price).toLocaleString('en-US')}${q.prev != null ? ` · <span class="${dirClass(q.chg)}">${signedNum(h.shares * (q.price - q.prev), 0)}</span>` : ''}` : '';
            const earn = e ? ` · <span class="earn-badge">Earnings ${esc(new Date(e.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }))}</span>` : '';
            return quoteRow(h.sym, q?.name || h.sym, '', pos + earn);
          }).join('')}</section>` : ''}
        ${state.pa.length ? alertsCard() : ''}`;
      wireAlertsCard(page);
      page.appendChild(newsBox);
    };
    const loadNews = async () => {
      const top = [...state.pa].sort((a, b) => Math.abs(pageQuotes[b.sym]?.chg ?? 0) - Math.abs(pageQuotes[a.sym]?.chg ?? 0)).slice(0, 5);
      if (!top.length) { newsBox.innerHTML = ''; return; }
      const lists = await Promise.all(top.map((h) => fetch('api/news?s=' + encodeURIComponent(h.sym)).then((r) => (r.ok ? r.json() : null)).catch(() => null)));
      const seen = new Set();
      const items = lists.flatMap((l, i) => (l?.news || []).slice(0, 3).map((n) => ({ ...n, sym: top[i].sym })))
        .filter((n) => n.title && !seen.has(n.title) && seen.add(n.title)).sort((a, b) => (b.time || 0) - (a.time || 0)).slice(0, 10);
      newsBox.innerHTML = items.length ? `<section class="dash-card"><div class="dash-head"><h2>Latest on your stocks</h2></div>
        <ul class="src-list">${items.map((n) => `<li><a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer"><span class="meta-ticker">$${esc(n.sym)}</span> ${esc(n.title)}<small>${esc(n.publisher || '')} · ${n.time ? esc(new Date(n.time * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })) : ''}</small></a></li>`).join('')}</ul></section>` : '';
    };
    const tick = async () => {
      await Promise.all([fetchPageQuotes(state.pa.map((h) => h.sym)), loadSideData()]);
      const y = feedEl.scrollTop;
      draw();
      feedEl.scrollTop = y;
      schedulePage(tick);
    };
    draw();
    tick().then(loadNews);
    page.addEventListener('submit', async (e) => {
      if (e.target.id !== 'paAdd') return;
      e.preventDefault();
      addHolding($('#paSym').value, tick, loadNews);
    });
    page.addEventListener('click', (e) => {
      const add = e.target.closest('[data-add]');
      if (add) return addHolding(add.dataset.add, tick, loadNews);
      const s = e.target.closest('[data-sort]');
      if (s) { state.paSort = s.dataset.sort; store.set('paSort', state.paSort); draw(); return; }
      onPageClick(e);
    });
  }

  async function addHolding(raw, tick, loadNews) {
    const sym = String(raw || '').trim().toUpperCase().replace(/^\$/, '');
    if (!/^[A-Z0-9^=.\-]{1,12}$/.test(sym)) return toast('Enter a ticker like AAPL');
    if (state.pa.some((h) => h.sym === sym)) return toast(`${sym} is already in PA`);
    const got = await fetchPageQuotes([sym]);
    if (!got[sym]) return toast(live.api ? `Couldn't find ${sym}` : 'Adding stocks needs the live (Vercel) version');
    state.pa.push({ sym, shares: null, cost: null, added: Date.now() });
    paSave();
    toast(`Added ${sym}`);
    await tick();
    loadNews();
  }

  // Tap a row: intraday chart, stats, news, Ask Claude, and PA controls.
  function onPageClick(e) {
    const go = e.target.closest('[data-go]');
    if (go) { setTab(go.dataset.go); return; }
    const row = e.target.closest('.qrow');
    if (row) openQuote(row.dataset.sym, row.dataset.name, row.dataset.fmt);
  }

  async function openQuote(sym, name, fmt) {
    const q = pageQuotes[sym] || live.quotes[sym];
    const held = state.pa.find((h) => h.sym === sym);
    const equity = q && (q.type === 'EQUITY' || q.type === 'ETF');
    const isYield = fmt === 'yield';
    const e = nextEarnings(sym);
    openSheet(`<div class="quote-sheet">
      <h3>${esc(name)} <small>${esc(sym)}</small></h3>
      <div class="qs-price"><b>${q ? fmtPx(fmt, q.price, q.type) : '—'}</b>
        <span class="${q ? dirClass(isYield ? q.price - q.prev : q.chg) : ''}">${q ? (isYield ? `${signedNum((q.price - q.prev) * 100, 1)} bp` : `${signedNum(q.price - q.prev)} (${pct(q.chg)})`) : ''}</span></div>
      <div class="qs-chart">${q?.points ? sparkSVG(q.points, q.prev, 320, 120) : '<p class="fineprint">Intraday chart needs the live (Vercel) version.</p>'}</div>
      <p class="fineprint">Today, 5-minute points · dashed line = previous close${q?.prev != null ? ` (${fmtPx(fmt, q.prev, q.type)})` : ''}${q?.time ? ` · as of ${esc(new Date(q.time * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))}` : ''}</p>
      ${e ? `<p><span class="earn-badge">Earnings ${esc(new Date(e.date + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }))}${e.when === 'pre' ? ', before the open' : e.when === 'post' ? ', after the close' : ''}</span> Consensus EPS ${esc(e.eps_est || '—')} · year-ago ${esc(e.eps_last_year || '—')}</p>` : ''}
      ${held ? `<form class="pa-edit" id="paEdit"><label>Shares<input id="paShares" inputmode="decimal" value="${held.shares ?? ''}" placeholder="0"></label>
        <label>Avg cost<input id="paCost" inputmode="decimal" value="${held.cost ?? ''}" placeholder="$"></label><button>Save</button></form>` : ''}
      <div class="qs-actions">
        <button class="btn primary" id="qsAsk">Ask Claude why it's moving</button>
        ${equity && !held ? '<button class="btn ghost" id="qsAdd">+ Add to PA</button>' : ''}
        ${held ? '<button class="btn ghost" id="qsRemove">Remove from PA</button>' : ''}
        <a class="btn ghost" href="https://finance.yahoo.com/quote/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Open in Yahoo Finance</a>
      </div>
      <h4>Headlines</h4><ul class="src-list" id="qsNews"><li class="fineprint">Loading…</li></ul></div>`);
    $('#qsAsk').onclick = () => {
      const move = q ? (isYield ? `${signedNum((q.price - q.prev) * 100, 1)} bp` : pct(q.chg)) : 'unknown';
      openChat({ id: 'q-' + sym, title: `${name} (${sym}) ${move} today`, category: 'markets', tag: 'Live quote', ticker: equity ? sym : null, art: 'chart',
        scenes: [{ kind: 'text', headline: `${name} is at ${q ? fmtPx(fmt, q.price, q.type) : '—'}, ${move} on the day`, body: `Previous close ${q ? fmtPx(fmt, q.prev, q.type) : '—'}.` }] });
    };
    $('#qsAdd') && ($('#qsAdd').onclick = async () => { closeSheet(); await addHolding(sym, async () => renderFeed(), () => {}); });
    $('#qsRemove') && ($('#qsRemove').onclick = () => { state.pa = state.pa.filter((h) => h.sym !== sym); paSave(); closeSheet(); renderFeed(); toast(`Removed ${sym}`); });
    $('#paEdit') && ($('#paEdit').onsubmit = (ev) => {
      ev.preventDefault();
      const num = (v) => { const n = parseFloat(String(v).replace(/[$,]/g, '')); return Number.isFinite(n) && n > 0 ? n : null; };
      held.shares = num($('#paShares').value);
      held.cost = num($('#paCost').value);
      paSave(); closeSheet(); renderFeed(); toast('Position saved');
    });
    try {
      const r = await fetch('api/news?s=' + encodeURIComponent(sym));
      const j = r.ok ? await r.json() : null;
      const items = (j?.news || []).slice(0, 6);
      $('#qsNews').innerHTML = items.length ? items.map((n) => `<li><a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">${esc(n.title)}<small>${esc(n.publisher || '')}${n.time ? ' · ' + esc(new Date(n.time * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })) : ''}</small></a></li>`).join('')
        : '<li class="fineprint">No recent headlines.</li>';
    } catch { $('#qsNews') && ($('#qsNews').innerHTML = '<li class="fineprint">Headlines need the live (Vercel) version.</li>'); }
  }

  // ---------- Calendar ----------
  const CAL_FILTERS = [['all', 'All'], ['fed', 'Fed'], ['data', 'US data'], ['earnings', 'Earnings'], ['global', 'Global'], ['other', 'Politics & market']];
  const CAT_LABEL = { fed: 'Fed', inflation: 'Inflation', jobs: 'Jobs', growth: 'Growth', consumer: 'Consumer', housing: 'Housing', bonds: 'Bonds', energy: 'Energy', global: 'Global', politics: 'Politics', market: 'Market', data: 'Data' };
  const clock12 = (t) => {
    const m = /^(\d{1,2}):(\d{2})/.exec(t || '');
    if (!m) return '';
    const h = Number(m[1]);
    return `${h % 12 || 12}:${m[2]}${h < 12 ? 'a' : 'p'}`;
  };

  function calMatch(e) {
    const f = state.calFilter;
    if (f === 'all') return true;
    if (f === 'fed') return e.category === 'fed';
    if (f === 'global') return e.category === 'global';
    if (f === 'other') return e.category === 'politics' || e.category === 'market';
    if (f === 'data') return !['fed', 'global', 'politics', 'market'].includes(e.category);
    return false;
  }

  function eventRow(e) {
    const vals = e.actual
      ? `<span class="ev-act">${esc(e.actual)}</span>${e.consensus ? `<span class="ev-sub">est. ${esc(e.consensus)}</span>` : ''}`
      : `${e.consensus ? `<span class="ev-sub">est. ${esc(e.consensus)}</span>` : ''}${e.previous ? `<span class="ev-sub">prior ${esc(e.previous)}</span>` : ''}`;
    return `<div class="ev cat-${esc(e.category)}">
      <span class="ev-time">${esc(clock12(e.time)) || '—'}</span>
      <span class="ev-main"><b>${esc(e.title)}</b><span class="ev-meta"><i class="imp imp-${e.importance}"></i>${esc(CAT_LABEL[e.category] || e.category)}${e.note ? ` · ${esc(e.note)}` : ''}</span>
        ${e.url ? `<a class="ev-link" href="${esc(e.url)}" target="_blank" rel="noopener">${e.actual ? 'Statement ›' : 'Fed calendar ›'}</a>` : ''}</span>
      <span class="ev-vals">${vals}</span></div>`;
  }

  function earningsRow(day, list) {
    const mine = new Set(state.pa.map((h) => h.sym));
    const sorted = [...list].sort((a, b) => (mine.has(b.symbol) - mine.has(a.symbol)) || (b.cap - a.cap));
    const chip = (x) => `<span class="earn-chip ${mine.has(x.symbol) ? 'mine' : ''}" title="${esc(x.name)} · EPS est. ${esc(x.eps_est || '—')}">${esc(x.symbol)}<small>${x.when === 'pre' ? 'AM' : x.when === 'post' ? 'PM' : ''}</small></span>`;
    return `<details class="ev ev-earn"><summary><span class="ev-time">—</span><span class="ev-main"><b>Earnings: ${list.length} large compan${list.length === 1 ? 'y' : 'ies'}</b>
      <span class="ev-meta">${sorted.slice(0, 8).map(chip).join('')}${list.length > 8 ? ` +${list.length - 8}` : ''}</span></span><span class="ev-vals"><span class="ev-sub">tap for EPS</span></span></summary>
      <ul class="earn-list">${sorted.map((x) => `<li><b class="${mine.has(x.symbol) ? 'hl' : ''}">${esc(x.symbol)}</b> ${esc(x.name)}<span>${x.when === 'pre' ? 'Before open' : x.when === 'post' ? 'After close' : 'Time TBA'} · EPS est. ${esc(x.eps_est || '—')} · yr ago ${esc(x.eps_last_year || '—')}</span></li>`).join('')}</ul></details>`;
  }

  async function renderCalendar() {
    feedEl.classList.add('free');
    const page = document.createElement('div');
    page.className = 'page';
    page.innerHTML = '<div class="loading"><div><div class="spinner"></div>Loading calendar…</div></div>';
    feedEl.appendChild(page);
    await loadSideData();
    await fetchPageQuotes(zqSymbols());
    const draw = () => {
      const cal_ = state.calendar || {};
      const today = todayKey();
      const evs = (cal_.events || []).filter(calMatch);
      const showEarn = ['all', 'earnings'].includes(state.calFilter);
      const earnings = cal_.earnings || [];
      const days = [...new Set([...evs.map((e) => e.date), ...(showEarn ? earnings.map((e) => e.date) : [])])].sort();
      const upcoming = days.filter((d) => d >= today), past = days.filter((d) => d < today).reverse().slice(0, 7);
      const dayLabel = (d) => {
        const diff = Math.round((new Date(d + 'T12:00:00') - new Date(today + 'T12:00:00')) / 86400000);
        const base = new Date(d + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
        return diff === 0 ? `Today · ${base}` : diff === 1 ? `Tomorrow · ${base}` : diff === -1 ? `Yesterday · ${base}` : base;
      };
      const dayBlock = (d) => {
        const items = state.calFilter === 'earnings' ? [] : evs.filter((e) => e.date === d);
        const earn = showEarn ? earnings.filter((e) => e.date === d) : [];
        if (!items.length && !earn.length) return '';
        return `<div class="cal-day"><h3>${esc(dayLabel(d))}</h3>${items.map(eventRow).join('')}${earn.length ? earningsRow(d, earn) : ''}</div>`;
      };
      const sched = (cal_.fomc_schedule || []).filter((m) => m.date >= String(new Date().getFullYear()));
      page.innerHTML = `<div class="page-head"><h1>Calendar</h1><p>Fed meetings, US & global data, big earnings, elections and market dates. Times are ET.</p></div>
        ${fedCard()}
        ${oddsCard()}
        <section class="dash-card"><div class="dash-head"><h2>FOMC meetings</h2><small>● = with projections (dot plot)</small></div>
          <div class="fomc-row">${sched.map((m) => `<span class="fomc-chip ${m.date < today ? 'past' : ''}">${esc(new Date(m.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + (m.date.slice(0, 4) !== String(new Date().getFullYear()) ? ` ’${m.date.slice(2, 4)}` : ''))}${m.sep ? ' ●' : ''}${m.actual ? `<small>${esc(m.actual.replace(' to ', ' → '))}</small>` : ''}</span>`).join('')}</div></section>
        <div class="seg-ctl cal-filters">${CAL_FILTERS.map(([k, l]) => `<button data-f="${k}" class="${state.calFilter === k ? 'on' : ''}">${l}</button>`).join('')}</div>
        <h2 class="cal-sec">Coming up</h2>${upcoming.map(dayBlock).join('') || '<p class="fineprint">Nothing scheduled in this view.</p>'}
        <h2 class="cal-sec">Recent results</h2>${past.map(dayBlock).join('') || '<p class="fineprint">No recent results in this view.</p>'}
        <p class="fineprint">Sources: Federal Reserve, Nasdaq economic & earnings calendars, US Treasury. Earnings shown for companies over $20B plus the app's watchlist.${cal_.generated_at ? ` Updated ${esc(new Date(cal_.generated_at).toLocaleString())}.` : ''}</p>`;
    };
    draw();
    page.addEventListener('click', (e) => {
      const f = e.target.closest('[data-f]');
      if (f) { state.calFilter = f.dataset.f; draw(); return; }
      onPageClick(e);
    });
  }

  // ---------- Fed rate odds (from 30-day fed funds futures) ----------
  // Same math as pipeline/fed_odds.py: each ZQ contract = 100 - average effective fed funds rate for its month.
  const ZQ_CODES = 'FGHJKMNQUVXZ';
  const zqSymbol = (y, m) => `ZQ${ZQ_CODES[m - 1]}${String(y).slice(2)}.CBT`;
  function zqSymbols(months = 10) {
    const out = [];
    let y = new Date().getFullYear(), m = new Date().getMonth() + 1;
    for (let i = 0; i < months; i++) { out.push(zqSymbol(y, m)); if (++m > 12) { m = 1; y++; } }
    return out;
  }

  function fedOdds() {
    const cal_ = state.calendar || {};
    const top = cal_.fed?.last?.result?.high;
    const today = todayKey();
    const meetings = (cal_.fomc_schedule || []).filter((m) => m.date >= today);
    if (top == null || !meetings.length) return [];
    const px = (s) => (pageQuotes[s] || live.quotes[s])?.price;
    const avg = (y, m) => { const p = px(zqSymbol(y, m)); return p ? 100 - p : null; };
    const shift = (y, m, k) => { const t = y * 12 + (m - 1) + k; return [Math.floor(t / 12), (t % 12) + 1]; };
    const meetMonths = new Set(meetings.map((x) => x.date.slice(0, 7)));
    const key = ([y, m]) => `${y}-${String(m).padStart(2, '0')}`;
    const out = [];
    let prevPost = null;
    for (const mt of meetings) {
      const [y, m, d] = mt.date.split('-').map(Number);
      const n = new Date(y, m, 0).getDate();
      const a = avg(y, m);
      if (a == null) break;
      const nxt = shift(y, m, 1), prv = shift(y, m, -1);
      const nextFree = !meetMonths.has(key(nxt)) && avg(...nxt) != null;
      const prevFree = !meetMonths.has(key(prv)) && avg(...prv) != null;
      const after = n - d;
      let pre, post;
      if (nextFree && (after < 1 || prevPost == null || !prevFree)) { post = avg(...nxt); pre = (a * n - post * after) / d; }
      else if (prevFree && after >= 1) { pre = avg(...prv); post = (a * n - pre * d) / after; }
      else if (prevPost != null && after >= 1) { pre = prevPost; post = (a * n - pre * d) / after; }
      else break;
      out.push({ date: mt.date, sep: mt.sep, pre, post, change: (post - pre) * 100 });
      prevPost = post;
    }
    let dist = new Map([[Math.round(top * 100), 1]]);
    for (const o of out) {
      const steps = o.change / 25, k = Math.floor(steps), p = steps - k;
      const moves = [[25 * k, 1 - p], [25 * (k + 1), p]].filter(([, pr]) => pr > 1e-6);
      const nd = new Map();
      for (const [lvl, pr] of dist) for (const [bp, mp] of moves) nd.set(lvl + bp, (nd.get(lvl + bp) || 0) + pr * mp);
      dist = nd;
      o.hold = moves.filter(([bp]) => bp === 0).reduce((s, [, pr]) => s + pr, 0);
      o.hike = moves.filter(([bp]) => bp > 0).reduce((s, [, pr]) => s + pr, 0);
      o.cut = moves.filter(([bp]) => bp < 0).reduce((s, [, pr]) => s + pr, 0);
      o.dist = [...dist].filter(([, pr]) => pr >= 0.005).sort((x, y2) => x[0] - y2[0]);
      o.likely = o.dist.reduce((best, cur) => (cur[1] > best[1] ? cur : best), [0, 0]);
    }
    return out;
  }

  const oddsText = (o) => [['Hold', o.hold], ['Hike', o.hike], ['Cut', o.cut]].filter(([, p]) => p >= 0.005)
    .sort((a, b) => b[1] - a[1]).map(([l, p]) => `${l} ${Math.round(p * 100)}%`).join(' · ');
  const rangeOf = (topBp) => `${((topBp - 25) / 100).toFixed(2)}–${(topBp / 100).toFixed(2)}%`;
  const shortDate = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + (iso.slice(0, 4) !== String(new Date().getFullYear()) ? ` ’${iso.slice(2, 4)}` : '');

  function oddsLine() {
    const odds = fedOdds();
    if (!odds.length) return '';
    const o = odds[0], last = odds[Math.min(odds.length - 1, 5)];
    const nowTop = state.calendar.fed.last.result.high * 100;
    return `<div class="odds-line"><b>Futures odds, ${esc(shortDate(o.date))}:</b> ${esc(oddsText(o))}
      <span>Priced by ${esc(shortDate(last.date))}: ${esc(rangeOf(last.likely[0]))} most likely (${signedNum(last.likely[0] - nowTop, 0)} bp)</span></div>`;
  }

  function oddsCard() {
    const odds = fedOdds().slice(0, 6);
    if (!odds.length) return '';
    const effr = state.calendar?.fed?.effr;
    const W = 320, H = 90, rates = [odds[0].pre, ...odds.map((o) => o.post)];
    const min = Math.min(...rates) - 0.05, max = Math.max(...rates) + 0.05;
    const x = (i) => 14 + (i / (rates.length - 1)) * (W - 28), y = (v) => 8 + (1 - (v - min) / (max - min)) * (H - 26);
    const labels = ['Now', ...odds.map((o) => shortDate(o.date))];
    return `<section class="dash-card"><div class="dash-head"><h2>Rate odds</h2><small>from fed funds futures</small></div>
      <div class="odds-table">${odds.map((o) => `<div class="odds-row">
        <span class="odds-date">${esc(shortDate(o.date))}${o.sep ? ' ●' : ''}</span>
        <span class="odds-bar">${o.cut >= 0.005 ? `<i class="cut" style="width:${o.cut * 100}%">${o.cut >= 0.12 ? Math.round(o.cut * 100) + '%' : ''}</i>` : ''}<i class="hold" style="width:${o.hold * 100}%">${o.hold >= 0.12 ? Math.round(o.hold * 100) + '%' : ''}</i>${o.hike >= 0.005 ? `<i class="hike" style="width:${o.hike * 100}%">${o.hike >= 0.12 ? Math.round(o.hike * 100) + '%' : ''}</i>` : ''}</span>
        <span class="odds-likely">${esc(rangeOf(o.likely[0]))}<small>${Math.round(o.likely[1] * 100)}% likely</small></span></div>`).join('')}</div>
      <div class="curve-legend"><span><i class="lg cut"></i>Cut</span><span><i class="lg hold"></i>Hold</span><span><i class="lg hike"></i>Hike</span><span>● = projections</span></div>
      <svg class="curve" viewBox="0 0 ${W} ${H}"><path class="curve-now" d="${rates.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join('')}"/>
        ${rates.map((v, i) => `<circle class="curve-dot" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="2.6"/><text x="${x(i).toFixed(1)}" y="${H - 3}" text-anchor="middle">${esc(labels[i])}</text>`).join('')}</svg>
      <p class="fineprint">Implied effective fed funds rate after each meeting, ${rates[0].toFixed(2)}% → ${rates[rates.length - 1].toFixed(2)}%.${effr ? ` Current EFFR ${effr.rate.toFixed(2)}% (NY Fed, ${esc(relDate(effr.date))}).` : ''} Method: CME FedWatch-style, using CBOT 30-day fed funds futures from Yahoo Finance; an estimate, not a forecast.</p></section>`;
  }

  // ---------- PA move alerts ----------
  // In-app: checked on every price refresh while the app is open (banner + optional system notification).
  // App closed: GitHub Actions + the free ntfy app (pipeline/alerts.py), set up from the PA tab.
  const alertState = () => {
    const s = store.get('alertSent', {});
    return s.date === todayKey() ? s : { date: todayKey(), sent: {} };
  };

  function checkAlerts() {
    if (!state.pa.length) return;
    const step = state.alertPct;
    const st = alertState();
    const fresh = [];
    for (const h of state.pa) {
      const q = pageQuotes[h.sym] || live.quotes[h.sym];
      if (!q || q.chg == null || !q.time || etDate(q.time) !== etDate(Date.now() / 1000)) continue;
      const level = Math.floor(Math.abs(q.chg) / step);
      const k = `${h.sym}:${q.chg > 0 ? 'up' : 'down'}`;
      if (level < 1 || level <= (st.sent[k] || 0)) continue;
      st.sent[k] = level;
      fresh.push({ sym: h.sym, chg: q.chg, price: q.price, t: Date.now() });
    }
    if (!fresh.length) return;
    store.set('alertSent', st);
    state.alertLog = [...fresh, ...state.alertLog].slice(0, 30);
    store.set('alertLog', state.alertLog);
    const a = fresh[0];
    toast(`🚨 ${a.sym} ${pct(a.chg, 1)} today${fresh.length > 1 ? ` (+${fresh.length - 1} more)` : ''}`);
    if (state.alertNotify && 'Notification' in window && Notification.permission === 'granted') {
      navigator.serviceWorker?.ready.then((reg) => fresh.forEach((x) => reg.showNotification(`${x.sym} ${pct(x.chg, 1)} today`, {
        body: `${x.sym} is at ${fmtLive('usd', x.price)}, ${pct(x.chg)} from yesterday's close.`, icon: 'assets/icons/icon-192.png', tag: x.sym,
      }))).catch(() => {});
    }
  }

  function alertsCard() {
    const today = (state.alertLog || []).filter((a) => new Date(a.t).toDateString() === new Date().toDateString());
    return `<section class="dash-card"><div class="dash-head"><h2>Alerts</h2><small>big moves in your PA stocks</small></div>
      <label class="setting">Alert when a stock moves <select id="alertPct">${[2, 3, 5, 7, 10].map((v) => `<option value="${v}" ${v === state.alertPct ? 'selected' : ''}>±${v}%</option>`).join('')}</select></label>
      <label class="setting">Notifications while the app is open<span class="switch"><input type="checkbox" id="alertNotify" ${state.alertNotify ? 'checked' : ''}><span></span></span></label>
      <button class="btn ghost" id="alertPhone">Get alerts when the app is closed (free) →</button>
      ${today.length ? `<h4 class="alert-h">Today</h4><ul class="alert-log">${today.map((a) => `<li><b>${esc(a.sym)}</b> <span class="${dirClass(a.chg)}">${pct(a.chg, 1)}</span> at ${esc(fmtLive('usd', a.price))}<small>${esc(new Date(a.t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))}</small></li>`).join('')}</ul>` : ''}</section>`;
  }

  function wireAlertsCard(root) {
    root.querySelector('#alertPct')?.addEventListener('change', (e) => { state.alertPct = Number(e.target.value); store.set('alertPct', state.alertPct); toast(`Alerts at ±${state.alertPct}%`); });
    root.querySelector('#alertNotify')?.addEventListener('change', async (e) => {
      if (e.target.checked && 'Notification' in window) {
        const perm = Notification.permission === 'default' ? await Notification.requestPermission() : Notification.permission;
        if (perm !== 'granted') { e.target.checked = false; toast(Notification.permission === 'denied' ? 'Notifications are blocked in your settings' : 'Notifications not allowed'); return; }
      } else if (e.target.checked) { e.target.checked = false; toast('This browser has no notifications; add the app to your home screen first'); return; }
      state.alertNotify = e.target.checked;
      store.set('alertNotify', state.alertNotify);
    });
    root.querySelector('#alertPhone')?.addEventListener('click', openPhoneAlerts);
  }

  function openPhoneAlerts() {
    const tickers = state.pa.map((h) => h.sym).join(',');
    openSheet(`<h3>Phone alerts when the app is closed</h3>
      <p>Free, using the <b>ntfy</b> app (no account). GitHub checks your stocks every ~10 minutes in market hours and sends a push when one moves past the <code>ALERT_PCT</code> size (3% unless you change it), then again at each further step.</p>
      <ol class="steps">
        <li>Install <b>ntfy</b> from the App Store or Google Play.</li>
        <li>In ntfy tap <b>+</b> and subscribe to your private topic. Claude gave you the topic name in chat; it's also the <code>NTFY_TOPIC</code> secret in your GitHub repo.</li>
        <li>Tell GitHub which stocks to watch: copy your list, then paste it as the <code>PA_TICKERS</code> variable.</li>
      </ol>
      <button class="btn primary" id="copyTickers" ${tickers ? '' : 'disabled'}>${tickers ? `Copy my tickers (${esc(tickers)})` : 'Add stocks to PA first'}</button>
      <a class="btn ghost" href="https://github.com/jferaz23/marketreels/settings/variables/actions" target="_blank" rel="noopener">Open GitHub variables →</a>
      <p class="fineprint">Phone alerts use the GitHub settings, separate from the in-app alert size above. Your list on GitHub only changes when you paste it there.</p>`);
    $('#copyTickers')?.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(tickers); toast('Tickers copied 📋'); } catch { toast(tickers); }
    });
  }

  // ---------- feed routing ----------
  let observer;
  function renderFeed(focusId) {
    stopPlayer();
    clearTimeout(pageTimer);
    observer?.disconnect();
    feedEl.innerHTML = '';
    feedEl.scrollTop = 0;
    if (state.tab === 'learn' && !state.course) return renderCourses();
    if (state.tab === 'scroll') return renderScroll();
    if (state.tab === 'board') return renderBoard();
    if (state.tab === 'pa') return renderPA();
    if (state.tab === 'calendar') return renderCalendar();
    feedEl.classList.remove('free');
    state.list = buildList(state.tab);
    if (!state.list.length) {
      feedEl.appendChild(endCard(true));
      return;
    }
    const frag = document.createDocumentFragment();
    state.list.forEach((reel, idx) => frag.appendChild(reelShell(reel, idx)));
    frag.appendChild(endCard(false));
    feedEl.appendChild(frag);

    observer = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting && en.intersectionRatio >= 0.6) activate(en.target);
      });
    }, { root: feedEl, threshold: [0.6] });
    feedEl.querySelectorAll('.reel[data-idx]').forEach((el) => observer.observe(el));

    if (focusId) {
      const el = feedEl.querySelector(`.reel[data-id="${CSS.escape(focusId)}"]`);
      if (el) requestAnimationFrame(() => el.scrollIntoView({ block: 'start' }));
    }
  }

  function endCard(empty) {
    const el = document.createElement('section');
    el.className = 'reel';
    el.style.setProperty('--h', 150);
    const updated = state.feed?.generated_at ? new Date(state.feed.generated_at).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' }) : null;
    const inCourse = state.tab === 'learn' && state.course;
    const msg = inCourse ? ['🎓', 'End of course', 'Nice work. Pick another course to keep going.']
      : empty
        ? (state.tab === 'saved' ? ['🔖', 'Nothing saved yet', 'Tap the bookmark on any reel to keep it here.'] : ['📭', 'No reels here yet', 'New market reels are generated every trading day. Check the Learn tab in the meantime.'])
        : ['🎉', "You're all caught up", 'New reels drop every market day before the open, at midday and after the close.' + (updated ? ` Last update: ${updated}.` : '')];
    el.innerHTML = `<div class="bg"><div class="blob a"></div><div class="blob b"></div><div class="grid"></div></div><div class="shade"></div>
      <div></div><div></div>
      <div class="stage" style="pointer-events:auto"><div class="endcard"><div><div class="emoji">${msg[0]}</div><h2>${msg[1]}</h2><p>${msg[2]}</p>
      <button class="btn primary inline" data-go="learn">${inCourse ? 'All courses →' : 'Keep learning →'}</button>
      <div style="height:10px"></div><button class="linkbtn" data-go="settings">Your taste & settings</button></div></div></div>`;
    el.addEventListener('click', (e) => {
      const go = e.target.closest('[data-go]')?.dataset.go;
      if (go === 'learn') { state.course = null; setTab('learn'); }
      if (go === 'settings') openSettings();
    });
    return el;
  }

  const ICONS = {
    ask: '<svg viewBox="0 0 24 24"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.6A8 8 0 1 1 21 12z"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.3 2.4c-.5.2-.8.6-.8 1.1v.5"/><path d="M12 16.5h.01"/></svg>',
    save: '<svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
    info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><path d="M12 16v-4.5"/><path d="M12 8h.01"/></svg>',
    share: '<svg viewBox="0 0 24 24"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>',
    soundOn: '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/></svg>',
    soundOff: '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M23 9l-6 6"/><path d="M17 9l6 6"/></svg>',
  };

  const rateGroup = (reel, cls = '') => {
    const cur = state.ratings[reel.id]?.v;
    return `<div class="rate ${cls}" role="group" aria-label="Rate this">${[1, 0, -1].map((v) =>
      `<button data-rate="${v}" class="${cur === v ? 'on' : ''}" aria-label="${RATE_LABELS[v]}" title="${RATE_LABELS[v]}">${RATE_ICONS[v]}</button>`).join('')}</div>`;
  };

  function onRate(btn, reel, root, inReel) {
    const v = Number(btn.dataset.rate);
    const now = rateReel(reel, v);
    root.querySelectorAll('[data-rate]').forEach((b) => b.classList.toggle('on', Number(b.dataset.rate) === now));
    btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop');
    if (now === 1) toast('👍 More like this');
    else if (now === 0) toast('Noted: neutral');
    else if (now === -1) {
      toast("👎 Got it, you'll see less like this");
      if (inReel) setTimeout(() => { if (state.player?.reel === reel) root.nextElementSibling?.scrollIntoView({ behavior: 'smooth' }); }, 700);
    }
  }

  function courseInfo(reel) {
    if (reel.category !== 'learn') return null;
    const c = state.courses.find((x) => x.lessons.includes(reel.id));
    return c ? { course: c, n: c.lessons.indexOf(reel.id) + 1 } : null;
  }

  function reelShell(reel, idx) {
    if (reel.kind === 'video') return videoShell(reel, idx);
    const cat = CATEGORIES[reel.category] || CATEGORIES.news;
    const ci = courseInfo(reel);
    const el = document.createElement('section');
    el.className = 'reel';
    el.dataset.idx = idx;
    el.dataset.id = reel.id;
    el.style.setProperty('--h', reel.hue ?? ci?.course.hue ?? cat.hue);
    const bg = reel.bg || {};
    if (bg.type === 'video' || bg.type === 'image') el.classList.add('has-media');
    const bgInner = bg.type === 'video'
      ? `<video muted playsinline loop preload="none" data-src="${esc(bg.src)}" ${bg.poster ? `poster="${esc(bg.poster)}"` : ''}></video>`
      : bg.type === 'image'
        ? `<img alt="" loading="lazy" decoding="async" src="${esc(bg.src)}" onerror="this.closest('.reel').classList.remove('has-media');this.remove()">`
        : '';
    const sources = reel.sources || [];
    const segs = visibleScenes(reel).map(() => '<div class="seg"><i></i></div>').join('');
    el.innerHTML = `
      <div class="bg"><div class="blob a"></div><div class="blob b"></div><div class="grid"></div>${bgInner}</div>
      <div class="shade"></div>
      <div></div>
      <div class="progress">${segs}</div>
      <div class="stage"></div>
      <div class="tapzones"><div data-tap="prev"></div><div data-tap="next"></div></div>
      <div class="paused-ind">❚❚</div>
      <aside class="rail">
        ${rateGroup(reel)}
        <button data-act="ask" aria-label="Ask Claude about this"><span class="ic ask-ic">${ICONS.ask}</span><small>Ask</small></button>
        <button data-act="save" class="${state.savedReels[reel.id] ? 'on' : ''}" aria-label="Save"><span class="ic save-ic">${ICONS.save}</span><small>Save</small></button>
        <button data-act="share" aria-label="Share"><span class="ic">${ICONS.share}</span><small>Share</small></button>
        <button data-act="sound" class="${state.sound ? 'on' : ''}" aria-label="Narration"><span class="ic snd-ic">${state.sound ? ICONS.soundOn : ICONS.soundOff}</span><small>Voice</small></button>
      </aside>
      <footer class="meta">
        <div class="meta-row">
          <span class="chip">${esc(ci ? `Chapter ${ci.n}/${ci.course.lessons.length}` : reel.tag || cat.label)}</span>
          ${reel.ticker ? `<span class="meta-ticker" data-sym="${esc(reel.ticker)}" data-kind="chip">$${esc(reel.ticker)}</span>` : ''}
          <span class="meta-date">${esc(ci ? ci.course.title : relDate(reel.date))}</span>
        </div>
        <p class="meta-title">${esc(plain(reel.title))}</p>
        <div class="meta-links">
          <button class="linkbtn" data-act="info">${sources.length ? `Sources · ${sources.length}` : 'Details'}</button>
          ${bg.credit ? `<span class="meta-date">${esc(bg.credit)}</span>` : ''}
        </div>
        ${reel.category === 'ideas' || reel.disclaimer ? `<div class="disclaimer">${IDEAS_DISCLAIMER}</div>` : ''}
      </footer>`;
    el._reel = reel;
    wireReel(el, reel);
    el.querySelectorAll('.meta-ticker[data-sym]').forEach(paintLive);
    return el;
  }

  function wireReel(el, reel) {
    el.querySelector('.rail').addEventListener('click', (e) => {
      const r = e.target.closest('[data-rate]');
      if (r) return onRate(r, reel, el, true);
      const b = e.target.closest('button[data-act]');
      if (b) onAction(b.dataset.act, b, reel);
    });
    el.querySelector('[data-act="info"]').addEventListener('click', () => openInfo(reel));

    // Tap left/right to change scene, press and hold to pause.
    const zones = el.querySelector('.tapzones');
    let holdTimer = 0, holding = false, startX = 0, startY = 0, moved = false;
    zones.addEventListener('pointerdown', (e) => {
      startX = e.clientX; startY = e.clientY; moved = false; holding = false;
      holdTimer = setTimeout(() => { holding = true; state.player?.setPaused(true); }, 260);
    });
    zones.addEventListener('pointermove', (e) => {
      if (Math.abs(e.clientX - startX) > 10 || Math.abs(e.clientY - startY) > 10) { moved = true; clearTimeout(holdTimer); }
    });
    const release = () => { clearTimeout(holdTimer); if (holding) state.player?.setPaused(false); };
    zones.addEventListener('pointerup', release);
    zones.addEventListener('pointercancel', release);
    zones.addEventListener('pointerleave', release);
    zones.addEventListener('click', (e) => {
      if (holding || moved) { holding = false; return; }
      const p = state.player;
      if (!p || p.el !== el) return;
      e.target.dataset.tap === 'prev' ? p.prev() : p.next();
    });
    zones.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  function toggleSave(reel) {
    if (state.savedReels[reel.id]) { delete state.savedReels[reel.id]; toast('Removed from Saved'); }
    else { state.savedReels[reel.id] = { ...reel, _savedAt: Date.now() }; toast('Saved 🔖'); }
    store.set('savedReels', state.savedReels);
    return !!state.savedReels[reel.id];
  }

  function onAction(act, btn, reel) {
    if (act === 'save') btn.classList.toggle('on', toggleSave(reel));
    else if (act === 'ask') openChat(reel);
    else if (act === 'share') shareReel(reel);
    else if (act === 'sound') {
      setSound(!state.sound);
      if (state.sound) state.player?.show(state.player.i);
    }
    const ic = btn.querySelector('.ic');
    if (ic) { ic.classList.remove('pop'); void ic.offsetWidth; ic.classList.add('pop'); }
  }

  async function shareReel(reel) {
    const url = location.origin + location.pathname + '#r=' + encodeURIComponent(reel.id);
    try {
      if (navigator.share) { await navigator.share({ title: plain(reel.title), text: plain(reel.title), url }); return; }
      await navigator.clipboard.writeText(url);
      toast('Link copied');
    } catch { /* user cancelled */ }
  }

  function setSound(on) {
    state.sound = on;
    store.set('sound', on);
    if (!on) speech.cancel();
    document.querySelectorAll('[data-act="sound"]').forEach((b) => {
      b.classList.toggle('on', on);
      b.querySelector('.ic').innerHTML = on ? ICONS.soundOn : ICONS.soundOff;
    });
    if (state.player instanceof VideoPlayer) state.player.applySound();
    toast(on ? 'Sound on 🔊' : 'Sound off');
  }

  // ---------- media ----------
  function prepareMedia(activeEl) {
    const reels = [...feedEl.querySelectorAll('.reel[data-idx]')];
    const i = reels.indexOf(activeEl);
    reels.forEach((el, j) => {
      const v = el.querySelector('video');
      if (!v) return;
      if (Math.abs(j - i) <= 1 && !v.src && v.dataset.src) { v.src = v.dataset.src; v.preload = 'auto'; }
      if (j === i) v.play().catch(() => {});
      else v.pause();
    });
  }

  // ---------- narration ----------
  const speech = {
    voice: null,
    token: 0,
    supported: 'speechSynthesis' in window,
    pickVoice() {
      if (!this.supported) return;
      const voices = speechSynthesis.getVoices().filter((v) => /^en[-_]/i.test(v.lang));
      const prefs = [/natural/i, /neural/i, /Samantha/, /Ava/, /Google US English/, /Aria|Jenny|Guy/, /en[-_]US/i];
      for (const p of prefs) {
        const v = voices.find((x) => p.test(x.name) || p.test(x.lang));
        if (v) { this.voice = v; return; }
      }
      this.voice = voices[0] || null;
    },
    speak(text, onEnd) {
      if (!this.supported || !state.sound || !text) { onEnd(); return; }
      const token = ++this.token;
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      if (this.voice) u.voice = this.voice;
      u.rate = state.rate;
      const done = () => { if (token === this.token) onEnd(); };
      u.onend = done;
      u.onerror = done;
      // Chrome drops an utterance queued in the same tick as cancel().
      setTimeout(() => { if (token === this.token) speechSynthesis.speak(u); }, 60);
    },
    cancel() { this.token++; if (this.supported) speechSynthesis.cancel(); },
    pause() { if (this.supported) speechSynthesis.pause(); },
    resume() { if (this.supported) speechSynthesis.resume(); },
  };
  if (speech.supported) {
    speech.pickVoice();
    speechSynthesis.onvoiceschanged = () => speech.pickVoice();
  }

  function sceneSpeech(scene) {
    if (scene.say) return plain(scene.say);
    const parts = [scene.headline, scene.body, scene.question];
    if (scene.kind === 'bullets') parts.push(...(scene.items || []));
    if (scene.kind === 'number') parts.splice(1, 0, `${scene.value}. ${scene.caption || ''}`);
    if (scene.kind === 'quiz') parts.push(...(scene.options || []).map((o, i) => `${'ABCD'[i]}: ${o}.`));
    if (scene.kind === 'blank') parts.push('Fill in the blank. ' + String(scene.text).replace('___', 'blank'));
    if (scene.kind === 'chart' && scene.note) parts.push(scene.note);
    return parts.filter(Boolean).map(plain).join('. ').replace(/\.\s*\./g, '.');
  }

  function sceneDuration(scene) {
    const words = sceneSpeech(scene).split(/\s+/).length;
    let s = 2.6 + words * 0.36;
    if (scene.kind === 'chart' || scene.kind === 'stats' || scene.kind === 'bars') s += 2;
    return Math.min(16, Math.max(4.5, s)) * 1000;
  }

  // ---------- scene rendering ----------
  let chartUid = 0;
  function chartSVG(points) {
    const w = 320, h = 150, pad = 8;
    const vals = points.filter((v) => v != null);
    if (vals.length < 2) return '';
    const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
    const x = (i) => pad + (i / (points.length - 1)) * (w - pad * 2);
    const y = (v) => pad + (1 - (v - min) / span) * (h - pad * 2);
    let d = '';
    points.forEach((v, i) => { if (v != null) d += (d ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); });
    const up = vals[vals.length - 1] >= vals[0];
    const color = up ? 'var(--up)' : 'var(--down)';
    const id = 'cg' + ++chartUid;
    const lx = x(points.length - 1), ly = y(vals[vals.length - 1]);
    return `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="price chart">
      <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${up ? '#2bd576' : '#ff5468'}" stop-opacity=".35"/><stop offset="1" stop-color="${up ? '#2bd576' : '#ff5468'}" stop-opacity="0"/></linearGradient></defs>
      <path class="area" d="${d}L${lx.toFixed(1)} ${h}L${x(0).toFixed(1)} ${h}Z" fill="url(#${id})"/>
      <path class="line" d="${d}" pathLength="1" stroke="${color}"/>
      <circle class="pulse" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="4" fill="${color}"/>
      <circle class="dot" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="4" fill="${color}"/>
    </svg>`;
  }

  // Fill-in-the-blank options are stored answer-first; show them in a stable shuffled order.
  function blankOrder(scene, seed) {
    return (scene.options || []).map((o, i) => ({ o, i })).sort((a, b) => hashStr(seed + a.o) - hashStr(seed + b.o));
  }

  function renderScene(scene, reel, index) {
    const node = buildScene(scene, reel, index);
    node.querySelectorAll('[data-sym]').forEach(paintLive);
    return node;
  }

  function buildScene(scene, reel, index) {
    const cat = CATEGORIES[reel.category] || CATEGORIES.news;
    const div = document.createElement('div');
    div.className = 'scene k-' + (scene.kind || 'text');
    const art = index === 0 && reel.art ? artSVG(reel.art, 'hero') : '';
    const eyebrow = scene.eyebrow ? `<div class="eyebrow">${esc(scene.eyebrow)}</div>` : (index === 0 ? `<div class="eyebrow">${esc(reel.tag || cat.label)}</div>` : '');
    const head = scene.headline ? `<h2 class="headline">${rich(scene.headline)}</h2>` : '';
    const body = scene.body ? String(scene.body).split('\n\n').map((p) => `<p class="body">${rich(p)}</p>`).join('') : '';
    const after = (html) => (html ? `<div style="height:12px"></div>${html}` : '');
    let main = '';
    switch (scene.kind) {
      case 'number':
        main = `<div class="bignum ${dirClass(scene.change)}">${esc(scene.value)}</div>${scene.caption ? `<div class="bignum-cap">${rich(scene.caption)}</div>` : ''}`;
        div.innerHTML = eyebrow + head + main + after(body);
        return div;
      case 'stats':
        main = `<div class="stats">${(scene.items || []).map((it, i) => `
          <div class="tile" style="animation-delay:${0.08 * i}s" ${it.sym ? `data-sym="${esc(it.sym)}" data-fmt="${esc(it.fmt || 'num')}" data-kind="tile" data-date="${esc(reel.date || '')}"` : ''}><div class="k">${esc(it.label)}</div><div class="v">${esc(it.value)}</div>
          ${it.change != null ? `<div class="c ${dirClass(it.change)}">${arrow(it.change)} ${pct(it.change)}</div>` : ''}
          ${it.note ? `<div class="n">${esc(it.note)}</div>` : ''}</div>`).join('')}</div>`;
        div.innerHTML = eyebrow + head + main + after(body);
        return div;
      case 'chart': {
        const dates = scene.dates || [];
        const chg = scene.change;
        main = `<div class="chart-wrap"><div class="chart-top" ${scene.sym ? `data-sym="${esc(scene.sym)}" data-fmt="${esc(scene.fmt || 'num')}" data-kind="chart" data-first="${esc(scene.first ?? '')}" data-date="${esc(reel.date || '')}"` : ''}><span class="chart-label">${esc(scene.label || '')}</span>
          <span><span class="chart-last">${esc(scene.last ?? '')}</span> <span class="chart-chg ${dirClass(chg)}">${chg != null ? pct(chg) : ''}</span></span></div>
          ${chartSVG(scene.points || [])}
          ${dates.length ? `<div class="chart-axis"><span>${esc(dates[0])}</span><span>${esc(dates[dates.length - 1])}</span></div>` : ''}</div>
          ${scene.note ? `<div class="chart-note">${rich(scene.note)}</div>` : ''}`;
        div.innerHTML = eyebrow + head + main;
        return div;
      }
      case 'bars': {
        const items = scene.items || [];
        const allPos = items.every((it) => it.value >= 0) && scene.mode !== 'diverging';
        const max = Math.max(...items.map((it) => Math.abs(it.value)), 0.0001);
        main = `<div class="bars">${items.map((it, i) => {
          const wPct = (Math.abs(it.value) / max) * (allPos ? 100 : 50);
          const cls = it.value >= 0 ? 'pos' : 'neg';
          const shown = it.display ?? (scene.unit === '%' || scene.unit == null ? pct(it.value) : it.value + (scene.unit || ''));
          return `<div class="bar-row"><span class="lbl">${esc(it.label)}</span><div class="bar-track ${allPos ? 'pos-only' : ''}"><div class="bar ${cls}" style="width:${wPct}%;animation-delay:${0.06 * i}s"></div></div><span class="val ${allPos ? '' : dirClass(it.value)}">${esc(shown)}</span></div>`;
        }).join('')}</div>`;
        div.innerHTML = eyebrow + head + main + after(body);
        return div;
      }
      case 'bullets':
        main = `<ul class="bullets ${scene.style || ''}">${(scene.items || []).map((t, i) => `<li style="animation-delay:${0.25 + 0.35 * i}s">${rich(t)}</li>`).join('')}</ul>`;
        div.innerHTML = eyebrow + head + body + main;
        return div;
      case 'quiz':
        div.innerHTML = `<div class="eyebrow">Quick quiz · +10 XP</div><p class="quiz-q">${rich(scene.question)}</p>
          <div class="quiz-opts interactive">${(scene.options || []).map((o, i) => `<button class="quiz-opt" data-i="${i}">${'ABCD'[i]}. ${esc(o)}</button>`).join('')}</div>
          <div class="quiz-hint">Tap an answer to continue</div>`;
        return div;
      case 'blank': {
        const [pre, post] = String(scene.text).split('___');
        div.innerHTML = `<div class="eyebrow">Key takeaway · fill the blank · +5 XP</div>
          <p class="blank-text">${rich(pre)}<span class="blank-slot">&nbsp;</span>${rich(post ?? '')}</p>
          <div class="blank-opts interactive">${blankOrder(scene, reel.id).map(({ o, i }) => `<button class="blank-opt" data-i="${i}">${esc(o)}</button>`).join('')}</div>
          <div class="quiz-hint">Tap the word that fits</div>`;
        return div;
      }
      default:
        div.innerHTML = art + eyebrow + head + body;
        return div;
    }
  }

  // Shared answer logic for quiz + fill-in-the-blank, used by the reel player and the scroll cards.
  function wireChoice(node, scene, key, onReveal) {
    const isBlank = scene.kind === 'blank';
    const opts = node.querySelector(isBlank ? '.blank-opts' : '.quiz-opts');
    const reveal = (choice, award) => {
      opts.classList.add('answered');
      opts.querySelectorAll('button').forEach((b) => {
        const j = Number(b.dataset.i);
        b.disabled = true;
        if (j === scene.answer) b.classList.add('right');
        else if (j === choice) b.classList.add('wrong');
      });
      const correct = choice === scene.answer;
      node.querySelector('.quiz-hint')?.remove();
      if (isBlank) {
        const slot = node.querySelector('.blank-slot');
        slot.textContent = scene.options[scene.answer];
        slot.classList.add(correct ? 'right' : 'wrong', 'filled');
      }
      const explain = isBlank ? '' : scene.explain || '';
      if (!isBlank || !correct) {
        const ex = document.createElement('div');
        ex.className = 'quiz-explain';
        ex.innerHTML = `<b class="${correct ? 'up' : 'down'}">${correct ? 'Correct!' : 'Not quite.'}</b> ${isBlank ? `The answer is <b>${esc(scene.options[scene.answer])}</b>.` : rich(explain)}`;
        node.appendChild(ex);
      }
      if (award && correct) addXP(isBlank ? 5 : 10);
      onReveal?.(correct, explain);
    };
    if (key in state.answered) { reveal(state.answered[key], false); return true; }
    opts.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b || opts.classList.contains('answered')) return;
      e.stopPropagation();
      const choice = Number(b.dataset.i);
      state.answered[key] = choice;
      store.set('answered', state.answered);
      reveal(choice, true);
    });
    return false;
  }

  // ---------- player ----------
  class Player {
    constructor(el, reel) {
      this.el = el;
      this.reel = reel;
      this.scenes = visibleScenes(reel);
      this.stage = el.querySelector('.stage');
      this.segs = [...el.querySelectorAll('.seg')];
      this.i = 0;
      this.paused = false;
      this.waiting = false;
      this.speaking = false;
      this.raf = 0;
    }
    start() {
      if (!state.seen.has(this.reel.id)) {
        state.seen.add(this.reel.id);
        store.set('seen', [...state.seen].slice(-3000));
      }
      this.show(0);
    }
    stop() {
      cancelAnimationFrame(this.raf);
      speech.cancel();
      this.el.classList.remove('paused');
    }
    setPaused(p) {
      this.paused = p;
      this.el.classList.toggle('paused', p);
      const v = this.el.querySelector('video');
      if (p) { speech.pause(); v?.pause(); } else { speech.resume(); v?.play().catch(() => {}); this.last = performance.now(); }
    }
    show(i) {
      if (!this.scenes.length) return;
      this.i = Math.max(0, Math.min(i, this.scenes.length - 1));
      const scene = this.scenes[this.i];
      if (this.i === this.scenes.length - 1) countCompletion(this.reel);
      const old = this.stage.querySelector('.scene:not(.out)');
      if (old) { old.classList.add('out'); setTimeout(() => old.remove(), 260); }
      const node = renderScene(scene, this.reel, this.i);
      this.stage.appendChild(node);
      this.segs.forEach((s, j) => { s.classList.toggle('done', j < this.i); s.firstChild.style.width = j < this.i ? '100%' : '0'; });
      this.elapsed = 0;
      this.duration = sceneDuration(scene);
      this.waiting = false;
      this.speaking = true;
      const say = (text) => { this.speaking = true; speech.speak(text, () => { this.speaking = false; }); };
      if (scene.kind === 'quiz' || scene.kind === 'blank') {
        // Wait for an answer, then read the explanation (answered earlier: reveal and read it right away).
        this.waiting = true;
        const already = wireChoice(node, scene, this.reel.id + ':' + this.i, (correct, explain) => {
          this.waiting = false;
          this.elapsed = 0;
          this.duration = Math.max(4000, 2500 + (explain || '').split(/\s+/).length * 330);
          say((correct ? 'Correct! ' : 'Not quite. ') + plain(explain || `The answer is ${scene.options[scene.answer]}.`));
        });
        if (!already) say(sceneSpeech(scene));
      } else {
        say(sceneSpeech(scene));
      }
      this.last = performance.now();
      cancelAnimationFrame(this.raf);
      this.raf = requestAnimationFrame((t) => this.tick(t));
    }
    tick(now) {
      const dt = now - this.last;
      this.last = now;
      if (!this.paused && !this.waiting) this.elapsed += dt;
      const p = Math.min(1, this.elapsed / this.duration);
      const seg = this.segs[this.i];
      if (seg) seg.firstChild.style.width = (p * 100).toFixed(2) + '%';
      // With narration on, hold the scene until the voice finishes.
      if (p >= 1 && !this.paused && !this.waiting && (!state.sound || !this.speaking)) { this.next(); return; }
      this.raf = requestAnimationFrame((t) => this.tick(t));
    }
    next() {
      if (this.i < this.scenes.length - 1) this.show(this.i + 1);
      else this.finish();
    }
    prev() {
      if (this.i === 0 || this.elapsed > 2500) this.show(this.i);
      else this.show(this.i - 1);
    }
    finish() {
      cancelAnimationFrame(this.raf);
      if (this.segs.length) this.segs[this.segs.length - 1].classList.add('done');
      if (state.autoplay) {
        const nextEl = this.el.nextElementSibling;
        if (nextEl) { nextEl.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
      }
      // Loop back like a short video would.
      setTimeout(() => { if (state.player === this) this.show(0); }, 1200);
    }
  }

  function activate(el) {
    if (state.player?.el === el) return;
    stopPlayer();
    if (!el._reel) return;
    prepareMedia(el);
    state.player = el._reel.kind === 'video' ? new VideoPlayer(el, el._reel) : new Player(el, el._reel);
    state.player.start();
  }

  function stopPlayer() {
    state.player?.stop();
    state.player = null;
  }

  // ---------- Video reels (real clips from news outlets' YouTube channels) ----------
  // Played in YouTube's embedded player (privacy-enhanced domain). A transparent layer above the player keeps
  // swipes scrolling the feed; taps pause/play through the player's postMessage API.
  const YT_ORIGIN = 'https://www.youtube-nocookie.com';
  const ytThumb = (id) => `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
  const fmtDur = (s) => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '');
  const agoText = (iso) => {
    const h = (Date.now() - Date.parse(iso)) / 36e5;
    if (!iso || !Number.isFinite(h)) return '';
    return h < 1 ? `${Math.max(1, Math.round(h * 60))} min ago` : h < 24 ? `${Math.round(h)}h ago` : `${Math.round(h / 24)}d ago`;
  };

  function videoShell(reel, idx) {
    const v = reel.video;
    const el = document.createElement('section');
    el.className = `reel vreel ${v.shorts ? 'short' : 'wide'}`;
    el.dataset.idx = idx;
    el.dataset.id = reel.id;
    el.style.setProperty('--h', CATEGORIES.video.hue);
    el.innerHTML = `
      <div class="bg"><img class="vbg" alt="" loading="lazy" src="${esc(ytThumb(v.id))}"></div>
      <div class="shade"></div>
      <div class="vstage"><div class="vframe"><img class="vposter" alt="" loading="lazy" src="${esc(ytThumb(v.id))}"><span class="vspin"></span></div></div>
      <div class="vtap"></div>
      <div class="vprog"><i></i></div>
      <div class="paused-ind">▶</div>
      <aside class="rail">
        ${rateGroup(reel)}
        <button data-act="ask" aria-label="Ask Claude about this"><span class="ic ask-ic">${ICONS.ask}</span><small>Ask</small></button>
        <button data-act="save" class="${state.savedReels[reel.id] ? 'on' : ''}" aria-label="Save"><span class="ic save-ic">${ICONS.save}</span><small>Save</small></button>
        <button data-act="share" aria-label="Share"><span class="ic">${ICONS.share}</span><small>Share</small></button>
        <button data-act="sound" class="${state.sound ? 'on' : ''}" aria-label="Sound"><span class="ic snd-ic">${state.sound ? ICONS.soundOn : ICONS.soundOff}</span><small>Sound</small></button>
      </aside>
      <footer class="meta">
        <div class="meta-row"><span class="chip">${esc(v.channel)}</span>
          ${reel.ticker ? `<span class="meta-ticker" data-sym="${esc(reel.ticker)}" data-kind="chip">$${esc(reel.ticker)}</span>` : ''}
          <span class="meta-date">${esc([v.shorts ? 'Short' : '', fmtDur(v.seconds), agoText(reel.ts)].filter(Boolean).join(' · '))}</span></div>
        <p class="meta-title">${esc(reel.title)}</p>
        <div class="meta-links"><button class="linkbtn" data-act="info">Details</button>
          <a class="linkbtn" href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">Watch on YouTube</a></div>
      </footer>`;
    el._reel = reel;
    el.querySelector('.rail').addEventListener('click', (e) => {
      const r = e.target.closest('[data-rate]');
      if (r) return onRate(r, reel, el, true);
      const b = e.target.closest('button[data-act]');
      if (b) onAction(b.dataset.act, b, reel);
    });
    el.querySelector('[data-act="info"]').addEventListener('click', () => openInfo(reel));
    el.querySelector('.vtap').addEventListener('click', () => { if (state.player?.el === el) state.player.toggle(); });
    el.querySelectorAll('.meta-ticker[data-sym]').forEach(paintLive);
    return el;
  }

  class VideoPlayer {
    constructor(el, reel) {
      this.el = el;
      this.reel = reel;
      this.v = reel.video;
      this.frame = null;
      this.paused = false;
      this.dur = this.v.seconds || 0;
      this.counted = false;
    }
    start() {
      if (!state.seen.has(this.reel.id)) { state.seen.add(this.reel.id); store.set('seen', [...state.seen].slice(-3000)); }
      const p = new URLSearchParams({ autoplay: 1, mute: 1, playsinline: 1, controls: 0, rel: 0, modestbranding: 1, iv_load_policy: 3, enablejsapi: 1, origin: location.origin });
      if (this.v.shorts) { p.set('loop', 1); p.set('playlist', this.v.id); }
      const f = document.createElement('iframe');
      f.src = `${YT_ORIGIN}/embed/${encodeURIComponent(this.v.id)}?${p}`;
      f.allow = 'autoplay; encrypted-media; picture-in-picture';
      f.title = this.reel.title;
      f.addEventListener('load', () => {
        this.post({ event: 'listening', id: this.v.id, channel: 'widget' });
        setTimeout(() => this.applySound(), 300);
      });
      this.el.querySelector('.vframe').appendChild(f);
      this.el.classList.add('playing');
      this.frame = f;
      // Reveal the player once it reports playback (or after 4s regardless), so loading shows the thumbnail, not black.
      setTimeout(() => { if (this.frame === f) this.el.classList.add('started'); }, 4000);
    }
    post(msg) { try { this.frame?.contentWindow?.postMessage(JSON.stringify(msg), YT_ORIGIN); } catch { /* player not ready */ } }
    cmd(func, args = []) { this.post({ event: 'command', func, args }); }
    applySound() { this.cmd(state.sound ? 'unMute' : 'mute'); if (!this.paused) this.cmd('playVideo'); }
    show() { this.applySound(); } // called when the sound button toggles
    setPaused(p) {
      this.paused = p;
      this.el.classList.toggle('paused', p);
      this.cmd(p ? 'pauseVideo' : 'playVideo');
    }
    toggle() { this.setPaused(!this.paused); }
    onInfo(info) {
      if (info.duration) this.dur = info.duration;
      if (info.currentTime != null && this.dur) {
        const frac = Math.min(1, info.currentTime / this.dur);
        this.el.querySelector('.vprog i').style.width = (frac * 100).toFixed(1) + '%';
        if (!this.counted && (frac > 0.6 || info.currentTime > 45)) { this.counted = true; countCompletion(this.reel); }
      }
      if (info.playerState === 1) this.el.classList.add('started');
      if (info.playerState === 0 && !this.v.shorts) this.finish();
    }
    next() { this.el.nextElementSibling?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    prev() { this.cmd('seekTo', [0, true]); }
    finish() { if (state.autoplay) this.next(); }
    stop() {
      this.frame?.remove();
      this.frame = null;
      this.el.classList.remove('playing', 'started', 'paused');
    }
  }

  window.addEventListener('message', (e) => {
    if (!/youtube(-nocookie)?\.com$/.test(new URL(e.origin || 'http://x').hostname)) return;
    const p = state.player;
    if (!(p instanceof VideoPlayer) || e.source !== p.frame?.contentWindow) return;
    let d;
    try { d = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch { return; }
    if (d?.event === 'onReady') p.applySound();
    if (d?.event === 'infoDelivery' && d.info) p.onInfo(d.info);
  });

  function videoCard(reel) {
    const v = reel.video;
    const card = document.createElement('article');
    card.className = 'card vcard';
    card.style.setProperty('--h', CATEGORIES.video.hue);
    card.innerHTML = `
      <div class="vthumb ${v.shorts ? 'short' : ''}"><img alt="" loading="lazy" src="${esc(ytThumb(v.id))}"><span class="vplay-btn">▶</span>
        ${v.seconds ? `<span class="vdur">${esc(fmtDur(v.seconds))}</span>` : ''}</div>
      <header class="card-head"><div class="card-head-in"><div class="meta-row"><span class="chip">${esc(v.channel)}</span>
        ${reel.ticker ? `<span class="meta-ticker" data-sym="${esc(reel.ticker)}" data-kind="chip">$${esc(reel.ticker)}</span>` : ''}<span class="meta-date">${esc(agoText(reel.ts))}</span></div>
        <h3 class="card-title">${esc(reel.title)}</h3></div></header>
      <footer class="card-foot card-end">${rateGroup(reel, 'inline')}
        <div class="card-actions"><button data-act="ask" class="ask-pill" aria-label="Ask Claude about this">${ICONS.ask}<span>Ask</span></button>
        <button data-act="save" class="${state.savedReels[reel.id] ? 'on' : ''}" aria-label="Save">${ICONS.save}</button>
        <button data-act="share" aria-label="Share">${ICONS.share}</button>
        <button data-act="info" aria-label="Details">${ICONS.info}</button></div></footer>`;
    card.querySelector('.vthumb').addEventListener('click', (e) => {
      const box = e.currentTarget;
      if (box.querySelector('iframe')) return;
      const p = new URLSearchParams({ autoplay: 1, playsinline: 1, rel: 0, modestbranding: 1 });
      box.innerHTML = `<iframe src="${YT_ORIGIN}/embed/${encodeURIComponent(v.id)}?${p}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="${esc(reel.title)}"></iframe>`;
      countCompletion(reel);
    });
    card.querySelector('.card-foot').addEventListener('click', (e) => {
      const r = e.target.closest('[data-rate]');
      if (r) return onRate(r, reel, card, false);
      const b = e.target.closest('[data-act]');
      if (!b) return;
      if (b.dataset.act === 'save') b.classList.toggle('on', toggleSave(reel));
      if (b.dataset.act === 'ask') openChat(reel);
      if (b.dataset.act === 'share') shareReel(reel);
      if (b.dataset.act === 'info') openInfo(reel);
    });
    card._reel = reel;
    card.querySelector('.card-end')._reel = reel;
    card.querySelectorAll('.meta-ticker[data-sym]').forEach(paintLive);
    return card;
  }

  // Videos first (TikTok-style), with the data reels that carry real numbers in between.
  function rankVideos() {
    const profile = tasteProfile();
    const mine = new Set(state.pa.map((h) => h.sym));
    return (state.videos || []).filter((r) => !disliked(r))
      .map((r) => ({ r, k: -(r.score || 0) - ((r.tickers || []).some((t) => mine.has(t)) ? 4 : 0) + (state.seen.has(r.id) ? 40 : 0) - prefScore(r, profile) * 12 }))
      .sort((a, b) => a.k - b.k).map((x) => x.r);
  }

  // ---------- Learn: courses ----------
  function renderCourses() {
    feedEl.classList.add('free');
    const totalDone = state.lessons.filter((l) => state.completed.has(l.id)).length;
    const page = document.createElement('div');
    page.className = 'page';
    page.innerHTML = `<div class="page-head"><h1>Courses</h1><p>Bite-size chapters, 2 minutes or less each. ${totalDone}/${state.lessons.length} chapters complete.</p></div>` +
      state.courses.map((c) => {
        const lessons = c.lessons.map((id) => state.lessons.find((l) => l.id === id)).filter(Boolean);
        const done = lessons.filter((l) => state.completed.has(l.id)).length;
        const next = lessons.find((l) => !state.completed.has(l.id)) || lessons[0];
        return `<section class="course" style="--h:${c.hue}">
          <div class="course-top">${artSVG(c.art, 'course-art')}<div><h2>${esc(c.title)}</h2><p>${esc(c.desc)}</p></div></div>
          <div class="course-prog"><div class="bar-fill" style="width:${(done / lessons.length) * 100}%"></div></div>
          <div class="course-meta">${done}/${lessons.length} chapters${done === lessons.length ? ' · 🎓 Complete' : ''}</div>
          <ol class="chapters">${lessons.map((l, i) => `<li><button data-course="${c.id}" data-lesson="${l.id}">
            <span class="ch-n ${state.completed.has(l.id) ? 'done' : ''}">${state.completed.has(l.id) ? '✓' : i + 1}</span>
            <span class="ch-t">${esc(l.title)}</span><span class="ch-go">›</span></button></li>`).join('')}</ol>
          <button class="btn primary course-go" data-course="${c.id}" data-lesson="${next.id}">${done === 0 ? 'Start course' : done === lessons.length ? 'Review course' : 'Continue'} →</button>
        </section>`;
      }).join('');
    page.addEventListener('click', (e) => {
      const b = e.target.closest('[data-course]');
      if (!b) return;
      state.course = b.dataset.course;
      renderTabs();
      renderFeed(b.dataset.lesson);
    });
    feedEl.appendChild(page);
  }

  // ---------- Scroll: free-scrolling info cards ----------
  let scrollObserver, seenObserver;
  function renderScroll() {
    feedEl.classList.add('free');
    scrollObserver?.disconnect();
    seenObserver?.disconnect();
    const list = buildList('scroll');
    const page = document.createElement('div');
    page.className = 'page';
    page.innerHTML = '<div class="page-head"><h1>Scroll</h1><p>Everything in one feed: read at your own pace. Rate cards to tune what you see.</p></div>';
    const sentinel = document.createElement('div');
    sentinel.className = 'sentinel';
    page.appendChild(sentinel);
    feedEl.appendChild(page);
    let cursor = 0;
    seenObserver = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting && en.target._reel) {
          const r = en.target._reel;
          if (!state.seen.has(r.id)) { state.seen.add(r.id); store.set('seen', [...state.seen].slice(-3000)); }
          countCompletion(r);
          seenObserver.unobserve(en.target);
        }
      });
    }, { root: feedEl, threshold: 0.75 });
    const more = () => {
      const batch = list.slice(cursor, cursor + 8);
      cursor += batch.length;
      batch.forEach((r) => {
        const card = infoCard(r);
        page.insertBefore(card, sentinel);
        seenObserver.observe(card.querySelector('.card-end'));
      });
      if (cursor >= list.length) {
        scrollObserver.disconnect();
        sentinel.innerHTML = `<div class="endcard small"><div class="emoji">🎉</div><h2>That's everything</h2><p>New cards arrive every market day.</p></div>`;
      }
    };
    scrollObserver = new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) more(); }, { root: feedEl, rootMargin: '600px' });
    more();
    scrollObserver.observe(sentinel);
  }

  function infoCard(reel) {
    if (reel.kind === 'video') return videoCard(reel);
    const cat = CATEGORIES[reel.category] || CATEGORIES.news;
    const ci = courseInfo(reel);
    const card = document.createElement('article');
    card.className = 'card';
    card.style.setProperty('--h', reel.hue ?? ci?.course.hue ?? cat.hue);
    const scenes = visibleScenes(reel);
    const PREVIEW = 3;
    const img = reel.bg?.type === 'image' ? reel.bg.src : reel.bg?.poster;
    card.innerHTML = `
      <header class="card-head">${img ? `<img class="card-img" alt="" loading="lazy" src="${esc(img)}" onerror="this.remove()">` : ''}
        <div class="card-head-in"><div class="meta-row"><span class="chip">${esc(ci ? `Chapter ${ci.n} · ${ci.course.title}` : reel.tag || cat.label)}</span>
        ${reel.ticker ? `<span class="meta-ticker" data-sym="${esc(reel.ticker)}" data-kind="chip">$${esc(reel.ticker)}</span>` : ''}<span class="meta-date">${esc(ci ? '' : relDate(reel.date))}</span></div>
        <h3 class="card-title">${rich(reel.title)}</h3></div>${artSVG(reel.art, 'card-art')}</header>
      <div class="card-body"></div>
      ${scenes.length > PREVIEW ? `<button class="card-more">Show ${scenes.length - PREVIEW} more ▾</button>` : ''}
      <footer class="card-foot card-end">${rateGroup(reel, 'inline')}
        <div class="card-actions"><button data-act="ask" class="ask-pill" aria-label="Ask Claude about this">${ICONS.ask}<span>Ask</span></button>
        <button data-act="save" class="${state.savedReels[reel.id] ? 'on' : ''}" aria-label="Save">${ICONS.save}</button>
        <button data-act="share" aria-label="Share">${ICONS.share}</button>
        <button data-act="info" aria-label="Sources and details">${ICONS.info}</button></div></footer>
      ${reel.category === 'ideas' || reel.disclaimer ? `<div class="disclaimer card-disc">${IDEAS_DISCLAIMER}</div>` : ''}`;
    const body = card.querySelector('.card-body');
    scenes.forEach((s, i) => {
      // Skip the title scene's headline when it repeats the card title.
      const scene = i === 0 && s.kind === 'title' && plain(s.headline) === plain(reel.title) ? { ...s, headline: '' } : s;
      if (i === 0 && !scene.headline && !scene.body) return;
      const node = renderScene({ ...scene, eyebrow: i === 0 ? scene.eyebrow : undefined }, { ...reel, art: null }, i === 0 ? 1 : i);
      node.classList.add('static');
      if (i >= PREVIEW) node.hidden = true;
      if (s.kind === 'quiz' || s.kind === 'blank') wireChoice(node, s, reel.id + ':' + i);
      body.appendChild(node);
    });
    card.querySelector('.card-more')?.addEventListener('click', (e) => {
      body.querySelectorAll('.scene[hidden]').forEach((n) => { n.hidden = false; });
      e.currentTarget.remove();
    });
    card.querySelector('.card-foot').addEventListener('click', (e) => {
      const r = e.target.closest('[data-rate]');
      if (r) return onRate(r, reel, card, false);
      const b = e.target.closest('[data-act]');
      if (!b) return;
      if (b.dataset.act === 'save') b.classList.toggle('on', toggleSave(reel));
      if (b.dataset.act === 'ask') openChat(reel);
      if (b.dataset.act === 'share') shareReel(reel);
      if (b.dataset.act === 'info') openInfo(reel);
    });
    card._reel = reel;
    card.querySelectorAll('.meta-ticker[data-sym]').forEach(paintLive);
    card.querySelector('.card-end')._reel = reel;
    return card;
  }

  // ---------- sheets ----------
  function openSheet(html) {
    $('#sheetBody').innerHTML = html;
    $('#sheet').hidden = false;
    $('#sheetBackdrop').hidden = false;
    state.player?.setPaused(true);
  }
  function closeSheet() {
    $('#sheet').hidden = true;
    $('#sheetBackdrop').hidden = true;
    state.player?.setPaused(false);
  }
  $('#sheetBackdrop').addEventListener('click', closeSheet);

  function openInfo(reel) {
    const sources = reel.sources || [];
    const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
    openSheet(`<h3>${esc(plain(reel.title))}</h3>
      ${reel.summary ? `<p>${rich(reel.summary)}</p>` : ''}
      ${sources.length ? `<h4>Sources</h4><ul class="src-list">${sources.map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title || s.url)}<small>${esc(host(s.url))}</small></a></li>`).join('')}</ul>` : ''}
      <h4>About this reel</h4>
      <p>${reel.category === 'learn' ? 'Evergreen lesson from the MarketReels library.' : `Generated ${esc(relDate(reel.date))} from public market data${reel.ai ? ' and written by AI. AI can make mistakes, so check the sources' : ''}.`}</p>
      ${reel.bg?.credit ? `<p>Background: ${esc(reel.bg.credit)}</p>` : ''}
      <p style="color:var(--faint)">${IDEAS_DISCLAIMER} Prices may be delayed.</p>
      <div style="height:6px"></div><button class="btn ghost" id="openSettings">Your taste & settings</button>`);
    $('#openSettings').onclick = openSettings;
  }

  function tasteHTML() {
    const p = tasteProfile();
    const n = Object.keys(state.ratings).length;
    if (!n) return '<p>Rate reels with 👍 😐 👎 and your preferences will show up here. The For You and Scroll feeds re-rank themselves around them.</p>';
    const row = (label, a) => {
      const score = a.sum / a.n;
      return `<div class="taste-row"><span class="taste-l">${esc(label)}</span>
        <span class="taste-bar"><i style="left:${50 + Math.min(0, score) * 50}%;width:${Math.abs(score) * 50}%" class="${score >= 0 ? 'pos' : 'neg'}"></i></span>
        <span class="taste-n">👍${a.likes} 😐${a.neutral} 👎${a.dislikes}</span></div>`;
    };
    const cats = Object.entries(p.cat).sort((a, b) => b[1].sum / b[1].n - a[1].sum / a[1].n);
    const tags = Object.entries(p.tag).filter(([, a]) => a.n >= 1).sort((a, b) => b[1].sum / b[1].n - a[1].sum / a[1].n);
    return `<p>${n} reels rated. Bars run from 👎 (left) to 👍 (right).</p>
      <h4>By section</h4>${cats.map(([k, a]) => row(CATEGORIES[k]?.label || k, a)).join('')}
      ${tags.length ? `<h4>By topic</h4>${tags.slice(0, 12).map(([k, a]) => row(k, a)).join('')}` : ''}
      <div style="height:10px"></div><button class="btn ghost" id="copyTaste">Copy my ratings (to share or tune the feed)</button>
      <button class="btn ghost" id="clearTaste">Clear ratings</button>`;
  }

  function openSettings() {
    const updated = state.feed?.generated_at ? new Date(state.feed.generated_at).toLocaleString() : 'never';
    openSheet(`<h3>Your taste</h3>${tasteHTML()}
      <h4>Settings</h4>
      <label class="setting">Narration (voice-over)<span class="switch"><input type="checkbox" id="setSound" ${state.sound ? 'checked' : ''}><span></span></span></label>
      <label class="setting">Experience level <select id="setLevel">
        <option value="pro" ${state.level === 'pro' ? 'selected' : ''}>Experienced: skip the basics</option>
        <option value="new" ${state.level === 'new' ? 'selected' : ''}>New to markets: explain everything</option></select></label>
      <label class="setting">Auto-advance to next reel<span class="switch"><input type="checkbox" id="setAuto" ${state.autoplay ? 'checked' : ''}><span></span></span></label>
      <label class="setting">Voice speed <select id="setRate">
        ${[0.9, 1, 1.05, 1.15, 1.25, 1.4].map((r) => `<option value="${r}" ${r === state.rate ? 'selected' : ''}>${r}×</option>`).join('')}</select></label>
      <h4>About</h4>
      <p>MarketReels turns each trading day into short, swipeable lessons: the US market, the economy, global events and stock ideas, plus courses on finance fundamentals.</p>
      <p>Feed last updated: ${esc(updated)}. Market data from Yahoo Finance (may be delayed), economic data from FRED, news from free public RSS feeds.</p>
      <p style="color:var(--faint)">Nothing here is investment advice. Stock ideas are educational write-ups, not recommendations to buy or sell.</p>
      <button class="btn ghost" id="resetProgress">Reset progress (streak, XP, courses)</button>`);
    $('#setSound').onchange = (e) => setSound(e.target.checked);
    $('#setAuto').onchange = (e) => { state.autoplay = e.target.checked; store.set('autoplay', state.autoplay); };
    $('#setLevel').onchange = (e) => { state.level = e.target.value; store.set('level', state.level); closeSheet(); renderFeed(); toast(state.level === 'pro' ? 'Experienced mode: basics hidden' : 'Beginner explainers on'); };
    $('#setRate').onchange = (e) => { state.rate = Number(e.target.value); store.set('rate', state.rate); };
    $('#copyTaste') && ($('#copyTaste').onclick = async () => {
      const p = tasteProfile();
      const summary = (o) => Object.fromEntries(Object.entries(o).map(([k, a]) => [k, { likes: a.likes, neutral: a.neutral, dislikes: a.dislikes }]));
      const out = { exported: new Date().toISOString(), by_section: summary(p.cat), by_topic: summary(p.tag), by_ticker: summary(p.ticker),
        ratings: Object.values(state.ratings).map((r) => ({ rating: RATE_LABELS[r.v], section: r.cat, topic: r.tag, ticker: r.ticker || undefined, title: r.title })) };
      try { await navigator.clipboard.writeText(JSON.stringify(out, null, 2)); toast('Ratings copied 📋'); } catch { toast('Copy failed'); }
    });
    $('#clearTaste') && ($('#clearTaste').onclick = () => { state.ratings = {}; store.set('ratings', {}); openSettings(); toast('Ratings cleared'); });
    $('#resetProgress').onclick = () => {
      state.seen.clear(); state.completed.clear(); state.answered = {}; state.xp = 0; state.daily = {};
      ['seen', 'completed'].forEach((k) => store.set(k, []));
      store.set('answered', {}); store.set('xp', 0); store.set('daily', {});
      renderStats(); closeSheet(); renderFeed(); toast('Progress reset');
    };
  }

  // ---------- Ask Claude (free) ----------
  // Opens Claude (claude.ai, or the Claude app on phones) with the reel and question filled in, using your own
  // Claude account. The app has no API key and no server for this, so asking questions can never cost anything.
  function reelContext(reel) {
    const lines = [`Reel: ${plain(reel.title)}`, `Section: ${CATEGORIES[reel.category]?.label || reel.category} · ${reel.tag || ''}`];
    if (reel.date) lines.push(`Date: ${reel.date}`);
    if (reel.ticker) lines.push(`Ticker: ${reel.ticker}`);
    if (reel.video) lines.push(`This is a ${reel.video.shorts ? 'short ' : ''}video from ${reel.video.channel}: "${reel.title}" (https://www.youtube.com/watch?v=${reel.video.id}).`, reel.summary ? `Description: ${reel.summary}` : '');
    (reel.scenes || []).forEach((s) => {
      const t = [s.eyebrow, s.headline, s.body].filter(Boolean).map(plain).join(' — ');
      if (t) lines.push(t);
      if (s.kind === 'bullets') (s.items || []).forEach((i) => lines.push('• ' + plain(i)));
      if (s.kind === 'stats' || s.kind === 'bars') (s.items || []).forEach((i) => lines.push(`• ${i.label}: ${i.display ?? i.value}${i.change != null ? ` (${pct(i.change)})` : ''}${i.note ? `, ${i.note}` : ''}`));
      if (s.kind === 'chart') lines.push(`Chart: ${s.label || ''}, last ${s.last ?? ''}${s.change != null ? `, ${pct(s.change)} over the period` : ''}. ${plain(s.note || '')}`);
      if (s.kind === 'quiz') lines.push(`Quiz: ${plain(s.question)} Answer: ${s.options?.[s.answer]}.`);
      if (s.kind === 'blank') lines.push(`Key takeaway: ${String(s.text).replace('___', s.options?.[s.answer] ?? '___')}`);
    });
    return lines.join('\n').slice(0, 3500);
  }

  function suggestions(reel) {
    if (reel.video) return ['What are the key takeaways?', 'What does this mean for stocks?', "What's the counterargument?", 'Give me more context on this'];
    const s = ['Explain this like I\'m brand new', 'Why does this matter for my money?', 'Give me a real-world example'];
    if (reel.category === 'ideas' || reel.ticker) s.splice(1, 0, `What's the biggest risk for ${reel.ticker || 'this'}?`);
    if (reel.category === 'macro') s.splice(1, 0, 'How could this affect stocks next?');
    s.push('Quiz me on this');
    return s.slice(0, 5);
  }

  function openChat(reel) {
    openSheet(`<div class="chat">
      <div class="chat-head">${artSVG(reel.art || 'news', 'chat-art')}<div><h3>Ask Claude</h3><p>About: ${esc(plain(reel.title))}</p></div></div>
      <div class="chat-sugg" id="chatSugg">${suggestions(reel).map((q) => `<button>${esc(q)}</button>`).join('')}</div>
      <form class="chat-form" id="chatForm"><input id="chatInput" autocomplete="off" maxlength="500" placeholder="Or type your own question…"><button aria-label="Ask">➤</button></form>
      <p class="chat-note">Opens Claude with this reel attached, using your own free Claude account. This app has no API key, so asking never costs anything. Your question is also copied, in case you need to paste it.</p></div>`);
    const ask = (q) => {
      q = q.trim();
      if (!q) return;
      const prompt = `I'm learning about markets with an app called MarketReels. Here's the reel I'm looking at:\n\n${reelContext(reel)}\n\nMy question: ${q}\n\nPlease answer simply, for a beginner. This is for learning, not financial advice.`;
      // Open synchronously inside the tap so popup blockers allow it.
      window.open('https://claude.ai/new?q=' + encodeURIComponent(prompt), '_blank', 'noopener');
      navigator.clipboard?.writeText(prompt).then(() => toast('Opening Claude · question copied 📋'), () => toast('Opening Claude…'));
    };
    $('#chatSugg').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) ask(b.textContent); });
    $('#chatForm').addEventListener('submit', (e) => {
      e.preventDefault();
      const input = $('#chatInput');
      ask(input.value);
      input.value = '';
    });
  }

  // ---------- global input ----------
  document.addEventListener('keydown', (e) => {
    if (!$('#sheet').hidden) { if (e.key === 'Escape') closeSheet(); return; }
    if (feedEl.classList.contains('free')) return;
    const p = state.player;
    const h = feedEl.clientHeight;
    if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); feedEl.scrollBy({ top: h, behavior: 'smooth' }); }
    else if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); feedEl.scrollBy({ top: -h, behavior: 'smooth' }); }
    else if (e.key === 'ArrowRight') p?.next();
    else if (e.key === 'ArrowLeft') p?.prev();
    else if (e.key === ' ') { e.preventDefault(); p?.setPaused(!p.paused); }
    else if (e.key === 'm') setSound(!state.sound);
  });
  $('#xp').addEventListener('click', openSettings);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { state.player?.setPaused(true); clearTimeout(live.timer); return; }
    if ($('#sheet').hidden) state.player?.setPaused(false);
    if (state.feed && Date.now() - live.fetchedAt > Math.min(quoteInterval(), 60e3)) refreshQuotes();
    if (['board', 'pa'].includes(state.tab)) renderFeed(); // restart the live table refresh
    if (state.feed && Date.now() - feedCheckedAt > 5 * 60e3) checkFeed(false);
  });

  // ---------- onboarding ----------
  function begin(withSound) {
    store.set('onboarded', true);
    $('#onboard').hidden = true;
    if (withSound && speech.supported) {
      // iOS only allows speech after a user gesture, so prime it here.
      speechSynthesis.speak(new SpeechSynthesisUtterance(' '));
    }
    if (withSound !== state.sound) setSound(withSound);
    load();
  }
  $('#startSound').addEventListener('click', () => begin(true));
  $('#startMuted').addEventListener('click', () => begin(false));

  if (!store.get('onboarded', false)) $('#onboard').hidden = false;
  else {
    // Speech needs a fresh gesture each launch on iOS; the first tap re-primes it.
    document.addEventListener('pointerdown', () => {
      if (state.sound && speech.supported) speechSynthesis.speak(new SpeechSynthesisUtterance(' '));
    }, { once: true });
    load();
  }

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
