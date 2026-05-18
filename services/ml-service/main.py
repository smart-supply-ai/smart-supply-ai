import os
import time
from typing import Any, Dict, Optional, List
from collections import defaultdict

import httpx
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging
import json
from datetime import datetime

# ── Logging structuré ─────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level":     record.levelname,
            "service":   "ml-service",
            "message":   record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("ml-service")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="ML Service", version="0.2.0")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:8000")
MODEL_PATH = "/app/models/model.joblib"
ENCODERS_PATH = "/app/models/encoders.joblib"
MODEL_NAME_PATH = "/app/models/model_name.txt"

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

# ── Segmentation ──────────────────────────────────────────────────────────────
SEGMENT_FEATURES = [
    "sales",
    "benefit_per_order",
    "order_item_quantity",
    "order_item_discount_rate",
    "late_delivery_risk",
    "days_for_shipping_scheduled",
]
SEGMENT_CATEGORICAL = ["customer_segment", "market"]

SEGMENT_MODEL_PATH   = "/app/models/segment_model.joblib"
SEGMENT_SCALER_PATH  = "/app/models/segment_scaler.joblib"
SEGMENT_ENCODERS_PATH = "/app/models/segment_encoders.joblib"
SEGMENT_SUMMARY_PATH = "/app/models/segment_summary.joblib"

segment_model   = None
segment_scaler  = None
segment_encoders: Dict[str, LabelEncoder] = {}
segment_summary: Dict = {}

model = None #Can be RandomForest or XGBoost
model_name: str = "none" #To know which model is active

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
    Encode categorical columns.
    fit=True  → learn the encoders (during training)
    fit=False → reuse existing encoders (during inference/prediction)
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
    global model, encoders, model_name
    global segment_model, segment_scaler, segment_encoders, segment_summary

    os.makedirs("/app/models", exist_ok=True)
    wait_for_dependency(DATA_SERVICE_URL, timeout_s=90)

    # Charge le modèle de prédiction
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH):
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODERS_PATH)
        if os.path.exists(MODEL_NAME_PATH):
            with open(MODEL_NAME_PATH) as f:
                model_name = f.read().strip()
        logger.info(f"✅ Prediction model loaded : {model_name}")
    else:
        logger.info("ℹ️  No prediction model — Auto training...")
        try:
            train()
        except Exception as e:
            logger.error(f"⚠️  Training failed: {e}")

    # Charge le modèle de segmentation
    if os.path.exists(SEGMENT_MODEL_PATH):
        segment_model   = joblib.load(SEGMENT_MODEL_PATH)
        segment_scaler  = joblib.load(SEGMENT_SCALER_PATH)
        segment_encoders = joblib.load(SEGMENT_ENCODERS_PATH)
        segment_summary = joblib.load(SEGMENT_SUMMARY_PATH)
        logger.info("✅ Segmentation model loaded")
    else:
        logger.info("ℹ️  No segmentation model — launching POST /segment/train")


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"service": "ml-service", "status": "ok"}


@app.get("/ready")
def ready():
    return {
        "service": "ml-service",
        "model_loaded": model is not None,
        "model_name": model_name,
        "data_service": DATA_SERVICE_URL,
    }


