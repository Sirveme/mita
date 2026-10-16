"""
PagoOK — validación de pagos Yape/Plin por CONSULTA (pull), zMita-34 v2.

Contrato: docs/consulta-pagos-v1.md. Autenticación por header X-API-Key. Nunca webhook.
  - consultar()     -> POST /pagos/consultar
  - marcar_usado()  -> POST /pagos/{id}/marcar-usado   (SIEMPRE antes de dar por pagada)
  - verificar_pago()-> orquesta una vuelta: consulta, decide por nivel, marca y cobra.

Protecciones (límite PagoOK 120 consultas/min por credencial):
  - 1 sola consulta EN VUELO por solicitud.
  - intervalo mínimo entre consultas de una misma solicitud.
  - 429 -> backoff 15s, 30s, 60s.
  - ventana de validez: 10 min desde "Ya pagué".
"""
import time
import json
import logging
import threading
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger("mita.pagook")

VENTANA_MAX_MIN = 10
_MIN_INTERVALO = 6.0
_BACKOFF_PASOS = [15, 30, 60]

_LOCK = threading.Lock()
_EN_VUELO = set()      # solicitud_ids con una consulta en curso
_ULTIMA = {}           # solicitud_id -> ts de la última consulta
_BACKOFF = {}          # solicitud_id -> (hasta_ts, paso_idx)
_MINUTO = {"t": 0, "n": 0}


def configurado() -> bool:
    return bool(settings.PAGOOK_API_KEY)


