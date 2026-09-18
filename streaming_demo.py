"""
STREAMING DE RESPUESTAS

Qué aprendes hoy:
- La diferencia entre una llamada bloqueante (esperas todo el texto)
  y una llamada en streaming (recibes fragmentos a medida que se generan)
- Por qué el streaming mejora la EXPERIENCIA percibida, aunque el tiempo
  TOTAL de la respuesta sea prácticamente el mismo
- Cómo medir el "time to first token" (TTFT), una métrica real que se usa
  para evaluar la capacidad de respuesta de un sistema de IA
"""

import os
import time
from dotenv import load_dotenv
import anthropic

load_dotenv()
cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PROMPT = "Escribe un párrafo breve explicando qué es la automatización con IA para una pyme."


def llamada_bloqueante():
    print("\n🔵 MODO BLOQUEANTE (esperando respuesta completa)...")
    inicio = time.time()

    respuesta = cliente.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": PROMPT}],
    )

    tiempo_total = time.time() - inicio
    print(f"\n(Nada se mostró hasta este momento: {tiempo_total:.2f}s)")
    print(respuesta.content[0].text)
    print(f"\n⏱️  Tiempo hasta ver ALGO de texto: {tiempo_total:.2f}s (= tiempo total)")


def llamada_streaming():
    print("\n🟢 MODO STREAMING (mostrando fragmentos a medida que llegan)...")
    inicio = time.time()
    tiempo_primer_token = None

    print()  # línea en blanco antes de empezar a imprimir el texto
    with cliente.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": PROMPT}],
    ) as stream:
        for texto_parcial in stream.text_stream:
            if tiempo_primer_token is None:
                tiempo_primer_token = time.time() - inicio
            print(texto_parcial, end="", flush=True)  # flush=True para que se vea al instante

    tiempo_total = time.time() - inicio
    print(f"\n\n⏱️  Tiempo hasta ver el PRIMER fragmento: {tiempo_primer_token:.2f}s")
    print(f"⏱️  Tiempo total de la respuesta completa: {tiempo_total:.2f}s")


if __name__ == "__main__":
    llamada_bloqueante()
    print("\n" + "=" * 60)
    llamada_streaming()

    print("\n" + "=" * 60)
    print("💡 Fíjate en la diferencia entre 'tiempo hasta ver algo' en cada modo.")
    print("   El tiempo TOTAL es parecido, pero la percepción de velocidad")
    print("   es muy distinta - eso es lo que aporta el streaming.")
