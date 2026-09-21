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
import sql_seguro

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
    Envoltorio fino: la validación (solo SELECT, una única sentencia) vive en
    sql_seguro.py, compartida con api.py. Se mantiene aquí para que las llamadas
    existentes no cambien y para que este script siga usando su propio BASE_DATOS.
    """
    return sql_seguro.ejecutar_sql_seguro(consulta_sql, BASE_DATOS)


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
