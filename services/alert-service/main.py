import os
import time
from typing import Optional

import httpx
from fastapi import FastAPI

app = FastAPI(title="Alert Service", version="0.1.0")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8000")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")


def wait_for_dependency(url: str, timeout_s: int = 60) -> None:

    """
    Simple blocking wait so the service doesn't start "ready" before dependencies are up.
    """

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


@app.on_event("startup")
def on_startup():
    wait_for_dependency(DATA_SERVICE_URL, timeout_s=90)
    wait_for_dependency(ML_SERVICE_URL, timeout_s=90)


@app.get("/health")
def health():
    return {"service": "alert-service", "status": "ok"}


@app.get("/ready")
def ready():
    # Check DB connectivity, etc.
    return {
        "service": "alert-service",
        "ready": True,
        "data_service": DATA_SERVICE_URL,
        "ml_service": ML_SERVICE_URL,
    }


@app.post("/alerts/run")
def run_alerts():

    """
    Dummy alert run: calls ml-service /predict once and returns a fake alert.
    This proves service-to-service HTTP calls work in Docker Compose.
    """
    
    with httpx.Client(timeout=5.0) as client:
        pred = client.post(f"{ML_SERVICE_URL}/predict", json={"entity_id": "ORDER_123", "context": {}})
        pred.raise_for_status()
        pred_json = pred.json()

    return {
        "service": "alert-service",
        "message": "Dummy alert run completed",
        "created_alerts": [
            {
                "entity_id": pred_json.get("entity_id", "ORDER_123"),
                "risk": "LOW",
                "reason": f"Dummy prediction={pred_json.get('prediction')}",
            }
        ],
    }
