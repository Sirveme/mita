"""
Chat IA de solicitudes (zMita-17).

El usuario narra su problema en lenguaje natural; OpenAI extrae entidades
(área, problema, dirección, detalles). Se valida la dirección con Google
Geocoding y se confirma antes de crear la solicitud.

- POST /api/v1/chat-ia/interpretar        {mensaje, contexto[]}
- POST /api/v1/chat-ia/validar-direccion   {direccion}

El cliente de OpenAI se crea de forma perezosa: si la librería no está instalada
o falta la API key, el endpoint responde 503 sin tumbar la app.
"""
import os
import json
import time
import uuid
import logging
from typing import Optional, List

from hashlib import sha256
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.chat_conocimiento import ChatConocimiento
from app.routes.admin_postulantes import require_admin_gerente as _require_admin

logger = logging.getLogger("mita.chat_ia")
router = APIRouter(prefix="/api/v1/chat-ia", tags=["Chat IA"])

# Mapeo de las áreas del asistente a los códigos de categoría MITA (solo áreas con categoría real)
AREA_A_CODIGO = {
    "gasfiteria": "GASF",
    "electricidad": "ELEC",
    "linea_blanca": "ELDOM",
    "aire_acondicionado": "ELDOM",
    "albanileria_menor": "ALBA",
    "instalaciones_hogar": "MUEB",
    "bombas_agua": "BOMB",
    "automotriz": "AUTO",
}
# Código de categoría MITA -> slug de área para el prompt
CODIGO_A_SLUG = {"ELEC": "electricidad", "GASF": "gasfiteria", "ELDOM": "linea_blanca",
                 "MUEB": "instalaciones_hogar", "ALBA": "albanileria_menor",
                 "BOMB": "bombas_agua", "AUTO": "automotriz"}

SYSTEM_PROMPT_BASE = """
Eres el asistente virtual de MITA, servicio de técnicos a domicilio en Lima, Perú.
Tutea, habla en español peruano neutro, con buena ortografía y tildes, y haz UNA sola pregunta por mensaje.

__CONOCIMIENTO__

RESPONDE SIEMPRE EN JSON (sin texto fuera del JSON):
{
  "entendido": true/false,
  "intencion": "solicitar" | "consulta" | "mixta" | "otro",
  "respuesta_consulta": "respuesta breve a lo que preguntó (precio/horario/garantía/pagos/cobertura) usando SOLO el bloque CONOCIMIENTO, o null",
  "area": "<slug de una categoría válida del bloque>" | null,
  "problema": "descripción corta del problema" | null,
  "localidad_mencionada": "ciudad o distrito que nombró el usuario (Iquitos, Miraflores…)" | null,
  "direccion": {
    "texto_original": "lo que dijo el usuario" | null,
    "calle": "nombre de calle/avenida" | null, "numero": "435" | null, "interior": "dpto 201" | null,
    "distrito": "Miraflores" | null, "referencia": "frente al parque" | null,
    "ambigua": true/false, "opciones": ["Av Larco, Miraflores", "Av Larco, Trujillo"] | null
  },
  "detalles": { "ambiente": null, "urgencia": "alta" | "normal" | null, "otros": null },
  "preferencia_horaria": { "fecha": "YYYY-MM-DD" | null, "franja": "manana"|"tarde"|"noche"|null, "hora": "HH:MM"|null, "lo_antes_posible": true/false } | null,
  "fuera_cobertura": true/false,
  "completo": true/false,
  "siguiente_pregunta": "..." | null,
  "confirmacion": "Entendí: ..." | null
}

REGLAS:
- Si el usuario PREGUNTA algo (precio, horario, garantía, tiempo de llegada, medios de pago, cobertura): intencion="consulta" o "mixta"; primero respóndelo en "respuesta_consulta" usando SOLO el bloque CONOCIMIENTO. Si ese dato NO está en el bloque, responde exactamente: "Ese dato te lo confirma nuestro equipo al agendar". NUNCA inventes cifras, horarios ni políticas.
- Las categorías válidas son SOLO las listadas en el bloque CONOCIMIENTO; usa sus slugs. No ofrezcas categorías que no estén ahí.
- Si el área no es clara, infiérela del problema (fuga -> gasfiteria, cortocircuito -> electricidad).
- Pide la dirección COMPLETA en una sola pregunta (calle, número y distrito si lo sabe). NUNCA preguntes el distrito por separado.
- NO preguntes detalles opcionales (ambiente, marca, modelo, antigüedad). Solo necesitas área, problema y dirección.
- Si el usuario dice que no es urgente o que solo quiere saber el precio, respóndele y NO lo presiones; guarda urgencia si la menciona.
- Si menciona una ciudad o distrito FUERA de Lima (Iquitos, Punchana, Arequipa, Trujillo, Cusco…), marca "fuera_cobertura": true y no pidas más datos.
- "completo"=true solo si tienes área + problema + dirección (al menos calle y distrito).
- No inventes información que el usuario no proporcionó.
"""


class MensajeInput(BaseModel):
    mensaje: str
    contexto: List[dict] = []
    estado: dict = {}
    prueba: bool = False   # modo sandbox: sin efectos (interpretar ya es sin efectos)


class DireccionInput(BaseModel):
    direccion: str


def _openai_key():
    return settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")


def _openai_client():
    """Factoría única (usada por /interpretar, /transcribir y /estado).
    No cachea None: si falla, reintenta en la siguiente llamada. Registra la causa."""
    key = _openai_key()
    if not key:
        logger.error("[chat-ia] OPENAI_API_KEY vacía (ni en settings ni en el entorno).")
        return None
    try:
        from openai import OpenAI
    except Exception:
        logger.error("[chat-ia] Paquete 'openai' no instalado en este entorno.")
        return None
    try:
        return OpenAI(api_key=key)
    except Exception as e:
        logger.error("[chat-ia] No se pudo crear el cliente OpenAI: %s", e)
        return None


