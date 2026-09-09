"""
DÍA 5 - Mini-proyecto: flujo completo entrada → IA → salida

Qué aprendes hoy:
- Leer varios archivos de una carpeta con Python (os / pathlib)
- Reutilizar la función de tool calling del Día 3-4 en un bucle
- Guardar resultados estructurados en un CSV, listo para abrir en Excel
- Manejo básico de errores (qué pasa si una factura falla)

Esto es, en miniatura, el mismo patrón que un pipeline de automatización
real: LEER -> PROCESAR CON IA -> GUARDAR. Lo que en n8n harías con
nodos conectados, aquí lo ves como código explícito.
"""

import os
import csv
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CARPETA_FACTURAS = Path("facturas")
ARCHIVO_SALIDA = "facturas_procesadas.csv"

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
        tool_choice={"type": "tool", "name": "extraer_datos_factura"},
        messages=[
            {"role": "user", "content": f"Extrae los datos de esta factura:\n\n{texto_factura}"}
        ],
    )
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return bloque.input
    return {}


def procesar_carpeta_facturas():
    if not CARPETA_FACTURAS.exists():
        print(f"❌ No existe la carpeta '{CARPETA_FACTURAS}'. Créala y mete archivos .txt de facturas.")
        return

    archivos = list(CARPETA_FACTURAS.glob("*.txt"))
    if not archivos:
        print(f"❌ No hay archivos .txt dentro de '{CARPETA_FACTURAS}'.")
        return

    resultados = []

    for archivo in archivos:
        print(f"Procesando: {archivo.name}...")
        texto = archivo.read_text(encoding="utf-8")

        try:
            datos = extraer_datos_estructurados(texto)
            datos["archivo_origen"] = archivo.name
            resultados.append(datos)
            print(f"  ✅ OK: {datos.get('numero_factura')} - {datos.get('nombre_cliente')}")
        except Exception as error:
            # En un pipeline real, nunca dejes que un fallo pare todo el proceso.
            # Registra el error y sigue con los demás archivos.
            print(f"  ⚠️ Error procesando {archivo.name}: {error}")

    if not resultados:
        print("No se pudo procesar ninguna factura.")
        return

    # Guardamos todo en un CSV, abrible directamente en Excel
    columnas = ["archivo_origen", "numero_factura", "fecha", "importe_total", "nombre_cliente"]
    # delimiter=";" porque Excel en español espera punto y coma como separador
    # de columnas (usa la coma para los decimales). Con "," en vez de ";",
    # Excel no separa las columnas al abrir el archivo con doble clic.
    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\n✅ Proceso completo: {len(resultados)} facturas guardadas en '{ARCHIVO_SALIDA}'")


if __name__ == "__main__":
    procesar_carpeta_facturas()
