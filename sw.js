/* ==========================================================================
   A TuBe High-Performance PWA Service Worker v3.0
   ● Tiered caching strategy (Core Shell / API / Streams)
   ● Stale-While-Revalidate for static assets
   ● Network-First with offline fallback for API responses
   ● Install prompt (beforeinstallprompt) support
   ========================================================================== */

const CACHE_VERSION = 'atube-v3.0.0';
const CORE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './robots.txt',
  './css/style.css',
  './css/tv-navigation.css',
  './css/movie-details.css',
  './css/responsive.css',
  './css/skeleton.css',
  './js/app.js',
  './js/player.js',
  './js/movie-details.js',
  './js/iptv-engine.js',
  './js/remote-control.js',
];

const API_CACHEABLE = [
  '/api/health',
  '/api/ping',
];

// ── Install: Cache Core App Shell ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => {
      return Promise.allSettled(
        CORE_ASSETS.map(url =>
          cache.add(url).catch(err => {
            console.warn(`[SW] Failed to precache ${url}:`, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: Remove Old Caches ───────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter(key => key !== CACHE_VERSION)
          .map(key => {
            console.log(`[SW] Clearing old cache: ${key}`);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// ── Fetch: Tiered Strategy ────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 1. Always bypass: Video streams, HLS segments, blob, chrome-extension
  if (
    req.url.startsWith('blob:') ||
    url.protocol === 'chrome-extension:' ||
    url.pathname.endsWith('.m3u8') ||
    url.pathname.endsWith('.ts') ||
    url.pathname.endsWith('.mp4') ||
    url.pathname.endsWith('.mkv') ||
    url.pathname.endsWith('.webm') ||
    url.pathname.startsWith('/api/stream/') ||
    url.pathname.startsWith('/api/media/stream') ||
    url.pathname.startsWith('/api/watch/') ||
    url.pathname.startsWith('/api/resolve-stream')
  ) {
    return; // Let browser handle raw stream requests directly
  }

  // 2. Network-First with Cache Fallback for dynamic API endpoints
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(req)
        .then((networkResponse) => {
          // Cache selected lightweight API responses for offline use
          if (
            networkResponse.ok &&
            API_CACHEABLE.some(path => url.pathname.startsWith(path))
          ) {
            const copy = networkResponse.clone();
            caches.open(CACHE_VERSION).then(cache => cache.put(req, copy));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match(req).then(cached => {
            if (cached) return cached;
            return new Response(
              JSON.stringify({ error: 'أنت غير متصل بالإنترنت', offline: true }),
              { status: 503, headers: { 'Content-Type': 'application/json' } }
            );
          });
        })
    );
    return;
  }

  // 3. Stale-While-Revalidate for app static assets (CSS, JS, HTML, images)
  event.respondWith(
    caches.open(CACHE_VERSION).then((cache) => {
      return cache.match(req).then((cachedResponse) => {
        const networkFetch = fetch(req)
          .then((networkResponse) => {
            if (
              networkResponse &&
              networkResponse.status === 200 &&
              (networkResponse.type === 'basic' || networkResponse.type === 'cors')
            ) {
              cache.put(req, networkResponse.clone());
            }
            return networkResponse;
          })
          .catch(() => cachedResponse);

        // Return cached immediately, update in background
        return cachedResponse || networkFetch;
      });
    })
  );
});

// ── Background Sync: Queue failed API calls for retry ────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'atube-sync-watchlist') {
    event.waitUntil(
      clients.matchAll().then(clientList => {
        clientList.forEach(client => {
          client.postMessage({ type: 'SYNC_WATCHLIST' });
        });
      })
    );
  }
});

// ── Push Notifications (future use) ──────────────────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'A TuBe';
  const options = {
    body: data.body || 'تحديث جديد متاح',
    icon: './assets/aljazeera.svg',
    badge: './assets/aljazeera.svg',
    dir: 'rtl',
    lang: 'ar',
  };
  event.waitUntil(self.registration.showNotification(title, options));
});
