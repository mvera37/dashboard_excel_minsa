import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Conectar
engine = create_engine(os.getenv("DATABASE_URL"))

try:
    # Reemplaza 'mamografias_teleatiendo' por el nombre real de tu tabla si es diferente
    query = "SELECT * FROM mamografias_teleatiendo LIMIT 10;"
    df = pd.read_sql(query, engine)
    
    print("--- PRIMERAS 10 FILAS DE LA TABLA ---")
    print(df.to_string()) # to_string() imprime todo bonito
except Exception as e:
    print("Error:", e)