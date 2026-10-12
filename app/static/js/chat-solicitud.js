/**
 * Chat IA para solicitudes MITA (zMita-17).
 * Narra el problema en lenguaje natural -> OpenAI extrae entidades -> confirma -> crea la solicitud.
 */
(function () {
    'use strict';
    const esc = (t) => { const d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; };

    const NOMBRES_AREA = {
        gasfiteria: 'Gasfitería', electricidad: 'Electricidad', cerrajeria: 'Cerrajería',
        linea_blanca: 'Línea Blanca', aire_acondicionado: 'Aire Acondicionado', computacion: 'Computación',
        albanileria_menor: 'Albañilería Menor', instalaciones_hogar: 'Instalaciones en el Hogar'
    };

    const ChatSolicitud = {
        historial: [], turno: 0, MAX_TURNOS: 3, datosExtraidos: null, container: null,

        init(arg) {
            // Acepta un id (string), un elemento, o {container, onComplete, onCancel}
            let opts = {};
            if (typeof arg === 'string') this.container = document.getElementById(arg);
            else if (arg && arg.nodeType === 1) this.container = arg;
            else if (arg && typeof arg === 'object') {
                opts = arg;
                this.container = (typeof opts.container === 'string') ? document.getElementById(opts.container) : opts.container;
            }
            this.onComplete = opts.onComplete || null;
            this.onCancel = opts.onCancel || null;
            if (!this.container) { console.error('[ChatSolicitud] Container no encontrado'); return; }
            this.container.classList.add('chat-solicitud');
            this.turno = 0; this.historial = []; this.datosExtraidos = null;
            this.renderUI();
            this.agregarMensajeBot('¡Hola! Cuéntame qué problema tienes y dónde te encuentras.');
            if (window.MitaVoz) { try { MitaVoz.init(); } catch (e) {} }
        },
        cancelar() { if (this.onCancel) try { this.onCancel(); } catch (e) {} },

        renderUI() {
            this.container.innerHTML = `
                <div class="chat-mensajes" id="chat-mensajes"></div>
                <div class="chat-opciones" id="chat-opciones" style="display:none;"></div>
                <div class="chat-confirmacion" id="chat-confirmacion" style="display:none;"></div>
                <div class="chat-input-container">
                    <div class="voice-buttons">
                        <button type="button" id="btnVozEstandar" class="btn-voice" title="Dictar (Estándar)">
                            <i class="fas fa-microphone"></i><span class="voice-label">Estándar</span>
                        </button>
                        <button type="button" id="btnVozPremium" class="btn-voice premium recommended" title="Dictar (Premium)">
                            <i class="fas fa-microphone-lines"></i><span class="voice-label">Premium</span>
                        </button>
                    </div>
                    <input type="text" id="chat-input" placeholder="Escribe o dicta tu problema...">
                    <button id="chat-enviar" class="btn-enviar" aria-label="Enviar"><i class="fas fa-paper-plane"></i></button>
                </div>`;
            const input = document.getElementById('chat-input');
            input.addEventListener('keypress', (e) => { if (e.key === 'Enter') this.enviar(); });
            document.getElementById('chat-enviar').addEventListener('click', () => this.enviar());
        },

        _avatar() { return '<div class="avatar-bot"><i class="fas fa-robot"></i></div>'; },

        agregarMensajeBot(texto) {
            const m = document.getElementById('chat-mensajes');
            m.insertAdjacentHTML('beforeend', `<div class="mensaje bot">${this._avatar()}<div class="burbuja">${esc(texto)}</div></div>`);
            m.scrollTop = m.scrollHeight;
        },
        agregarMensajeUsuario(texto) {
            const m = document.getElementById('chat-mensajes');
            m.insertAdjacentHTML('beforeend', `<div class="mensaje usuario"><div class="burbuja">${esc(texto)}</div></div>`);
            m.scrollTop = m.scrollHeight;
        },

        async enviar() {
            const input = document.getElementById('chat-input');
            const texto = (input.value || '').trim();
            if (!texto) return;
            input.value = '';
            this.agregarMensajeUsuario(texto);
            this.turno++;
            this.historial.push({ role: 'user', content: texto });
            await this._interpretar(texto);
        },

        async _interpretar(mensaje) {
            this.mostrarEscribiendo();
            try {
                const resp = await fetch('/api/v1/chat-ia/interpretar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mensaje, contexto: this.historial })
                });
                this.ocultarEscribiendo();
                if (resp.status === 503) { this.agregarMensajeBot('El asistente no está disponible por ahora. Usa el menú de servicios.'); this.mostrarFallbackVisual(); return; }
                if (!resp.ok) throw new Error('bad');
                this.procesarRespuesta(await resp.json());
            } catch (e) {
                this.ocultarEscribiendo();
                this.agregarMensajeBot('Hubo un error. ¿Puedes intentar de nuevo?');
            }
        },

        procesarRespuesta(data) {
            this.datosExtraidos = data;
            if (data.direccion && data.direccion.ambigua && data.direccion.opciones && data.direccion.opciones.length) {
                this.mostrarOpciones(data.direccion.opciones); return;
            }
            if (data.completo && data.confirmacion) { this.mostrarConfirmacion(data); return; }
            if (data.siguiente_pregunta) {
                this.agregarMensajeBot(data.siguiente_pregunta);
                this.historial.push({ role: 'assistant', content: data.siguiente_pregunta });
            }
            if (this.turno >= this.MAX_TURNOS && !data.completo) {
                this.agregarMensajeBot('Mejor te muestro las opciones:');
                this.mostrarFallbackVisual();
            }
        },

        mostrarOpciones(opciones) {
            const c = document.getElementById('chat-opciones');
            c.style.display = 'block';
            c.innerHTML = '<p>¿Cuál es tu ubicación?</p>';
            opciones.forEach(op => {
                const b = document.createElement('button');
                b.className = 'btn-opcion'; b.textContent = '📍 ' + op;
                b.addEventListener('click', () => this.seleccionarOpcion(op));
                c.appendChild(b);
            });
        },
        seleccionarOpcion(opcion) {
            document.getElementById('chat-opciones').style.display = 'none';
            this.agregarMensajeUsuario(opcion);
            this.historial.push({ role: 'user', content: opcion });
            this._interpretar('(el usuario eligió: ' + opcion + ')');
        },

        mostrarConfirmacion(data) {
            const dir = data.direccion || {};
            const c = document.getElementById('chat-confirmacion');
            c.style.display = 'block';
            c.innerHTML = `
                <div class="confirmacion-card">
                    <h4>✅ ${esc(data.confirmacion)}</h4>
                    <div class="confirmacion-detalles">
                        <p><strong>Servicio:</strong> ${esc(NOMBRES_AREA[data.area] || data.area || '—')}</p>
                        <p><strong>Problema:</strong> ${esc(data.problema || '—')}</p>
                        <p><strong>Dirección:</strong> ${esc([dir.calle, dir.numero].filter(Boolean).join(' '))}${dir.distrito ? ', ' + esc(dir.distrito) : ''}</p>
                    </div>
                    <div class="confirmacion-acciones">
                        <button class="btn-confirmar" id="chat-confirmar">✓ Confirmar y buscar técnico</button>
                        <button class="btn-corregir" id="chat-corregir">✏️ Corregir</button>
                    </div>
                </div>`;
            document.getElementById('chat-confirmar').addEventListener('click', () => this.confirmarSolicitud());
            document.getElementById('chat-corregir').addEventListener('click', () => this.corregir());
        },

        async confirmarSolicitud() {
            const data = this.datosExtraidos || {};
            const dir = data.direccion || {};
            const btn = document.getElementById('chat-confirmar'); if (btn) btn.disabled = true;
            const direccionCompleta = [dir.calle, dir.numero].filter(Boolean).join(' ') + (dir.distrito ? ', ' + dir.distrito : '');
            let geo = null;
            try { geo = await (await fetch('/api/v1/chat-ia/validar-direccion', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direccion: direccionCompleta }) })).json();
            } catch (e) { /* sigue con lo extraído */ }
            if (geo && geo.valida === false) { if (btn) btn.disabled = false; this.agregarMensajeBot('No pude validar la dirección. ¿Puedes verificarla?'); return; }

            if (!data.categoria_id) {
                this.agregarMensajeBot('Para este servicio, elige la categoría en el menú. Te llevo allí.');
                this.mostrarFallbackVisual(); return;
            }
            // Crear la solicitud con lo extraído + geocodificación
            try {
                const payload = {
                    problema: `[${NOMBRES_AREA[data.area] || data.area}] ${data.problema || ''}`.trim(),
                    categoria_id: data.categoria_id,
                    direccion: (geo && geo.direccion_formateada) || direccionCompleta,
                    distrito: (geo && geo.distrito) || dir.distrito || null,
                    referencia: dir.referencia || null,
                    lat: geo ? geo.lat : null, lng: geo ? geo.lng : null
                };
                const r = await fetch('/api/v1/solicitudes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await r.json();
                if (r.ok && d.id) {
                    if (d.id) fetch(`/api/v1/asignacion/iniciar/${d.id}`, { method: 'POST' }).catch(() => {});
                    if (this.onComplete) { try { this.onComplete({ id: d.id, ...data }); } catch (e) {} }
                    window.location.href = `/cliente/servicio/${d.id}/chats`;
                } else { if (btn) btn.disabled = false; this.agregarMensajeBot('No se pudo crear la solicitud. Intenta por el menú.'); }
            } catch (e) { if (btn) btn.disabled = false; this.agregarMensajeBot('Error al crear la solicitud.'); }
        },

        corregir() {
            document.getElementById('chat-confirmacion').style.display = 'none';
            this.agregarMensajeBot('¿Qué quieres corregir? Escríbelo y lo ajusto.');
        },

        mostrarFallbackVisual() { setTimeout(() => { window.location.href = '/#servicios'; }, 1600); },

        mostrarEscribiendo() {
            const m = document.getElementById('chat-mensajes');
            m.insertAdjacentHTML('beforeend', `<div class="mensaje bot escribiendo" id="escribiendo">${this._avatar()}<div class="burbuja"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div></div>`);
            m.scrollTop = m.scrollHeight;
        },
        ocultarEscribiendo() { const e = document.getElementById('escribiendo'); if (e) e.remove(); }
    };

    window.ChatSolicitud = ChatSolicitud;
})();
