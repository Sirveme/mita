/* Chat individual MITA (salas post-servicio) — carga, envío y polling. */
(function () {
    'use strict';
    const SALA = window.SALA_ID;
    const $ = (s) => document.querySelector(s);
    const esc = (t) => { const d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
    let ultimoAt = null;

    function hora(iso) { if (!iso) return ''; return new Date(iso).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' }); }

    function pintar(m) {
        const propio = m.emisor_tipo === 'cliente';
        const div = document.createElement('div');
        div.className = 'c-msg ' + (propio ? 'sent' : 'recv');
        div.innerHTML =
            (!propio && m.emisor_nombre ? `<span class="sender">${esc(m.emisor_nombre)}</span>` : '') +
            `<span class="t">${esc(m.mensaje)}</span>` +
            `<span class="meta">${hora(m.creado_en)}${propio ? ' <span class="check">✓✓</span>' : ''}</span>`;
        $('#msgs').appendChild(div);
        if (m.creado_en) ultimoAt = m.creado_en;
    }
    function scroll() { const c = $('#msgs'); c.scrollTop = c.scrollHeight; }

    async function cargar() {
        try {
            const d = await (await fetch(`/api/v1/chats/${SALA}/mensajes`)).json();
            if (d.sala) { $('#c-title').textContent = d.sala.titulo || 'Chat'; $('#c-avatar').innerHTML = `<i class="fas ${d.sala.icono || 'fa-comments'}"></i>`; }
            $('#msgs').innerHTML = '';
            (d.mensajes || []).forEach(pintar);
            if (!(d.mensajes || []).length) $('#msgs').innerHTML = '<div class="c-empty">Aún no hay mensajes. Escribe el primero 👋</div>';
            scroll();
        } catch (e) { $('#msgs').innerHTML = '<div class="c-empty">No se pudo cargar el chat.</div>'; }
    }
    async function poll() {
        if (!ultimoAt) return;
        try {
            const d = await (await fetch(`/api/v1/chats/${SALA}/mensajes/nuevos?desde=${encodeURIComponent(ultimoAt)}`)).json();
            (d.mensajes || []).forEach(pintar); if ((d.mensajes || []).length) scroll();
        } catch (e) {}
    }
    async function enviar() {
        const inp = $('#c-text'); const texto = (inp.value || '').trim(); if (!texto) return;
        inp.value = '';
        try {
            const d = await (await fetch(`/api/v1/chats/${SALA}/mensajes`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mensaje: texto, emisor_tipo: 'cliente' })
            })).json();
            if (d.mensaje) { const e = $('#msgs .c-empty'); if (e) e.remove(); pintar(d.mensaje); scroll(); }
        } catch (e) { inp.value = texto; alert('No se pudo enviar.'); }
    }
    document.addEventListener('DOMContentLoaded', () => {
        $('#c-send').addEventListener('click', enviar);
        $('#c-text').addEventListener('keypress', (e) => { if (e.key === 'Enter') enviar(); });
        $('#c-attach').addEventListener('click', () => alert('Adjuntar foto: próximamente.'));
        cargar(); setInterval(poll, 3000);
    });
})();
