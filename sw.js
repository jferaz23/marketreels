// App shell is cached for offline use; the feed is network-first so new reels show up right away.
const VERSION = 'mr-v6';
const SHELL = ['./', 'index.html', 'assets/styles.css?v=6', 'assets/app.js?v=6', 'manifest.webmanifest', 'assets/icons/icon.svg', 'assets/icons/icon-192.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Live prices (api/) always go to the network.
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.includes('/api/')) return;
  const networkFirst = url.pathname.includes('/data/') || e.request.mode === 'navigate' || /\.(js|css)$/.test(url.pathname);
  if (networkFirst) {
    e.respondWith(
      fetch(e.request, { cache: 'no-cache' }) // revalidate so updates appear on the next open
        .then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); return res; })
        .catch(() => caches.match(e.request).then((r) => r || caches.match('index.html')))
    );
  } else {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});
