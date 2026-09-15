"""
CONEXIÓN A GMAIL REAL CON OAUTH

Qué aprendes hoy:
- El flujo de autenticación OAuth "Authorization Code" en la práctica:
  la primera vez se abre el navegador para que TÚ apruebes el acceso,
  y se guarda un token.json para no repetir ese paso cada vez.
- Cómo leer y parsear datos reales de una API externa (Gmail), que vienen
  en un formato más complejo que un JSON simple (MIME, base64).
- Reutilizar el agente de clasificación ya construido, pero ahora sobre
  datos 100% reales, no archivos de prueba.

La primera vez que ejecutes esto, se abrirá tu navegador pidiéndote
iniciar sesión con Google y aprobar el acceso de SOLO LECTURA a tu Gmail.
"""

import os
import base64
import csv
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()
cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# SOLO LECTURA - nunca pidas permisos de escritura/borrado si no los necesitas.
# Es el mismo principio de "mínimo privilegio" que viste con el SQL de solo SELECT.
PERMISOS = ["https://www.googleapis.com/auth/gmail.readonly"]

NUMERO_CORREOS = 5  # cuántos correos recientes procesar
ARCHIVO_SALIDA = "gmail_procesados.csv"


def autenticar_gmail():
    """
    Gestiona el flujo OAuth completo:
    - Si ya existe token.json (de una sesión anterior), lo reutiliza.
    - Si el token caducó, lo renueva automáticamente.
    - Si no existe nada, abre el navegador para que apruebes el acceso.
    """
    credenciales = None

    if Path("token.json").exists():
        credenciales = Credentials.from_authorized_user_file("token.json", PERMISOS)

    if not credenciales or not credenciales.valid:
        if credenciales and credenciales.expired and credenciales.refresh_token:
            credenciales.refresh(Request())
        else:
            flujo = InstalledAppFlow.from_client_secrets_file("credentials.json", PERMISOS)
            credenciales = flujo.run_local_server(port=0)

        # Guardamos el token para no tener que volver a aprobar cada vez
        with open("token.json", "w") as archivo_token:
            archivo_token.write(credenciales.to_json())

    return build("gmail", "v1", credentials=credenciales)


def extraer_texto_del_mensaje(payload) -> str:
    """
    Los emails vienen en formato MIME, que puede tener varias partes
    (texto plano, HTML, adjuntos...) codificadas en base64. Esta función
    busca la parte de texto plano y la decodifica.
    """
    if "parts" in payload:
        for parte in payload["parts"]:
            if parte.get("mimeType") == "text/plain":
                datos = parte["body"].get("data", "")
                return base64.urlsafe_b64decode(datos).decode("utf-8", errors="ignore")
        # Si no hay texto plano directo, buscamos en subpartes (emails anidados)
        for parte in payload["parts"]:
            texto = extraer_texto_del_mensaje(parte)
            if texto:
                return texto
        return ""
    else:
        datos = payload.get("body", {}).get("data", "")
        if datos:
            return base64.urlsafe_b64decode(datos).decode("utf-8", errors="ignore")
        return ""


def obtener_correos_recientes(servicio, cantidad: int) -> list[dict]:
    resultado = servicio.users().messages().list(userId="me", maxResults=cantidad, labelIds=["INBOX"]).execute()
    mensajes = resultado.get("messages", [])

    correos = []
    for m in mensajes:
        mensaje_completo = servicio.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = mensaje_completo["payload"]["headers"]

        de = next((h["value"] for h in headers if h["name"] == "From"), "")
        asunto = next((h["value"] for h in headers if h["name"] == "Subject"), "(sin asunto)")
        cuerpo = extraer_texto_del_mensaje(mensaje_completo["payload"])

        correos.append({
            "id": m["id"],
            "de": de,
            "asunto": asunto,
            "cuerpo": cuerpo[:2000],  # limitamos por si algún email es muy largo
        })

    return correos


# --- Reutilizamos el mismo agente de análisis que ya construiste ---
HERRAMIENTA_ANALIZAR_EMAIL = {
    "name": "analizar_email",
    "description": "Analiza un email: lo clasifica, evalúa su prioridad, lo resume y sugiere una respuesta.",
    "input_schema": {
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "enum": ["consulta_cliente", "incidencia", "solicitud_presupuesto", "spam", "otro"],
            },
            "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
            "resumen": {"type": "string"},
            "requiere_respuesta": {"type": "boolean"},
            "respuesta_sugerida": {"type": "string"},
        },
        "required": ["categoria", "prioridad", "resumen", "requiere_respuesta", "respuesta_sugerida"],
    },
}


def analizar_email(asunto: str, de: str, cuerpo: str) -> dict:
    texto_completo = f"De: {de}\nAsunto: {asunto}\n\n{cuerpo}"
    respuesta = cliente_claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        tools=[HERRAMIENTA_ANALIZAR_EMAIL],
        tool_choice={"type": "tool", "name": "analizar_email"},
        messages=[{"role": "user", "content": f"Analiza este email:\n\n{texto_completo}"}],
    )
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return bloque.input
    return {}


def main():
    print("🔐 Autenticando con Gmail...")
    servicio = autenticar_gmail()
    print("✅ Autenticado correctamente\n")

    print(f"📥 Descargando los {NUMERO_CORREOS} correos más recientes...")
    correos = obtener_correos_recientes(servicio, NUMERO_CORREOS)

    resultados = []
    for correo in correos:
        print(f"\nProcesando: {correo['asunto'][:60]}...")
        analisis = analizar_email(correo["asunto"], correo["de"], correo["cuerpo"])
        analisis["de"] = correo["de"]
        analisis["asunto"] = correo["asunto"]
        resultados.append(analisis)
        print(f"  ✅ [{analisis['categoria']}] prioridad {analisis['prioridad']}")

    orden_prioridad = {"alta": 0, "media": 1, "baja": 2}
    resultados.sort(key=lambda x: orden_prioridad.get(x["prioridad"], 3))

    print("\n" + "=" * 60)
    print("📥 TU BANDEJA REAL, ORDENADA POR PRIORIDAD")
    print("=" * 60)
    for r in resultados:
        print(f"\n[{r['prioridad'].upper()}] {r['asunto']}")
        print(f"  De: {r['de']}")
        print(f"  Categoría: {r['categoria']}")
        print(f"  Resumen: {r['resumen']}")

    columnas = ["asunto", "de", "categoria", "prioridad", "resumen", "requiere_respuesta", "respuesta_sugerida"]
    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\n✅ Guardado en '{ARCHIVO_SALIDA}'")


if __name__ == "__main__":
    main()
