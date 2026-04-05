# Production Deployment Guide

This project can be deployed as a production API + dashboard web app using Docker.

## 1. Prerequisites

- Docker Desktop (or Docker Engine)
- Docker Compose v2+

## 2. Environment Setup

1. Create a `.env` file from template:

```powershell
copy .env.example .env
```

2. Open `.env` and set:

- `TOMTOM_API_KEY=...` (required for live traffic features)

## 3. Build and Run (Production Mode)

```powershell
docker compose -f docker-compose.prod.yml up --build -d
```

## 4. Verify Health

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/traffic/health
```

Expected:

- `/health` returns `status: ok`
- `/traffic/health` returns `key_configured: true` when key is configured

## 5. Access App

- Dashboard: `http://127.0.0.1:8000/dashboard?global-routing=1`
- API docs: `http://127.0.0.1:8000/docs`

## 6. Stop / Restart

```powershell
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## 7. Production Notes

- The app uses Gunicorn + Uvicorn workers in the container.
- Keep `models/lightgbm_delay_model.txt` and `models/metrics.json` present in deployment artifact.
- For cloud deployment, map platform `PORT` env var and ensure outbound internet access for TomTom traffic and OSM route fetches.
