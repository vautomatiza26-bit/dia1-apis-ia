"""
SEMANA 3 - DÍAS 3-4: Agente text-to-SQL

Qué aprendes hoy:
- Cómo darle a un LLM el "esquema" de una base de datos para que escriba
  consultas SQL válidas por sí mismo
- Por qué esto es mucho más flexible que tener una función por cada
  tipo de pregunta (lo que hacías en la Semana 2)
- Una medida de seguridad CRÍTICA: nunca dejar que el modelo ejecute
  SQL que modifique o borre datos, solo lectura (SELECT)

⚠️ Nota de seguridad importante: en un sistema real, ejecutar SQL generado
por un modelo es potencialmente peligroso (podría escribir un DROP TABLE,
por ejemplo). Aquí lo limitamos a solo permitir consultas SELECT como
medida básica de protección - en producción se añadirían más capas
(usuario de base de datos de solo lectura, límites de filas, etc.)
"""

import os
import sqlite3
from dotenv import load_dotenv
import anthropic

load_dotenv()

cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
BASE_DATOS = "facturas.db"

# Le describimos al modelo la estructura de la tabla, para que sepa qué
# columnas existen y pueda escribir SQL válido sobre ellas.
ESQUEMA_BASE_DATOS = """
Tabla: facturas
Columnas:
  - id (entero, identificador único)
  - archivo_origen (texto, nombre del archivo original)
  - numero_factura (texto)
  - fecha (texto, formato DD/MM/AAAA)
  - importe_total (número decimal, en euros)
  - nombre_cliente (texto)
"""


def ejecutar_sql_seguro(consulta_sql: str) -> str:
    """
    Ejecuta una consulta SQL, pero SOLO si es de lectura (SELECT).
    Esta comprobación es una primera barrera de seguridad básica.
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
        conexion = sqlite3.connect(BASE_DATOS)
        conexion.row_factory = sqlite3.Row  # para poder leer resultados por nombre de columna
        cursor = conexion.execute(consulta_sql)
        filas = [dict(fila) for fila in cursor.fetchall()]
        conexion.close()
        return str(filas) if filas else "La consulta no devolvió resultados."
    except sqlite3.Error as error:
        return f"ERROR al ejecutar la consulta: {error}"


HERRAMIENTA_SQL = {
    "name": "ejecutar_consulta_sql",
    "description": (
        f"Ejecuta una consulta SQL de solo lectura (SELECT) sobre la base de datos de facturas.\n"
        f"Esquema disponible:\n{ESQUEMA_BASE_DATOS}\n"
        f"Escribe SQL estándar de SQLite. Usa funciones como SUM(), COUNT(), AVG(), "
        f"ORDER BY, WHERE con LIKE para búsquedas parciales de texto, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "consulta_sql": {"type": "string", "description": "La consulta SQL SELECT a ejecutar"}
        },
        "required": ["consulta_sql"],
    },
}


def preguntar_al_agente_sql(pregunta: str):
    print(f"\n❓ Pregunta: {pregunta}")

    mensajes = [{"role": "user", "content": pregunta}]

    while True:
        respuesta = cliente_claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            tools=[HERRAMIENTA_SQL],
            messages=mensajes,
        )

        if respuesta.stop_reason != "tool_use":
            texto_final = next(b.text for b in respuesta.content if b.type == "text")
            print(f"\n💬 Respuesta:\n{texto_final}")
            return

        mensajes.append({"role": "assistant", "content": respuesta.content})
        resultados = []

        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                sql_generado = bloque.input["consulta_sql"]
                print(f"🔧 SQL generado por el modelo:\n   {sql_generado}")
                resultado = ejecutar_sql_seguro(sql_generado)
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": resultado,
                })

        mensajes.append({"role": "user", "content": resultados})


if __name__ == "__main__":
    preguntar_al_agente_sql("¿Cuál es el importe medio de todas las facturas?")
    preguntar_al_agente_sql("¿Qué facturas son de clientes cuyo nombre contiene 'S.L.'?")
    preguntar_al_agente_sql("Bórrame todas las facturas")  # prueba de seguridad
