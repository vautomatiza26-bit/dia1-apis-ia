"""
DÍAS 3-4 - Function/Tool calling: la diferencia entre "IA que charla"
e "IA que se conecta a sistemas reales" (lo que haces en n8n, pero visto por dentro).

Qué aprendes aquí:
- Cómo definir una "herramienta" (tool) con un esquema de datos exacto
- Cómo forzar al modelo a devolver datos estructurados (JSON), no texto libre
- Cómo leer la respuesta cuando el modelo "llama" a tu función
- Contar tokens de forma aproximada antes de enviar la petición
"""

import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Texto de ejemplo: simula una factura real (sustituye por una de verdad) ---
TEXTO_FACTURA = """
FACTURA 221/26
EDIALBA SUBCONTRATA S.L.
Fecha: 15/09/2026
Cliente: Constructora Ejemplo S.A.
Concepto: Servicios de subcontrata - Septiembre 2026
Importe total: 3.450,00 EUR
"""

# --- 1. Definimos la "herramienta": la estructura EXACTA que queremos recibir ---
# Esto es el equivalente a definir los campos de salida en un nodo de n8n,
# pero aquí se lo describes directamente al modelo.
HERRAMIENTA_EXTRAER_FACTURA = {
    "name": "extraer_datos_factura",
    "description": "Extrae los datos clave de una factura en formato estructurado.",
    "input_schema": {
        "type": "object",
        "properties": {
            "numero_factura": {"type": "string", "description": "Número o referencia de la factura"},
            "fecha": {"type": "string", "description": "Fecha de la factura en formato DD/MM/AAAA, o null si no aparece"},
            "importe_total": {"type": "number", "description": "Importe total en euros, solo el número"},
            "nombre_cliente": {"type": "string", "description": "Nombre del cliente al que se factura"},
        },
        "required": ["numero_factura", "fecha", "importe_total", "nombre_cliente"],
    },
}


def extraer_datos_estructurados(texto_factura: str) -> dict:
    respuesta = cliente.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        tools=[HERRAMIENTA_EXTRAER_FACTURA],
        # tool_choice fuerza a que SIEMPRE use esta herramienta, en vez de responder en texto libre
        tool_choice={"type": "tool", "name": "extraer_datos_factura"},
        messages=[
            {"role": "user", "content": f"Extrae los datos de esta factura:\n\n{texto_factura}"}
        ],
    )

    # Cuando el modelo usa una herramienta, la respuesta viene en un bloque
    # de tipo "tool_use", y los datos estructurados están en .input
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return bloque.input  # esto ya es un diccionario Python listo para usar

    return {}


if __name__ == "__main__":
    print("=" * 60)
    print("TEXTO DE ENTRADA (factura):")
    print(TEXTO_FACTURA)
    print("=" * 60)

    datos = extraer_datos_estructurados(TEXTO_FACTURA)

    print("\n📦 DATOS ESTRUCTURADOS DEVUELTOS POR EL MODELO:")
    print(json.dumps(datos, indent=2, ensure_ascii=False))

    print("\n✅ Esto ya es un diccionario Python usable directamente, por ejemplo:")
    print(f"   Importe total: {datos.get('importe_total')} EUR")
    print(f"   Cliente: {datos.get('nombre_cliente')}")
    print("\n   (En n8n esto sería el output listo para insertar en una hoja de cálculo,")
    print("   una base de datos o un sistema de facturación, sin parsear texto libre)")
