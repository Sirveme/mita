// ============================================
// MITA - NOTIFICATION UI
// Ubicación: app/static/js/components/notification-ui.js
// ============================================

class NotificationUI {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.sounds = {
            success: null,
            info: null,
            warning: null,
            error: null
        };
        this.config = {
            position: 'top-right', // top-right, top-left, bottom-right, bottom-left, top-center
            maxNotifications: 5,
            defaultDuration: 5000,
            soundEnabled: true,
            vibrationEnabled: true
        };
        
        this.init();
    }

    // ============================================
    // INICIALIZACIÓN
    // ============================================
    
    init() {
        this.createContainer();
        this.loadSounds();
        console.log('[Notifications] Sistema inicializado ✅');
    }

    createContainer() {
        // Crear contenedor si no existe
        if (document.getElementById('notification-container')) {
            this.container = document.getElementById('notification-container');
            return;
        }

        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = `notification-container ${this.config.position}`;
        document.body.appendChild(this.container);
    }

    loadSounds() {
        // Rutas a sonidos (opcional)
        this.sounds.success = new Audio('/static/sounds/success.mp3');
        this.sounds.info = new Audio('/static/sounds/info.mp3');
        this.sounds.warning = new Audio('/static/sounds/warning.mp3');
        this.sounds.error = new Audio('/static/sounds/error.mp3');
        
        // Configurar volumen
        Object.values(this.sounds).forEach(sound => {
            if (sound) {
                sound.volume = 0.5;
            }
        });
    }

    // ============================================
    // MOSTRAR NOTIFICACIONES
    // ============================================
    
    show(message, type = 'info', options = {}) {
        const id = this.generateId();
        
        // Configuración
        const config = {
            duration: options.duration || this.config.defaultDuration,
            closable: options.closable !== false,
            icon: options.icon || this.getDefaultIcon(type),
            action: options.action || null,
            sound: options.sound !== false,
            vibrate: options.vibrate !== false
        };

        // Crear elemento
        const notification = this.createNotificationElement(id, message, type, config);
        
        // Agregar al contenedor
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Animar entrada
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Efectos
        this.playSound(type, config.sound);
        this.vibrate(type, config.vibrate);
        
        // Auto-cerrar
        if (config.duration > 0) {
            setTimeout(() => {
                this.hide(id);
            }, config.duration);
        }
        
        // Limpiar si hay muchas
        this.cleanupOld();
        
        return id;
    }

    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', { duration: 7000, ...options });
    }

    // ============================================
    // CREAR ELEMENTO
    // ============================================
    
    createNotificationElement(id, message, type, config) {
        const notification = document.createElement('div');
        notification.id = `notification-${id}`;
        notification.className = `notification notification-${type}`;
        
        // Icono
        const icon = document.createElement('div');
        icon.className = 'notification-icon';
        icon.innerHTML = config.icon;
        
        // Contenido
        const content = document.createElement('div');
        content.className = 'notification-content';
        content.innerHTML = `<p>${message}</p>`;
        
        // Botón cerrar
        let closeBtn;
        if (config.closable) {
            closeBtn = document.createElement('button');
            closeBtn.className = 'notification-close';
            closeBtn.innerHTML = '×';
            closeBtn.onclick = () => this.hide(id);
        }
        
        // Acción (opcional)
        let actionBtn;
        if (config.action) {
            actionBtn = document.createElement('button');
            actionBtn.className = 'notification-action';
            actionBtn.textContent = config.action.label;
            actionBtn.onclick = () => {
                config.action.callback();
                this.hide(id);
            };
            content.appendChild(actionBtn);
        }
        
        // Ensamblar
        notification.appendChild(icon);
        notification.appendChild(content);
        if (closeBtn) notification.appendChild(closeBtn);
        
        return notification;
    }

    // ============================================
    // OCULTAR/ELIMINAR
    // ============================================
    
    hide(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        // Animar salida
        notification.classList.remove('show');
        notification.classList.add('hide');
        
        // Eliminar del DOM
        setTimeout(() => {
            notification.remove();
            this.notifications.delete(id);
        }, 300);
    }

    hideAll() {
        this.notifications.forEach((_, id) => {
            this.hide(id);
        });
    }

    // ============================================
    // NOTIFICACIONES ESPECIALES
    // ============================================
    
    showChatMessage(from, message, avatar = null) {
        const content = `
            <div class="chat-notification">
                ${avatar ? `<img src="${avatar}" class="chat-avatar">` : ''}
                <div>
                    <strong>${from}</strong>
                    <p>${message}</p>
                </div>
            </div>
        `;
        
        return this.show(content, 'info', {
            icon: '💬',
            duration: 6000,
            action: {
                label: 'Responder',
                callback: () => {
                    // TODO: Abrir chat
                    console.log('Abrir chat con:', from);
                }
            }
        });
    }

    showServiceUpdate(servicioId, estado, mensaje) {
        const iconos = {
            'asignado': '✅',
            'en_camino': '🚗',
            'llegado': '📍',
            'en_proceso': '🔧',
            'completado': '🎉',
            'cancelado': '❌'
        };
        
        return this.show(mensaje, 'info', {
            icon: iconos[estado] || '📋',
            duration: 7000,
            action: {
                label: 'Ver detalle',
                callback: () => {
                    window.location.href = `/cliente/seguimiento?servicio=${servicioId}`;
                }
            }
        });
    }

    showTecnicoAsignado(tecnico) {
        const content = `
            <div class="tecnico-notification">
                ${tecnico.foto ? `<img src="${tecnico.foto}" class="tecnico-avatar">` : ''}
                <div>
                    <strong>Técnico asignado</strong>
                    <p>${tecnico.nombre}</p>
                    <small>⭐ ${tecnico.calificacion}/5.0</small>
                </div>
            </div>
        `;
        
        return this.show(content, 'success', {
            icon: '🔧',
            duration: 10000,
            sound: true,
            vibrate: true
        });
    }

    // ============================================
    // LOADING SPINNER
    // ============================================
    
    showLoading(message = 'Cargando...') {
        const id = this.generateId();
        
        const notification = document.createElement('div');
        notification.id = `notification-${id}`;
        notification.className = 'notification notification-loading';
        
        notification.innerHTML = `
            <div class="notification-icon">
                <div class="spinner"></div>
            </div>
            <div class="notification-content">
                <p>${message}</p>
            </div>
        `;
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        return id;
    }

    // ============================================
    // EFECTOS
    // ============================================
    
    playSound(type, enabled) {
        if (!enabled || !this.config.soundEnabled) return;
        
        const sound = this.sounds[type];
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(() => {
                // Ignorar errores de autoplay
            });
        }
    }

    vibrate(type, enabled) {
        if (!enabled || !this.config.vibrationEnabled) return;
        if (!('vibrate' in navigator)) return;
        
        const patterns = {
            success: [100, 50, 100],
            info: [100],
            warning: [100, 50, 100, 50, 100],
            error: [200, 100, 200]
        };
        
        navigator.vibrate(patterns[type] || [100]);
    }

    // ============================================
    // UTILIDADES
    // ============================================
    
    getDefaultIcon(type) {
        const icons = {
            success: '✅',
            info: 'ℹ️',
            warning: '⚠️',
            error: '❌',
            loading: '⏳'
        };
        
        return icons[type] || 'ℹ️';
    }

    generateId() {
        return `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    cleanupOld() {
        const notifications = Array.from(this.notifications.keys());
        
        if (notifications.length > this.config.maxNotifications) {
            const toRemove = notifications.slice(0, notifications.length - this.config.maxNotifications);
            toRemove.forEach(id => this.hide(id));
        }
    }

    // ============================================
    // CONFIGURACIÓN
    // ============================================
    
    setConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // Actualizar posición del contenedor
        if (newConfig.position) {
            this.container.className = `notification-container ${newConfig.position}`;
        }
    }

    toggleSound(enabled) {
        this.config.soundEnabled = enabled;
        localStorage.setItem('notificationsSoundEnabled', enabled);
    }

    toggleVibration(enabled) {
        this.config.vibrationEnabled = enabled;
        localStorage.setItem('notificationsVibrationEnabled', enabled);
    }
}

// ============================================
// EXPORTAR E INICIALIZAR
// ============================================

// Crear instancia global
window.NotificationUI = NotificationUI;

// Auto-inicializar
let notificationUI = null;

document.addEventListener('DOMContentLoaded', () => {
    notificationUI = new NotificationUI();
    window.notificationUI = notificationUI;
    
    // Helper global para toast rápido
    window.showToast = (message, type = 'info', options = {}) => {
        return notificationUI.show(message, type, options);
    };
    
    console.log('[Notifications] UI inicializada ✅');
});

console.log('[Notifications] notification-ui.js cargado ✅');