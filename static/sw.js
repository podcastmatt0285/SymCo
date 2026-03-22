// Wadsworth PWA Service Worker — static assets cached, live API/pages always network
const CACHE_VERSION = "wadsworth-v2";

importScripts('https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js');

// Activate immediately — don't wait for existing tabs to close
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(clients.claim()));

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

// API routes: always fetch live — never serve stale game data
workbox.routing.registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new workbox.strategies.NetworkOnly()
);

// Navigation requests (HTML pages): network-first with 3s timeout — fresh data when server is fast,
// cached page shown immediately if server is slow, cache updated in background either way
workbox.routing.registerRoute(
  ({ request }) => request.mode === 'navigate',
  new workbox.strategies.NetworkFirst({
    cacheName: 'wadsworth-pages-v1',
    networkTimeoutSeconds: 3
  })
);

// Static assets only: JS, CSS, images, fonts — safe to cache with stale-while-revalidate
workbox.routing.registerRoute(
  ({ request }) => ['script', 'style', 'image', 'font'].includes(request.destination),
  new workbox.strategies.StaleWhileRevalidate({
    cacheName: CACHE_VERSION
  })
);