_GSRV_OK = {"t": 0.0, "ok": None}


async def _google_server_ok() -> Optional[bool]:
    """Prueba un geocode de una dirección fija de Miraflores (cacheado 10 min)."""
    if _GSRV_OK["ok"] is not None and (time.time() - _GSRV_OK["t"] < 600):
        return _GSRV_OK["ok"]
    try:
        g = await _geocode("Av Larco 100, Miraflores")
        ok = bool(g and g.get("lat"))
    except Exception:
        ok = False
    _GSRV_OK.update(t=time.time(), ok=ok)
    return ok


@router.get("/estado")
async def estado_ia():
    """Diagnóstico del chat IA (sin exponer el secreto completo)."""
    import importlib.util
    key = _openai_key()
    return {
        "openai_instalado": importlib.util.find_spec("openai") is not None,
        "key_presente": bool(key),
        "key_prefijo": (key[:7] + "…") if key else None,
        "cliente_ok": _openai_client() is not None,
        "google_maps": bool(settings.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")),
        "google_server_key": bool(settings.GOOGLE_MAPS_SERVER_KEY or os.getenv("GOOGLE_MAPS_SERVER_KEY")),
        "google_server_ok": await _google_server_ok(),
    }


import unicodedata

def _norm_txt(s: str) -> str:
    s = (s or "").lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

# Alucinaciones típicas de Whisper ante silencio
WHISPER_BLACKLIST = ["amara.org", "subtitulos realizados", "subtitulos por",
                     "gracias por ver", "suscribete", "www.", "musica"]
WHISPER_PROMPT = ("Cliente en Lima describe un problema doméstico: gasfitería, electricidad, "
                  "electrodomésticos, refrigeradora, lavadora, fuga, cortocircuito, dirección, distrito.")


def _es_alucinacion(texto: str) -> bool:
    t = _norm_txt(texto)
    if not t:
        return True
    if any(b in t for b in WHISPER_BLACKLIST):
        return True
    palabras = [w for w in t.split() if len(w) > 1]
    return len(palabras) < 2


def _distritos_cobertura(db: Session):
    try:
        from app.models.personal import Distrito
        return [d.nombre for d in db.query(Distrito).filter(Distrito.habilitado == True).all() if d.nombre]
    except Exception:
        return []


def _en_cobertura(db: Session, distrito: Optional[str]):
    """True/False si el distrito está (o no) en cobertura; None si no se puede determinar."""
    if not distrito:
        return None
    n = _norm_txt(distrito)
    cob = _distritos_cobertura(db)
    if not cob:
        return None
    for nom in cob:
        a = _norm_txt(nom)
        if a and (a in n or n in a):
            return True
    return False


def _marcar_cobertura(db: Session, data: dict) -> dict:
    """Decide la cobertura por el distrito actual. Un distrito EN cobertura manda sobre
    un flag viejo (así una corrección de dirección reabre el flujo; zMita-31 Parte B)."""
    distrito = (data.get("direccion") or {}).get("distrito")
    fuera = bool(data.get("fuera_cobertura"))
    if distrito:
        en = _en_cobertura(db, distrito)
        if en is True:
            fuera = False
        elif en is False:
            fuera = True
    data["fuera_cobertura"] = fuera
    return data


def _slug(nombre: str) -> str:
    n = _norm_txt(nombre)
    for a, b in ((" ", "_"), ("-", "_")):
        n = n.replace(a, b)
    return "".join(c for c in n if c.isalnum() or c == "_")


# Base de conocimiento inyectada en el prompt (cacheada 5 min)
_CONO = {"t": 0.0, "txt": None, "faltantes": None, "cats": None}

def limpiar_cache_conocimiento():
    _CONO.update(t=0.0, txt=None, faltantes=None, cats=None)


def _conocimiento(db: Session):
    """Devuelve (texto_bloque, claves_faltantes, slugs_validos) desde datos reales."""
    import time as _t
    if _CONO["txt"] and (_t.time() - _CONO["t"] < 300):
        return _CONO["txt"], _CONO["faltantes"], _CONO["cats"]
    from app.models.models import CategoriaServicio
    cats = [c for c in db.query(CategoriaServicio).filter(CategoriaServicio.activo == True)
            .order_by(CategoriaServicio.orden).all() if not getattr(c, "proximamente", False)]
    cat_lines, validos = [], []
    for c in cats:
        slug = CODIGO_A_SLUG.get(c.codigo) or _slug(c.nombre)
        validos.append(slug)
        cat_lines.append(f"- {slug}: {c.nombre}")
    from app.services.catalogo import precio_visita_vigente
    pv = precio_visita_vigente(db)
    distritos = _distritos_cobertura(db)
    activos = db.query(ChatConocimiento).filter(ChatConocimiento.activo == True).all()
    faltantes = [e.clave for e in db.query(ChatConocimiento).all()
                 if not e.activo or not (e.contenido or "").strip()]
    lines = ["BLOQUE CONOCIMIENTO (único origen de precios, horarios y políticas):", "",
             "CATEGORÍAS VÁLIDAS (usa solo estos slugs):"]
    lines += cat_lines
    if pv["es_promo"]:
        tarifa_line = (f"TARIFA DE VISITA / DIAGNÓSTICO: S/ {pv['precio']:.2f} en PROMOCIÓN "
                       f"(precio regular S/ {pv['regular']:.2f}" +
                       (f", promoción hasta {pv['hasta']}" if pv['hasta'] else "") + "). "
                       "Incluye el diagnóstico; la reparación la cotiza el técnico en sitio antes de empezar.")
    else:
        tarifa_line = (f"TARIFA DE VISITA / DIAGNÓSTICO: S/ {pv['precio']:.2f} (incluye el diagnóstico; "
                       "la reparación la cotiza el técnico en sitio antes de empezar).")
    lines += ["", tarifa_line,
              "DISTRITOS CON COBERTURA: " + (", ".join(distritos) if distritos else "(aún no hay distritos habilitados)")]
    extras = [e for e in activos if (e.contenido or "").strip()]
    if extras:
        lines += ["", "INFORMACIÓN ADICIONAL:"]
        lines += [f"- {e.titulo}: {e.contenido.strip()}" for e in extras]
    txt = "\n".join(lines)
    _CONO.update(t=_t.time(), txt=txt, faltantes=faltantes, cats=validos)
    return txt, faltantes, validos


def _conocimiento_valor(db: Session, clave: str) -> Optional[str]:
    """Contenido de una clave de chat_conocimiento si está activa y no vacía."""
    try:
        row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == clave,
                                                ChatConocimiento.activo == True).first()
        v = (row.contenido or "").strip() if row else ""
        return v or None
    except Exception:
        return None


