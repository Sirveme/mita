"""
Asignación automática de técnicos (zMita-13), adaptado al esquema real:
Personal (datos base, rating) + TecnicoPersonal (estado_actual, especialidades
ARRAY de categoria_id, ultima_ubicacion_lat/lng). Solicitud usa cliente_lat/lng.
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal, EstadoTecnico
from app.models.solicitud_mita import Solicitud
from app.models.cola_asignacion import ColaAsignacion, AlertaTecnico
from app.services.config_service import (
    get_tiempo_respuesta, get_radio_inicial, usar_prioridad_rating, ConfigService,
)

# Centro de Lima por defecto si no hay coordenadas
LIMA_LAT, LIMA_LNG = -12.0464, -77.0428


class AsignacionService:
    """Asignación automática por distancia (y opcionalmente rating)."""

    @staticmethod
    def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distancia en km (Haversine)."""
        R = 6371
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def buscar_tecnicos_disponibles(
        db: Session,
        categoria_id: int,
        lat_cliente: float,
        lon_cliente: float,
        radio_km: float,
        excluir_ids: Optional[List[int]] = None,
        usar_rating: bool = False,
        limite: int = 3,
    ) -> List[Tuple[Personal, float]]:
        """Técnicos activos+disponibles con la especialidad, dentro del radio."""
        q = (
            db.query(Personal, TecnicoPersonal)
            .join(TecnicoPersonal, TecnicoPersonal.personal_id == Personal.id)
            .filter(
                Personal.tipo == TipoPersonal.TECNICO,
                Personal.estado == EstadoPersonal.ACTIVO,
                TecnicoPersonal.estado_actual == EstadoTecnico.DISPONIBLE,
            )
        )
        if excluir_ids:
            q = q.filter(~Personal.id.in_(excluir_ids))

        resultados: List[Tuple[Personal, float]] = []
        for persona, info in q.all():
            # Especialidad: categoria_id dentro del array especialidades
            if not info.especialidades or categoria_id not in info.especialidades:
                continue
            if info.ultima_ubicacion_lat is None or info.ultima_ubicacion_lng is None:
                continue
            dist = AsignacionService.calcular_distancia(
                lat_cliente, lon_cliente,
                float(info.ultima_ubicacion_lat), float(info.ultima_ubicacion_lng),
            )
            if dist <= radio_km:
                resultados.append((persona, dist))

        if usar_rating:
            resultados.sort(key=lambda x: (-(float(x[0].rating_promedio or 0)), x[1]))
        else:
            resultados.sort(key=lambda x: x[1])
        return resultados[:limite]

    @staticmethod
    def iniciar_asignacion(db: Session, solicitud_id: int) -> ColaAsignacion:
        solicitud = db.query(Solicitud).get(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        cola = ColaAsignacion(
            solicitud_id=solicitud_id,
            estado="PENDIENTE",
            ronda=1,
            radio_km=get_radio_inicial(db),
            usar_rating=usar_prioridad_rating(db),
        )
        db.add(cola)
        db.commit()
        db.refresh(cola)
        return cola

    @staticmethod
    def ejecutar_ronda(db: Session, cola_id: int) -> dict:
        cola = db.query(ColaAsignacion).get(cola_id)
        if not cola:
            return {"exito": False, "mensaje": "Cola no encontrada"}
        if cola.estado not in ("PENDIENTE", "EN_PROCESO"):
            return {"exito": False, "mensaje": f"Cola en estado {cola.estado}"}

        solicitud = db.query(Solicitud).get(cola.solicitud_id)
        excluir = (
            list(cola.tecnicos_alertados or [])
            + list(cola.tecnicos_rechazaron or [])
            + list(cola.tecnicos_timeout or [])
        )
        tecnicos = AsignacionService.buscar_tecnicos_disponibles(
            db=db,
            categoria_id=solicitud.categoria_id,
            lat_cliente=float(solicitud.cliente_lat) if solicitud.cliente_lat else LIMA_LAT,
            lon_cliente=float(solicitud.cliente_lng) if solicitud.cliente_lng else LIMA_LNG,
            radio_km=float(cola.radio_km or 5),
            excluir_ids=excluir,
            usar_rating=bool(cola.usar_rating),
            limite=ConfigService.get(db, "tecnicos_por_alerta", 3),
        )

        if not tecnicos:
            radio_max = ConfigService.get(db, "radio_busqueda_maximo_km", 20)
            nuevo_radio = min(float(cola.radio_km or 5) * 1.5, radio_max)
            if nuevo_radio >= radio_max:
                cola.estado = "EXPIRADA"
                db.commit()
                return {"exito": False, "mensaje": "No hay técnicos disponibles"}
            cola.radio_km = nuevo_radio
            cola.ronda += 1
            db.commit()
            return {"exito": False, "tecnicos_alertados": 0, "mensaje": "Ampliando búsqueda"}

        tiempo_respuesta = get_tiempo_respuesta(db)
        expira_at = datetime.utcnow() + timedelta(seconds=tiempo_respuesta)
        alertados = []
        for i, (persona, dist) in enumerate(tecnicos):
            db.add(AlertaTecnico(
                cola_id=cola.id, tecnico_id=persona.id, solicitud_id=solicitud.id,
                estado="ENVIADA", enviada_at=datetime.utcnow(), expira_at=expira_at,
                distancia_km=round(dist, 2), rating_tecnico=persona.rating_promedio, posicion_en_ronda=i + 1,
            ))
            alertados.append(persona.id)

        cola.estado = "EN_PROCESO"
        cola.tecnicos_alertados = list(cola.tecnicos_alertados or []) + alertados
        cola.ronda_iniciada_at = datetime.utcnow()
        cola.expira_at = expira_at
        db.commit()
        # TODO (zMita-14): push/WebSocket a los técnicos alertados
        return {"exito": True, "tecnicos_alertados": len(alertados), "expira_en": tiempo_respuesta,
                "mensaje": f"Alertados {len(alertados)} técnicos"}

    @staticmethod
    def tecnico_acepta(db: Session, alerta_id: int) -> dict:
        alerta = db.query(AlertaTecnico).get(alerta_id)
        if not alerta:
            return {"exito": False, "mensaje": "Alerta no encontrada"}
        if alerta.expira_at and datetime.utcnow() > alerta.expira_at:
            alerta.estado = "TIMEOUT"
            db.commit()
            return {"exito": False, "mensaje": "Tiempo expirado"}

        cola = db.query(ColaAsignacion).get(alerta.cola_id)
        if cola and cola.estado == "ASIGNADA":
            return {"exito": False, "mensaje": "Ya fue asignada a otro técnico"}

        alerta.estado = "ACEPTADA"
        alerta.respondida_at = datetime.utcnow()
        if cola:
            cola.estado = "ASIGNADA"
            cola.asignada_at = datetime.utcnow()
            cola.tecnico_asignado_id = alerta.tecnico_id

        solicitud = db.query(Solicitud).get(alerta.solicitud_id)
        if solicitud:
            solicitud.tecnico_id = alerta.tecnico_id
            solicitud.estado = "ASIGNADA"

        db.query(AlertaTecnico).filter(
            AlertaTecnico.cola_id == alerta.cola_id,
            AlertaTecnico.id != alerta_id,
            AlertaTecnico.estado == "ENVIADA",
        ).update({"estado": "NO_SELECCIONADO"})
        db.commit()
        return {"exito": True, "tecnico_id": alerta.tecnico_id, "solicitud_id": alerta.solicitud_id,
                "mensaje": "Asignación exitosa"}

    @staticmethod
    def tecnico_rechaza(db: Session, alerta_id: int, motivo: Optional[str] = None) -> dict:
        alerta = db.query(AlertaTecnico).get(alerta_id)
        if not alerta:
            return {"exito": False, "mensaje": "Alerta no encontrada"}
        alerta.estado = "RECHAZADA"
        alerta.respondida_at = datetime.utcnow()
        cola = db.query(ColaAsignacion).get(alerta.cola_id)
        if cola:
            rech = list(cola.tecnicos_rechazaron or [])
            rech.append(alerta.tecnico_id)
            cola.tecnicos_rechazaron = rech
        db.commit()
        return {"exito": True, "mensaje": "Rechazo registrado"}
