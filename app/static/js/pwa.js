/**
 * MITA PWA (zMita-33) — instalación + avisos Web Push.
 * Se carga en todas las páginas (inyectado en <head>). Expone window.MitaPWA.
 *   - Registra el service worker /sw.js (scope "/").
 *   - Captura beforeinstallprompt y ofrece "Instalar MITA" (Chrome/Edge).
 *   - En iPhone/iPad muestra una guía de 3 pasos (Safari no instala solo).
 *   - "Activar avisos" pide permiso SOLO con gesto del usuario y suscribe al push.
 * Nunca pide permiso de notificaciones al cargar la página.
 */
(function () {
    'use strict';
    let deferredPrompt = null;
    let swReg = null;

    const esIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) ||
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const esInstalada = () => window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true;

    // Identificador local estable del dispositivo (para no acumular suscripciones).
    function dispositivoId() {
        try {
            let id = localStorage.getItem('mita_device_id');
            if (!id) {
                id = (crypto && crypto.randomUUID) ? crypto.randomUUID()
                    : (Date.now().toString(36) + Math.random().toString(36).slice(2));
                localStorage.setItem('mita_device_id', id);
            }
            return id;
        } catch (e) {
            return 'sin-storage-' + Math.random().toString(36).slice(2);
        }
    }

    function plataforma() {
        const u = navigator.userAgent.toLowerCase();
        if (/iphone|ipad|ipod/.test(u) || esIOS()) return 'ios';
        if (/android/.test(u)) return 'android';
        if (/windows/.test(u)) return 'windows';
        if (/mac/.test(u)) return 'mac';
        return 'otro';
    }

    function navegador() {
        const u = navigator.userAgent;
        if (/edg\//i.test(u) || /edgios/i.test(u)) return 'Edge';
        if (/crios/i.test(u)) return 'Chrome';           // Chrome en iOS
        if (/fxios/i.test(u)) return 'Firefox';          // Firefox en iOS
        if (/chrome\//i.test(u) && !/edg\//i.test(u)) return 'Chrome';
        if (/firefox\//i.test(u)) return 'Firefox';
        if (/safari\//i.test(u) && !/chrome/i.test(u)) return 'Safari';
        return 'otro';
    }

    // ---- Service Worker ----
    async function registrarSW() {
        if (!('serviceWorker' in navigator)) return null;
        try {
            swReg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
            return swReg;
        } catch (e) {
            console.warn('[MitaPWA] SW no registrado:', e);
            return null;
        }
    }

    // ---- Instalación ----
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        // Chip discreto solo en el landing
        if (location.pathname === '/' && !esInstalada()) mostrarChipInstalar();
    });
    window.addEventListener('appinstalled', () => { deferredPrompt = null; quitarChip(); });

    function puedeInstalar() { return !!deferredPrompt; }

    async function instalar() {
        if (esInstalada()) return 'instalada';
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const r = await deferredPrompt.userChoice;
            deferredPrompt = null; quitarChip();
            return r && r.outcome === 'accepted' ? 'aceptada' : 'rechazada';
        }
        if (esIOS()) { mostrarGuiaIOS(); return 'guia-ios'; }
        return 'no-disponible';
    }

    // ---- UI: chip discreto de instalar (landing). En iOS dice "Agregar a inicio". ----
    function mostrarChipInstalar() {
        try { if (localStorage.getItem('mita_pwa_chip') === 'off') return; } catch (e) {}
        if (document.getElementById('mita-pwa-chip') || esInstalada()) return;
        const ios = esIOS();
        const etiqueta = ios ? 'Agrega MITA a inicio' : 'Instala MITA';
        const accion = ios ? 'Agregar' : 'Instalar';
        const c = document.createElement('div');
        c.id = 'mita-pwa-chip';
        c.style.cssText = 'position:fixed;left:16px;bottom:16px;z-index:9996;display:flex;align-items:center;gap:10px;background:#12101a;color:#e9edef;border:1px solid #2a2a4e;border-radius:14px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.45);font-family:system-ui,sans-serif;font-size:14px;max-width:84vw';
        c.innerHTML = '<img src="/static/img/mita/icon-192.png" width="28" height="28" style="border-radius:7px" alt="MITA"><span>' + etiqueta + '</span>' +
            '<button type="button" id="mita-pwa-chip-ok" style="background:#22c55e;color:#06210f;border:none;border-radius:9px;padding:7px 12px;font-weight:700;cursor:pointer">' + accion + '</button>' +
            '<button type="button" id="mita-pwa-chip-x" aria-label="Cerrar" style="background:transparent;color:#8a8a9a;border:none;cursor:pointer;font-size:16px">✕</button>';
        document.body.appendChild(c);
        document.getElementById('mita-pwa-chip-ok').onclick = () => (ios ? mostrarGuiaIOS() : instalar());
        document.getElementById('mita-pwa-chip-x').onclick = () => { quitarChip(); try { localStorage.setItem('mita_pwa_chip', 'off'); } catch (e) {} };
    }
    function quitarChip() { const c = document.getElementById('mita-pwa-chip'); if (c) c.remove(); }

    // ---- UI: guía de instalación iOS ----
    function mostrarGuiaIOS() {
        if (document.getElementById('mita-ios-guia')) return;
        const ov = document.createElement('div');
        ov.id = 'mita-ios-guia';
        ov.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(6,4,12,.6);backdrop-filter:blur(4px);display:flex;align-items:flex-end;justify-content:center;font-family:system-ui,sans-serif';
        ov.innerHTML =
            '<div style="background:#12101a;color:#e9edef;border-radius:18px 18px 0 0;max-width:460px;width:100%;padding:22px 20px 28px;box-shadow:0 -10px 40px rgba(0,0,0,.5)">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">' +
            '<b style="font-size:17px">Agrega MITA a tu inicio</b>' +
            '<button type="button" id="mita-ios-x" aria-label="Cerrar" style="background:transparent;border:none;color:#8a8a9a;font-size:20px;cursor:pointer">✕</button></div>' +
            '<p style="color:#c9bfe0;font-size:14px;margin:0 0 16px">Para avisarte cuando tu técnico esté en camino, agrega MITA a tu pantalla de inicio.</p>' +
            paso('1', 'Toca <b>Compartir</b>', '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M12 15V3m0 0L8 7m4-4l4 4"/><path d="M4 12v7a1 1 0 001 1h14a1 1 0 001-1v-7"/></svg>') +
            paso('2', 'Elige <b>“Agregar a inicio”</b>', '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/></svg>') +
            paso('3', 'Toca <b>“Agregar”</b> y abre MITA desde el ícono', '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>') +
            '</div>';
        document.body.appendChild(ov);
        const cerrar = () => ov.remove();
        document.getElementById('mita-ios-x').onclick = cerrar;
        ov.addEventListener('click', (e) => { if (e.target === ov) cerrar(); });
    }
    function paso(n, texto, icono) {
        return '<div style="display:flex;align-items:center;gap:14px;padding:12px;background:#181830;border:1px solid #2a2a4e;border-radius:12px;margin-bottom:10px">' +
            '<div style="width:34px;height:34px;flex:0 0 auto;border-radius:50%;background:#22c55e;color:#06210f;font-weight:800;display:flex;align-items:center;justify-content:center">' + n + '</div>' +
            '<div style="flex:1;font-size:14px">' + texto + '</div>' + icono + '</div>';
    }

    // ---- Avisos Web Push ----
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const raw = atob(base64);
        const arr = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
        return arr;
    }

    async function activarAvisos(opts) {
        opts = opts || {};
        if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) {
            return { ok: false, motivo: 'no-soportado' };
        }
        if (esIOS() && !esInstalada()) {
            // Safari en iOS solo permite avisos cuando MITA está abierta como app instalada
            mostrarGuiaIOS();
            return { ok: false, motivo: 'ios-requiere-instalar' };
        }
        const permiso = await Notification.requestPermission();
        if (permiso !== 'granted') {
            return { ok: false, motivo: permiso === 'denied' ? 'denegado' : 'sin-permiso',
                     error: permiso === 'denied'
                         ? 'Permiso denegado. Actívalo en los ajustes del navegador para este sitio.'
                         : 'No se concedió el permiso de avisos.' };
        }
        try {
            const reg = swReg || await navigator.serviceWorker.ready;
            const r = await fetch('/api/v1/push/clave-publica');
            const { clave, configurado } = await r.json();
            if (!configurado || !clave) {
                return { ok: false, motivo: 'servidor-sin-vapid',
                         error: 'El servidor aún no tiene las claves de avisos (VAPID). Falta configurarlas en Railway.' };
            }
            let sub = await reg.pushManager.getSubscription();
            if (!sub) {
                sub = await reg.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(clave)
                });
            }
            const body = { subscription: sub.toJSON(), plataforma: plataforma(), dispositivo_id: dispositivoId() };
            if (opts.solicitud_id) body.solicitud_id = opts.solicitud_id;
            if (opts.rol) body.rol = opts.rol;
            const resp = await fetch('/api/v1/push/suscribir', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || data.ok === false) {
                return { ok: false, motivo: 'servidor',
                         error: data.error || data.detail || data.detalle || ('No se pudo guardar la suscripción (HTTP ' + resp.status + ').') };
            }
            return { ok: true, suscripcion: sub.toJSON(), datos: data };
        } catch (e) {
            return { ok: false, motivo: 'excepcion', error: (e && e.message) ? e.message : 'No se pudo activar los avisos.' };
        }
    }

    async function suscripcionActual() {
        try {
            const reg = swReg || await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.getSubscription();
            return sub ? sub.toJSON() : null;
        } catch (e) { return null; }
    }

    async function diagnostico() {
        let sw = false, sub = null;
        try { sw = !!(await navigator.serviceWorker.getRegistration('/')); } catch (e) {}
        try { sub = await suscripcionActual(); } catch (e) {}
        return {
            plataforma: plataforma(),
            navegador: navegador(),
            instalada: esInstalada(),
            soporta_push: ('PushManager' in window) && ('Notification' in window),
            service_worker: sw,
            permiso: ('Notification' in window) ? Notification.permission : 'no-soportado',
            suscripcion: sub
        };
    }

    // ---- Canal de avisos / WhatsApp ----
    async function _setCanal(solicitudId, canal) {
        if (!solicitudId) return;
        try {
            await fetch('/api/v1/push/canal', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ solicitud_id: solicitudId, canal: canal })
            });
        } catch (e) {}
    }
    async function _linkWhatsApp(codigo) {
        let num = '';
        try { num = (await (await fetch('/api/v1/push/canal-config')).json()).whatsapp_numero || ''; } catch (e) {}
        const texto = encodeURIComponent('Hola MITA, quiero recibir avisos de mi solicitud ' + (codigo || ''));
        return num ? ('https://wa.me/' + num + '?text=' + texto) : null;
    }

    // ---- Paso de avisos tras el pago/confirmación (Parte A) ----
    // opts: { solicitud_id, codigo, onListo }  -> devuelve {canal}
    function pasoAvisos(opts) {
        opts = opts || {};
        const sid = opts.solicitud_id;
        const codigo = opts.codigo || (sid ? ('#' + sid) : '');
        return new Promise((resolve) => {
            if (document.getElementById('mita-paso-avisos')) { resolve({ canal: 'ninguno', cerrado: true }); return; }
            const iosSinApp = esIOS() && !esInstalada();
            const ov = document.createElement('div');
            ov.id = 'mita-paso-avisos';
            ov.style.cssText = 'position:fixed;inset:0;z-index:10001;background:rgba(6,4,12,.6);backdrop-filter:blur(4px);display:flex;align-items:flex-end;justify-content:center;font-family:system-ui,sans-serif';
            const btn = (id, txt, primario) => '<button type="button" id="' + id + '" style="width:100%;padding:14px;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:10px;' +
                (primario ? 'background:#22c55e;color:#06210f' : 'background:#181830;color:#e9edef;border:1px solid #2a2a4e') + '">' + txt + '</button>';
            let cuerpo;
            if (iosSinApp) {
                cuerpo = '<p style="color:#c9bfe0;font-size:14px;margin:0 0 14px">Para avisarte cuando tu técnico esté en camino:</p>' +
                    btn('mita-pa-wa', '💬 Recibir avisos por WhatsApp', true) +
                    btn('mita-pa-ios', '➕ O agrega MITA a tu inicio', false) +
                    btn('mita-pa-no', 'Ahora no', false);
            } else {
                cuerpo = '<p style="color:#c9bfe0;font-size:14px;margin:0 0 14px">Te avisamos en tu teléfono apenas un técnico acepte y cuando esté en camino.</p>' +
                    btn('mita-pa-si', '🔔 Sí, avisarme', true) +
                    btn('mita-pa-no', 'Ahora no', false);
            }
            ov.innerHTML = '<div style="background:#12101a;color:#e9edef;border-radius:18px 18px 0 0;max-width:460px;width:100%;padding:22px 20px 28px;box-shadow:0 -10px 40px rgba(0,0,0,.5)">' +
                '<b style="font-size:17px;display:block;margin-bottom:6px">¿Te avisamos cuando tu técnico esté en camino?</b>' +
                cuerpo +
                '<div id="mita-pa-msg" style="margin-top:12px;font-size:13px;color:#22c55e;min-height:16px"></div></div>';
            document.body.appendChild(ov);
            const msg = (t, err) => { const m = document.getElementById('mita-pa-msg'); if (m) { m.textContent = t; m.style.color = err ? '#ff6b6b' : '#22c55e'; } };
            const cerrar = (r) => { try { ov.remove(); } catch (e) {} if (opts.onListo) { try { opts.onListo(r); } catch (e) {} } resolve(r); };

            const si = document.getElementById('mita-pa-si');
            if (si) si.onclick = async () => {
                si.disabled = true; msg('Pidiendo permiso…');
                const r = await activarAvisos({ solicitud_id: sid, rol: 'cliente' });
                if (r.ok) { msg('¡Listo! Te avisaremos ✓'); setTimeout(() => cerrar({ canal: 'push', res: r }), 700); }
                else { msg(r.error || 'No se pudo activar.', true); si.disabled = false; }
            };
            const wa = document.getElementById('mita-pa-wa');
            if (wa) wa.onclick = async () => {
                await _setCanal(sid, 'whatsapp');
                const link = await _linkWhatsApp(codigo);
                if (link) { window.open(link, '_blank'); cerrar({ canal: 'whatsapp' }); }
                else msg('Aún no hay número de WhatsApp configurado. Te avisaremos por la app.', true);
            };
            const iosb = document.getElementById('mita-pa-ios');
            if (iosb) iosb.onclick = () => mostrarGuiaIOS();
            const no = document.getElementById('mita-pa-no');
            if (no) no.onclick = async () => { await _setCanal(sid, 'ninguno'); cerrar({ canal: 'ninguno' }); };
        });
    }

    window.MitaPWA = {
        esIOS, esInstalada, puedeInstalar, instalar, mostrarGuiaIOS, mostrarChipInstalar,
        activarAvisos, suscripcionActual, diagnostico, plataforma, navegador, registrarSW,
        dispositivoId, pasoAvisos
    };

    // Auto-init
    function _init() {
        registrarSW();
        // iOS no dispara beforeinstallprompt: ofrecer la guía de forma visible en el landing.
        if (location.pathname === '/' && esIOS() && !esInstalada()) {
            setTimeout(mostrarChipInstalar, 1200);
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }
})();
