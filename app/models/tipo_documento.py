"""
Tipos de documento requeridos en la postulación de técnicos.
Configurable por el admin (excepto dni_anverso / dni_reverso, que son fijos).
"""

from sqlalchemy import Column, Integer, String, Text, Boolean

from app.core.database import Base


class TipoDocumentoPostulacion(Base):
    __tablename__ = "tipos_documento_postulacion"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    obligatorio = Column(Boolean, default=False)
    fijo = Column(Boolean, default=False)   # dni_anverso / dni_reverso -> no editable ni eliminable
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
