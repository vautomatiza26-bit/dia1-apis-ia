"""
SEMANA 3 - DÍA 5: API web con FastAPI (preparación para despliegue)

Qué aprendes hoy:
- Cómo exponer tu agente como un servicio web (API REST), no solo un
  script que solo tú puedes ejecutar desde tu terminal
- El concepto de "endpoint": una URL que recibe una petición y devuelve
  una respuesta - es exactamente lo que consume n8n cuando llamas a
  una API externa, pero ahora construido por ti
- Cómo preparar el proyecto para desplegarlo en un servicio gratuito (Render)

Uso local (antes de desplegar):
  py -m uvicorn api:app --reload
Luego abre en el navegador: http://127.0.0.1:8000/docs
Ahí verás una interfaz automática para probar la API sin escribir código.
"""

import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic
import sql_seguro

load_dotenv()

cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
BASE_DATOS = "facturas.db"

ESQUEMA_BASE_DATOS = """
Tabla: facturas
Columnas:
  - id (entero, identificador único)
  - archivo_origen (texto)
  - numero_factura (texto)
  - fecha (texto, formato DD/MM/AAAA)
  - importe_total (número decimal, en euros)
  - nombre_cliente (texto)
"""

HERRAMIENTA_SQL = {
    "name": "ejecutar_consulta_sql",
    "description": (
        f"Ejecuta una consulta SQL de solo lectura (SELECT) sobre la base de datos de facturas.\n"
        f"Esquema disponible:\n{ESQUEMA_BASE_DATOS}"
    ),
    "input_schema": {
        "type": "object",
        "properties": {"consulta_sql": {"type": "string", "description": "La consulta SQL SELECT a ejecutar"}},
        "required": ["consulta_sql"],
    },
}


def ejecutar_sql_seguro(consulta_sql: str) -> str:
    """Envoltorio fino: la validación vive en sql_seguro.py, compartida con semana3_agente_sql.py."""
    return sql_seguro.ejecutar_sql_seguro(consulta_sql, BASE_DATOS)


def preguntar_al_agente(pregunta: str) -> str:
    mensajes = [{"role": "user", "content": pregunta}]

    while True:
        respuesta = cliente_claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            tools=[HERRAMIENTA_SQL],
            messages=mensajes,
        )

        if respuesta.stop_reason != "tool_use":
            return next(b.text for b in respuesta.content if b.type == "text")

        mensajes.append({"role": "assistant", "content": respuesta.content})
        resultados = []
        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                resultado = ejecutar_sql_seguro(bloque.input["consulta_sql"])
                resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": resultado})
        mensajes.append({"role": "user", "content": resultados})


# --- Definición de la API ---
app = FastAPI(title="API Asistente de Facturas")


class PreguntaEntrada(BaseModel):
    pregunta: str


@app.get("/")
def interfaz_chat():
    """Sirve la interfaz de chat web en la raíz del sitio."""
    return FileResponse("index.html")


@app.get("/health")
def salud():
    """Endpoint de comprobación técnica: confirma que la API está viva."""
    return {"estado": "ok", "mensaje": "API del asistente de facturas funcionando"}


@app.post("/preguntar")
def preguntar(entrada: PreguntaEntrada):
    """
    Endpoint principal: recibe una pregunta en JSON y devuelve la
    respuesta del agente. Esto es lo que cualquier aplicación externa
    (una web, un n8n, otro programa) podría llamar para usar tu agente.
    """
    respuesta = preguntar_al_agente(entrada.pregunta)
    return {"pregunta": entrada.pregunta, "respuesta": respuesta}
