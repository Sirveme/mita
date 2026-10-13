"""
Capa de síntesis de voz (TTS) con proveedores intercambiables (zMita-29).

sintetizar(texto, cfg) -> bytes MP3, donde cfg = {proveedor, voz, velocidad, instrucciones}.
Proveedores: openai (gpt-4o-mini-tts / tts-1), azure (Neural, SSML), elevenlabs.
Un proveedor sin su API key simplemente no aparece en voces_disponibles().
Cache en memoria por hash(proveedor+voz+velocidad+instrucciones+texto).
"""
import os
import logging
from hashlib import sha256

from app.core.config import settings

logger = logging.getLogger("mita.tts")

INSTRUCCIONES_DEFAULT = ("Habla en español peruano de Lima, tono cálido y profesional, "
                         "ritmo natural, cercano, sin sonar a locutor de radio. "
                         "Habla exclusivamente en español; nunca cambies a inglés.")
_ES_ONLY = "Habla exclusivamente en español; nunca cambies a inglés."

# Voces por proveedor (las de OpenAI gpt-4o-mini-tts son neutras/multilingües)
OPENAI_VOCES = ["coral", "nova", "sage", "shimmer", "ash", "alloy", "onyx"]
AZURE_VOCES = ["es-PE-CamilaNeural", "es-PE-AlexNeural"]

# Costo aprox. por respuesta corta (~250 car.), solo referencia para el laboratorio
COSTO_APROX = {"openai": "~US$0.0004", "openai-tts1": "~US$0.0004", "azure": "~US$0.004 (gratis hasta 0.5M car/mes)", "elevenlabs": "~US$0.01"}


def _openai_key():
    return settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")


def _openai_client():
    key = _openai_key()
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:
        return None


def voces_disponibles() -> list:
    """Voces listas para usar según las keys configuradas. OpenAI siempre que haya key."""
    out = []
    if _openai_key():
        for v in OPENAI_VOCES:
            out.append({"proveedor": "openai", "voz": v, "label": f"OpenAI · {v}", "costo": COSTO_APROX["openai"]})
        out.append({"proveedor": "openai-tts1", "voz": "shimmer", "label": "OpenAI tts-1 · shimmer (referencia)", "costo": COSTO_APROX["openai-tts1"]})
    if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
        for v in AZURE_VOCES:
            out.append({"proveedor": "azure", "voz": v, "label": f"Azure Neural · {v}", "costo": COSTO_APROX["azure"]})
    if settings.ELEVENLABS_API_KEY:
        out.append({"proveedor": "elevenlabs", "voz": os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"),
                    "label": "ElevenLabs · multilingüe", "costo": COSTO_APROX["elevenlabs"]})
    return out


def proveedores_activos() -> list:
    p = []
    if _openai_key():
        p.append("openai")
    if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
        p.append("azure")
    if settings.ELEVENLABS_API_KEY:
        p.append("elevenlabs")
    return p


_CACHE = {}   # hash -> bytes


def _clave(cfg, texto):
    base = "|".join([cfg.get("proveedor", ""), cfg.get("voz", ""), str(cfg.get("velocidad", "")),
                     (cfg.get("instrucciones") or "")[:60], texto])
    return sha256(base.encode("utf-8")).hexdigest()


def _openai_tts(texto, cfg, modelo):
    client = _openai_client()
    if client is None:
        raise RuntimeError("openai no configurado")
    voz = cfg.get("voz") or "coral"
    speed = float(cfg.get("velocidad") or 1.0)
    kwargs = {"model": modelo, "voice": voz, "input": texto}
    # gpt-4o-mini-tts admite instrucciones de estilo; tts-1 admite speed
    if modelo == "gpt-4o-mini-tts":
        instr = cfg.get("instrucciones") or INSTRUCCIONES_DEFAULT
        if "espa" not in instr.lower():   # reforzar español aunque el admin ponga instrucciones propias
            instr = instr.rstrip(". ") + ". " + _ES_ONLY
        try:
            resp = client.audio.speech.create(instructions=instr, **kwargs)
            return _leer(resp)
        except Exception:
            pass  # algún SDK no admite instructions -> reintento simple abajo
    try:
        resp = client.audio.speech.create(speed=speed, **kwargs)
    except Exception:
        resp = client.audio.speech.create(**kwargs)
    return _leer(resp)


def _leer(resp):
    return resp.read() if hasattr(resp, "read") else (resp.content if hasattr(resp, "content") else bytes(resp))


def _azure_tts(texto, cfg):
    import httpx
    region = settings.AZURE_SPEECH_REGION
    key = settings.AZURE_SPEECH_KEY
    voz = cfg.get("voz") or "es-PE-CamilaNeural"
    # rate: 1.0 -> 0%; 1.1 -> +10%
    pct = int(round((float(cfg.get("velocidad") or 1.0) - 1.0) * 100))
    rate = f"{'+' if pct >= 0 else ''}{pct}%"
    ssml = (f"<speak version='1.0' xml:lang='es-PE'><voice name='{voz}'>"
            f"<prosody rate='{rate}'>{_xml(texto)}</prosody></voice></speak>")
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
               "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"}
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers=headers, content=ssml.encode("utf-8"))
        r.raise_for_status()
        return r.content


def _xml(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _elevenlabs_tts(texto, cfg):
    import httpx
    key = settings.ELEVENLABS_API_KEY
    voice_id = cfg.get("voz") or os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    body = {"text": texto, "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.content


def sintetizar(texto, cfg) -> bytes:
    """Devuelve MP3. Lanza excepción si el proveedor falla/no está configurado."""
    cfg = cfg or {}
    from app.services.texto import texto_para_voz
    texto = texto_para_voz(texto)      # Parte D: voz siempre en español y bien leída
    prov = (cfg.get("proveedor") or "openai").lower()
    k = _clave(cfg, texto)
    if k in _CACHE:
        return _CACHE[k]
    if prov == "openai":
        audio = _openai_tts(texto, cfg, "gpt-4o-mini-tts")
    elif prov == "openai-tts1":
        audio = _openai_tts(texto, cfg, "tts-1")
    elif prov == "azure":
        audio = _azure_tts(texto, cfg)
    elif prov == "elevenlabs":
        audio = _elevenlabs_tts(texto, cfg)
    else:
        audio = _openai_tts(texto, cfg, "gpt-4o-mini-tts")
    if len(_CACHE) > 300:
        _CACHE.clear()
    _CACHE[k] = audio
    return audio
