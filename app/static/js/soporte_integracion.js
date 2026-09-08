/* Panel de soporte — configurar integraciones (facturador / pasarela). */
let _TIPO = 'facturador';
let _ITEMS = [];

function _val(id) { const e = document.getElementById(id); return e ? e.value.trim() : ''; }
function _set(id, v) { const e = document.getElementById(id); if (e) e.value = v || ''; }
function _chk(id, v) { const e = document.getElementById(id); if (e) e.checked = !!v; }
function _msg(t, tipo) { const m = document.getElementById('msg'); m.textContent = t; m.className = 'msg show ' + (tipo || 'ok'); }

async function initIntegracion(tipo) {
    _TIPO = tipo;
    try {
        const r = await fetch(`/soporte/api/integracion/${tipo}`);
        if (r.status === 401) { location.href = '/soporte/login'; return; }
        _ITEMS = (await r.json()).items || [];
    } catch (e) { _ITEMS = []; }
    cargarProveedor();
}

function cargarProveedor() {
    const prov = _val('proveedor');
    const row = _ITEMS.find(i => i.proveedor === prov);
    _set('url_produccion', row?.url_produccion);
    _set('url_sandbox', row?.url_sandbox);
    _set('url_webhook', row?.url_webhook);
    _set('merchant_id', row?.merchant_id);
    _chk('modo_sandbox', row ? row.modo_sandbox : true);
    _chk('activo', row ? row.activo : false);
    // Credenciales: nunca se muestran; el placeholder indica si ya hay una guardada
    ['api_key', 'api_secret'].forEach(id => {
        const e = document.getElementById(id); if (!e) return;
        e.value = '';
        const set = id === 'api_key' ? row?.api_key_set : row?.api_secret_set;
        e.placeholder = set ? '•••••• (configurado — dejar en blanco para conservar)' : '(vacío)';
    });
}

function _payload() {
    return {
        proveedor: _val('proveedor'),
        url_produccion: _val('url_produccion'),
        url_sandbox: _val('url_sandbox'),
        url_webhook: _val('url_webhook'),
        merchant_id: _val('merchant_id'),
        api_key: _val('api_key'),
        api_secret: _val('api_secret'),
        modo_sandbox: document.getElementById('modo_sandbox')?.checked || false,
        activo: document.getElementById('activo')?.checked || false,
    };
}

async function guardar() {
    try {
        const r = await fetch(`/soporte/api/integracion/${_TIPO}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(_payload())
        });
        if (r.status === 401) { location.href = '/soporte/login'; return; }
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Error al guardar');
        // refrescar cache local
        const idx = _ITEMS.findIndex(i => i.proveedor === d.integracion.proveedor);
        if (idx >= 0) _ITEMS[idx] = d.integracion; else _ITEMS.push(d.integracion);
        // si se activó, los demás quedan inactivos
        if (d.integracion.activo) _ITEMS.forEach(i => { if (i.proveedor !== d.integracion.proveedor) i.activo = false; });
        cargarProveedor();
        _msg('Guardado correctamente' + (d.integracion.activo ? ' (proveedor activo)' : ''), 'ok');
    } catch (e) { _msg(e.message, 'err'); }
}

async function probar() {
    try {
        const r = await fetch(`/soporte/api/probar-conexion/${_TIPO}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(_payload())
        });
        if (r.status === 401) { location.href = '/soporte/login'; return; }
        const d = await r.json();
        _msg(d.mensaje, d.ok ? 'ok' : 'err');
    } catch (e) { _msg('No se pudo probar la conexión', 'err'); }
}

window.cargarProveedor = cargarProveedor; window.guardar = guardar; window.probar = probar; window.initIntegracion = initIntegracion;
