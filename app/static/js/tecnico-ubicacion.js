/*
 * Envío de ubicación del técnico (tipo Uber). Mientras el servicio está EN_CAMINO,
 * envía su posición al servidor cada pocos segundos.
 *   MitaUbicacion.iniciar(solicitudId);  MitaUbicacion.detener();
 * Degrada sin romper si el navegador no tiene geolocalización o se niega el permiso.
 */
(function () {
    'use strict';
    let watchId = null;
    let solicitudActiva = null;
    let ultimoEnvio = 0;
    const MIN_MS = 8000;   // no enviar más de una vez cada ~8s

    async function enviar(pos) {
        if (!solicitudActiva) return;
        const ahora = Date.now();
        if (ahora - ultimoEnvio < MIN_MS) return;
        ultimoEnvio = ahora;
        const c = pos.coords;
        try {
            await fetch(`/api/v1/solicitudes/${solicitudActiva}/ubicacion-tecnico`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: c.latitude, lng: c.longitude,
                    precision: c.accuracy, velocidad: c.speed, rumbo: c.heading
                })
            });
        } catch (e) { /* red intermitente: reintenta en el próximo tick */ }
    }

    const MitaUbicacion = {
        async iniciar(solicitudId) {
            if (!solicitudId || !('geolocation' in navigator)) return false;
            if (watchId !== null && solicitudActiva === solicitudId) return true;
            this.detener();
            solicitudActiva = solicitudId;
            try {
                if (navigator.permissions && navigator.permissions.query) {
                    const p = await navigator.permissions.query({ name: 'geolocation' });
                    if (p.state === 'denied') {
                        console.warn('[MitaUbicacion] permiso de ubicación denegado.');
                        return false;
                    }
                }
            } catch (e) { /* permissions API no soportada: seguimos */ }
            watchId = navigator.geolocation.watchPosition(
                enviar,
                (err) => console.warn('[MitaUbicacion] GPS:', err && err.message),
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
            );
            return true;
        },
        detener() {
            if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
            solicitudActiva = null;
        },
        activo() { return watchId !== null; }
    };
    window.MitaUbicacion = MitaUbicacion;
})();
