"""
Production Dashboard API
Provides consolidated endpoints for the web dashboard
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from routing.rerouting_agent import ReroutingAgent, RerouteStrategy
from routing.route_optimizer import RouteOptimizer
from cloud.feature_builder import DelayFeatureBuilder
from scripts.predict_delay import DelayPredictor

logger = logging.getLogger(__name__)

# Initialize components
_rerouting_agent = None
_route_optimizer = None
_feature_builder = None
_delay_predictor = None


def get_rerouting_agent() -> ReroutingAgent:
    """Lazy initialization of rerouting agent"""
    global _rerouting_agent
    if _rerouting_agent is None:
        _rerouting_agent = ReroutingAgent()
    return _rerouting_agent


def get_route_optimizer() -> RouteOptimizer:
    """Lazy initialization of route optimizer"""
    global _route_optimizer
    if _route_optimizer is None:
        _route_optimizer = RouteOptimizer("Lisbon", "Portugal")
    return _route_optimizer


def get_feature_builder() -> DelayFeatureBuilder:
    """Lazy initialization of feature builder"""
    global _feature_builder
    if _feature_builder is None:
        _feature_builder = DelayFeatureBuilder()
    return _feature_builder


def get_delay_predictor() -> DelayPredictor:
    """Lazy initialization of delay predictor"""
    global _delay_predictor
    if _delay_predictor is None:
        _delay_predictor = DelayPredictor()
    return _delay_predictor


# ========== Pydantic Models ==========

class TripRequest(BaseModel):
    """Request for consolidated trip planning/prediction"""
    trip_id: str = Field(..., description="Unique trip identifier")
    driver_id: Optional[str] = Field(None, description="Driver identifier")
    pickup_lat: float
    pickup_lon: float
    destination_lat: float
    destination_lon: float
    pickup_timestamp: int
    taxi_id: int
    call_type: str
    day_type: str
    temperature_2m: float
    precipitation: float
    windspeed_10m: float
    strategy: Optional[str] = Field("balanced", description="Rerouting strategy")


class DashboardTripResponse(BaseModel):
    """Complete trip information for dashboard"""
    trip_id: str
    driver_id: str
    pickup: dict
    destination: dict
    predicted_delay: dict
    primary_route: dict
    alternate_routes: List[dict]
    reroute_recommendation: dict
    agent_decision: dict
    driver_alert: Optional[str]
    timestamp: str


# ========== API Router ==========

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/health", summary="Dashboard service health")
async def dashboard_health():
    """Check if dashboard service is ready"""
    return {
        "status": "ok",
        "service": "dashboard",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/plan-trip", response_model=DashboardTripResponse, summary="Complete trip planning")
async def plan_trip(request: TripRequest):
    """
    Complete consolidated endpoint for trip planning.
    
    Takes raw trip data and returns:
    1. Delay prediction
    2. Multiple routes with risk scores
    3. Agent-based reroute recommendation
    4. Driver alert message
    
    This is the main endpoint for the dashboard.
    """
    try:
        # Get all components
        feature_builder = get_feature_builder()
        delay_predictor = get_delay_predictor()
        route_optimizer = get_route_optimizer()
        rerouting_agent = get_rerouting_agent()

        # ===== STEP 1: Build features and predict delay =====
        trip_payload = {
            "pickup_lat": request.pickup_lat,
            "pickup_lon": request.pickup_lon,
            "destination_lat": request.destination_lat,
            "destination_lon": request.destination_lon,
            "pickup_timestamp": request.pickup_timestamp,
            "taxi_id": request.taxi_id,
            "call_type": request.call_type,
            "day_type": request.day_type,
            "temperature_2m": request.temperature_2m,
            "precipitation": request.precipitation,
            "windspeed_10m": request.windspeed_10m
        }

        built_features = feature_builder.build(trip_payload)
        delay_prediction = delay_predictor.predict(built_features.features)

        # ===== STEP 2: Calculate routes =====
        routes_data = route_optimizer.get_all_routes(
            origin_lat=request.pickup_lat,
            origin_lon=request.pickup_lon,
            dest_lat=request.destination_lat,
            dest_lon=request.destination_lon,
            num_alternatives=2,
            delay_probability=delay_prediction["delay_probability"],
            time_of_day=built_features.features.get("hour"),
            weather="rain" if request.precipitation > 2.0 else ("clear" if request.precipitation < 0.5 else "rain")
        )

        # ===== STEP 3: Agent-based rerouting decision =====
        # Ensure we have valid routes
        primary_route = routes_data["primary_route"] or (routes_data["alternate_routes"][0] if routes_data["alternate_routes"] else None)
        if not primary_route:
            raise HTTPException(status_code=400, detail="Could not calculate routes for this trip")
        
        strategy_map = {
            "fastest": RerouteStrategy.FASTEST,
            "safest": RerouteStrategy.SAFEST,
            "balanced": RerouteStrategy.BALANCED,
            "avoid_traffic": RerouteStrategy.AVOID_TRAFFIC,
            "minimize_distance": RerouteStrategy.MINIMIZE_DISTANCE
        }
        
        strategy = strategy_map.get(request.strategy, RerouteStrategy.BALANCED)

        rerouting_decision = rerouting_agent.decide_reroute(
            current_route=primary_route,
            alternate_routes=routes_data["alternate_routes"],
            delay_probability=delay_prediction["delay_probability"],
            weather="rain" if request.precipitation > 2.0 else "clear",
            time_of_day=built_features.features.get("hour"),
            strategy=strategy
        )

        # ===== BUILD RESPONSE =====
        response = DashboardTripResponse(
            trip_id=request.trip_id,
            driver_id=request.driver_id or "driver_unknown",
            pickup={
                "lat": request.pickup_lat,
                "lon": request.pickup_lon
            },
            destination={
                "lat": request.destination_lat,
                "lon": request.destination_lon
            },
            predicted_delay={
                "probability": round(delay_prediction["delay_probability"], 3),
                "is_delayed": delay_prediction["is_delayed"],
                "confidence": delay_prediction["confidence"],
                "threshold_used": delay_prediction["threshold_used"]
            },
            primary_route=primary_route,
            alternate_routes=routes_data["alternate_routes"],
            reroute_recommendation={
                "should_reroute": rerouting_decision.should_reroute,
                "recommended_route_index": rerouting_decision.reroute_action.recommended_route_index if rerouting_decision.reroute_action else 0,
                "reasoning": rerouting_decision.reasoning,
                "confidence": rerouting_decision.confidence,
                "urgency_level": rerouting_decision.urgency_level,
                "potential_time_savings": rerouting_decision.reroute_action.potential_time_savings_min if rerouting_decision.reroute_action else 0
            },
            agent_decision={
                "decision": rerouting_decision.should_reroute,
                "reasoning": rerouting_decision.reasoning,
                "confidence": round(rerouting_decision.confidence, 2),
                "urgency": rerouting_decision.urgency_level
            },
            driver_alert=rerouting_decision.driver_notification,
            timestamp=datetime.now().isoformat()
        )

        return response

    except Exception as e:
        logger.error(f"Error in plan_trip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-status/{driver_id}", summary="Get agent status for driver")
async def get_agent_status(driver_id: str):
    """Get rerouting agent status and decision history for a driver"""
    try:
        agent = get_rerouting_agent()
        status = agent.get_agent_status()
        return {
            "driver_id": driver_id,
            "agent_status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route-coordinates/{route_index}", summary="Get route coordinates")
async def get_route_coordinates(route_index: int):
    """Get detailed coordinates for a specific route"""
    try:
        # This would fetch from saved route data
        return {
            "route_index": route_index,
            "message": "Route coordinates available from /plan-trip response"
        }
    except Exception as e:
        logger.error(f"Error getting route coordinates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
