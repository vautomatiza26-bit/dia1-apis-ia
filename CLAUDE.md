# dia1-apis — Portfolio técnico de AI Automation Engineer

Repositorio público de aprendizaje: cada script es un paso incremental, desde llamadas básicas a APIs de LLM hasta un sistema desplegado en producción (dos dominios: facturas y clasificación de email).
Repo: https://github.com/vautomatiza26-bit/dia1-apis-ia · Demo: https://asistente-facturas-api.onrender.com

## Entorno y comandos
- Windows + PowerShell (no bash). Python 3.14 con las dependencias instaladas globalmente (no hay entorno virtual).
- Arrancar la API: `py -m uvicorn api:app --reload`
- Tests: `py -m pytest -v` (offline y gratuitos)
- Docker (build y run): `docker build -t asistente-facturas-api .` y `docker run -p 8000:8000 --env-file .env asistente-facturas-api`
- Estructura: `api.py` + `index.html`, scripts `dia*`/`semana*`, `asistente_facturas.py`, `agente_bandeja_email.py`, `eval_extraccion_facturas.py`, `facturas/`, `emails/`, `Dockerfile`, `.github/workflows/`

## Convenciones
- Código y comentarios en español. Cada script nuevo explica el "por qué" en comentarios, no solo el "qué".
- Si añades un script nuevo, actualiza el README correspondiente.
- Antes de cada commit, muestra `git status` y comprueba que no se cuela ninguna credencial.

## Reglas que no se rompen
- Nunca leer, mostrar ni subir `.env`, `credentials.json` ni `token.json` (están en `.gitignore`).
- El agente text-to-SQL solo permite SELECT, y esa validación vive en el código, no en el prompt.
- El CSV/base de datos usa `;` como delimitador (compatibilidad con Excel en español).
- La interfaz web usa rutas relativas, no `http://localhost...` (evita errores de CORS en Docker).
- Los evals que llaman a la API de pago (`eval_extraccion_facturas.py`) solo se ejecutan a mano, nunca en CI automático (ver `.github/workflows/eval-manual.yml`). No los lances sin preguntar.

## Cómo trabajar
- Responde en español. Es un proyecto de aprendizaje: explica el porqué de cada decisión y da pasos concretos con comandos de PowerShell.
- Si algo no es buena idea, dilo directamente.
- Antes de cambios grandes, propón un plan corto y espera confirmación.
- Ahorra tokens: no leas carpetas enteras (busca por texto y abre solo lo necesario), no pegues logs largos y no repitas código que no cambia.

# Compact instructions
Al compactar conserva: objetivo actual, archivos modificados, comandos ya ejecutados, errores exactos de tests y decisiones tomadas. Descarta exploraciones descartadas y logs repetidos.
