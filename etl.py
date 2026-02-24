# ==============================================================================
# ETL MINSA - v11.0 (CORRECCIÓN GEOGRÁFICA QUILLABAMBA)
# ==============================================================================
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# --- CONFIGURACIÓN ---
EXCEL_MAIN =  r"D:\MINSA\Proyecto Mónica\Analisis - copia\Reporte_SIA_TELEATIENDO_24022026.xlsx"
EXCEL_EESS = "EESS.xlsx"
TABLE_DESTINO = "vista_master_dashboard"

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def normalize_text(series):
    return series.astype(str).str.upper().str.strip()

# ---------------------------------------------------------
# 1. CARGA DE MAESTROS
# ---------------------------------------------------------
def cargar_maestros():
    print("\n=== 1. CARGANDO MAESTROS ===")
    maestros = {}

    # A. EESS
    file_eess = EXCEL_EESS if os.path.exists(EXCEL_EESS) else ("EESS.xlsx" if os.path.exists("EESS.xlsx") else None)
    if file_eess:
        try:
            df = pd.read_excel(file_eess, usecols=["Nombre del establecimiento", "Departamento", "Provincia", "Distrito"])
            df.columns = ["nombre_eess", "geo_departamento", "geo_provincia", "geo_distrito"]
            df["key_eess"] = normalize_text(df["nombre_eess"])
            # NOTA: Aquí es donde se eliminaban duplicados y ganaba Apurímac. 
            # No cambiamos esto para no romper otros cruces, corregiremos abajo.
            maestros['eess'] = df.drop_duplicates(subset=["key_eess"])
            print(f"✔ EESS cargado: {len(maestros['eess'])} registros.")
        except Exception as e: print(f"❌ Error EESS: {e}")
    else: print("❌ Falta archivo EESS")

    # B. NACIONALIDAD
    if os.path.exists("Nacionalidad.xlsx"):
        try:
            df = pd.read_excel("Nacionalidad.xlsx", dtype=str)
            df = df.iloc[:, [0, 1]] 
            df.columns = ["cod_nac", "pais"]
            df["cod_nac"] = df["cod_nac"].str.split('.').str[0].str.strip()
            maestros['nacionalidad'] = df
            print(f"✔ Nacionalidad cargada: {len(df)} registros.")
        except: pass

    # C. ETNIA
    if os.path.exists("Etnia.xlsx"):
        try:
            df = pd.read_excel("Etnia.xlsx", dtype=str)
            df = df.iloc[:, [0, 1]]
            df.columns = ["cod_etnia", "raza"]
            df["cod_etnia"] = df["cod_etnia"].str.split('.').str[0].str.strip()
            maestros['etnia'] = df
            print(f"✔ Etnia cargada: {len(df)} registros.")
        except: pass

    return maestros

