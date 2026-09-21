"""
Ejecución segura de SQL generado por un modelo: solo lectura (SELECT).

Por qué existe este módulo aparte: la validación vivía copiada en
semana3_agente_sql.py y en api.py, y las dos copias divergieron (la de api.py,
que es el endpoint público, se quedó sin el rechazo de varias sentencias).
Una regla de seguridad duplicada acaba desincronizada; con una sola copia, un
cambio o un test cubren a todos los que la usan.

Es un módulo deliberadamente PEQUEÑO y SIN EFECTOS SECUNDARIOS: solo importa la
biblioteca estándar, así que se puede importar desde cualquier sitio (y desde los tests)
sin leer .env ni crear un cliente de la API. Por eso recibe la ruta de la base
de datos como parámetro en vez de tener su propia constante: cada script sigue
decidiendo qué base usa.
"""

import contextlib
import pathlib
import sqlite3


def ejecutar_sql_seguro(consulta_sql: str, ruta_bd) -> str:
    """
    Ejecuta una consulta SQL sobre la base ruta_bd, pero SOLO si es de lectura
    (un único SELECT). Devuelve siempre un texto (las filas, o un mensaje de
    error) y nunca lanza excepciones de SQLite: el resultado se le devuelve
    tal cual al modelo como resultado de la herramienta.
    """
    consulta_limpia = consulta_sql.strip().upper()
    if not consulta_limpia.startswith("SELECT"):
        return "ERROR: por seguridad, solo se permiten consultas SELECT (solo lectura)."

    # Varias sentencias ("SELECT 1; DROP TABLE facturas"): empiezan por SELECT,
    # así que el guard de arriba las dejaría pasar. Hoy las frena sqlite3.execute()
    # (solo admite una sentencia por llamada), pero eso es una protección ajena a
    # nuestro código que podría cambiar (otro driver, executescript...). La
    # validación tiene que vivir aquí. Se tolera UN solo ";" final (los modelos lo
    # escriben a menudo); si tras quitarlo aún queda algún ";", se rechaza.
    # Limitación conocida: un ";" dentro de un texto entre comillas
    # (WHERE nombre_cliente LIKE '%;%') también se rechaza. Es conservador a
    # propósito: preferimos perder una consulta legítima rara a analizar SQL.
    if ";" in consulta_sql.strip().removesuffix(";"):
        return "ERROR: por seguridad, solo se permite una única sentencia SELECT (sin ';' intermedios)."

    try:
        # Segunda barrera, independiente del guard de arriba: la base se abre en
        # SOLO LECTURA (mode=ro). Aunque un día el guard tuviera un hueco, SQLite
        # rechazaría cualquier escritura. Además, si la ruta está mal, falla en
        # vez de crear una base vacía. Un URI "file:" exige ruta absoluta y bien
        # codificada (espacios...), de ahí .resolve().as_uri().
        # Todo va DENTRO del try para que un fallo al abrir devuelva el mensaje
        # de error y no una excepción. closing() cierra la conexión aunque la
        # consulta falle (el "with conexion" de sqlite3 no cierra, solo gestiona
        # transacciones).
        uri = pathlib.Path(ruta_bd).resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as conexion:
            conexion.row_factory = sqlite3.Row  # para poder leer resultados por nombre de columna
            cursor = conexion.execute(consulta_sql)
            filas = [dict(fila) for fila in cursor.fetchall()]
        return str(filas) if filas else "La consulta no devolvió resultados."
    except sqlite3.Error as error:
        return f"ERROR al ejecutar la consulta: {error}"
