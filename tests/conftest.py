"""
Fixtures compartidos para los tests.

Objetivo: que los tests sean 100 % offline, gratuitos y sin tocar datos reales.

Hay dos tipos de test y cada uno necesita cosas distintas:
  - Los de sql_seguro.py (la validación de verdad) no necesitan neutralizar nada:
    ese módulo no importa anthropic ni dotenv. Solo les hace falta una base
    SQLite temporal, para que facturas.db (la real, versionada) nunca se abra.
  - Los de los envoltorios (semana3_agente_sql.py y api.py) sí importan
    anthropic y dotenv al cargarse, así que hay que neutralizar dos cosas:
      1. load_dotenv() al importar (leería el .env real).
      2. anthropic.Anthropic(api_key=...) al importar (sin clave falla, y con
         clave real tendría riesgo de gastar dinero si algún test llamara al modelo).
"""

import importlib
import sqlite3
import sys

import pytest

# Los dos archivos que llevan un envoltorio fino sobre sql_seguro.ejecutar_sql_seguro.
NOMBRES_MODULOS_ENVOLTORIO = ["semana3_agente_sql", "api"]


@pytest.fixture
def modulo_sql_seguro():
    """
    Importa sql_seguro. Es un import como cualquier otro, pero vive en un
    fixture (y no arriba del todo en cada test) para que, si el módulo falta o
    falla al importarse, se vea qué tests concretos se rompen en lugar de un
    único error de colección que oculta cuántos casos hay.
    """
    return importlib.import_module("sql_seguro")


@pytest.fixture(params=NOMBRES_MODULOS_ENVOLTORIO)
def modulo_envoltorio(request, monkeypatch):
    """Importa semana3_agente_sql y luego api (uno por ejecución) sin leer .env y con clave falsa."""
    import dotenv

    # Los módulos hacen "from dotenv import load_dotenv": esa referencia se resuelve
    # en el momento del import, así que basta con sustituirla antes de importar.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    # El constructor de Anthropic solo exige que haya una clave; no hace red.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa-solo-para-tests")

    # Import limpio en cada test, para que no arrastre estado de otro.
    nombre = request.param
    sys.modules.pop(nombre, None)
    modulo = importlib.import_module(nombre)
    yield modulo
    sys.modules.pop(nombre, None)


@pytest.fixture
def base_temporal(tmp_path):
    """
    Crea una base SQLite temporal con la tabla 'facturas' (3 filas) y devuelve
    su ruta. Cada test decide cómo apuntar a ella: pasándola como ruta_bd a
    sql_seguro, o con monkeypatch de BASE_DATOS en un envoltorio.
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
    return ruta


def contar_filas(ruta) -> int:
    """Cuenta las filas de 'facturas' para comprobar que nada se ha modificado."""
    conexion = sqlite3.connect(ruta)
    try:
        return conexion.execute("SELECT COUNT(*) FROM facturas").fetchone()[0]
    finally:
        conexion.close()
