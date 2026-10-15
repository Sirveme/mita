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
            if (window.MitaVoz) { try { MitaVoz.init(); MitaVoz.onAutoEnviar(() => this.enviar()); } catch (e) {} }
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
                        <button type="button" id="btnTts" class="btn-voice" title="Que el asistente hable" aria-label="Activar o silenciar la voz del asistente">
                            <i class="fas fa-volume-high"></i>
                        </button>
                    </div>
                    <input type="text" id="chat-input" placeholder="Escribe o dicta tu problema...">
                    <button id="chat-enviar" class="btn-enviar" aria-label="Enviar"><i class="fas fa-paper-plane"></i></button>
                </div>`;
            const input = document.getElementById('chat-input');
            input.addEventListener('keypress', (e) => { if (e.key === 'Enter') this.enviar(); });
            document.getElementById('chat-enviar').addEventListener('click', () => this.enviar());
            // Toggle de voz del asistente (recordado)
            try { this.tts = localStorage.getItem('mita_tts') !== 'off'; } catch (e) { this.tts = true; }
            this._pintarTts();
            const bt = document.getElementById('btnTts');
            if (bt) bt.addEventListener('click', () => {
                this.tts = !this.tts;
                try { localStorage.setItem('mita_tts', this.tts ? 'on' : 'off'); } catch (e) {}
                if (!this.tts && window.MitaVoz) MitaVoz.detenerVoz();
                this._pintarTts();
            });
        },
        _pintarTts() {
            const bt = document.getElementById('btnTts'); if (!bt) return;
            bt.innerHTML = `<i class="fas ${this.tts ? 'fa-volume-high' : 'fa-volume-xmark'}"></i>`;
            bt.classList.toggle('premium', !!this.tts);
        },
        _debeHablar() {
            // "si me hablas, te hablo": si usó el micrófono en este turno, habla aunque esté en mute
            let usoMic = false;
            try { usoMic = window.MitaVoz && (Date.now() - MitaVoz.ultimoDictado() < 30000); } catch (e) {}
            return !!(this.tts || usoMic);
        },
        _hablar(texto, reabrir) {
            if (!texto || !window.MitaVoz || !this._debeHablar()) return;
            const m = document.getElementById('chat-mensajes');
            const ult = m ? m.querySelector('.mensaje.bot:last-of-type') : null;
            const puedeReabrir = !!(reabrir && this._entradaVoz && !this.cerrado);
            MitaVoz.hablar(texto, {
                onPlay: () => { if (ult) ult.classList.add('hablando'); },
                onEnded: () => {
                    if (ult) ult.classList.remove('hablando');
                    // Modo conversación: reabrir el micrófono si el turno vino por voz
                    if (puedeReabrir) { try { MitaVoz.reabrir(); } catch (e) {} }
                },
                onBlocked: () => { if (ult) ult.classList.remove('hablando'); this.agregarMensajeBot('Toca 🔊 para escucharme.'); },
                onEstandar: () => { if (ult && !ult.querySelector('.voz-std')) ult.insertAdjacentHTML('beforeend', '<span class="voz-std" title="Voz estándar del navegador"> · voz estándar</span>'); }
            });
        },
        _fmtFecha(iso) {
            if (!iso) return '';
            try {
                const d = new Date(iso);
                return d.toLocaleString('es-PE', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
            } catch (e) { return iso; }
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
            // ¿Este turno vino por voz? (para "si me hablas, te hablo" y modo conversación)
            try { this._entradaVoz = !!(window.MitaVoz && (Date.now() - MitaVoz.ultimoDictado() < 30000)); } catch (e) { this._entradaVoz = false; }
            input.value = '';
            this.agregarMensajeUsuario(texto);
            this.turno++;
            this.historial.push({ role: 'user', content: texto });
            await this._interpretar(texto);
        },

        async _interpretar(mensaje) {
            this.mostrarEscribiendo();
            const req = { mensaje, contexto: this.historial, estado: this.estado || {} };
            this._ultimoReq = req;
            const ctrl = new AbortController();
            const tmo = setTimeout(() => ctrl.abort(), 20000);   // timeout 20 s
            try {
                const resp = await fetch('/api/v1/chat-ia/interpretar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(req), signal: ctrl.signal
                });
                if (!resp.ok && resp.status !== 200) {
                    const t = await resp.text().catch(() => '');
                    this._logCliente('interpretar HTTP ' + resp.status, t);
                    this.agregarMensajeBot('Tuve un problema, ¿me lo repites?');
                    return;
                }
                const data = await resp.json();
                this._ultimoResp = data; this._pintarDebug();
                // Error controlado del backend (nunca silencio)
                if (data && data.mensaje) {
                    this.agregarMensajeBot(data.mensaje); this._hablar(data.mensaje);
                    if (data.estado) this.estado = data.estado;
                    if (data.sin_ia) this.mostrarFallback();
                    return;
                }
                this.procesarRespuesta(data);
            } catch (e) {
                const abort = e && e.name === 'AbortError';
                this._logCliente('interpretar ' + (abort ? 'timeout' : 'fetch error'), (e && e.stack) || String(e));
                this.agregarMensajeBot(abort ? 'Me tomó demasiado responder, ¿me lo repites?' : 'Tuve un problema, ¿me lo repites?');
            } finally {
                clearTimeout(tmo);
                this.ocultarEscribiendo();   // el "escribiendo…" SIEMPRE se quita
            }
        },

        _logCliente(mensaje, stack) {
            try {
                fetch('/api/v1/chat-ia/log-cliente', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mensaje, stack, ultimo_request: this._ultimoReq || {} })
                }).catch(() => {});
            } catch (e) {}
        },

        _pintarDebug() {
            try {
                if (!/[?&]debug=1/.test(location.search)) return;
                let p = document.getElementById('chat-debug');
                if (!p) {
                    p = document.createElement('details'); p.id = 'chat-debug';
                    p.style.cssText = 'margin:8px 4px;font-size:11px;color:#8a8a9a;';
                    p.innerHTML = '<summary>debug</summary><pre style="white-space:pre-wrap;max-height:200px;overflow:auto;"></pre>';
                    this.container.appendChild(p);
                }
                p.querySelector('pre').textContent = JSON.stringify({ req: this._ultimoReq, resp: this._ultimoResp, estado: this.estado }, null, 2);
            } catch (e) {}
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
                this._hablar(data.respuesta_consulta, true);
            }

            // B.2 Fuera de cobertura: registrar y cerrar
            if (data.fuera_cobertura) { this.mostrarFueraCobertura(data); return; }

            // C) Agenda: ofrecer horarios concretos
            if (Array.isArray(data.horarios) && data.horarios.length) {
                if (data.siguiente_pregunta) { this.agregarMensajeBot(data.siguiente_pregunta); this._hablar(data.siguiente_pregunta, true); }
                if (data.asap) this.mostrarAsap(data.horarios[0]);
                else this.mostrarHorarios(data.horarios);
                return;
            }

            // Dirección ambigua -> opciones (solo si hay opciones reales)
            if (data.direccion && data.direccion.ambigua && Array.isArray(data.direccion.opciones) && data.direccion.opciones.length) {
                this.mostrarOpciones(data.direccion.opciones); return;
            }

            // Completo -> confirmación
            if (data.completo && data.confirmacion) {
                this.mostrarConfirmacion(data);
                this._hablar('Te dejo el resumen en pantalla, ¿lo confirmas?');
                return;
            }

            // Siguiente pregunta
            if (data.siguiente_pregunta) {
                this.agregarMensajeBot(data.siguiente_pregunta);
                this.historial.push({ role: 'assistant', content: data.siguiente_pregunta });
                this._hablar(data.siguiente_pregunta, true);
            } else {
                // Nada renderizable: nunca dejar al usuario sin respuesta
                this.agregarMensajeBot('Tuve un problema, ¿me lo repites?');
                this._logCliente('respuesta sin texto renderizable', JSON.stringify(data).slice(0, 400));
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

        mostrarHorarios(horarios) {
            const c = document.getElementById('chat-opciones');
            c.style.display = 'block';
            c.innerHTML = '<p>Horarios disponibles:</p>';
            horarios.forEach(h => {
                const b = document.createElement('button');
                b.className = 'btn-opcion'; b.type = 'button'; b.textContent = '🕐 ' + h.etiqueta;
                b.addEventListener('click', () => this.elegirHorario(h));
                c.appendChild(b);
            });
        },
        elegirHorario(h) {
            document.getElementById('chat-opciones').style.display = 'none';
            this.estado = this.estado || {}; this.estado.horario_elegido = h.iso;
            this.agregarMensajeUsuario(h.etiqueta);
            this.historial.push({ role: 'user', content: 'Quiero el horario: ' + h.etiqueta });
            this._interpretar('Confirmo ese horario');
        },

        // C) Oferta ASAP: el primer horario disponible + "¿Te lo reservo?"
        mostrarAsap(h) {
            const c = document.getElementById('chat-opciones');
            if (!c || !h) return;
            c.style.display = 'block'; c.innerHTML = '';
            const si = document.createElement('button');
            si.className = 'btn-opcion'; si.type = 'button'; si.textContent = '✓ Sí, resérvalo';
            si.addEventListener('click', () => this.elegirHorario(h));
            const otros = document.createElement('button');
            otros.className = 'btn-opcion'; otros.type = 'button'; otros.textContent = '🕐 Ver otros horarios';
            otros.addEventListener('click', () => {
                c.style.display = 'none';
                this.agregarMensajeUsuario('Ver otros horarios');
                this.historial.push({ role: 'user', content: 'Prefiero ver otros horarios' });
                this._interpretar('Prefiero ver otros horarios');
            });
            c.appendChild(si); c.appendChild(otros);
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
                    <h4>📋 Revisa los datos de tu solicitud</h4>
                    <div class="confirmacion-detalles">
                        <p><strong>Servicio:</strong> ${esc(servicio)}</p>
                        <p><strong>Problema:</strong> ${esc(data.problema || '—')}</p>
                        <p><strong>Dirección:</strong> ${esc(dirLinea || '—')}</p>
                        ${dir.distrito ? `<p><strong>Distrito:</strong> ${esc(dir.distrito)}</p>` : ''}
                        ${(data.fecha_programada || (this.estado && this.estado.horario_elegido)) ? `<p><strong>Fecha y hora:</strong> ${esc(this._fmtFecha(data.fecha_programada || this.estado.horario_elegido))}</p>` : ''}
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
                    lat: geo ? geo.lat : null, lng: geo ? geo.lng : null,
                    fecha_programada: (this.estado && this.estado.horario_elegido) || data.fecha_programada || null
                };
                const r = await fetch('/api/v1/solicitudes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await r.json();
                if (r.ok && d.id) {
                    if (d.id) fetch(`/api/v1/asignacion/iniciar/${d.id}`, { method: 'POST' }).catch(() => {});
                    // Parte E: mensaje de registro (no "cita confirmada")
                    const f = this._fmtFecha((this.estado && this.estado.horario_elegido) || data.fecha_programada);
                    const listo = f
                        ? `¡Listo! Tu solicitud quedó registrada para el ${f}. Te avisaremos cuando el técnico esté en camino.`
                        : '¡Listo! Tu solicitud quedó registrada. Te avisaremos cuando el técnico esté en camino.';
                    this.agregarMensajeBot(listo); this._hablar(listo);
                    if (this.onComplete) { try { this.onComplete({ id: d.id, ...data }); } catch (e) {} }
                    this._ofrecerAvisos(d.id);   // zMita-33: ofrecer avisos destacado tras confirmar
                } else { if (btn) btn.disabled = false; this.agregarMensajeBot('No se pudo crear la solicitud. Intenta por el menú.'); }
            } catch (e) { if (btn) btn.disabled = false; this.agregarMensajeBot('Error al crear la solicitud.'); }
        },

        corregir() {
            document.getElementById('chat-confirmacion').style.display = 'none';
            this.agregarMensajeBot('¿Qué quieres corregir? Escríbelo y lo ajusto.');
        },

        // zMita-33: tras confirmar, ofrecer avisos de forma destacada y luego ir al servicio.
        _ofrecerAvisos(solicitudId) {
            const ir = () => { window.location.href = `/cliente/servicio/${solicitudId}/chats`; };
            const c = document.getElementById('chat-opciones');
            if (!c || !window.MitaPWA) { setTimeout(ir, 1600); return; }
            c.style.display = 'block'; c.innerHTML = '';
            const avisar = document.createElement('button');
            avisar.className = 'btn-opcion'; avisar.type = 'button';
            avisar.textContent = '🔔 Activar avisos (saber cuándo llega tu técnico)';
            avisar.addEventListener('click', async () => {
                avisar.disabled = true;
                try {
                    const res = await window.MitaPWA.activarAvisos({ solicitud_id: solicitudId, rol: 'cliente' });
                    if (res.ok) this.agregarMensajeBot('Listo, te avisaremos aquí y en tu teléfono.');
                    else if (res.motivo === 'ios-requiere-instalar') this.agregarMensajeBot('En iPhone, primero agrega MITA a tu inicio y ábrela desde el ícono para activar los avisos.');
                    else this.agregarMensajeBot('Puedes activar los avisos más tarde desde /prueba-avisos.');
                } catch (e) {}
                ir();
            });
            const ver = document.createElement('button');
            ver.className = 'btn-opcion'; ver.type = 'button'; ver.textContent = 'Ver mi servicio';
            ver.addEventListener('click', ir);
            c.appendChild(avisar); c.appendChild(ver);
        },

        async mostrarFueraCobertura(data) {
            // B.2: NO cerramos el chat — el usuario puede corregir la dirección.
            const dir = data.direccion || {};
            const est = data.estado || this.estado || {};
            const distrito = dir.distrito || est.localidad_mencionada || (est.direccion || {}).distrito || '';
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
            const zona = (distrito || 'tu zona').trim();
            const msgFuera = `Por ahora no tenemos cobertura en ${zona}. Registramos tu solicitud y te avisaremos cuando ampliemos la cobertura a tu zona.`;
            this.agregarMensajeBot(msgFuera); this._hablar(msgFuera);
            const c = document.getElementById('chat-opciones');
            if (c) {
                c.style.display = 'block'; c.innerHTML = '';
                const corregir = document.createElement('button');
                corregir.className = 'btn-opcion'; corregir.type = 'button'; corregir.textContent = '✏️ Corregir mi dirección';
                corregir.addEventListener('click', () => {
                    c.style.display = 'none';
                    this.agregarMensajeBot('Dime la dirección correcta (calle, número y distrito).');
                    const input = document.getElementById('chat-input');
                    if (input) input.focus();
                });
                const ok = document.createElement('button');
                ok.className = 'btn-opcion'; ok.type = 'button'; ok.textContent = 'Entendido';
                ok.addEventListener('click', () => { c.style.display = 'none'; this.cerrado = true; this.cancelar(); });
                c.appendChild(corregir); c.appendChild(ok);
            }
        },

        mostrarFallback() {
            if (this.cerrado) return;
            this.cerrado = true;
            const msgFb = 'Para no hacerte perder tiempo, sigamos con el formulario — ya llevo lo que me contaste.';
            this.agregarMensajeBot(msgFb); this._hablar(msgFb);
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
                    referencia: dir.referencia || null,
                    fecha_programada: (this.estado && this.estado.horario_elegido) || null
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
