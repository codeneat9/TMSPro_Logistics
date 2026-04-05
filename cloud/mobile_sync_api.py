"""Mobile auth and cloud-sync endpoints for TMS mobile app.

This module provides a lightweight persistence layer so the mobile app can
store trip history and retrieve user/driver KPIs. It is intentionally simple
and file-backed to avoid introducing new infrastructure dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import json


router = APIRouter(prefix="/mobile", tags=["mobile"])

_STORE_LOCK = Lock()
_STORE_PATH = Path(__file__).resolve().parent.parent / "tmp" / "mobile_sync_store.json"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(customer|logistics)$")


class TripSyncRequest(BaseModel):
    trip_id: str
    user_id: str
    role: str
    shipment_id: str | None = None
    delay_probability: float = 0.0
    distance_km: float = 0.0
    eta_min: float = 0.0
    sla_status: str | None = None
    dispatch_priority: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverProfileRequest(BaseModel):
    driver_id: str
    fleet: str | None = None
    vehicle_type: str | None = None
    base_hub: str | None = None


def _default_store() -> dict[str, Any]:
    return {
        "users": {},
        "drivers": {},
        "trips": [],
        "kpi_snapshots": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_store() -> dict[str, Any]:
    if not _STORE_PATH.exists():
        return _default_store()

    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_store()


def _write_store(store: dict[str, Any]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    store["updated_at"] = datetime.now(timezone.utc).isoformat()
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _user_kpis(trips: list[dict[str, Any]]) -> dict[str, Any]:
    if not trips:
        return {
            "trip_count": 0,
            "avg_delay_probability": 0.0,
            "avg_eta_min": 0.0,
            "at_risk_trips": 0,
            "breach_trips": 0,
        }

    trip_count = len(trips)
    avg_delay_probability = sum(float(t.get("delay_probability", 0.0)) for t in trips) / trip_count
    avg_eta_min = sum(float(t.get("eta_min", 0.0)) for t in trips) / trip_count
    at_risk = sum(1 for t in trips if float(t.get("delay_probability", 0.0)) >= 0.5)
    breach = sum(1 for t in trips if str(t.get("sla_status", "")).lower() == "breach")

    return {
        "trip_count": trip_count,
        "avg_delay_probability": round(avg_delay_probability, 4),
        "avg_eta_min": round(avg_eta_min, 2),
        "at_risk_trips": at_risk,
        "breach_trips": breach,
    }


@router.get("/health")
def mobile_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mobile-sync",
        "store_path": str(_STORE_PATH),
    }


@router.post("/auth/login")
def mobile_login(request: LoginRequest) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()

        user_id = request.username.strip()
        if not user_id:
            raise HTTPException(status_code=400, detail="username cannot be empty")

        users = store.setdefault("users", {})
        users[user_id] = {
            "user_id": user_id,
            "role": request.role,
            "last_login_at": datetime.now(timezone.utc).isoformat(),
        }

        token = f"mobile-{request.role}-{user_id}-{int(datetime.now(timezone.utc).timestamp())}"
        _write_store(store)

    return {
        "user_id": user_id,
        "role": request.role,
        "token": token,
        "signed_in_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sync/trip")
def sync_trip(request: TripSyncRequest) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()
        trip_record = {
            "trip_id": request.trip_id,
            "user_id": request.user_id,
            "role": request.role,
            "shipment_id": request.shipment_id,
            "delay_probability": request.delay_probability,
            "distance_km": request.distance_km,
            "eta_min": request.eta_min,
            "sla_status": request.sla_status,
            "dispatch_priority": request.dispatch_priority,
            "metadata": request.metadata,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

        store.setdefault("trips", []).append(trip_record)
        _write_store(store)

    return {
        "status": "synced",
        "trip_id": request.trip_id,
    }


@router.get("/sync/trips/{user_id}")
def get_user_trips(user_id: str) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()
        all_trips = store.get("trips", [])

    user_trips = [t for t in all_trips if t.get("user_id") == user_id]
    user_trips = sorted(user_trips, key=lambda x: x.get("synced_at", ""), reverse=True)

    return {
        "user_id": user_id,
        "count": len(user_trips),
        "trips": user_trips[:100],
    }


@router.get("/sync/kpis/{user_id}")
def get_user_kpis(user_id: str) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()
        user_trips = [t for t in store.get("trips", []) if t.get("user_id") == user_id]

    return {
        "user_id": user_id,
        "kpis": _user_kpis(user_trips),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sync/driver")
def upsert_driver_profile(request: DriverProfileRequest) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()
        drivers = store.setdefault("drivers", {})

        drivers[request.driver_id] = {
            "driver_id": request.driver_id,
            "fleet": request.fleet or "default-fleet",
            "vehicle_type": request.vehicle_type or "van",
            "base_hub": request.base_hub or "lisbon-hub",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        _write_store(store)

    return {
        "status": "updated",
        "driver": drivers[request.driver_id],
    }


@router.get("/sync/driver/{driver_id}")
def get_driver_profile(driver_id: str) -> dict[str, Any]:
    with _STORE_LOCK:
        store = _read_store()
        driver = store.get("drivers", {}).get(driver_id)

    if not driver:
        raise HTTPException(status_code=404, detail="driver not found")

    return {
        "driver": driver,
    }
