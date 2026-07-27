"""
API REST de administración MITA (CRUD).
Montado en main.py sin prefijo extra (el router ya define /api/v1/admin).

Entidades:
  - Categorías / Tipos de servicio (catálogo)
  - Distritos / Tiempos entre distritos
  - Tarifas y Configuración general
  - Personal (lectura + alta básica)

NOTA: sin autenticación por ahora (pendiente proteger con rol admin).
Requiere la BD (Railway) con las tablas de zMita-1/2 creadas.
"""

from typing import Optional
import datetime as _dt
import decimal
import enum as _enum

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CategoriaServicio, TipoServicio
from app.models.personal import (
    Personal, TecnicoPersonal, Secretaria, Distrito, TiempoEntreDistritos,
    TipoPersonal, EstadoPersonal,
)
from app.models.configuracion import ConfiguracionGeneral, TarifaServicio
from app.models.auth_mita import UsuarioMita
from app.models.ubigeo import Ubigeo

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ============================================
# HELPERS
# ============================================

def _to_dict(obj) -> dict:
    """Serializa un modelo SQLAlchemy a dict JSON-safe."""
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, _enum.Enum):
            val = val.value
        elif isinstance(val, decimal.Decimal):
            val = float(val)
        elif isinstance(val, (_dt.datetime, _dt.date, _dt.time)):
            val = val.isoformat()
        out[col.name] = val
    return out


def _filtrar_columnas(model, data: dict) -> dict:
    """Deja solo las claves que son columnas del modelo (evita kwargs inválidos)."""
    cols = {c.name for c in model.__table__.columns}
    return {k: v for k, v in data.items() if k in cols and k != "id"}


