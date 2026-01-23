from fastapi import FastAPI

app = FastAPI(title="Data Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "data-service", "status": "ok"}


@app.get("/ready")
def ready():
    # Check DB connectivity here
    return {"service": "data-service", "ready": True}


@app.get("/")
def root():
    return {
        "service": "data-service",
        "message": "Dummy Data Service running. See /docs",
    }
