"""
API pública de postulación de técnicos (proveedores).

Montado en main.py con prefix="/api/v1/postulacion".
No requiere autenticación. Los documentos se envían por email (no se guardan).
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Body, Form, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.postulante import Postulante, EstadoPostulante
from app.models.personal import Personal
from app.models.tipo_documento import TipoDocumentoPostulacion
from app.services import sunat_service
from app.services.email_service import enviar_email, RRHH_EMAIL

logger = logging.getLogger("mita.postulacion")

router = APIRouter(prefix="/api/v1/postulacion", tags=["Postulación"])

MAX_ADJUNTO_BYTES = 8 * 1024 * 1024   # 8 MB por archivo
BASE_URL = "https://mita.pe"


# ============================================
# Helpers
# ============================================

def _generar_codigo(db: Session) -> str:
    """POST-YYYYMM-XXXX incremental por mes."""
    prefijo = f"POST-{datetime.utcnow():%Y%m}-"
    n = db.query(Postulante).filter(Postulante.codigo.like(prefijo + "%")).count()
    return f"{prefijo}{n + 1:04d}"


def _dni_registrado(db: Session, dni: str) -> Optional[str]:
    """Devuelve un mensaje si el DNI ya existe en postulantes o personal."""
    if db.query(Postulante).filter(Postulante.dni == dni).first():
        return "Ya tienes una postulación registrada con este DNI."
    if db.query(Personal).filter(Personal.dni == dni).first():
        return "Ya existe una cuenta asociada a este DNI."
    return None


# ============================================
# Validación inicial
# ============================================

@router.post("/validar-dni")
def validar_dni(data: dict = Body(...), db: Session = Depends(get_db)):
    dni = (data.get("dni") or "").strip()
    if len(dni) != 8 or not dni.isdigit():
        raise HTTPException(400, "El DNI debe tener 8 dígitos.")

    ya = _dni_registrado(db, dni)
    if ya:
        return {"disponible": False, "mensaje": ya}

    datos = sunat_service.consultar_dni(dni)
    if datos and (datos.get("nombres") or datos.get("apellido_paterno")):
        return {
            "disponible": True,
            "encontrado": True,
            "nombres": datos.get("nombres", ""),
            "apellido_paterno": datos.get("apellido_paterno", ""),
            "apellido_materno": datos.get("apellido_materno", ""),
            "mensaje": "Datos encontrados. Verifica y continúa.",
        }
    # No se encontró (o sin token): pedir RUC para validar identidad
    return {
        "disponible": True,
        "encontrado": False,
        "mensaje": "No pudimos validar tu DNI automáticamente. Ingresa tu RUC de persona natural.",
    }


@router.post("/validar-ruc")
def validar_ruc(data: dict = Body(...), db: Session = Depends(get_db)):
    dni = (data.get("dni") or "").strip()
    ruc = (data.get("ruc") or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(400, "El RUC debe tener 11 dígitos.")
    if not sunat_service.ruc_contiene_dni(ruc, dni):
        return {"valido": False, "mensaje": "El RUC no corresponde al DNI ingresado."}
    if db.query(Postulante).filter(Postulante.ruc == ruc).first():
        return {"valido": False, "mensaje": "Este RUC ya está registrado en una postulación."}
    info = sunat_service.consultar_ruc(ruc) or {}
    return {"valido": True, "mensaje": "RUC válido.", "razon_social": info.get("razon_social", "")}


@router.get("/tipos-documento")
def tipos_documento(db: Session = Depends(get_db)):
    tipos = (
        db.query(TipoDocumentoPostulacion)
        .filter(TipoDocumentoPostulacion.activo.is_(True))
        .order_by(TipoDocumentoPostulacion.orden)
        .all()
    )
    return [
        {"codigo": t.codigo, "nombre": t.nombre, "descripcion": t.descripcion,
         "obligatorio": bool(t.obligatorio)}
        for t in tipos
    ]


# ============================================
# Envío de la postulación
# ============================================

@router.post("/enviar")
async def enviar_postulacion(
    payload: str = Form(...),
    documentos_meta: str = Form("[]"),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """Crea el postulante, envía email a RRHH con adjuntos y devuelve el código."""
    try:
        data = json.loads(payload)
    except Exception:
        raise HTTPException(400, "payload inválido (JSON).")

    dni = (data.get("dni") or "").strip()
    if len(dni) != 8 or not dni.isdigit():
        raise HTTPException(400, "DNI inválido.")
    ya = _dni_registrado(db, dni)
    if ya:
        raise HTTPException(409, ya)

    # Validaciones mínimas
    especialidades = data.get("especialidades") or []
    if not especialidades:
        raise HTTPException(400, "Selecciona al menos una especialidad.")
    for campo in ("nombres", "celular_1", "email"):
        if not (data.get(campo) or "").strip():
            raise HTTPException(400, f"Falta el campo obligatorio: {campo}.")
    for campo in ("banco", "numero_cuenta", "cci", "yape", "plin"):
        if not (data.get(campo) or "").strip():
            raise HTTPException(400, f"Datos de pago incompletos: {campo}.")

    # Adjuntos (se envían por email, no se guardan)
    try:
        metas = json.loads(documentos_meta)
    except Exception:
        metas = []
    adjuntos, docs_declarados = [], []
    for idx, uf in enumerate(archivos):
        contenido = await uf.read()
        if len(contenido) > MAX_ADJUNTO_BYTES:
            raise HTTPException(400, f"El archivo {uf.filename} supera 8 MB.")
        tipo = metas[idx].get("tipo") if idx < len(metas) and isinstance(metas[idx], dict) else "documento"
        adjuntos.append({"filename": uf.filename or f"{tipo}.bin", "content": contenido,
                         "mimetype": uf.content_type or "application/octet-stream"})
        docs_declarados.append({"tipo": tipo, "nombre_archivo": uf.filename, "enviado_email": True})

    # Fecha de nacimiento
    fnac = None
    if data.get("fecha_nacimiento"):
        try:
            fnac = datetime.strptime(data["fecha_nacimiento"], "%Y-%m-%d").date()
        except Exception:
            fnac = None

    codigo = _generar_codigo(db)
    post = Postulante(
        codigo=codigo,
        estado=EstadoPostulante.PENDIENTE.value,
        dni=dni,
        ruc=(data.get("ruc") or None),
        nombres=data.get("nombres", "").strip(),
        apellido_paterno=(data.get("apellido_paterno") or "").strip() or None,
        apellido_materno=(data.get("apellido_materno") or "").strip() or None,
        fecha_nacimiento=fnac,
        sexo=(data.get("sexo") or None),
        celular_1=data.get("celular_1", "").strip(),
        celular_2=(data.get("celular_2") or None),
        email=data.get("email", "").strip(),
        departamento=(data.get("departamento") or None),
        provincia=(data.get("provincia") or None),
        distrito=(data.get("distrito") or None),
        direccion=(data.get("direccion") or None),
        referencia=(data.get("referencia") or None),
        especialidades=especialidades,
        anios_experiencia=int(data.get("anios_experiencia") or 0),
        experiencia_laboral=data.get("experiencia_laboral") or [],
        nivel_educativo=(data.get("nivel_educativo") or None),
        institucion=(data.get("institucion") or None),
        certificaciones=(data.get("certificaciones") or None),
        banco=data.get("banco"),
        numero_cuenta=data.get("numero_cuenta"),
        cci=data.get("cci"),
        yape=data.get("yape"),
        plin=data.get("plin"),
        sol_usuario=(data.get("sol_usuario") or None),
        sol_clave_encriptada=(data.get("sol_clave") or None),  # TODO: cifrar realmente
        emision_automatica_rxh=bool(data.get("emision_automatica_rxh")),
        documentos_enviados=docs_declarados,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # Email a RRHH
    asunto = f"[MITA] Nueva postulación: {codigo} - {post.nombre_completo}"
    cuerpo = _email_rrhh_html(post)
    enviado = enviar_email(RRHH_EMAIL, asunto, cuerpo, adjuntos=adjuntos)
    if not enviado:
        logger.warning("Postulación %s guardada, pero el email a RRHH no se envió (SMTP?).", codigo)

    return {"success": True, "codigo": codigo, "email": post.email, "email_enviado": enviado}


def _email_rrhh_html(p: Postulante) -> str:
    esp = ", ".join(p.especialidades or [])
    return f"""
    <div style="font-family:Arial,sans-serif;color:#222">
      <h2>Nueva postulación MITA</h2>
      <p><b>Código:</b> {p.codigo}<br>
         <b>Estado:</b> {p.estado}<br>
         <b>Fecha:</b> {datetime.utcnow():%d/%m/%Y %H:%M} UTC</p>
      <h3>Postulante</h3>
      <p><b>Nombre:</b> {p.nombre_completo}<br>
         <b>DNI:</b> {p.dni} &nbsp; <b>RUC:</b> {p.ruc or '-'}<br>
         <b>Celular:</b> {p.celular_1} {('/ ' + p.celular_2) if p.celular_2 else ''}<br>
         <b>Email:</b> {p.email}</p>
      <h3>Perfil</h3>
      <p><b>Especialidades:</b> {esp}<br>
         <b>Años de experiencia:</b> {p.anios_experiencia}<br>
         <b>Formación:</b> {p.nivel_educativo or '-'} — {p.institucion or '-'}</p>
      <h3>Pago</h3>
      <p><b>Banco:</b> {p.banco} &nbsp; <b>Cuenta:</b> {p.numero_cuenta}<br>
         <b>CCI:</b> {p.cci}<br>
         <b>Yape:</b> {p.yape} &nbsp; <b>Plin:</b> {p.plin}</p>
      <p style="color:#666;font-size:13px">Documentos adjuntos en este correo.
         Ver en panel: <a href="{BASE_URL}/admin/postulantes/{p.id}">{BASE_URL}/admin/postulantes/{p.id}</a></p>
    </div>
    """
