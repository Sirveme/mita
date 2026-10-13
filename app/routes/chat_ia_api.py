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
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
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
    distrito = (data.get("direccion") or {}).get("distrito")
    fuera = bool(data.get("fuera_cobertura"))
    if not fuera and distrito:
        if _en_cobertura(db, distrito) is False:
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
              "DISTRITOS CON COBERTURA: " + (", ".join(distritos) if distritos else "Lima Moderna")]
    extras = [e for e in activos if (e.contenido or "").strip()]
    if extras:
        lines += ["", "INFORMACIÓN ADICIONAL:"]
        lines += [f"- {e.titulo}: {e.contenido.strip()}" for e in extras]
    txt = "\n".join(lines)
    _CONO.update(t=_t.time(), txt=txt, faltantes=faltantes, cats=validos)
    return txt, faltantes, validos


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


def _siguiente_pregunta(estado: dict) -> Optional[str]:
    """Decide la siguiente pregunta según lo que falta (problema/área -> dirección)."""
    d = estado.get("direccion") or {}
    if not estado.get("problema") and not estado.get("area"):
        return "¿Qué necesitas y qué está pasando? (por ejemplo: una fuga de agua, un cortocircuito, la refri que no enfría)"
    if not estado.get("problema"):
        return "¿Qué está pasando exactamente?"
    if not d.get("calle"):
        if d.get("distrito"):
            return f"¿En qué calle y número de {d['distrito']}?"
        return "¿Cuál es tu dirección? (calle, número y distrito)"
    return None


def _esta_completo(estado: dict) -> bool:
    d = estado.get("direccion") or {}
    return bool(estado.get("area") and estado.get("problema") and d.get("calle"))


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


def _err_chat(estado, mensaje):
    """Respuesta de error legible (nunca deja al usuario sin texto). Loguea con request_id."""
    eid = uuid.uuid4().hex[:8]
    logger.exception("[chat-ia][%s] %s", eid, mensaje)
    return {"mensaje": mensaje, "error_id": eid, "estado": estado or {},
            "siguiente_pregunta": None, "completo": False, "fuera_cobertura": False}


@router.post("/interpretar")
async def interpretar_mensaje(datos: MensajeInput, db: Session = Depends(get_db)):
    """Interpreta el mensaje con memoria: fusiona el estado y decide la siguiente pregunta.
    NUNCA falla en silencio: ante cualquier error devuelve un JSON con `mensaje` y `error_id`."""
    estado_prev = dict(datos.estado or {})
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
        return _err_chat(estado_prev, "Tuve un problema con el asistente, ¿me lo repites?")
    if not isinstance(data, dict):
        return _err_chat(estado_prev, "Tuve un problema entendiéndote, ¿me lo repites?")

    try:
        return await _procesar_interpretacion(db, data, estado_prev)
    except Exception:
        return _err_chat(estado_prev, "Tuve un problema procesando tu mensaje, ¿me lo repites?")


