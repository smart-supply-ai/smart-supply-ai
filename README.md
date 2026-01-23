# Smart Supply AI

## Collaborators
- **Guillaume (Gui)** — Backend, APIs, Microservices, Frontend, Software Engineering
- **Maxime (Max)** — Data Engineering, Machine Learning, Supply Chain expertise  
- **Shared** — PostgreSQL, Docker, Git workflow, CI/CD

---

## Goal
Build a **predictive supply chain platform** that:
- forecasts demand and lead times,
- detects and alerts on stockout risks,
- exposes results through APIs and a web interface.

The project is based on a public Kaggle supply-chain dataset and is designed as a **scalable, microservices-oriented system**.

---

## High-level architecture

- **PostgreSQL** as the shared data store
- **FastAPI microservices** for data access, ML inference, and alerting
- **React frontend** consuming the APIs
- **Docker Compose** for local orchestration
- **CI/CD-ready structure** (GitHub Actions)

---

## Repository structure

```text
smart-supply-ai/
  infra/          # Docker Compose & infrastructure config
  db/             # PostgreSQL schema, indexes, seed data
  services/       # Backend microservices (FastAPI)
  frontend/       # React web application
  ml/             # ML notebooks & training scripts (research)
  libs/           # Shared Python code (API contracts, models)
  scripts/        # Developer helper scripts
```
