/*
 * Seguimiento del técnico en el mapa (lado cliente). Muestra la casa del cliente,
 * el técnico moviéndose, la ruta y el ETA. Actualiza cada 5s.
 *   MitaSeguimiento.iniciar({ solicitudId, clienteLat, clienteLng, mapaId, etaId });
 *   MitaSeguimiento.detener();
 * Degrada sin romper si no hay Google Maps.
 */
(function () {
    'use strict';
    const S = { map: null, mCliente: null, mTecnico: null, dirSvc: null, dirRender: null, timer: null, opts: null };

    const darkMapStyle = [
        { elementType: 'geometry', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#8a8a9a' }] },
        { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2a2a4e' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e0e1a' }] }
    ];

    function icon(kind) {
        const home = `<svg xmlns="http://www.w3.org/2000/svg" width="46" height="46" viewBox="0 0 40 40">
            <path d="M20 2 C11 2 4 9 4 18 c0 11 16 20 16 20 s16-9 16-20 C36 9 29 2 20 2z" fill="#3b82f6"/>
            <path d="M20 11 l7 6 v9 h-4 v-6 h-6 v6 h-4 v-9z" fill="#0e1726"/></svg>`;
        const tec = `<svg xmlns="http://www.w3.org/2000/svg" width="46" height="46" viewBox="0 0 40 40">
            <path d="M20 2 C11 2 4 9 4 18 c0 11 16 20 16 20 s16-9 16-20 C36 9 29 2 20 2z" fill="#22c55e"/>
            <g fill="#0e1726"><rect x="11" y="16" width="18" height="7" rx="2"/><rect x="14" y="12" width="12" height="6" rx="2"/>
            <circle cx="15" cy="24" r="2.4"/><circle cx="25" cy="24" r="2.4"/></g></svg>`;
        return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(kind === 'home' ? home : tec);
    }

    function setEta(html) { const e = S.opts.etaId && document.getElementById(S.opts.etaId); if (e) e.innerHTML = html; }

    async function tick() {
        try {
            const resp = await fetch(`/api/v1/solicitudes/${S.opts.solicitudId}/ubicacion-tecnico`);
            const d = await resp.json();
            if (!d.disponible) { setEta('<span class="eta-tiempo">🕐 Esperando ubicación del técnico…</span>'); return; }
            const tPos = { lat: d.lat, lng: d.lng };
            const cPos = { lat: S.opts.clienteLat, lng: S.opts.clienteLng };
            S.mTecnico.setPosition(tPos);
            if (Number.isFinite(cPos.lat) && Number.isFinite(cPos.lng)) {
                calcularRuta(tPos, cPos);
                const b = new google.maps.LatLngBounds(); b.extend(tPos); b.extend(cPos);
                S.map.fitBounds(b, 60);
            } else {
                S.map.setCenter(tPos);
            }
        } catch (e) { /* reintenta en el próximo tick */ }
    }

    function calcularRuta(origen, destino) {
        S.dirSvc.route({ origin: origen, destination: destino, travelMode: google.maps.TravelMode.DRIVING },
            (res, status) => {
                if (status === 'OK') {
                    S.dirRender.setDirections(res);
                    const leg = res.routes[0].legs[0];
                    setEta(`<span class="eta-tiempo">🕐 ${leg.duration.text}</span> <span class="eta-distancia">📍 ${leg.distance.text}</span>`);
                }
            });
    }

    const MitaSeguimiento = {
        iniciar(opts) {
            S.opts = opts || {};
            const cont = document.getElementById(S.opts.mapaId);
            if (!cont) return false;
            if (!window.google || !google.maps) {
                cont.innerHTML = '<div style="padding:24px;text-align:center;color:#8a8a9a;">Mapa no disponible. Configura Google Maps para ver el seguimiento.</div>';
                return false;
            }
            const centro = { lat: S.opts.clienteLat || -12.0464, lng: S.opts.clienteLng || -77.0428 };
            S.map = new google.maps.Map(cont, { zoom: 14, center: centro, disableDefaultUI: true, zoomControl: true, styles: darkMapStyle });
            if (Number.isFinite(S.opts.clienteLat)) {
                S.mCliente = new google.maps.Marker({ position: centro, map: S.map, title: 'Tu ubicación',
                    icon: { url: icon('home'), scaledSize: new google.maps.Size(46, 46) } });
            }
            S.mTecnico = new google.maps.Marker({ map: S.map, title: 'Técnico en camino',
                icon: { url: icon('tec'), scaledSize: new google.maps.Size(46, 46) } });
            S.dirSvc = new google.maps.DirectionsService();
            S.dirRender = new google.maps.DirectionsRenderer({ map: S.map, suppressMarkers: true,
                polylineOptions: { strokeColor: '#22c55e', strokeWeight: 4, strokeOpacity: 0.85 } });
            tick();
            S.timer = setInterval(tick, 5000);
            return true;
        },
        detener() { if (S.timer) { clearInterval(S.timer); S.timer = null; } }
    };
    window.MitaSeguimiento = MitaSeguimiento;
})();
