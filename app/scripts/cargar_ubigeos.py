"""
Carga los ubigeos principales de Lima y Callao.
Ejecutar: python -m app.scripts.cargar_ubigeos
Fuente completa: https://github.com/jmcastagnetto/ubigeo-peru-data
"""

UBIGEOS_LIMA = [
    ("150101", "LIMA", "LIMA", "LIMA"),
    ("150102", "LIMA", "LIMA", "ANCON"),
    ("150103", "LIMA", "LIMA", "ATE"),
    ("150104", "LIMA", "LIMA", "BARRANCO"),
    ("150105", "LIMA", "LIMA", "BREÑA"),
    ("150106", "LIMA", "LIMA", "CARABAYLLO"),
    ("150107", "LIMA", "LIMA", "CHACLACAYO"),
    ("150108", "LIMA", "LIMA", "CHORRILLOS"),
    ("150109", "LIMA", "LIMA", "CIENEGUILLA"),
    ("150110", "LIMA", "LIMA", "COMAS"),
    ("150111", "LIMA", "LIMA", "EL AGUSTINO"),
    ("150112", "LIMA", "LIMA", "INDEPENDENCIA"),
    ("150113", "LIMA", "LIMA", "JESUS MARIA"),
    ("150114", "LIMA", "LIMA", "LA MOLINA"),
    ("150115", "LIMA", "LIMA", "LA VICTORIA"),
    ("150116", "LIMA", "LIMA", "LINCE"),
    ("150117", "LIMA", "LIMA", "LOS OLIVOS"),
    ("150118", "LIMA", "LIMA", "LURIGANCHO"),
    ("150119", "LIMA", "LIMA", "LURIN"),
    ("150120", "LIMA", "LIMA", "MAGDALENA DEL MAR"),
    ("150121", "LIMA", "LIMA", "PUEBLO LIBRE"),
    ("150122", "LIMA", "LIMA", "MIRAFLORES"),
    ("150123", "LIMA", "LIMA", "PACHACAMAC"),
    ("150124", "LIMA", "LIMA", "PUCUSANA"),
    ("150125", "LIMA", "LIMA", "PUENTE PIEDRA"),
    ("150126", "LIMA", "LIMA", "PUNTA HERMOSA"),
    ("150127", "LIMA", "LIMA", "PUNTA NEGRA"),
    ("150128", "LIMA", "LIMA", "RIMAC"),
    ("150129", "LIMA", "LIMA", "SAN BARTOLO"),
    ("150130", "LIMA", "LIMA", "SAN BORJA"),
    ("150131", "LIMA", "LIMA", "SAN ISIDRO"),
    ("150132", "LIMA", "LIMA", "SAN JUAN DE LURIGANCHO"),
    ("150133", "LIMA", "LIMA", "SAN JUAN DE MIRAFLORES"),
    ("150134", "LIMA", "LIMA", "SAN LUIS"),
    ("150135", "LIMA", "LIMA", "SAN MARTIN DE PORRES"),
    ("150136", "LIMA", "LIMA", "SAN MIGUEL"),
    ("150137", "LIMA", "LIMA", "SANTA ANITA"),
    ("150138", "LIMA", "LIMA", "SANTA MARIA DEL MAR"),
    ("150139", "LIMA", "LIMA", "SANTA ROSA"),
    ("150140", "LIMA", "LIMA", "SANTIAGO DE SURCO"),
    ("150141", "LIMA", "LIMA", "SURQUILLO"),
    ("150142", "LIMA", "LIMA", "VILLA EL SALVADOR"),
    ("150143", "LIMA", "LIMA", "VILLA MARIA DEL TRIUNFO"),
    ("070101", "CALLAO", "CALLAO", "CALLAO"),
    ("070102", "CALLAO", "CALLAO", "BELLAVISTA"),
    ("070103", "CALLAO", "CALLAO", "CARMEN DE LA LEGUA REYNOSO"),
    ("070104", "CALLAO", "CALLAO", "LA PERLA"),
    ("070105", "CALLAO", "CALLAO", "LA PUNTA"),
    ("070106", "CALLAO", "CALLAO", "VENTANILLA"),
    ("070107", "CALLAO", "CALLAO", "MI PERU"),
]


def cargar():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        for codigo, depa, prov, dist in UBIGEOS_LIMA:
            db.execute(text("""
                INSERT INTO ubigeos (codigo, departamento, provincia, distrito)
                VALUES (:codigo, :depa, :prov, :dist)
                ON CONFLICT (codigo) DO NOTHING
            """), {"codigo": codigo, "depa": depa, "prov": prov, "dist": dist})
        db.commit()
        print(f"OK: {len(UBIGEOS_LIMA)} ubigeos cargados")
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    cargar()
