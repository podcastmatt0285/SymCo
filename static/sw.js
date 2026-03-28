// Wadsworth PWA Service Worker — static assets cached, live API/pages always network
const CACHE_VERSION = "wadsworth-v4";

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

  const isDM = data.tag && data.tag.startsWith("dm-");
  const options = {
    body:               data.body  || "",
    icon:               data.icon  || "/static/icons/icon-192.png",
    image:              data.icon  || "/static/icons/icon-192.png",
    badge:              "/static/icons/icon-72.png",
    tag:                data.tag   || "wadsworth-notif",
    renotify:           true,
    timestamp:          Date.now(),
    requireInteraction: isDM,
    vibrate:            [100, 50, 100, 50, 100],
    data:               { url: data.url || "/" },
  };
  if (isDM) {
    options.actions = [{ action: "reply", type: "text", title: "Reply",
                         placeholder: "Type a reply…" }];
  }
  event.waitUntil(self.registration.showNotification(data.title || "Wadsworth", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "/";

  // Inline reply action
  if (event.action === "reply") {
    const replyText = event.reply;

    // Android Chrome supports inline text reply; desktop Chrome does not
    // (event.reply will be empty on desktop) — fall through to open the DM page
    if (replyText && replyText.trim()) {
      const withMatch = targetUrl.match(/[?&]with=(\d+)/);
      const otherId   = withMatch ? withMatch[1] : null;
      if (otherId) {
        event.waitUntil(
          fetch("/api/dm/reply", {
            method:      "POST",
            credentials: "include",
            headers:     { "Content-Type": "application/x-www-form-urlencoded" },
            body:        `other_id=${otherId}&content=${encodeURIComponent(replyText.trim())}`,
          }).then((r) => {
            return r.json().then((d) => {
              if (!d.ok) {
                return self.registration.showNotification("Reply failed", {
                  body: "Server error: " + (d.error || r.status), tag: "reply-debug"
                });
              }
            });
          }).catch((err) => {
            return self.registration.showNotification("Reply failed", {
              body: "Fetch error: " + err.message, tag: "reply-debug"
            });
          })
        );
        return;
      }
    }
    // Desktop fallback: no text input support — open the DM conversation instead
  }

  // Regular tap — open/focus the app at the target URL
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
      for (const c of cs) {
        if ("focus" in c) {
          return c.focus().then(() => {
            if ("navigate" in c) return c.navigate(targetUrl);
          }).catch(() => clients.openWindow(targetUrl));
        }
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
