"""
Tipos de columna portables (zMita-39, Parte 0).

`ARRAY` de Postgres no compila en sqlite y rompía 39 tests (create_all en
sqlite). Estos tipos usan ARRAY en Postgres y JSON en sqlite vía `with_variant`,
para que la suite corra en sqlite sin perder el ARRAY nativo en producción.
"""
from sqlalchemy import ARRAY, Integer, Text, JSON, String
from sqlalchemy.dialects.postgresql import JSONB as _JSONB, INET as _INET


def array_int():
    """ARRAY(Integer) en Postgres, JSON (lista) en sqlite."""
    return ARRAY(Integer).with_variant(JSON(), "sqlite")


def array_text():
    """ARRAY(Text) en Postgres, JSON (lista) en sqlite."""
    return ARRAY(Text).with_variant(JSON(), "sqlite")


def jsonb():
    """JSONB en Postgres, JSON en sqlite."""
    return _JSONB().with_variant(JSON(), "sqlite")


def inet():
    """INET en Postgres, String en sqlite."""
    return _INET().with_variant(String(45), "sqlite")
