import os
import time
from typing import Any, Dict, Optional, List

import httpx
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

app = FastAPI(title="ML Service", version="0.2.0")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8000")
MODEL_PATH = "/app/models/model.joblib"
ENCODERS_PATH = "/app/models/encoders.joblib"

FEATURES = [
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
TARGET = "late_delivery_risk"
CATEGORICAL = ["shipping_mode", "order_status", "customer_segment", "market", "order_region", "department_name", "category_name"]

model: Optional[RandomForestClassifier] = None
encoders: Dict[str, LabelEncoder] = {}


# ── Utilitaires ──────────────────────────────────────────────────────────────

def wait_for_dependency(url: str, timeout_s: int = 60) -> None:
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


def fetch_all_data() -> pd.DataFrame:
    """Récupère toutes les données depuis data-service."""
    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{DATA_SERVICE_URL}/data/all")
        r.raise_for_status()
    return pd.DataFrame(r.json()["data"])


def preprocess(df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
    """
    Encode les colonnes catégorielles.
    fit=True  → on apprend les encodeurs (à l'entraînement)
    fit=False → on réutilise les encodeurs existants (à la prédiction)
    """
    df = df.copy()
    for col in CATEGORICAL:
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            le = encoders[col]
            # Gère les valeurs inconnues avec la classe la plus fréquente
            df[col] = df[col].astype(str).map(
                lambda x, le=le: le.transform([x])[0]
                if x in le.classes_
                else 0
            )
    return df


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    global model, encoders
    os.makedirs("/app/models", exist_ok=True)
    wait_for_dependency(DATA_SERVICE_URL, timeout_s=90)
    # Charge le modèle s'il existe déjà
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH):
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODERS_PATH)
        print("✅ Modèle chargé depuis le disque")
    else:
        print("ℹ️  Aucun modèle trouvé — entraînement automatique en cours...")
        try:
            result = train()
            print(f"✅ Modèle entraîné automatiquement — accuracy: {result['accuracy']}")
        except Exception as e:
            # Non-fatal: the service starts anyway, /predict will return 503
            # until the model is trained manually via POST /train.
            print(f"⚠️  Entraînement automatique échoué: {e}")


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"service": "ml-service", "status": "ok"}


@app.get("/ready")
def ready():
    return {
        "service": "ml-service",
        "model_loaded": model is not None,
        "data_service": DATA_SERVICE_URL,
    }


@app.post("/train")
def train():
    """Entraîne le modèle sur toutes les données disponibles."""
    global model, encoders

    # 1. Récupération des données
    try:
        df = fetch_all_data()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur data-service : {e}")

    # 2. Nettoyage
    df = df[FEATURES + [TARGET]].dropna()
    if len(df) < 100:
        raise HTTPException(status_code=400, detail="Pas assez de données pour entraîner")

    # 3. Preprocessing
    df = preprocess(df, fit=True)
    X = df[FEATURES]
    y = df[TARGET]

    # 4. Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 5. Entraînement
    clf = RandomForestClassifier(
        n_estimators=200,        # plus d'arbres = plus stable
        max_depth=15,            # évite l'overfitting
        min_samples_split=10,    # noeuds plus robustes
        min_samples_leaf=4,      # feuilles plus robustes
        class_weight="balanced", # gère le déséquilibre des classes
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # 6. Évaluation
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)

    # 7. Sauvegarde
    model = clf
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODERS_PATH)

    return {
        "status": "success",
        "rows_trained": len(X_train),
        "rows_tested": len(X_test),
        "accuracy": round(report["accuracy"], 4),
        "precision": round(report["1"]["precision"], 4),
        "recall": round(report["1"]["recall"], 4),
        "f1_score": round(report["1"]["f1-score"], 4),
    }

def risk_label(probability: float) -> str:
    """Mirrors the thresholds used in the train/predict logic."""
    if probability > 0.7:
        return "HIGH"
    if probability > 0.4:
        return "MEDIUM"
    return "LOW"

# ── Batch predict ──────────────────────────────────────────────────────────────

class OrderFeatures(BaseModel):
    """Feature set for a single order."""
    days_for_shipping_scheduled: int   = Field(..., examples=[4])
    shipping_mode:               str   = Field(..., examples=["Standard Class"])
    order_status:                str   = Field(..., examples=["PENDING"])
    customer_segment:            str   = Field(..., examples=["Consumer"])
    market:                      str   = Field(..., examples=["Europe"])
    order_region:                str   = Field(..., examples=["Western Europe"])
    department_name:             str   = Field(..., examples=["Fitness"])
    order_item_quantity:         int   = Field(..., examples=[2])
    sales:                       float = Field(..., examples=[199.99])
    benefit_per_order:           float = Field(..., examples=[35.0])
    category_name:               str   = Field(..., examples=["Cleats"])


class BatchPredictRequest(BaseModel):
    """
    Accepts one or more orders in a single request.
    """
    orders: List[OrderFeatures] = Field(..., min_length=1)


class OrderPrediction(BaseModel):
    """Prediction result for one order, at the same index as the input list."""
    order_index:        int
    late_delivery_risk: int    # 1 = at risk, 0 = on time
    probability:        float  # raw model probability
    risk_level:         str    # "HIGH" | "MEDIUM" | "LOW"


@app.post("/predict", response_model=List[OrderPrediction])
def predict(req: BatchPredictRequest):
    """
    Batch prediction endpoint. Accepts 1–N orders and returns one prediction
    per order at the matching index.

    Request body:
        { "orders": [ { ...11 fields... }, ... ] }

    Response body:
        [ { "order_index": 0, "late_delivery_risk": 1, "probability": 0.83, "risk_level": "HIGH" }, ... ]
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not train - launch model first.",
        )

    df = pd.DataFrame([order.model_dump() for order in req.orders])
    df = preprocess(df, fit=False)

    predictions  = model.predict(df[FEATURES])
    probabilities = model.predict_proba(df[FEATURES])[:, 1]

    return [
        OrderPrediction(
            order_index        = i,
            late_delivery_risk = int(predictions[i]),
            probability        = round(float(probabilities[i]), 4),
            risk_level         = risk_label(float(probabilities[i])),
        )
        for i in range(len(req.orders))
    ]