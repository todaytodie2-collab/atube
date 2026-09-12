/* ==========================================================================
   A TuBe High-Performance PWA Service Worker
   Provides instant-boot asset caching, offline resilience & streaming bypass
   ========================================================================== */

const CACHE_NAME = 'atube-v2.6.0-live-tv';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './css/style.css',
  './css/tv-navigation.css',
  './css/movie-details.css',
  './css/responsive.css',
  './js/bundled-data.js',
  './js/media-catalog.js',
  './js/iptv-engine.js',
  './js/player.js',
  './js/remote-control.js',
  './js/movie-details.js',
  './js/app.js'
];

// Install Event: Cache Core Application Shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[A TuBe SW] Some static assets failed to precache:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Purge Old Caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Cache-First for static assets, Network-First for dynamic APIs, Bypass for video streams
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 1. Bypass video streams, HLS segments, and video proxy to preserve bandwidth and real-time streaming
  if (
    url.pathname.endsWith('.m3u8') ||
    url.pathname.endsWith('.ts') ||
    url.pathname.endsWith('.mp4') ||
    url.pathname.includes('/api/stream/') ||
    url.pathname.includes('/api/media/stream')
  ) {
    return;
  }

  // 2. Network-First with fallback for API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(req)
        .then((response) => {
          return response;
        })
        .catch(() => {
          return caches.match(req);
        })
    );
    return;
  }

  // 3. Cache-First with Stale-While-Revalidate for app static assets
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return networkResponse;
        })
        .catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
