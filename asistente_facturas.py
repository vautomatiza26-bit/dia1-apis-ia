"""
SEMANA 2 - DÍA 5: Asistente interactivo de facturas

Cierre de la Semana 2: el mismo agente multi-herramienta de los Días 3-4,
convertido en una herramienta interactiva por terminal. Puedes hacerle
preguntas seguidas sin tocar el código - esto es lo más parecido a un
producto real que has construido hasta ahora.

Uso: py asistente_facturas.py
Escribe 'salir' para terminar.
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


# --- Herramienta 1: búsqueda semántica (RAG) ---
def obtener_embedding(texto: str) -> np.ndarray:
    respuesta = cliente_openai.embeddings.create(model=MODELO_EMBEDDINGS, input=texto)
    return np.array(respuesta.data[0].embedding)


def similitud_coseno(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def buscar_facturas_por_contenido(pregunta: str) -> str:
    indice = []
    for archivo in CARPETA_FACTURAS.glob("*.txt"):
        texto = archivo.read_text(encoding="utf-8")
        indice.append({"archivo": archivo.name, "texto": texto, "embedding": obtener_embedding(texto)})

    embedding_pregunta = obtener_embedding(pregunta)
    for item in indice:
        item["similitud"] = similitud_coseno(embedding_pregunta, item["embedding"])

    top = sorted(indice, key=lambda x: x["similitud"], reverse=True)[:2]
    return "\n\n".join(f"[{d['archivo']}]\n{d['texto']}" for d in top)


# --- Herramienta 2: consulta de datos estructurados ---
def consultar_todas_las_facturas() -> str:
    if not CSV_FACTURAS.exists():
        return "No hay datos disponibles. Ejecuta primero dia5_procesar_facturas.py"
    with open(CSV_FACTURAS, "r", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    return json.dumps(filas, ensure_ascii=False, indent=2)


HERRAMIENTAS = [
    {
        "name": "buscar_facturas_por_contenido",
        "description": (
            "Busca facturas relacionadas semánticamente con un tema o contenido. "
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
            "Devuelve TODOS los datos estructurados de TODAS las facturas procesadas. "
            "Úsala para cálculos, comparaciones, totales, importes máximos/mínimos."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCIONES_DISPONIBLES = {
    "buscar_facturas_por_contenido": lambda entrada: buscar_facturas_por_contenido(entrada["pregunta"]),
    "consultar_todas_las_facturas": lambda entrada: consultar_todas_las_facturas(),
}


def preguntar_al_agente(pregunta: str, historial: list) -> str:
    """
    Igual que en el Día 3-4, pero ahora recibe y devuelve el historial
    completo de la conversación, para que el asistente recuerde preguntas
    anteriores (memoria conversacional básica).
    """
    historial.append({"role": "user", "content": pregunta})

    while True:
        respuesta = cliente_claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            tools=HERRAMIENTAS,
            messages=historial,
        )

        if respuesta.stop_reason != "tool_use":
            texto_final = next(b.text for b in respuesta.content if b.type == "text")
            historial.append({"role": "assistant", "content": respuesta.content})
            return texto_final

        historial.append({"role": "assistant", "content": respuesta.content})
        resultados_herramientas = []

        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                print(f"   🔧 usando herramienta: {bloque.name}")
                funcion = FUNCIONES_DISPONIBLES[bloque.name]
                resultado = funcion(bloque.input)
                resultados_herramientas.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": resultado,
                })

        historial.append({"role": "user", "content": resultados_herramientas})


def main():
    print("=" * 60)
    print("🤖 ASISTENTE DE FACTURAS")
    print("Pregúntame lo que quieras sobre tus facturas.")
    print("Escribe 'salir' para terminar.")
    print("=" * 60)

    historial = []

    while True:
        pregunta = input("\n🧑 Tú: ").strip()

        if pregunta.lower() in ("salir", "exit", "quit"):
            print("👋 ¡Hasta la próxima!")
            break

        if not pregunta:
            continue

        try:
            respuesta = preguntar_al_agente(pregunta, historial)
            print(f"\n🤖 Asistente: {respuesta}")
        except Exception as error:
            print(f"⚠️ Ha ocurrido un error: {error}")


if __name__ == "__main__":
    main()
