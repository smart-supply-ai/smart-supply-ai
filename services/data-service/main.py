from fastapi import FastAPI
import psycopg
import os

app = FastAPI()

# Récupération des variables avec des valeurs de secours
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "smart_supply")
DB_HOST = "db"

# Chaîne de connexion robuste
CONN_STR = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

@app.get("/")
def read_root():
    return {
        "message": "Bienvenue sur l'API Smart Supply !",
        "status": "C'est opérationnel",
        "endpoints": {
            "data": "/data (pour voir les 10 premières lignes)",
            "health": "/health (check pour Docker)",
            "docs": "/docs (interface interactive)"
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

@app.get("/data/all")
def get_all_data():
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT late_delivery_risk, days_for_shipping_scheduled,
                           shipping_mode, order_status, customer_segment,
                           market, order_region, department_name,
                           order_item_quantity, sales, benefit_per_order,
                           category_name
                    FROM supply_chain_data
                """)
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}