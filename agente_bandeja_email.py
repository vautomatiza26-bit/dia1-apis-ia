"""
PROYECTO: Agente de gestión inteligente de bandeja de email

Aplica el mismo patrón que ya dominas (extracción estructurada + tool
calling) a un dominio nuevo, añadiendo dos capacidades nuevas:
- Clasificación en categorías predefinidas
- Generación de una respuesta sugerida (no solo extracción de datos)

Esto demuestra que el patrón que aprendiste con facturas se transfiere
a cualquier tipo de documento no estructurado, no es un caso memorizado.
"""

import os
import json
import csv
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
CARPETA_EMAILS = Path("emails")
ARCHIVO_SALIDA = "emails_procesados.csv"

HERRAMIENTA_ANALIZAR_EMAIL = {
    "name": "analizar_email",
    "description": "Analiza un email: lo clasifica, evalúa su prioridad, lo resume y sugiere una respuesta.",
    "input_schema": {
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "enum": ["consulta_cliente", "incidencia", "solicitud_presupuesto", "spam", "otro"],
                "description": "Categoría del email",
            },
            "prioridad": {
                "type": "string",
                "enum": ["alta", "media", "baja"],
                "description": "Urgencia con la que debería atenderse",
            },
            "resumen": {
                "type": "string",
                "description": "Resumen del email en una frase",
            },
            "requiere_respuesta": {
                "type": "boolean",
                "description": "Si este email necesita una respuesta humana o no (ej. el spam no la necesita)",
            },
            "respuesta_sugerida": {
                "type": "string",
                "description": (
                    "Un borrador breve y profesional de respuesta, en español. "
                    "Si requiere_respuesta es false, deja este campo vacío."
                ),
            },
        },
        "required": ["categoria", "prioridad", "resumen", "requiere_respuesta", "respuesta_sugerida"],
    },
}


def analizar_email(texto_email: str) -> dict:
    respuesta = cliente.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        tools=[HERRAMIENTA_ANALIZAR_EMAIL],
        tool_choice={"type": "tool", "name": "analizar_email"},
        messages=[{"role": "user", "content": f"Analiza este email:\n\n{texto_email}"}],
    )
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return bloque.input
    return {}


def procesar_bandeja():
    archivos = list(CARPETA_EMAILS.glob("*.txt"))
    if not archivos:
        print(f"❌ No hay archivos .txt en '{CARPETA_EMAILS}'.")
        return

    resultados = []
    # Orden de prioridad para poder ordenar la bandeja de más a menos urgente
    orden_prioridad = {"alta": 0, "media": 1, "baja": 2}

    for archivo in archivos:
        print(f"Procesando: {archivo.name}...")
        texto = archivo.read_text(encoding="utf-8")
        datos = analizar_email(texto)
        datos["archivo"] = archivo.name
        resultados.append(datos)
        print(f"  ✅ [{datos['categoria']}] prioridad {datos['prioridad']}")

    # Ordenamos la bandeja por prioridad, como haría un buen triaje
    resultados.sort(key=lambda x: orden_prioridad.get(x["prioridad"], 3))

    print("\n" + "=" * 60)
    print("📥 BANDEJA ORDENADA POR PRIORIDAD")
    print("=" * 60)
    for r in resultados:
        print(f"\n[{r['prioridad'].upper()}] {r['archivo']} — {r['categoria']}")
        print(f"  Resumen: {r['resumen']}")
        if r["requiere_respuesta"]:
            print(f"  💬 Respuesta sugerida: {r['respuesta_sugerida']}")
        else:
            print("  (no requiere respuesta)")

    columnas = ["archivo", "categoria", "prioridad", "resumen", "requiere_respuesta", "respuesta_sugerida"]
    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\n✅ {len(resultados)} emails procesados y guardados en '{ARCHIVO_SALIDA}'")


if __name__ == "__main__":
    procesar_bandeja()