def _merge_dir(cur: dict, new: dict) -> dict:
    cur = dict(cur or {}); new = new or {}
    for k in ("texto_original", "calle", "numero", "interior", "distrito", "referencia"):
        v = new.get(k)
        if v and not cur.get(k):
            cur[k] = v
    return cur


def _fusionar(estado: dict, data: dict) -> dict:
    """Fusiona la respuesta de la IA sobre el estado acumulado. Nunca borra un campo
    ya lleno con null/vacío."""
    estado = dict(estado or {})
    for k in ("area", "problema"):
        v = data.get(k)
        if v and not estado.get(k):
            estado[k] = v
    estado["direccion"] = _merge_dir(estado.get("direccion"), data.get("direccion"))
    det = dict(estado.get("detalles") or {})
    for k, v in (data.get("detalles") or {}).items():
        if v and not det.get(k):
            det[k] = v
    estado["detalles"] = det
    urg = (data.get("detalles") or {}).get("urgencia")
    if urg:
        estado["urgencia"] = urg
    return estado


_PREGUNTA_KW = ("cuanto", "cuánto", "cobran", "cobra", "precio", "tarifa", "cuesta", "vale",
                "como ", "cómo ", "cuando", "cuándo", "donde", "dónde", "atienden", "atiende",
                "garantia", "garantía", "cancel", "demora", "demoran", "tardan",
                "medios de pago", "si cancelo", "que pasa", "qué pasa", "qué sucede", "que sucede")


def _es_pregunta(mensaje: str) -> bool:
    """¿El mensaje ACTUAL del usuario pregunta algo? (para decidir intención por turno)."""
    m = _norm_txt(mensaje or "")
    if "?" in (mensaje or "") or "¿" in (mensaje or ""):
        return True
    return any(k.strip() in m for k in _PREGUNTA_KW)


_ASAP_KW = ("ahora mismo", "ahora", "ya mismo", "cuanto antes", "lo antes posible",
            "de inmediato", "inmediato", "en este momento", "emergencia", "urgente", "urgencia")
_VER_OTROS_KW = ("ver otros", "otros horarios", "otro horario", "mas horarios", "más horarios",
                 "otra hora", "ver mas", "ver más")
_CORRIGE_KW = ("no, ", "no es", "no era", "mejor ", "me equivoque", "me equivoque,", "equivoca",
               "perdon", "perdón", "disculpa", "corrige", "corrijo", "cambia", "cambiar",
               "en realidad", "es en ", "mas bien", "más bien", "queria decir", "quería decir")


def _es_asap(mensaje: str) -> bool:
    m = _norm_txt(mensaje or "")
    return any(k.strip() in m for k in (_norm_txt(x) for x in _ASAP_KW))


def _quiere_otros(mensaje: str) -> bool:
    m = _norm_txt(mensaje or "")
    return any(_norm_txt(k) in m for k in _VER_OTROS_KW)


def _es_correccion(mensaje: str) -> bool:
    m = _norm_txt(mensaje or "")
    return any(k.strip() in m for k in (_norm_txt(x) for x in _CORRIGE_KW))


def _reformular_problema(area: Optional[str]) -> str:
    a = (area or "").lower()
    if a == "electricidad":
        return "Cuéntame un poco más: ¿no prende nada, salta la llave o hay olor a quemado?"
    if a == "gasfiteria":
        return "Cuéntame un poco más: ¿hay una fuga, está atorado o no sale agua?"
    if a == "linea_blanca":
        return "Cuéntame un poco más: ¿no enfría, hace ruido raro o no enciende?"
    return "¿Qué está pasando en tu casa?"


def _siguiente_pregunta(estado: dict) -> Optional[str]:
    """Decide la siguiente pregunta según lo que falta. NUNCA devuelve None si falta algo."""
    d = estado.get("direccion") or {}
    if not estado.get("problema") and not estado.get("area"):
        return "¿Qué necesitas y qué está pasando? (por ejemplo: una fuga de agua, un cortocircuito, la refri que no enfría)"
    if not estado.get("problema"):
        return "¿Qué está pasando exactamente?"
    if not d.get("calle"):
        if d.get("distrito"):
            return f"¿En qué calle y número de {d['distrito']}?"
        return "¿Cuál es tu dirección? (calle, número y distrito)"
    if not d.get("distrito"):
        return "¿En qué distrito queda esa dirección?"
    if not d.get("validada"):
        return "¿Me confirmas la dirección exacta? (calle, número y distrito)"
    return None