# ---------------------------------------------------------
# 2. PROCESAMIENTO
# ---------------------------------------------------------
def procesar_principal(maestros):
    print(f"\n=== 2. PROCESANDO REPORTE PRINCIPAL ===")
    try:
        df = pd.read_excel(EXCEL_MAIN)
        if "Unnamed: 0" in str(df.columns[0]): df = pd.read_excel(EXCEL_MAIN, header=2)
        
        df.columns = [str(c).lower().strip().replace('.', '').replace('_', ' ') for c in df.columns]

        # Borrar geo vieja
        cols_borrar = ['departamento', 'provincia', 'distrito', 'ubigeo']
        df.drop(columns=[c for c in cols_borrar if c in df.columns], inplace=True, errors='ignore')

        # Mapeo de columnas
        col_map = {}
        for c in df.columns:
            if "servicio" in c and "id" not in c: col_map[c] = "servicio_texto"
            elif "fecha solicitud" in c: col_map[c] = "fecha_solicitud"
            elif "fecha registro consultor" in c: col_map[c] = "fecha_registro_consultor"
            elif "fecha nacimiento" in c: col_map[c] = "fecha_nacimiento"
            elif "fuat anio" in c: col_map[c] = "anio_fuat"
            elif "bi rads" in c: col_map[c] = "birads_raw"
            elif "estado" in c: col_map[c] = "estado"
            elif "sexo" in c: col_map[c] = "sexo"
            elif "nacionalidad id" in c: col_map[c] = "nac_id"
            elif "etnia id" in c: col_map[c] = "etnia_id"
        
        df.rename(columns=col_map, inplace=True)

        # Lógica Servicio
        if "servicio_texto" in df.columns:
            df['tipo_servicio'] = df["servicio_texto"].apply(lambda x: "MAMOGRAFIA" if "mamo" in str(x).lower() else "RADIOLOGIA")
        else: df['tipo_servicio'] = "DESCONOCIDO"

        # Fechas y Año
        for d in ["fecha_solicitud", "fecha_registro_consultor", "fecha_nacimiento"]:
            if d in df.columns: df[d] = pd.to_datetime(df[d], dayfirst=True, errors='coerce')
            
        df["anio"] = pd.to_numeric(df.get("anio_fuat", 0), errors='coerce').fillna(0).astype(int)
        mask_cero = df["anio"] == 0
        if mask_cero.any() and "fecha_solicitud" in df.columns:
             df.loc[mask_cero, "anio"] = df.loc[mask_cero, "fecha_solicitud"].dt.year.fillna(0).astype(int)

        if "fecha_registro_consultor" in df.columns and "fecha_solicitud" in df.columns:
             df["tiempo_atencion_dias"] = (df["fecha_registro_consultor"] - df["fecha_solicitud"]).dt.total_seconds() / 86400.0

        # === CRUCE GEOGRÁFICO ===
        col_origen = next((c for c in df.columns if "nombre" in c and "establecimiento" in c and "origen" in c), None)
        if col_origen and 'eess' in maestros:
            print("   > Cruzando EESS...")
            df.rename(columns={col_origen: "nombre_eess_origen"}, inplace=True)
            df["key_join"] = normalize_text(df["nombre_eess_origen"])
            
            # Merge inicial (aquí es donde Quillabamba se va a Apurimac erróneamente)
            df = df.merge(maestros['eess'], left_on="key_join", right_on="key_eess", how="left")
            df.rename(columns={"geo_departamento": "departamento", "geo_provincia": "provincia", "geo_distrito": "distrito_nombre"}, inplace=True)
            df["departamento"] = df["departamento"].fillna("DESCONOCIDO")

            # --- 🔥 CORRECCIÓN MANUAL DE GEOGRAFÍA 🔥 ---
            # Buscamos todo lo que diga QUILLABAMBA y lo forzamos a CUSCO
            mask_quilla = df['nombre_eess_origen'].astype(str).str.upper().str.contains("QUILLABAMBA", na=False)
            count_q = mask_quilla.sum()
            if count_q > 0:
                print(f"   ⚠️ CORRIGIENDO: Se movieron {count_q} registros de 'QUILLABAMBA' a CUSCO.")
                df.loc[mask_quilla, 'departamento'] = 'CUSCO'
                df.loc[mask_quilla, 'provincia'] = 'LA CONVENCION' # Asignamos también su provincia correcta
            
            # 🔥 2. FIX TUPAC AMARU -> ANCASH (NUEVO)
                mask_tupac = df['nombre_eess_origen'].astype(str).str.upper().str.contains("TUPAC AMARU", na=False)
                if mask_tupac.any():
                    print(f"   ⚠️ Corrección Tupac Amaru aplicada (ICA -> CUSCO).")
                    df.loc[mask_tupac, 'departamento'] = 'CUSCO'
                    # Opcional: Si sabes la provincia exacta, puedes ponerla aquí también
            
            # ------------------------------------------------
        
        # === B. IDENTIFICAR Y RENOMBRAR DESTINO (TU CORRECCIÓN) ===
        # Buscamos "nombre" + "establecimiento" + "destino" para evitar IDs
        col_destino = next((c for c in df.columns if "nombre" in c and "establecimiento" in c and "destino" in c), None)
        
        if col_destino:
            print("   > Detectado EESS Destino.")
            df.rename(columns={col_destino: "nombre_eess_destino"}, inplace=True)
        else:
            print("   ⚠️ No se encontró columna destino, se crea vacía.")
            df["nombre_eess_destino"] = "DESCONOCIDO"


        # Cruces Nacio/Etnia
        if "nac_id" in df.columns and 'nacionalidad' in maestros:
            df["nac_join"] = df["nac_id"].fillna(0).astype(str).str.split('.').str[0].str.strip()
            df = df.merge(maestros['nacionalidad'], left_on="nac_join", right_on="cod_nac", how="left")
            df.rename(columns={"pais": "nacionalidad"}, inplace=True)
            df["nacionalidad"] = df["nacionalidad"].fillna("DESCONOCIDO")

        if "etnia_id" in df.columns and 'etnia' in maestros:
            df["etn_join"] = df["etnia_id"].fillna(0).astype(str).str.split('.').str[0].str.strip()
            df = df.merge(maestros['etnia'], left_on="etn_join", right_on="cod_etnia", how="left")
            df.rename(columns={"raza": "etnia"}, inplace=True)
            df["etnia"] = df["etnia"].fillna("DESCONOCIDO")

        # Indicadores finales
        if "estado" in df.columns:
            df["es_atendido"] = df["estado"].astype(str).str.upper().apply(lambda x: 1 if "ATENDIDO" in x else 0)
            df["es_anulado"] = df["estado"].astype(str).str.upper().apply(lambda x: 1 if "ANULADO" in x else 0)

        if "birads_raw" in df.columns:
             df["es_anormal"] = df.apply(lambda r: 1 if (r.get("tipo_servicio")=="MAMOGRAFIA" and str(r.get("birads_raw")).replace('.0','') in ['3','4','5']) else 0, axis=1)

        # Edad
        hoy = pd.Timestamp.today()
        if "fecha_nacimiento" in df.columns:
            df["edad"] = ((hoy - df["fecha_nacimiento"]).dt.days / 365.25).fillna(0).astype(int)
            def calc_grupo(edad):
                if edad <= 11: return "Niño (0-11)"
                elif edad <= 17: return "Adolescente (12-17)"
                elif edad <= 29: return "Joven (18-29)"
                elif edad <= 59: return "Adulto (30-59)"
                else: return "Adulto Mayor (60+)"
            df["grupo_etario"] = df["edad"].apply(calc_grupo)

        return df

    except Exception as e: print(f"❌ Error procesando: {e}"); return pd.DataFrame()

