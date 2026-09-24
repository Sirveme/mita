/* Dashboard técnico: toggle EN_SERVICIO, solicitud entrante (sonido+voz), servicio activo. */
(function () {
    'use strict';
    const $ = (s) => document.querySelector(s);
    const esc = (t) => { const d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
    const money = (v) => 'S/ ' + (Number(v) || 0).toFixed(2);
    const CATS = { 1: '⚡ Electricidad', 2: '🚰 Gasfitería', 3: '🧊 Artefactos', 4: '🛋️ Instalaciones', 5: '🧱 Albañilería' };

    let estadoServicio = 'FUERA_SERVICIO';
    let entranteId = null;      // notif_id actual
    let timer = null, restante = 0;
    const ESPERA = 180;         // 3 min

    function toast(msg) { const t = $('#t-toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2200); }

    // ---- Estado en servicio ----
    function pintarToggle() {
        const on = estadoServicio === 'EN_SERVICIO';
        const card = $('#t-toggle');
        card.classList.toggle('on', on);
        $('#t-estado-txt').textContent = on ? 'EN SERVICIO' : (estadoServicio === 'OCUPADO' ? 'OCUPADO' : 'FUERA DE SERVICIO');
        $('#t-knob').textContent = on ? 'ON' : 'OFF';
    }
    async function toggle() {
        if (estadoServicio === 'OCUPADO') { toast('Tienes un servicio activo'); return; }
        const nuevo = estadoServicio === 'EN_SERVICIO' ? 'FUERA_SERVICIO' : 'EN_SERVICIO';
        try {
            const r = await fetch('/api/v1/tecnico/estado-servicio', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado: nuevo }) });
            if (r.status === 401) { location.href = '/login'; return; }
            const d = await r.json(); estadoServicio = d.estado_servicio; pintarToggle();
            if (window.MitaSonido && nuevo === 'EN_SERVICIO') MitaSonido.alerta();
        } catch (e) { toast('No se pudo cambiar el estado'); }
    }

    // ---- Solicitud entrante ----
    function renderEntrante(e) {
        entranteId = e.notif_id; restante = ESPERA;
        const cont = $('#t-entrante-cont');
        cont.innerHTML = `
            <div class="t-entrante">
                <div class="cat">${CATS[0] || ''}<span>${esc(extraerCat(e.problema))}</span><small>#${String(e.id).padStart(5, '0')}</small></div>
                <div class="cuerpo">
                    <div class="prob">${esc(limpiar(e.problema))}</div>
                    <div class="meta"><i class="fas fa-location-dot"></i> ${esc(e.direccion || '—')}</div>
                    <div class="precio"><i class="fas fa-coins"></i> ${money(e.costo_visita)} (base)</div>
                    <div class="t-timer"><i class="fas fa-clock"></i> <span id="t-count">03:00</span><div class="bar"><div class="fill" id="t-fill" style="width:100%"></div></div></div>
                </div>
                <div class="acciones">
                    <button class="t-btn aceptar" id="t-aceptar"><i class="fas fa-check"></i> ACEPTO</button>
                    <button class="t-btn rechazar" id="t-rechazar"><i class="fas fa-xmark"></i> PASO</button>
                </div>
            </div>`;
        $('#t-aceptar').addEventListener('click', () => responder('aceptada'));
        $('#t-rechazar').addEventListener('click', () => responder('rechazada'));
        // Alerta sensorial
        if (window.MitaSonido) MitaSonido.alerta();
        if (window.MitaVoz) {
            MitaVoz.speak(`Nuevo servicio en ${e.distrito || 'tu zona'}. Di ACEPTO para asegurar, o RECHAZA si no puedes ir.`);
            setTimeout(() => MitaVoz.listen(() => responder('aceptada'), () => responder('rechazada')), 3500);
        }
        iniciarTimer();
    }
    function limpiar(p) { const m = (p || '').match(/^\[.*?\]\s*(.*)$/); return (m ? m[1] : (p || '')).split(' — ')[0]; }
    function extraerCat(p) { const m = (p || '').match(/^\[(.*?)\]/); return m ? m[1] : 'Servicio'; }
    function iniciarTimer() {
        clearInterval(timer);
        timer = setInterval(() => {
            restante--;
            const mm = String(Math.floor(restante / 60)).padStart(2, '0'), ss = String(restante % 60).padStart(2, '0');
            const c = $('#t-count'), f = $('#t-fill');
            if (c) c.textContent = `${mm}:${ss}`;
            if (f) f.style.width = Math.max(0, (restante / ESPERA) * 100) + '%';
            if (restante <= 0) { clearInterval(timer); limpiarEntrante(); toast('Tiempo agotado'); }
        }, 1000);
    }
    function limpiarEntrante() { clearInterval(timer); entranteId = null; $('#t-entrante-cont').innerHTML = ''; if (window.MitaVoz) MitaVoz.stop(); }

    async function responder(respuesta) {
        if (!entranteId) return;
        const nid = entranteId; limpiarEntrante();
        try {
            const r = await fetch(`/api/v1/tecnico/notificaciones/${nid}/responder`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ respuesta }) });
            const d = await r.json();
            if (d.estado === 'ACEPTADA') { location.href = '/tecnico/servicio/' + d.solicitud_id; }
            else { toast('Solicitud rechazada'); cargar(); }
        } catch (e) { toast('No se pudo responder'); }
    }

    // ---- Servicio activo ----
    function renderActivo(a) {
        const cont = $('#t-activo-cont');
        if (!a) { cont.innerHTML = '<div class="t-vacio">Sin servicio activo. Ponte EN SERVICIO para recibir solicitudes.</div>'; return; }
        cont.innerHTML = `<div class="t-activo">
            <div class="num">#${String(a.id).padStart(5, '0')} · ${esc(extraerCat(a.problema))}</div>
            <div class="badge">${esc(a.estado)}</div>
            <div class="meta"><i class="fas fa-location-dot"></i> ${esc(a.direccion || '—')}</div>
            <a class="ver" href="/tecnico/servicio/${a.id}">VER DETALLE →</a>
        </div>`;
    }

    async function cargar() {
        try {
            const r = await fetch('/api/v1/tecnico/resumen');
            if (r.status === 401) { location.href = '/login'; return; }
            const d = await r.json();
            estadoServicio = (d.tecnico && d.tecnico.estado_servicio) || 'FUERA_SERVICIO';
            pintarToggle();
            $('#t-nombre').textContent = d.tecnico ? d.tecnico.nombre : 'Técnico';
            $('#t-ava').textContent = (d.tecnico && d.tecnico.nombre ? d.tecnico.nombre[0] : 'T').toUpperCase();
            if (d.entrante && d.entrante.notif_id !== entranteId) renderEntrante(d.entrante);
            else if (!d.entrante && entranteId) limpiarEntrante();
            renderActivo(d.servicio_activo);
        } catch (e) {}
    }

    // ---- Toggles de sonido/voz ----
    function pintarPrefs() {
        const son = localStorage.getItem('mita_sonido') !== 'off';
        const voz = localStorage.getItem('mita_voz') !== 'off';
        $('#t-son').innerHTML = `<i class="fas ${son ? 'fa-volume-high' : 'fa-volume-xmark'}"></i>`;
        $('#t-voz').innerHTML = `<i class="fas ${voz ? 'fa-microphone' : 'fa-microphone-slash'}"></i>`;
    }
    function togglePref(key) { try { localStorage.setItem(key, localStorage.getItem(key) === 'off' ? 'on' : 'off'); } catch (e) {} pintarPrefs(); }

    document.addEventListener('DOMContentLoaded', () => {
        $('#t-toggle').addEventListener('click', toggle);
        $('#t-son').addEventListener('click', () => togglePref('mita_sonido'));
        $('#t-voz').addEventListener('click', () => togglePref('mita_voz'));
        pintarPrefs(); cargar();
        setInterval(cargar, 5000);   // polling de entrantes/estado
    });
})();