def presion_alta() -> bool:
    """True si vamos por encima de 90 consultas/min (de 120): alargar la cadencia a 10 s."""
    m = int(time.time() // 60)
    return _MINUTO["t"] == m and _MINUTO["n"] > 90


def _headers():
    return {"X-API-Key": settings.PAGOOK_API_KEY or "", "Content-Type": "application/json"}


def _base():
    return (settings.PAGOOK_BASE_URL or "https://pagook.pro/api/v1").rstrip("/")


def _cuenta_minuto():
    m = int(time.time() // 60)
    if _MINUTO["t"] != m:
        _MINUTO["t"] = m
        _MINUTO["n"] = 0
    _MINUTO["n"] += 1
    if _MINUTO["n"] % 20 == 0 or _MINUTO["n"] > 100:
        logger.info("[pagook] consultas este minuto: %s (límite 120)", _MINUTO["n"])


def consultar(monto, fecha_hora_declarada, canal=None, nombre_pagador_declarado=None,
              codigo_operacion=None, ventana_minutos=15) -> dict:
    """POST /pagos/consultar. Devuelve {status, body} (body=dict de la respuesta)."""
    import httpx
    cuerpo = {"monto": monto, "fecha_hora_declarada": fecha_hora_declarada,
              "ventana_minutos": ventana_minutos}
    if canal:
        cuerpo["canal"] = canal
    if nombre_pagador_declarado:
        cuerpo["nombre_pagador_declarado"] = nombre_pagador_declarado
    if codigo_operacion:
        cuerpo["codigo_operacion"] = codigo_operacion
    _cuenta_minuto()
    try:
        r = httpx.post(f"{_base()}/pagos/consultar", headers=_headers(), json=cuerpo, timeout=10)
    except Exception as e:
        logger.warning("[pagook] consultar red: %s", e)
        return {"status": 0, "error": str(e)}
    try:
        data = r.json()
    except Exception:
        data = {}
    return {"status": r.status_code, "body": data}


def marcar_usado(pago_id, referencia_externa, sistema="Mita.pe") -> dict:
    """POST /pagos/{id}/marcar-usado. Devuelve {status, body}. 200 ok, 409 conflicto, 404 no existe."""
    import httpx
    try:
        r = httpx.post(f"{_base()}/pagos/{pago_id}/marcar-usado", headers=_headers(),
                       json={"referencia_externa": referencia_externa, "sistema": sistema}, timeout=10)
    except Exception as e:
        logger.warning("[pagook] marcar-usado red: %s", e)
        return {"status": 0, "error": str(e)}
    try:
        data = r.json()
    except Exception:
        data = {}
    return {"status": r.status_code, "body": data}


# ----------------------------------------------------------------------------
def _lima_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "-05:00"


def _resp(ps, mensaje=None, extra=None):
    out = {"estado": ps.estado, "nivel": ps.nivel, "pagada": ps.estado == "pagada",
           "posible_reuso": bool(ps.posible_reuso),
           "comprobante_estado": ps.comprobante_estado, "mensaje": mensaje}
    if extra:
        out.update(extra)
    return out


def _alerta_torre(texto):
    # La torre de control lee estos avisos del log y del panel /admin/pagos-qr
    logger.warning("[pagook][TORRE] %s", texto)


# ----------------------------------------------------------------------------
# Puntaje de nombre con contraparte ENMASCARADA (zMita-36 Parte C)
# ----------------------------------------------------------------------------
import re as _re
import unicodedata as _ud


def _palabras(s: str):
    s = (s or "")
    s = "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn").lower()
    s = s.replace(".", " ")
    return [w for w in s.split() if w]


def puntaje_nombre(declarado: str, contraparte: str):
    """Devuelve (puntaje:int, tiene_completa:bool).

    Compara cualquier palabra con cualquiera, sin orden; cada palabra del declarado se usa
    una sola vez. Palabra completa de la contraparte: compatible si es igual a una del
    declarado. Palabra enmascarada/truncada (Per*, P***, P): compatible si su prefijo visible
    es prefijo de una palabra del declarado. Las coincidencias solo por inicial cuentan 1 como
    máximo en total."""
    decl = _palabras(declarado)
    # separar por espacios conservando los '*' para detectar enmascaradas
    cont_raw = [w for w in _re.sub(r"\s+", " ",
                (("".join(c for c in _ud.normalize("NFD", contraparte or "") if _ud.category(c) != "Mn")
                  ).lower().replace(".", " "))).split() if w]
    usados = [False] * len(decl)
    puntaje = 0
    completas = 0
    por_inicial = 0
    for w in cont_raw:
        limpio = w.replace("*", "")
        if not limpio:
            continue
        enmascarada = ("*" in w) or (len(limpio) == 1)
        mejor = -1
        completa_match = False
        inicial_match = False
        for i, d in enumerate(decl):
            if usados[i]:
                continue
            if not enmascarada:
                if limpio == d:
                    mejor = i; completa_match = True; break
            else:
                if d.startswith(limpio):
                    mejor = i; inicial_match = (len(limpio) == 1)
                    break
        if mejor >= 0:
            usados[mejor] = True
            if completa_match:
                puntaje += 1; completas += 1
            elif inicial_match:
                por_inicial += 1
            else:
                puntaje += 1   # prefijo truncado de 2+ letras
    puntaje += min(por_inicial, 1)
    return puntaje, completas > 0


def _parse_fh(iso: str):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "").split("+")[0].split("-05:00")[0])
    except Exception:
        return None


def _referencia(ps) -> str:
    """MITA-SOL-{id} para la visita; MITA-SOL-{id}-R para la reparación (zMita-40)."""
    base = f"MITA-SOL-{ps.solicitud_id}"
    return base + "-R" if (getattr(ps, "concepto", "visita") == "reparacion") else base


def _otras_esperando(db, ps):
    """Otras solicitudes esperando pago con el MISMO monto y canal, ventana vigente (10 min)."""
    from app.models.pago_solicitud import PagoSolicitud
    limite = datetime.utcnow() - timedelta(minutes=VENTANA_MAX_MIN)
    q = (db.query(PagoSolicitud)
         .filter(PagoSolicitud.id != ps.id,
                 PagoSolicitud.estado.in_(["esperando_pago", "verificando", "media_pendiente"]),
                 PagoSolicitud.canal == ps.canal,
                 PagoSolicitud.monto_esperado == ps.monto_esperado,
                 PagoSolicitud.qr_mostrado_en.isnot(None),
                 PagoSolicitud.qr_mostrado_en > limite))
    return q.all()


