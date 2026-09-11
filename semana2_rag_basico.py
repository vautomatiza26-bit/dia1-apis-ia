"""
SEMANA 2 - DÍAS 1-2: RAG básico (Retrieval-Augmented Generation)

Qué aprendes hoy:
- Qué es un embedding y cómo se genera
- Cómo calcular similitud entre vectores (similitud coseno)
- Cómo montar un flujo RAG completo: indexar -> buscar -> generar respuesta

Ejemplo práctico: preguntas en lenguaje natural sobre tus facturas,
sin necesidad de que el LLM las haya visto antes.
"""

import os
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()

cliente_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CARPETA_FACTURAS = Path("facturas")
MODELO_EMBEDDINGS = "text-embedding-3-small"  # modelo económico de OpenAI para embeddings


def obtener_embedding(texto: str) -> np.ndarray:
    """Convierte un texto en un vector numérico (embedding)."""
    respuesta = cliente_openai.embeddings.create(
        model=MODELO_EMBEDDINGS,
        input=texto,
    )
    return np.array(respuesta.data[0].embedding)


def similitud_coseno(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """
    Mide qué tan 'parecidos' son dos vectores, en una escala de -1 a 1
    (en la práctica, para embeddings de texto, normalmente entre 0 y 1).
    Cuanto más alto, más relacionados están los textos en significado.
    """
    return np.dot(vector_a, vector_b) / (np.linalg.norm(vector_a) * np.linalg.norm(vector_b))


def indexar_facturas() -> list[dict]:
    """
    Paso 1 de RAG: 'indexar' - leer todos los documentos y calcular
    su embedding una sola vez, guardándolo en memoria.
    """
    print("📚 Indexando facturas (calculando embeddings)...")
    indice = []

    for archivo in CARPETA_FACTURAS.glob("*.txt"):
        texto = archivo.read_text(encoding="utf-8")
        embedding = obtener_embedding(texto)
        indice.append({
            "archivo": archivo.name,
            "texto": texto,
            "embedding": embedding,
        })
        print(f"  ✅ {archivo.name} indexado")

    return indice


def buscar_relevantes(pregunta: str, indice: list[dict], top_n: int = 2) -> list[dict]:
    """
    Paso 2 de RAG: 'retrieval' - convierte la pregunta en embedding
    y devuelve los documentos más parecidos (los top_n más relevantes).
    """
    embedding_pregunta = obtener_embedding(pregunta)

    for item in indice:
        item["similitud"] = similitud_coseno(embedding_pregunta, item["embedding"])

    # Ordena de más a menos relevante y coge los top_n
    ordenados = sorted(indice, key=lambda x: x["similitud"], reverse=True)
    return ordenados[:top_n]


def responder_con_contexto(pregunta: str, documentos_relevantes: list[dict]) -> str:
    """
    Paso 3 de RAG: 'generation' - le pasamos a Claude SOLO los documentos
    relevantes (no todos) junto con la pregunta, para que responda basándose
    en ellos.
    """
    contexto = "\n\n---\n\n".join(
        f"[{doc['archivo']}]\n{doc['texto']}" for doc in documentos_relevantes
    )

    respuesta = cliente_claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"Aquí tienes información de facturas:\n\n{contexto}\n\n"
                f"Basándote SOLO en esta información, responde a esta pregunta: {pregunta}"
            ),
        }],
    )
    return respuesta.content[0].text


def preguntar(pregunta: str, indice: list[dict]):
    print(f"\n❓ Pregunta: {pregunta}")

    relevantes = buscar_relevantes(pregunta, indice)
    print("📄 Documentos recuperados como más relevantes:")
    for doc in relevantes:
        print(f"   - {doc['archivo']} (similitud: {doc['similitud']:.3f})")

    respuesta = responder_con_contexto(pregunta, relevantes)
    print(f"\n💬 Respuesta:\n{respuesta}")


if __name__ == "__main__":
    indice = indexar_facturas()

    # Prueba con un par de preguntas distintas
    preguntar("¿Qué factura tiene el importe más alto?", indice)
    preguntar("¿Hay alguna factura relacionada con transporte?", indice)
