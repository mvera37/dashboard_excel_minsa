import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# ==========================
# 1. Cargar variables .env
# ==========================
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("DATABASE_URL no está configurado en el archivo .env")

engine = create_engine(DB_URL)

# ==========================
# 2. Función para cargar tabla dimensión
# ==========================
def subir_tabla_dimension(df, table_name):
    print(f"Subiendo tabla: {table_name} ...")
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"✔ Tabla '{table_name}' subida correctamente. Filas: {len(df)}\n")

# ==========================
# 3. Cargar archivos Excel
# ==========================
RUTAS = {
    "nacionalidad": r"D:\MINSA\Proyecto Mónica\Analisis - copia\Nacionalidad.xlsx",
    "etnia":        r"D:\MINSA\Proyecto Mónica\Analisis - copia\Etnia.xlsx",
    "ubigeo":       r"D:\MINSA\Proyecto Mónica\Analisis - copia\UBIGEO.xlsx",
}

# ==========================
# 4. Procesamiento y carga
# ==========================
def main():

    # ---- Nacionalidad ----
    df_nac = pd.read_excel(RUTAS["nacionalidad"])
    df_nac.columns = ["codigo_nacionalidad", "pais"]
    subir_tabla_dimension(df_nac, "dim_nacionalidad")

    # ---- Etnia ----
    df_etnia = pd.read_excel(RUTAS["etnia"])
    df_etnia.columns = ["codigo_etnia", "raza"]
    subir_tabla_dimension(df_etnia, "dim_etnia")

    # ---- UBIGEO ----
    df_ubi = pd.read_excel(RUTAS["ubigeo"])
    
    # Renombrar columnas asegurando uniformidad
    df_ubi.columns = [
        "ubigeo",
        "departamento",
        "provincia",
        "distrito",
        "capital",
        "cod_region_nat",
        "region_natural"
    ]
    
    subir_tabla_dimension(df_ubi, "dim_ubigeo")

    print("\n🎉 Todas las tablas dimensión fueron cargadas exitosamente.")


if __name__ == "__main__":
    main()

