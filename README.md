# Smart Supply AI

Smart Supply AI is a microservices-based supply chain analytics platform designed to predict delivery risks, analyze logistics data, and provide business insights through APIs and an interactive dashboard.

The project combines data engineering, machine learning, backend systems, and frontend development into a scalable end-to-end architecture.

---

## Features

- Predict late deliveries and shipping risks
- Analyze supply chain and order data
- Interactive React dashboard
- AI-powered chatbot using Anthropic Claude + SQL generation
- PostgreSQL-backed analytics platform
- Dockerized microservices architecture
- REST APIs with FastAPI
- Repository structure prepared for future CI/CD workflows

---

## Tech Stack

### Backend

- Python
- FastAPI
- PostgreSQL
- Psycopg
- Anthropic Claude API

### Frontend

- React
- Vite
- Nginx

### Infrastructure

- Docker
- Docker Compose
- GitHub Actions-ready structure

### Machine Learning

- Scikit-learn
- Pandas
- NumPy

---

## Architecture

```text
                        ┌─────────────────┐
                        │  React Frontend │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
          ┌─────────▼─────────┐    ┌─────────▼─────────┐
          │   Alert Service   │    │   Query Service   │
          │  Risk Prediction  │    │ AI Chatbot + SQL  │
          └─────────┬─────────┘    └─────────┬─────────┘
                    │                        │
          ┌─────────▼─────────┐    ┌────────▼─────────┐
          │    ML Service     │    │  Anthropic API   │
          │  ML Inference     │    │     Claude       │
          └─────────┬─────────┘    └──────────────────┘
                    │
          ┌─────────▼─────────┐
          │   Data Service    │
          │ PostgreSQL Access │
          └─────────┬─────────┘
                    │
              ┌─────▼──────┐
              │ PostgreSQL │
              └────────────┘
```

---

## Repository Structure

```text
smart-supply-ai/
│
├── infra/                  # Docker Compose & infrastructure
├── db/                     # Database initialization scripts
├── data/                   # Dataset files
├── frontend/               # React frontend
│   ├── src/
│   │   ├── services/       # Frontend API services
│   │   ├── Chatbot.jsx
│   │   └── SmartSupplyDashboard.jsx
│
├── services/
│   ├── alert-service/      # Delivery risk prediction API
│   ├── data-service/       # Database access service
│   ├── ml-service/         # ML inference service
│   └── query-service/      # AI chatbot service
│
├── .github/
│   └── CODEOWNERS
│
└── README.md
```

---

## Services

### Data Service

Provides centralized access to PostgreSQL data.

### ML Service

Runs machine learning inference and prediction logic.

### Alert Service

Detects and exposes high-risk or delayed orders.

### Query Service

AI-powered chatbot that:

- converts natural language into SQL queries,
- retrieves relevant data,
- generates business-friendly insights using Claude.

---

## AI Chatbot

The chatbot allows users to query supply chain data in natural language.

Example:

```text
"Give me the 5 most delayed orders."
```

The backend:

1. Uses Claude to generate safe SQL queries
2. Retrieves data from PostgreSQL
3. Uses Claude again to transform raw results into business insights

The chatbot interface is integrated directly into the React dashboard.

---

## Local Development

1. Clone the repository

```bash
git clone <repository-url>
cd smart-supply-ai
```

2. Configure environment variables

Create a .env file from .env.example.

```env
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
ANTHROPIC_API_KEY=...
```

3. Start the services and the frontend

```bash
./dev.sh up
```

4. Access the website

```text
http://localhost:3000
```

---

## Collaborators

- Guillaume QUINTIN
  - Backend & Frontend development
  - APIs & microservices
  - Infrastructure & architecture
- Maxime
  - Backend development
  - Data engineering & Machine learning
  - Supply chain expertise

---

## Project Goals

This project was built to:

- explore scalable software architecture,
- apply machine learning to logistics problems,
- integrate LLMs into business analytics workflows.

---

## Disclaimer

This project uses a public Kaggle supply chain dataset for educational and portfolio purposes.

The predictions, alerts, and AI-generated insights displayed by the platform are intended for demonstration only and should not be used for real operational or business-critical decisions.

This repository is a personal engineering project focused on software architecture, machine learning integration, microservices design, and AI-assisted analytics.
