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

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger("mita.chat_ia")
router = APIRouter(prefix="/api/v1/chat-ia", tags=["Chat IA"])

# Mapeo de las áreas del asistente a los códigos de categoría MITA
AREA_A_CODIGO = {
    "gasfiteria": "GASF",
    "electricidad": "ELEC",
    "linea_blanca": "ELDOM",
    "aire_acondicionado": "ELDOM",
    "albanileria_menor": "ALBA",
    "instalaciones_hogar": "MUEB",
    "cerrajeria": None,       # sin categoría MITA directa
    "computacion": None,
}

SYSTEM_PROMPT_CHAT_MITA = """
Eres el asistente virtual de MITA, un servicio de técnicos a domicilio en Lima, Perú.

Tu objetivo es extraer del mensaje del usuario:
1. Área de servicio
2. Problema específico
3. Dirección completa
4. Detalles adicionales

ÁREAS DE SERVICIO DISPONIBLES:
- gasfiteria: fugas, atoros, instalación de termas, grifería, inodoros, tanques
- electricidad: cortos, apagones, instalación de tomacorrientes, tableros, luminarias
- cerrajeria: chapas, llaves, cerraduras, puertas trabadas
- linea_blanca: refrigeradoras, lavadoras, secadoras, microondas
- aire_acondicionado: instalación, mantenimiento, reparación de AC, split
- computacion: PCs, laptops, redes, wifi, impresoras
- albanileria_menor: pintura, resanes, enchapes pequeños
- instalaciones_hogar: muebles, persianas, tendederos, camas, closets

DISTRITOS CON COBERTURA:
Miraflores, San Isidro, Surco, San Borja, La Molina, Barranco, Surquillo,
Jesus Maria, Lince, Magdalena, Pueblo Libre, San Miguel, Lima Centro

RESPONDE SIEMPRE EN JSON:
{
  "entendido": true/false,
  "area": "gasfiteria" | "electricidad" | "cerrajeria" | "linea_blanca" | "aire_acondicionado" | "computacion" | "albanileria_menor" | "instalaciones_hogar" | null,
  "problema": "descripcion corta del problema" | null,
  "direccion": {
    "texto_original": "lo que dijo el usuario",
    "calle": "nombre de calle/avenida" | null,
    "numero": "435" | null,
    "interior": "dpto 201" | null,
    "distrito": "Miraflores" | null,
    "referencia": "frente al parque" | null,
    "ambigua": true/false,
    "opciones": ["Av Larco, Miraflores", "Av Larco, Victor Larco Herrera"] | null
  },
  "detalles": {
    "ambiente": "cocina" | "bano" | "sala" | "dormitorio" | "garage" | null,
    "urgencia": "alta" | "normal" | null,
    "otros": "cualquier otro detalle relevante" | null
  },
  "completo": true/false,
  "faltante": ["direccion.numero", "area"] | [],
  "siguiente_pregunta": "En que distrito te encuentras?" | null,
  "confirmacion": "Entendi: Gasfiteria por fuga de agua en Av Larco 435, Miraflores" | null
}

REGLAS:
- Si el area no es clara, infiere del problema (fuga -> gasfiteria, cortocircuito -> electricidad)
- Si la direccion es ambigua (Av Larco existe en varios distritos), marca ambigua=true y da opciones
- Si falta informacion critica, indica que falta en "faltante" y sugiere pregunta
- "completo"=true SOLO si tienes: area + problema + calle + numero + distrito
- Se conciso en siguiente_pregunta (max 15 palabras)
- Si el distrito NO esta en cobertura, igual extrae todo pero indica en detalles.otros: "distrito sin cobertura"
- No inventes informacion que el usuario no proporciono
"""


class MensajeInput(BaseModel):
    mensaje: str
    contexto: List[dict] = []


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
    """Interpreta el mensaje del usuario y extrae entidades (área, problema, dirección)."""
    client = _openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Chat IA no disponible (OpenAI no configurado).")

    mensajes = [{"role": "system", "content": SYSTEM_PROMPT_CHAT_MITA}]
    for msg in (datos.contexto or [])[-4:]:
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
    return _enriquecer_categoria(db, data)


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
            response_format="text",
        )
        logger.info("[chat-ia] Whisper respondió en %.2fs", time.monotonic() - t0)
        texto = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))
        return {"texto": (texto or "").strip(), "modo": "premium"}
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
