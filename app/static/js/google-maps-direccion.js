/*
 * Validación de dirección con Google Maps usando PlaceAutocompleteElement
 * (nueva API, obligatoria para cuentas GCP creadas después de marzo 2025 — zMita-16).
 *
 * Mantiene la API pública:
 *   MitaDireccion.init({
 *     inputId:'v-direccion', distritoId:'v-distrito', mapaId:'v-mapa-confirmacion',
 *     onValid:(info)=>{...}, onError:(msg)=>{...},
 *     cobertura:[...opcional], contexto:()=>({area_servicio_id,problema_id,descripcion})  // opcional
 *   });
 * Valida cobertura del distrito y registra los intentos sin cobertura para análisis.
 * Degrada sin romper si Google Maps no está disponible.
 */
(function () {
    'use strict';
    const S = { opts: null, pac: null, map: null, marker: null, coords: null, distritoOk: false, last: null };

    // Distritos con cobertura MITA (fallback; se puede sobreescribir con opts.cobertura)
    const DISTRITOS_COBERTURA = [
        'miraflores', 'san isidro', 'surco', 'santiago de surco', 'san borja', 'la molina',
        'barranco', 'surquillo', 'jesus maria', 'lince', 'magdalena', 'magdalena del mar',
        'pueblo libre', 'san miguel', 'lima', 'cercado de lima'
    ];

    const darkMapStyle = [
        { elementType: 'geometry', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#1a1a2e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#8a8a9a' }] },
        { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2a2a4e' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e0e1a' }] }
    ];

    function homeIcon() {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
            <path d="M20 2 C11 2 4 9 4 18 c0 11 16 20 16 20 s16-9 16-20 C36 9 29 2 20 2z" fill="#22c55e"/>
            <path d="M20 11 l7 6 v9 h-4 v-6 h-6 v6 h-4 v-9z" fill="#0e1726"/></svg>`;
        return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg);
    }

    const norm = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();

    // Soporta tanto la nueva API (types/longText/shortText) como la antigua (long_name)
    function extraerDistrito(components) {
        const pref = ['locality', 'sublocality_level_1', 'administrative_area_level_2', 'administrative_area_level_3'];
        for (const t of pref) {
            const c = (components || []).find(x => (x.types || []).includes(t));
            if (c) return c.longText || c.long_name || c.shortText || c.short_name || null;
        }
        return null;
    }

    function tieneCobertura(gDistrito) {
        const n = norm(gDistrito);
        if (!n) return true; // si no se pudo detectar, no bloquear
        const lista = (S.opts.cobertura && S.opts.cobertura.length) ? S.opts.cobertura.map(norm) : DISTRITOS_COBERTURA;
        return lista.some(d => n.includes(d) || d.includes(n));
    }

    function coincideDistrito(gDistrito, seleccionado) {
        if (!gDistrito || !seleccionado) return true;
        const a = norm(gDistrito), b = norm(seleccionado);
        return a.includes(b) || b.includes(a);
    }

    function distritoSeleccionado() {
        const sel = S.opts.distritoId && document.getElementById(S.opts.distritoId);
        if (!sel) return '';
        const opt = sel.options[sel.selectedIndex];
        return (opt ? (opt.text || opt.value) : '').trim();
    }

    function pintarMapa(location) {
        const cont = S.opts.mapaId && document.getElementById(S.opts.mapaId);
        if (!cont || !window.google) return;
        cont.style.display = '';
        if (!S.map) {
            S.map = new google.maps.Map(cont, { zoom: 16, center: location, disableDefaultUI: true, styles: darkMapStyle });
            S.marker = new google.maps.Marker({ position: location, map: S.map, icon: { url: homeIcon(), scaledSize: new google.maps.Size(40, 40) } });
        } else { S.map.setCenter(location); S.marker.setPosition(location); }
    }

    async function registrarSinCobertura(distrito) {
        try {
            const ctx = (typeof S.opts.contexto === 'function') ? (S.opts.contexto() || {}) : {};
            await fetch('/api/v1/maps/sin-cobertura', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    distrito_solicitado: distrito || 'Desconocido',
                    direccion_ingresada: S.last ? S.last.formatted : null,
                    lat: S.last ? S.last.lat : null, lng: S.last ? S.last.lng : null,
                    area_servicio_id: ctx.area_servicio_id || null,
                    problema_id: ctx.problema_id || null,
                    descripcion: ctx.descripcion || null
                })
            });
        } catch (e) { /* registro opcional */ }
    }

    function fail(msg) {
        S.coords = null; S.distritoOk = false;
        if (typeof S.opts.onError === 'function') S.opts.onError(msg);
    }

    // Extrae lat/lng de un place tanto si location expone métodos como números
    function latlng(place) {
        const loc = place && place.location;
        if (!loc) return null;
        const lat = typeof loc.lat === 'function' ? loc.lat() : loc.lat;
        const lng = typeof loc.lng === 'function' ? loc.lng() : loc.lng;
        return { lat, lng };
    }

    async function resolverPlace(ev) {
        // Nueva API: evento gmp-select con placePrediction.toPlace()
        try {
            if (ev && ev.placePrediction && typeof ev.placePrediction.toPlace === 'function') {
                const place = ev.placePrediction.toPlace();
                await place.fetchFields({ fields: ['addressComponents', 'formattedAddress', 'location'] });
                return place;
            }
        } catch (e) { /* probar siguiente forma */ }
        // API intermedia: el elemento expone .value con fetchFields
        try {
            const v = S.pac && S.pac.value;
            if (v) {
                if (typeof v.fetchFields === 'function') {
                    const r = await v.fetchFields({ fields: ['addressComponents', 'formattedAddress', 'location'] });
                    return (r && r.place) ? r.place : v;
                }
                return v;
            }
        } catch (e) { /* nada */ }
        return null;
    }

    async function onSelect(ev) {
        const place = await resolverPlace(ev);
        if (!place) { fail('Elige una dirección de la lista de sugerencias.'); return; }
        const ll = latlng(place);
        if (!ll || ll.lat == null) { fail('No pudimos ubicar esa dirección. Intenta de nuevo.'); return; }
        const comps = place.addressComponents || place.address_components || [];
        const gDistrito = extraerDistrito(comps);
        const formatted = place.formattedAddress || place.formatted_address || '';
        S.last = { lat: ll.lat, lng: ll.lng, formatted, distrito: gDistrito };

        // 1) Cobertura
        if (!tieneCobertura(gDistrito)) {
            fail(`Sin cobertura en ${gDistrito || 'ese distrito'}. Registramos tu interés para expandirnos pronto.`);
            registrarSinCobertura(gDistrito);
            return;
        }
        // 2) Coincidencia con el distrito seleccionado (si hay)
        const sel = distritoSeleccionado();
        if (sel && !coincideDistrito(gDistrito, sel)) {
            fail(`La dirección está en ${gDistrito || 'otro distrito'}, pero seleccionaste ${sel}.`);
            return;
        }
        // 3) OK
        S.coords = { lat: ll.lat, lng: ll.lng };
        S.distritoOk = true;
        // Mantener el input original poblado para el resto del flujo
        const input = S.opts.inputId && document.getElementById(S.opts.inputId);
        if (input) input.value = formatted;
        pintarMapa(ll);
        if (typeof S.opts.onValid === 'function') S.opts.onValid({ coords: S.coords, formatted, distrito: gDistrito });
    }

    const MitaDireccion = {
        init(opts) {
            S.opts = opts || {};
            const input = document.getElementById(S.opts.inputId);
            if (!input) return false;
            const places = window.google && google.maps && google.maps.places;
            if (!places || !places.PlaceAutocompleteElement) {
                console.warn('[MitaDireccion] PlaceAutocompleteElement no disponible; dirección manual.');
                return false;
            }
            if (S.pac) return true; // ya inicializado
            let pac;
            try {
                pac = new places.PlaceAutocompleteElement({ includedRegionCodes: ['pe'], types: ['address'] });
            } catch (e) {
                try { pac = new places.PlaceAutocompleteElement({ componentRestrictions: { country: 'pe' } }); }
                catch (e2) { console.warn('[MitaDireccion] no se pudo crear el autocomplete:', e2); return false; }
            }
            pac.style.width = '100%';
            pac.style.cssText += ';--gmpx-color-surface:#151520;--gmpx-color-on-surface:#e9edef;--gmpx-color-primary:#FFCD11;';
            // Insertar el elemento junto al input y ocultar el input (se usa como almacén de valor)
            input.style.display = 'none';
            input.parentNode.insertBefore(pac, input.nextSibling);
            S.pac = pac;
            pac.addEventListener('gmp-select', onSelect);        // API actual
            pac.addEventListener('gmpx-placechange', onSelect);  // fallback versiones previas
            const sel = document.getElementById(S.opts.distritoId);
            if (sel) sel.addEventListener('change', () => { if (S.last) onSelect({}); });
            return true;
        },
        getCoords() { return S.coords; },
        distritoValido() { return S.distritoOk; },
        reset() { S.coords = null; S.distritoOk = false; S.last = null; }
    };

    window.MitaDireccion = MitaDireccion;
    // Callback del script de Maps (&callback=initAutocomplete)
    window.initAutocomplete = window.initAutocomplete || function () {
        document.dispatchEvent(new CustomEvent('mita-maps-ready'));
    };
})();
