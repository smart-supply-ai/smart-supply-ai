# Backend Services Overview

This folder contains the **backend microservices** of Smart Supply AI.  
Each service is an independent **FastAPI application**, deployed as its own Docker container and orchestrated locally via Docker Compose.

All services communicate over **HTTP** and share:
- a common PostgreSQL database (different schemas / tables),
- common API contracts defined in `libs/contracts`.

---

## Services

### 1) Data Service (`data-service/`)
**Responsibility:**  
Expose supply-chain data stored in PostgreSQL in a clean, queryable way.

**Main roles:**
- Read raw and cleaned data from the database
- Provide filtered & paginated endpoints for the frontend
- Expose **feature views** used by the ML service

**Typical endpoints:**
- `GET /health`
- `GET /orders`
- `GET /products`
- `GET /feature-view/order/{order_id}`

**Dependencies:**
- PostgreSQL  
(see [`db/README.md`](../db/README.md))

---

### 2) ML Service (`ml-service/`)
**Responsibility:**  
Serve trained Machine Learning models for inference.

**Main roles:**
- Load a serialized model artifact (e.g. joblib / pickle)
- Run predictions (lead time, demand, risk)
- Return predictions with metadata (model version, confidence, etc.)

**Typical endpoints:**
- `POST /predict/lead-time`
- `POST /predict/demand`
- `GET /models/current`

**Dependencies:**
- Data Service (optional, for feature retrieval)
- Model artifacts produced in the `ml/` folder

---

### 3) Alert Service (`alert-service/`)
**Responsibility:**  
Transform predictions into actionable business alerts.

**Main roles:**
- Query relevant entities (products, orders, stock)
- Call the ML Service to obtain predictions
- Apply business rules (thresholds, risk logic)
- Store and expose alerts

**Typical endpoints:**
- `POST /alerts/run` (manual or scheduled trigger)
- `GET /alerts`
- `PATCH /alerts/{id}/ack`

**Dependencies:**
- PostgreSQL
- Data Service
- ML Service

---

## Service interactions (simplified)

```text
Frontend
   │
   ▼
Alert Service ──► ML Service
      │               ▲
      ▼               │
  PostgreSQL ◄── Data Service
```
