// Wadsworth PWA Service Worker — static assets cached, live API/pages always network
const CACHE_VERSION = "wadsworth-v3";

importScripts('https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js');

// Activate immediately — don't wait for existing tabs to close
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(clients.claim()));

self.addEventListener("message", (event) => {
  if (!event.data) return;
  if (event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
  if (event.data.type === "SET_BADGE") {
    const n = event.data.count || 0;
    if ("setAppBadge" in self.navigator) {
      n > 0 ? self.navigator.setAppBadge(n) : self.navigator.clearAppBadge();
    }
  }
});

// ── Push notifications ─────────────────────────────────────────────────────────
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch(e) {}
  const title   = data.title || "Wadsworth";
  const options = {
    body:      data.body  || "",
    icon:      "/static/icons/icon-192.png",
    badge:     "/static/icons/icon-72.png",
    tag:       data.tag   || "wadsworth-notif",
    renotify:  true,
    data:      { url: data.url || "/" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
      // Navigate any existing open window to the target URL
      for (const c of cs) {
        if ("navigate" in c) { return c.focus().then(() => c.navigate(targetUrl)); }
        if ("focus" in c)    { return c.focus(); }
      }
      return clients.openWindow(targetUrl);
    })
  );
});

// ── Routing ───────────────────────────────────────────────────────────────────

// API routes: always fetch live — never serve stale game data
workbox.routing.registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new workbox.strategies.NetworkOnly()
);

// Navigation requests (HTML pages): always fetch live — pages contain server-rendered game state
// (inventory, prices, balances) that must never be served stale from cache
workbox.routing.registerRoute(
  ({ request }) => request.mode === 'navigate',
  new workbox.strategies.NetworkOnly()
);

// Static assets only: JS, CSS, images, fonts — safe to cache with stale-while-revalidate
workbox.routing.registerRoute(
  ({ request }) => ['script', 'style', 'image', 'font'].includes(request.destination),
  new workbox.strategies.StaleWhileRevalidate({
    cacheName: CACHE_VERSION
  })
);