def _enriquecer_categoria(db: Session, data: dict) -> dict:
    """Agrega categoria_id/codigo/nombre a partir del área detectada."""
    area = (data.get("area") or "").lower()
    cod = AREA_A_CODIGO.get(area)
    if cod:
        from app.models.models import CategoriaServicio
        cat = db.query(CategoriaServicio).filter(CategoriaServicio.codigo == cod).first()
        if cat:
            data["categoria_id"] = cat.id
            data["categoria_codigo"] = cat.codigo
            data["categoria_nombre"] = cat.nombre
            return data
    data.setdefault("categoria_id", None)
    return data


def _err_chat(estado, mensaje, request=None):
    """Respuesta de error legible (nunca deja al usuario sin texto). Loguea con request_id.
    Incluye traceback solo si la request trae X-Debug-Token == settings.DEBUG_TOKEN."""
    import traceback as _tb
    eid = uuid.uuid4().hex[:8]
    tb = _tb.format_exc()
    logger.error("[chat-ia][%s] %s\n%s", eid, mensaje, tb)
    out = {"mensaje": mensaje, "error_id": eid, "estado": estado or {},
           "siguiente_pregunta": None, "completo": False, "fuera_cobertura": False}
    tok = settings.DEBUG_TOKEN
    if request is not None and tok and request.headers.get("X-Debug-Token") == tok:
        out["traceback"] = tb
    return out


@router.post("/interpretar")
async def interpretar_mensaje(datos: MensajeInput, request: Request, db: Session = Depends(get_db)):
    """Interpreta el mensaje con memoria: fusiona el estado y decide la siguiente pregunta.
    NUNCA falla en silencio: ante cualquier error devuelve un JSON con `mensaje` y `error_id`."""
    estado_prev = dict(datos.estado or {})
    t_ini = time.monotonic()
    client = _openai_client()
    if client is None:
        return {"mensaje": "El asistente no está disponible ahora. Intenta por el formulario.",
                "error_id": None, "estado": estado_prev, "siguiente_pregunta": None,
                "completo": False, "fuera_cobertura": False, "sin_ia": True}

    conocimiento, _faltantes, _validos = _conocimiento(db)
    system = SYSTEM_PROMPT_BASE.replace("__CONOCIMIENTO__", conocimiento)

    from app.services.agenda import ahora_lima as _ahora_lima
    _now = _ahora_lima()
    system += (f"\n\nFECHA Y HORA ACTUAL (America/Lima): {_now.strftime('%Y-%m-%d %H:%M')} "
               f"({['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][_now.weekday()]}). "
               "Interpreta 'hoy', 'mañana', 'el sábado', 'en la tarde' respecto a esta fecha y "
               "llena preferencia_horaria. No propongas tú los horarios concretos; el sistema los calcula.")

    mensajes = [{"role": "system", "content": system}]
    if estado_prev:
        mensajes.append({"role": "system", "content": "Estado acumulado (no vuelvas a pedir lo que ya está): " + json.dumps(estado_prev, ensure_ascii=False)})
    for msg in (datos.contexto or [])[-10:]:
        if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
            mensajes.append({"role": msg["role"], "content": str(msg["content"])})
    mensajes.append({"role": "user", "content": datos.mensaje})

    t_oai = time.monotonic()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensajes,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception:
        return _err_chat(estado_prev, "Tuve un problema con el asistente, ¿me lo repites?", request)
    if not isinstance(data, dict):
        return _err_chat(estado_prev, "Tuve un problema entendiéndote, ¿me lo repites?", request)
    dt_oai = time.monotonic() - t_oai

    try:
        res = await _procesar_interpretacion(db, data, estado_prev, datos.mensaje)
        logger.info("[chat-ia] turno OK: openai=%.2fs total=%.2fs", dt_oai, time.monotonic() - t_ini)
        return res
    except Exception:
        return _err_chat(estado_prev, "Tuve un problema procesando tu mensaje, ¿me lo repites?", request)


