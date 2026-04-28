FROM python:3.11-slim

WORKDIR /app

# Install build tools for packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Remove .env to avoid leaking secrets in image (use Cloud Run env vars instead)
RUN rm -f .env

# Train ML model at build time if not already present
RUN python ml/train_model.py --no-regen 2>/dev/null || python ml/train_model.py

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
