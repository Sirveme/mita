// ============================================
// MITA — Service Worker único (scope "/") — zMita-33
// Servido desde /sw.js (raíz). Maneja avisos Web Push e instalación.
// Se mantiene liviano a propósito: sin caché agresiva que pueda servir una
// versión vieja de la app. El objetivo es que los avisos lleguen siempre.
// ============================================
const VERSION = 'mita-sw-v33';
const ICON = '/static/img/mita/icon-192.png';
const BADGE = '/static/img/mita/badge-72.png';

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

// Permite activar de inmediato una versión nueva del SW
self.addEventListener('message', (event) => {
    if (event.data === 'SKIP_WAITING' || (event.data && event.data.type === 'SKIP_WAITING')) {
        self.skipWaiting();
    }
});

// ============================================
// PUSH — mostrar la notificación
// ============================================
self.addEventListener('push', (event) => {
    let d = {};
    try { d = event.data ? event.data.json() : {}; } catch (e) {
        d = { title: 'MITA', body: event.data ? event.data.text() : '' };
    }
    const titulo = d.title || 'MITA';
    const url = d.url || '/';
    const opciones = {
        body: d.body || '',
        icon: d.icon || ICON,
        badge: d.badge || BADGE,
        tag: d.tag || 'mita',
        renotify: true,
        data: { url: url, ...(d.data || {}) },
        vibrate: [80, 40, 80]
    };
    event.waitUntil(self.registration.showNotification(titulo, opciones));
});

// ============================================
// CLICK — enfocar una ventana de MITA o abrir data.url
// ============================================
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const destino = (event.notification.data && event.notification.data.url) || '/';
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((lista) => {
            for (const c of lista) {
                try {
                    const u = new URL(c.url);
                    if (u.origin === self.location.origin && 'focus' in c) {
                        c.focus();
                        if ('navigate' in c && destino && u.pathname !== destino) {
                            try { c.navigate(destino); } catch (e) {}
                        }
                        return;
                    }
                } catch (e) {}
            }
            if (self.clients.openWindow) return self.clients.openWindow(destino);
        })
    );
});
