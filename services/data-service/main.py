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
def get_data(
    market: str = Query(default=None, description="Filtrer par marché"),
    order_status: str = Query(default=None, description="Filtrer par statut"),
    late_delivery_risk: int = Query(default=None, description="0 ou 1"),
    limit: int = Query(default=10, ge=1, le=100, description="Nombre de lignes"),
):
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                filters = []
                params = []

                if market:
                    filters.append("market = %s")
                    params.append(market)
                if order_status:
                    filters.append("order_status = %s")
                    params.append(order_status)
                if late_delivery_risk is not None:
                    filters.append("late_delivery_risk = %s")
                    params.append(late_delivery_risk)

                where = f"WHERE {' AND '.join(filters)}" if filters else ""
                params.append(limit)

                cur.execute(f"SELECT * FROM supply_chain_data {where} LIMIT %s", params)
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

@app.get("/data/segments")
def get_segment_data():
    """Retourne les features nécessaires pour la segmentation clients."""
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        customer_segment,
                        market,
                        late_delivery_risk,
                        days_for_shipping_scheduled,
                        sales,
                        benefit_per_order,
                        order_item_quantity,
                        order_item_discount_rate
                    FROM supply_chain_data
                """)
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/stats")
def get_stats():
    """Retourne les statistiques globales pour le dashboard."""
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*)                                    AS total_orders,
                        SUM(late_delivery_risk)                     AS at_risk_orders,
                        AVG(days_for_shipping_real - 
                            days_for_shipping_scheduled)            AS avg_delay_days,
                        AVG(CASE WHEN late_delivery_risk = 0 
                            THEN 1.0 ELSE 0.0 END)                  AS on_time_rate
                    FROM supply_chain_data
                """)
                row = cur.fetchone()
                return {
                    "status":        "success",
                    "total_orders":  int(row[0]),
                    "at_risk_orders": int(row[1]),
                    "avg_delay_days": round(float(row[2]), 1) if row[2] else 0.0,
                    "on_time_rate":   round(float(row[3]) * 100, 1) if row[3] else 0.0,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/stats")
def get_data_stats():
    return get_stats()
    
@app.get("/stats/by-market")
def get_stats_by_market():
    """Stats de retard groupées par marché."""
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        market,
                        COUNT(*)                                        AS total_orders,
                        SUM(late_delivery_risk)                         AS at_risk_orders,
                        ROUND(AVG(late_delivery_risk::numeric) * 100, 1) AS late_delivery_rate
                    FROM supply_chain_data
                    GROUP BY market
                    ORDER BY late_delivery_rate DESC
                """)
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/by-shipping-mode")
def get_stats_by_shipping_mode():
    """Stats de retard groupées par mode d'expédition."""
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        shipping_mode,
                        COUNT(*)                                        AS total_orders,
                        SUM(late_delivery_risk)                         AS at_risk_orders,
                        ROUND(AVG(late_delivery_risk::numeric) * 100, 1) AS late_delivery_rate,
                        ROUND(AVG(days_for_shipping_real::numeric), 1)   AS avg_real_days,
                        ROUND(AVG(days_for_shipping_scheduled::numeric), 1) AS avg_scheduled_days
                    FROM supply_chain_data
                    GROUP BY shipping_mode
                    ORDER BY late_delivery_rate DESC
                """)
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))