# Camino hacia AI Engineer

Proyectos prácticos de automatización con LLMs (Claude y GPT), construidos como parte de mi proceso de especialización en IA generativa y automatización.

Vengo del mundo de la automatización con **n8n** (proyecto profesional [JAPIOS IA](https://github.com/vautomatiza26-bit)) y este repositorio documenta el paso a construir estas soluciones también a nivel de código, entendiendo qué ocurre "por debajo" de las herramientas no-code.

## Contenido

### `dia1_comparar_modelos.py`
Primera llamada directa a las APIs de Anthropic (Claude) y OpenAI (GPT), sin intermediarios. Compara la respuesta de ambos modelos al mismo prompt y muestra el consumo de tokens de cada uno.

### `dia3_4_tool_calling.py`
Extracción de datos estructurados de una factura usando **tool/function calling**: en vez de que el modelo responda en texto libre, se le fuerza a devolver un JSON con un esquema exacto (número de factura, fecha, importe, cliente). Es la base técnica que hace fiable conectar un LLM a un sistema real.

### `dia5_procesar_facturas.py`
Mini-pipeline completo: lee varias facturas de la carpeta `facturas/`, extrae los datos de cada una con IA y exporta el resultado a un CSV listo para abrir en Excel — con manejo de errores para que un fallo en un archivo no detenga el proceso completo.

## Stack

- Python
- Anthropic API (Claude) / OpenAI API (GPT)
- Tool/function calling para salidas estructuradas
- Manejo de variables de entorno (`python-dotenv`) para no exponer claves

## Por qué este enfoque

Cada script está pensado como un paso incremental: de "hablar con una IA" a "extraer datos estructurados" a "procesar documentos en lote de forma fiable". Es el mismo patrón que uso en producción con n8n en JAPIOS IA, pero aquí construido desde el código para entender y controlar cada parte del proceso.

---

*Este repositorio se irá ampliando con nuevos proyectos: RAG, agentes con herramientas, e integraciones más avanzadas.*