def _crud_basico(model, prefijo: str, orden_col: Optional[str] = None):
    """Registra GET(list)/GET(id)/POST/PUT/DELETE genéricos para un modelo simple."""

    @router.get(f"/{prefijo}", name=f"listar_{prefijo}")
    def listar(db: Session = Depends(get_db)):
        q = db.query(model)
        if orden_col and hasattr(model, orden_col):
            q = q.order_by(getattr(model, orden_col))
        return {"success": True, "items": [_to_dict(x) for x in q.all()]}

    @router.get(f"/{prefijo}/{{item_id}}", name=f"obtener_{prefijo}")
    def obtener(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(404, f"{prefijo} no encontrado")
        return _to_dict(obj)

    @router.post(f"/{prefijo}", name=f"crear_{prefijo}", status_code=201)
    def crear(data: dict = Body(...), db: Session = Depends(get_db)):
        obj = model(**_filtrar_columnas(model, data))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _to_dict(obj)

    @router.put(f"/{prefijo}/{{item_id}}", name=f"actualizar_{prefijo}")
    def actualizar(item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(404, f"{prefijo} no encontrado")
        for k, v in _filtrar_columnas(model, data).items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return _to_dict(obj)

    @router.delete(f"/{prefijo}/{{item_id}}", name=f"eliminar_{prefijo}")
    def eliminar(item_id: int, db: Session = Depends(get_db)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(404, f"{prefijo} no encontrado")
        db.delete(obj)
        db.commit()
        return {"success": True, "eliminado": item_id}


# ============================================
# CRUD genéricos (columnas simples, sin enums Python)
# ============================================
_crud_basico(CategoriaServicio, "categorias", orden_col="orden")
_crud_basico(TipoServicio, "tipos", orden_col="nombre")
_crud_basico(Distrito, "distritos", orden_col="nombre")
_crud_basico(TiempoEntreDistritos, "tiempos-distritos")
_crud_basico(TarifaServicio, "tarifas")


# ============================================
# CONFIGURACIÓN GENERAL (por clave)
# ============================================

@router.get("/config")
def listar_config(db: Session = Depends(get_db)):
    items = db.query(ConfiguracionGeneral).order_by(ConfiguracionGeneral.categoria).all()
    return {"success": True, "items": [_to_dict(x) for x in items]}


@router.get("/config/{clave}")
def obtener_config(clave: str, db: Session = Depends(get_db)):
    cfg = db.query(ConfiguracionGeneral).filter(ConfiguracionGeneral.clave == clave).first()
    if not cfg:
        raise HTTPException(404, "Configuración no encontrada")
    return _to_dict(cfg)


@router.put("/config/{clave}")
def actualizar_config(clave: str, data: dict = Body(...), db: Session = Depends(get_db)):
    cfg = db.query(ConfiguracionGeneral).filter(ConfiguracionGeneral.clave == clave).first()
    if not cfg:
        cfg = ConfiguracionGeneral(clave=clave, **_filtrar_columnas(ConfiguracionGeneral, data))
        db.add(cfg)
    else:
        for k, v in _filtrar_columnas(ConfiguracionGeneral, data).items():
            setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return _to_dict(cfg)


# ============================================
# PERSONAL (lectura + alta básica con manejo de enums)
# ============================================

@router.get("/personal")
def listar_personal(tipo: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Personal)
    if tipo:
        try:
            q = q.filter(Personal.tipo == TipoPersonal(tipo))
        except ValueError:
            raise HTTPException(400, f"tipo inválido: {tipo}")
    return {"success": True, "items": [_to_dict(x) for x in q.all()]}


@router.post("/personal", status_code=201)
def crear_personal(data: dict = Body(...), db: Session = Depends(get_db)):
    payload = _filtrar_columnas(Personal, data)
    # Coerción de enums desde string
    if "tipo" in payload and payload["tipo"] is not None:
        try:
            payload["tipo"] = TipoPersonal(payload["tipo"])
        except ValueError:
            raise HTTPException(400, f"tipo inválido: {payload['tipo']}")
    if "estado" in payload and payload["estado"] is not None:
        try:
            payload["estado"] = EstadoPersonal(payload["estado"])
        except ValueError:
            raise HTTPException(400, f"estado inválido: {payload['estado']}")
    obj = Personal(**payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.delete("/personal/{item_id}")
def eliminar_personal(item_id: int, db: Session = Depends(get_db)):
    obj = db.query(Personal).get(item_id)
    if not obj:
        raise HTTPException(404, "Personal no encontrado")
    db.delete(obj)
    db.commit()
    return {"success": True, "eliminado": item_id}


@router.get("/tecnicos")
def listar_tecnicos(db: Session = Depends(get_db)):
    return {"success": True, "items": [_to_dict(x) for x in db.query(TecnicoPersonal).all()]}


@router.get("/secretarias")
def listar_secretarias(db: Session = Depends(get_db)):
    return {"success": True, "items": [_to_dict(x) for x in db.query(Secretaria).all()]}


@router.get("/ubigeos")
def listar_ubigeos(db: Session = Depends(get_db)):
    """Lista de ubigeos activos para el buscador de distritos."""
    ubigeos = (
        db.query(Ubigeo)
        .filter(Ubigeo.activo == True)
        .order_by(Ubigeo.distrito)
        .all()
    )
    return [
        {"id": u.id, "codigo": u.codigo, "departamento": u.departamento,
         "provincia": u.provincia, "distrito": u.distrito}
        for u in ubigeos
    ]


@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    """Usuarios del panel (usuarios_mita) — sin exponer el password_hash."""
    items = db.query(UsuarioMita).order_by(UsuarioMita.tipo, UsuarioMita.dni).all()
    out = []
    for u in items:
        d = _to_dict(u)
        d.pop("password_hash", None)
        out.append(d)
    return {"success": True, "items": out}


@router.post("/reset-password/{dni}")
def reset_password_admin(dni: str, db: Session = Depends(get_db)):
    """Resetea la clave de un usuario a su DNI, la marca para cambio y desbloquea la cuenta."""
    import bcrypt
    usuario = db.query(UsuarioMita).filter(UsuarioMita.dni == dni).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # bcrypt directo (passlib es incompatible con bcrypt>=4.1 en este entorno); 72 bytes máx
    usuario.password_hash = bcrypt.hashpw(dni.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
    usuario.requiere_cambio_clave = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()
    return {"success": True, "message": f"Clave reseteada para {dni} (nueva clave = DNI, cambio obligatorio)."}


@router.put("/usuarios/{item_id}")
def actualizar_usuario(item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Actualiza un usuario del panel (p.ej. activar/desactivar)."""
    u = db.query(UsuarioMita).get(item_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if "activo" in data:
        u.activo = bool(data["activo"])
    db.commit()
    d = _to_dict(u)
    d.pop("password_hash", None)
    return d
