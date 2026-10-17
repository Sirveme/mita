/* =========================================================================
   MITA — camino único post-"Confirmar" (zMita-43, Parte A).
   Lo usan LAS DOS entradas (chat con IA y formulario/wizard): el MISMO código.
   crear solicitud → método de pago → /pagar (QR) o /pagos/efectivo → paso de
   avisos → (el backend difunde) → Buscando técnico → seguimiento.
   ========================================================================= */
window.MitaFlujo = (function () {
    'use strict';

    async function configQR() {
        try { return !!(await (await fetch('/api/v1/pagos-qr/config')).json()).habilitado; }
        catch (e) { return false; }
    }

    // POST /api/v1/solicitudes — devuelve el id. `datos` es el payload común
    // (problema, categoria_id, direccion, distrito, referencia, lat, lng, metodo_pago, ...).
    async function crearSolicitud(datos) {
        const r = await fetch('/api/v1/solicitudes', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos)
        });
        const d = await r.json();
        if (!r.ok || !d.id) throw new Error('No se pudo crear la solicitud');
        return d.id;
    }

    function irAPagarQR(id) { window.location.href = '/pagar/' + id; }

    // Efectivo: el backend marca el método y DIFUNDE a los técnicos (ofertas.difundir).
    async function pagarEfectivo(id) {
        try {
            await fetch('/api/v1/pagos/efectivo', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ solicitud_id: id })
            });
        } catch (e) {}
    }

    // Paso de avisos (zMita-35) y luego a la pantalla del servicio (Buscando técnico → seguimiento).
    function pasoAvisosYSeguir(id) {
        const ir = () => { window.location.href = '/cliente/servicio/' + id + '/chats'; };
        if (window.MitaPWA && window.MitaPWA.pasoAvisos) {
            window.MitaPWA.pasoAvisos({ solicitud_id: id, codigo: '#' + id, onListo: ir });
        } else { setTimeout(ir, 1600); }
    }

    // Camino de pago completo (idéntico para ambas entradas).
    async function pagar(id, metodo) {
        if (metodo === 'qr') { irAPagarQR(id); return; }
        await pagarEfectivo(id);
        pasoAvisosYSeguir(id);
    }

    // ---- Paso "Tu comprobante" (zMita-44): entre crear solicitud y método de pago ----
    function _css() {
        if (document.getElementById('mf-css')) return;
        if (!document.querySelector('link[href*="mita.css"]')) {
            var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '/static/css/mita.css'; document.head.appendChild(l);
        }
        var s = document.createElement('style'); s.id = 'mf-css';
        s.textContent = '#mf-ov{position:fixed;inset:0;z-index:9999;background:var(--mita-bg,#0e0e1a);color:var(--mita-text,#e9edef);'
            + 'font-family:var(--mita-font,system-ui);overflow-y:auto;display:flex;flex-direction:column}'
            + '#mf-ov .mf-wrap{max-width:520px;margin:0 auto;width:100%;flex:1;display:flex;flex-direction:column}'
            + '#mf-ov .mf-body{padding:16px 16px 100px}'
            + '#mf-ov .mf-seg{display:flex;gap:8px;margin-bottom:14px}'
            + '#mf-ov .mf-seg button{flex:1;padding:12px;border-radius:12px;border:1px solid var(--mita-border,#2a2a4e);background:var(--mita-surface,#15131f);color:var(--mita-text,#e9edef);font-weight:700;cursor:pointer;font-family:inherit}'
            + '#mf-ov .mf-seg button.on{background:var(--mita-accent,#22c55e);color:var(--mita-accent-ink,#06210f);border-color:var(--mita-accent,#22c55e)}'
            + '#mf-ov label{display:block;color:var(--mita-text-2,#a6a6bd);font-size:12px;margin:12px 0 4px}'
            + '#mf-ov input{width:100%;background:var(--mita-bg,#0e0e1a);border:1px solid var(--mita-border,#2a2a4e);color:var(--mita-text,#e9edef);border-radius:12px;padding:11px 13px;font-family:inherit;font-size:14px}'
            + '#mf-ov .help{color:var(--mita-text-3,#8a8a9a);font-size:12px;margin-top:4px}'
            + '#mf-ov .err{color:var(--mita-error,#ff6b6b);font-size:13px;margin-top:8px;min-height:16px}';
        document.head.appendChild(s);
    }

    async function pedirComprobante(solicitudId) {
        _css();
        var cfg = {};
        try { cfg = await (await fetch('/api/v1/servicios/' + solicitudId + '/comprador')).json(); } catch (e) { cfg = {}; }
        var pre = (cfg.actual && (cfg.actual.doc_numero || cfg.actual.razon_social)) ? cfg.actual : (cfg.recordado || {});
        var total = cfg.total_visita || 50, umbral = cfg.umbral_boleta || 700;
        var tipo = pre.tipo_comprobante || 'boleta';

        return new Promise(function (resolve) {
            var ov = document.createElement('div'); ov.id = 'mf-ov';
            var boletaOblig = total >= umbral;
            ov.innerHTML =
                '<div class="mf-wrap">'
                + '<div class="m-header"><button class="m-back" id="mf-back" aria-label="Regresar">←</button>'
                + '<h1>Tu comprobante<small>Para enviártelo cuando pagues</small></h1></div>'
                + '<div class="m-steps"><span class="s done"></span><span class="s now"></span><span class="s"></span><span class="s"></span><span class="s"></span></div>'
                + '<div class="mf-body">'
                + '<div class="mf-seg"><button type="button" id="mf-boleta">Boleta</button><button type="button" id="mf-factura">Factura</button></div>'
                + '<div id="mf-boleta-f">'
                + '  <label>Tu nombre</label><input id="mf-nombre" placeholder="Nombre y apellido" value="' + (pre.razon_social || cfg.cliente_nombre || '') + '">'
                + '  <label>DNI, CE o pasaporte ' + (boletaOblig ? '(obligatorio)' : '(opcional)') + '</label><input id="mf-doc" placeholder="Documento" value="' + (pre.doc_numero || '') + '">'
                + '  <div class="help">' + (boletaOblig ? 'Por el monto (S/ ' + total.toFixed(2) + ') el documento es obligatorio.' : 'Puedes dejarlo en blanco para montos pequeños.') + '</div>'
                + '</div>'
                + '<div id="mf-factura-f" style="display:none">'
                + '  <label>RUC (11 dígitos)</label><input id="mf-ruc" inputmode="numeric" placeholder="20xxxxxxxxx" value="' + (pre.doc_tipo === 'RUC' ? (pre.doc_numero || '') : '') + '">'
                + '  <label>Razón social</label><input id="mf-razon" placeholder="Se completa con el RUC" value="' + (pre.doc_tipo === 'RUC' ? (pre.razon_social || '') : '') + '">'
                + '  <label>Dirección fiscal</label><input id="mf-dir" placeholder="Se completa con el RUC" value="' + (pre.direccion_fiscal || '') + '">'
                + '</div>'
                + '<div class="err" id="mf-err"></div>'
                + '</div>'
                + '<div class="m-actions"><button class="m-btn" id="mf-cont">Continuar</button></div>'
                + '</div>';
            document.body.appendChild(ov);
            var $ = function (id) { return ov.querySelector('#' + id); };
            function setTipo(t) {
                tipo = t;
                $('mf-boleta').classList.toggle('on', t === 'boleta');
                $('mf-factura').classList.toggle('on', t === 'factura');
                $('mf-boleta-f').style.display = t === 'boleta' ? '' : 'none';
                $('mf-factura-f').style.display = t === 'factura' ? '' : 'none';
            }
            setTipo(tipo);
            $('mf-boleta').addEventListener('click', function () { setTipo('boleta'); });
            $('mf-factura').addEventListener('click', function () { setTipo('factura'); });
            // Factura: autocompletar con el RUC (consulta sunat)
            $('mf-ruc').addEventListener('blur', async function () {
                var ruc = $('mf-ruc').value.trim(); if (ruc.length !== 11) return;
                try {
                    var d = await (await fetch('/api/v1/identificacion/consulta?tipo=RUC&numero=' + ruc)).json();
                    if (d.ok && d.razon_social) { $('mf-razon').value = d.razon_social; if (d.direccion) $('mf-dir').value = d.direccion; }
                    else $('mf-err').textContent = 'No pudimos consultar el RUC; escribe la razón social a mano.';
                } catch (e) {}
            });
            function cerrar() { ov.remove(); }
            $('mf-back').addEventListener('click', function () { cerrar(); resolve({ volver: true }); });
            $('mf-cont').addEventListener('click', async function () {
                $('mf-err').textContent = '';
                var body = { tipo_comprobante: tipo, total: total };
                if (tipo === 'factura') {
                    body.doc_tipo = 'RUC'; body.doc_numero = $('mf-ruc').value.trim();
                    body.razon_social = $('mf-razon').value.trim(); body.direccion_fiscal = $('mf-dir').value.trim();
                } else {
                    body.razon_social = $('mf-nombre').value.trim();
                    var doc = $('mf-doc').value.trim();
                    if (doc) { body.doc_numero = doc; body.doc_tipo = /^\d{8}$/.test(doc) ? 'DNI' : (/^\d{11}$/.test(doc) ? 'RUC' : 'CE'); }
                }
                var btn = $('mf-cont'); btn.disabled = true;
                try {
                    var r = await fetch('/api/v1/servicios/' + solicitudId + '/comprador', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
                    });
                    if (r.ok) { cerrar(); resolve({ ok: true }); return; }
                    var e = await r.json().catch(function () { return {}; });
                    $('mf-err').textContent = e.detail || 'Revisa los datos.';
                } catch (e) { $('mf-err').textContent = 'No se pudo guardar. Intenta de nuevo.'; }
                btn.disabled = false;
            });
        });
    }

    return { configQR, crearSolicitud, irAPagarQR, pagarEfectivo, pasoAvisosYSeguir, pagar, pedirComprobante };
})();
