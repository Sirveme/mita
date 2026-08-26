"""
Panel admin de postulantes + gestión de tipos de documento.
Montado en main.py (el router define su propio prefix /api/v1/admin).
"""

import logging
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.postulante import Postulante, EstadoPostulante
from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal
from app.models.models import CategoriaServicio
from app.models.auth_mita import UsuarioMita
from app.models.tipo_documento import TipoDocumentoPostulacion
from app.routes.login_mita import hash_password
from app.services.email_service import enviar_email

# Especialidad del postulante (etiqueta) -> código de categoría (categorias_servicio.codigo)
ESPECIALIDAD_A_CODIGO = {
    "ELECTRICIDAD": "ELEC",
    "GASFITERIA": "GASF",
    "ELECTRODOMESTICOS": "ELDOM",
    "MUEBLES": "MUEB",
}


def _mapear_especialidades(db: Session, especialidades: list) -> list:
    """Convierte ['ELECTRICIDAD', ...] a [id_categoria, ...] usando categorias_servicio.
    Loguea advertencia por cada especialidad/categoría no encontrada, pero continúa."""
    ids = []
    for esp in (especialidades or []):
        codigo = ESPECIALIDAD_A_CODIGO.get(str(esp).upper())
        if not codigo:
            logger.warning("Especialidad sin mapeo de código: %r", esp)
            continue
        cat = db.query(CategoriaServicio).filter(CategoriaServicio.codigo == codigo).first()
        if not cat:
            logger.warning("Categoría no encontrada en BD para código %s (especialidad %s)", codigo, esp)
            continue
        if cat.id not in ids:
            ids.append(cat.id)
    return ids

logger = logging.getLogger("mita.admin_postulantes")

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Postulantes"])

_ESTADOS = {e.value for e in EstadoPostulante}


def _dict(p: Postulante) -> dict:
    return {
        "id": p.id, "codigo": p.codigo, "estado": p.estado, "dni": p.dni, "ruc": p.ruc,
        "nombres": p.nombres, "apellido_paterno": p.apellido_paterno, "apellido_materno": p.apellido_materno,
        "nombre_completo": p.nombre_completo,
        "fecha_nacimiento": p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else None,
        "sexo": p.sexo, "celular_1": p.celular_1, "celular_2": p.celular_2, "email": p.email,
        "departamento": p.departamento, "provincia": p.provincia, "distrito": p.distrito,
        "direccion": p.direccion, "referencia": p.referencia,
        "especialidades": p.especialidades or [], "anios_experiencia": p.anios_experiencia,
        "experiencia_laboral": p.experiencia_laboral or [],
        "nivel_educativo": p.nivel_educativo, "institucion": p.institucion, "certificaciones": p.certificaciones,
        "banco": p.banco, "numero_cuenta": p.numero_cuenta, "cci": p.cci, "yape": p.yape, "plin": p.plin,
        "sol_usuario": p.sol_usuario, "emision_automatica_rxh": p.emision_automatica_rxh,
        "documentos_enviados": p.documentos_enviados or [],
        "fecha_postulacion": p.fecha_postulacion.isoformat() if p.fecha_postulacion else None,
        "fecha_revision": p.fecha_revision.isoformat() if p.fecha_revision else None,
        "revisado_por": p.revisado_por, "observaciones": p.observaciones,
    }


# ============================================
# Lista y detalle
# ============================================

@router.get("/postulantes")
def listar_postulantes(
    estado: Optional[str] = None,
    especialidad: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Postulante)
    if estado and estado.upper() in _ESTADOS:
        query = query.filter(Postulante.estado == estado.upper())
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Postulante.nombres.ilike(like)) | (Postulante.dni.ilike(like)) | (Postulante.codigo.ilike(like))
        )
    postulantes = query.order_by(Postulante.fecha_postulacion.desc()).all()
    # Especialidad: filtrar en Python (JSONB array de strings)
    if especialidad:
        postulantes = [p for p in postulantes if especialidad.upper() in (p.especialidades or [])]
    return {"success": True, "items": [_dict(p) for p in postulantes]}


@router.get("/postulantes/{item_id}")
def detalle_postulante(item_id: int, db: Session = Depends(get_db)):
    p = db.query(Postulante).get(item_id)
    if not p:
        raise HTTPException(404, "Postulante no encontrado")
    return _dict(p)


# ============================================
# Acciones de revisión
# ============================================

