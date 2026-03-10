import os
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Alert Service", version="0.1.0")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8000")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")

# ── Utilities ──

def wait_for_dependency(url: str, timeout_s: int = 60) -> None:
    """Blocks startup until the dependency's /health returns 200."""
    deadline = time.time() + timeout_s
    last_err: Optional[str] = None
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{url}/health")
                if r.status_code == 200:
                    return
                last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(1)
    raise RuntimeError(f"Dependency not ready: {url} (last error: {last_err})")

# Fields the ML service /predict endpoint requires (mirrors PredictRequest)
ML_PREDICT_FIELDS = [
    "days_for_shipping_scheduled",
    "shipping_mode",
    "order_status",
    "customer_segment",
    "market",
    "order_region",
    "department_name",
    "order_item_quantity",
    "sales",
    "benefit_per_order",
    "category_name",
]

def fetch_orders(client: httpx.Client, limit: int = 50) -> list[dict]:
    """
    Fetches a random sample of orders from data-service GET /data/sample.
    """
    r = client.get(f"{DATA_SERVICE_URL}/data/sample", params={"limit": limit})
    r.raise_for_status()
    return r.json()["data"]

def build_batch_payload(orders: list[dict]) -> dict:
    """
    Builds the { "orders": [...] } body for ml-service POST /predict.
    Extracts only the 11 fields OrderFeatures expects from each raw order dict.
    Raises KeyError if a required field is missing from an order.
    """
    return {
        "orders": [
            {field: order[field] for field in ML_PREDICT_FIELDS}
            for order in orders
        ]
    }

def risk_level_to_score(risk_level: str) -> int:
    """
    Converts ml-service risk_level string to a 0-100 numeric score for the UI.
    Mirrors the thresholds used in ml-service main.py:
        probability > 0.7 → HIGH, > 0.4 → MEDIUM, else → LOW
    """
    return {"HIGH": 75, "MEDIUM": 50, "LOW": 25}.get(risk_level.upper(), 25)


# ── Startup ──

@app.on_event("startup")
def on_startup():
    wait_for_dependency(DATA_SERVICE_URL, timeout_s=90)
    wait_for_dependency(ML_SERVICE_URL,   timeout_s=90)


# ── Endpoints ──

@app.get("/health")
def health():
    return {"service": "alert-service", "status": "ok"}


@app.get("/ready")
def ready():
    return {
        "service": "alert-service",
        "ready": True,
        "data_service": DATA_SERVICE_URL,
        "ml_service":   ML_SERVICE_URL,
    }


@app.post("/alerts/run")
def run_alerts():
    """
    Batch prediction pipeline:
      1. GET  /data/sample
      2. POST /predict
      3. Filter results where late_delivery_risk == 1 and return as alerts

    Response shape:
    {
      "service":          "alert-service",
      "orders_analyzed":  50,
      "alerts_found":     12,
      "alerts": [
        {
          "order_index":        4,     # position in the original fetched list
          "risk_level":         "HIGH",
          "risk_score":         75,    # numeric score for the UI progress bar
          "probability":        0.83,
          "late_delivery_risk": 1
        },
        ...
      ]
    }
    """
    with httpx.Client(timeout=60.0) as client:

        # ── Step 1: Fetch orders ──
        SAMPLE_SIZE = 50
        try:
            orders = fetch_orders(client, limit=SAMPLE_SIZE)
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"data-service error {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"data-service unreachable: {e}")

        if not orders:
            raise HTTPException(status_code=404, detail="No orders returned by data-service")

        # ── Step 2: Single batch prediction call ──
        try:
            payload = build_batch_payload(orders)
        except KeyError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Order is missing required field for ML model: {e}",
            )

        try:
            r = client.post(f"{ML_SERVICE_URL}/predict", json=payload)
            r.raise_for_status()
            predictions = r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"ml-service error {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ml-service unreachable: {e}")

        # ── Step 3: Filter to at-risk orders only ──
        alerts = [
            {
                "order_index":        pred["order_index"],
                "risk_level":         pred["risk_level"],
                "risk_score":         risk_level_to_score(pred["risk_level"]),
                "probability":        pred["probability"],
                "late_delivery_risk": pred["late_delivery_risk"],
            }
            for pred in predictions
            if pred["late_delivery_risk"] == 1
        ]

    return {
        "service":         "alert-service",
        "orders_analyzed": len(orders),
        "alerts_found":    len(alerts),
        "alerts":          alerts,
    }
