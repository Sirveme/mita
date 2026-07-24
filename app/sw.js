// ============================================
// MITA - SERVICE WORKER
// Ubicación: app/static/sw.js
// ============================================

const CACHE_VERSION = 'serviplus-v2.0.0';
const CACHE_STATIC = `${CACHE_VERSION}-static`;
const CACHE_DYNAMIC = `${CACHE_VERSION}-dynamic`;
const CACHE_IMAGES = `${CACHE_VERSION}-images`;

// Archivos críticos para cachear en instalación
const STATIC_FILES = [
    '/static/js/core/push-manager.js'
];

// Rutas que NO deben cachearse
const EXCLUDED_URLS = [
    '/api/',
    '/ws/',
    '/admin/',
    'chrome-extension://'
];

// ============================================
// INSTALL - Primera instalación del SW
// ============================================
self.addEventListener('install', (event) => {
    console.log('[SW] Instalando Service Worker...');
    
    event.waitUntil(
        caches.open(CACHE_STATIC)
            .then(async (cache) => {
                console.log('[SW] Cacheando archivos estáticos...');
                
                // Cachear archivos uno por uno (tolerante a errores)
                const cachePromises = STATIC_FILES.map(async (url) => {
                    try {
                        await cache.add(url);
                        console.log(`[SW] ✅ Cacheado: ${url}`);
                    } catch (error) {
                        console.warn(`[SW] ⚠️ No se pudo cachear: ${url}`, error.message);
                    }
                });
                
                await Promise.all(cachePromises);
                console.log('[SW] Proceso de cacheo completado');
            })
            .then(() => {
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Error en instalación SW:', error);
            })
    );
});

// ============================================
// ACTIVATE - Activación del SW
// ============================================
self.addEventListener('activate', (event) => {
    console.log('[SW] Activando Service Worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        // Eliminar cachés viejos
                        if (cacheName !== CACHE_STATIC && 
                            cacheName !== CACHE_DYNAMIC && 
                            cacheName !== CACHE_IMAGES) {
                            console.log('[SW] Eliminando caché antigua:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] Service Worker activado ✅');
                return self.clients.claim(); // Tomar control inmediatamente
            })
    );
});

// ============================================
// FETCH - Interceptar peticiones
// ============================================
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Ignorar URLs excluidas
    if (EXCLUDED_URLS.some(excluded => url.pathname.startsWith(excluded))) {
        return;
    }
    
    // Ignorar peticiones que no sean GET
    if (request.method !== 'GET') {
        return;
    }
    
    // Estrategia según tipo de recurso
    if (url.pathname.startsWith('/static/img/')) {
        event.respondWith(cacheFirstStrategy(request, CACHE_IMAGES));
    } else if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirstStrategy(request, CACHE_STATIC));
    } else {
        event.respondWith(networkFirstStrategy(request));
    }
});

