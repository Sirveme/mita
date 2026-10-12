"""
Script para crear usuarios de prueba en MITA.
Ejecutar:  python -m app.scripts.crear_usuarios_prueba
Requiere la BD (Railway) con las tablas de zMita-2/3/4 creadas (SQL 01-04).

Notas de adaptación (vs. borrador original):
- Se usa el paquete `bcrypt` directo (passlib 1.7.4 es incompatible con bcrypt>=4.1).
- `personal.tipo` / `personal.estado` son ENUM en PostgreSQL con etiquetas en
  MAYÚSCULA (SECRETARIA/TECNICO/ADMIN/GERENTE, ACTIVO...), así que se insertan así.
- `usuarios_mita.tipo` es texto en minúscula (lo que espera el login).
- La tabla `clientes` NO tiene columnas nombre/apellidos/telefono (esos viven en
  `usuarios`), por eso los clientes de prueba se crean solo en `usuarios_mita`
  (con el nombre en la columna `nombres`); cliente_id queda NULL.
"""

from sqlalchemy import text
from app.core.database import SessionLocal
from app.routes.login_mita import hash_password

# (dni, nombre, apellido, tipo, telefono)
USUARIOS_PRUEBA = [
    ("10000001", "Erwin", "Schiper", "admin", "999000001"),
    ("20000001", "María", "García", "secretaria", "999000002"),
    ("20000002", "Lucía", "Torres", "secretaria", "999000003"),
    ("30000001", "Carlos", "López", "tecnico", "999000004"),
    ("30000002", "Juan", "Pérez", "tecnico", "999000005"),
    ("30000003", "Miguel", "Sánchez", "tecnico", "999000006"),
    ("30000004", "Pedro", "Ramírez", "tecnico", "999000007"),
    ("30000005", "Luis", "Fernández", "tecnico", "999000008"),
]

CLIENTES_PRUEBA = [
    ("40000001", "Ana", "Martínez", "999000009"),
    ("40000002", "Rosa", "Villanueva", "999000010"),
    ("40000003", "Jorge", "Castillo", "999000011"),
]


def crear_usuarios():
    db = SessionLocal()
    try:
        # Asegurar columnas requeridas (idempotente)
        db.execute(text("ALTER TABLE usuarios_mita ADD COLUMN IF NOT EXISTS cliente_id INTEGER"))
        db.execute(text("ALTER TABLE usuarios_mita ADD COLUMN IF NOT EXISTS requiere_cambio_clave BOOLEAN DEFAULT FALSE"))
        db.commit()

        # Personal + usuarios del staff
        for dni, nombre, apellido, tipo, telefono in USUARIOS_PRUEBA:
            password_hash = hash_password(dni)  # clave inicial = DNI

            # personal.tipo / estado son ENUM en MAYÚSCULA
            db.execute(text("""
                INSERT INTO personal (dni, nombres, apellido_paterno, tipo, telefono, estado)
                VALUES (:dni, :nombre, :apellido, CAST(:tipo AS tipopersonal), :telefono, CAST('ACTIVO' AS estadopersonal))
                ON CONFLICT (dni) DO NOTHING
            """), {"dni": dni, "nombre": nombre, "apellido": apellido, "tipo": tipo.upper(), "telefono": telefono})

            row = db.execute(text("SELECT id FROM personal WHERE dni = :dni"), {"dni": dni}).fetchone()
            personal_id = row[0] if row else None

            db.execute(text("""
                INSERT INTO usuarios_mita (dni, password_hash, tipo, nombres, personal_id, activo, verificado, requiere_cambio_clave)
                VALUES (:dni, :hash, :tipo, :nombres, :personal_id, true, true, true)
                ON CONFLICT (dni) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    requiere_cambio_clave = true
            """), {"dni": dni, "hash": password_hash, "tipo": tipo,
                   "nombres": f"{nombre} {apellido}", "personal_id": personal_id})

            print(f"OK usuario {tipo}: {nombre} {apellido} - DNI: {dni}")

        # Clientes de prueba (solo usuarios_mita; el nombre va en 'nombres')
        for dni, nombre, apellido, telefono in CLIENTES_PRUEBA:
            password_hash = hash_password(dni)
            db.execute(text("""
                INSERT INTO usuarios_mita (dni, password_hash, tipo, nombres, activo, verificado, requiere_cambio_clave)
                VALUES (:dni, :hash, 'cliente', :nombres, true, true, true)
                ON CONFLICT (dni) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    requiere_cambio_clave = true
            """), {"dni": dni, "hash": password_hash, "nombres": f"{nombre} {apellido}"})
            print(f"OK cliente: {nombre} {apellido} - DNI: {dni}")

        db.commit()
        print("\nTodos los usuarios de prueba creados correctamente")
        print("\nCREDENCIALES: usuario = DNI, clave = DNI (se pedira cambio en el 1er login)")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    crear_usuarios()
