"""
Agent decision service.

Selects the best route based on delay, risk, and cost signals and returns
actionable recommendations for normal and emergency scenarios.
"""

import json
import uuid
from typing import Any
from sqlalchemy.orm import Session

from backend.models.route import Route
from backend.models.trip import Trip
from backend.models.trip_log import TripLog


class DecisionAgentService:
    """Rule-based decision engine for route selection."""

    @staticmethod
    def _severity_weight(severity: str) -> float:
        severity = (severity or "low").lower()
        if severity == "high":
            return 1.4
        if severity == "medium":
            return 1.15
        return 1.0

    @staticmethod
    def decide(
        route_options: list[dict[str, Any]],
        delay_prediction: dict[str, Any],
        emergency: bool = False,
    ) -> dict[str, Any]:
        """
        Produce route decision and handling actions.

        Inputs:
        - route_options: [{route_id|id, route_type, distance_km, duration_minutes, risk_score, predicted_cost, predicted_delay_minutes}]
        - delay_prediction: {predicted_delay_minutes, delay_probability, severity}
        - emergency: prioritize fastest safe route when true
        """
        if not route_options:
            raise ValueError("route_options must not be empty")

        predicted_delay = float(delay_prediction.get("predicted_delay_minutes", 0) or 0)
        delay_probability = float(delay_prediction.get("delay_probability", 0) or 0)
        severity = delay_prediction.get("severity", "low")
        sev_w = DecisionAgentService._severity_weight(severity)

        scored: list[dict[str, Any]] = []
        for option in route_options:
            distance = float(option.get("distance_km", 0) or 0)
            duration = float(option.get("duration_minutes", 0) or 0)
            risk = float(option.get("risk_score", 0) or 0)
            cost = float(option.get("predicted_cost", 0) or 0)
            route_delay = float(option.get("predicted_delay_minutes", predicted_delay) or 0)

            if emergency:
                score = (duration * 0.6) + (risk * 0.3 * sev_w) + (route_delay * 0.1)
            else:
                score = (
                    (duration * 0.40)
                    + (risk * 0.25 * sev_w)
                    + (cost * 0.20)
                    + (route_delay * 0.15)
                    + (delay_probability * 5.0)
                    + (distance * 0.05)
                )

            scored.append(
                {
                    "route_id": option.get("route_id") or option.get("id"),
                    "route_type": option.get("route_type", "unknown"),
                    "score": round(score, 3),
                    "inputs": {
                        "distance_km": distance,
                        "duration_minutes": duration,
                        "risk_score": risk,
                        "predicted_cost": cost,
                        "predicted_delay_minutes": route_delay,
                    },
                }
            )

        scored.sort(key=lambda item: item["score"])
        chosen = scored[0]

        actions: list[str] = ["notify_client", "notify_driver"]
        if emergency:
            actions.extend(["escalate_dispatch", "priority_reroute"])
        elif severity in ["high", "medium"]:
            actions.append("monitor_trip")

        return {
            "selected_route_id": chosen["route_id"],
            "selected_route_type": chosen["route_type"],
            "decision_reason": f"lowest_composite_score ({chosen['score']})",
            "emergency_mode": emergency,
            "recommended_actions": actions,
            "ranked_routes": scored,
        }

    @staticmethod
    def decide_and_apply(
        db: Session,
        trip_id: str,
        route_options: list[dict[str, Any]],
        delay_prediction: dict[str, Any],
        emergency: bool = False,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        """Decide best route, apply it to trip state, and persist an audit log."""
        decision = DecisionAgentService.decide(
            route_options=route_options,
            delay_prediction=delay_prediction,
            emergency=emergency,
        )

        selected_route_id = decision.get("selected_route_id")
        if not selected_route_id:
            raise ValueError("No route selected by decision engine")

        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise ValueError("Trip not found")

        route = (
            db.query(Route)
            .filter(Route.id == selected_route_id, Route.trip_id == trip_id)
            .first()
        )
        if not route:
            raise ValueError("Selected route not found for trip")

        trip.selected_route_polyline = route.polyline
        trip.estimated_delay_minutes = route.predicted_delay_minutes

        log_payload = {
            "selected_route_id": selected_route_id,
            "selected_route_type": decision.get("selected_route_type"),
            "decision_reason": decision.get("decision_reason"),
            "emergency_mode": decision.get("emergency_mode"),
            "recommended_actions": decision.get("recommended_actions", []),
            "ranked_routes": decision.get("ranked_routes", []),
        }
        trip_log = TripLog(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            actor_user_id=actor_user_id,
            event_type="agent_decision_applied",
            message="Applied agent-selected route to trip",
            details=json.dumps(log_payload),
        )

        db.add(trip_log)
        db.commit()

        return {
            "trip_id": trip_id,
            "applied": True,
            **decision,
        }
