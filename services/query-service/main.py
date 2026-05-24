import os
import json
import decimal
import datetime
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

ANTHROPIC_MODEL = "claude-opus-4-5"
MAX_ROWS_FOR_SUMMARY = 20

# ── DB Schema ─────────────────────────────────────────────────────────────────
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

SQL_SYSTEM_PROMPT = f"""You are a SQL expert for a supply chain database (PostgreSQL).
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

ANSWER_SYSTEM_PROMPT = """You are a helpful supply chain analytics assistant.

Your job is to transform database query results into a clear, user-friendly chatbot answer.

Rules:
- Do not mention SQL.
- Do not reveal the SQL query.
- Do not expose raw database output directly.
- Do not invent data.
- Do not make assumptions beyond the provided result.
- If the result is limited or partial, say so clearly.
- Use simple business language understandable by non-technical users.
- The answer must include:
  1. A short direct answer.
  2. A well-displayed list or table-like summary of the data requested by the user.
  3. A short insight section explaining what the data shows.
- Keep the answer concise but complete.
- If dates are present, keep them readable.
- If numeric values are present, preserve their meaning.
"""

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"service": "query-service", "status": "ok"}


class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(req: QueryRequest):
    question = req.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    sql = generate_sql(question)
    validate_sql(sql)

    results = execute_sql(sql)

    if len(results) == 0:
        return {
            "answer": "I could not find matching records for this question.",
            "count": 0,
            "data": [],
        }

    answer = generate_user_answer(
        question=question,
        sql=sql,
        results=results,
    )

    return {
        "answer": answer,
        "count": len(results),
        "data": format_display_data(results[:MAX_ROWS_FOR_SUMMARY]),
    }


# ── Anthropic / SQL helpers ───────────────────────────────────────────────────

def generate_sql(question: str) -> str:
    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SQL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )

        return message.content[0].text.strip()

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error while generating SQL: {e}")


def generate_user_answer(question: str, sql: str, results: list[dict]) -> str:
    rows_for_summary = results[:MAX_ROWS_FOR_SUMMARY]

    prompt = f"""
User question:
{question}

Generated SQL query, for internal context only. Do NOT reveal it to the user:
{sql}

Total number of rows returned by the database:
{len(results)}

Rows included for your summary:
{json.dumps(make_json_safe(rows_for_summary), ensure_ascii=False, indent=2)}

Important:
- Only the first {MAX_ROWS_FOR_SUMMARY} rows are included if the result is larger.
- The user should receive a readable business answer, not SQL and not raw JSON.
- Include the requested data in a clean list/table-like format.
- Then provide a short insight based only on the displayed data.
"""

    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1600,
            temperature=0,
            system=ANSWER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text.strip()

    except Exception:
        # Deterministic fallback: no second Claude call result, but still no SQL exposure.
        return build_fallback_answer(question, results)


def validate_sql(sql: str) -> None:
    sql_clean = sql.strip().rstrip(";")
    sql_upper = sql_clean.upper()

    forbidden_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "EXECUTE",
    ]

    if not sql_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed.",
        )

    if any(keyword in sql_upper for keyword in forbidden_keywords):
        raise HTTPException(
            status_code=400,
            detail="Unsafe SQL keyword detected.",
        )

    if ";" in sql_clean:
        raise HTTPException(
            status_code=400,
            detail="Multiple SQL statements are not allowed.",
        )


def execute_sql(sql: str) -> list[dict]:
    try:
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL execution error: {e}",
        )


# ── Formatting helpers ────────────────────────────────────────────────────────

def make_json_safe(value):
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {key: make_json_safe(val) for key, val in value.items()}

    if isinstance(value, decimal.Decimal):
        return float(value)

    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()

    return value


def format_display_data(rows: list[dict]) -> list[dict]:
    return [make_json_safe(row) for row in rows]


def build_fallback_answer(question: str, results: list[dict]) -> str:
    preview_rows = format_display_data(results[:5])

    lines = [
        f"I found {len(results)} result{'s' if len(results) != 1 else ''} for your question.",
        "",
        "Here are the most relevant results:",
    ]

    for index, row in enumerate(preview_rows, start=1):
        readable_row = " · ".join(
            f"{humanize_key(key)}: {format_value(value)}"
            for key, value in row.items()
        )
        lines.append(f"{index}. {readable_row}")

    if len(results) > len(preview_rows):
        lines.append("")
        lines.append(f"Only the first {len(preview_rows)} results are shown here.")

    lines.append("")
    lines.append("Insight:")
    lines.append("These results match your request, but I could not generate a deeper natural-language analysis at this time.")

    return "\n".join(lines)


def humanize_key(key: str) -> str:
    return key.replace("_", " ").capitalize()


def format_value(value) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)