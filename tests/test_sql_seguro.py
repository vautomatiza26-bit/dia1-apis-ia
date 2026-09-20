"""
Tests de ejecutar_sql_seguro (semana3_agente_sql.py): la validación SELECT-only.

Por qué existen: el agente text-to-SQL deja que un modelo escriba SQL, y la
única barrera contra un DROP/DELETE es esta función. Es una regla que no se
rompe, así que conviene que un test falle si alguien la debilita sin querer.

Son tests offline y gratuitos: usan una base SQLite temporal y no llaman a
ninguna API (ver conftest.py).
"""

import pytest

from conftest import contar_filas

MENSAJE_GUARD = "ERROR: por seguridad"
MENSAJE_SQLITE = "ERROR al ejecutar"


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
def test_rechaza_sentencias_que_no_son_select(modulo_sql, base_temporal, consulta):
    resultado = modulo_sql.ejecutar_sql_seguro(consulta)

    assert resultado.startswith(MENSAJE_GUARD)
    # Además del mensaje, comprobamos el efecto real: la tabla sigue intacta.
    assert contar_filas(base_temporal) == 3


@pytest.mark.parametrize("consulta", ["", "   \n\t "])
def test_rechaza_consultas_vacias(modulo_sql, base_temporal, consulta):
    assert modulo_sql.ejecutar_sql_seguro(consulta).startswith(MENSAJE_GUARD)


def test_rechaza_with_aunque_acabe_en_select(modulo_sql, base_temporal):
    # Límite conocido: el guard exige que EMPIECE por SELECT, así que las CTE
    # (WITH ... SELECT) se descartan. Es conservador (seguro) a costa de
    # perder consultas legítimas. Este test documenta esa decisión.
    consulta = "WITH x AS (SELECT * FROM facturas) SELECT COUNT(*) FROM x"
    assert modulo_sql.ejecutar_sql_seguro(consulta).startswith(MENSAJE_GUARD)


# --- 2. SELECT válidos: deben ejecutarse ---------------------------------------

def test_select_valido_devuelve_filas(modulo_sql, base_temporal):
    resultado = modulo_sql.ejecutar_sql_seguro("SELECT COUNT(*) AS n FROM facturas")
    assert resultado == "[{'n': 3}]"


def test_select_con_agregacion(modulo_sql, base_temporal):
    resultado = modulo_sql.ejecutar_sql_seguro(
        "SELECT SUM(importe_total) AS total FROM facturas"
    )
    assert resultado == "[{'total': 400.0}]"


def test_select_con_like(modulo_sql, base_temporal):
    resultado = modulo_sql.ejecutar_sql_seguro(
        "SELECT numero_factura FROM facturas "
        "WHERE nombre_cliente LIKE '%cme%' ORDER BY id"
    )
    assert resultado == "[{'numero_factura': 'F-001'}, {'numero_factura': 'F-003'}]"


@pytest.mark.parametrize(
    "consulta",
    [
        "select COUNT(*) AS n from facturas",
        "  \n SeLeCt COUNT(*) AS n FROM facturas",
    ],
)
def test_acepta_select_en_minusculas_y_con_espacios(modulo_sql, base_temporal, consulta):
    # El guard normaliza con strip().upper() solo para comprobar; la consulta
    # original es la que se ejecuta.
    assert modulo_sql.ejecutar_sql_seguro(consulta) == "[{'n': 3}]"


def test_select_sin_resultados(modulo_sql, base_temporal):
    resultado = modulo_sql.ejecutar_sql_seguro("SELECT * FROM facturas WHERE id = 999")
    assert resultado == "La consulta no devolvió resultados."


def test_acepta_punto_y_coma_final(modulo_sql, base_temporal):
    # Un único ";" al final es válido en SQLite y los modelos lo escriben a menudo.
    resultado = modulo_sql.ejecutar_sql_seguro("SELECT COUNT(*) AS n FROM facturas;")
    assert resultado == "[{'n': 3}]"


# --- 3. Varias sentencias con ";" ------------------------------------------------

@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT 1; DROP TABLE facturas",
        "SELECT 1; DELETE FROM facturas",
    ],
)
def test_varias_sentencias_no_modifican_la_base(modulo_sql, base_temporal, consulta):
    # OJO, hueco conocido: estas consultas PASAN el guard (empiezan por SELECT).
    # Lo que las frena es que sqlite3.execute() solo admite una sentencia por
    # llamada y lanza ProgrammingError, que la función captura. Es decir, la base
    # está protegida por SQLite y no por nuestra validación.
    # Por eso el test comprueba el RESULTADO (nada cambia y hay error), no qué
    # capa lo impidió. Al endurecer el guard, el mensaje pasará a MENSAJE_GUARD.
    resultado = modulo_sql.ejecutar_sql_seguro(consulta)

    assert resultado.startswith(MENSAJE_SQLITE)
    assert contar_filas(base_temporal) == 3


# --- 4. SQL inválido: no debe lanzar excepción -----------------------------------

def test_sql_invalido_devuelve_error_sin_lanzar_excepcion(modulo_sql, base_temporal):
    resultado = modulo_sql.ejecutar_sql_seguro("SELECT * FROM tabla_que_no_existe")
    assert resultado.startswith(MENSAJE_SQLITE)