def verificar_pago(db, ps, forzar=False, operador=False, voucher=False) -> dict:
    """Una vuelta de verificación para el pago `ps` (PagoSolicitud). Idempotente:
    si ya está pagada, no consulta ni marca de nuevo."""
    if ps.estado == "pagada":
        return _resp(ps, "Pago confirmado.")

    inicio = ps.qr_mostrado_en or ps.fecha_hora_declarada
    vencido = bool(inicio and datetime.utcnow() - inicio > timedelta(minutes=VENTANA_MAX_MIN))

    # Guardas de rate-limit / una sola consulta en vuelo
    with _LOCK:
        if ps.solicitud_id in _EN_VUELO:
            return _resp(ps, "Verificando tu pago…", {"en_vuelo": True})
        bo = _BACKOFF.get(ps.solicitud_id)
        if bo and time.time() < bo[0]:
            return _resp(ps, "Verificando tu pago…", {"backoff": True})
        if not forzar and (time.time() - _ULTIMA.get(ps.solicitud_id, 0)) < _MIN_INTERVALO:
            return _resp(ps, "Verificando tu pago…")
        if vencido and not forzar:
            return _resp(ps, "Aún no vemos tu pago.", {"timeout": True})
        _EN_VUELO.add(ps.solicitud_id)
        _ULTIMA[ps.solicitud_id] = time.time()

    try:
        return _una_consulta(db, ps, operador, voucher=voucher)
    finally:
        with _LOCK:
            _EN_VUELO.discard(ps.solicitud_id)


def _una_consulta(db, ps, operador, voucher=False) -> dict:
    monto = f"{float(ps.monto_esperado or 0):.2f}"
    # fecha_hora_declarada = hora de CADA consulta (o la hora del voucher, caso C2)
    if voucher and ps.hora_voucher:
        cuando = _lima_iso(ps.hora_voucher); ventana = 3
    else:
        cuando = _lima_iso(datetime.utcnow()); ventana = 15
    res = consultar(monto, cuando, canal=ps.canal, nombre_pagador_declarado=ps.titular_declarado,
                    codigo_operacion=ps.codigo_operacion, ventana_minutos=ventana)
    status = res.get("status")
    ps.intentos = (ps.intentos or 0) + 1

    if status == 401:
        _alerta_torre("Credencial PagoOK inválida (401). Revisar PAGOOK_API_KEY.")
        db.commit()
        return _resp(ps, "Estamos verificando tu pago, te avisamos en unos minutos.", {"error": "credencial"})
    if status == 429:
        with _LOCK:
            bo = _BACKOFF.get(ps.solicitud_id)
            paso = min((bo[1] + 1) if bo else 0, len(_BACKOFF_PASOS) - 1)
            _BACKOFF[ps.solicitud_id] = (time.time() + _BACKOFF_PASOS[paso], paso)
        logger.warning("[pagook] 429 sol=%s -> backoff %ss", ps.solicitud_id, _BACKOFF_PASOS[paso])
        db.commit()
        return _resp(ps, "Verificando tu pago…", {"backoff": True})
    if status != 200:
        logger.warning("[pagook] consultar status=%s body=%s", status, str(res.get("body"))[:200])
        db.commit()
        return _resp(ps, "Estamos verificando tu pago…", {"error": str(status)})

    # Éxito del backoff -> limpiar
    with _LOCK:
        _BACKOFF.pop(ps.solicitud_id, None)

    body = res.get("body") or {}
    ps.nivel = body.get("nivel")
    ps.motivo = body.get("motivo")
    ps.respuesta_cruda = json.dumps(body, ensure_ascii=False)[:8000]
    ps.posible_reuso = bool(body.get("pagos_ya_usados"))

    if ps.nivel == "alta":
        return _decidir_alta(db, ps, body, operador, voucher)
    if ps.nivel == "media":
        return _a_media(db, ps, body, "PagoOK nivel media (varios candidatos)")
    # sin_coincidencia
    ps.estado = "verificando"
    if ps.posible_reuso:
        _alerta_torre(f"Posible voucher reutilizado en solicitud #{ps.solicitud_id} (pagos_ya_usados).")
    db.commit()
    return _resp(ps, "Aún no vemos tu pago.", {"sin_coincidencia": True})