@app.post("/train")
def train():
    global model, encoders, model_name

    # 1. Récupération des données
    try:
        df = fetch_all_data()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"data-service error: {e}")

    # 2. Nettoyage
    df = df[FEATURES + [TARGET]].dropna()
    if len(df) < 100:
        raise HTTPException(status_code=400, detail="Not enough data")

    # 3. Preprocessing
    df = preprocess(df, fit=True)
    X = df[FEATURES]
    y = df[TARGET]

    # 4. Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 5. Entraînement des deux modèles
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
        verbosity=0,
    )

    rf.fit(X_train, y_train)
    xgb.fit(X_train, y_train)

    # 6. Comparaison sur le test set
    rf_report  = classification_report(y_test, rf.predict(X_test),  output_dict=True)
    xgb_report = classification_report(y_test, xgb.predict(X_test), output_dict=True)

    rf_f1  = rf_report["1"]["f1-score"]
    xgb_f1 = xgb_report["1"]["f1-score"]

    # 7. Sélection du meilleur
    if xgb_f1 >= rf_f1:
        best_model      = xgb
        best_report     = xgb_report
        best_name       = "xgboost"
    else:
        best_model      = rf
        best_report     = rf_report
        best_name       = "random_forest"

    # 8. Sauvegarde
    model      = best_model
    model_name = best_name
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODERS_PATH)
    with open(MODEL_NAME_PATH, "w") as f:
        f.write(model_name)
    logger.info(f"Entraînement terminé — winner: {best_name}, f1: {round(max(rf_f1, xgb_f1), 4)}")
    return {
        "status":       "success",
        "winner":       best_name,
        "rows_trained": len(X_train),
        "rows_tested":  len(X_test),
        "random_forest": {
            "accuracy":  round(rf_report["accuracy"], 4),
            "precision": round(rf_report["1"]["precision"], 4),
            "recall":    round(rf_report["1"]["recall"], 4),
            "f1_score":  round(rf_f1, 4),
        },
        "xgboost": {
            "accuracy":  round(xgb_report["accuracy"], 4),
            "precision": round(xgb_report["1"]["precision"], 4),
            "recall":    round(xgb_report["1"]["recall"], 4),
            "f1_score":  round(xgb_f1, 4),
        },
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
    logger.info(f"Prédiction batch — {len(req.orders)} commandes traitées")
    return [
        OrderPrediction(
            order_index        = i,
            late_delivery_risk = int(predictions[i]),
            probability        = round(float(probabilities[i]), 4),
            risk_level         = risk_label(float(probabilities[i])),
        )
        for i in range(len(req.orders))
    ]


@app.post("/segment/train")
def train_segmentation(n_clusters: int = 4):
    """
    Entraîne un modèle KMeans pour segmenter les clients.
    n_clusters : nombre de segments souhaité (défaut: 4)
    """
    global segment_model, segment_scaler, segment_encoders, segment_summary

    # 1. Récupération des données
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.get(f"{DATA_SERVICE_URL}/data/segments")
            r.raise_for_status()
        df = pd.DataFrame(r.json()["data"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"data-service error : {e}")

    # 2. Encodage des colonnes catégorielles
    seg_encoders = {}
    for col in SEGMENT_CATEGORICAL:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        seg_encoders[col] = le

    # 3. Nettoyage
    df = df[SEGMENT_FEATURES + SEGMENT_CATEGORICAL].dropna()

    all_features = SEGMENT_FEATURES + SEGMENT_CATEGORICAL

    # 4. Normalisation (KMeans est sensible aux échelles)
    scaler = StandardScaler()
    X = scaler.fit_transform(df[all_features])

    # 5. Entraînement KMeans
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["segment"] = km.fit_predict(X)

    # 6. Calcul du résumé par segment
    summary = {}
    for seg_id in range(n_clusters):
        seg_df = df[df["segment"] == seg_id]
        summary[str(seg_id)] = {
            "size":                      int(len(seg_df)),
            "pct":                       round(len(seg_df) / len(df) * 100, 1),
            "avg_sales":                 round(float(seg_df["sales"].mean()), 2),
            "avg_benefit":               round(float(seg_df["benefit_per_order"].mean()), 2),
            "avg_quantity":              round(float(seg_df["order_item_quantity"].mean()), 2),
            "avg_discount_rate":         round(float(seg_df["order_item_discount_rate"].mean()), 4),
            "late_delivery_rate":        round(float(seg_df["late_delivery_risk"].mean()), 4),
            "avg_shipping_scheduled":    round(float(seg_df["days_for_shipping_scheduled"].mean()), 2),
        }

    # 7. Sauvegarde
    segment_model   = km
    segment_scaler  = scaler
    segment_encoders = seg_encoders
    segment_summary = summary

    joblib.dump(segment_model,    SEGMENT_MODEL_PATH)
    joblib.dump(segment_scaler,   SEGMENT_SCALER_PATH)
    joblib.dump(segment_encoders, SEGMENT_ENCODERS_PATH)
    joblib.dump(segment_summary,  SEGMENT_SUMMARY_PATH)

    return {
        "status":     "success",
        "n_clusters": n_clusters,
        "total_rows": len(df),
        "segments":   summary,
    }


@app.get("/segment/summary")
def get_segment_summary():
    """Retourne le résumé des segments entraînés."""
    if not segment_summary:
        raise HTTPException(
            status_code=503,
            detail="Segementation Model not trained — launch POST /segment/train"
        )
    return {"status": "success", "segments": segment_summary}


class SegmentRequest(BaseModel):
    customer_segment:            str   = Field(..., examples=["Consumer"])
    market:                      str   = Field(..., examples=["Europe"])
    sales:                       float = Field(..., examples=[199.99])
    benefit_per_order:           float = Field(..., examples=[35.0])
    order_item_quantity:         int   = Field(..., examples=[2])
    order_item_discount_rate:    float = Field(..., examples=[0.05])
    late_delivery_risk:          int   = Field(..., examples=[0])
    days_for_shipping_scheduled: int   = Field(..., examples=[4])


@app.post("/segment/predict")
def predict_segment(req: SegmentRequest):
    """Assigne un client à un segment."""
    if segment_model is None:
        raise HTTPException(
            status_code=503,
            detail="Segmentation Model not trained — launch POST /segment/train"
        )

    df = pd.DataFrame([req.model_dump()])

    # Encodage
    for col in SEGMENT_CATEGORICAL:
        le = segment_encoders[col]
        df[col] = df[col].astype(str).map(
            lambda x, le=le: le.transform([x])[0] if x in le.classes_ else 0
        )

    all_features = SEGMENT_FEATURES + SEGMENT_CATEGORICAL
    X = segment_scaler.transform(df[all_features])
    seg_id = int(segment_model.predict(X)[0])

    return {
        "segment_id":  seg_id,
        "segment_info": segment_summary.get(str(seg_id), {}),
    }


request_counts: dict = defaultdict(int)
error_counts:   dict = defaultdict(int)

@app.middleware("http")
async def count_requests(request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = round(time.time() - start, 4)
    
    endpoint = request.url.path
    request_counts[endpoint] += 1
    if response.status_code >= 400:
        error_counts[endpoint] += 1
    
    logger.info(f"HTTP {request.method} {endpoint} {response.status_code} {duration}s")
    return response


@app.get("/metrics")
def get_metrics():
    return {
        "service":        "ml-service",
        "model_loaded":   model is not None,
        "model_name":     model_name,
        "segment_loaded": segment_model is not None,
        "request_counts": dict(request_counts),
        "error_counts":   dict(error_counts),
    }