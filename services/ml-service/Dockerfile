FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.8 \
    uvicorn[standard]==0.30.6 \
    httpx==0.27.2 \
    pandas==2.2.2 \
    scikit-learn==1.5.1 \
    joblib==1.4.2 \
    xgboost==2.0.3

COPY main.py /app/main.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]