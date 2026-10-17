"""
Modo ensayo (zMita-45 D): clientes de prueba pagan monto_ensayo (def S/ 1), sus comprobantes
salen en serie de pruebas (B999) aunque FACTURALO_MODO=produccion, llevan la marca ENSAYO en la
torre y se excluyen de la liquidación de técnicos.
"""
import logging

logger = logging.getLogger("mita.ensayo")


def _digitos(s):
    return "".join(ch for ch in (s or "") if ch.isdigit())


def es_cliente_prueba(db, dni=None, celular=None) -> bool:
    from app.models.cliente_prueba import ClientePrueba
    cel = _digitos(celular)[-9:] if celular else None
    d = _digitos(dni) if dni else None
    q = db.query(ClientePrueba).filter(ClientePrueba.activo.is_(True))
    filtros = []
    from sqlalchemy import or_
    if d:
        filtros.append(ClientePrueba.dni == d)
    if cel:
        filtros.append(ClientePrueba.celular.like("%" + cel))
    if not filtros:
        return False
    return q.filter(or_(*filtros)).first() is not None


def monto_ensayo(db) -> float:
    try:
        from app.services.config_service import ConfigService
        return float(ConfigService.get(db, "monto_ensayo", 1.0) or 1.0)
    except Exception:
        return 1.0


def marcar(db, solicitud) -> bool:
    """Si el cliente de la solicitud es de prueba, la marca como ENSAYO y baja el costo."""
    dni = None
    try:
        if solicitud.cliente_id:
            from app.models.models import Cliente
            c = db.query(Cliente).get(solicitud.cliente_id)
            dni = getattr(c, "dni", None) if c else None
    except Exception:
        dni = None
    if not es_cliente_prueba(db, dni=dni, celular=solicitud.cliente_telefono):
        return False
    solicitud.ensayo = True
    solicitud.costo_visita = monto_ensayo(db)
    db.commit()
    logger.info("[ensayo] solicitud #%s marcada ENSAYO (monto %.2f)", solicitud.id, solicitud.costo_visita)
    return True