async def _procesar_interpretacion(db, data, estado_prev, mensaje=""):
    # 1) Fusionar estado (la memoria vive en el backend)
    estado = _fusionar(estado_prev, data)
    estado = _enriquecer_categoria(db, estado)      # categoria_id a partir de estado.area

    # Parte B: corregir un dato dicho antes, o dar una nueva dirección tras "fuera de cobertura".
    # El mensaje actual REEMPLAZA lo que trae y obliga a revalidar.
    nueva_dir = data.get("direccion") or {}
    nueva_loc = data.get("localidad_mencionada")
    hay_ubic_nueva = bool(nueva_dir.get("calle") or nueva_dir.get("distrito") or nueva_loc)
    corrige = _es_correccion(mensaje)
    if corrige or (estado_prev.get("fuera_cobertura") and hay_ubic_nueva):
        d = dict(estado.get("direccion") or {})
        for k in ("texto_original", "calle", "numero", "interior", "distrito", "referencia"):
            v = nueva_dir.get(k)
            if v:
                d[k] = v                     # reemplaza (no conserva el valor viejo)
        for k in ("validada", "lat", "lng", "direccion_formateada"):
            d.pop(k, None)                   # revalidar la dirección corregida
        estado["direccion"] = d
        if nueva_loc:
            estado["localidad_mencionada"] = nueva_loc
        elif nueva_dir.get("distrito"):
            estado["localidad_mencionada"] = nueva_dir.get("distrito")
        estado.pop("fuera_cobertura", None)  # se recalcula este turno

    # Cobertura POR TURNO: parte del flag fresco de la IA (no del estado viejo)
    estado["fuera_cobertura"] = bool(data.get("fuera_cobertura")) and not corrige
    estado = _marcar_cobertura(db, estado)          # refina según distrito en cobertura

    # 2) Intención SOLO por el mensaje actual (no por el historial)
    es_pregunta = _es_pregunta(mensaje)
    respuesta_consulta = data.get("respuesta_consulta") or None
    if not es_pregunta:
        respuesta_consulta = None          # consulta "pegada" de turnos anteriores -> descartar
    elif not respuesta_consulta:
        # El usuario preguntó algo y la IA no lo respondió (p.ej. cancelación sin dato cargado)
        respuesta_consulta = "Con gusto: esa información te la confirma nuestro equipo al agendar."
    intencion = "consulta" if (respuesta_consulta and not (estado.get("area") or estado.get("problema"))) else "solicitar"
    # El flag de la IA prevalece
    fuera = bool(estado.get("fuera_cobertura"))
    # Localidad mencionada por el usuario (si la IA la devolvió)
    localidad = data.get("localidad_mencionada") or estado.get("localidad_mencionada")
    if localidad:
        estado["localidad_mencionada"] = localidad

    # Parte D: guardar la preferencia horaria aunque aún falte otro dato
    pref_ia = data.get("preferencia_horaria")
    if isinstance(pref_ia, dict) and any(pref_ia.get(k) for k in ("fecha", "franja", "hora", "lo_antes_posible")):
        estado["preferencia_horaria"] = {**(estado.get("preferencia_horaria") or {}), **pref_ia}

    # Si el usuario nombró una localidad que NO está en cobertura (p.ej. Iquitos),
    # es fuera de cobertura aunque Geocoding sesgue el resultado a Lima.
    if not fuera and localidad and _en_cobertura(db, localidad) is False:
        fuera = True
        estado["fuera_cobertura"] = True

    dir_ = estado.get("direccion") or {}
    pregunta_confirmar_distrito = None

    # 3) Geocodificar en el backend cuando hay calle y aún no está validada
    if not fuera and dir_.get("calle") and not dir_.get("validada"):
        texto_dir = dir_.get("texto_original") or " ".join(
            [x for x in (dir_.get("calle"), dir_.get("numero"), dir_.get("distrito") or localidad) if x])
        g = await _geocode(texto_dir)
        if g:
            region = _norm_txt(g.get("region") or "")
            g_distrito = g.get("distrito")
            # Resultado fuera de la región de Lima -> fuera de cobertura
            if region and "lima" not in region:
                fuera = True
            else:
                en_cob = _en_cobertura(db, g_distrito)
                if en_cob is False:
                    fuera = True
                else:
                    # Distrito válido y en cobertura: lo damos por validado
                    dir_["lat"] = g["lat"]; dir_["lng"] = g["lng"]
                    dir_["distrito"] = g_distrito or dir_.get("distrito")
                    dir_["direccion_formateada"] = g.get("direccion_formateada")
                    dir_["validada"] = True
                    estado["direccion"] = dir_
                    # Si el usuario mencionó otro distrito de Lima, pedir confirmación
                    if localidad and g_distrito and _norm_txt(localidad) not in _norm_txt(g_distrito) \
                            and _norm_txt(g_distrito) not in _norm_txt(localidad) \
                            and _en_cobertura(db, localidad) is not False:
                        pregunta_confirmar_distrito = f"Encontré esa dirección en {g_distrito}. ¿Es correcto?"
        else:
            # Geocoding NO disponible (p.ej. API key restringida a navegador / sin red):
            # no bloquear. Si hay un distrito en cobertura, aceptamos la dirección (sin lat/lng;
            # el horario/ubicación se confirman luego). Iquitos ya quedó marcado fuera arriba.
            dd = dir_.get("distrito")
            if dd and _en_cobertura(db, dd) is True:
                dir_["validada"] = True
                dir_["direccion_formateada"] = dir_.get("texto_original") or \
                    " ".join([x for x in (dir_.get("calle"), dir_.get("numero"), dd) if x])
                estado["direccion"] = dir_
                logger.warning("[chat-ia] geocoding no disponible; dirección aceptada por distrito en cobertura: %s", dd)

    estado["fuera_cobertura"] = fuera
    dir_ = estado.get("direccion") or {}

    # "listo" = área + problema + dirección validada (lat/lng opcional: el geocoding puede
    # no estar disponible en el servidor) en cobertura y sin confirmación de distrito pendiente
    listo = (bool(estado.get("area") and estado.get("problema")
                  and dir_.get("validada") and dir_.get("distrito"))
             and not fuera and not pregunta_confirmar_distrito)

    # ----- Agenda: antes de confirmar, elegir fecha/hora (Parte C) -----
    from app.services.agenda import opciones_horarios, ahora_lima
    from app.services.texto import hora_coloquial, dia_coloquial
    horarios = None
    asap = False
    asap_msg = None
    horario_elegido = estado.get("horario_elegido")
    if _quiere_otros(mensaje):
        estado["mostrar_todos"] = True
    if listo and not horario_elegido:
        pref = data.get("preferencia_horaria") or estado.get("preferencia_horaria") or {}
        if not isinstance(pref, dict):
            pref = {}
        urg = estado.get("urgencia") or (data.get("detalles") or {}).get("urgencia")
        asap = (_es_asap(mensaje) or urg == "alta" or bool(pref.get("lo_antes_posible"))) \
            and not estado.get("mostrar_todos")
        if urg == "alta" or asap:
            pref["lo_antes_posible"] = True
        estado["preferencia_horaria"] = pref
        _now = ahora_lima()
        try:
            horarios = opciones_horarios(db, _now, pref, n=3)
        except Exception:
            logger.exception("[chat-ia] agenda falló; se confirma sin horario")
            horarios = []
        if asap and horarios:
            h0 = horarios[0]
            dia = dia_coloquial(h0["iso"], _now)
            hora = hora_coloquial(h0["iso"])
            if dia == "hoy":
                asap_msg = f"El primer técnico disponible puede llegar hoy a las {hora}. ¿Te lo reservo?"
            else:
                asap_msg = (f"Hoy ya no tengo cupos. El primero disponible es {dia} a las {hora}. "
                            "¿Te lo reservo?")
                contacto = _conocimiento_valor(db, "contacto_emergencias")
                if contacto:
                    asap_msg += f" Si es una emergencia, comunícate ya: {contacto}."
            horarios = [h0]   # ofrecer el primero; "Ver otros horarios" muestra el resto

    # Agenda sin cupos/datos (A.5): no bloquear; permitir confirmar sin horario
    agenda_pendiente = bool(listo and not horario_elegido and not horarios)
    completo = bool(listo and (horario_elegido or agenda_pendiente))
    if agenda_pendiente:
        estado["agenda_pendiente"] = True

    if fuera or completo:
        siguiente = None
    elif pregunta_confirmar_distrito:
        siguiente = pregunta_confirmar_distrito
    elif asap_msg:
        siguiente = asap_msg
    elif listo and not horario_elegido:
        siguiente = "¿Para cuándo lo necesitas? Elige un horario o dime otro momento (ej. mañana en la tarde)."
    else:
        siguiente = _siguiente_pregunta(estado)

    # No repetir textualmente el MISMO mensaje dos turnos seguidos (Parte C): reformular/avanzar.
    ultimo_bot = estado_prev.get("_ultimo_bot")
    if siguiente and siguiente == ultimo_bot and not horarios:
        bajo = siguiente.lower()
        if "está pasando" in siguiente or "qué necesitas" in bajo:
            siguiente = _reformular_problema(estado.get("area"))
        elif "para cuándo" in bajo or "horario" in bajo:
            siguiente = "Cuéntame, ¿a qué hora te viene bien? Puedes elegir uno de los horarios de abajo."
        elif "dirección" in bajo or "distrito" in bajo or "calle" in bajo:
            siguiente = "Para ubicarte, dime la calle, el número y el distrito, por favor."
        else:
            siguiente = siguiente.rstrip(". ") + " (cuéntame para avanzar)."
    if siguiente:
        estado["_ultima_pregunta"] = siguiente

    # Ambigüedad/opciones son transitorias (no se guardan en el estado): tómalas del turno actual
    iad = data.get("direccion") or {}
    dir_ = dict(dir_)
    dir_["ambigua"] = bool(iad.get("ambigua"))
    dir_["opciones"] = iad.get("opciones")

    confirmacion = data.get("confirmacion")
    if completo and not confirmacion:
        area_txt = (estado.get("categoria_nombre") or estado.get("area") or "servicio").replace("_", " ")
        d = estado.get("direccion") or {}
        dir_txt = " ".join([x for x in (d.get("calle"), d.get("numero")) if x])
        if d.get("distrito"):
            dir_txt = (dir_txt + ", " + d["distrito"]).strip(", ")
        confirmacion = f"Entendí: {area_txt} por {estado.get('problema')} en {dir_txt}".strip()
    if completo and estado.get("agenda_pendiente") and confirmacion:
        confirmacion += " · Te confirmamos el horario por WhatsApp en minutos."

    # Parte A.3: si hubo consulta y hay una pregunta de texto pendiente, un solo mensaje.
    if respuesta_consulta and siguiente:
        respuesta_consulta = respuesta_consulta.rstrip(" .") + ". " + siguiente
        siguiente = None

    # Recordar el mensaje principal de este turno (para no repetirlo en el siguiente)
    if respuesta_consulta:
        estado["_ultimo_bot"] = respuesta_consulta
    elif not fuera and completo and confirmacion:
        estado["_ultimo_bot"] = confirmacion
    elif siguiente:
        estado["_ultimo_bot"] = siguiente

    from app.services.catalogo import precio_visita_vigente
    # 3) Armar respuesta (incluye el estado fusionado para reenviar)
    resp = {
        "estado": estado,
        "intencion": intencion,
        "respuesta_consulta": respuesta_consulta,
        "area": estado.get("area"),
        "problema": estado.get("problema"),
        "direccion": dir_,
        "detalles": estado.get("detalles") or {},
        "urgencia": estado.get("urgencia"),
        "categoria_id": estado.get("categoria_id"),
        "categoria_codigo": estado.get("categoria_codigo"),
        "categoria_nombre": estado.get("categoria_nombre"),
        "precio_visita": precio_visita_vigente(db),
        "fuera_cobertura": fuera,
        "completo": completo,
        "horarios": horarios,
        "asap": asap,
        "fecha_programada": horario_elegido,
        "siguiente_pregunta": siguiente,
        "confirmacion": confirmacion,
    }
    return _asegurar_mensaje(resp, estado)


