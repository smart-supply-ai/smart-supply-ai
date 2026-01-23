import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="ML Service", version="0.1.0")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8000")


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


@app.get("/health")
def health():
    return {"service": "ml-service", "status": "ok"}


@app.get("/ready")
def ready():
    # Check if model loaded, etc.
    return {"service": "ml-service", "ready": True, "data_service": DATA_SERVICE_URL}


class PredictRequest(BaseModel):
    entity_id: str = Field(..., examples=["ORDER_123"])
    context: Dict[str, Any] = Field(default_factory=dict)


@app.post("/predict")
def predict(req: PredictRequest):
    # Dummy prediction
    return {
        "service": "ml-service",
        "entity_id": req.entity_id,
        "prediction": 3.14,
        "model_version": "dummy-0.1.0",
    }