// ============================================
// ESTRATEGIA: Cache First (para archivos estáticos)
// ============================================
async function cacheFirstStrategy(request, cacheName) {
    try {
        // Buscar en caché primero
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            console.log('[SW] Sirviendo desde caché:', request.url);
            return cachedResponse;
        }
        
        // Si no está en caché, traer de red
        const networkResponse = await fetch(request);
        
        // Guardar en caché para futuro
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('[SW] Error en cache-first:', error);
        
        // Fallback a página offline si es HTML
        if (request.headers.get('accept').includes('text/html')) {
            return caches.match('/offline.html');
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// ============================================
// ESTRATEGIA: Network First (para contenido dinámico)
// ============================================
async function networkFirstStrategy(request) {
    try {
        // Intentar traer de red primero
        const networkResponse = await fetch(request);
        
        // Guardar en caché dinámico
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_DYNAMIC);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('[SW] Red no disponible, buscando en caché:', request.url);
        
        // Fallback a caché
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Si es HTML, mostrar página offline
        if (request.headers.get('accept').includes('text/html')) {
            return caches.match('/offline.html');
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// ============================================
// PUSH NOTIFICATIONS - Recibir notificación
// ============================================
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification recibida');
    
    let data = {
        title: 'MITA',
        body: 'Nueva notificación',
        icon: '/static/img/icon-192x192.png',
        badge: '/static/img/badge-72x72.png',
        data: {}
    };
    
    // Parsear data si viene en el push
    if (event.data) {
        try {
            const payload = event.data.json();
            data = {
                ...data,
                ...payload
            };
        } catch (error) {
            console.error('[SW] Error parseando push data:', error);
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        vibrate: [200, 100, 200, 100, 200],
        tag: data.tag || 'serviplus-notification',
        renotify: true,
        requireInteraction: data.requireInteraction || false,
        data: data.data,
        actions: data.actions || [
            {
                action: 'open',
                title: 'Abrir',
                icon: '/static/img/action-open.png'
            },
            {
                action: 'close',
                title: 'Cerrar',
                icon: '/static/img/action-close.png'
            }
        ],
        image: data.image,
        silent: data.silent || false
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// ============================================
// NOTIFICATION CLICK - Click en notificación
// ============================================
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Click en notificación:', event.action);
    
    event.notification.close();
    
    const data = event.notification.data || {};
    const action = event.action;
    
    // Si presionó "Cerrar", no hacer nada más
    if (action === 'close') {
        return;
    }
    
    // Determinar URL a abrir
    let urlToOpen = '/';
    
    if (data.url) {
        urlToOpen = data.url;
    } else if (data.tipo === 'nuevo_servicio') {
        urlToOpen = '/tecnico/panel';
    } else if (data.tipo === 'tecnico_asignado') {
        urlToOpen = '/cliente/seguimiento';
    } else if (data.tipo === 'chat_message') {
        urlToOpen = `/chat/${data.servicio_id}`;
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Si ya hay una ventana abierta con esa URL, enfocarla
                for (let client of clientList) {
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Si hay alguna ventana abierta de MITA, navegar ahí
                if (clientList.length > 0) {
                    return clientList[0].focus().then(client => {
                        return client.navigate(urlToOpen);
                    });
                }
                
                // Si no, abrir nueva ventana
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// ============================================
// NOTIFICATION CLOSE - Notificación cerrada
// ============================================
self.addEventListener('notificationclose', (event) => {
    console.log('[SW] Notificación cerrada:', event.notification.tag);
    
    // Analytics: registrar que cerró sin interactuar
    const data = event.notification.data || {};
    
    if (data.trackClose) {
        event.waitUntil(
            fetch('/api/v1/analytics/notification-close', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tag: event.notification.tag,
                    timestamp: new Date().toISOString()
                })
            }).catch(() => {
                // Ignorar errores de analytics
            })
        );
    }
});

// ============================================
// SYNC - Sincronización en background
// ============================================
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncPendingMessages());
    } else if (event.tag === 'sync-location') {
        event.waitUntil(syncTecnicoLocation());
    }
});

// Sincronizar mensajes pendientes
async function syncPendingMessages() {
    try {
        const cache = await caches.open('pending-messages');
        const requests = await cache.keys();
        
        for (let request of requests) {
            try {
                await fetch(request);
                await cache.delete(request);
                console.log('[SW] Mensaje sincronizado:', request.url);
            } catch (error) {
                console.log('[SW] Sync fallido, reintentará:', error);
            }
        }
    } catch (error) {
        console.error('[SW] Error en syncPendingMessages:', error);
    }
}

// Sincronizar ubicación del técnico
async function syncTecnicoLocation() {
    try {
        const cache = await caches.open('pending-location');
        const requests = await cache.keys();
        
        for (let request of requests) {
            try {
                await fetch(request);
                await cache.delete(request);
                console.log('[SW] Ubicación sincronizada');
            } catch (error) {
                console.log('[SW] Sync ubicación fallido');
            }
        }
    } catch (error) {
        console.error('[SW] Error en syncTecnicoLocation:', error);
    }
}

// ============================================
// MESSAGE - Mensajes desde la app
// ============================================
self.addEventListener('message', (event) => {
    console.log('[SW] Mensaje recibido:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data.type === 'CACHE_URLS') {
        event.waitUntil(
            caches.open(CACHE_DYNAMIC)
                .then(cache => cache.addAll(event.data.urls))
        );
    } else if (event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then(keys => 
                Promise.all(keys.map(key => caches.delete(key)))
            )
        );
    }
});

// ============================================
// UTILITIES
// ============================================

// Limpiar cachés antiguas (llamar periódicamente)
async function cleanOldCaches() {
    const cacheWhitelist = [CACHE_STATIC, CACHE_DYNAMIC, CACHE_IMAGES];
    const cacheNames = await caches.keys();
    
    return Promise.all(
        cacheNames.map((cacheName) => {
            if (!cacheWhitelist.includes(cacheName)) {
                console.log('[SW] Eliminando caché antigua:', cacheName);
                return caches.delete(cacheName);
            }
        })
    );
}

console.log('[SW] Service Worker cargado ✅');