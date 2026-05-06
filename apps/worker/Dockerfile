FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# NOTE: The build context is "apps/" (set in docker-compose.yml).
# So paths in COPY are relative to apps/, not to this Dockerfile's location.

COPY worker/requirements.txt /app/requirements.txt

# Install system dependencies for OCR and PDF image conversion
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the shared package (database models used by both API and Worker).
COPY shared /app/shared

# Copy the worker application code.
COPY worker/worker /app/worker

CMD ["celery", "-A", "worker.celery_app:celery_app", "worker", "--loglevel=INFO"]
