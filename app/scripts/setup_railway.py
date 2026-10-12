"""
setup_railway.py — Inicializa la base de datos de MITA (paso de demo → producción real).

Qué hace, en orden:
  0. Verifica la conexión a la BD (DATABASE_URL del .env / Railway).
  1. Crea las tablas faltantes desde los modelos ORM (idempotente).
  2. Ejecuta los 7 SQL en orden (enums, columnas, datos seed de catálogo,
     tablas/vistas extra, índices, etc.).
  3. Corre los 2 seeds: ubigeos de Lima y usuarios de prueba.

Uso:
    python -m app.scripts.setup_railway            # ejecuta todo
    python -m app.scripts.setup_railway --dry-run  # muestra el plan, no ejecuta nada
    python -m app.scripts.setup_railway --skip-create-all   # no corre create_all (solo SQL + seeds)
    python -m app.scripts.setup_railway --stop-on-error     # aborta al primer fallo

Todo es idempotente: se puede volver a correr sin dañar datos existentes.
"""

import argparse
import sys
import time
from pathlib import Path

from app.core.database import engine, Base
import app.models  # noqa: F401  # registra TODAS las tablas en Base.metadata

# Evitar el volcado de SQL de SQLAlchemy (el .env de dev trae DEBUG=True → echo).
engine.echo = False

# La consola de Windows suele ser cp1252 y no puede imprimir algunos caracteres;
# forzamos UTF-8 y, si aun así falla, reemplazamos en vez de reventar.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ------------------------------------------------------------------
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"

SQL_FILES = [
    "01_categorias_servicios.sql",
    "02_sistema_reportes_tecnico.sql",
    "03_personal_chat_liquidaciones.sql",
    "04_auth_panel.sql",
    "05_ubigeos.sql",
    "06_solicitudes.sql",
    "07_billeteras.sql",
    "08_modelo_v2.sql",   # asignación automática + calificaciones + config (zMita-13)
    "09_postulantes.sql", # postulación de técnicos + tipos de documento + config extra
    "10_flujo_config.sql",# parámetros del flujo de solicitud + cobro (configurables)
    "11_soporte_integraciones.sql",  # panel de soporte: integraciones + auditoría
    "12_distritos_habilitado.sql",   # flag de cobertura por distrito
    "13_waitlist_distrito.sql",      # lista de espera por distrito
    "14_comprobantes_liquidaciones.sql",  # servicios completados + liquidaciones semanales
    "15_pagos.sql",                       # pagos por pasarela (IziPay/...)
    "16_areas_problemas.sql",             # áreas y problemas de servicio (flujo VISA)
    "17_chats.sql",                       # salas y mensajes de chat por servicio
    "18_dashboard_tecnico.sql",           # estado en servicio, notificaciones, adicionales, pre-auth
    "19_timeout_tecnico.sql",             # config del timeout de respuesta de tecnico (cron)
    "20_notificaciones_todos.sql",        # notificar a todos + reintentos (intento_notificacion)
    "21_ubicacion_tecnico.sql",           # seguimiento en vivo del técnico (Google Maps)
    "22_sin_cobertura.sql",               # registro de distritos sin cobertura (análisis)
    "23_chat_conocimiento.sql",           # base de conocimiento editable del chat IA
    "24_catalogo_historial.sql",          # historial de catálogo + promoción de visita
]

# (etiqueta, módulo, función)
SEEDS = [
    ("Ubigeos de Lima/Callao", "app.scripts.cargar_ubigeos", "cargar"),
    ("Usuarios de prueba", "app.scripts.crear_usuarios_prueba", "crear_usuarios"),
]

OK = "\033[92m[OK]\033[0m"
FAIL = "\033[91m[X ]\033[0m"
SKIP = "\033[93m[- ]\033[0m"


def _line(char="-", n=64):
    print(char * n)


def verificar_conexion() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception as e:
        print(f"{FAIL} No se pudo conectar a la BD.")
        print(f"    Detalle: {str(e).splitlines()[0][:160]}")
        print("    Revisa que Railway esté ACTIVO y que DATABASE_URL en .env sea correcta.")
        return False


def crear_tablas_orm(resultados: list, dry: bool):
    total = len(Base.metadata.tables)
    if dry:
        print(f"{SKIP} [dry-run] create_all() crearía las tablas faltantes de {total} definidas en los modelos.")
        resultados.append(("create_all (ORM)", "dry-run", ""))
        return
    try:
        Base.metadata.create_all(engine)
        print(f"{OK} Tablas del ORM verificadas/creadas ({total} definidas).")
        resultados.append(("create_all (ORM)", "ok", f"{total} tablas"))
    except Exception as e:
        msg = str(e).splitlines()[0][:160]
        print(f"{FAIL} create_all falló: {msg}")
        resultados.append(("create_all (ORM)", "fail", msg))


