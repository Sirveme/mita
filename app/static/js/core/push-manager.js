// ============================================
// MITA - PUSH NOTIFICATION MANAGER
// Ubicación: app/static/js/core/push-manager.js
// ============================================

class PushNotificationManager {
    constructor() {
        this.registration = null;
        this.subscription = null;
        this.permission = 'default';
        this.isSupported = 'Notification' in window && 'serviceWorker' in navigator;
        this.callbacks = {};
    }

    // ============================================
    // INICIALIZAR
    // ============================================
    async init() {
        console.log('[Push] Inicializando Push Manager...');

        if (!this.isSupported) {
            console.warn('[Push] Push Notifications no soportadas en este navegador');
            return false;
        }

        try {
            // Obtener Service Worker registration
            this.registration = await navigator.serviceWorker.ready;
            console.log('[Push] Service Worker listo');

            // Verificar permiso actual
            this.permission = Notification.permission;
            console.log('[Push] Permiso actual:', this.permission);

            // Si ya tiene permiso, obtener suscripción existente
            if (this.permission === 'granted') {
                await this.getExistingSubscription();
            }

            return true;

        } catch (error) {
            console.error('[Push] Error inicializando:', error);
            return false;
        }
    }

    // ============================================
    // SOLICITAR PERMISO
    // ============================================
    async requestPermission() {
        console.log('[Push] Solicitando permiso...');

        if (!this.isSupported) {
            this.showNotSupported();
            return false;
        }

        if (this.permission === 'granted') {
            console.log('[Push] Permiso ya otorgado');
            return true;
        }

        if (this.permission === 'denied') {
            this.showPermissionDenied();
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            this.permission = permission;

            if (permission === 'granted') {
                console.log('[Push] ✅ Permiso otorgado');
                await this.subscribe();
                return true;
            } else {
                console.log('[Push] ❌ Permiso denegado');
                return false;
            }

        } catch (error) {
            console.error('[Push] Error solicitando permiso:', error);
            return false;
        }
    }

    // ============================================
    // SUSCRIBIRSE A PUSH
    // ============================================
    async subscribe() {
        console.log('[Push] Suscribiendo a push notifications...');

        try {
            // Configuración de suscripción
            const options = {
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(
                    // VAPID Public Key - Generar en backend
                    'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U'
                )
            };

            this.subscription = await this.registration.pushManager.subscribe(options);
            console.log('[Push] ✅ Suscripción exitosa');

            // Enviar suscripción al servidor
            await this.sendSubscriptionToServer(this.subscription);

            return this.subscription;

        } catch (error) {
            console.error('[Push] Error suscribiendo:', error);
            throw error;
        }
    }

    // ============================================
    // DESUSCRIBIRSE
    // ============================================
    async unsubscribe() {
        console.log('[Push] Desuscribiendo...');

        try {
            if (!this.subscription) {
                await this.getExistingSubscription();
            }

            if (this.subscription) {
                await this.subscription.unsubscribe();
                console.log('[Push] ✅ Desuscripción exitosa');

                // Notificar al servidor
                await this.removeSubscriptionFromServer(this.subscription);

                this.subscription = null;
                return true;
            }

            return false;

        } catch (error) {
            console.error('[Push] Error desuscribiendo:', error);
            return false;
        }
    }

    // ============================================
    // OBTENER SUSCRIPCIÓN EXISTENTE
    // ============================================
    async getExistingSubscription() {
        try {
            this.subscription = await this.registration.pushManager.getSubscription();

            if (this.subscription) {
                console.log('[Push] Suscripción existente encontrada');
            } else {
                console.log('[Push] No hay suscripción existente');
            }

            return this.subscription;

        } catch (error) {
            console.error('[Push] Error obteniendo suscripción:', error);
            return null;
        }
    }

    // ============================================
    // ENVIAR SUSCRIPCIÓN AL SERVIDOR
    // ============================================
    async sendSubscriptionToServer(subscription) {
        console.log('[Push] Enviando suscripción al servidor...');

        try {
            const token = localStorage.getItem('token');

            const response = await fetch('/api/v1/notificaciones/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    subscription: subscription.toJSON(),
                    user_agent: navigator.userAgent,
                    device_type: this.getDeviceType()
                })
            });

            if (response.ok) {
                console.log('[Push] ✅ Suscripción guardada en servidor');
                return true;
            } else {
                console.error('[Push] Error guardando suscripción:', response.status);
                return false;
            }

        } catch (error) {
            console.error('[Push] Error enviando suscripción:', error);
            return false;
        }
    }

    // ============================================
    // ELIMINAR SUSCRIPCIÓN DEL SERVIDOR
    // ============================================
    async removeSubscriptionFromServer(subscription) {
        try {
            const token = localStorage.getItem('token');

            await fetch('/api/v1/notificaciones/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint
                })
            });

            console.log('[Push] Suscripción eliminada del servidor');

        } catch (error) {
            console.error('[Push] Error eliminando suscripción:', error);
        }
    }

    // ============================================
    // MOSTRAR NOTIFICACIÓN LOCAL (sin push)
    // ============================================
    async showLocalNotification(title, options = {}) {
        if (this.permission !== 'granted') {
            console.warn('[Push] No hay permiso para mostrar notificaciones');
            return false;
        }

        try {
            const defaultOptions = {
                icon: '/static/img/icon-192x192.png',
                badge: '/static/img/badge-72x72.png',
                vibrate: [200, 100, 200],
                tag: 'serviplus-local',
                renotify: false
            };

            await this.registration.showNotification(title, {
                ...defaultOptions,
                ...options
            });

            return true;

        } catch (error) {
            console.error('[Push] Error mostrando notificación local:', error);
            return false;
        }
    }

    // ============================================
    // TEST - Enviar notificación de prueba
    // ============================================
    async sendTestNotification() {
        console.log('[Push] Enviando notificación de prueba...');

        try {
            const token = localStorage.getItem('token');

            const response = await fetch('/api/v1/notificaciones/test', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                console.log('[Push] ✅ Notificación de prueba enviada');
                return true;
            }

            return false;

        } catch (error) {
            console.error('[Push] Error enviando test:', error);
            return false;
        }
    }

    // ============================================
    // CALLBACKS
    // ============================================
    on(event, callback) {
        this.callbacks[event] = callback;
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event](data);
        }
    }

    // ============================================
    // UI HELPERS
    // ============================================
    showNotSupported() {
        alert('⚠️ Tu navegador no soporta notificaciones push.\n\nRecomendamos usar Chrome, Firefox o Edge.');
    }

    showPermissionDenied() {
        alert('⚠️ Has bloqueado las notificaciones.\n\nPara habilitarlas:\n1. Click en el candado 🔒 en la barra de dirección\n2. Cambiar "Notificaciones" a "Permitir"');
    }

    // ============================================
    // UTILIDADES
    // ============================================
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }

    getDeviceType() {
        const ua = navigator.userAgent;

        if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
            return 'tablet';
        }
        if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/.test(ua)) {
            return 'mobile';
        }
        return 'desktop';
    }

    // ============================================
    // GETTERS
    // ============================================
    isSubscribed() {
        return this.subscription !== null;
    }

    hasPermission() {
        return this.permission === 'granted';
    }

    getPermissionStatus() {
        return this.permission;
    }
}

// ============================================
// EXPORTAR
// ============================================
window.PushNotificationManager = PushNotificationManager;

console.log('[Push] PushNotificationManager cargado ✅');