def _decidir_alta(db, ps, body, operador, voucher=False) -> dict:
    """Con nombres enmascarados, el nombre es UNA señal. Acepta solo si (Parte C):
    nivel=alta + pago.fecha_hora >= qr_mostrado_en-60s + (A código | B puntaje≥2 único |
    C puntaje≥1 y es la única esperando | D hora_voucher coincide). Si no, pasa a la torre."""
    pago = body.get("pago") or {}
    contraparte = pago.get("contraparte") or ""
    ps.pago_id = pago.get("pago_id")
    ps.contraparte = contraparte
    fh = _parse_fh(pago.get("fecha_hora"))
    ps.fecha_hora_pago = fh

    # El pago no puede ser anterior al QR (−60 s de tolerancia). qr_mostrado_en está en UTC;
    # la fecha_hora de PagoOK viene en hora de Lima (−05:00) -> convertir a UTC (+5 h).
    fh_utc = (fh + timedelta(hours=5)) if fh else None
    if ps.qr_mostrado_en and fh_utc and fh_utc < ps.qr_mostrado_en - timedelta(seconds=60):
        return _a_media(db, ps, body, "pago anterior al QR")

    punt, completa = puntaje_nombre(ps.titular_declarado, contraparte)
    ps.puntaje = punt
    es_codigo = (ps.motivo == "codigo_operacion")
    otras = _otras_esperando(db, ps)

    caso_A = es_codigo
    caso_B = (punt >= 2 and completa and
              not any(puntaje_nombre(o.titular_declarado, contraparte)[0] >= 2 for o in otras))
    # Parte 0.1: además de ser la única solicitud esperando, exigir que sea el ÚNICO pago sin usar
    # en la ventana (PagoOK lo indica con motivo="candidato_unico"; si hubo 2+ pagos -> torre).
    caso_C = (punt >= 1 and len(otras) == 0 and ps.motivo == "candidato_unico")
    caso_D = False
    if voucher and ps.hora_voucher and fh:
        own_diff = abs((fh - ps.hora_voucher).total_seconds())
        cerca = own_diff <= 180
        # Parte 0.2: ninguna otra solicitud esperando con su hora_voucher a <= 2 min de ESTE pago.
        otra_cerca_2min = any(
            o.hora_voucher and abs((fh - o.hora_voucher).total_seconds()) <= 120 for o in otras)
        caso_D = (punt >= 1 or es_codigo) and cerca and not otra_cerca_2min

    if caso_A or caso_B or caso_C or caso_D:
        return _aceptar(db, ps, operador)
    return _a_media(db, ps, body,
                    f"puntaje={punt} completa={completa} otras={len(otras)} -> decide la torre")


def _aceptar(db, ps, operador) -> dict:
    ref = _referencia(ps)
    ps.referencia_externa = ref
    m = marcar_usado(ps.pago_id, ref, sistema="Mita.pe")
    st = m.get("status")
    if st == 200:
        return _al_pagar(db, ps, operador)
    if st == 409:
        ps.estado = "conflicto"
        _alerta_torre(f"marcar-usado 409 solicitud #{ps.solicitud_id}: pago ya registrado en otra operación. "
                      f"detalle={str((m.get('body') or {}).get('detail'))[:120]}")
        db.commit()
        return _resp(ps, "Ese pago ya fue registrado en otra operación. Un asesor te ayudará.", {"conflicto": True})
    logger.warning("[pagook] marcar-usado status=%s sol=%s", st, ps.solicitud_id)
    ps.estado = "verificando"
    db.commit()
    return _resp(ps, "Estamos verificando tu pago…", {"error": str(st)})


def _a_media(db, ps, body, razon) -> dict:
    """La solicitud no se acepta sola: va a la torre con la contraparte tal como llegó."""
    ps.estado = "media_pendiente"
    # Asegurar que la torre vea el/los pago(s) candidato(s) con su contraparte real
    cruda = dict(body)
    if not cruda.get("candidatos") and cruda.get("pago"):
        cruda["candidatos"] = [cruda["pago"]]
    ps.respuesta_cruda = json.dumps(cruda, ensure_ascii=False)[:8000]
    _alerta_torre(f"Pago a revisión solicitud #{ps.solicitud_id}: {razon}. "
                  f"contraparte={ps.contraparte!r} puntaje={ps.puntaje}")
    db.commit()
    return _resp(ps, "Estamos verificando tu pago, te avisamos en unos minutos.", {"media": True})


