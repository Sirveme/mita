/**
 * MITA Maps (zMita-15) — módulo unificado de Google Maps.
 * Carga la API key desde /api/v1/maps/config e inyecta el script de Maps en runtime.
 *   window.MitaMaps.{ inicializarGoogleMaps, inicializarAutocomplete,
 *                     obtenerDireccionSeleccionada, iniciarSeguimientoTecnico,
 *                     detenerSeguimientoTecnico, iniciarEnvioUbicacion, detenerEnvioUbicacion }
 * Degrada sin romper si no hay API key o el navegador no soporta geolocalización.
 */
(function () {
    'use strict';

    let mapsInitialized = false;
    let mapsLoading = null;   // Promesa de carga en curso

    const MITA_MAP_STYLE = [
        { elementType: 'geometry', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#8a8a9a' }] },
        { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2a2a4e' }] },
        { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#1a1a2e' }] },
        { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#3a3a5e' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e0e1a' }] },
        { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#252542' }] },
        { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#1a3a2a' }] }
    ];

    async function cargarConfigMaps() {
        try {
            const resp = await fetch('/api/v1/maps/config');
            if (!resp.ok) return null;
            return await resp.json();
        } catch (e) { return null; }
    }

    function inicializarGoogleMaps(callback) {
        if (mapsInitialized) { if (callback) callback(true); return Promise.resolve(true); }
        if (mapsLoading) { if (callback) mapsLoading.then(callback); return mapsLoading; }
        mapsLoading = (async () => {
            if (window.google && window.google.maps) { mapsInitialized = true; return true; }
            const config = await cargarConfigMaps();
            if (!config || !config.api_key) { console.warn('[MitaMaps] Sin API key; mapas deshabilitados.'); return false; }
            return await new Promise((resolve) => {
                window.onGoogleMapsLoaded = function () { mapsInitialized = true; resolve(true); };
                const s = document.createElement('script');
                s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(config.api_key)}&libraries=places&callback=onGoogleMapsLoaded&loading=async`;
                s.async = true; s.defer = true;
                s.onerror = () => { console.warn('[MitaMaps] no se pudo cargar Google Maps.'); resolve(false); };
                document.head.appendChild(s);
            });
        })();
        mapsLoading.then((ok) => { if (callback) callback(ok); });
        return mapsLoading;
    }

    // ---------- Autocomplete ----------
    let autocompleteInstance = null;
    let direccionSeleccionada = null;
    let mapaConfirmacion = null, markerConfirmacion = null;

    const normalizar = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();

    function extraerDistrito(components) {
        const tipos = ['locality', 'sublocality_level_1', 'administrative_area_level_2', 'administrative_area_level_3'];
        for (const t of tipos) {
            const c = (components || []).find(x => (x.types || []).includes(t));
            if (c) return c.longText || c.long_name || c.shortText || c.short_name;
        }
        return 'Desconocido';
    }
    function validarDistrito(g, sel) {
        if (!sel) return true;
        const a = normalizar(g), b = normalizar(sel);
        return a.includes(b) || b.includes(a) || a === b;
    }
    function mostrarError(msg) {
        let d = document.getElementById('error-direccion');
        if (!d) {
            d = document.createElement('div'); d.id = 'error-direccion'; d.className = 'error-direccion';
            const inp = document.getElementById('input-direccion') || document.getElementById('v-direccion');
            if (inp && inp.parentNode) inp.parentNode.appendChild(d);
        }
        d.textContent = msg; d.style.display = 'block';
    }
    function ocultarError() { const d = document.getElementById('error-direccion'); if (d) d.style.display = 'none'; }

    function mostrarEnMapaConfirmacion(containerId, dir) {
        const cont = document.getElementById(containerId);
        if (!cont || !window.google) return;
        cont.style.display = 'block'; cont.classList.add('visible');
        const loc = { lat: dir.lat, lng: dir.lng };
        if (!mapaConfirmacion) {
            mapaConfirmacion = new google.maps.Map(cont, { zoom: 17, center: loc, disableDefaultUI: true, zoomControl: true, styles: MITA_MAP_STYLE });
            markerConfirmacion = new google.maps.Marker({
                position: loc, map: mapaConfirmacion, title: 'Tu ubicación',
                icon: { path: google.maps.SymbolPath.CIRCLE, scale: 12, fillColor: '#22c55e', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 3 }
            });
        } else { mapaConfirmacion.setCenter(loc); markerConfirmacion.setPosition(loc); }
    }

    // Extrae lat/lng de un place (location con métodos o números)
    function _latlng(place) {
        const loc = place && place.location; if (!loc) return null;
        return { lat: typeof loc.lat === 'function' ? loc.lat() : loc.lat, lng: typeof loc.lng === 'function' ? loc.lng() : loc.lng };
    }
    async function _resolverPlace(pac, ev) {
        try {
            if (ev && ev.placePrediction && typeof ev.placePrediction.toPlace === 'function') {
                const p = ev.placePrediction.toPlace();
                await p.fetchFields({ fields: ['addressComponents', 'formattedAddress', 'location'] });
                return p;
            }
        } catch (e) { /* siguiente forma */ }
        try {
            const v = pac && pac.value;
            if (v && typeof v.fetchFields === 'function') { const r = await v.fetchFields({ fields: ['addressComponents', 'formattedAddress', 'location'] }); return (r && r.place) ? r.place : v; }
            return v || null;
        } catch (e) { return null; }
    }

    // PlaceAutocompleteElement (nueva API, zMita-16)
    function inicializarAutocomplete(inputId, distritoSelectId, mapaContainerId, onDireccionValida) {
        const input = document.getElementById(inputId);
        const distritoSelect = document.getElementById(distritoSelectId);
        const places = window.google && google.maps && google.maps.places;
        if (!input || !places || !places.PlaceAutocompleteElement) { console.warn('[MitaMaps] autocomplete no disponible.'); return; }
        let pac;
        try { pac = new places.PlaceAutocompleteElement({ includedRegionCodes: ['pe'], types: ['address'] }); }
        catch (e) { console.warn('[MitaMaps] no se pudo crear el autocomplete:', e); return; }
        pac.style.width = '100%';
        input.style.display = 'none';
        input.parentNode.insertBefore(pac, input.nextSibling);
        autocompleteInstance = pac;
        const handler = async (ev) => {
            const place = await _resolverPlace(pac, ev);
            const ll = place && _latlng(place);
            if (!place || !ll || ll.lat == null) { mostrarError('Dirección no válida. Selecciona una de la lista.'); return; }
            const gDistrito = extraerDistrito(place.addressComponents || place.address_components);
            const selTxt = distritoSelect ? (distritoSelect.options[distritoSelect.selectedIndex]?.text || '') : '';
            if (selTxt && !validarDistrito(gDistrito, selTxt)) {
                mostrarError(`La dirección está en ${gDistrito}, pero seleccionaste ${selTxt}.`); return;
            }
            direccionSeleccionada = {
                direccion_completa: place.formattedAddress || place.formatted_address || '',
                lat: ll.lat, lng: ll.lng, distrito_google: gDistrito
            };
            if (input) input.value = direccionSeleccionada.direccion_completa;
            if (mapaContainerId) mostrarEnMapaConfirmacion(mapaContainerId, direccionSeleccionada);
            ocultarError();
            if (onDireccionValida) onDireccionValida(direccionSeleccionada);
        };
        pac.addEventListener('gmp-select', handler);
        pac.addEventListener('gmpx-placechange', handler);
    }
    function obtenerDireccionSeleccionada() { return direccionSeleccionada; }

    // ---------- Seguimiento (cliente ve al técnico) ----------
    let mapaSeg = null, mCliente = null, mTecnico = null, dirSvc = null, dirRender = null, intervaloSeg = null;

    function iniciarSeguimientoTecnico(containerId, solicitudId, clienteLat, clienteLng, onUpdate) {
        const cont = document.getElementById(containerId);
        if (!cont) return;
        if (!window.google) { cont.innerHTML = '<div style="padding:24px;text-align:center;color:#8a8a9a;">Mapa no disponible.</div>'; return; }
        const cPos = { lat: clienteLat, lng: clienteLng };
        mapaSeg = new google.maps.Map(cont, { zoom: 15, center: cPos, disableDefaultUI: true, zoomControl: true, styles: MITA_MAP_STYLE });
        if (Number.isFinite(clienteLat)) {
            mCliente = new google.maps.Marker({ position: cPos, map: mapaSeg, title: 'Tu ubicación',
                icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: '#22c55e', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 } });
        }
        mTecnico = new google.maps.Marker({ map: mapaSeg, title: 'Técnico en camino',
            icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 6, fillColor: '#FFCD11', fillOpacity: 1, strokeColor: '#000', strokeWeight: 2, rotation: 0 } });
        dirSvc = new google.maps.DirectionsService();
        dirRender = new google.maps.DirectionsRenderer({ map: mapaSeg, suppressMarkers: true,
            polylineOptions: { strokeColor: '#FFCD11', strokeWeight: 4, strokeOpacity: 0.8 } });
        actualizar(solicitudId, clienteLat, clienteLng, onUpdate);
        intervaloSeg = setInterval(() => actualizar(solicitudId, clienteLat, clienteLng, onUpdate), 5000);
    }
    async function actualizar(solicitudId, clienteLat, clienteLng, onUpdate) {
        try {
            const data = await (await fetch(`/api/v1/maps/solicitudes/${solicitudId}/ubicacion-tecnico`)).json();
            if (!data.disponible) { if (onUpdate) onUpdate({ disponible: false, mensaje: 'Esperando ubicación…' }); return; }
            const tPos = { lat: data.lat, lng: data.lng };
            mTecnico.setPosition(tPos);
            if (data.rumbo != null) { const ic = mTecnico.getIcon(); ic.rotation = data.rumbo; mTecnico.setIcon(ic); }
            if (Number.isFinite(clienteLat) && Number.isFinite(clienteLng)) {
                calcularRuta(tPos, { lat: clienteLat, lng: clienteLng }, onUpdate);
                const b = new google.maps.LatLngBounds(); b.extend(tPos); b.extend({ lat: clienteLat, lng: clienteLng });
                mapaSeg.fitBounds(b, 60);
            } else { mapaSeg.setCenter(tPos); }
        } catch (e) { /* reintenta */ }
    }
    function calcularRuta(origen, destino, onUpdate) {
        dirSvc.route({ origin: origen, destination: destino, travelMode: google.maps.TravelMode.DRIVING }, (res, status) => {
            if (status === 'OK') {
                dirRender.setDirections(res);
                const leg = res.routes[0].legs[0];
                if (onUpdate) onUpdate({ disponible: true, duracion: leg.duration.text, duracion_segundos: leg.duration.value, distancia: leg.distance.text, distancia_metros: leg.distance.value });
            }
        });
    }
    function detenerSeguimientoTecnico() { if (intervaloSeg) { clearInterval(intervaloSeg); intervaloSeg = null; } }

    // ---------- Envío de ubicación (técnico) ----------
    let watchId = null, solicitudActiva = null, ultimoEnvio = 0;
    const MIN_MS = 8000;

    async function iniciarEnvioUbicacion(solicitudId) {
        if (!solicitudId || !('geolocation' in navigator)) return false;
        if (watchId !== null && solicitudActiva === solicitudId) return true;
        detenerEnvioUbicacion();
        solicitudActiva = solicitudId;
        try {
            if (navigator.permissions && navigator.permissions.query) {
                const p = await navigator.permissions.query({ name: 'geolocation' });
                if (p.state === 'denied') { console.warn('[MitaMaps] ubicación denegada.'); return false; }
            }
        } catch (e) { /* sin permissions API */ }
        watchId = navigator.geolocation.watchPosition(enviar,
            (err) => console.warn('[MitaMaps] GPS:', err && err.message),
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 });
        return true;
    }
    async function enviar(position) {
        if (!solicitudActiva) return;
        const ahora = Date.now(); if (ahora - ultimoEnvio < MIN_MS) return; ultimoEnvio = ahora;
        const c = position.coords;
        try {
            await fetch(`/api/v1/maps/solicitudes/${solicitudActiva}/ubicacion-tecnico`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: c.latitude, lng: c.longitude, precision: c.accuracy, velocidad: c.speed, rumbo: c.heading })
            });
        } catch (e) { /* reintenta */ }
    }
    function detenerEnvioUbicacion() {
        if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
        solicitudActiva = null;
    }

    window.MitaMaps = {
        inicializarGoogleMaps,
        inicializarAutocomplete, obtenerDireccionSeleccionada,
        iniciarSeguimientoTecnico, detenerSeguimientoTecnico,
        iniciarEnvioUbicacion, detenerEnvioUbicacion
    };
})();
