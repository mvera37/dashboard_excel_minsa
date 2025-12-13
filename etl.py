# ================================================================
#                    ETL FINAL TELE-MAMOGRAFÍA
# ================================================================
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# ================================================================
# CONFIG
# ================================================================
EXCEL_PATH = r"D:\MINSA\Proyecto Mónica\Analisis - copia\Reporte_SIA_TELEATIENDO_02122025.xlsx"

TABLE_FACT = "mamografias_teleatiendo"
TABLE_DIM_UBIGEO = "dim_ubigeo"
TABLE_DIM_NACIONALIDAD = "dim_nacionalidad"
TABLE_DIM_ETNIA = "dim_etnia"

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


# ================================================================
# UTILIDAD: Normalizar columnas
# ================================================================
def norm_col(c):
    import unicodedata
    c = c.strip()
    c = ''.join(ch for ch in unicodedata.normalize('NFD', c)
                if unicodedata.category(ch) != "Mn")
    c = c.lower().replace(" ", "_")
    c = ''.join(ch for ch in c if ch.isalnum() or ch == "_")
    return c


def normalizar_columnas(df):
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]
    return df


# ================================================================
# CARGA DIMENSIONES
# ================================================================
def cargar_tablas_dimension(engine):
    print("\n=== Cargando tablas dimensión ===")

    # Dim. Nacionalidad
    df_n = pd.read_excel("Nacionalidad.xlsx")
    df_n.columns = ["codigo_nacionalidad", "pais"]
    df_n.to_sql(TABLE_DIM_NACIONALIDAD, engine, if_exists="replace", index=False)

    # Dim Etnia
    df_e = pd.read_excel("Etnia.xlsx")
    df_e.columns = ["codigo_etnia", "raza"]
    df_e.to_sql(TABLE_DIM_ETNIA, engine, if_exists="replace", index=False)

    # Dim UBIGEO
    df_u = pd.read_excel("UBIGEO.xlsx")
    df_u.columns = [
        "iddist", "nombdep", "nombprov", "nombdist",
        "capital_legal", "cod_reg_nat", "region_natural"
    ]
    df_u.to_sql(TABLE_DIM_UBIGEO, engine, if_exists="replace", index=False)


# ================================================================
# LIMPIEZA BASE PRINCIPAL
# ================================================================
def limpiar_df(df):

    df = normalizar_columnas(df)

    if "servicio" not in df:
        raise Exception("No existe columna SERVICIO")

    # Solo telemamografía
    df = df[df["servicio"] == "mamografia"].copy()

    # Columnas que se eliminan
    eliminar = [
        "medico_tratante_id", "servicio_id", "paciente_id",
        "procedimiento_id", "establecimiento_destino_id",
        "establecimiento_origen_id", "codigo_prestacion_id",
        "observacion_consultor", "conclusion_consultor", "provincia",
        "departamento", "id"
    ]
    df = df.drop(columns=[c for c in eliminar if c in df], errors="ignore")

    # Convertir fecha
    df["fecha_solicitud"] = pd.to_datetime(df.get("fecha_solicitud"), errors="coerce")
    df["fecha_registro_consultor"] = pd.to_datetime(df.get("fecha_registro_consultor"), errors="coerce")

    # Edad
    df["fecha_nacimiento"] = pd.to_datetime(df.get("fecha_nacimiento"), errors="coerce")
    hoy = pd.Timestamp.today()
    df["edad"] = ((hoy - df["fecha_nacimiento"]).dt.days / 365.25).astype("float")
    df.loc[df["edad"] < 0, "edad"] = None

    # Tiempo de atención
    df["tiempo_atencion_dias"] = (
        (df["fecha_registro_consultor"] - df["fecha_solicitud"]) / pd.Timedelta(days=1)
    )

    # Sexo
    df["sexo"] = df["sexo"].replace({
        1: "MASCULINO",
        2: "FEMENINO"
    })

    # Grupo etario
    df["grupo_etario"] = pd.cut(
        df["edad"],
        bins=[0, 19, 29, 39, 49, 59, 69, 200],
        labels=["0-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
    )

    # BIRADS texto
    df["birads_categoria"] = df["bi_rads"].map({
        0: "0 – Incompleto",
        1: "1 – Negativo",
        2: "2 – Benigno",
        3: "3 – Probablemente benigno",
        4: "4 – Sospechoso",
        5: "5 – Alta sospecha"
    })

    # Severidad clínica
    df["birads_severidad"] = df["bi_rads"].apply(
        lambda x: "NORMAL" if x in [0, 1, 2] else "ANORMAL" if x in [3, 4, 5] else None
    )

    # Indicador de anormalidad
    df["es_anormalidad"] = df["bi_rads"].apply(lambda x: 1 if x in [3, 4, 5] else 0)

    # Mujeres 40-69 y entrega resultado
    df["es_mujer_40_69"] = ((df["sexo"] == "FEMENINO") &
                            (df["edad"].between(40, 69))).astype(int)

    df["es_entrega_resultado_4069"] = (
        df["es_mujer_40_69"] &
        (df["estado"].str.lower() == "atendido")
    ).astype(int)

    # Normalización de estado
    df["estado_atencion_normalizado"] = df["estado"].str.lower().str.strip()

    # Añadir dimensiones temporales
    df["anio"] = df["fecha_solicitud"].dt.year
    df["mes"] = df["fecha_solicitud"].dt.month
    df["anio_mes"] = df["fecha_solicitud"].dt.to_period("M").astype(str)

    return df


# ================================================================
# JOINS
# ================================================================
def hacer_joins(df, engine):
    u = pd.read_sql(f"SELECT * FROM {TABLE_DIM_UBIGEO}", engine)
    n = pd.read_sql(f"SELECT * FROM {TABLE_DIM_NACIONALIDAD}", engine)
    e = pd.read_sql(f"SELECT * FROM {TABLE_DIM_ETNIA}", engine)

    df = df.merge(u, left_on="distrito", right_on="iddist", how="left")
    df = df.merge(n, left_on="nacionalidad_id", right_on="codigo_nacionalidad", how="left")
    df = df.merge(e, left_on="etnia_id", right_on="codigo_etnia", how="left")

    return df


# ================================================================
# MAIN
# ================================================================
def main():
    print("\n=== Leyendo archivo ===")
    df = pd.read_excel(EXCEL_PATH)
    df = limpiar_df(df)

    if DB_URL is None:
        print("DATABASE_URL NO CONFIGURADO")
        return

    engine = create_engine(DB_URL)

    # Cargar tablas dimensión
    cargar_tablas_dimension(engine)

    # Joins
    df = hacer_joins(df, engine)

    # Subir fact
    df.to_sql(TABLE_FACT, engine, if_exists="replace", index=False)

    print("\n=== ETL COMPLETO ===")
    print(f"Registros finales: {len(df)}")


if __name__ == "__main__":
    main()