@router.post("/postulantes/{item_id}/aprobar")
def aprobar_postulante(item_id: int, data: dict = Body(default={}), db: Session = Depends(get_db)):
    p = db.query(Postulante).get(item_id)
    if not p:
        raise HTTPException(404, "Postulante no encontrado")
    if p.estado == EstadoPostulante.APROBADO.value:
        raise HTTPException(409, "El postulante ya fue aprobado.")

    revisado_por = (data.get("revisado_por") or "admin").strip()

    # Evitar duplicar personal/usuario si el DNI ya existe
    if db.query(UsuarioMita).filter(UsuarioMita.dni == p.dni).first():
        raise HTTPException(409, "Ya existe un usuario con este DNI.")

    # 1) Crear registro en personal (proveedor / técnico)
    persona = Personal(
        tipo=TipoPersonal.TECNICO,
        dni=p.dni,
        nombres=p.nombres,
        apellido_paterno=p.apellido_paterno or "-",
        apellido_materno=p.apellido_materno,
        fecha_nacimiento=p.fecha_nacimiento,
        sexo=p.sexo,
        telefono=p.celular_1,
        celular_2=p.celular_2,
        email=p.email,
        direccion=p.direccion,
        referencia=p.referencia,
        estado=EstadoPersonal.ACTIVO,
        banco=p.banco,
        numero_cuenta=p.numero_cuenta,
        cci=p.cci,
        ruc=p.ruc,
        emite_recibo_honorarios=bool(p.emision_automatica_rxh),
        tipo_relacion="PROVEEDOR",
        postulante_id=p.id,
    )
    db.add(persona)
    db.flush()  # obtiene persona.id

    # 1b) Registro de técnico con especialidades mapeadas a IDs de categoría
    especialidad_ids = _mapear_especialidades(db, p.especialidades)
    tecnico = TecnicoPersonal(
        personal_id=persona.id,
        especialidades=especialidad_ids or None,
    )
    db.add(tecnico)

    # 2) Crear usuario_mita con clave temporal (fuerza cambio en el primer login)
    clave_temporal = f"{p.dni[:4]}{secrets.token_hex(2)}"  # ej: 4512a3f9
    usuario = UsuarioMita(
        dni=p.dni,
        password_hash=hash_password(clave_temporal),
        tipo="tecnico",
        nombres=p.nombre_completo,
        email=p.email,
        personal_id=persona.id,
        activo=True,
        requiere_cambio_clave=True,
    )
    db.add(usuario)

    # 3) Actualizar estado del postulante
    p.estado = EstadoPostulante.APROBADO.value
    p.fecha_revision = datetime.utcnow()
    p.revisado_por = revisado_por
    db.commit()

    # 4) Email con credenciales
    asunto = "[MITA] ¡Tu postulación fue aprobada!"
    cuerpo = f"""
    <div style="font-family:Arial,sans-serif;color:#222">
      <h2>¡Bienvenido a MITA, {p.nombres}!</h2>
      <p>Tu postulación <b>{p.codigo}</b> fue <b>aprobada</b>. Ya puedes ingresar a la plataforma de técnicos.</p>
      <p><b>Usuario (DNI):</b> {p.dni}<br>
         <b>Clave temporal:</b> {clave_temporal}</p>
      <p>Por seguridad, deberás cambiar tu clave en el primer ingreso.</p>
      <p><a href="https://mita.pe/login">Ingresar a MITA</a></p>
    </div>
    """
    enviado = enviar_email(p.email, asunto, cuerpo)

    return {
        "success": True, "personal_id": persona.id, "usuario_id": usuario.id,
        "tecnico_id": tecnico.id, "especialidades_mapeadas": especialidad_ids,
        "clave_temporal": clave_temporal,  # visible para el admin si el email no salió
        "email_enviado": enviado,
    }


