"""
BASES DE DATOS VECTORIALES: de NumPy a ChromaDB

Qué aprendes hoy:
- Por qué recalcular embeddings en cada ejecución no escala
- Cómo una base de datos vectorial persiste los embeddings en disco,
  para calcularlos una sola vez y reutilizarlos siempre
- Cómo delega la búsqueda de similitud en la propia base de datos,
  en vez de escribir el bucle de similitud coseno a mano

Diferencia clave con semana2_rag_basico.py:
- Antes: cada ejecución = recalcular TODOS los embeddings (lento, caro)
- Ahora: "indexar" se hace UNA VEZ; luego solo se calcula el embedding
  de la PREGUNTA, y ChromaDB busca entre lo ya guardado en disco
"""

import os
from pathlib import Path
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()

cliente_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CARPETA_FACTURAS = Path("facturas")
MODELO_EMBEDDINGS = "text-embedding-3-small"

# ChromaDB guardará los datos en esta carpeta - persiste entre ejecuciones
cliente_chroma = chromadb.PersistentClient(path="./base_vectorial")
coleccion = cliente_chroma.get_or_create_collection(name="facturas")


def obtener_embedding(texto: str) -> list[float]:
    respuesta = cliente_openai.embeddings.create(model=MODELO_EMBEDDINGS, input=texto)
    return respuesta.data[0].embedding


def indexar_facturas_si_hace_falta():
    """
    A diferencia del script anterior, esto SOLO calcula embeddings de
    facturas que aún no están en la base de datos. Si ya ejecutaste esto
    antes y no has añadido facturas nuevas, no vuelve a gastar ni un
    token en embeddings.
    """
    archivos = list(CARPETA_FACTURAS.glob("*.txt"))
    ids_existentes = set(coleccion.get()["ids"])

    nuevos_ids, nuevos_textos, nuevos_embeddings = [], [], []

    for archivo in archivos:
        if archivo.name in ids_existentes:
            continue  # ya estaba indexada, nos la saltamos

        texto = archivo.read_text(encoding="utf-8")
        embedding = obtener_embedding(texto)

        nuevos_ids.append(archivo.name)
        nuevos_textos.append(texto)
        nuevos_embeddings.append(embedding)
        print(f"  🆕 Indexando por primera vez: {archivo.name}")

    if nuevos_ids:
        coleccion.add(ids=nuevos_ids, documents=nuevos_textos, embeddings=nuevos_embeddings)
        print(f"✅ {len(nuevos_ids)} facturas nuevas añadidas a la base vectorial")
    else:
        print("✅ Todas las facturas ya estaban indexadas (0 llamadas nuevas a embeddings)")


def buscar_relevantes(pregunta: str, top_n: int = 2) -> list[str]:
    """
    Ya no hay bucle manual de similitud coseno: ChromaDB lo hace
    internamente y de forma mucho más eficiente (usa estructuras de
    datos optimizadas para búsqueda vectorial, no un bucle en Python).
    """
    embedding_pregunta = obtener_embedding(pregunta)
    resultado = coleccion.query(query_embeddings=[embedding_pregunta], n_results=top_n)
    return resultado["documents"][0]


def responder_con_contexto(pregunta: str, documentos: list[str]) -> str:
    contexto = "\n\n---\n\n".join(documentos)
    respuesta = cliente_claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"Contexto:\n\n{contexto}\n\nBasándote en esto, responde: {pregunta}",
        }],
    )
    return respuesta.content[0].text


if __name__ == "__main__":
    print("📚 Comprobando índice vectorial...")
    indexar_facturas_si_hace_falta()

    pregunta = "¿Hay alguna factura relacionada con almacenaje?"
    print(f"\n❓ Pregunta: {pregunta}")
    documentos = buscar_relevantes(pregunta)
    respuesta = responder_con_contexto(pregunta, documentos)
    print(f"\n💬 Respuesta:\n{respuesta}")
