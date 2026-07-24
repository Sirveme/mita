// ============================================
// MITA - CHAT WIDGET
// Ubicación: app/static/js/components/chat-widget.js
// ============================================

class ChatWidget {
    constructor() {
        this.isOpen = false;
        this.currentChat = null;
        this.messages = [];
        this.unreadCount = 0;
        this.isTyping = false;
        
        this.init();
    }

    // ============================================
    // INICIALIZACIÓN
    // ============================================
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        console.log('[Chat Widget] Inicializado ✅');
    }

    createWidget() {
        // Crear HTML del widget
        const widget = document.createElement('div');
        widget.id = 'chat-widget';
        widget.innerHTML = `
            <!-- Botón flotante -->
            <button id="chat-toggle-btn" class="chat-toggle-btn">
                <span class="chat-icon">💬</span>
                <span class="chat-badge" style="display: none;">0</span>
            </button>

            <!-- Ventana de chat -->
            <div id="chat-window" class="chat-window" style="display: none;">
                <!-- Header -->
                <div class="chat-header">
                    <div class="chat-header-info">
                        <img src="/static/img/avatar-default.svg" 
                             alt="Avatar" 
                             class="chat-avatar"
                             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E%3Ccircle cx=%2250%22 cy=%2250%22 r=%2250%22 fill=%22%23FFCD11%22/%3E%3Ctext x=%2250%22 y=%2265%22 text-anchor=%22middle%22 font-size=%2240%22 fill=%22%230f1419%22%3E👤%3C/text%3E%3C/svg%3E'">
                        <div class="chat-header-text">
                            <h3 id="chat-contact-name">Técnico</h3>
                            <p id="chat-contact-status" class="chat-status">En línea</p>
                        </div>
                    </div>
                    <div class="chat-header-actions">
                        <button id="chat-minimize-btn" class="chat-action-btn" title="Minimizar">
                            <span>─</span>
                        </button>
                        <button id="chat-close-btn" class="chat-action-btn" title="Cerrar">
                            <span>✕</span>
                        </button>
                    </div>
                </div>

                <!-- Mensajes -->
                <div id="chat-messages" class="chat-messages">
                    <div class="chat-empty">
                        <span class="chat-empty-icon">💬</span>
                        <p>No hay mensajes aún</p>
                        <small>Inicia la conversación</small>
                    </div>
                </div>

                <!-- Indicador "escribiendo..." -->
                <div id="chat-typing" class="chat-typing" style="display: none;">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-text">escribiendo...</span>
                </div>

                <!-- Input -->
                <div class="chat-input-container">
                    <button id="chat-attach-btn" class="chat-attach-btn" title="Adjuntar">
                        📎
                    </button>
                    <input 
                        type="text" 
                        id="chat-input" 
                        class="chat-input" 
                        placeholder="Escribe un mensaje..."
                        autocomplete="off">
                    <button id="chat-send-btn" class="chat-send-btn" title="Enviar">
                        ➤
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(widget);
    }

    attachEventListeners() {
        // Toggle chat
        const toggleBtn = document.getElementById('chat-toggle-btn');
        toggleBtn?.addEventListener('click', () => this.toggleChat());

        // Minimizar
        const minimizeBtn = document.getElementById('chat-minimize-btn');
        minimizeBtn?.addEventListener('click', () => this.minimizeChat());

        // Cerrar
        const closeBtn = document.getElementById('chat-close-btn');
        closeBtn?.addEventListener('click', () => this.closeChat());

        // Enviar mensaje
        const sendBtn = document.getElementById('chat-send-btn');
        sendBtn?.addEventListener('click', () => this.sendMessage());

        // Enter para enviar
        const input = document.getElementById('chat-input');
        input?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // Indicador de escritura
        input?.addEventListener('input', () => {
            this.handleTyping();
        });

        // Adjuntar archivo
        const attachBtn = document.getElementById('chat-attach-btn');
        attachBtn?.addEventListener('click', () => this.handleAttach());
    }

    // ============================================
    // ACCIONES
    // ============================================
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        const chatWindow = document.getElementById('chat-window');
        const toggleBtn = document.getElementById('chat-toggle-btn');
        
        chatWindow.style.display = 'flex';
        toggleBtn.classList.add('active');
        
        this.isOpen = true;
        this.clearUnreadCount();
        
        // Scroll to bottom
        setTimeout(() => {
            this.scrollToBottom();
            document.getElementById('chat-input')?.focus();
        }, 100);

        console.log('[Chat Widget] Abierto');
    }

    closeChat() {
        const chatWindow = document.getElementById('chat-window');
        const toggleBtn = document.getElementById('chat-toggle-btn');
        
        chatWindow.style.display = 'none';
        toggleBtn.classList.remove('active');
        
        this.isOpen = false;
        
        console.log('[Chat Widget] Cerrado');
    }

    minimizeChat() {
        this.closeChat();
    }

    // ============================================
    // MENSAJES
    // ============================================
    
    sendMessage() {
        const input = document.getElementById('chat-input');
        const mensaje = input?.value.trim();

        if (!mensaje) return;

        // Agregar mensaje propio
        this.addMessage({
            id: Date.now(),
            texto: mensaje,
            emisor: 'yo',
            timestamp: new Date().toISOString()
        });

        // Limpiar input
        input.value = '';

        // Enviar por WebSocket
        if (window.wsManager && this.currentChat) {
            // Simular envío
            console.log('[Chat Widget] 📤 Enviando mensaje:', mensaje);
            
            // Usar el método correcto del mock
            if (typeof window.wsManager.sendChatMessage === 'function') {
                window.wsManager.sendChatMessage(
                    this.currentChat.userId,
                    mensaje,
                    this.currentChat.servicioId
                );
            } else {
                // Fallback: enviar directo
                window.wsManager.send({
                    tipo: 'chat',
                    destinatario_id: this.currentChat.userId,
                    mensaje: mensaje,
                    servicio_id: this.currentChat.servicioId,
                    timestamp: new Date().toISOString()
                });
            }
        }

        console.log('[Chat Widget] ✅ Mensaje enviado');
    }

    receiveMessage(data) {
        // Agregar mensaje recibido
        this.addMessage({
            id: data.mensaje_id || Date.now(),
            texto: data.mensaje,
            emisor: data.emisor_nombre || 'Técnico',
            timestamp: data.timestamp || new Date().toISOString(),
            avatar: data.emisor_foto || null
        });

        // Si el chat está cerrado, incrementar contador
        if (!this.isOpen) {
            this.incrementUnreadCount();
        }

        // Reproducir sonido (opcional)
        this.playNotificationSound();
    }

    addMessage(message) {
        this.messages.push(message);

        const messagesContainer = document.getElementById('chat-messages');
        
        // Remover mensaje vacío si existe
        const emptyMsg = messagesContainer?.querySelector('.chat-empty');
        if (emptyMsg) {
            emptyMsg.remove();
        }

        // Crear elemento de mensaje
        const messageEl = this.createMessageElement(message);
        messagesContainer?.appendChild(messageEl);

        // Scroll to bottom
        this.scrollToBottom();
    }

    createMessageElement(message) {
        const div = document.createElement('div');
        div.className = `chat-message ${message.emisor === 'yo' ? 'chat-message-own' : 'chat-message-other'}`;
        
        const time = new Date(message.timestamp).toLocaleTimeString('es-PE', {
            hour: '2-digit',
            minute: '2-digit'
        });

        if (message.emisor === 'yo') {
            div.innerHTML = `
                <div class="chat-message-bubble">
                    <p>${this.escapeHtml(message.texto)}</p>
                    <span class="chat-message-time">${time}</span>
                </div>
            `;
        } else {
            div.innerHTML = `
                <img src="${message.avatar || '/static/img/avatar-default.png'}" 
                     class="chat-message-avatar"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E%3Ccircle cx=%2250%22 cy=%2250%22 r=%2250%22 fill=%22%23FFCD11%22/%3E%3Ctext x=%2250%22 y=%2265%22 text-anchor=%22middle%22 font-size=%2240%22 fill=%22%230f1419%22%3E👤%3C/text%3E%3C/svg%3E'">
                <div class="chat-message-bubble">
                    <p class="chat-message-sender">${this.escapeHtml(message.emisor)}</p>
                    <p>${this.escapeHtml(message.texto)}</p>
                    <span class="chat-message-time">${time}</span>
                </div>
            `;
        }

        return div;
    }

    // ============================================
    // INDICADORES
    // ============================================
    
    showTypingIndicator() {
        const typingEl = document.getElementById('chat-typing');
        typingEl.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingEl = document.getElementById('chat-typing');
        typingEl.style.display = 'none';
    }

    handleTyping() {
        // Notificar al otro usuario que estás escribiendo
        if (window.wsManager && this.currentChat) {
            window.wsManager.send({
                tipo: 'typing',
                destinatario_id: this.currentChat.userId,
                escribiendo: true
            });
        }

        // Detener indicador después de 2 segundos sin escribir
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            if (window.wsManager && this.currentChat) {
                window.wsManager.send({
                    tipo: 'typing',
                    destinatario_id: this.currentChat.userId,
                    escribiendo: false
                });
            }
        }, 2000);
    }

    // ============================================
    // CONTADOR NO LEÍDOS
    // ============================================
    
    incrementUnreadCount() {
        this.unreadCount++;
        this.updateBadge();
    }

    clearUnreadCount() {
        this.unreadCount = 0;
        this.updateBadge();
    }

    updateBadge() {
        const badge = document.querySelector('.chat-badge');
        
        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    // ============================================
    // CONFIGURACIÓN
    // ============================================
    
    setContact(contactData) {
        this.currentChat = contactData;

        const nameEl = document.getElementById('chat-contact-name');
        const statusEl = document.getElementById('chat-contact-status');
        const avatarEl = document.querySelector('.chat-header .chat-avatar');

        if (nameEl) nameEl.textContent = contactData.nombre;
        if (statusEl) statusEl.textContent = contactData.estado || 'En línea';
        if (avatarEl && contactData.foto) avatarEl.src = contactData.foto;

        console.log('[Chat Widget] Contacto configurado:', contactData.nombre);
    }

    setStatus(status) {
        const statusEl = document.getElementById('chat-contact-status');
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = 'chat-status ' + (status === 'En línea' ? 'online' : '');
        }
    }

    // ============================================
    // UTILIDADES
    // ============================================
    
    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    playNotificationSound() {
        // Opcional: reproducir sonido
        try {
            const audio = new Audio('/static/sounds/message.mp3');
            audio.volume = 0.5;
            audio.play().catch(() => {});
        } catch (e) {}
    }

    handleAttach() {
        showToast('Funcionalidad de adjuntos próximamente', 'info');
        // TODO: Implementar subida de archivos
    }

    // ============================================
    // API PÚBLICA
    // ============================================
    
    open() {
        this.openChat();
    }

    close() {
        this.closeChat();
    }

    clear() {
        this.messages = [];
        const container = document.getElementById('chat-messages');
        if (container) {
            container.innerHTML = `
                <div class="chat-empty">
                    <span class="chat-empty-icon">💬</span>
                    <p>No hay mensajes aún</p>
                    <small>Inicia la conversación</small>
                </div>
            `;
        }
    }
}

// ============================================
// EXPORTAR E INICIALIZAR
// ============================================

window.ChatWidget = ChatWidget;

// Auto-inicializar
let chatWidget = null;

document.addEventListener('DOMContentLoaded', () => {
    chatWidget = new ChatWidget();
    window.chatWidget = chatWidget;
    
    console.log('[Chat Widget] Widget cargado ✅');
});

console.log('[Chat Widget] chat-widget.js cargado ✅');