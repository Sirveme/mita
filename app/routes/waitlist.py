"""
Lista de espera por distrito.
  POST /api/v1/waitlist                      (público) — el cliente deja su contacto
  GET  /api/v1/admin/waitlist                (admin)   — lista con filtros
  POST /api/v1/admin/waitlist/{id}/notificar (admin)   — marcar como notificado
  GET  /api/v1/admin/waitlist/export.csv     (admin)   — export CSV
"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.waitlist import WaitlistDistrito
from app.routes.admin_postulantes import require_admin_gerente

router = APIRouter(tags=["Waitlist"])


# ============================================
# Público: el cliente se registra
# ============================================

@router.post("/api/v1/waitlist")
def crear_waitlist(data: dict = Body(...), db: Session = Depends(get_db)):
    email = (data.get("email") or "").strip()
    if "@" not in email or len(email) < 5:
        raise HTTPException(400, "Email inválido.")
    item = WaitlistDistrito(
        email=email,
        telefono=(data.get("telefono") or None),
        distrito_id=data.get("distrito_id") or None,
        distrito_nombre=(data.get("distrito_nombre") or None),
        categoria_interes=(data.get("categoria_interes") or None),
        mensaje=(data.get("mensaje") or None),
    )
    db.add(item)
    db.commit()
    return {"success": True, "mensaje": "Te avisaremos cuando lleguemos a tu zona"}


# ============================================
# Admin
# ============================================

def _dict(w: WaitlistDistrito) -> dict:
    return {
        "id": w.id, "email": w.email, "telefono": w.telefono,
        "distrito_id": w.distrito_id, "distrito_nombre": w.distrito_nombre,
        "categoria_interes": w.categoria_interes, "mensaje": w.mensaje,
        "notificado": bool(w.notificado),
        "creado_en": w.creado_en.isoformat() if w.creado_en else None,
    }


def _query(db: Session, distrito_id: Optional[int], notificado: Optional[str]):
    q = db.query(WaitlistDistrito)
    if distrito_id:
        q = q.filter(WaitlistDistrito.distrito_id == distrito_id)
    if notificado in ("true", "false"):
        q = q.filter(WaitlistDistrito.notificado.is_(notificado == "true"))
    return q.order_by(WaitlistDistrito.creado_en.desc())


@router.get("/api/v1/admin/waitlist")
def listar_waitlist(distrito_id: Optional[int] = None, notificado: Optional[str] = None,
                    db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    items = _query(db, distrito_id, notificado).all()
    return {"success": True, "total": len(items), "items": [_dict(w) for w in items]}


@router.post("/api/v1/admin/waitlist/{item_id}/notificar")
def marcar_notificado(item_id: int, data: dict = Body(default={}),
                      db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    w = db.query(WaitlistDistrito).get(item_id)
    if not w:
        raise HTTPException(404, "No encontrado")
    w.notificado = bool(data.get("notificado", True))
    db.commit()
    return {"success": True, "notificado": w.notificado}


@router.get("/api/v1/admin/waitlist/export.csv")
def exportar_csv(distrito_id: Optional[int] = None, notificado: Optional[str] = None,
                 db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    items = _query(db, distrito_id, notificado).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "email", "telefono", "distrito", "categoria", "mensaje", "notificado", "creado_en"])
    for i in items:
        w.writerow([i.id, i.email, i.telefono or "", i.distrito_nombre or "", i.categoria_interes or "",
                    (i.mensaje or "").replace("\n", " "), "si" if i.notificado else "no",
                    i.creado_en.isoformat() if i.creado_en else ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=waitlist_distrito.csv"},
    )
