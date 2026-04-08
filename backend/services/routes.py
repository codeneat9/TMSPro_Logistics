"""
Routes Service
Handles route generation, optimization, and delay prediction
"""

import math
import uuid
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from backend.models.route import Route
from backend.models.trip import Trip
from backend.config import settings


class RoutesService:
    """Service for route operations"""

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Approximate distance in km between two coordinates."""
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    @staticmethod
    def fetch_routes(
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        alternatives: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Fetch route options from OSRM with deterministic fallback.

        Returns a list with an optimal route and up to N alternatives.
        """
        alternatives = max(0, min(alternatives, 3))
        desired_total = 1 + alternatives
        osrm_alternatives = "true" if alternatives > 0 else "false"

        url = (
            f"{settings.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/"
            f"{origin_lng},{origin_lat};{destination_lng},{destination_lat}"
        )
        params = {
            "overview": "full",
            "geometries": "polyline",
            "alternatives": osrm_alternatives,
            "steps": "false",
            "annotations": "false",
        }

        routes: List[Dict[str, Any]] = []

        try:
            response = requests.get(url, params=params, timeout=settings.OSRM_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            osrm_routes = payload.get("routes", [])

            for idx, item in enumerate(osrm_routes[:desired_total]):
                route_type = "optimal" if idx == 0 else f"alternative_{idx}"
                routes.append(
                    {
                        "route_type": route_type,
                        "distance_km": round(float(item.get("distance", 0.0)) / 1000.0, 2),
                        "duration_minutes": max(1, int(round(float(item.get("duration", 0.0)) / 60.0))),
                        "polyline": item.get("geometry", ""),
                        "source": "osrm",
                    }
                )
        except Exception:
            # Fallback is applied below
            routes = []

        if routes:
            return routes

        # Fallback if OSRM is unavailable.
        direct_km = max(
            0.5,
            RoutesService._haversine_km(origin_lat, origin_lng, destination_lat, destination_lng),
        )
        base_duration = max(2, int(round((direct_km / 35.0) * 60.0)))

        fallback = []
        for idx in range(desired_total):
            factor = 1.0 + (idx * 0.12)
            route_type = "optimal" if idx == 0 else f"alternative_{idx}"
            fallback.append(
                {
                    "route_type": route_type,
                    "distance_km": round(direct_km * factor, 2),
                    "duration_minutes": max(2, int(round(base_duration * factor))),
                    "polyline": f"fallback:{origin_lat},{origin_lng}|{destination_lat},{destination_lng}|{route_type}",
                    "source": "fallback",
                }
            )

        return fallback
    
    @staticmethod
    def create_route(
        db: Session,
        trip_id: str,
        distance_km: float,
        duration_minutes: int,
        polyline: str,
        route_type: str = "optimal",
        predicted_delay_minutes: int = 0,
        predicted_cost: Optional[float] = None,
        risk_score: Optional[float] = None
    ) -> Route:
        """Create a route for a trip"""
        route = Route(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            polyline=polyline,
            route_type=route_type,
            predicted_delay_minutes=predicted_delay_minutes,
            predicted_cost=predicted_cost,
            risk_score=risk_score or 0.0
        )
        db.add(route)
        db.commit()
        db.refresh(route)
        return route
    
    @staticmethod
    def get_route(db: Session, route_id: str) -> Optional[Route]:
        """Get a route by ID"""
        return db.query(Route).filter(Route.id == route_id).first()
    
    @staticmethod
    def get_trip_routes(db: Session, trip_id: str) -> List[Route]:
        """Get all routes for a trip"""
        return db.query(Route).filter(Route.trip_id == trip_id).all()
    
    @staticmethod
    def get_optimal_route(db: Session, trip_id: str) -> Optional[Route]:
        """Get the optimal (shortest/fastest) route for a trip"""
        return db.query(Route).filter(
            Route.trip_id == trip_id,
            Route.route_type == "optimal"
        ).first()
    
    @staticmethod
    def get_alternative_routes(db: Session, trip_id: str) -> List[Route]:
        """Get alternative routes for a trip"""
        return db.query(Route).filter(
            Route.trip_id == trip_id,
            Route.route_type.in_(["alternative_1", "alternative_2"])
        ).all()
    
    @staticmethod
    def select_route(
        db: Session,
        trip_id: str,
        route_id: str
    ) -> Optional[Trip]:
        """Select a route for a trip"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        
        if not trip:
            return None
        
        route = db.query(Route).filter(Route.id == route_id).first()
        
        if not route:
            return None
        
        # Update trip with selected route info
        trip.estimated_delay_minutes = route.predicted_delay_minutes
        
        db.commit()
        db.refresh(trip)
        return trip
    
    @staticmethod
    def predict_delay(
        db: Session,
        trip_id: str,
        hour_of_day: int,
        day_of_week: int,
        distance_km: float,
        weather_condition: Optional[str] = None
    ) -> int:
        """
        Predict delay minutes for a trip
        
        In production, integrate with:
        - Traffic API (Google Maps, TomTom)
        - Weather API
        - Historical traffic patterns
        - Machine learning model
        """
        
        # Simplified prediction logic
        base_delay = 0
        
        # Peak hours (7-9am, 5-7pm)
        if hour_of_day in [7, 8, 17, 18]:
            base_delay += 10
        
        # Weekend traffic is lighter
        if day_of_week > 5:  # Saturday/Sunday
            base_delay -= 5
        
        # Distance factor: ~1 minute per 5km in good conditions
        base_delay += int(distance_km / 5)
        
        # Weather impact
        if weather_condition and weather_condition.lower() in ["rain", "heavy_rain"]:
            base_delay += 15
        elif weather_condition and weather_condition.lower() == "foggy":
            base_delay += 10
        
        return max(base_delay, 0)

    @staticmethod
    def predict_delay_profile(
        db: Session,
        trip_id: str,
        hour_of_day: int,
        day_of_week: int,
        distance_km: float,
        weather_condition: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a richer prediction contract for delay-aware clients."""
        started = time.perf_counter()
        delay_minutes = RoutesService.predict_delay(
            db=db,
            trip_id=trip_id,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            distance_km=distance_km,
            weather_condition=weather_condition,
        )

        # Simple calibrated mapping for MVP; replace with model probability output later.
        probability = min(0.95, max(0.05, round(delay_minutes / 60.0, 2)))
        if delay_minutes >= 30:
            severity = "high"
        elif delay_minutes >= 15:
            severity = "medium"
        else:
            severity = "low"

        inference_ms = int((time.perf_counter() - started) * 1000)

        return {
            "trip_id": trip_id,
            "predicted_delay_minutes": delay_minutes,
            "delay_probability": probability,
            "severity": severity,
            "confidence": round(0.75 + (0.2 if weather_condition else 0.0), 2),
            "model_version": "heuristic-v1",
            "inference_ms": max(1, inference_ms),
        }
    
    @staticmethod
    def calculate_risk_score(
        db: Session,
        trip_id: str,
        weather_condition: Optional[str] = None,
        traffic_condition: Optional[str] = None
    ) -> float:
        """
        Calculate risk score (0-100) for a route
        
        Factors:
        - Weather conditions
        - Traffic congestion
        - Time of day
        - Road types
        - Historical incident data
        """
        
        risk = 20.0  # Base risk
        
        # Weather impact
        if weather_condition:
            if weather_condition.lower() == "heavy_rain":
                risk += 25
            elif weather_condition.lower() == "rain":
                risk += 15
            elif weather_condition.lower() == "foggy":
                risk += 10
        
        # Traffic impact
        if traffic_condition:
            if traffic_condition.lower() == "congested":
                risk += 20
            elif traffic_condition.lower() == "moderate":
                risk += 10
        
        return min(round(risk, 1), 100.0)
    
    @staticmethod
    def estimate_cost(
        db: Session,
        distance_km: float,
        duration_minutes: int,
        vehicle_type: str = "standard"
    ) -> float:
        """
        Estimate trip cost
        
        Pricing model:
        - Base fare: $3
        - Per km: $1.5
        - Per minute (for waiting): $0.25
        - Vehicle multiplier (premium, etc)
        """
        
        # Base pricing
        base_fare = 3.0
        per_km = 1.5
        per_minute = 0.25
        
        # Vehicle multiplier
        vehicle_multipliers = {
            "economy": 1.0,
            "standard": 1.0,
            "comfort": 1.5,
            "premium": 2.0
        }
        
        multiplier = vehicle_multipliers.get(vehicle_type, 1.0)
        
        # Calculate cost
        cost = (base_fare + (distance_km * per_km) + (duration_minutes * per_minute)) * multiplier
        
        return round(cost, 2)
