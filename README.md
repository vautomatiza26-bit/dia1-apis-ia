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

### `semana2_rag_basico.py`
Sistema de **RAG (Retrieval-Augmented Generation)**: indexa las facturas calculando sus embeddings, busca las más relevantes por similitud semántica ante una pregunta en lenguaje natural, y genera una respuesta con Claude basada solo en esos documentos.

### `semana2_agente_herramientas.py`
**Agente multi-herramienta**: el modelo elige por sí mismo, según la pregunta, entre búsqueda semántica (RAG) o consulta de datos estructurados agregados — sin lógica if/else fija en el código. Implementa el bucle estándar de un agente (el modelo puede pedir herramientas varias veces antes de responder).

### `asistente_facturas.py`
Versión interactiva por terminal del agente anterior, con **memoria conversacional**: mantiene el historial de la conversación para responder preguntas de seguimiento sin repetir contexto, y evita llamadas innecesarias a herramientas cuando ya tiene la información.

## Stack

- Python
- Anthropic API (Claude) / OpenAI API (GPT), incluyendo su API de embeddings
- Tool/function calling para salidas estructuradas y para agentes multi-herramienta
- RAG (embeddings + similitud coseno con NumPy)
- Manejo de variables de entorno (`python-dotenv`) para no exponer claves

## Por qué este enfoque

Cada script está pensado como un paso incremental: de "hablar con una IA" a "extraer datos estructurados" a "procesar documentos en lote de forma fiable" a "un agente que decide por sí mismo qué herramienta usar". Es el mismo patrón que uso en producción con n8n en JAPIOS IA, pero aquí construido desde el código para entender y controlar cada parte del proceso.

---

*Este repositorio se irá ampliando con nuevos proyectos: integraciones más avanzadas, despliegue y bases de datos.*
