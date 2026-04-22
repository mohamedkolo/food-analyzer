// NutraX Service Worker
const CACHE_NAME = ‘nutrax-v1’;
const urlsToCache = [
‘/’,
‘/static/icon-192.png’,
‘/static/icon-512.png’,
‘https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;900&display=swap’,
‘https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css’
];

// Install — cache essentials
self.addEventListener(‘install’, event => {
event.waitUntil(
caches.open(CACHE_NAME)
.then(cache => cache.addAll(urlsToCache).catch(err => console.log(‘Cache error:’, err)))
);
self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener(‘activate’, event => {
event.waitUntil(
caches.keys().then(cacheNames => {
return Promise.all(
cacheNames.map(cacheName => {
if (cacheName !== CACHE_NAME) {
return caches.delete(cacheName);
}
})
);
})
);
self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener(‘fetch’, event => {
// Skip non-GET
if (event.request.method !== ‘GET’) return;

// Skip API/dynamic routes (need fresh data)
const url = new URL(event.request.url);
if (url.pathname.startsWith(’/api/’) ||
url.pathname.startsWith(’/admin/’) ||
url.pathname.startsWith(’/log_weight’) ||
url.pathname.startsWith(’/edit_meal’) ||
url.pathname.startsWith(’/swap_meal’) ||
url.pathname.startsWith(’/download_pdf’)) {
return; // Let browser handle normally
}

event.respondWith(
fetch(event.request)
.then(response => {
// Cache successful responses
if (response && response.status === 200) {
const responseClone = response.clone();
caches.open(CACHE_NAME).then(cache => {
cache.put(event.request, responseClone).catch(() => {});
});
}
return response;
})
.catch(() => {
// Offline - try cache
return caches.match(event.request);
})
);
});
