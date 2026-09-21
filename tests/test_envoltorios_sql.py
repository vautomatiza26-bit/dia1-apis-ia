"""
Tests de los envoltorios de ejecutar_sql_seguro en semana3_agente_sql.py y api.py.

Por qué existen: la validación real vive en sql_seguro.py (ver test_sql_seguro.py),
pero cada archivo mantiene su BASE_DATOS y su propia ejecutar_sql_seguro(consulta_sql)
como envoltorio fino. Estos tests comprueban que ese cableado funciona: que cada
envoltorio delega en la validación endurecida y usa SU base de datos.

Importa sobre todo para api.py: es el endpoint público (/preguntar) donde el
modelo escribe SQL. Hasta que delegó en sql_seguro, su copia no rechazaba varias
sentencias y dependía de que SQLite las frenara por su cuenta.

Offline y gratuitos: la fixture modulo_envoltorio (conftest.py) neutraliza
load_dotenv y pone una clave falsa; la base es una SQLite temporal.
"""

import pytest

from conftest import contar_filas

MENSAJE_GUARD = "ERROR: por seguridad"


@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT 1; DROP TABLE facturas",
        "SELECT 1;   DROP TABLE facturas   ;",
        "SELECT 1;;",
    ],
)
def test_envoltorio_rechaza_varias_sentencias(modulo_envoltorio, base_temporal, monkeypatch, consulta):
    monkeypatch.setattr(modulo_envoltorio, "BASE_DATOS", str(base_temporal))

    resultado = modulo_envoltorio.ejecutar_sql_seguro(consulta)

    # Que empiece por el mensaje del guard (y no por un error de SQLite) prueba
    # que el rechazo lo hace nuestra validación y no el driver.
    assert resultado.startswith(MENSAJE_GUARD)
    assert contar_filas(base_temporal) == 3


def test_envoltorio_acepta_select_valido(modulo_envoltorio, base_temporal, monkeypatch):
    # También prueba que el envoltorio pasa SU BASE_DATOS: si no lo hiciera,
    # no encontraría la tabla 'facturas' de la base temporal.
    monkeypatch.setattr(modulo_envoltorio, "BASE_DATOS", str(base_temporal))

    resultado = modulo_envoltorio.ejecutar_sql_seguro("SELECT COUNT(*) AS n FROM facturas")

    assert resultado == "[{'n': 3}]"