def _al_pagar(db, ps, operador) -> dict:
    """Pago confirmado. La VISITA marca pagada + difunde a técnicos; la REPARACIÓN
    entra al cierre (zMita-39 B4): PAGADO + comprobante."""
    ps.estado = "pagada"
    ps.confirmado_por = "operador" if operador else "automatico"
    from app.models.solicitud_mita import Solicitud
    sol = db.query(Solicitud).get(ps.solicitud_id)

    if getattr(ps, "concepto", "visita") == "reparacion":
        db.commit()
        if sol:
            try:
                from app.services import cierre
                cierre.confirmar_pago_digital(db, sol)
            except Exception:
                logger.exception("[pagook] cierre reparación")
        return _resp(ps, "¡Pago recibido! Gracias.")

    # --- Visita (flujo original) ---
    if sol:
        sol.estado = "PAGADA"
        sol.pagado = 1
        try:
            sol.pago_confirmado_at = datetime.utcnow()
        except Exception:
            pass
    _emitir_comprobante(db, ps, sol)
    db.commit()

    # Aviso "Pago recibido" + difusión a técnicos (best-effort)
    try:
        from app.services import push as _push
        if sol:
            _push.avisar_pago_recibido(db, sol)
    except Exception:
        logger.exception("[pagook] aviso pago recibido")
    try:
        _difundir_a_tecnicos(db, ps.solicitud_id)
    except Exception:
        logger.exception("[pagook] difusión a técnicos")
    return _resp(ps, "¡Pago recibido! Buscando un técnico para ti.")


def _emitir_comprobante(db, ps, sol):
    """Comprobante de la VISITA (zMita-41): valida el documento del comprador y emite por
    Facturalo real (estado honesto). Si falta algo, queda 'pendiente' (no revierte el pago)."""
    from app.services.documento import validar_documento, tipo_comprobante_por_documento
    from app.services import comprobante as _comp
    tipo_doc = ps.comprador_doc_tipo or (getattr(sol, "comprador_doc_tipo", None) if sol else None)
    num_doc = ps.comprador_doc_numero or (getattr(sol, "comprador_doc_numero", None) if sol else None)
    nombre = (ps.comprador_nombre or (getattr(sol, "comprador_nombre", None) if sol else None)
              or (getattr(sol, "cliente_nombre", None) if sol else None) or "Cliente")
    if not tipo_doc or not num_doc:
        ps.comprobante_estado = "pendiente"
        _alerta_torre(f"Comprobante pendiente solicitud #{ps.solicitud_id}: falta documento del comprador.")
        return
    ok, tipo_n, msg = validar_documento(tipo_doc, num_doc)
    if not ok:
        ps.comprobante_estado = "pendiente"
        _alerta_torre(f"Comprobante pendiente solicitud #{ps.solicitud_id}: documento inválido ({msg}).")
        return
    tipo_comp = tipo_comprobante_por_documento(tipo_n)
    cliente = {"doc_tipo": tipo_n, "doc_numero": num_doc, "razon_social": nombre}
    monto = float(ps.monto_esperado or 0)
    r = _comp.emitir(db, ps.solicitud_id, "visita", tipo_comp, cliente,
                     items=[{"descripcion": "Visita técnica MITA", "monto": monto}], monto=monto)
    ps.comprobante_tipo = tipo_comp
    ps.comprobante_estado = ("emitido" if r.get("estado") in ("aceptado", "simulado")
                             else ("enviando" if r.get("estado") == "enviando" else "pendiente"))


def _difundir_a_tecnicos(db, solicitud_id):
    """Dispara la oferta a técnicos tras el pago (etapa 4, zMita-37)."""
    try:
        from app.services import ofertas
        from app.models.solicitud_mita import Solicitud
        s = db.query(Solicitud).get(solicitud_id)
        if s:
            ofertas.difundir(db, s)
    except Exception:
        logger.exception("[pagook] no se pudo difundir")
