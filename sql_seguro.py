"""
Ejecución segura de SQL generado por un modelo: solo lectura (SELECT).

Por qué existe este módulo aparte: la validación vivía copiada en
semana3_agente_sql.py y en api.py, y las dos copias divergieron (la de api.py,
que es el endpoint público, se quedó sin el rechazo de varias sentencias).
Una regla de seguridad duplicada acaba desincronizada; con una sola copia, un
cambio o un test cubren a todos los que la usan.

Es un módulo deliberadamente PEQUEÑO y SIN EFECTOS SECUNDARIOS: solo importa
sqlite3, así que se puede importar desde cualquier sitio (y desde los tests)
sin leer .env ni crear un cliente de la API. Por eso recibe la ruta de la base
de datos como parámetro en vez de tener su propia constante: cada script sigue
decidiendo qué base usa.
"""

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
        conexion = sqlite3.connect(ruta_bd)
        conexion.row_factory = sqlite3.Row  # para poder leer resultados por nombre de columna
        cursor = conexion.execute(consulta_sql)
        filas = [dict(fila) for fila in cursor.fetchall()]
        conexion.close()
        return str(filas) if filas else "La consulta no devolvió resultados."
    except sqlite3.Error as error:
        return f"ERROR al ejecutar la consulta: {error}"