def ejecutar_sql(nombre: str, resultados: list, dry: bool) -> bool:
    path = SQL_DIR / nombre
    if not path.exists():
        print(f"{FAIL} {nombre} — no encontrado en {SQL_DIR}")
        resultados.append((nombre, "fail", "archivo no encontrado"))
        return False

    sql = path.read_text(encoding="utf-8")
    if dry:
        n = sql.count(";")
        print(f"{SKIP} [dry-run] {nombre} ({len(sql):,} bytes, ~{n} sentencias)")
        resultados.append((nombre, "dry-run", ""))
        return True

    t0 = time.time()
    try:
        # Un archivo = una transacción. psycopg2 admite múltiples sentencias
        # (incluidos bloques DO $$ .. $$ y funciones) en un solo envío.
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
        dt = time.time() - t0
        print(f"{OK} {nombre}  ({dt:.1f}s)")
        resultados.append((nombre, "ok", f"{dt:.1f}s"))
        return True
    except Exception as e:
        msg = str(e).splitlines()[0][:180]
        print(f"{FAIL} {nombre}")
        print(f"    {msg}")
        resultados.append((nombre, "fail", msg))
        return False


def correr_seed(etiqueta: str, modulo: str, funcion: str, resultados: list, dry: bool):
    if dry:
        print(f"{SKIP} [dry-run] seed: {etiqueta}  ({modulo}.{funcion})")
        resultados.append((f"seed: {etiqueta}", "dry-run", ""))
        return
    print(f"\n>> Seed: {etiqueta}  ({modulo}.{funcion})")
    try:
        import importlib
        mod = importlib.import_module(modulo)
        getattr(mod, funcion)()
        resultados.append((f"seed: {etiqueta}", "ok", "ver salida arriba"))
    except Exception as e:
        msg = str(e).splitlines()[0][:180]
        print(f"{FAIL} {etiqueta}: {msg}")
        resultados.append((f"seed: {etiqueta}", "fail", msg))


def main():
    parser = argparse.ArgumentParser(description="Inicializa la BD de MITA (SQL 01-07 + seeds).")
    parser.add_argument("--dry-run", action="store_true", help="Muestra el plan sin ejecutar nada.")
    parser.add_argument("--skip-create-all", action="store_true", help="No ejecutar create_all (solo SQL + seeds).")
    parser.add_argument("--stop-on-error", action="store_true", help="Abortar al primer error de SQL.")
    args = parser.parse_args()

    _line("=")
    print("  MITA — setup_railway  " + ("(DRY-RUN)" if args.dry_run else ""))
    print(f"  SQL: {SQL_DIR}")
    _line("=")

    # 0) Conexión
    print("\n[0] Conexión a la base de datos")
    if verificar_conexion():
        print(f"{OK} Conexión OK.")
    else:
        if args.dry_run:
            print(f"{SKIP} (dry-run) continúo mostrando el plan aunque no haya conexión.")
        else:
            print("\nAbortado: sin conexión a la BD.")
            sys.exit(2)

    resultados: list = []

    # 1) Tablas del ORM
    print("\n[1] Tablas del ORM (create_all)")
    if args.skip_create_all:
        print(f"{SKIP} Omitido por --skip-create-all")
    else:
        crear_tablas_orm(resultados, args.dry_run)

    # 2) SQL 01-07
    print("\n[2] Scripts SQL (en orden)")
    for nombre in SQL_FILES:
        ok = ejecutar_sql(nombre, resultados, args.dry_run)
        if not ok and args.stop_on_error and not args.dry_run:
            print("\nAbortado por --stop-on-error.")
            break

    # 3) Seeds
    print("\n[3] Seeds de datos")
    for etiqueta, modulo, funcion in SEEDS:
        correr_seed(etiqueta, modulo, funcion, resultados, args.dry_run)

    # Resumen
    print("\n")
    _line("=")
    print("  RESUMEN")
    _line("=")
    n_ok = sum(1 for _, s, _ in resultados if s == "ok")
    n_fail = sum(1 for _, s, _ in resultados if s == "fail")
    n_dry = sum(1 for _, s, _ in resultados if s == "dry-run")
    for nombre, estado, detalle in resultados:
        icono = {"ok": OK, "fail": FAIL, "dry-run": SKIP}.get(estado, " ")
        extra = f"  {detalle}" if detalle else ""
        print(f"  {icono} {nombre}{extra}")
    _line("─")
    if args.dry_run:
        print(f"  Plan: {n_dry} pasos (nada ejecutado).")
        print("  Ejecuta sin --dry-run para aplicar los cambios.")
    else:
        print(f"  OK: {n_ok}   Fallos: {n_fail}")
        if n_fail == 0:
            print("\n  >>> BD lista. MITA puede pasar de demo a produccion real.")
            print("      Recuerda cambiar demoMode:false en los templates de chat cuando quieras")
            print("      conversaciones reales por WebSocket.")
        else:
            print("\n  (!) Hubo fallos. Revisa los detalles arriba (los pasos son idempotentes:")
            print("     puedes corregir y volver a ejecutar sin dañar lo ya cargado).")
    _line("=")

    if not args.dry_run and n_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
