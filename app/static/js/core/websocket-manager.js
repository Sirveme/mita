// ============================================
// MITA - WEBSOCKET MANAGER
// Ubicación: app/static/js/core/websocket-manager.js
// ============================================

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.userId = null;
        this.userRole = null;
        this.connectionId = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1 segundo inicial
        this.heartbeatInterval = null;
        this.handlers = {};
        this.messageQueue = [];
        this.config = {
            heartbeatInterval: 30000, // 30 segundos
            reconnectBackoff: true,
            maxReconnectDelay: 30000, // 30 segundos máximo
            debug: true
        };
    }

    // ============================================
    // CONEXIÓN
    // ============================================
    
    async connect(userId, userRole) {
        if (this.isConnected) {
            this.log('Ya hay una conexión activa', 'warn');
            return;
        }

        this.userId = userId;
        this.userRole = userRole;
        this.connectionId = this.generateConnectionId();

        const token = localStorage.getItem('token');
        if (!token) {
            this.log('No hay token de autenticación', 'error');
            this.trigger('error', { message: 'No autenticado' });
            return;
        }

        try {
            // Determinar protocolo (ws:// o wss://)
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            
            // URL del WebSocket
            const wsUrl = `${protocol}//${host}/api/v1/ws/notificaciones?token=${token}`;
            
            this.log(`Conectando a: ${wsUrl}`, 'info');
            
            // Crear conexión WebSocket
            this.ws = new WebSocket(wsUrl);
            
            // Event Handlers
            this.ws.onopen = this.onOpen.bind(this);
            this.ws.onmessage = this.onMessage.bind(this);
            this.ws.onerror = this.onError.bind(this);
            this.ws.onclose = this.onClose.bind(this);
            
        } catch (error) {
            this.log('Error creando WebSocket: ' + error.message, 'error');
            this.attemptReconnect();
        }
    }

    disconnect() {
        this.log('Desconectando...', 'info');
        
        this.stopHeartbeat();
        
        if (this.ws) {
            this.ws.close(1000, 'Usuario desconectó');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.messageQueue = [];
        
        this.trigger('disconnected');
    }

    // ============================================
    // EVENT HANDLERS
    // ============================================
    
    onOpen(event) {
        this.log('✅ Conexión WebSocket establecida', 'success');
        
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Iniciar heartbeat
        this.startHeartbeat();
        
        // Enviar mensajes en cola
        this.flushMessageQueue();
        
        // Trigger callback
        this.trigger('connected', {
            connectionId: this.connectionId,
            userId: this.userId,
            userRole: this.userRole
        });
    }

    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            this.log(`📩 Mensaje recibido: ${message.tipo}`, 'info');
            
            // Respuesta a ping
            if (message.tipo === 'pong') {
                this.log('💓 Heartbeat OK', 'debug');
                return;
            }
            
            // Sistema: Confirmación de conexión
            if (message.tipo === 'sistema' && message.evento === 'conectado') {
                this.log('Sistema confirmó conexión', 'info');
                return;
            }
            
            // Llamar handler específico del tipo de mensaje
            this.handleMessage(message);
            
        } catch (error) {
            this.log('Error parseando mensaje: ' + error.message, 'error');
        }
    }

    onError(error) {
        this.log('❌ Error WebSocket: ' + error, 'error');
        this.trigger('error', { error });
    }

    onClose(event) {
        this.log(`🔌 Conexión cerrada (código: ${event.code})`, 'warn');
        
        this.isConnected = false;
        this.stopHeartbeat();
        
        this.trigger('disconnected', {
            code: event.code,
            reason: event.reason
        });
        
        // Intentar reconectar si no fue cierre normal
        if (event.code !== 1000) {
            this.attemptReconnect();
        }
    }

    // ============================================
    // ENVIAR MENSAJES
    // ============================================
    
    send(message) {
        if (!this.isConnected) {
            this.log('No conectado, encolando mensaje', 'warn');
            this.messageQueue.push(message);
            return false;
        }

        try {
            const messageStr = JSON.stringify(message);
            this.ws.send(messageStr);
            this.log(`📤 Mensaje enviado: ${message.tipo}`, 'debug');
            return true;
        } catch (error) {
            this.log('Error enviando mensaje: ' + error.message, 'error');
            this.messageQueue.push(message);
            return false;
        }
    }

    // ============================================
    // MENSAJES ESPECÍFICOS
    // ============================================
    
    sendChatMessage(destinatarioId, mensaje, servicioId = null) {
        return this.send({
            tipo: 'chat',
            destinatario_id: destinatarioId,
            mensaje: mensaje,
            servicio_id: servicioId,
            timestamp: new Date().toISOString()
        });
    }

    sendTypingIndicator(destinatarioId, isTyping = true) {
        return this.send({
            tipo: 'typing',
            destinatario_id: destinatarioId,
            escribiendo: isTyping
        });
    }

    sendLocationUpdate(latitude, longitude, servicioId) {
        return this.send({
            tipo: 'ubicacion',
            servicio_id: servicioId,
            latitude: latitude,
            longitude: longitude,
            timestamp: new Date().toISOString()
        });
    }

    sendServiceStatusUpdate(servicioId, nuevoEstado, notas = null) {
        return this.send({
            tipo: 'estado_servicio',
            servicio_id: servicioId,
            nuevo_estado: nuevoEstado,
            notas: notas,
            timestamp: new Date().toISOString()
        });
    }

    acceptService(servicioId) {
        return this.send({
            tipo: 'aceptar_servicio',
            servicio_id: servicioId,
            timestamp: new Date().toISOString()
        });
    }

    rejectService(servicioId, motivo = null) {
        return this.send({
            tipo: 'rechazar_servicio',
            servicio_id: servicioId,
            motivo: motivo,
            timestamp: new Date().toISOString()
        });
    }

    // ============================================
    // HEARTBEAT (PING/PONG)
    // ============================================
    
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({
                    tipo: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, this.config.heartbeatInterval);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    // ============================================
    // RECONEXIÓN
    // ============================================
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.log('❌ Máximo de reintentos alcanzado', 'error');
            this.trigger('max_reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        
        // Backoff exponencial
        let delay = this.reconnectDelay;
        if (this.config.reconnectBackoff) {
            delay = Math.min(
                this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
                this.config.maxReconnectDelay
            );
        }

        this.log(`🔄 Reconectando en ${delay/1000}s (intento ${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'info');
        
        this.trigger('reconnecting', {
            attempt: this.reconnectAttempts,
            delay: delay
        });

        setTimeout(() => {
            this.connect(this.userId, this.userRole);
        }, delay);
    }

    // ============================================
    // HANDLERS DE MENSAJES
    // ============================================
    
    handleMessage(message) {
        const { tipo } = message;
        
        // Handler específico para este tipo
        if (this.handlers[tipo]) {
            this.handlers[tipo](message);
        }
        
        // Handler genérico (para todos los mensajes)
        if (this.handlers['*']) {
            this.handlers['*'](message);
        }
        
        // Trigger como evento
        this.trigger(tipo, message);
    }

    on(eventType, handler) {
        this.handlers[eventType] = handler;
    }

    off(eventType) {
        delete this.handlers[eventType];
    }

    trigger(event, data = null) {
        if (this.handlers[event]) {
            this.handlers[event](data);
        }
    }

    // ============================================
    // COLA DE MENSAJES
    // ============================================
    
    flushMessageQueue() {
        if (this.messageQueue.length === 0) {
            return;
        }

        this.log(`📬 Enviando ${this.messageQueue.length} mensajes en cola`, 'info');
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    // ============================================
    // UTILIDADES
    // ============================================
    
    generateConnectionId() {
        return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    log(message, level = 'info') {
        if (!this.config.debug && level === 'debug') {
            return;
        }

        const emoji = {
            'info': 'ℹ️',
            'success': '✅',
            'warn': '⚠️',
            'error': '❌',
            'debug': '🔍'
        };

        const prefix = `[WS ${emoji[level] || ''}]`;
        
        if (level === 'error') {
            console.error(prefix, message);
        } else if (level === 'warn') {
            console.warn(prefix, message);
        } else {
            console.log(prefix, message);
        }
    }

    // ============================================
    // GETTERS
    // ============================================
    
    getConnectionState() {
        if (!this.ws) return 'DISCONNECTED';
        
        const states = {
            0: 'CONNECTING',
            1: 'OPEN',
            2: 'CLOSING',
            3: 'CLOSED'
        };
        
        return states[this.ws.readyState] || 'UNKNOWN';
    }

    isOnline() {
        return this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    getStats() {
        return {
            connected: this.isConnected,
            userId: this.userId,
            userRole: this.userRole,
            connectionId: this.connectionId,
            reconnectAttempts: this.reconnectAttempts,
            messageQueueLength: this.messageQueue.length,
            state: this.getConnectionState()
        };
    }
}

// ============================================
// EXPORTAR
// ============================================
window.WebSocketManager = WebSocketManager;

console.log('[WS] WebSocketManager cargado ✅');