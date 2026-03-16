/**
 * Memex PAIM – Service Worker
 * Offline cache: minden statikus fájlt cache-el, hogy internet nélkül is betöltsön
 */

const CACHE_VERSION = 'memex-v7';
const STATIC_ASSETS = [
  './',
  './index.html',
  './memex-db.js',
  './manifest.json',
  './icon.svg',
];

// Telepítés: statikus fájlok cache-be
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Aktiválás: régi cache törlése
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: cache-first stratégia statikus fájlokra
// API hívások (Claude, Gemini) mindig hálózaton mennek át
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Külső API hívások + version.json: soha ne cache-eljük
  if (
    url.hostname.includes('anthropic.com') ||
    url.hostname.includes('googleapis.com') ||
    url.hostname.includes('generativelanguage.googleapis.com') ||
    url.hostname.includes('openrouter.ai') ||
    url.pathname.includes('version.json')
  ) {
    return; // Alapértelmezett hálózati viselkedés
  }

  // Statikus fájlok: cache-first
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        // Sikeres választ cache-eljük
        if (response && response.status === 200 && response.type !== 'opaque') {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Offline fallback: ha nincs cache és nincs net
        if (event.request.destination === 'document') {
          return caches.match('./index.html');
        }
      });
    })
  );
});
