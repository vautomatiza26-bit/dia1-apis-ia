# Contexto del proyecto

Este repositorio es el portfolio técnico de Víctor Herreros Arenas, construido como parte de su
proceso de reconversión hacia AI Automation Engineer. Cada script documenta un paso incremental
de aprendizaje, desde llamadas básicas a APIs de LLM hasta un sistema completo desplegado en
producción.

## Objetivo del repositorio
Portfolio público y funcional para candidaturas a empleo remoto como AI Automation Engineer.
Repositorio: https://github.com/vautomatiza26-bit/dia1-apis-ia
Demo en vivo: https://asistente-facturas-api.onrender.com

## Convenciones del proyecto
- Código y comentarios en español.
- Cada script nuevo debe explicar el "por qué" en comentarios, no solo el "qué" — es un
  proyecto de aprendizaje, no solo de entrega.
- Nunca subir `.env`, `credentials.json`, `token.json` ni cualquier archivo de credenciales
  (ya están en `.gitignore`, pero revisa `git status` antes de cada commit por costumbre).
- El CSV/base de datos se genera con delimitador `;` (no `,`), por compatibilidad con Excel
  en español.
- Los evals que llaman a la API de pago (`eval_extraccion_facturas.py`) solo se ejecutan
  manualmente, nunca en CI automático (ver `.github/workflows/eval-manual.yml`).
- Tras cualquier cambio, actualizar el README correspondiente si añade un script nuevo.

## Estado actual
Cubiertos: LLMs (Claude/GPT), tool calling, RAG (manual y ChromaDB), agentes multi-herramienta
con memoria, SQLite y text-to-SQL con seguridad, OAuth con Gmail, evals, streaming, FastAPI +
interfaz de chat, Docker, CI/CD con GitHub Actions.

Dos dominios trabajados: facturas y clasificación de email.
