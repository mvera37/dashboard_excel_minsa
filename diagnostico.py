import pandas as pd

# CONFIGURA EL NOMBRE DE TU ARCHIVO
EXCEL_MAIN = r"D:\MINSA\Proyecto Mónica\Analisis - copia\Reporte_SIA_TELEATIENDO_13012026.xlsx"

print(f"🕵️‍♂️ AUDITANDO SERVICIOS EN: {EXCEL_MAIN}")

try:
    df = pd.read_excel(EXCEL_MAIN)
    if "Unnamed: 0" in str(df.columns[0]): df = pd.read_excel(EXCEL_MAIN, header=2)
    
    # Normalizar columnas
    df.columns = [str(c).lower().strip().replace('.', '') for c in df.columns]
    
    # Buscar columna servicio
    col_servicio = next((c for c in df.columns if "servicio" in c and "id" not in c), None)
    
    if col_servicio:
        # Filtrar como hace el ETL
        mask = df[col_servicio].astype(str).str.lower().str.contains("mamo|radio", na=False)
        df_filtrado = df[mask].copy()
        
        # Clasificar
        df_filtrado['tipo'] = df_filtrado[col_servicio].apply(lambda x: 
            "MAMOGRAFIA" if "mamo" in str(x).lower() else "RADIOLOGIA")
        
        print("\n--- 🔎 DETALLE DE NOMBRES ENCONTRADOS ---")
        print(df_filtrado.groupby(['tipo', col_servicio]).size().to_string())
        
        print("\n-------------------------------------------")
        print(f"TOTAL REGISTROS DETECTADOS: {len(df_filtrado)}")
    else:
        print("❌ No se encontró columna Servicio")

except Exception as e:
    print(f"Error: {e}")