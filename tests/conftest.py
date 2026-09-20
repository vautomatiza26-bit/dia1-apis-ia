"""
Fixtures compartidos para los tests.

Objetivo: que los tests sean 100 % offline, gratuitos y sin tocar datos reales.
Para eso hay que neutralizar tres cosas de semana3_agente_sql.py:
  1. load_dotenv() al importar (leería el .env real).
  2. anthropic.Anthropic(api_key=...) al importar (sin clave falla, y con clave
     real tendría riesgo de gastar dinero si algún test llamara al modelo).
  3. BASE_DATOS = "facturas.db" (la base real, que está versionada).
"""

import importlib
import sqlite3
import sys

import pytest

NOMBRE_MODULO = "semana3_agente_sql"


@pytest.fixture
def modulo_sql(monkeypatch):
    """Importa semana3_agente_sql sin leer .env y con una clave falsa."""
    import dotenv

    # El módulo hace "from dotenv import load_dotenv": esa referencia se resuelve
    # en el momento del import, así que basta con sustituirla antes de importar.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    # El constructor de Anthropic solo exige que haya una clave; no hace red.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa-solo-para-tests")

    # Import limpio en cada test, para que no arrastre estado de otro.
    sys.modules.pop(NOMBRE_MODULO, None)
    modulo = importlib.import_module(NOMBRE_MODULO)
    yield modulo
    sys.modules.pop(NOMBRE_MODULO, None)


@pytest.fixture
def base_temporal(modulo_sql, tmp_path, monkeypatch):
    """
    Crea una base SQLite temporal con la tabla 'facturas' (3 filas) y hace que
    el módulo apunte a ella, de modo que facturas.db real nunca se abre.
    """
    ruta = tmp_path / "facturas_test.db"

    conexion = sqlite3.connect(ruta)
    conexion.execute(
        """
        CREATE TABLE facturas (
            id INTEGER PRIMARY KEY,
            archivo_origen TEXT,
            numero_factura TEXT,
            fecha TEXT,
            importe_total REAL,
            nombre_cliente TEXT
        )
        """
    )
    conexion.executemany(
        "INSERT INTO facturas VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "f1.pdf", "F-001", "01/01/2025", 100.0, "Acme"),
            (2, "f2.pdf", "F-002", "15/02/2025", 250.5, "Globex"),
            (3, "f3.pdf", "F-003", "20/03/2025", 49.5, "Acme"),
        ],
    )
    conexion.commit()
    conexion.close()

    # La función lee BASE_DATOS en cada llamada, así que monkeypatch surte efecto.
    monkeypatch.setattr(modulo_sql, "BASE_DATOS", str(ruta))
    return ruta


def contar_filas(ruta) -> int:
    """Cuenta las filas de 'facturas' para comprobar que nada se ha modificado."""
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute("SELECT COUNT(*) FROM facturas").fetchone()[0]
    finally:
        conexion.close()
