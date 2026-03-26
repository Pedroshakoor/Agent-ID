FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Generate RSA keys if not present, then run migrations and start
RUN mkdir -p /app/keys

CMD ["sh", "-c", "\
    python -c \"from app.services.jwt_service import ensure_keys; ensure_keys()\" && \
    alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 \
"]
