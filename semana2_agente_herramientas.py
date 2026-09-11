"""
SEMANA 2 - DÍAS 3-4: Agente con herramientas (multi-tool agent)

Qué aprendes hoy:
- La diferencia entre "forzar" una herramienta (Semana 1) y dejar que el
  modelo ELIJA entre varias según la pregunta (esto es un agente de verdad)
- El "bucle de agente": el modelo puede pedir usar una herramienta, tú
  ejecutas el código real, le devuelves el resultado, y el modelo decide
  si necesita otra herramienta más o ya puede responder
- Cómo aplicar la lección del RAG: dar al agente la herramienta correcta
  para cada tipo de pregunta (semántica vs. agregación de datos)
"""

import os
import csv
import json
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()

cliente_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CARPETA_FACTURAS = Path("facturas")
CSV_FACTURAS = Path("facturas_procesadas.csv")
MODELO_EMBEDDINGS = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# HERRAMIENTA 1: búsqueda semántica (RAG) - para preguntas sobre CONTENIDO
# ---------------------------------------------------------------------------
def obtener_embedding(texto: str) -> np.ndarray:
    respuesta = cliente_openai.embeddings.create(model=MODELO_EMBEDDINGS, input=texto)
    return np.array(respuesta.data[0].embedding)


def similitud_coseno(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def buscar_facturas_por_contenido(pregunta: str) -> str:
    """Busca facturas relacionadas semánticamente con la pregunta (RAG)."""
    indice = []
    for archivo in CARPETA_FACTURAS.glob("*.txt"):
        texto = archivo.read_text(encoding="utf-8")
        indice.append({"archivo": archivo.name, "texto": texto, "embedding": obtener_embedding(texto)})

    embedding_pregunta = obtener_embedding(pregunta)
    for item in indice:
        item["similitud"] = similitud_coseno(embedding_pregunta, item["embedding"])

    top = sorted(indice, key=lambda x: x["similitud"], reverse=True)[:2]
    return "\n\n".join(f"[{d['archivo']}]\n{d['texto']}" for d in top)


# ---------------------------------------------------------------------------
# HERRAMIENTA 2: consulta de datos estructurados - para preguntas de CÁLCULO
# ---------------------------------------------------------------------------
def consultar_todas_las_facturas() -> str:
    """Devuelve TODAS las facturas ya extraídas en el CSV, para cálculos/comparaciones."""
    if not CSV_FACTURAS.exists():
        return "No hay datos disponibles. Ejecuta primero dia5_procesar_facturas.py"

    with open(CSV_FACTURAS, "r", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f, delimiter=";"))

    return json.dumps(filas, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# DEFINICIÓN DE HERRAMIENTAS PARA EL MODELO
# ---------------------------------------------------------------------------
HERRAMIENTAS = [
    {
        "name": "buscar_facturas_por_contenido",
        "description": (
            "Busca facturas relacionadas semánticamente con un tema o contenido "
            "(ej: 'facturas de transporte', 'facturas relacionadas con logística'). "
            "NO sirve para cálculos, totales o comparaciones numéricas entre TODAS las facturas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"pregunta": {"type": "string", "description": "El tema o contenido a buscar"}},
            "required": ["pregunta"],
        },
    },
    {
        "name": "consultar_todas_las_facturas",
        "description": (
            "Devuelve TODOS los datos estructurados (número, fecha, importe, cliente) de TODAS "
            "las facturas procesadas. Úsala para preguntas de cálculo, comparación, totales, "
            "importes máximos/mínimos, o cuando necesites ver el conjunto completo de datos."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCIONES_DISPONIBLES = {
    "buscar_facturas_por_contenido": lambda entrada: buscar_facturas_por_contenido(entrada["pregunta"]),
    "consultar_todas_las_facturas": lambda entrada: consultar_todas_las_facturas(),
}


# ---------------------------------------------------------------------------
# BUCLE DEL AGENTE
# ---------------------------------------------------------------------------
def preguntar_al_agente(pregunta: str):
    print(f"\n❓ Pregunta: {pregunta}")

    mensajes = [{"role": "user", "content": pregunta}]

    while True:
        respuesta = cliente_claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            tools=HERRAMIENTAS,
            messages=mensajes,
        )

        # Si el modelo no pidió usar ninguna herramienta, ya tenemos la respuesta final
        if respuesta.stop_reason != "tool_use":
            texto_final = next(b.text for b in respuesta.content if b.type == "text")
            print(f"\n💬 Respuesta final:\n{texto_final}")
            return

        # El modelo quiere usar una o más herramientas: las ejecutamos
        mensajes.append({"role": "assistant", "content": respuesta.content})
        resultados_herramientas = []

        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                print(f"🔧 El agente decidió usar: {bloque.name}")
                funcion = FUNCIONES_DISPONIBLES[bloque.name]
                resultado = funcion(bloque.input)
                resultados_herramientas.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": resultado,
                })

        # Le devolvemos el resultado de la herramienta al modelo para que continúe
        mensajes.append({"role": "user", "content": resultados_herramientas})


if __name__ == "__main__":
    preguntar_al_agente("¿Qué factura tiene el importe más alto?")
    preguntar_al_agente("¿Hay alguna factura relacionada con logística o almacenaje?")
