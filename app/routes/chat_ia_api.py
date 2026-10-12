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
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
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
  "direccion": {
    "texto_original": "lo que dijo el usuario" | null,
    "calle": "nombre de calle/avenida" | null, "numero": "435" | null, "interior": "dpto 201" | null,
    "distrito": "Miraflores" | null, "referencia": "frente al parque" | null,
    "ambigua": true/false, "opciones": ["Av Larco, Miraflores", "Av Larco, Trujillo"] | null
  },
  "detalles": { "ambiente": null, "urgencia": "alta" | "normal" | null, "otros": null },
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


@router.post("/interpretar")
async def interpretar_mensaje(datos: MensajeInput, db: Session = Depends(get_db)):
    """Interpreta el mensaje con memoria: fusiona el estado y decide la siguiente pregunta."""
    client = _openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Chat IA no disponible (OpenAI no configurado).")

    conocimiento, _faltantes, _validos = _conocimiento(db)
    system = SYSTEM_PROMPT_BASE.replace("__CONOCIMIENTO__", conocimiento)

    mensajes = [{"role": "system", "content": system}]
    estado_prev = dict(datos.estado or {})
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
    except Exception as e:
        logger.exception("Error llamando a OpenAI")
        raise HTTPException(status_code=502, detail=f"Error del asistente: {e}")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Respuesta del asistente no válida")

    # 1) Fusionar estado (la memoria vive en el backend)
    estado = _fusionar(estado_prev, data)
    estado = _enriquecer_categoria(db, estado)      # categoria_id a partir de estado.area
    estado = _marcar_cobertura(db, estado)          # fuera_cobertura según distrito en cobertura

    # 2) Decidir intención / respuesta de consulta / completitud / siguiente pregunta (backend)
    intencion = (data.get("intencion") or "solicitar").lower()
    respuesta_consulta = data.get("respuesta_consulta") or None
    fuera = bool(estado.get("fuera_cobertura"))
    dir_ = estado.get("direccion") or {}
    completo = _esta_completo(estado) and not fuera

    if fuera or completo:
        siguiente = None
    else:
        # El backend decide QUÉ falta; preferimos la redacción del modelo si apunta a lo mismo
        siguiente = _siguiente_pregunta(estado)

    # Ambigüedad/opciones son transitorias (no se guardan en el estado): tómalas del turno actual
    iad = data.get("direccion") or {}
    dir_ = dict(dir_)
    dir_["ambigua"] = bool(iad.get("ambigua"))
    dir_["opciones"] = iad.get("opciones")

    confirmacion = data.get("confirmacion")
    if completo and not confirmacion:
        area_txt = (estado.get("area") or "servicio").replace("_", " ")
        d = estado.get("direccion") or {}
        dir_txt = " ".join([x for x in (d.get("calle"), d.get("numero")) if x])
        if d.get("distrito"):
            dir_txt = (dir_txt + ", " + d["distrito"]).strip(", ")
        confirmacion = f"Entendí: {area_txt} por {estado.get('problema')} en {dir_txt}".strip()

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
        "fuera_cobertura": fuera,
        "completo": completo,
        "siguiente_pregunta": siguiente,
        "confirmacion": confirmacion,
    }


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
        logger.info("[chat-ia] Whisper respondió en %.2fs", time.monotonic() - t0)
        texto = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))
        texto = (texto or "").strip()
        if _es_alucinacion(texto):
            logger.info("[chat-ia] Transcripción descartada (sin_voz): %r", texto[:60])
            return {"texto": "", "motivo": "sin_voz"}
        return {"texto": texto, "modo": "premium"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error transcribiendo audio")
        raise HTTPException(status_code=502, detail="Error al transcribir el audio")


@router.post("/validar-direccion")
async def validar_direccion_maps(datos: DireccionInput):
    """Valida la dirección con Google Geocoding API y devuelve lat/lng + distrito."""
    import httpx
    api_key = settings.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Google Maps no configurado")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{datos.direccion}, Lima, Peru", "key": api_key, "language": "es", "region": "pe"}
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            resp = await http_client.get(url, params=params)
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de geocodificación: {e}")

    if data.get("status") != "OK" or not data.get("results"):
        return {"valida": False, "mensaje": "No se encontró la dirección"}

    result = data["results"][0]
    distrito = None
    for comp in result.get("address_components", []):
        t = comp.get("types", [])
        if "locality" in t or "sublocality_level_1" in t:
            distrito = comp.get("long_name")
            break
    loc = result["geometry"]["location"]
    return {
        "valida": True,
        "direccion_formateada": result.get("formatted_address"),
        "lat": loc["lat"], "lng": loc["lng"],
        "distrito": distrito,
    }
