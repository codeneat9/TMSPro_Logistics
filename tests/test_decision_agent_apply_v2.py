import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.route import Route
from backend.models.trip import Trip
from backend.models.trip_log import TripLog
from backend.models.user import User
from backend.services.decision_agent import DecisionAgentService


def _build_local_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _seed_trip_with_route(db, route_id: str = "r-1"):
    user = User(
        id="user-1",
        email="agent-test@example.com",
        password_hash="hashed",
        full_name="Agent Test",
        phone="+10000000000",
        role="customer",
        is_active=True,
        is_verified=True,
    )
    trip = Trip(
        id="trip-1",
        user_id=user.id,
        pickup_lat=12.90,
        pickup_lng=77.50,
        dropoff_lat=12.97,
        dropoff_lng=77.59,
    )
    route = Route(
        id=route_id,
        trip_id=trip.id,
        route_type="optimal",
        distance_km=12.5,
        duration_minutes=25,
        polyline="encoded-polyline",
        predicted_delay_minutes=9,
        predicted_cost=22.0,
        risk_score=0.2,
    )
    db.add(user)
    db.add(trip)
    db.add(route)
    db.commit()


def test_decide_and_apply_persists_log_and_updates_trip():
    db = _build_local_session()
    try:
        _seed_trip_with_route(db, route_id="r-1")

        result = DecisionAgentService.decide_and_apply(
            db=db,
            trip_id="trip-1",
            route_options=[
                {
                    "route_id": "r-1",
                    "route_type": "optimal",
                    "distance_km": 12.5,
                    "duration_minutes": 25,
                    "risk_score": 0.2,
                    "predicted_cost": 22.0,
                    "predicted_delay_minutes": 9,
                }
            ],
            delay_prediction={"predicted_delay_minutes": 10, "delay_probability": 0.3, "severity": "low"},
            emergency=False,
            actor_user_id="user-1",
        )

        assert result["applied"] is True
        assert result["trip_id"] == "trip-1"
        assert result["selected_route_id"] == "r-1"

        trip = db.query(Trip).filter(Trip.id == "trip-1").first()
        assert trip is not None
        assert trip.selected_route_polyline == "encoded-polyline"
        assert trip.estimated_delay_minutes == 9

        logs = db.query(TripLog).filter(TripLog.trip_id == "trip-1").all()
        assert len(logs) == 1
        assert logs[0].event_type == "agent_decision_applied"
        payload = json.loads(logs[0].details)
        assert payload["selected_route_id"] == "r-1"
        assert payload["emergency_mode"] is False
    finally:
        db.close()


def test_decide_and_apply_rejects_missing_trip():
    db = _build_local_session()
    try:
        with pytest.raises(ValueError, match="Trip not found"):
            DecisionAgentService.decide_and_apply(
                db=db,
                trip_id="missing-trip",
                route_options=[
                    {
                        "route_id": "r-1",
                        "route_type": "optimal",
                        "distance_km": 12.5,
                        "duration_minutes": 25,
                        "risk_score": 0.2,
                        "predicted_cost": 22.0,
                        "predicted_delay_minutes": 9,
                    }
                ],
                delay_prediction={"predicted_delay_minutes": 10, "delay_probability": 0.3, "severity": "low"},
                emergency=False,
                actor_user_id="user-1",
            )
    finally:
        db.close()


def test_decide_and_apply_rejects_unknown_selected_route():
    db = _build_local_session()
    try:
        _seed_trip_with_route(db, route_id="r-known")

        with pytest.raises(ValueError, match="Selected route not found for trip"):
            DecisionAgentService.decide_and_apply(
                db=db,
                trip_id="trip-1",
                route_options=[
                    {
                        "route_id": "r-missing",
                        "route_type": "optimal",
                        "distance_km": 12.5,
                        "duration_minutes": 25,
                        "risk_score": 0.2,
                        "predicted_cost": 22.0,
                        "predicted_delay_minutes": 9,
                    }
                ],
                delay_prediction={"predicted_delay_minutes": 10, "delay_probability": 0.3, "severity": "low"},
                emergency=False,
                actor_user_id="user-1",
            )
    finally:
        db.close()


def test_decide_and_apply_route_api_contract(client, auth_headers, monkeypatch):
    def _fake_apply(**kwargs):
        return {
            "trip_id": "trip-x",
            "applied": True,
            "selected_route_id": "route-x",
            "selected_route_type": "optimal",
            "decision_reason": "lowest_composite_score (10.2)",
            "emergency_mode": False,
            "recommended_actions": ["notify_client"],
            "ranked_routes": [{"route_id": "route-x", "score": 10.2}],
        }

    monkeypatch.setattr(DecisionAgentService, "decide_and_apply", staticmethod(_fake_apply))

    response = client.post(
        "/api/routes/agent/decide-and-apply",
        headers=auth_headers,
        json={
            "trip_id": "trip-x",
            "route_options": [
                {
                    "route_id": "route-x",
                    "route_type": "optimal",
                    "distance_km": 10.0,
                    "duration_minutes": 20,
                    "risk_score": 0.2,
                    "predicted_cost": 15.0,
                    "predicted_delay_minutes": 4,
                }
            ],
            "delay_prediction": {
                "predicted_delay_minutes": 6,
                "delay_probability": 0.3,
                "severity": "low",
            },
            "emergency": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trip_id"] == "trip-x"
    assert body["applied"] is True
    assert body["selected_route_id"] == "route-x"


def test_decide_and_apply_route_api_rejects_service_error(client, auth_headers, monkeypatch):
    def _raise_error(**kwargs):
        raise ValueError("Selected route not found for trip")

    monkeypatch.setattr(DecisionAgentService, "decide_and_apply", staticmethod(_raise_error))

    response = client.post(
        "/api/routes/agent/decide-and-apply",
        headers=auth_headers,
        json={
            "trip_id": "trip-x",
            "route_options": [
                {
                    "route_id": "route-x",
                    "route_type": "optimal",
                    "distance_km": 10.0,
                    "duration_minutes": 20,
                    "risk_score": 0.2,
                    "predicted_cost": 15.0,
                    "predicted_delay_minutes": 4,
                }
            ],
            "delay_prediction": {
                "predicted_delay_minutes": 6,
                "delay_probability": 0.3,
                "severity": "low",
            },
            "emergency": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected route not found for trip"
