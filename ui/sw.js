// Memex Service Worker – offline cache
const CACHE = 'memex-v1';
const OFFLINE_URLS = ['/'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(OFFLINE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API hívások – mindig network, cache nélkül
  if (url.pathname.startsWith('/kerdes') ||
      url.pathname.startsWith('/bejegyez') ||
      url.pathname.startsWith('/keres') ||
      url.pathname.startsWith('/info') ||
      url.pathname.startsWith('/export') ||
      url.pathname.startsWith('/import')) {
    e.respondWith(fetch(e.request).catch(() =>
      new Response(JSON.stringify({hiba: 'Offline – szerver nem elérhető'}),
        {headers: {'Content-Type': 'application/json'}})
    ));
    return;
  }

  // UI fájlok – cache first, network fallback
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match('/'));
    })
  );
});
