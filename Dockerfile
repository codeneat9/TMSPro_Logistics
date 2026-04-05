FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt /app/requirements-prod.txt
RUN python -m pip install --upgrade pip && \
    pip install -r /app/requirements-prod.txt

COPY . /app

EXPOSE 8000

# Production ASGI serving with multiple workers.
CMD ["sh", "-c", "gunicorn cloud.app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 --graceful-timeout 30 --keep-alive 30"]