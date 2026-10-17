"""
Panel: clientes de prueba (modo ensayo, zMita-45 D). Marcar por DNI o celular; su visita/reparación
cuestan monto_ensayo. No afecta a los demás clientes.
"""
import re
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.servicio_api import _es_admin

logger = logging.getLogger("mita.ensayo_admin")
router = APIRouter(tags=["Clientes de prueba"])


async def _guard(request, db):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")


@router.get("/api/v1/admin/clientes-prueba")
async def listar(request: Request, db: Session = Depends(get_db)):
    await _guard(request, db)
    from app.models.cliente_prueba import ClientePrueba
    from app.services.ensayo import monto_ensayo
    rows = db.query(ClientePrueba).order_by(ClientePrueba.id.desc()).all()
    return {"monto_ensayo": monto_ensayo(db),
            "items": [{"id": r.id, "dni": r.dni, "celular": r.celular, "nota": r.nota, "activo": bool(r.activo)}
                      for r in rows]}


@router.post("/api/v1/admin/clientes-prueba")
async def agregar(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    await _guard(request, db)
    from app.models.cliente_prueba import ClientePrueba
    d = data or {}
    dni = re.sub(r"\D", "", d.get("dni") or "") or None
    cel = re.sub(r"\D", "", d.get("celular") or "")
    cel = cel[-9:] if cel else None
    if not dni and not cel:
        raise HTTPException(status_code=422, detail="Indica un DNI o un celular.")
    if dni and len(dni) != 8:
        raise HTTPException(status_code=422, detail="El DNI debe tener 8 dígitos.")
    if cel and (len(cel) != 9 or not cel.startswith("9")):
        raise HTTPException(status_code=422, detail="El celular debe tener 9 dígitos y empezar con 9.")
    u = None
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
    except Exception:
        pass
    row = ClientePrueba(dni=dni, celular=cel, nota=(d.get("nota") or "")[:200], activo=True,
                        creado_por=str(getattr(u, "id", "admin")))
    db.add(row); db.commit()
    return {"ok": True, "id": row.id}


@router.delete("/api/v1/admin/clientes-prueba/{cid}")
async def quitar(cid: int, request: Request, db: Session = Depends(get_db)):
    await _guard(request, db)
    from app.models.cliente_prueba import ClientePrueba
    row = db.query(ClientePrueba).get(cid)
    if not row:
        raise HTTPException(status_code=404, detail="No existe")
    db.delete(row); db.commit()
    return {"ok": True}
