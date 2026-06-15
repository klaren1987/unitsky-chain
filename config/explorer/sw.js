// Killer SW: replaces old Otterscan service worker and immediately unregisters.
// The browser fetches sw.js bypassing SW cache — so this always runs.
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', () => {
  self.registration.unregister()
    .then(() => self.clients.matchAll({ type: 'window' }))
    .then(clients => clients.forEach(c => c.navigate(c.url)));
});
