import os
import psycopg
from fastapi import FastAPI

app = FastAPI()

# Utilise DATABASE_URL injecté par Docker
CONN_STR = os.getenv("DATABASE_URL", 
    "postgresql+psycopg://postgres:postgres@db:5432/smart_supply")

@app.get("/")
def read_root():
    return {
        "message": "Bienvenue sur l'API Smart Supply !",
        "status": "opérationnel",
        "endpoints": {
            "data": "/data",
            "health": "/health", 
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "data-service"}

@app.get("/data")
def get_data():
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM supply_chain_data LIMIT 10")
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}