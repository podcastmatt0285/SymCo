self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => self.clients.claim());
self.addEventListener('fetch', (event) => { event.respondWith(fetch(event.request)); });
self.addEventListener('push', function(event) {
  if (event.data) {
    const data = event.data.json();
    const options = { body: data.body, icon: data.icon || '/icon.svg', badge: '/badge.svg', image: data.image, data: { url: data.url }, vibrate: [100, 50, 100], requireInteraction: true };
    event.waitUntil(self.registration.showNotification(data.title, options));
  }
});
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  if (event.notification.data && event.notification.data.url) {
    const url = event.notification.data.url;
    const target = new URL(url, self.location.origin).href;
    event.waitUntil(clients.matchAll({type: 'window'}).then(windowClients => {
        for (let client of windowClients) { if (client.url === target && 'focus' in client) return client.focus(); }
        if (clients.openWindow) return clients.openWindow(target);
    }));
  }
});
self.addEventListener('notificationclose', function(event) {
  if (event.notification.data && event.notification.data.url) {
    const url = event.notification.data.url;
    const parts = url.split('/');
    const bid = parts[parts.length - 1];
    if(bid) { fetch('/trk/d/' + bid, {mode: 'no-cors'}); }
  }
});
