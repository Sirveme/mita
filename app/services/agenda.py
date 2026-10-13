"""
Disponibilidad y propuesta de horarios para agendar la visita (zMita-25).

Usa HorarioAtencion si está poblada; si no, horario por defecto 08:00–20:00 todos
los días. Genera slots en horas en punto cada `PASO_H` horas. Nunca propone
horarios pasados ni fuera del horario de atención. Todo en America/Lima.
"""
from datetime import datetime, timedelta, time

from sqlalchemy.orm import Session

PASO_H = 2                      # separación entre slots (horas)
DEF_INICIO, DEF_FIN = 8, 20     # horario por defecto (si no hay HorarioAtencion)
FRANJAS = {"manana": (8, 12), "mañana": (8, 12), "tarde": (12, 18), "noche": (18, 22)}
DIAS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES_ES = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def ahora_lima() -> datetime:
    return datetime.utcnow() - timedelta(hours=5)


def _horario_dia(db: Session, dow: int):
    """(hora_inicio, hora_fin) para el día (0=lunes). None si cerrado."""
    try:
        from app.models.configuracion import HorarioAtencion
        rows = db.query(HorarioAtencion).filter(HorarioAtencion.dia_semana == dow,
                                                HorarioAtencion.activo == True,
                                                HorarioAtencion.es_feriado == False).all()
        if rows:
            r = rows[0]
            return (r.hora_inicio.hour, r.hora_fin.hour)
    except Exception:
        pass
    return (DEF_INICIO, DEF_FIN)


def _etiqueta(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    ampm = "am" if dt.hour < 12 else "pm"
    return f"{DIAS_ES[dt.weekday()]} {dt.day} {MESES_ES[dt.month]}, {h}:{dt.minute:02d} {ampm}"


def _slots_dia(db: Session, dia: datetime.date, desde_hora: int = 0, franja=None):
    ini, fin = _horario_dia(db, dia.weekday())
    if ini is None:
        return []
    if franja and franja.lower() in FRANJAS:
        f0, f1 = FRANJAS[franja.lower()]
        ini, fin = max(ini, f0), min(fin, f1)
    out = []
    h = max(ini, desde_hora)
    # alinear al próximo múltiplo de PASO_H dentro del horario
    while h < fin:
        out.append(datetime.combine(dia, time(hour=h)))
        h += PASO_H
    return out


def proponer_horarios(db: Session, ahora: datetime = None, preferencia: dict = None, n: int = 3):
    """Devuelve hasta n slots (datetime) acordes a la preferencia, nunca en el pasado.

    preferencia: {fecha: 'YYYY-MM-DD'|None, franja: 'manana'|'tarde'|'noche'|None,
                  hora: 'HH:MM'|None, lo_antes_posible: bool}
    """
    ahora = ahora or ahora_lima()
    preferencia = preferencia or {}
    franja = (preferencia.get("franja") or None)
    lo_antes = bool(preferencia.get("lo_antes_posible"))
    fecha_pref = preferencia.get("fecha")

    # margen mínimo: no proponer dentro de las próximas 2 horas
    piso = ahora + timedelta(hours=2)

    candidatos = []
    # 1) preferencia de fecha concreta
    dias = []
    if fecha_pref:
        try:
            d = datetime.strptime(fecha_pref[:10], "%Y-%m-%d").date()
            dias = [d]
        except ValueError:
            dias = []
    if not dias:
        dias = [(ahora + timedelta(days=i)).date() for i in range(0, 8)]

    for d in dias:
        desde = piso.hour + 1 if d == piso.date() else 0
        for s in _slots_dia(db, d, desde_hora=desde, franja=franja):
            if s >= piso:
                candidatos.append(s)
        if len(candidatos) >= n and not lo_antes:
            break

    # Si pidió fecha/franja y no hubo nada, ampliar a los próximos días sin franja
    if not candidatos:
        for i in range(0, 8):
            d = (ahora + timedelta(days=i)).date()
            desde = piso.hour + 1 if d == piso.date() else 0
            for s in _slots_dia(db, d, desde_hora=desde):
                if s >= piso:
                    candidatos.append(s)
            if len(candidatos) >= n:
                break

    candidatos = sorted(set(candidatos))
    return candidatos[:n]


def opciones_horarios(db: Session, ahora: datetime = None, preferencia: dict = None, n: int = 3):
    return [{"iso": s.isoformat(timespec="minutes"), "etiqueta": _etiqueta(s)}
            for s in proponer_horarios(db, ahora, preferencia, n)]
