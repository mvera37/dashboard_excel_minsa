# Ver tipos de datos en la BD
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    # Esta consulta le pregunta a Postgres: "¿De qué tipo son mis columnas?"
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'mamografias_teleatiendo';e
    """)
    result = pd.read_sql(query, conn)
    print(result)