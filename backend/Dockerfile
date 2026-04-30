FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5

# Install system-level dependencies required by LightGBM / XGBoost (used by FLAML AutoML).
# libgomp1  → GNU OpenMP runtime (libgomp.so.1) — the direct cause of the crash.
# libgcc-s1 → GCC support library also needed by compiled ML binaries.
# build-essential → ensures gcc/g++ are available if any pip build happens at install time.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        libgcc-s1 \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

EXPOSE 5000

CMD ["python", "backend/app.py"]
