"""
EVALUACIÓN DE SISTEMAS DE IA (LLM EVALS)

Qué aprendes hoy:
- Qué es un "ground truth" (conjunto de casos con la respuesta correcta
  ya conocida de antemano) y por qué es la base de cualquier evaluación seria
- Cómo medir automáticamente si un sistema de IA "funciona bien", en vez
  de confiar en "a mí me parece que responde bien" mirando unos pocos casos
- La diferencia entre coincidencia exacta y coincidencia flexible al
  comparar texto generado por IA (ej. fechas o importes con formato distinto)
- Por qué esto es CRÍTICO antes de cambiar un prompt, un modelo, o
  desplegar una actualización: sin evals, no sabes si mejoraste o rompiste algo

Este es el tipo de sistema que un equipo de IA en producción ejecuta
automáticamente en cada cambio, como si fueran "tests" pero para
comportamiento de IA en vez de código determinista.
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()
cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

HERRAMIENTA_EXTRAER_FACTURA = {
    "name": "extraer_datos_factura",
    "description": "Extrae los datos clave de una factura en formato estructurado.",
    "input_schema": {
        "type": "object",
        "properties": {
            "numero_factura": {"type": "string"},
            "fecha": {"type": "string", "description": "Formato DD/MM/AAAA"},
            "importe_total": {"type": "number"},
            "nombre_cliente": {"type": "string"},
        },
        "required": ["numero_factura", "fecha", "importe_total", "nombre_cliente"],
    },
}


def extraer_datos_factura(texto: str) -> dict:
    respuesta = cliente.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        tools=[HERRAMIENTA_EXTRAER_FACTURA],
        tool_choice={"type": "tool", "name": "extraer_datos_factura"},
        messages=[{"role": "user", "content": f"Extrae los datos de esta factura:\n\n{texto}"}],
    )
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return bloque.input
    return {}


# --- CONJUNTO DE EVALUACIÓN: casos con la respuesta correcta YA CONOCIDA ---
# En un proyecto real, esto se construye a partir de casos reales ya
# verificados a mano, no inventados - aquí los inventamos para practicar.
CASOS_DE_PRUEBA = [
    {
        "texto": "FACTURA 100/26\nACME S.L.\nFecha: 01/01/2026\nCliente: Cliente Uno\nImporte total: 100,00 EUR",
        "esperado": {"numero_factura": "100/26", "fecha": "01/01/2026", "importe_total": 100.0, "nombre_cliente": "Cliente Uno"},
    },
    {
        "texto": "Nº Factura: F-500\nEmisor: Beta Corp\nFecha de emisión: 15/03/2026\nFacturado a: Empresa Dos S.L.\nTotal a pagar: 2.350,75 €",
        "esperado": {"numero_factura": "F-500", "fecha": "15/03/2026", "importe_total": 2350.75, "nombre_cliente": "Empresa Dos S.L."},
    },
    {
        # Caso "trampa": número de factura y fecha NO aparecen en el texto,
        # pero el nombre del cliente SÍ. Un buen sistema debe extraer lo que
        # SÍ está presente, y marcar como desconocido solo lo que falta de verdad.
        "texto": "FACTURA SIN NÚMERO VISIBLE\nCliente: Empresa Tres\nSin fecha ni importe especificados en el texto",
        "esperado": {
            "numero_factura": None,   # None = esperamos que quede marcado como desconocido
            "fecha": None,
            "importe_total": None,
            "nombre_cliente": "Empresa Tres",  # esto sí debe extraerlo correctamente
        },
    },
    {
        "texto": "Factura 77/2026 - Distribuciones Cuatro S.A. - 08/07/2026 - Total: 45,00€",
        "esperado": {"numero_factura": "77/2026", "fecha": "08/07/2026", "importe_total": 45.0, "nombre_cliente": "Distribuciones Cuatro S.A."},
    },
]


MARCADORES_DESCONOCIDO = {"<unknown>", "unknown", "n/a", "desconocido", "", "none", "null"}


def es_marcador_desconocido(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, (int, float)) and valor == 0:
        return True
    return str(valor).strip().lower() in MARCADORES_DESCONOCIDO


def campos_coinciden(esperado, obtenido, campo: str) -> bool:
    """
    Comparación 'flexible': para texto, ignoramos mayúsculas/espacios extra.
    Para números, comparamos con margen de error mínimo (redondeo).
    Si se esperaba 'desconocido' (None), aceptamos cualquier marcador
    habitual que use el modelo para decir 'no lo sé' (<UNKNOWN>, N/A, 0...).
    """
    valor_esperado = esperado.get(campo)
    valor_obtenido = obtenido.get(campo)

    if valor_esperado is None:
        return es_marcador_desconocido(valor_obtenido)

    if campo == "importe_total":
        try:
            return abs(float(valor_obtenido) - float(valor_esperado)) < 0.01
        except (TypeError, ValueError):
            return False

    return str(valor_esperado).strip().lower() == str(valor_obtenido).strip().lower()


def evaluar_caso(caso: dict, numero_caso: int) -> dict:
    obtenido = extraer_datos_factura(caso["texto"])

    resultados_por_campo = {
        campo: campos_coinciden(caso["esperado"], obtenido, campo)
        for campo in caso["esperado"]
    }
    todos_correctos = all(resultados_por_campo.values())

    return {
        "caso": numero_caso,
        "correcto": todos_correctos,
        "detalle": resultados_por_campo if not todos_correctos else "✅ Todos los campos correctos",
    }


def ejecutar_evaluacion():
    print("=" * 60)
    print(f"🧪 EVALUANDO SOBRE {len(CASOS_DE_PRUEBA)} CASOS DE PRUEBA")
    print("=" * 60)

    resultados = []
    for i, caso in enumerate(CASOS_DE_PRUEBA, start=1):
        print(f"\nCaso {i}...")
        resultado = evaluar_caso(caso, i)
        resultados.append(resultado)
        estado = "✅ PASÓ" if resultado["correcto"] else "❌ FALLÓ"
        print(f"  {estado} — {resultado['detalle']}")

    aciertos = sum(1 for r in resultados if r["correcto"])
    precision = (aciertos / len(resultados)) * 100

    print("\n" + "=" * 60)
    print(f"📊 RESULTADO: {aciertos}/{len(resultados)} casos correctos ({precision:.1f}% de precisión)")
    print("=" * 60)

    if precision < 100:
        print("\n⚠️ Revisa los casos fallidos antes de considerar el sistema listo para producción.")


if __name__ == "__main__":
    ejecutar_evaluacion()
