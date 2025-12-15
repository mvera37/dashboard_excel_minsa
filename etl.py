# ================================================================
#          ETL FINAL - SINCRONIZACIÓN TOTAL DE UBIGEO (6 DIGITOS)
# ================================================================
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os

# CONFIGURACIÓN
EXCEL_PATH = r"D:\MINSA\Proyecto Mónica\Analisis - copia\Reporte_SIA_TELEATIENDO_0212025.xlsx"
TABLE_FACT = "mamografias_teleatiendo"
TABLE_DIM_UBIGEO = "dim_ubigeo"
TABLE_DIM_NACIONALIDAD = "dim_nacionalidad"
TABLE_DIM_ETNIA = "dim_etnia"

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# ================================================================
# 1. CARGA DE DIMENSIONES (CON RELLENO DE CEROS)
# ================================================================
def cargar_dimensiones(engine):
    print("\n=== 1. CARGANDO DIMENSIONES ===")
    try:
        # UBIGEO
        if os.path.exists("UBIGEO.xlsx"):
            df_u = pd.read_excel("UBIGEO.xlsx")
            # Nombres estándar internos (minúsculas)
            df_u.columns = ["iddist", "nombdep", "nombprov", "nombdist", "capital_legal", "cod_reg_nat", "region_natural"]
            
            # --- CORRECCIÓN CLAVE ---
            # 1. Convertir a Texto
            # 2. Quitar decimales (.0)
            # 3. Rellenar con ceros a la izquierda hasta llegar a 6 dígitos (zfill)
            df_u["iddist"] = df_u["iddist"].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
            
            df_u.to_sql(TABLE_DIM_UBIGEO, engine, if_exists="replace", index=False)
            print(f"✔ Dimensión Ubigeo normalizada a 6 dígitos. Ejemplo: '{df_u['iddist'].iloc[0]}'")

        # NACIONALIDAD
        if os.path.exists("Nacionalidad.xlsx"):
            df_n = pd.read_excel("Nacionalidad.xlsx")
            df_n.columns = ["codigo_nacionalidad", "pais"]
            df_n.to_sql(TABLE_DIM_NACIONALIDAD, engine, if_exists="replace", index=False)

        # ETNIA
        if os.path.exists("Etnia.xlsx"):
            df_e = pd.read_excel("Etnia.xlsx")
            df_e.columns = ["codigo_etnia", "raza"]
            df_e.to_sql(TABLE_DIM_ETNIA, engine, if_exists="replace", index=False)

    except Exception as e:
        print(f"⚠️ Error cargando dimensiones: {e}")

# ================================================================
# 2. PROCESAMIENTO EXCEL
# ================================================================
def procesar_excel(df):
    print(f"\n=== 2. PROCESANDO EXCEL ({len(df)} filas) ===")
    
    # Normalizar cabeceras
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # FILTRO SERVICIO
    if "servicio" in df.columns:
        df = df[df["servicio"].astype(str).str.lower().str.contains("mamo", na=False)].copy()

    # FECHAS
    cols_fechas = ["fecha registro consultor", "fecha solicitud", "fecha nacimiento"]
    for col in cols_fechas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    # --- PREPARACIÓN UBIGEO (REGLA DE 6 DÍGITOS) ---
    if "distrito" in df.columns:
        # Limpieza base
        clean_dist = df["distrito"].astype(str).str.split('.').str[0].str.strip()
        # Aplicamos la misma regla que a la dimensión: Rellenar con ceros (20101 -> 020101)
        df["distrito_6dig"] = clean_dist.str.zfill(6)
        
        print(f"   > Ejemplo conversión: Original '{df['distrito'].iloc[0]}' -> Normalizado '{df['distrito_6dig'].iloc[0]}'")

    # BI-RADS
    if "bi rads" in df.columns:
        temp = df["bi rads"].astype(str).str.replace(" ", "")
        df["birads_categoria"] = temp.map({
            '0': "0 – Incompleto", '1': "1 – Negativo", '2': "2 – Benigno",
            '3': "3 – Probablemente benigno", '4': "4 – Sospechoso", '5': "5 – Alta sospecha",
            '0.0': "0 – Incompleto", '1.0': "1 – Negativo", '2.0': "2 – Benigno",
            '3.0': "3 – Probablemente benigno", '4.0': "4 – Sospechoso", '5.0': "5 – Alta sospecha"
        })
        df["es_anormalidad"] = temp.apply(lambda x: 1 if x in ['3', '4', '5', '3.0', '4.0', '5.0'] else 0)
        df["bi rads"] = pd.to_numeric(df["bi rads"], errors='coerce')

    # CÁLCULOS VARIOS
    hoy = pd.Timestamp.today()
    if "fecha nacimiento" in df.columns:
        df["edad"] = ((hoy - df["fecha nacimiento"]).dt.days / 365.25).fillna(0).astype(int)
        df.loc[df["edad"] < 0, "edad"] = 0

    if "fecha registro consultor" in df.columns and "fecha solicitud" in df.columns:
        df["tiempo_atencion_dias"] = (df["fecha registro consultor"] - df["fecha solicitud"]).dt.total_seconds() / 86400.0

    if "sexo" in df.columns:
        df["sexo"] = df["sexo"].replace({1: "MASCULINO", 2: "FEMENINO", "1": "MASCULINO", "2": "FEMENINO"})
    
    if "estado" in df.columns:
        df["estado_atencion_normalizado"] = df["estado"].astype(str).str.lower().str.strip()
    
    if "fecha solicitud" in df.columns:
        df["anio_mes"] = df["fecha solicitud"].dt.to_period("M").astype(str)
        df["anio"] = df["fecha solicitud"].dt.year
        df["mes"] = df["fecha solicitud"].dt.month

    if "sexo" in df.columns and "edad" in df.columns:
        df["es_mujer_40_69"] = ((df["sexo"] == "FEMENINO") & (df["edad"].between(40, 69))).astype(int)

    return df

