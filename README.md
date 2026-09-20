# Camino hacia AI Engineer

> Todos los datos de ejemplo (facturas, emails y base de datos) son ficticios.

![CI](https://github.com/vautomatiza26-bit/dia1-apis-ia/actions/workflows/ci.yml/badge.svg)
Proyectos prácticos de automatización con LLMs (Claude y GPT), construidos como parte de mi proceso de especialización en IA generativa y automatización.

Vengo del mundo de la automatización con **n8n** (proyecto propio de especialización [JAPIOS IA](https://github.com/vautomatiza26-bit)) y este repositorio documenta el paso a construir estas soluciones también a nivel de código, entendiendo qué ocurre "por debajo" de las herramientas no-code.

🚀 **Demo en vivo:** [asistente-facturas-api.onrender.com](https://asistente-facturas-api.onrender.com) — chatea directamente con el agente, sin instalar nada (el plan gratuito puede tardar hasta 1 minuto en "despertar" si lleva un rato inactiva). Documentación técnica de la API en [/docs](https://asistente-facturas-api.onrender.com/docs).

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

### `semana3_crear_base_datos.py`
Migra los datos de facturas de CSV a una base de datos **SQLite**, con esquema tipado y control de duplicados.

### `semana3_agente_sql.py`
Agente **text-to-SQL**: el modelo escribe sus propias consultas SQL según la pregunta en lenguaje natural, en vez de depender de funciones fijas por tipo de pregunta. Incluye una capa de seguridad que bloquea cualquier consulta que no sea de solo lectura (`SELECT`).

### `api.py` + `index.html`
La lógica del agente expuesta como **API web con FastAPI**, con documentación interactiva automática (`/docs`) y una **interfaz de chat propia** servida en la raíz, desplegadas públicamente en Render.

### `agente_bandeja_email.py`
Aplicación del mismo patrón de extracción estructurada a un **dominio distinto**: clasifica emails por categoría y prioridad (usando `enum` para restringir valores válidos), genera un resumen y sugiere una respuesta — dejando el campo de respuesta vacío cuando no es necesaria (ej. spam). Demuestra que la arquitectura se transfiere entre dominios, no es un caso memorizado.

### `conectar_gmail.py`
Integración con **Gmail real vía OAuth**: autenticación con el flujo estándar de "Authorization Code" (incluye renovación automática de token), lectura y parseo de mensajes MIME reales, y aplicación del agente de clasificación sobre la bandeja de entrada de verdad.

### `vectorial_chromadb.py`
Sustituye la búsqueda semántica manual (NumPy) por una **base de datos vectorial persistente (ChromaDB)**: los embeddings se calculan una sola vez y se reutilizan entre ejecuciones, en vez de recalcularse cada vez.

### `eval_extraccion_facturas.py`
Sistema de **evaluación (eval)** con casos de prueba y respuesta correcta conocida (*ground truth*), incluyendo un caso diseñado para detectar si el modelo "alucina" datos que no están en el texto. Mide precisión de forma automática y reproducible, en vez de comprobar manualmente caso a caso.

### `streaming_demo.py`
Comparación entre llamadas bloqueantes y **streaming** de respuestas, midiendo el "time to first token" real frente al tiempo total.

### `Dockerfile` + `.dockerignore`
**Containerización** de la API: define el entorno exacto (versión de Python, dependencias) en el que corre la aplicación, de forma que el mismo contenedor funciona igual en local, en Render o en cualquier otro proveedor cloud.

### `.github/workflows/`
**CI/CD con GitHub Actions**: comprobaciones automáticas gratuitas en cada `push` (sintaxis, ausencia de credenciales filtradas), separadas de un workflow manual de evaluación que sí consume la API de pago — una decisión deliberada de coste, no accidental.

### `tests/` (pytest)
**Tests automáticos de la validación SELECT-only** de `semana3_agente_sql.py`: comprueban que `DROP`, `DELETE`, `INSERT`, etc. se rechazan, que un `SELECT` válido funciona y que varias sentencias con `;` no modifican la base. Son **offline y gratuitos**: usan una base SQLite temporal, no leen `.env` y no llaman a ninguna API. Las dependencias de test van aparte en `requirements-dev.txt` para no engordar la imagen de producción.

```powershell
py -m pip install -r requirements-dev.txt   # una sola vez
py -m pytest -v
```

## Stack

- Python
- Anthropic API (Claude) / OpenAI API (GPT), incluyendo su API de embeddings
- Tool/function calling para salidas estructuradas y para agentes multi-herramienta
- RAG con embeddings, tanto manual (NumPy) como con base de datos vectorial (ChromaDB)
- SQL (SQLite) y patrón text-to-SQL, con validación de seguridad en las consultas generadas por IA
- OAuth 2.0 (integración real con la API de Gmail)
- FastAPI + despliegue en Render, con interfaz de chat web propia
- Evaluación sistemática de resultados de IA (evals) y streaming de respuestas
- Docker (containerización) y CI/CD con GitHub Actions
- Manejo de variables de entorno (`python-dotenv`) para no exponer claves

## Por qué este enfoque

Cada script está pensado como un paso incremental: de "hablar con una IA" a "extraer datos estructurados" a "procesar documentos en lote de forma fiable" a "un agente que decide por sí mismo qué herramienta usar" a "ese agente expuesto como servicio real, con interfaz propia y accesible por cualquiera" — pasando por generalizar el patrón a un dominio distinto, conectar con un proveedor externo real (Gmail), medir la calidad del sistema de forma sistemática, y automatizar su propia validación en cada cambio. Es el mismo enfoque que aplico en mi proyecto propio de automatización con n8n (JAPIOS IA), pero aquí construido desde el código para entender y controlar cada parte del proceso.

---

*Este repositorio se irá ampliando con nuevos proyectos e integraciones más avanzadas.*