# 3. SUBIDA
def main():
    print("=== 🚀 INICIANDO ETL v11.0 (FIX CUSCO) ===")
    if not DB_URL: print("❌ Falta DATABASE_URL"); return
    try: engine = create_engine(DB_URL)
    except: print("❌ Error conexión"); return

    maestros = cargar_maestros()
    df_final = procesar_principal(maestros)
    
    if df_final.empty: return

    # Selección final
    cols_keep = [
        'anio', 'fecha_solicitud', 'tipo_servicio', 'estado', 
        'es_atendido', 'es_anulado', 'es_anormal', 'birads_raw',
        'tiempo_atencion_dias', 'edad', 'sexo', 'grupo_etario',
        'departamento', 'provincia', 'distrito_nombre', 'nombre_eess_origen','nombre_eess_destino',
        'nacionalidad', 'etnia'
    ]
    final_cols = [c for c in cols_keep if c in df_final.columns]
    df_subida = df_final[final_cols].copy()

    print(f"\n=== 3. SUBIENDO A NEON ({len(df_subida)} filas) ===")
    with engine.connect() as conn:
        try: conn.execute(text(f"DROP VIEW IF EXISTS {TABLE_DESTINO} CASCADE")); conn.commit()
        except: pass
        try: conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_DESTINO} CASCADE")); conn.commit()
        except: pass

    try:
        df_subida.to_sql(TABLE_DESTINO, engine, if_exists='replace', index=False)
        print("✅ ¡CARGA EXITOSA!")
    except Exception as e: print(f"❌ Error DB: {e}")

if __name__ == "__main__":
    main()