# ================================================================
# 3. REALIZAR JOINS
# ================================================================
def hacer_joins(df, engine):
    print("\n=== 3. REALIZANDO JOINS ===")
    
    # UBIGEO
    if "distrito_6dig" in df.columns:
        try:
            u = pd.read_sql(f"SELECT * FROM {TABLE_DIM_UBIGEO}", engine)
            u.columns = [c.lower() for c in u.columns]
            
            # Buscamos la columna ID y aplicamos LA MISMA REGLA DE 6 DÍGITOS
            col_id = "iddist" if "iddist" in u.columns else "id_dist"
            u[col_id] = u[col_id].astype(str).str.split('.').str[0].str.strip().str.zfill(6)
            
            # MERGE
            df = df.merge(u, left_on="distrito_6dig", right_on=col_id, how="left")
            
            # Verificación
            cruzados = df['nombdep'].notna().sum()
            print(f"   > Match Ubigeo: {cruzados} filas de {len(df)}")
            
            # Llenado de columnas
            if "nombdep" in df.columns:
                df["nombdep"] = df["nombdep"].fillna("DESCONOCIDO")
                df["nombprov"] = df["nombprov"].fillna("DESCONOCIDO")
                df["departamento"] = df["nombdep"]
                df["provincia"] = df["nombprov"]

        except Exception as e:
            print(f"   ❌ Falló Merge Ubigeo: {e}")

    # JOINS NACIONALIDAD / ETNIA
    if "nacionalidad id" in df.columns:
        try:
            n = pd.read_sql(f"SELECT * FROM {TABLE_DIM_NACIONALIDAD}", engine)
            df["nacionalidad id"] = pd.to_numeric(df["nacionalidad id"], errors='coerce')
            n.columns = [c.lower() for c in n.columns]
            if "codigo_nacionalidad" in n.columns:
                n["codigo_nacionalidad"] = pd.to_numeric(n["codigo_nacionalidad"], errors='coerce')
                df = df.merge(n, left_on="nacionalidad id", right_on="codigo_nacionalidad", how="left")
        except: pass

    if "etnia id" in df.columns:
        try:
            e = pd.read_sql(f"SELECT * FROM {TABLE_DIM_ETNIA}", engine)
            df["etnia id"] = pd.to_numeric(df["etnia id"], errors='coerce')
            e.columns = [c.lower() for c in e.columns]
            if "codigo_etnia" in e.columns:
                e["codigo_etnia"] = pd.to_numeric(e["codigo_etnia"], errors='coerce')
                df = df.merge(e, left_on="etnia id", right_on="codigo_etnia", how="left")
        except: pass

    return df

# ================================================================
# MAIN (SINCRONIZACIÓN AUTOMÁTICA DE NOMBRES)
# ================================================================
def main():
    print(f"Leyendo: {os.path.basename(EXCEL_PATH)}")
    try:
        df = pd.read_excel(EXCEL_PATH)
        if "Unnamed: 0" in str(df.columns): df = pd.read_excel(EXCEL_PATH, header=2)
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    try:
        engine = create_engine(DB_URL)
        # 1. Cargamos dimensiones (asegurando 6 dígitos)
        cargar_dimensiones(engine)
        
        # 2. Procesamos Excel (asegurando 6 dígitos) y unimos
        df = procesar_excel(df)
        df = hacer_joins(df, engine)
        
    except Exception as e:
        print(f"❌ Error procesando: {e}")
        return

    # 4. SUBIDA FINAL
    try:
        insp = inspect(engine)
        cols_reales_bd = [c['name'] for c in insp.get_columns(TABLE_FACT)]
        
        # Sincronizador de nombres (Mapeo minúscula -> Nombre Real BD)
        mapa_nombres = {c.lower(): c for c in cols_reales_bd}
        df.rename(columns=mapa_nombres, inplace=True)
        
        cols_finales = [c for c in df.columns if c in cols_reales_bd]
        df_final = df[cols_finales].copy()
        
        # Revertir distrito a numérico para guardado (opcional, pero buena práctica si BD es bigint)
        # Nota: Si el zfill agregó ceros '020101', al pasarlo a int será 20101.
        # Si la BD espera el número 20101, esto es correcto.
        if "distrito" in df_final.columns:
             df_final["distrito"] = pd.to_numeric(df_final["distrito"], errors='coerce').fillna(0).astype('int64')

        print(f"\n=== 4. ACTUALIZANDO BD ({len(df_final)} registros) ===")
        print(f"   > Columnas detectadas para subir: {len(cols_finales)}")
        
        if len(df_final) > 0:
            with engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {TABLE_FACT}"))
                conn.commit()
            
            df_final.to_sql(TABLE_FACT, engine, if_exists="append", index=False)
            print("✅ ¡CARGA EXITOSA!")
        else:
            print("⚠️ Tabla vacía.")
            
    except Exception as e:
        print(f"❌ Error subiendo a BD: {e}")

if __name__ == "__main__":
    main()