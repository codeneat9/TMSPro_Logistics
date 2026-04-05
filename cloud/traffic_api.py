"""TomTom traffic integration endpoints.

This module keeps API keys server-side and exposes a simple route-level
traffic summary for the dashboard.
"""

from __future__ import annotations

import os
from typing import Any
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/traffic", tags=["traffic"])

_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"


class RouteTrafficRequest(BaseModel):
    coordinates: list[list[float]] = Field(
        ...,
        description="Route coordinates as [[lat, lon], ...]",
        min_length=2,
    )


def _get_tomtom_key() -> str:
    key = os.getenv("TOMTOM_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="TomTom API key not configured. Set TOMTOM_API_KEY in environment.",
        )
    return key


def _sample_route_points(coords: list[list[float]], max_points: int = 18) -> list[tuple[float, float]]:
    """Sample route points to keep API calls bounded while staying representative."""
    cleaned: list[tuple[float, float]] = []
    for pair in coords:
        if len(pair) < 2:
            continue
        lat = float(pair[0])
        lon = float(pair[1])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            cleaned.append((lat, lon))

    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Invalid route coordinates")

    if len(cleaned) <= max_points:
        return cleaned

    step = max(1, len(cleaned) // max_points)
    sampled = cleaned[::step]
    if sampled[-1] != cleaned[-1]:
        sampled.append(cleaned[-1])
    return sampled[:max_points]


def _point_flow(lat: float, lon: float, key: str) -> dict[str, Any] | None:
    try:
        resp = requests.get(
            _FLOW_URL,
            params={"point": f"{lat},{lon}", "key": key},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json().get("flowSegmentData") or {}
        current = float(payload.get("currentSpeed", 0.0) or 0.0)
        free = float(payload.get("freeFlowSpeed", 0.0) or 0.0)
        conf = float(payload.get("confidence", 0.0) or 0.0)

        ratio = (current / free) if free > 0 else 0.0
        congestion = max(0.0, min(1.0, 1.0 - ratio))
        return {
            "current_speed_kph": current,
            "free_flow_speed_kph": free,
            "confidence": conf,
            "speed_ratio": ratio,
            "congestion": congestion,
        }
    except Exception:
        return None


def _bucket(congestion: float) -> str:
    if congestion >= 0.65:
        return "severe"
    if congestion >= 0.45:
        return "heavy"
    if congestion >= 0.25:
        return "moderate"
    return "light"


@router.get("/health", summary="Traffic service health")
def traffic_health() -> dict[str, Any]:
    key_present = bool(os.getenv("TOMTOM_API_KEY", "").strip())
    return {
        "status": "ok",
        "provider": "tomtom",
        "key_configured": key_present,
    }


@router.post("/route-summary", summary="Get live traffic summary for route")
def route_summary(request: RouteTrafficRequest) -> dict[str, Any]:
    key = _get_tomtom_key()
    sampled = _sample_route_points(request.coordinates)

    flow_points = []
    for lat, lon in sampled:
        point_data = _point_flow(lat, lon, key)
        if point_data:
            flow_points.append(point_data)

    if not flow_points:
        raise HTTPException(status_code=502, detail="TomTom flow data unavailable for route")

    avg_current = sum(p["current_speed_kph"] for p in flow_points) / len(flow_points)
    avg_free = sum(p["free_flow_speed_kph"] for p in flow_points) / len(flow_points)
    avg_ratio = (avg_current / avg_free) if avg_free > 0 else 0.0
    avg_congestion = max(0.0, min(1.0, 1.0 - avg_ratio))
    severity = _bucket(avg_congestion)

    # Heuristic multiplier for ETA penalty derived from congestion.
    congestion_factor = 1.0 + (avg_congestion * 0.7)

    return {
        "provider": "tomtom",
        "sampled_points": len(flow_points),
        "avg_current_speed_kph": round(avg_current, 1),
        "avg_free_flow_speed_kph": round(avg_free, 1),
        "avg_speed_ratio": round(avg_ratio, 3),
        "avg_congestion": round(avg_congestion, 3),
        "severity": severity,
        "congestion_factor": round(congestion_factor, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
