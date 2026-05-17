from fastapi import FastAPI, HTTPException, Query
import psycopg
import os

app = FastAPI()

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "smart_supply")
DB_HOST = "db"

CONN_STR = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

# Protects against accidental large fetches during testing.
SAMPLE_LIMIT_CAP = 500

@app.get("/")
def read_root():
    return {
        "message": "Bienvenue sur l'API Smart Supply !",
        "status": "opérationnel",
        "endpoints": {
            "data":        "/data",
            "data_all":    "/data/all",
            "data_sample": "/data/sample?limit=50",
            "health":      "/health",
            "docs":        "/docs",
        },
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
    
@app.get("/data/sample")
def get_sample_data(
    limit: int = Query(
        default=50,
        ge=1,
        le=SAMPLE_LIMIT_CAP,
        description=f"Number of rows to return (1–{SAMPLE_LIMIT_CAP})",
    )
):
    """
    Returns a random sample of orders for testing purposes.

    Query parameter:
        limit (int): number of rows to return, between 1 and 500. Default: 50.
    """
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT late_delivery_risk, days_for_shipping_scheduled,
                           shipping_mode, order_status, customer_segment,
                           market, order_region, department_name,
                           order_item_quantity, sales, benefit_per_order,
                           category_name,
                           product_name, order_city, order_country, shipping_date
                    FROM supply_chain_data TABLESAMPLE BERNOULLI(10)
                    LIMIT %s
                """, (limit,))

                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                if not rows:
                    cur.execute("""
                        SELECT late_delivery_risk, days_for_shipping_scheduled,
                               shipping_mode, order_status, customer_segment,
                               market, order_region, department_name,
                               order_item_quantity, sales, benefit_per_order,
                               category_name,
                               product_name, order_city, order_country, shipping_date
                        FROM supply_chain_data
                        ORDER BY RANDOM()
                        LIMIT %s
                    """, (limit,))
                    rows = cur.fetchall()

                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail="No orders found in the database."
                    )

                results = [dict(zip(columns, row)) for row in rows]
                return {"status": "success", "count": len(results), "data": results}

    except HTTPException:
        raise
    except psycopg.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {e}"
        )
    except psycopg.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {e}"
        )
