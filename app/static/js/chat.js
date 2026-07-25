/**
 * Chat MITA - Estilo WhatsApp
 * WebSocket + UI responsive
 */

class MitaChat {
    constructor(config) {
        this.conversacionId = config.conversacionId;
        this.userType = config.userType; // cliente, secretaria, tecnico
        this.userId = config.userId;
        this.userName = config.userName;
        this.containerId = config.containerId || 'chat-container';

        this.ws = null;
        this.mensajes = [];
        this.isTyping = false;
        this.typingTimeout = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        this.init();
    }

    init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error('Chat container not found');
            return;
        }

        this.render();
        this.connect();
        this.bindEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="mita-chat">
                <!-- Header -->
                <div class="chat-header">
                    <div class="chat-header-info">
                        <div class="chat-avatar">
                            <img src="/static/img/avatar-default.png" alt="Avatar" id="chat-avatar-img">
                        </div>
                        <div class="chat-header-text">
                            <div class="chat-name" id="chat-partner-name">Cargando...</div>
                            <div class="chat-status" id="chat-partner-status">
                                <span class="status-dot"></span>
                                <span class="status-text">en línea</span>
                            </div>
                        </div>
                    </div>
                    <div class="chat-header-actions">
                        <button class="chat-action-btn" onclick="mitaChat.copiarChat()">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button class="chat-action-btn" onclick="mitaChat.compartirWhatsApp()">
                            <i class="fab fa-whatsapp"></i>
                        </button>
                    </div>
                </div>

                <!-- Mensajes -->
                <div class="chat-messages" id="chat-messages">
                    <div class="chat-loading">
                        <div class="spinner"></div>
                        <span>Cargando mensajes...</span>
                    </div>
                </div>

                <!-- Typing indicator -->
                <div class="chat-typing" id="chat-typing" style="display: none;">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                    <span class="typing-text">escribiendo...</span>
                </div>

                <!-- Input -->
                <div class="chat-input-container">
                    <button class="chat-attach-btn" onclick="mitaChat.adjuntar()">
                        <i class="fas fa-paperclip"></i>
                    </button>
                    <div class="chat-input-wrapper">
                        <textarea
                            id="chat-input"
                            placeholder="Escribe un mensaje..."
                            rows="1"
                            maxlength="1000"
                        ></textarea>
                    </div>
                    <button class="chat-send-btn" id="chat-send-btn" onclick="mitaChat.enviar()">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>

                <!-- Preview adjunto -->
                <div class="chat-attachment-preview" id="chat-attachment-preview" style="display: none;">
                    <div class="attachment-content">
                        <img id="attachment-img" src="" alt="">
                        <video id="attachment-video" src="" style="display: none;"></video>
                    </div>
                    <button class="attachment-remove" onclick="mitaChat.removerAdjunto()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversacionId}/${this.userType}/${this.userId}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket conectado');
            this.reconnectAttempts = 0;
            this.cargarMensajes();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket desconectado');
            this.reconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconectando en ${delay / 1000}s...`);
            setTimeout(() => this.connect(), delay);
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'nuevo_mensaje':
                this.agregarMensaje(data.mensaje);
                break;
            case 'typing':
                this.mostrarTyping(data.user_type, data.is_typing);
                break;
            case 'mensajes_leidos':
                this.marcarLeidos(data.mensaje_ids);
                break;
            case 'user_joined':
                this.actualizarEstado(data.user_type, true);
                break;
            case 'user_left':
                this.actualizarEstado(data.user_type, false);
                break;
        }
    }

    async cargarMensajes() {
        try {
            const response = await fetch(`/api/v1/chat/conversacion/${this.conversacionId}/mensajes`);
            const data = await response.json();

            const container = document.getElementById('chat-messages');
            container.innerHTML = '';

            data.mensajes.forEach(msg => this.agregarMensaje(msg, false));
            this.scrollToBottom();
        } catch (error) {
            console.error('Error cargando mensajes:', error);
        }
    }

    agregarMensaje(mensaje, scroll = true) {
        const container = document.getElementById('chat-messages');
        const esMio = mensaje.de_tipo === this.userType && mensaje.de_id == this.userId;

        const msgEl = document.createElement('div');
        msgEl.className = `chat-message ${esMio ? 'sent' : 'received'}`;
        msgEl.dataset.id = mensaje.id;

        let contenido = '';

        // Contenido según tipo
        if (mensaje.tipo_mensaje === 'imagen' || mensaje.tipo === 'imagen') {
            contenido = `<img src="${mensaje.archivo_url}" alt="Imagen" class="msg-image" onclick="mitaChat.verImagen('${mensaje.archivo_url}')">`;
        } else if (mensaje.tipo_mensaje === 'video' || mensaje.tipo === 'video') {
            contenido = `<video src="${mensaje.archivo_url}" controls class="msg-video"></video>`;
        } else if (mensaje.tipo_mensaje === 'ubicacion' || mensaje.tipo === 'ubicacion') {
            contenido = `
                <div class="msg-location" onclick="mitaChat.verMapa(${mensaje.ubicacion_lat}, ${mensaje.ubicacion_lng})">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${mensaje.ubicacion_nombre || 'Ver ubicación'}</span>
                </div>
            `;
        } else {
            contenido = `<div class="msg-text">${this.formatearTexto(mensaje.contenido)}</div>`;
        }

        // Estado del mensaje (checks)
        let estadoIcon = '';
        if (esMio) {
            switch (mensaje.estado) {
                case 'enviando':
                    estadoIcon = '<i class="fas fa-clock msg-status"></i>';
                    break;
                case 'enviado':
                    estadoIcon = '<i class="fas fa-check msg-status"></i>';
                    break;
                case 'entregado':
                    estadoIcon = '<i class="fas fa-check-double msg-status"></i>';
                    break;
                case 'leido':
                    estadoIcon = '<i class="fas fa-check-double msg-status read"></i>';
                    break;
            }
        }

        msgEl.innerHTML = `
            ${!esMio ? `<div class="msg-sender">${mensaje.de_nombre}</div>` : ''}
            ${contenido}
            <div class="msg-meta">
                <span class="msg-time">${this.formatearHora(mensaje.timestamp || mensaje.created_at)}</span>
                ${estadoIcon}
            </div>
        `;

        container.appendChild(msgEl);

        if (scroll) {
            this.scrollToBottom();
        }

        // Marcar como leído si no es mío
        if (!esMio && mensaje.id) {
            this.enviarLeido([mensaje.id]);
        }
    }

    formatearTexto(texto) {
        if (!texto) return '';
        // Escapar HTML
        texto = texto.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        // Links
        texto = texto.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
        // Saltos de línea
        texto = texto.replace(/\n/g, '<br>');
        return texto;
    }

    formatearHora(timestamp) {
        const fecha = new Date(timestamp);
        return fecha.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
    }

    bindEvents() {
        const input = document.getElementById('chat-input');

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
            this.enviarTyping(true);
        });

        // Enter para enviar (Shift+Enter para nueva línea)
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.enviar();
            }
        });
    }

    enviar() {
        const input = document.getElementById('chat-input');
        const texto = input.value.trim();

        if (!texto && !this.archivoAdjunto) return;

        const tempId = Date.now();

        // Agregar mensaje local inmediatamente
        this.agregarMensaje({
            id: tempId,
            de_tipo: this.userType,
            de_id: this.userId,
            de_nombre: this.userName,
            contenido: texto,
            tipo_mensaje: 'texto',
            timestamp: new Date().toISOString(),
            estado: 'enviando'
        });

        // Enviar por WebSocket
        this.ws.send(JSON.stringify({
            type: 'mensaje',
            temp_id: tempId,
            contenido: texto,
            tipo_mensaje: 'texto',
            de_nombre: this.userName
        }));

        // Limpiar input
        input.value = '';
        input.style.height = 'auto';
        this.enviarTyping(false);
    }

    enviarTyping(isTyping) {
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        if (isTyping && !this.isTyping) {
            this.isTyping = true;
            this.ws.send(JSON.stringify({
                type: 'typing',
                is_typing: true
            }));
        }

        this.typingTimeout = setTimeout(() => {
            if (this.isTyping) {
                this.isTyping = false;
                this.ws.send(JSON.stringify({
                    type: 'typing',
                    is_typing: false
                }));
            }
        }, 2000);
    }

    enviarLeido(mensajeIds) {
        this.ws.send(JSON.stringify({
            type: 'leido',
            mensaje_ids: mensajeIds
        }));
    }

    mostrarTyping(userType, isTyping) {
        const el = document.getElementById('chat-typing');
        if (userType !== this.userType) {
            el.style.display = isTyping ? 'flex' : 'none';
        }
    }

    marcarLeidos(mensajeIds) {
        mensajeIds.forEach(id => {
            const msgEl = document.querySelector(`.chat-message[data-id="${id}"] .msg-status`);
            if (msgEl) {
                msgEl.className = 'fas fa-check-double msg-status read';
            }
        });
    }

    actualizarEstado(userType, online) {
        const statusEl = document.getElementById('chat-partner-status');
        if (userType !== this.userType) {
            statusEl.innerHTML = online
                ? '<span class="status-dot online"></span><span class="status-text">en línea</span>'
                : '<span class="status-dot"></span><span class="status-text">desconectado</span>';
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }

    adjuntar() {
        // TODO: Implementar selector de archivos
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*,video/*';
        input.onchange = (e) => this.handleAdjunto(e.target.files[0]);
        input.click();
    }

    handleAdjunto(file) {
        // TODO: Subir archivo y enviar
        console.log('Adjunto:', file);
    }

    removerAdjunto() {
        this.archivoAdjunto = null;
        const preview = document.getElementById('chat-attachment-preview');
        if (preview) preview.style.display = 'none';
    }

    copiarChat() {
        const mensajes = Array.from(document.querySelectorAll('.chat-message'))
            .map(el => {
                const sender = el.querySelector('.msg-sender')?.textContent || 'Yo';
                const text = el.querySelector('.msg-text')?.textContent || '[multimedia]';
                const time = el.querySelector('.msg-time')?.textContent || '';
                return `[${time}] ${sender}: ${text}`;
            })
            .join('\n');

        navigator.clipboard.writeText(mensajes).then(() => {
            alert('Chat copiado al portapapeles');
        });
    }

    compartirWhatsApp() {
        const ultimoMensaje = document.querySelector('.chat-message:last-child .msg-text')?.textContent || '';
        const url = `https://wa.me/?text=${encodeURIComponent(ultimoMensaje)}`;
        window.open(url, '_blank');
    }

    verImagen(url) {
        // TODO: Lightbox
        window.open(url, '_blank');
    }

    verMapa(lat, lng) {
        window.open(`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`, '_blank');
    }
}

// Instancia global
let mitaChat = null;

function iniciarChat(config) {
    mitaChat = new MitaChat(config);
}