@router.post("/postulantes/{item_id}/rechazar")
def rechazar_postulante(item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    p = db.query(Postulante).get(item_id)
    if not p:
        raise HTTPException(404, "Postulante no encontrado")
    motivo = (data.get("motivo") or "").strip()
    p.estado = EstadoPostulante.RECHAZADO.value
    p.observaciones = motivo or "Sin especificar"
    p.fecha_revision = datetime.utcnow()
    p.revisado_por = (data.get("revisado_por") or "admin").strip()
    db.commit()

    cuerpo = f"""
    <div style="font-family:Arial,sans-serif;color:#222">
      <h2>Sobre tu postulación {p.codigo}</h2>
      <p>Hola {p.nombres}, lamentamos informarte que tu postulación no fue aprobada en esta ocasión.</p>
      <p><b>Motivo:</b> {motivo or 'No especificado'}</p>
    </div>
    """
    enviado = enviar_email(p.email, "[MITA] Resultado de tu postulación", cuerpo)
    return {"success": True, "estado": p.estado, "email_enviado": enviado}


@router.post("/postulantes/{item_id}/observar")
def observar_postulante(item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    p = db.query(Postulante).get(item_id)
    if not p:
        raise HTTPException(404, "Postulante no encontrado")
    obs = (data.get("observaciones") or "").strip()
    if not obs:
        raise HTTPException(400, "Indica qué información falta.")
    p.estado = EstadoPostulante.OBSERVADO.value
    p.observaciones = obs
    p.fecha_revision = datetime.utcnow()
    p.revisado_por = (data.get("revisado_por") or "admin").strip()
    db.commit()

    cuerpo = f"""
    <div style="font-family:Arial,sans-serif;color:#222">
      <h2>Tu postulación {p.codigo} necesita información adicional</h2>
      <p>Hola {p.nombres}, para continuar con tu evaluación necesitamos:</p>
      <p>{obs}</p>
      <p>Responde a este correo con la información/documentos solicitados.</p>
    </div>
    """
    enviado = enviar_email(p.email, "[MITA] Tu postulación necesita más información", cuerpo)
    return {"success": True, "estado": p.estado, "email_enviado": enviado}


# ============================================
# Tipos de documento (CRUD) — dni_anverso/reverso son fijos
# ============================================

def _doc_dict(t: TipoDocumentoPostulacion) -> dict:
    return {"id": t.id, "codigo": t.codigo, "nombre": t.nombre, "descripcion": t.descripcion,
            "obligatorio": bool(t.obligatorio), "fijo": bool(t.fijo), "orden": t.orden, "activo": bool(t.activo)}


@router.get("/tipos-documento")
def listar_tipos_documento(db: Session = Depends(get_db)):
    tipos = db.query(TipoDocumentoPostulacion).order_by(TipoDocumentoPostulacion.orden).all()
    return {"success": True, "items": [_doc_dict(t) for t in tipos]}


@router.post("/tipos-documento", status_code=201)
def crear_tipo_documento(data: dict = Body(...), db: Session = Depends(get_db)):
    codigo = (data.get("codigo") or "").strip().lower().replace(" ", "_")
    if not codigo or not (data.get("nombre") or "").strip():
        raise HTTPException(400, "Código y nombre son obligatorios.")
    if db.query(TipoDocumentoPostulacion).filter(TipoDocumentoPostulacion.codigo == codigo).first():
        raise HTTPException(409, "Ya existe un tipo de documento con ese código.")
    t = TipoDocumentoPostulacion(
        codigo=codigo, nombre=data["nombre"].strip(), descripcion=(data.get("descripcion") or None),
        obligatorio=bool(data.get("obligatorio")), fijo=False,
        orden=int(data.get("orden") or 99), activo=bool(data.get("activo", True)),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _doc_dict(t)


@router.put("/tipos-documento/{item_id}")
def actualizar_tipo_documento(item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    t = db.query(TipoDocumentoPostulacion).get(item_id)
    if not t:
        raise HTTPException(404, "Tipo de documento no encontrado")
    if t.fijo:
        raise HTTPException(403, "Este documento es fijo y no puede editarse.")
    for campo in ("nombre", "descripcion"):
        if campo in data:
            setattr(t, campo, data[campo])
    if "obligatorio" in data:
        t.obligatorio = bool(data["obligatorio"])
    if "orden" in data:
        t.orden = int(data["orden"] or 99)
    if "activo" in data:
        t.activo = bool(data["activo"])
    db.commit()
    db.refresh(t)
    return _doc_dict(t)


@router.delete("/tipos-documento/{item_id}")
def eliminar_tipo_documento(item_id: int, db: Session = Depends(get_db)):
    t = db.query(TipoDocumentoPostulacion).get(item_id)
    if not t:
        raise HTTPException(404, "Tipo de documento no encontrado")
    if t.fijo:
        raise HTTPException(403, "Este documento es fijo y no puede eliminarse.")
    db.delete(t)
    db.commit()
    return {"success": True, "eliminado": item_id}
