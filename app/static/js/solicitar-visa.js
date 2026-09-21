/* ============================================================
   Solicitar servicio — flujo estilo VISA (home del cliente)
   Niveles 1-4 + pasos Dirección > Pago > (IziPay) > Confirmación
   ============================================================ */
(function () {
    'use strict';

    const TIPOS = {
        urgencia:    { label: 'Urgencia / Emergencia',      icon: 'fa-triangle-exclamation', c1: '#ef4444', c2: '#b91c1c', desc: 'Atención inmediata para situaciones de riesgo.' },
        reparacion:  { label: 'Reparación / Mantenimiento', icon: 'fa-screwdriver-wrench',   c1: '#f59e0b', c2: '#d97706', desc: 'Arreglos y mantenimiento de lo que ya tienes.' },
        instalacion: { label: 'Instalación',                icon: 'fa-plus',                 c1: '#10b981', c2: '#059669', desc: 'Instalación de equipos y accesorios nuevos.' },
    };
    const ORDEN_TIPOS = ['urgencia', 'reparacion', 'instalacion'];

    let AREAS = [], DISTRITOS = [];
    const CFG = { permitir_efectivo: true, momento_cobro: 'cliente_elige', tarifa_visita: 50, mensaje_distrito: 'Distrito fuera de alcance' };
    const estado = { area: null, tipoKey: null, problema: null, descripcion: '', foto: null,
                     direccion: '', distrito: '', referencia: '', telefono: '', metodo: 'efectivo',
                     solicitudId: null, pagoRef: null };

    const $ = (s) => document.querySelector(s);
    const esc = (t) => { const d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
    const grad = (a, b) => `linear-gradient(135deg, ${a}, ${b})`;
    const bt = (v) => v === true || v === 'true';
    const money = (v) => 'S/ ' + Number(v).toFixed(2);
    const areaImg = (a) => a.imagen_url || null;                       // foto real del área
    const imgReal = (url) => url ? `<img src="${url}" loading="lazy" onerror="this.remove()" alt="">` : '';

    // -------- Sonido --------
    let audioCtx = null;
    function silenciado() {
        try { if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return true; } catch (e) {}
        try { return localStorage.getItem('mita_sound') === 'off'; } catch (e) { return false; }
    }
    function pop() {
        if (silenciado()) return;
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const o = audioCtx.createOscillator(), g = audioCtx.createGain(), t = audioCtx.currentTime;
            o.type = 'sine'; o.frequency.value = 800;
            g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.06, t + 0.012);
            g.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
            o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(t + 0.16);
        } catch (e) {}
    }
    function pintarMute() { const b = $('#v-mute'); if (b) b.innerHTML = `<i class="fas ${silenciado() ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>`; }
    function toggleMute() { try { localStorage.setItem('mita_sound', silenciado() ? 'on' : 'off'); } catch (e) {} pintarMute(); if (!silenciado()) pop(); }

    // -------- Carga --------
    async function cargarAreas() {
        try { const r = await fetch('/api/v1/areas-servicio'); if (r.ok) { const d = await r.json(); if (Array.isArray(d) && d.length) { AREAS = d; return; } } throw 0; }
        catch (e) { AREAS = window.AREAS_DATA || []; }
    }
    async function cargarConfig() {
        try {
            const c = await (await fetch('/api/v1/admin/config-mita')).json();
            if (c && typeof c === 'object') {
                if ('permitir_pago_efectivo' in c) CFG.permitir_efectivo = bt(c.permitir_pago_efectivo);
                if (c.momento_cobro) CFG.momento_cobro = c.momento_cobro;
                if (c.tarifa_visita_default) CFG.tarifa_visita = parseFloat(c.tarifa_visita_default) || 50;
                if (c.mensaje_distrito_fuera_alcance) CFG.mensaje_distrito = c.mensaje_distrito_fuera_alcance;
            }
        } catch (e) {}
    }
    async function cargarDistritos() {
        try { const d = (await (await fetch('/api/v1/admin/distritos')).json()).items || []; if (d.length) DISTRITOS = d; else throw 0; }
        catch (e) { DISTRITOS = ['Miraflores','San Isidro','Santiago de Surco','La Molina','San Borja','Barranco','Magdalena','Jesús María'].map(n => ({ nombre: n, habilitado: true })); }
        $('#v-distrito').innerHTML = '<option value="">Selecciona tu distrito</option>' + DISTRITOS.map(x => `<option value="${esc(x.nombre)}">${esc(x.nombre)}</option>`).join('');
    }

    // -------- NIVEL 1: chips --------
    function renderChips() {
        $('#v-chips').innerHTML = AREAS.map(a => `
            <div class="v-chip" data-cod="${a.codigo}" role="button" tabindex="0">
                <div class="thumb" style="background:${grad(a.color1, a.color2)}"><i class="fas ${a.icono}"></i>${imgReal(areaImg(a))}</div>
                <div class="name">${esc(a.nombre)}</div>
            </div>`).join('');
        $('#v-chips').querySelectorAll('.v-chip').forEach(el => {
            el.addEventListener('click', () => seleccionarArea(el.dataset.cod));
            el.addEventListener('keydown', (e) => { if (e.key === 'Enter') seleccionarArea(el.dataset.cod); });
        });
    }
    function seleccionarArea(cod) {
        const area = AREAS.find(a => a.codigo === cod); if (!area) return;
        estado.area = area; estado.tipoKey = null; estado.problema = null;
        try { localStorage.setItem('mita_ultima_area', cod); } catch (e) {}
        document.body.classList.add('selected-mode');
        $('#v-chips').querySelectorAll('.v-chip').forEach(el => el.classList.toggle('selected', el.dataset.cod === cod));
        renderTipos(area); ocultar('#nivel3'); pop(); mostrar('#nivel2');
        setTimeout(() => $('#nivel2').scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
    }

    // -------- NIVEL 2: tipos --------
    function renderTipos(area) {
        $('#nivel2-titulo').textContent = area.nombre;
        const areaFoto = areaImg(area);
        $('#v-tipos').innerHTML = ORDEN_TIPOS.map(k => {
            const t = TIPOS[k], n = (area.problemas || []).filter(p => p.tipo === k).length;
            return `<div class="v-tipo-card" data-tipo="${k}" role="button" tabindex="0">
                <div class="v-tipo-img" style="background:${grad(t.c1, t.c2)}"><i class="fas ${t.icon}"></i>${imgReal(areaFoto)}</div>
                <div class="v-tipo-body"><div class="t">${t.label}</div><div class="d">${t.desc}</div>
                    <div class="arrow">${n} opciones <i class="fas fa-chevron-right"></i></div></div>
            </div>`;
        }).join('');
        $('#v-tipos').querySelectorAll('.v-tipo-card').forEach(el => {
            el.addEventListener('click', () => seleccionarTipo(el.dataset.tipo));
            el.addEventListener('keydown', (e) => { if (e.key === 'Enter') seleccionarTipo(el.dataset.tipo); });
        });
    }
    function seleccionarTipo(k) {
        estado.tipoKey = k; estado.problema = null;
        $('#v-tipos').querySelectorAll('.v-tipo-card').forEach(el => el.classList.toggle('selected', el.dataset.tipo === k));
        renderProblemas(estado.area, k); pop(); mostrar('#nivel3');
        setTimeout(() => $('#nivel3').scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
    }

    // -------- NIVEL 3: problemas --------
    function renderProblemas(area, k) {
        const t = TIPOS[k], areaFoto = areaImg(area);
        $('#nivel3-titulo').innerHTML = `${esc(area.nombre)} · <span style="color:${t.c1}">${t.label}</span>`;
        const lista = (area.problemas || []).filter(p => p.tipo === k);
        $('#v-problemas').innerHTML = lista.map(p => `
            <div class="v-prob-card" data-id="${p.id}" role="button" tabindex="0">
                <div class="v-prob-thumb" style="background:${grad(area.color1, area.color2)}"><i class="fas ${area.icono}"></i>${imgReal(areaFoto)}</div>
                <div class="v-prob-name">${esc(p.nombre)}<span class="v-prob-sub">${t.label}</span></div>
                <i class="fas fa-chevron-right chev"></i>
            </div>`).join('');
        $('#v-problemas').querySelectorAll('.v-prob-card').forEach(el => {
            const p = lista.find(x => String(x.id) === el.dataset.id);
            el.addEventListener('click', () => abrirModal(p));
            el.addEventListener('keydown', (e) => { if (e.key === 'Enter') abrirModal(p); });
        });
    }

    // -------- Modal multi-pantalla --------
    function screen(id) { document.querySelectorAll('.v-screen').forEach(s => s.classList.toggle('active', s.id === id)); const b = $('.v-modal-box'); if (b) b.scrollTop = 0; }
    function abrirModal(problema) {
        estado.problema = problema; estado.descripcion = ''; estado.foto = null;
        const area = estado.area;
        $('#v-hero').style.background = grad(area.color1, area.color2);
        $('#v-hero').innerHTML = `<i class="fas ${area.icono}"></i>` + imgReal(areaImg(area));
        $('#v-breadcrumb').innerHTML = `<b>${esc(area.nombre)}</b> › ${esc(TIPOS[estado.tipoKey].label)}`;
        $('#v-modal-title').textContent = problema.nombre;
        $('#v-desc').value = '';
        const pb = $('#v-photo'); pb.classList.remove('has'); pb.querySelector('span').textContent = 'Agregar foto (opcional)';
        screen('screen-detalle'); pop(); $('#v-modal').classList.add('open');
    }
    function cerrarModal() { $('#v-modal').classList.remove('open'); }

    function isLogged() { try { return !!localStorage.getItem('mita_cliente'); } catch (e) { return false; } }
    function irADireccion() {
        estado.descripcion = ($('#v-desc').value || '').trim();
        // Visitante no identificado -> login rápido antes de la dirección
        if (isLogged()) screen('screen-direccion'); else screen('screen-login');
    }
    function continuarWhatsapp() {
        const cel = ($('#v-celular').value || '').replace(/\D/g, '');
        if (cel.length < 9) { $('#v-celular').focus(); return; }
        try { localStorage.setItem('mita_cliente', cel); } catch (e) {}
        estado.telefono = cel;
        const tel = $('#v-telefono'); if (tel && !tel.value) tel.value = cel;
        // (En producción: aquí iría la verificación por SMS/WhatsApp)
        screen('screen-direccion');
    }

    function mostrarWaitlist(v) { $('#v-waitlist').style.display = v ? 'block' : 'none'; }
    function irAPago() {
        estado.direccion = ($('#v-direccion').value || '').trim();
        estado.distrito = $('#v-distrito').value;
        estado.referencia = ($('#v-referencia').value || '').trim();
        estado.telefono = ($('#v-telefono').value || '').trim();
        const al = $('#v-distrito-alerta'); al.classList.remove('show'); mostrarWaitlist(false);
        if (!estado.direccion) { $('#v-direccion').focus(); return; }
        if (!estado.distrito) { $('#v-distrito').focus(); return; }
        const d = DISTRITOS.find(x => x.nombre === estado.distrito);
        if (d && d.habilitado === false) { al.textContent = CFG.mensaje_distrito; al.classList.add('show'); mostrarWaitlist(true); return; }
        renderPagos(); screen('screen-pago');
    }
    async function avisarme() {
        const email = ($('#v-wl-email').value || '').trim();
        if (!email || !email.includes('@')) { alert('Ingresa un email válido'); return; }
        try {
            await fetch('/api/v1/waitlist', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, distrito_nombre: $('#v-distrito').value, categoria_interes: estado.area ? estado.area.codigo : null }) });
            alert('¡Gracias! Te avisaremos cuando lleguemos a tu zona.'); mostrarWaitlist(false);
        } catch (e) { alert('No se pudo registrar.'); }
    }

    function renderPagos() {
        $('#v-monto').textContent = money(CFG.tarifa_visita);
        const ops = [];
        if (CFG.permitir_efectivo) ops.push({ k: 'efectivo', icon: 'fa-hand-holding-dollar', t: 'Efectivo al técnico', s: 'Pagas cuando llegue' });
        ops.push({ k: 'tarjeta', icon: 'fa-credit-card', t: 'Pagar con tarjeta', s: 'Visa, Mastercard, etc.' });
        estado.metodo = ops[0].k;
        $('#v-pagos').innerHTML = ops.map((o, i) => `
            <div class="v-pay-opt ${i === 0 ? 'sel' : ''}" data-k="${o.k}">
                <div class="pi"><i class="fas ${o.icon}"></i></div>
                <div class="pt"><b>${o.t}</b><small>${o.s}</small></div><div class="radio"></div>
            </div>`).join('');
        $('#v-pagos').querySelectorAll('.v-pay-opt').forEach(el => el.addEventListener('click', () => {
            estado.metodo = el.dataset.k;
            $('#v-pagos').querySelectorAll('.v-pay-opt').forEach(x => x.classList.toggle('sel', x === el)); pop();
        }));
    }

    // -------- Crear solicitud + pago --------
    async function crearSolicitud() {
        const t = TIPOS[estado.tipoKey];
        const problemaTexto = `[${estado.area.nombre} › ${t.label}] ${estado.problema.nombre}` + (estado.descripcion ? ` — ${estado.descripcion}` : '');
        const r = await fetch('/api/v1/solicitudes', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problema: problemaTexto, categoria_id: estado.area.categoria_id || 1,
                direccion: estado.direccion, distrito: estado.distrito || null,
                referencia: estado.referencia || null, telefono: estado.telefono || null,
                metodo_pago: estado.metodo, pago_adelantado: false
            })
        });
        if (!r.ok) throw new Error('crear');
        const d = await r.json();
        if (d.id) fetch(`/api/v1/asignacion/iniciar/${d.id}`, { method: 'POST' }).catch(() => {});
        return d.id;
    }

    async function confirmar() {
        const btn = $('#v-submit'); btn.disabled = true;
        try {
            estado.solicitudId = await crearSolicitud();
            if (estado.metodo === 'tarjeta') {
                const r = await fetch('/api/v1/pagos/iniciar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ solicitud_id: estado.solicitudId, monto: CFG.tarifa_visita, tipo_comprobante: 'boleta', cliente_telefono: estado.telefono || null })
                });
                const pd = await r.json(); estado.pagoRef = pd.referencia;
                if (r.ok && pd.simulado === false && pd.url_pago) { window.location.href = pd.url_pago; return; }  // pasarela real
                $('#izi-monto').textContent = money(CFG.tarifa_visita);
                $('#izi-btn-monto').textContent = money(CFG.tarifa_visita);
                screen('screen-izipay'); btn.disabled = false; return;   // stub: form IziPay in-app
            }
            estado.pagoMetodo = 'efectivo'; estado.pagoComprobante = null;
            buscarTecnicos();
        } catch (e) { alert('No se pudo enviar la solicitud. Intenta de nuevo.'); }
        finally { btn.disabled = false; }
    }

    async function pagarIzipay() {
        const btn = $('#izi-pagar'); btn.disabled = true; $('#v-paying').classList.add('open');
        let comprobante = null;
        try {
            if (estado.pagoRef) {
                await fetch('/api/v1/pagos/retorno?ref=' + encodeURIComponent(estado.pagoRef) + '&sim=1');  // aprueba + emite comprobante
                const est = await (await fetch('/api/v1/pagos/' + encodeURIComponent(estado.pagoRef) + '/estado')).json();
                comprobante = est.comprobante;
            }
        } catch (e) {}
        $('#v-paying').classList.remove('open'); btn.disabled = false;
        estado.pagoMetodo = 'tarjeta'; estado.pagoComprobante = comprobante;
        buscarTecnicos();
    }

    // ---- Selección de técnico (post-pago) ----
    async function buscarTecnicos() {
        cerrarModal();
        $('#v-tecnicos').classList.add('open');
        $('#v-tec-buscando').hidden = false; $('#v-tec-lista').hidden = true;
        $('#v-tec-num').textContent = 'Solicitud #' + String(estado.solicitudId || 0).padStart(5, '0');
        let tecnicos = [];
        try { const d = await (await fetch('/api/v1/tecnicos-disponibles?categoria_id=' + (estado.area.categoria_id || ''))).json(); tecnicos = d.tecnicos || []; } catch (e) {}
        await new Promise(r => setTimeout(r, 1200));   // "buscando…"
        renderTecnicos(tecnicos);
    }
    function renderTecnicos(tecnicos) {
        $('#v-tec-buscando').hidden = true; $('#v-tec-lista').hidden = false;
        $('#v-tec-cards').innerHTML = tecnicos.map((t, i) => `
            <div class="v-tec-card">
                <div class="ava"><i class="fas fa-user"></i></div>
                <div class="body"><b>${esc(t.nombre)}</b>
                    <div class="stars">⭐ ${t.rating} <span>(${t.total_servicios} servicios)</span></div>
                    <div class="sub">${esc(t.especialidad || 'Técnico')} · <i class="fas fa-location-dot"></i> ${esc(t.tiempo_estimado || '~20 min')} de ti</div>
                </div>
                <button type="button" class="v-tec-elegir" data-i="${i}">ELEGIR</button>
            </div>`).join('') || '<p style="color:var(--v-text2)">No hay técnicos en línea ahora — usa la asignación automática.</p>';
        $('#v-tec-cards').querySelectorAll('.v-tec-elegir').forEach(b => b.addEventListener('click', () => elegirTecnico(tecnicos[+b.dataset.i])));
    }
    async function elegirTecnico(t) { await asignar(t ? { tecnico_id: t.id, tecnico_nombre: t.nombre, rating: t.rating, total_servicios: t.total_servicios } : { auto: true }); }
    async function asignarAuto() { await asignar({ auto: true }); }
    async function asignar(payload) {
        try {
            const d = await (await fetch('/api/v1/solicitudes/' + estado.solicitudId + '/asignar-tecnico', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            })).json();
            estado.tecnico = d.tecnico || null;
            $('#v-tecnicos').classList.remove('open');
            mostrarExito();
        } catch (e) { alert('No se pudo asignar el técnico.'); }
    }

    function mostrarExito() {
        const t = TIPOS[estado.tipoKey], tec = estado.tecnico;
        if (tec && tec.nombre) {
            $('#v-succ-tec').style.display = 'flex';
            $('#v-succ-tec-nombre').textContent = tec.nombre;
            $('#v-succ-tec-meta').textContent = (tec.rating ? '⭐ ' + tec.rating + ' · ' : '') + 'Técnico';
        }
        $('#v-succ-bc').textContent = `${estado.area.nombre} › ${t.label} › ${estado.problema.nombre}`;
        $('#v-succ-dir').textContent = `${estado.direccion}${estado.distrito ? ', ' + estado.distrito : ''}`;
        const ic = $('#v-succ-pago-ic'), lbl = $('#v-succ-pago');
        if (estado.pagoMetodo === 'tarjeta') { ic.className = 'fas fa-credit-card'; lbl.textContent = 'Pagado con tarjeta' + (estado.pagoComprobante ? ' · ' + estado.pagoComprobante : ''); }
        else { ic.className = 'fas fa-hand-holding-dollar'; lbl.textContent = 'Pago en efectivo (al técnico)'; }
        $('#v-succ-num').textContent = '#' + String(estado.solicitudId || 0).padStart(5, '0');
        $('#v-success-chat').href = '/cliente/servicio/' + (estado.solicitudId || '') + '/chats';
        $('#v-success').classList.add('open');
    }

    // -------- Foto --------
    function elegirFoto() { $('#v-photo-input').click(); }
    function onFoto(e) { const f = e.target.files && e.target.files[0]; if (!f) return; estado.foto = f; const pb = $('#v-photo'); pb.classList.add('has'); pb.querySelector('span').textContent = '✓ ' + f.name; }

    // -------- Navegación --------
    function mostrar(sel) { const el = $(sel); el.hidden = false; requestAnimationFrame(() => el.classList.add('show')); }
    function ocultar(sel) { const el = $(sel); el.classList.remove('show'); el.hidden = true; }
    function navBack() {
        if ($('#v-modal').classList.contains('open')) {
            if ($('#screen-izipay').classList.contains('active')) return screen('screen-pago');
            if ($('#screen-pago').classList.contains('active')) return screen('screen-direccion');
            if ($('#screen-direccion').classList.contains('active')) return screen('screen-detalle');
            if ($('#screen-login').classList.contains('active')) return screen('screen-detalle');
            return cerrarModal();
        }
        if (!$('#nivel3').hidden) return ocultar('#nivel3');
        if (document.body.classList.contains('selected-mode')) {
            document.body.classList.remove('selected-mode'); ocultar('#nivel2');
            $('#v-chips').querySelectorAll('.v-chip').forEach(el => el.classList.remove('selected'));
            estado.area = null; estado.tipoKey = null; window.scrollTo({ top: 0, behavior: 'smooth' }); return;
        }
        window.location.href = '/';
    }

    const on = (sel, ev, fn) => { const e = $(sel); if (e) e.addEventListener(ev, fn); };
    async function init() {
        if (!$('#v-chips')) return;   // el flujo no está en esta página
        pintarMute();
        on('#v-back', 'click', navBack);          // opcionales (ausentes en la landing)
        on('#v-mute', 'click', toggleMute);
        on('#v-modal-close', 'click', cerrarModal);
        on('#v-modal', 'click', (e) => { if (e.target === $('#v-modal')) cerrarModal(); });
        on('#v-photo', 'click', elegirFoto);
        on('#v-photo-input', 'change', onFoto);
        on('#btn-a-direccion', 'click', irADireccion);
        on('#btn-whatsapp', 'click', continuarWhatsapp);
        on('#btn-a-pago', 'click', irAPago);
        on('#v-submit', 'click', confirmar);
        on('#izi-pagar', 'click', pagarIzipay);
        on('#v-tec-auto', 'click', asignarAuto);
        on('#v-wl-btn', 'click', avisarme);
        document.querySelectorAll('[data-back]').forEach(b => b.addEventListener('click', () => screen('screen-' + b.dataset.back)));
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && $('#v-modal').classList.contains('open')) navBack(); });

        await cargarConfig(); await cargarAreas(); await cargarDistritos(); renderChips();
    }
    document.addEventListener('DOMContentLoaded', init);
})();
