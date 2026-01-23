# Database (PostgreSQL) — Smart Supply AI

This folder contains everything related to the **PostgreSQL database** used by **Smart Supply AI**.

The database acts as the **shared persistence layer** for all backend services:
- Data Service (raw & cleaned supply-chain data)
- Alert Service (generated alerts, alert status, history)
- ML Service (optional metadata such as model versions or inference logs)

---

## Role in the architecture

PostgreSQL is **not accessed directly by the frontend**.

All access goes through backend services:
- **Data Service** → reads supply-chain data and feature views
- **Alert Service** → stores and retrieves alerts
- **ML Service** → may read metadata (optional)

The database is started and managed by **Docker Compose** (see `infra/docker-compose.yml`).

---

## Contents

This folder contains:
- **Schema** — tables, constraints, and relationships
- **Indexes** — performance-related indexes
- **Seed data** — small, non-sensitive datasets for local development

All initialization SQL files are located in `db/init/`.

They are executed automatically by the official PostgreSQL Docker image:
- **only on first startup**
- **only when the database volume is empty**
