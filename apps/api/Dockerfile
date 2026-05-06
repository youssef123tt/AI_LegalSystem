FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# NOTE: The build context is "apps/" (set in docker-compose.yml).
# So paths in COPY are relative to apps/, not to this Dockerfile's location.

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the shared package (database models used by both API and Worker).
COPY shared /app/shared

# Copy the API application code.
COPY api/app /app/app

# Create upload directory.
RUN mkdir -p /data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
