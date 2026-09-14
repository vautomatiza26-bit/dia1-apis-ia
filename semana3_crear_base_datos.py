"""
SEMANA 3 - DÍAS 1-2: De CSV a base de datos SQL

Qué aprendes hoy:
- Por qué un CSV no escala (sin tipos de datos reales, sin consultas,
  sin control de duplicados, todo el archivo se reescribe cada vez)
- Crear una tabla en SQLite con tipos de datos definidos
- Migrar datos existentes de CSV a la base de datos
- Consultas SQL básicas: SELECT, WHERE, ORDER BY, SUM

SQLite guarda toda la base de datos en un solo archivo (facturas.db),
sin necesidad de instalar ni configurar ningún servidor - ideal para
proyectos pequeños y para aprender SQL antes de dar el salto a
PostgreSQL/MySQL en un proyecto más grande.
"""

import sqlite3
import csv
from pathlib import Path

CSV_ORIGEN = Path("facturas_procesadas.csv")
BASE_DATOS = Path("facturas.db")


def crear_tabla(conexion: sqlite3.Connection):
    """
    Define la ESTRUCTURA de la tabla: cada columna con su tipo de dato.
    Esto es algo que un CSV no tiene - en un CSV, todo es texto plano
    hasta que alguien lo interpreta; en SQL, el tipo se garantiza.
    """
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo_origen TEXT,
            numero_factura TEXT UNIQUE,
            fecha TEXT,
            importe_total REAL,
            nombre_cliente TEXT
        )
    """)
    # UNIQUE en numero_factura evita que la misma factura se guarde dos veces
    # si ejecutas la migración varias veces por error.


def migrar_csv_a_sql(conexion: sqlite3.Connection):
    if not CSV_ORIGEN.exists():
        print(f"❌ No existe {CSV_ORIGEN}. Ejecuta antes dia5_procesar_facturas.py")
        return

    with open(CSV_ORIGEN, "r", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f, delimiter=";"))

    insertadas = 0
    for fila in filas:
        try:
            conexion.execute(
                """
                INSERT INTO facturas (archivo_origen, numero_factura, fecha, importe_total, nombre_cliente)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    fila["archivo_origen"],
                    fila["numero_factura"],
                    fila["fecha"],
                    float(fila["importe_total"]),
                    fila["nombre_cliente"],
                ),
            )
            insertadas += 1
        except sqlite3.IntegrityError:
            # Ya existía esa factura (por el UNIQUE) - no pasa nada, la saltamos
            print(f"  ⏭️  {fila['numero_factura']} ya estaba en la base de datos, se omite")

    conexion.commit()
    print(f"✅ {insertadas} facturas nuevas migradas a {BASE_DATOS}")


def probar_consultas(conexion: sqlite3.Connection):
    """Algunas consultas SQL de ejemplo para que veas el patrón."""
    print("\n--- Consultas de prueba ---")

    cursor = conexion.execute("SELECT COUNT(*) FROM facturas")
    print(f"Total de facturas: {cursor.fetchone()[0]}")

    cursor = conexion.execute("SELECT SUM(importe_total) FROM facturas")
    print(f"Suma de todos los importes: {cursor.fetchone()[0]:.2f} €")

    cursor = conexion.execute(
        "SELECT numero_factura, nombre_cliente, importe_total FROM facturas ORDER BY importe_total DESC LIMIT 1"
    )
    factura_mayor = cursor.fetchone()
    print(f"Factura de mayor importe: {factura_mayor[0]} ({factura_mayor[1]}) - {factura_mayor[2]} €")


if __name__ == "__main__":
    conexion = sqlite3.connect(BASE_DATOS)
    crear_tabla(conexion)
    migrar_csv_a_sql(conexion)
    probar_consultas(conexion)
    conexion.close()