def _asegurar_mensaje(resp: dict, estado: dict) -> dict:
    """Contrato 'nunca vacío': si no hay nada renderizable, construye un mensaje desde el
    estado y loguea un WARNING (llegar aquí es un bug de alguna rama)."""
    tiene = (resp.get("respuesta_consulta") or resp.get("fuera_cobertura") or resp.get("horarios")
             or (resp.get("completo") and resp.get("confirmacion")) or resp.get("siguiente_pregunta")
             or resp.get("mensaje"))
    if not tiene:
        sp = _siguiente_pregunta(estado) or "¿Me confirmas tu dirección? (calle, número y distrito)"
        resp["siguiente_pregunta"] = sp
        logger.warning("[chat-ia] respuesta vacía reconstruida -> %r | estado=%s",
                       sp, json.dumps(estado, ensure_ascii=False)[:400])
    return resp


_LOG_CLIENTE = {"ventana": 0, "n": 0}


@router.post("/log-cliente")
async def log_cliente(data: dict = Body(...)):
    """Recibe errores del chat/voz del navegador y los escribe en el log del servidor."""
    import time as _t
    ahora = int(_t.time() // 60)
    if _LOG_CLIENTE["ventana"] != ahora:
        _LOG_CLIENTE["ventana"] = ahora; _LOG_CLIENTE["n"] = 0
    _LOG_CLIENTE["n"] += 1
    if _LOG_CLIENTE["n"] > 60:          # rate-limit: 60/min global
        return {"ok": False, "motivo": "rate_limited"}
    msg = str(data.get("mensaje") or "")[:500]
    stack = str(data.get("stack") or "")[:1500]
    ultimo = json.dumps(data.get("ultimo_request") or {}, ensure_ascii=False)[:1000]
    logger.warning("[CHAT-CLIENTE] %s | ultimo_request=%s | stack=%s", msg, ultimo, stack)
    return {"ok": True}


@router.get("/precio-visita")
async def precio_visita(db: Session = Depends(get_db)):
    """Precio de la visita vigente HOY (misma fuente que usa el chat y el formulario)."""
    from app.services.catalogo import precio_visita_vigente
    return precio_visita_vigente(db)


@router.get("/conocimiento-bloque")
async def conocimiento_bloque(db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Texto exacto del bloque CONOCIMIENTO que recibe el modelo (para el sandbox admin)."""
    from app.services.catalogo import ultima_actualizacion
    txt, faltantes, validos = _conocimiento(db)
    return {"bloque": txt, "faltantes": faltantes, "categorias": validos, "actualizado": ultima_actualizacion()}


@router.get("/conocimiento")
async def listar_conocimiento(db: Session = Depends(get_db), _=Depends(_require_admin)):
    rows = db.query(ChatConocimiento).order_by(ChatConocimiento.id).all()
    return [{"clave": r.clave, "titulo": r.titulo, "contenido": r.contenido or "", "activo": bool(r.activo)} for r in rows]


@router.put("/conocimiento/{clave}")
async def actualizar_conocimiento(clave: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(_require_admin)):
    row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == clave).first()
    if not row:
        raise HTTPException(404, "Clave no encontrada")
    if "contenido" in data:
        row.contenido = (data.get("contenido") or "").strip()
    if "activo" in data:
        row.activo = bool(data.get("activo"))
    db.commit()
    limpiar_cache_conocimiento()
    return {"ok": True, "clave": clave, "activo": bool(row.activo)}


def _voz_config(db) -> dict:
    """Lee la voz elegida de chat_conocimiento (con defaults de Lima)."""
    cfg = {"proveedor": "openai", "voz": "coral", "velocidad": 1.0, "instrucciones": None}
    try:
        filas = {r.clave: (r.contenido or "") for r in db.query(ChatConocimiento).all()}
        if filas.get("voz_proveedor"): cfg["proveedor"] = filas["voz_proveedor"].strip().lower()
        if filas.get("voz_id"): cfg["voz"] = filas["voz_id"].strip()
        if filas.get("voz_velocidad"):
            try: cfg["velocidad"] = float(filas["voz_velocidad"])
            except ValueError: pass
        if filas.get("voz_instrucciones"): cfg["instrucciones"] = filas["voz_instrucciones"].strip()
    except Exception:
        pass
    return cfg


def _recortar_voz(texto: str) -> str:
    import re
    texto = (texto or "").strip()
    if len(texto) > 600:
        partes = re.split(r"(?<=[.!?])\s", texto)
        texto = (partes[0] if partes else texto[:200]).strip() + " Te dejo el detalle en pantalla."
    return texto


@router.post("/hablar")
async def hablar(data: dict = Body(...), db: Session = Depends(get_db)):
    """TTS (proveedor configurable) -> audio/mpeg. 503 si no hay proveedor; 422 si el cuerpo es inválido."""
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Cuerpo inválido: se espera JSON {\"texto\": \"...\"}")
    texto = _recortar_voz(str(data.get("texto") or ""))
    if not texto:
        raise HTTPException(status_code=422, detail="Falta 'texto' (JSON UTF-8).")
    from app.services import tts
    if not tts.proveedores_activos():
        raise HTTPException(status_code=503, detail="Voz Premium no disponible")
    cfg = _voz_config(db)
    try:
        audio = tts.sintetizar(texto, cfg)
    except Exception:
        logger.exception("Error TTS (%s/%s)", cfg.get("proveedor"), cfg.get("voz"))
        raise HTTPException(status_code=502, detail="Error de síntesis de voz")
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"X-Proveedor": cfg.get("proveedor", ""), "X-Voz": cfg.get("voz", "")})


@router.get("/voces")
async def listar_voces(_=Depends(_require_admin)):
    """Voces disponibles según las keys configuradas (laboratorio admin)."""
    from app.services import tts
    cfg = None
    return {"voces": tts.voces_disponibles(), "proveedores": tts.proveedores_activos()}


@router.post("/voces/probar")
async def probar_voz(data: dict = Body(...), _=Depends(_require_admin)):
    """Sintetiza la frase de prueba con una voz dada (devuelve audio + latencia)."""
    from app.services import tts
    texto = _recortar_voz(str(data.get("texto") or "Hola, soy el asistente de MITA."))
    cfg = {"proveedor": (data.get("proveedor") or "openai").lower(), "voz": data.get("voz") or "coral",
           "velocidad": data.get("velocidad") or 1.0, "instrucciones": data.get("instrucciones")}
    t0 = time.monotonic()
    try:
        audio = tts.sintetizar(texto, cfg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo generar la voz: {e}")
    ms = int((time.monotonic() - t0) * 1000)
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"X-Latencia-Ms": str(ms), "X-Bytes": str(len(audio)),
                             "X-Proveedor": cfg["proveedor"], "X-Voz": str(cfg["voz"])})


@router.post("/voces/usar")
async def usar_voz(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Guarda la voz elegida en chat_conocimiento + invalida cache + historial."""
    from app.services.catalogo import invalidar_conocimiento, registrar_historial
    mapa = {"voz_proveedor": (data.get("proveedor") or "openai").lower(),
            "voz_id": str(data.get("voz") or "coral"),
            "voz_velocidad": str(data.get("velocidad") or "1.0"),
            "voz_instrucciones": (data.get("instrucciones") or "").strip()}
    for clave, valor in mapa.items():
        row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == clave).first()
        if not row:
            row = ChatConocimiento(clave=clave, titulo=clave, activo=True)
            db.add(row)
        if (row.contenido or "") != valor:
            registrar_historial(db, "chat_conocimiento", clave, clave, row.contenido, valor)
        row.contenido = valor; row.activo = True
    db.commit()
    invalidar_conocimiento()
    return {"ok": True, "proveedor": mapa["voz_proveedor"], "voz": mapa["voz_id"]}


@router.post("/transcribir")
async def transcribir_audio(audio: UploadFile = File(...)):
    """Transcribe audio (webm/opus u otros) con OpenAI Whisper → texto (modo Premium)."""
    client = _openai_client()
    if client is None:
        # La causa concreta ya quedó en el log del servidor (_openai_client)
        raise HTTPException(status_code=503, detail="Servicio de transcripción no disponible")
    try:
        audio_bytes = await audio.read()
        if not audio_bytes or len(audio_bytes) < 1024:
            raise HTTPException(status_code=400, detail="No se grabó audio")
        nombre = audio.filename or "audio.webm"
        # Safari graba en mp4; aceptamos los formatos típicos de MediaRecorder
        ctype = (audio.content_type or "").lower()
        if ctype not in ("audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-m4a"):
            ctype = "audio/webm"
        logger.info("[chat-ia] /transcribir recibido: %s bytes, content_type=%s", len(audio_bytes), ctype)
        t0 = time.monotonic()
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(nombre, audio_bytes, ctype),
            language="es",
            temperature=0,
            prompt=WHISPER_PROMPT,
            response_format="text",
        )
        dt = time.monotonic() - t0
        texto = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))
        texto = (texto or "").strip()
        logger.info("[chat-ia] Whisper %.2fs, %s bytes, texto=%r", dt, len(audio_bytes), texto[:120])
        if _es_alucinacion(texto):
            logger.info("[chat-ia] Transcripción descartada (sin_voz): %r", texto[:60])
            return {"texto": "", "motivo": "sin_voz"}
        return {"texto": texto, "modo": "premium"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error transcribiendo audio")
        raise HTTPException(status_code=502, detail="Error al transcribir el audio")


_GEO_CACHE = {}   # direccion_norm -> (ts, dict|None)


async def _geocode(direccion: str) -> Optional[dict]:
    """Geocodifica en Perú (sin forzar Lima). Devuelve lat/lng, distrito, provincia y
    región (administrative_area_level_1), o None. Cachea 10 min y nunca bloquea >6s."""
    import httpx
    # Preferir la key de servidor (sin restricción de referrer); nunca se expone al frontend
    api_key = (settings.GOOGLE_MAPS_SERVER_KEY or os.getenv("GOOGLE_MAPS_SERVER_KEY")
               or settings.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY"))
    if not api_key:
        return None
    clave = _norm_txt(direccion)
    hit = _GEO_CACHE.get(clave)
    if hit and (time.time() - hit[0] < 600):
        return hit[1]
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": direccion, "components": "country:PE", "key": api_key, "language": "es", "region": "pe"}
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=6) as http_client:
            resp = await http_client.get(url, params=params)
            data = resp.json()
        logger.info("[chat-ia] geocoding %.2fs status=%s", time.monotonic() - t0, data.get("status"))
    except Exception as e:
        logger.warning("[chat-ia] geocoding error en %.2fs: %s", time.monotonic() - t0, e)
        _GEO_CACHE[clave] = (time.time(), None)
        return None
    if data.get("status") != "OK" or not data.get("results"):
        _GEO_CACHE[clave] = (time.time(), None)
        return None
    result = data["results"][0]
    distrito = provincia = region = None
    for comp in result.get("address_components", []):
        t = comp.get("types", [])
        if not distrito and ("locality" in t or "sublocality_level_1" in t):
            distrito = comp.get("long_name")
        if not provincia and "administrative_area_level_2" in t:
            provincia = comp.get("long_name")
        if not region and "administrative_area_level_1" in t:
            region = comp.get("long_name")
    loc = result["geometry"]["location"]
    out = {"lat": loc["lat"], "lng": loc["lng"], "distrito": distrito,
           "provincia": provincia, "region": region,
           "direccion_formateada": result.get("formatted_address")}
    _GEO_CACHE[clave] = (time.time(), out)
    return out


@router.post("/validar-direccion")
async def validar_direccion_maps(datos: DireccionInput):
    """Valida la dirección con Google Geocoding API y devuelve lat/lng + distrito."""
    api_key = settings.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Google Maps no configurado")
    g = await _geocode(datos.direccion)
    if not g:
        return {"valida": False, "mensaje": "No se encontró la dirección"}
    return {"valida": True, "direccion_formateada": g["direccion_formateada"],
            "lat": g["lat"], "lng": g["lng"], "distrito": g["distrito"], "region": g.get("region")}
