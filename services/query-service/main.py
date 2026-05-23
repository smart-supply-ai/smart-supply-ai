import os
import json
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

app = FastAPI(title="Query Service", version="0.1.0")

# ── Config ────────────────────────────────────────────────────────────────────
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "smart_supply")
DB_HOST = "db"
CONN_STR = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Schéma de la DB envoyé à Claude ──────────────────────────────────────────
DB_SCHEMA = """
Table: supply_chain_data
Columns:
- type TEXT (payment type: DEBIT, TRANSFER, CASH, PAYMENT)
- days_for_shipping_real INTEGER (actual shipping days)
- days_for_shipping_scheduled INTEGER (scheduled shipping days)
- benefit_per_order NUMERIC (profit per order)
- sales_per_customer NUMERIC (sales per customer)
- delivery_status TEXT (Advance shipping, Late delivery, Shipping on time, Shipping canceled)
- late_delivery_risk INTEGER (0 = on time, 1 = late)
- category_id INTEGER
- category_name TEXT (product category)
- customer_city TEXT
- customer_country TEXT
- customer_segment TEXT (Consumer, Corporate, Home Office)
- department_name TEXT
- latitude NUMERIC
- longitude NUMERIC
- market TEXT (Europe, Pacific Asia, USCA, LATAM, Africa)
- order_city TEXT
- order_country TEXT
- order_date TIMESTAMP
- order_id INTEGER
- order_item_discount NUMERIC
- order_item_discount_rate NUMERIC
- order_item_quantity INTEGER
- sales NUMERIC
- order_item_total NUMERIC
- order_profit_per_order NUMERIC
- order_region TEXT
- order_status TEXT (COMPLETE, PENDING, CLOSED, CANCELED, PENDING_PAYMENT, PROCESSING, SUSPECTED_FRAUD, ON_HOLD, PAYMENT_REVIEW)
- product_name TEXT
- product_price NUMERIC
- shipping_date TIMESTAMP
- shipping_mode TEXT (Standard Class, First Class, Second Class, Same Day)

Table: alerts
Columns:
- id SERIAL PRIMARY KEY
- created_at TIMESTAMP
- order_index INTEGER
- risk_level TEXT (HIGH, MEDIUM, LOW)
- risk_score INTEGER (0-100)
- probability NUMERIC
- late_delivery_risk INTEGER
- product_name TEXT
- order_city TEXT
- order_country TEXT
- shipping_date TIMESTAMP
"""

SYSTEM_PROMPT = f"""You are a SQL expert for a supply chain database (PostgreSQL).
Your job is to convert natural language questions into valid PostgreSQL SQL queries.

Here is the database schema:
{DB_SCHEMA}

Rules:
- Only generate SELECT queries, never INSERT, UPDATE, DELETE, DROP, or any other modifying statement
- Always add LIMIT 100 if no limit is specified
- Return ONLY the SQL query, no explanation, no markdown, no backticks
- Use proper PostgreSQL syntax
- Column and table names are case-sensitive, use lowercase
- For aggregations, always include relevant GROUP BY clauses
"""

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"service": "query-service", "status": "ok"}


class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(req: QueryRequest):
    """
    Converts a natural language question to SQL and executes it.
    
    Example:
        { "question": "What are the top 5 markets with the most late deliveries?" }
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # 1. Claude génère le SQL
    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": req.question}]
        )
        sql = message.content[0].text.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    # 2. Sécurité — on vérifie que c'est bien un SELECT
    sql_upper = sql.upper().strip()
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
    if not sql_upper.startswith("SELECT") or any(kw in sql_upper for kw in forbidden):
        raise HTTPException(
            status_code=400,
            detail=f"Only SELECT queries are allowed. Generated: {sql}"
        )

    # 3. Exécution sur PostgreSQL
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL execution error: {e} | SQL: {sql}"
        )

    return {
        "question": req.question,
        "sql":      sql,
        "count":    len(results),
        "data":     results,
    }