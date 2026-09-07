"""
DÍA 1 - Primer script: hablar directamente con las APIs de Claude y GPT
sin pasar por n8n, para entender qué hace n8n "por debajo".

Qué aprendes aquí:
- Cómo se autentica una petición a una API de IA (con una API key)
- Qué es un "mensaje" y un "rol" (user/assistant/system)
- Qué es un token (verás el conteo en la respuesta)
- Cómo se estructura una respuesta JSON de estas APIs
"""

import os
from dotenv import load_dotenv
import anthropic
from openai import OpenAI

# Carga las claves desde el archivo .env (nunca las escribas aquí a mano)
load_dotenv()

# --- Configuración ---
PROMPT = "Explícame en 2 frases qué es un webhook, como si se lo explicaras a alguien de logística."

# --- Llamada a Claude (Anthropic) ---
def preguntar_a_claude(prompt: str) -> str:
    cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    respuesta = cliente.messages.create(
        model="claude-sonnet-4-6",   # modelo que usa el motor de Claude
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # La respuesta viene como una lista de "bloques" de contenido.
    # Para texto simple, tomamos el texto del primer bloque.
    texto = respuesta.content[0].text
    tokens_usados = respuesta.usage.input_tokens + respuesta.usage.output_tokens

    return f"{texto}\n\n(tokens usados: {tokens_usados})"


# --- Llamada a GPT (OpenAI) ---
def preguntar_a_gpt(prompt: str) -> str:
    cliente = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    respuesta = cliente.chat.completions.create(
        model="gpt-4o-mini",  # modelo económico y rápido de OpenAI
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    texto = respuesta.choices[0].message.content
    tokens_usados = respuesta.usage.total_tokens

    return f"{texto}\n\n(tokens usados: {tokens_usados})"


# --- Programa principal ---
if __name__ == "__main__":
    print("=" * 60)
    print("PROMPT ENVIADO A AMBOS MODELOS:")
    print(PROMPT)
    print("=" * 60)

    print("\n🔵 RESPUESTA DE CLAUDE:")
    print(preguntar_a_claude(PROMPT))

    print("\n🟢 RESPUESTA DE GPT:")
    print(preguntar_a_gpt(PROMPT))