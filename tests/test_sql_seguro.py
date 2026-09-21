"""
Tests de ejecutar_sql_seguro (sql_seguro.py): la validación SELECT-only.

Por qué existen: el agente text-to-SQL deja que un modelo escriba SQL, y la
única barrera contra un DROP/DELETE es esta función. Es una regla que no se
rompe, así que conviene que un test falle si alguien la debilita sin querer.

Estos tests prueban la función compartida directamente, pasándole la ruta de una
base SQLite temporal. Que los dos envoltorios (semana3_agente_sql.py y api.py)
la usen de verdad se comprueba en test_envoltorios_sql.py.

Son tests offline y gratuitos: no llaman a ninguna API (ver conftest.py).
"""

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import contar_filas

MENSAJE_GUARD = "ERROR: por seguridad"
MENSAJE_SQLITE = "ERROR al ejecutar"

RAIZ_DEL_REPO = Path(__file__).resolve().parent.parent


# --- 0. El módulo no arrastra efectos secundarios --------------------------------

def test_sql_seguro_no_importa_anthropic_ni_dotenv():
    # Es la razón de que la validación viva en un módulo aparte: los tests (y
    # cualquier script) pueden importarla sin leer .env ni crear un cliente de
    # la API. Se comprueba en un intérprete NUEVO, porque en el de pytest otros
    # tests ya habrán importado anthropic y dotenv y el resultado no valdría.
    codigo = (
        "import sys, sql_seguro; "
        "print([m for m in ('anthropic', 'dotenv') if m in sys.modules])"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ_DEL_REPO,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "[]"


# --- 1. Sentencias que NO son SELECT: las frena el guard del código -----------

@pytest.mark.parametrize(
    "consulta",
    [
        "DROP TABLE facturas",
        "DELETE FROM facturas",
        "INSERT INTO facturas (id, numero_factura) VALUES (99, 'X-999')",
        "UPDATE facturas SET importe_total = 0",
        "CREATE TABLE intrusa (a INTEGER)",
        "PRAGMA table_info(facturas)",
        "ATTACH DATABASE 'otra.db' AS otra",
    ],
)
def test_rechaza_sentencias_que_no_son_select(modulo_sql_seguro, base_temporal, consulta):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(consulta, base_temporal)

    assert resultado.startswith(MENSAJE_GUARD)
    # Además del mensaje, comprobamos el efecto real: la tabla sigue intacta.
    assert contar_filas(base_temporal) == 3


@pytest.mark.parametrize("consulta", ["", "   \n\t "])
def test_rechaza_consultas_vacias(modulo_sql_seguro, base_temporal, consulta):
    assert modulo_sql_seguro.ejecutar_sql_seguro(consulta, base_temporal).startswith(MENSAJE_GUARD)


def test_rechaza_with_aunque_acabe_en_select(modulo_sql_seguro, base_temporal):
    # Límite conocido: el guard exige que EMPIECE por SELECT, así que las CTE
    # (WITH ... SELECT) se descartan. Es conservador (seguro) a costa de
    # perder consultas legítimas. Este test documenta esa decisión.
    consulta = "WITH x AS (SELECT * FROM facturas) SELECT COUNT(*) FROM x"
    assert modulo_sql_seguro.ejecutar_sql_seguro(consulta, base_temporal).startswith(MENSAJE_GUARD)


# --- 2. SELECT válidos: deben ejecutarse ---------------------------------------

def test_select_valido_devuelve_filas(modulo_sql_seguro, base_temporal):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT COUNT(*) AS n FROM facturas", base_temporal
    )
    assert resultado == "[{'n': 3}]"


def test_select_con_agregacion(modulo_sql_seguro, base_temporal):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT SUM(importe_total) AS total FROM facturas", base_temporal
    )
    assert resultado == "[{'total': 400.0}]"


def test_select_con_like(modulo_sql_seguro, base_temporal):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT numero_factura FROM facturas "
        "WHERE nombre_cliente LIKE '%cme%' ORDER BY id",
        base_temporal,
    )
    assert resultado == "[{'numero_factura': 'F-001'}, {'numero_factura': 'F-003'}]"


@pytest.mark.parametrize(
    "consulta",
    [
        "select COUNT(*) AS n from facturas",
        "  \n SeLeCt COUNT(*) AS n FROM facturas",
    ],
)
def test_acepta_select_en_minusculas_y_con_espacios(modulo_sql_seguro, base_temporal, consulta):
    # El guard normaliza con strip().upper() solo para comprobar; la consulta
    # original es la que se ejecuta.
    assert modulo_sql_seguro.ejecutar_sql_seguro(consulta, base_temporal) == "[{'n': 3}]"


def test_select_sin_resultados(modulo_sql_seguro, base_temporal):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT * FROM facturas WHERE id = 999", base_temporal
    )
    assert resultado == "La consulta no devolvió resultados."


def test_acepta_punto_y_coma_final(modulo_sql_seguro, base_temporal):
    # Un único ";" al final es válido en SQLite y los modelos lo escriben a menudo.
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT COUNT(*) AS n FROM facturas;", base_temporal
    )
    assert resultado == "[{'n': 3}]"


# --- 3. Varias sentencias con ";" ------------------------------------------------

@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT 1; DROP TABLE facturas",
        "SELECT 1; DELETE FROM facturas",
        # Espacios y saltos de línea alrededor del segundo ";" (y ";" final).
        "SELECT 1;   DROP TABLE facturas   ;",
        "SELECT 1\n;\nDELETE FROM facturas\n;\n",
        "SELECT 1 ;\n\t DELETE FROM facturas  \n ;  ",
        # Solo se tolera UN ";" final: dos seguidos ya son varias sentencias.
        "SELECT 1;;",
    ],
)
def test_rechaza_varias_sentencias_en_el_validador(modulo_sql_seguro, base_temporal, consulta):
    # El rechazo debe venir de NUESTRA validación, no de SQLite. Lo distinguimos
    # por el mensaje: el guard responde "ERROR: por seguridad..." y un fallo de
    # SQLite (p. ej. el ProgrammingError de execute() con varias sentencias)
    # responde "ERROR al ejecutar...". Si el guard no las frena, este test falla
    # aunque SQLite acabe protegiendo la base.
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(consulta, base_temporal)

    assert resultado.startswith(MENSAJE_GUARD)
    assert contar_filas(base_temporal) == 3


# --- 4. SQL inválido: no debe lanzar excepción -----------------------------------

def test_sql_invalido_devuelve_error_sin_lanzar_excepcion(modulo_sql_seguro, base_temporal):
    resultado = modulo_sql_seguro.ejecutar_sql_seguro(
        "SELECT * FROM tabla_que_no_existe", base_temporal
    )
    assert resultado.startswith(MENSAJE_SQLITE)
