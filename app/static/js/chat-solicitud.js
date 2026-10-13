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
        historial: [], turno: 0, MAX_SIN_PROGRESO: 3, sinProgreso: 0, ultimaFirma: '',
        cerrado: false, datosExtraidos: null, container: null,

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
            this.sinProgreso = 0; this.ultimaFirma = ''; this.cerrado = false; this.estado = {};
            this.renderUI();
            this.agregarMensajeBot('¡Hola! Cuéntame qué problema tienes y dónde te encuentras.');
            this.mostrarSugerencias(['Tengo una fuga de agua', 'Mi refri no enfría', 'Necesito un electricista']);
            if (window.MitaVoz) { try { MitaVoz.init(); } catch (e) {} }
        },
        cancelar() { if (this.onCancel) try { this.onCancel(); } catch (e) {} },

        mostrarSugerencias(lista) {
            const m = document.getElementById('chat-mensajes');
            if (!m) return;
            const cont = document.createElement('div');
            cont.className = 'chat-sugerencias';
            lista.forEach(txt => {
                const b = document.createElement('button');
                b.className = 'chat-sugerencia'; b.type = 'button'; b.textContent = txt;
                b.addEventListener('click', () => {
                    cont.remove();
                    const input = document.getElementById('chat-input');
                    if (input) input.value = txt;
                    this.enviar();
                });
                cont.appendChild(b);
            });
            m.appendChild(cont);
            m.scrollTop = m.scrollHeight;
        },

        renderUI() {
            this.container.innerHTML = `
                <div class="chat-mensajes" id="chat-mensajes"></div>
                <div class="chat-opciones" id="chat-opciones" style="display:none;"></div>
                <div class="chat-confirmacion" id="chat-confirmacion" style="display:none;"></div>
                <div class="chat-input-container">
                    <div class="voice-buttons">
                        <button type="button" id="btnVozEstandar" class="btn-voice" title="Dictar (Estándar)" aria-label="Dictar en modo Estándar">
                            <i class="fas fa-microphone"></i>
                        </button>
                        <button type="button" id="btnVozPremium" class="btn-voice premium recommended" title="Dictar (Premium)" aria-label="Dictar en modo Premium">
                            <i class="fas fa-microphone-lines"></i>
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
            if (this.cerrado) return;
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
                    body: JSON.stringify({ mensaje, contexto: this.historial, estado: this.estado || {} })
                });
                this.ocultarEscribiendo();
                if (resp.status === 503) { this.agregarMensajeBot('El asistente no está disponible por ahora. Usa el menú de servicios.'); this.mostrarFallback(); return; }
                if (!resp.ok) throw new Error('bad');
                this.procesarRespuesta(await resp.json());
            } catch (e) {
                this.ocultarEscribiendo();
                this.agregarMensajeBot('Hubo un error. ¿Puedes intentar de nuevo?');
            }
        },

        _firma(data) {
            const d = data.direccion || {};
            return JSON.stringify([data.area || '', data.problema || '', d.calle || '', d.numero || '', d.distrito || '']);
        },

        procesarRespuesta(data) {
            this.datosExtraidos = data;
            if (data.estado) this.estado = data.estado;   // memoria: guardar estado fusionado

            // Progreso: ¿la IA extrajo algún dato nuevo respecto al turno anterior?
            const firma = this._firma(data);
            const huboProgreso = firma !== this.ultimaFirma && firma !== '["","","","",""]';
            const esConsulta = (data.intencion === 'consulta');
            if (huboProgreso) { this.sinProgreso = 0; this.ultimaFirma = firma; }
            else if (!esConsulta) { this.sinProgreso++; }   // consultas no cuentan para el fallback

            // Responder primero la consulta (precio/horario/garantía…)
            if (data.respuesta_consulta) {
                this.agregarMensajeBot(data.respuesta_consulta);
                this.historial.push({ role: 'assistant', content: data.respuesta_consulta });
            }

            // B.2 Fuera de cobertura: registrar y cerrar
            if (data.fuera_cobertura) { this.mostrarFueraCobertura(data); return; }

            // Dirección ambigua -> opciones (solo si hay opciones reales)
            if (data.direccion && data.direccion.ambigua && Array.isArray(data.direccion.opciones) && data.direccion.opciones.length) {
                this.mostrarOpciones(data.direccion.opciones); return;
            }

            // Completo -> confirmación
            if (data.completo && data.confirmacion) { this.mostrarConfirmacion(data); return; }

            // Siguiente pregunta
            if (data.siguiente_pregunta) {
                this.agregarMensajeBot(data.siguiente_pregunta);
                this.historial.push({ role: 'assistant', content: data.siguiente_pregunta });
            }

            // Fallback solo tras 3 turnos SEGUIDOS sin progreso
            if (this.sinProgreso >= this.MAX_SIN_PROGRESO && !data.completo) {
                this.mostrarFallback();
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

        _precioHtml(pv) {
            if (!pv || typeof pv.precio !== 'number') return '';
            if (pv.es_promo) {
                return `<p><strong>Visita y diagnóstico:</strong> <span style="text-decoration:line-through;color:#8a8a9a">S/ ${pv.regular.toFixed(2)}</span> <b style="color:#22c55e">S/ ${pv.precio.toFixed(2)}</b>${pv.hasta ? ' (promo hasta ' + esc(pv.hasta) + ')' : ''}</p>`;
            }
            return `<p><strong>Visita y diagnóstico:</strong> S/ ${pv.precio.toFixed(2)}</p>`;
        },
        mostrarConfirmacion(data) {
            const dir = data.direccion || {};
            const servicio = data.categoria_nombre || NOMBRES_AREA[data.area] || data.area || 'Servicio';
            const dirLinea = dir.direccion_formateada || [dir.calle, dir.numero].filter(Boolean).join(' ');
            const urg = data.urgencia === 'alta' ? 'urgente' : (data.urgencia === 'normal' ? 'normal' : '');
            const c = document.getElementById('chat-confirmacion');
            c.style.display = 'block';
            c.innerHTML = `
                <div class="confirmacion-card">
                    <h4>✅ ${esc(data.confirmacion || 'Confirmemos tu solicitud')}</h4>
                    <div class="confirmacion-detalles">
                        <p><strong>Servicio:</strong> ${esc(servicio)}</p>
                        <p><strong>Problema:</strong> ${esc(data.problema || '—')}</p>
                        <p><strong>Dirección:</strong> ${esc(dirLinea || '—')}</p>
                        ${dir.distrito ? `<p><strong>Distrito:</strong> ${esc(dir.distrito)}</p>` : ''}
                        ${this._precioHtml(data.precio_visita)}
                        ${urg ? `<p><strong>Prioridad:</strong> ${urg}</p>` : ''}
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
            if (dir.validada && dir.lat && dir.lng) {
                // Ya validada por el backend: no re-geocodificar
                geo = { valida: true, lat: dir.lat, lng: dir.lng, distrito: dir.distrito, direccion_formateada: dir.direccion_formateada || direccionCompleta };
            } else {
                try { geo = await (await fetch('/api/v1/chat-ia/validar-direccion', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ direccion: direccionCompleta }) })).json();
                } catch (e) { /* sigue con lo extraído */ }
            }
            if (geo && geo.valida === false) { if (btn) btn.disabled = false; this.agregarMensajeBot('No pude validar la dirección. ¿Puedes verificarla?'); return; }

            if (!data.categoria_id) {
                this.agregarMensajeBot('Para este servicio, elige la categoría en el menú. Te llevo allí.');
                this.mostrarFallback(); return;
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

        async mostrarFueraCobertura(data) {
            if (this.cerrado) return;
            this.cerrado = true;
            const dir = data.direccion || {};
            const distrito = dir.distrito || '';
            try {
                await fetch('/api/v1/maps/sin-cobertura', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        distrito_solicitado: distrito || 'Desconocido',
                        direccion_ingresada: dir.texto_original || null,
                        area_servicio_id: data.categoria_id || null,
                        descripcion: data.problema || null
                    })
                });
            } catch (e) {}
            this.agregarMensajeBot('Por ahora atendemos solo en Lima Moderna. Ya registramos tu zona para avisarte apenas lleguemos.');
            const c = document.getElementById('chat-opciones');
            if (c) {
                c.style.display = 'block'; c.innerHTML = '';
                const b = document.createElement('button');
                b.className = 'btn-opcion'; b.type = 'button'; b.textContent = 'Entendido';
                b.addEventListener('click', () => { c.style.display = 'none'; this.cancelar(); });
                c.appendChild(b);
            }
        },

        mostrarFallback() {
            if (this.cerrado) return;
            this.cerrado = true;
            this.agregarMensajeBot('Para no hacerte perder tiempo, sigamos con el formulario — ya llevo lo que me contaste.');
            const c = document.getElementById('chat-opciones');
            if (c) {
                c.style.display = 'block'; c.innerHTML = '';
                const b = document.createElement('button');
                b.className = 'btn-opcion'; b.type = 'button'; b.textContent = '📝 Continuar con el formulario';
                b.addEventListener('click', () => this._irAlFormulario());
                c.appendChild(b);
            }
        },

        _irAlFormulario() {
            const data = this.datosExtraidos || {};
            const dir = data.direccion || {};
            try {
                sessionStorage.setItem('mita_chat_prefill', JSON.stringify({
                    categoria_id: data.categoria_id || null, area: data.area || null, problema: data.problema || null,
                    direccion: [dir.calle, dir.numero].filter(Boolean).join(' '), distrito: dir.distrito || null,
                    referencia: dir.referencia || null
                }));
            } catch (e) {}
            window.location.href = '/#servicios';
        },

        mostrarEscribiendo() {
            const m = document.getElementById('chat-mensajes');
            m.insertAdjacentHTML('beforeend', `<div class="mensaje bot escribiendo" id="escribiendo">${this._avatar()}<div class="burbuja"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div></div>`);
            m.scrollTop = m.scrollHeight;
        },
        ocultarEscribiendo() { const e = document.getElementById('escribiendo'); if (e) e.remove(); }
    };

    window.ChatSolicitud = ChatSolicitud;
})();
