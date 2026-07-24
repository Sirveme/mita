/**
 * Cliente WebSocket para MITA
 * Gestiona la conexión en tiempo real con el servidor
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.url = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.heartbeatInterval = null;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.onConnectCallbacks = [];
        this.onDisconnectCallbacks = [];
        this.onErrorCallbacks = [];
    }

    /**
     * Conecta al servidor WebSocket
     */
    connect(token) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('✅ WebSocket ya está conectado');
            return;
        }

        // Determinar protocolo (ws o wss)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.url = `${protocol}//${window.location.host}/api/v1/ws/notificaciones?token=${token}`;

        console.log('🔌 Conectando a WebSocket...', this.url);

        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = (event) => {
                console.log('✅ WebSocket conectado');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Iniciar heartbeat
                this.startHeartbeat();
                
                // Notificar callbacks
                this.onConnectCallbacks.forEach(cb => cb(event));
                
                // Mostrar notificación
                this.showSystemNotification('Conectado', 'Conexión establecida con el servidor');
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onerror = (error) => {
                console.error('❌ Error en WebSocket:', error);
                this.onErrorCallbacks.forEach(cb => cb(error));
            };

            this.ws.onclose = (event) => {
                console.log('🔌 WebSocket desconectado', event.code, event.reason);
                this.isConnected = false;
                this.stopHeartbeat();
                
                // Notificar callbacks
                this.onDisconnectCallbacks.forEach(cb => cb(event));
                
                // Intentar reconectar
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`🔄 Intentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                    
                    setTimeout(() => {
                        this.connect(token);
                    }, this.reconnectDelay * this.reconnectAttempts);
                } else {
                    console.error('❌ No se pudo reconectar después de varios intentos');
                    this.showSystemNotification('Desconectado', 'No se pudo establecer conexión con el servidor');
                }
            };

        } catch (error) {
            console.error('❌ Error creando WebSocket:', error);
        }
    }

    /**
     * Desconecta el WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.stopHeartbeat();
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
            console.log('🔌 WebSocket desconectado manualmente');
        }
    }

    /**
     * Envía un mensaje al servidor
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('⚠️ WebSocket no está conectado. No se puede enviar mensaje.');
        }
    }

    /**
     * Maneja mensajes recibidos del servidor
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            const tipo = message.tipo;

            console.log('📨 Mensaje recibido:', tipo, message);

            // Llamar handlers registrados para este tipo
            if (this.messageHandlers.has(tipo)) {
                const handlers = this.messageHandlers.get(tipo);
                handlers.forEach(handler => handler(message));
            }

            // Handlers por defecto
            switch (tipo) {
                case 'notificacion':
                    this.handleNotificacion(message);
                    break;
                
                case 'chat':
                    this.handleChatMessage(message);
                    break;
                
                case 'pong':
                    // Respuesta a heartbeat
                    break;
                
                case 'sistema':
                    this.handleSistemaMessage(message);
                    break;
                
                case 'typing':
                    this.handleTyping(message);
                    break;
                
                default:
                    console.log('Tipo de mensaje no manejado:', tipo);
            }

        } catch (error) {
            console.error('❌ Error parseando mensaje:', error);
        }
    }

    /**
     * Maneja notificaciones push
     */
    handleNotificacion(message) {
        // Actualizar contador de notificaciones
        this.updateNotificationBadge();

        // Mostrar notificación del navegador
        if (message.es_urgente) {
            this.showBrowserNotification(message.titulo, message.mensaje, message.accion_url);
        }

        // Mostrar notificación in-app
        mostrarNotificacion(message.mensaje, message.es_urgente ? 'warning' : 'info');

        // Reproducir sonido
        this.playNotificationSound();
    }

    /**
     * Maneja mensajes de chat
     */
    handleChatMessage(message) {
        // Actualizar UI del chat si está abierto
        const chatWindow = document.getElementById('chat-window');
        if (chatWindow) {
            this.appendChatMessage(message);
        }

        // Actualizar contador de mensajes no leídos
        this.updateChatBadge(message.emisor_id);

        // Notificación de nuevo mensaje
        if (!document.hasFocus()) {
            this.showBrowserNotification(
                `Nuevo mensaje de ${message.emisor_nombre}`,
                message.mensaje,
                `/chat/${message.emisor_id}`
            );
        }

        // Reproducir sonido
        this.playMessageSound();
    }

    /**
     * Maneja mensajes del sistema
     */
    handleSistemaMessage(message) {
        console.log('📢 Mensaje del sistema:', message.mensaje);
        
        if (message.evento === 'conectado') {
            console.log('✅ Conexión confirmada por el servidor');
        }
    }

    /**
     * Maneja indicador de "escribiendo..."
     */
    handleTyping(message) {
        const typingIndicator = document.getElementById(`typing-${message.usuario_id}`);
        
        if (typingIndicator) {
            if (message.escribiendo) {
                typingIndicator.style.display = 'block';
            } else {
                typingIndicator.style.display = 'none';
            }
        }
    }

    /**
     * Heartbeat para mantener la conexión activa
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({
                    tipo: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, 30000); // Cada 30 segundos
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Registra un handler para un tipo de mensaje
     */
    on(tipo, handler) {
        if (!this.messageHandlers.has(tipo)) {
            this.messageHandlers.set(tipo, []);
        }
        this.messageHandlers.get(tipo).push(handler);
    }

    /**
     * Registra callback para evento de conexión
     */
    onConnect(callback) {
        this.onConnectCallbacks.push(callback);
    }

    /**
     * Registra callback para evento de desconexión
     */
    onDisconnect(callback) {
        this.onDisconnectCallbacks.push(callback);
    }

    /**
     * Registra callback para errores
     */
    onError(callback) {
        this.onErrorCallbacks.push(callback);
    }

    /**
     * Actualiza el badge de notificaciones
     */
    updateNotificationBadge() {
        const badge = document.querySelector('.badge-notification');
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'flex';
        }
    }

    /**
     * Actualiza el badge de chat
     */
    updateChatBadge(userId) {
        const badge = document.getElementById(`chat-badge-${userId}`);
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'block';
        }
    }

    /**
     * Muestra notificación del navegador
     */
    async showBrowserNotification(title, body, url = null) {
        if (!("Notification" in window)) {
            console.log("Este navegador no soporta notificaciones");
            return;
        }

        if (Notification.permission === "granted") {
            const notification = new Notification(title, {
                body: body,
                icon: '/static/img/logo.png',
                badge: '/static/img/badge.png',
                tag: 'serviplus-notification',
                requireInteraction: true
            });

            if (url) {
                notification.onclick = () => {
                    window.focus();
                    window.location.href = url;
                };
            }
        } else if (Notification.permission !== "denied") {
            const permission = await Notification.requestPermission();
            if (permission === "granted") {
                this.showBrowserNotification(title, body, url);
            }
        }
    }

    /**
     * Muestra notificación del sistema in-app
     */
    showSystemNotification(title, message) {
        console.log(`📢 ${title}: ${message}`);
        // Puedes usar tu función mostrarNotificacion aquí
    }

    /**
     * Reproduce sonido de notificación
     */
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('No se pudo reproducir sonido:', e));
    }

    /**
     * Reproduce sonido de mensaje
     */
    playMessageSound() {
        const audio = new Audio('/static/sounds/message.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('No se pudo reproducir sonido:', e));
    }

    /**
     * Envía notificación de que el usuario está escribiendo
     */
    sendTypingIndicator(destinatarioId, escribiendo = true) {
        this.send({
            tipo: 'typing',
            destinatario_id: destinatarioId,
            escribiendo: escribiendo
        });
    }

    /**
     * Envía un mensaje de chat
     */
    sendChatMessage(destinatarioId, mensaje) {
        this.send({
            tipo: 'chat',
            destinatario_id: destinatarioId,
            mensaje: mensaje,
            timestamp: new Date().toISOString()
        });
    }

    /**
     * Verifica si está conectado
     */
    isAlive() {
        return this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Instancia global
const wsClient = new WebSocketClient();

// Auto-inicializar si hay token
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (token) {
        wsClient.connect(token);
    }
});