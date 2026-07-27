/**
 * MITA Chat - Versión funcional completa (WhatsApp style)
 * Renderiza en #chat-messages (o #messagesContainer) y usa
 * #chat-input, #btn-enviar, #btn-adjuntar, #btn-emoji.
 * Requiere chat_whatsapp.css para las clases .wa-message.
 */

class MitaChat {
    constructor(config) {
        config = config || {};
        this.conversacionId = config.conversacionId || 1;
        this.userType = config.userType || 'cliente';
        this.userId = config.userId || 1;
        this.userName = config.userName || 'Usuario';
        // default demo=true, pero permite false explícito (fix del bug `|| true`)
        this.demoMode = config.demoMode !== false;
        this.ws = null;
        this.mensajes = [];
        this.typing = false;
        this.typingTimeout = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.cargarMensajes();
        if (!this.demoMode) this.connect();
    }

    bindEvents() {
        const input = document.getElementById('chat-input') || document.getElementById('messageInput');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.enviarMensaje(); }
            });
            input.addEventListener('input', () => { this.ajustarAlturaInput(input); this.mostrarTyping(); });
        }

        const btnEnviar = document.getElementById('btn-enviar') || document.getElementById('sendBtn');
        if (btnEnviar) btnEnviar.addEventListener('click', () => this.enviarMensaje());

        const btnAdjuntar = document.getElementById('btn-adjuntar') || document.getElementById('attachBtn');
        if (btnAdjuntar) btnAdjuntar.addEventListener('click', () => this.abrirSelectorArchivo());

        let fileInput = document.getElementById('file-input');
        if (!fileInput) {
            fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.id = 'file-input';
            fileInput.accept = 'image/*,.pdf,.doc,.docx';
            fileInput.multiple = true;
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
        }
        fileInput.addEventListener('change', (e) => this.procesarArchivos(e.target.files));

        const btnEmoji = document.getElementById('btn-emoji');
        if (btnEmoji) btnEmoji.addEventListener('click', () => this.toggleEmojiPicker());
    }

    ajustarAlturaInput(input) {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    mostrarTyping() {
        if (!this.demoMode && this.ws && this.ws.readyState === WebSocket.OPEN) {
            // Enviar indicador de typing (real)
        }
    }

    async cargarMensajes() {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;

        container.innerHTML = '<div class="chat-loading"><div class="spinner"></div>Cargando mensajes...</div>';

        if (this.demoMode) {
            await new Promise(r => setTimeout(r, 400));
            this.cargarMensajesDemo();
            return;
        }

        try {
            const response = await fetch(`/api/v1/chat/conversacion/${this.conversacionId}/mensajes`);
            if (!response.ok) throw new Error('API no disponible');
            const data = await response.json();
            container.innerHTML = '';
            (data.mensajes || []).forEach(msg => this.renderizarMensaje(msg, false));
            this.scrollToBottom();
        } catch (error) {
            console.log('Usando modo demo:', error.message);
            this.cargarMensajesDemo();
        }
    }

    cargarMensajesDemo() {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;
        container.innerHTML = '';

        const t = (ms) => new Date(Date.now() - ms).toISOString();
        const mensajesDemo = [
            { id: 1, tipo: 'sistema', de_tipo: 'sistema', de_nombre: 'Sistema', contenido: 'Solicitud de servicio #1234 creada - Gasfitería', created_at: t(3600000), estado: 'leido' },
            { id: 2, tipo: 'texto', de_tipo: 'cliente', de_id: 1, de_nombre: 'Juan Pérez', contenido: 'Hola, tengo una fuga de agua en la cocina. El caño está goteando desde ayer.', created_at: t(3500000), estado: 'leido' },
            { id: 3, tipo: 'texto', de_tipo: 'secretaria', de_id: 1, de_nombre: 'María García', contenido: '¡Hola Juan! Entiendo, una fuga puede ser molesta. ¿Es urgente o podemos programar para hoy en la tarde?', created_at: t(3400000), estado: 'leido' },
            { id: 4, tipo: 'texto', de_tipo: 'cliente', de_id: 1, de_nombre: 'Juan Pérez', contenido: 'Sí, es bastante urgente porque está mojando el piso y tengo miedo que se dañe la madera.', created_at: t(3300000), estado: 'leido' },
            { id: 5, tipo: 'texto', de_tipo: 'secretaria', de_id: 1, de_nombre: 'María García', contenido: 'Perfecto, te asignaré a Carlos López, nuestro técnico especialista en gasfitería. Estará en tu domicilio en aproximadamente 30 minutos. El costo de la visita es S/ 50.00', created_at: t(3200000), estado: 'leido' },
            { id: 6, tipo: 'sistema', de_tipo: 'sistema', de_nombre: 'Sistema', contenido: '✓ Técnico Carlos López asignado al servicio', created_at: t(3100000), estado: 'leido' },
            { id: 7, tipo: 'texto', de_tipo: 'tecnico', de_id: 1, de_nombre: 'Carlos López', contenido: 'Buenas tardes Sr. Juan, soy Carlos el técnico asignado. Ya estoy en camino. ¿Me puede confirmar la dirección exacta?', created_at: t(1800000), estado: 'leido' },
            { id: 8, tipo: 'texto', de_tipo: 'cliente', de_id: 1, de_nombre: 'Juan Pérez', contenido: '¡Perfecto! Estoy en Av. Arequipa 1234, San Isidro. Edificio azul, departamento 502.', created_at: t(1700000), estado: 'leido' },
            { id: 9, tipo: 'texto', de_tipo: 'tecnico', de_id: 1, de_nombre: 'Carlos López', contenido: 'Excelente, llego en 10 minutos aproximadamente. 🚗', created_at: t(1600000), estado: 'entregado' }
        ];

        this.mensajes = mensajesDemo;
        mensajesDemo.forEach(msg => this.renderizarMensaje(msg, false));
        this.scrollToBottom();
    }

    renderizarMensaje(msg, animate = true) {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;

        const div = document.createElement('div');
        const esMio = msg.de_tipo === this.userType;

        if (msg.tipo === 'sistema' || msg.de_tipo === 'sistema') {
            div.className = 'wa-message system';
            div.innerHTML = `<div class="bubble">${this.formatearTexto(msg.contenido)}</div>`;
        } else {
            div.className = `wa-message ${esMio ? 'sent' : 'received'}`;
            const hora = new Date(msg.created_at).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
            let estadoIcon = '';
            if (esMio) {
                if (msg.estado === 'leido') estadoIcon = '<span class="status read">✓✓</span>';
                else if (msg.estado === 'entregado') estadoIcon = '<span class="status">✓✓</span>';
                else estadoIcon = '<span class="status">✓</span>';
            }
            div.innerHTML = `
                <div class="bubble">
                    ${!esMio ? `<div class="sender-name">${this.formatearTexto(msg.de_nombre || 'Usuario')}</div>` : ''}
                    <div class="text">${this.formatearTexto(msg.contenido)}</div>
                    <div class="meta"><span class="time">${hora}</span>${estadoIcon}</div>
                </div>`;
        }

        if (animate) { div.style.opacity = '0'; div.style.transform = 'translateY(10px)'; }
        container.appendChild(div);
        if (animate) {
            requestAnimationFrame(() => {
                div.style.transition = 'all 0.2s ease-out';
                div.style.opacity = '1';
                div.style.transform = 'translateY(0)';
            });
        }
    }

    formatearTexto(texto) {
        if (!texto) return '';
        texto = String(texto).replace(/</g, '&lt;').replace(/>/g, '&gt;');
        texto = texto.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        texto = texto.replace(/\n/g, '<br>');
        return texto;
    }

    enviarMensaje() {
        const input = document.getElementById('chat-input') || document.getElementById('messageInput');
        if (!input) return;
        const texto = input.value.trim();
        if (!texto) return;

        const nuevoMensaje = {
            id: Date.now(), tipo: 'texto', de_tipo: this.userType, de_id: this.userId,
            de_nombre: this.userName, contenido: texto, created_at: new Date().toISOString(), estado: 'enviado'
        };
        this.renderizarMensaje(nuevoMensaje, true);
        this.scrollToBottom();

        input.value = '';
        input.style.height = 'auto';
        input.focus();

        if (!this.demoMode && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'mensaje', contenido: texto, de_nombre: this.userName, tipo_mensaje: 'texto' }));
        } else {
            this.simularRespuestaDemo(texto);
        }
    }

    simularRespuestaDemo(textoUsuario) {
        setTimeout(() => this.mostrarIndicadorTyping(), 1000);
        setTimeout(() => {
            this.ocultarIndicadorTyping();
            const respuestas = [
                'Entendido, estamos procesando tu solicitud.',
                'Gracias por la información. Un momento por favor.',
                'Perfecto, ya tenemos tu solicitud registrada.',
                'De acuerdo, el técnico ha sido notificado.'
            ];
            const respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
            this.renderizarMensaje({
                id: Date.now(), tipo: 'texto', de_tipo: 'secretaria', de_id: 1,
                de_nombre: 'María García', contenido: respuesta, created_at: new Date().toISOString(), estado: 'leido'
            }, true);
            this.scrollToBottom();
        }, 2500);
    }

    mostrarIndicadorTyping() {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;
        const existing = document.getElementById('typing-indicator');
        if (existing) existing.remove();
        const div = document.createElement('div');
        div.id = 'typing-indicator';
        div.className = 'wa-message received';
        div.innerHTML = `<div class="bubble typing"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
        container.appendChild(div);
        this.scrollToBottom();
    }

    ocultarIndicadorTyping() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    abrirSelectorArchivo() {
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.click();
    }

    async procesarArchivos(files) {
        if (!files || files.length === 0) return;
        for (const file of files) {
            if (file.size > 10 * 1024 * 1024) {
                if (window.MitaAlert) MitaAlert.error('Archivo muy grande', `${file.name} supera el límite de 10MB`);
                else alert(`${file.name} supera el límite de 10MB`);
                continue;
            }
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.renderizarMensajeImagen({
                        id: Date.now(), de_tipo: this.userType, de_nombre: this.userName,
                        imagen_url: e.target.result, created_at: new Date().toISOString(), estado: 'enviado'
                    });
                    this.scrollToBottom();
                };
                reader.readAsDataURL(file);
            } else {
                this.renderizarMensajeArchivo({
                    id: Date.now(), de_tipo: this.userType, de_nombre: this.userName,
                    archivo_nombre: file.name, archivo_size: file.size, created_at: new Date().toISOString(), estado: 'enviado'
                });
                this.scrollToBottom();
            }
        }
        document.getElementById('file-input').value = '';
    }

    renderizarMensajeImagen(msg) {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;
        const esMio = msg.de_tipo === this.userType;
        const hora = new Date(msg.created_at).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
        const div = document.createElement('div');
        div.className = `wa-message ${esMio ? 'sent' : 'received'}`;
        div.innerHTML = `
            <div class="bubble image-bubble">
                <img src="${msg.imagen_url}" alt="Imagen" onclick="window.open(this.src)" style="max-width: 250px; border-radius: 8px; cursor: pointer;">
                <div class="meta"><span class="time">${hora}</span>${esMio ? '<span class="status">✓</span>' : ''}</div>
            </div>`;
        container.appendChild(div);
    }

    renderizarMensajeArchivo(msg) {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (!container) return;
        const esMio = msg.de_tipo === this.userType;
        const hora = new Date(msg.created_at).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
        const sizeKB = Math.round(msg.archivo_size / 1024);
        const div = document.createElement('div');
        div.className = `wa-message ${esMio ? 'sent' : 'received'}`;
        div.innerHTML = `
            <div class="bubble file-bubble">
                <div class="file-info"><i class="fas fa-file"></i>
                    <div><div class="file-name">${this.formatearTexto(msg.archivo_nombre)}</div><div class="file-size">${sizeKB} KB</div></div>
                </div>
                <div class="meta"><span class="time">${hora}</span>${esMio ? '<span class="status">✓</span>' : ''}</div>
            </div>`;
        container.appendChild(div);
    }

    toggleEmojiPicker() {
        const emojis = ['😀', '😂', '👍', '❤️', '🙏', '👋', '✅', '⭐', '🔧', '💡'];
        let picker = document.getElementById('emoji-picker');
        if (picker) { picker.remove(); return; }
        picker = document.createElement('div');
        picker.id = 'emoji-picker';
        picker.style.cssText = 'position:absolute; bottom:60px; left:16px; background:#111118; border:1px solid #2a2a3a; border-radius:8px; padding:8px; display:flex; gap:4px; z-index:100;';
        emojis.forEach(emoji => {
            const btn = document.createElement('button');
            btn.textContent = emoji;
            btn.style.cssText = 'background:transparent; border:none; font-size:20px; cursor:pointer; padding:4px; border-radius:4px;';
            btn.onmouseover = () => btn.style.background = '#2a2a3a';
            btn.onmouseout = () => btn.style.background = 'transparent';
            btn.onclick = () => {
                const input = document.getElementById('chat-input') || document.getElementById('messageInput');
                if (input) { input.value += emoji; input.focus(); }
                picker.remove();
            };
            picker.appendChild(btn);
        });
        (document.querySelector('.conversation-input, .chat-input-area') || document.body).appendChild(picker);
        setTimeout(() => {
            document.addEventListener('click', function closePicker(e) {
                if (!picker.contains(e.target) && e.target.id !== 'btn-emoji') {
                    picker.remove();
                    document.removeEventListener('click', closePicker);
                }
            });
        }, 100);
    }

    scrollToBottom() {
        const container = document.getElementById('chat-messages') || document.getElementById('messagesContainer');
        if (container) container.scrollTop = container.scrollHeight;
    }

    connect() {
        if (this.demoMode) return;
        const wsUrl = `ws://${window.location.host}/ws/chat/${this.conversacionId}/${this.userType}/${this.userId}`;
        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = () => console.log('WebSocket conectado');
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'nuevo_mensaje' && data.mensaje) { this.renderizarMensaje(data.mensaje, true); this.scrollToBottom(); }
            };
            this.ws.onclose = () => { console.log('WebSocket desconectado, reintentando...'); setTimeout(() => this.connect(), 3000); };
            this.ws.onerror = (error) => console.error('WebSocket error:', error);
        } catch (e) {
            console.error('Error conectando WebSocket:', e);
        }
    }
}

// Estilos adicionales (typing, loading, file bubble)
const chatStyles = document.createElement('style');
chatStyles.textContent = `
    .typing-dots { display: flex; gap: 4px; padding: 4px 0; }
    .typing-dots span { width: 8px; height: 8px; border-radius: 50%; background: #888; animation: typing-bounce 1.4s infinite ease-in-out both; }
    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
    @keyframes typing-bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
    .chat-loading { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 40px; color: #888; }
    .chat-loading .spinner { width: 24px; height: 24px; border: 2px solid #333; border-top-color: #FFCD11; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .file-bubble .file-info { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
    .file-bubble .file-info i { font-size: 32px; color: #FFCD11; }
    .file-bubble .file-name { font-weight: 500; }
    .file-bubble .file-size { font-size: 12px; color: #888; }
`;
document.head.appendChild(chatStyles);

// Compatibilidad: exponer clase y helper de inicio
window.MitaChat = MitaChat;
window.iniciarChat = function (config) { window.mitaChat = new MitaChat(config); return window.mitaChat; };
