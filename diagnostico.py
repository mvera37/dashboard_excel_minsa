import pandas as pd
import os

# --- CONFIGURACIÓN ---
EXCEL_MAIN = r"D:\MINSA\Proyecto Mónica\Analisis - copia\Reporte_SIA_TELEATIENDO_13012026.xlsx"
EXCEL_EESS = "EESS.xlsX"  # Asegúrate de la extensión (.xls o .xlsx)

def normalize_text(series):
    """Limpia textos para comparar (Mayúsculas y sin espacios extra)"""
    return series.astype(str).str.upper().str.strip()

def diagnosticar_radiologia():
    print("🕵️‍♂️ DIAGNÓSTICO ESPECÍFICO: 2026 + RADIOLOGÍA\n")

    # 1. CARGAR MAESTRO EESS
    print("--- 1. CARGANDO MAESTRO EESS ---")
    if os.path.exists(EXCEL_EESS):
        try:
            df_eess = pd.read_excel(EXCEL_EESS, usecols=["Nombre del establecimiento"])
            claves_maestro = set(normalize_text(df_eess["Nombre del establecimiento"]).unique())
            print(f"✅ Maestro cargado: {len(claves_maestro)} establecimientos únicos.")
        except Exception as e:
            print(f"❌ Error leyendo EESS: {e}")
            return
    else:
        print("❌ NO SE ENCONTRÓ EL ARCHIVO EESS.")
        return

    # 2. CARGAR Y FILTRAR REPORTE
    print("\n--- 2. PROCESANDO REPORTE (FILTRANDO...) ---")
    try:
        # Cargar reporte
        df = pd.read_excel(EXCEL_MAIN)
        if "Unnamed: 0" in str(df.columns[0]): df = pd.read_excel(EXCEL_MAIN, header=2)
        
        # Normalizar nombres de columnas
        df.columns = [str(c).lower().strip().replace('.', '').replace('_', ' ') for c in df.columns]

        # --- A) FILTRO DE SERVICIO (RADIOLOGÍA) ---
        col_serv = next((c for c in df.columns if "servicio" in c and "id" not in c), None)
        if col_serv:
            # Buscamos términos comunes de radiología
            # A veces sale como "TELERADIOLOGIA", "RADIOLOGIA", "RAYOS X", etc.
            mask_radio = df[col_serv].astype(str).str.upper().str.contains("RADIO|RAYOS|RX", regex=True, na=False)
            df = df[mask_radio]
            print(f"   -> Filtrado por Servicio (RADIOLOGÍA): Quedan {len(df)} filas.")
        else:
            print("   ⚠️ No encontré columna de Servicio. Se analizará todo.")

        # --- B) FILTRO DE AÑO (2026) ---
        col_fecha = next((c for c in df.columns if "fecha solicitud" in c), None)
        col_anio = next((c for c in df.columns if "fuat anio" in c), None)

        if col_anio:
            df = df[df[col_anio].astype(str).str.contains("2026", na=False)]
            print(f"   -> Filtrado por Año 2026 (Columna Año): Quedan {len(df)} filas.")
        elif col_fecha:
            df[col_fecha] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
            df = df[df[col_fecha].dt.year == 2026]
            print(f"   -> Filtrado por Año 2026 (Desde Fecha): Quedan {len(df)} filas.")
        else:
            print("   ⚠️ No encontré columna de Fecha/Año.")

    except Exception as e:
        print(f"❌ Error leyendo Reporte: {e}")
        return

    # 3. COMPARACIÓN (EL CRUCE)
    print("\n--- 3. BUSCANDO 'DESCONOCIDOS' ---")
    
    if df.empty:
        print("⚠️ No hay datos para analizar (¿Quizás no hay Radiología en 2026?).")
        return

    col_origen = next((c for c in df.columns if "nombre" in c and "establecimiento" in c and "origen" in c), None)
    
    if not col_origen:
        print("❌ No encontré la columna 'Nombre Establecimiento Origen'.")
        return

    # Extraer nombres únicos del reporte filtrado
    df["key_busqueda"] = normalize_text(df[col_origen])
    claves_reporte_filtrado = set(df["key_busqueda"].unique())
    
    # Restar conjuntos
    no_cruzados = claves_reporte_filtrado - claves_maestro
    total_fallos = len(no_cruzados)

    print(f"📊 Establecimientos únicos de Radiología a analizar: {len(claves_reporte_filtrado)}")
    
    if total_fallos == 0:
        print("\n🎉 ¡EXCELENTE! Todo Radiología 2026 cruza perfecto.")
    else:
        print(f"❌ SE ENCONTRARON {total_fallos} ESTABLECIMIENTOS SIN CRUCE.")
        print("\n⚠️ LISTA DE ERRORES (Revisar en EESS.xls):")
        print("-------------------------------------------------------------------")
        for i, nombre in enumerate(sorted(list(no_cruzados))):
            print(f"{i+1}. {nombre}")
        print("-------------------------------------------------------------------")

        # Guardar Excel
        try:
            pd.DataFrame(list(no_cruzados), columns=["NOMBRE_EN_REPORTE"]).to_excel("ERRORES_RADIO_2026.xlsx", index=False)
            print(f"\n📄 Archivo generado: 'ERRORES_RADIO_2026.xlsx'")
        except: pass

if __name__ == "__main__":
    diagnosticar_radiologia()