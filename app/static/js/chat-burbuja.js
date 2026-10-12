/**
 * MitaBurbuja (zMita-19 Parte A) — burbuja flotante que abre el chat IA en un modal.
 * Carga chat-solicitud.js / mita-voz.js / chat-solicitud.css de forma perezosa al abrir.
 */
const MitaBurbuja = (function () {
    'use strict';
    let bubble, modal, overlay, closeBtn, modalBody;
    let isOpen = false, chatInitialized = false;

    function init() {
        bubble = document.getElementById('chatBubble');
        modal = document.getElementById('chatModal');
        overlay = document.getElementById('chatOverlay');
        closeBtn = document.getElementById('chatModalClose');
        modalBody = document.getElementById('chatModalBody');
        if (!bubble || !modal) { console.warn('[MitaBurbuja] Elementos no encontrados'); return; }

        bubble.addEventListener('click', toggle);
        if (closeBtn) closeBtn.addEventListener('click', close);
        if (overlay) overlay.addEventListener('click', close);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && isOpen) close(); });
        setTimeout(() => { if (!isOpen) bubble.classList.add('attention'); }, 5000);
        console.log('[MitaBurbuja] Inicializado');
    }

    function toggle() { isOpen ? close() : open(); }

    function open() {
        isOpen = true;
        bubble.classList.remove('attention');
        modal.classList.remove('hidden');
        if (overlay) overlay.classList.remove('hidden');
        void modal.offsetHeight; // reflow
        modal.classList.add('visible');
        if (overlay) overlay.classList.add('visible');
        bubble.style.opacity = '0'; bubble.style.pointerEvents = 'none';
        if (!chatInitialized) initChat();
    }

    function close() {
        isOpen = false;
        modal.classList.remove('visible');
        if (overlay) overlay.classList.remove('visible');
        setTimeout(() => { modal.classList.add('hidden'); if (overlay) overlay.classList.add('hidden'); }, 300);
        bubble.style.opacity = '1'; bubble.style.pointerEvents = 'auto';
    }

    function initChat() {
        if (typeof ChatSolicitud === 'undefined') { loadChatScript(); return; }
        modalBody.classList.add('chat-solicitud');
        ChatSolicitud.init({
            container: modalBody,
            onComplete: (sol) => console.log('[MitaBurbuja] Solicitud completada:', sol),
            onCancel: () => close()
        });
        chatInitialized = true;
    }

    function cargarCSS(href) {
        if (document.querySelector(`link[href*="${href}"]`)) return;
        const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '/static/css/' + href; document.head.appendChild(l);
    }
    function cargarJS(src) {
        return new Promise((resolve) => {
            if (document.querySelector(`script[src*="${src}"]`)) { resolve(); return; }
            const s = document.createElement('script'); s.src = '/static/js/' + src; s.onload = () => resolve(); s.onerror = () => resolve(); document.body.appendChild(s);
        });
    }

    async function loadChatScript() {
        modalBody.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;"><div style="text-align:center;"><div class="spinner" style="margin:0 auto 12px;"></div><span>Cargando asistente…</span></div></div>';
        cargarCSS('chat-solicitud.css');
        await cargarJS('mita-voz.js');
        await cargarJS('chat-solicitud.js');
        if (typeof ChatSolicitud === 'undefined') { modalBody.innerHTML = '<p style="padding:24px;color:#888;text-align:center;">No se pudo cargar el asistente.</p>'; return; }
        initChat();
    }

    return { init, open, close };
})();

document.addEventListener('DOMContentLoaded', () => MitaBurbuja.init());