async def _procesar_interpretacion(db, data, estado_prev):
    # 1) Fusionar estado (la memoria vive en el backend)
    estado = _fusionar(estado_prev, data)
    estado = _enriquecer_categoria(db, estado)      # categoria_id a partir de estado.area
    estado = _marcar_cobertura(db, estado)          # fuera_cobertura según distrito en cobertura

    # 2) Decidir intención / consulta
    intencion = (data.get("intencion") or "solicitar").lower()
    respuesta_consulta = data.get("respuesta_consulta") or None
    # El flag de la IA prevalece
    fuera = bool(estado.get("fuera_cobertura"))
    # Localidad mencionada por el usuario (si la IA la devolvió)
    localidad = data.get("localidad_mencionada") or estado.get("localidad_mencionada")
    if localidad:
        estado["localidad_mencionada"] = localidad

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
        # si no hubo geocoding (sin clave/sin resultado), no marcamos validada -> no completará

    estado["fuera_cobertura"] = fuera
    dir_ = estado.get("direccion") or {}

    # "listo" = área + problema + dirección validada en cobertura (sin confirmación pendiente)
    listo = (bool(estado.get("area") and estado.get("problema")
                  and dir_.get("validada") and dir_.get("lat") and dir_.get("distrito"))
             and not fuera and not pregunta_confirmar_distrito)

    # ----- Agenda: antes de confirmar, elegir fecha/hora (Parte C) -----
    from app.services.agenda import opciones_horarios, ahora_lima
    horarios = None
    horario_elegido = estado.get("horario_elegido")
    if listo and not horario_elegido:
        pref = data.get("preferencia_horaria") or estado.get("preferencia_horaria") or {}
        if not isinstance(pref, dict):
            pref = {}
        urg = estado.get("urgencia") or (data.get("detalles") or {}).get("urgencia")
        if urg == "alta":
            pref["lo_antes_posible"] = True
        estado["preferencia_horaria"] = pref
        horarios = opciones_horarios(db, ahora_lima(), pref, n=3)

    completo = bool(listo and horario_elegido)

    if fuera or completo:
        siguiente = None
    elif pregunta_confirmar_distrito:
        siguiente = pregunta_confirmar_distrito
    elif listo and not horario_elegido:
        siguiente = "¿Para cuándo lo necesitas? Elige un horario o dime otro momento (ej. mañana en la tarde)."
    else:
        siguiente = _siguiente_pregunta(estado)

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

    from app.services.catalogo import precio_visita_vigente
    # 3) Armar respuesta (incluye el estado fusionado para reenviar)
    return {
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
        "fecha_programada": horario_elegido,
        "siguiente_pregunta": siguiente,
        "confirmacion": confirmacion,
    }


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


_TTS_CACHE = {}   # hash -> bytes (memoria)


@router.post("/hablar")
async def hablar(data: dict = Body(...), db: Session = Depends(get_db)):
    """OpenAI TTS -> audio/mpeg (modo Premium). Cachea por texto+voz. 503 si no hay cliente."""
    import re
    texto = (data.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="texto vacío")
    if len(texto) > 600:
        partes = re.split(r"(?<=[.!?])\s", texto)
        texto = (partes[0] if partes else texto[:200]).strip() + " Te dejo el detalle en pantalla."
    client = _openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Voz Premium no disponible")
    try:
        row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == "voz_asistente").first()
        pref = (row.contenido if row and row.contenido else "femenina").lower()
    except Exception:
        pref = "femenina"
    voice = "shimmer" if "fem" in pref else "onyx"
    key = sha256((voice + "|" + texto).encode("utf-8")).hexdigest()
    if key in _TTS_CACHE:
        return Response(content=_TTS_CACHE[key], media_type="audio/mpeg", headers={"X-Cache": "hit"})
    try:
        try:
            resp = client.audio.speech.create(model="gpt-4o-mini-tts", voice=voice, input=texto)
        except Exception:
            resp = client.audio.speech.create(model="tts-1", voice=voice, input=texto)
        audio = resp.read() if hasattr(resp, "read") else (resp.content if hasattr(resp, "content") else bytes(resp))
    except Exception:
        logger.exception("Error TTS")
        raise HTTPException(status_code=502, detail="Error de síntesis de voz")
    if len(_TTS_CACHE) > 200:
        _TTS_CACHE.clear()
    _TTS_CACHE[key] = audio
    return Response(content=audio, media_type="audio/mpeg", headers={"X-Cache": "miss"})


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


async def _geocode(direccion: str) -> Optional[dict]:
    """Geocodifica en Perú (sin forzar Lima). Devuelve lat/lng, distrito, provincia y
    región (administrative_area_level_1), o None si no hay resultado/clave."""
    import httpx
    api_key = settings.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": direccion, "components": "country:PE", "key": api_key, "language": "es", "region": "pe"}
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            resp = await http_client.get(url, params=params)
            data = resp.json()
    except Exception as e:
        logger.warning("[chat-ia] geocoding error: %s", e)
        return None
    if data.get("status") != "OK" or not data.get("results"):
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
    return {"lat": loc["lat"], "lng": loc["lng"], "distrito": distrito,
            "provincia": provincia, "region": region,
            "direccion_formateada": result.get("formatted_address")}


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
