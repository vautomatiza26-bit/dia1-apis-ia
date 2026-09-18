# Dockerfile - define el entorno exacto donde corre tu aplicación,
# igual en tu PC, en Render, o en cualquier otro proveedor.

# Imagen base: Python 3.12 en su versión "slim" (más ligera, menos peso)
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero SOLO requirements.txt (no todo el código todavía).
# Esto es una optimización importante: Docker cachea cada paso, así que
# si solo cambias tu código (no las dependencias), no vuelve a reinstalar
# todo desde cero - solo si requirements.txt cambia.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ahora sí, copiamos el resto del código del proyecto
COPY . .

# Documenta qué puerto usa la aplicación (informativo, no abre el puerto por sí solo)
EXPOSE 8000

# Comando que se ejecuta al arrancar el contenedor
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
