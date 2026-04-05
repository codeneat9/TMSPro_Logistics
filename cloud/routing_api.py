"""
FastAPI Routing Endpoints

Provides RESTful API for:
- Route calculation (primary + alternates)
- Rerouting decisions based on delay predictions
- Route optimization recommendations
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import asyncio

from routing.route_optimizer import RouteOptimizer
from routing.decision_agent import RerouteDecisionAgent

logger = logging.getLogger(__name__)

# Initialize router components (lazy-loaded)
_optimizer = None
_decision_agent = None


def get_optimizer() -> RouteOptimizer:
    """Lazy initialization of route optimizer"""
    global _optimizer
    if _optimizer is None:
        _optimizer = RouteOptimizer("Lisbon", "Portugal")
        # Note: Network loading happens on first route request
    return _optimizer


def get_decision_agent() -> RerouteDecisionAgent:
    """Lazy initialization of decision agent"""
    global _decision_agent
    if _decision_agent is None:
        _decision_agent = RerouteDecisionAgent()
    return _decision_agent


# ========== Pydantic Models ==========

class RouteRequest(BaseModel):
    """Request for route calculation"""
    origin_lat: float = Field(..., ge=-90, le=90, description="Origin latitude")
    origin_lon: float = Field(..., ge=-180, le=180, description="Origin longitude")
    destination_lat: float = Field(..., ge=-90, le=90, description="Destination latitude")
    destination_lon: float = Field(..., ge=-180, le=180, description="Destination longitude")
    delay_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Predicted delay probability")
    time_of_day: Optional[int] = Field(None, ge=0, le=23, description="Hour of day (0-23)")
    weather: Optional[str] = Field("clear", description="Weather condition: clear, rain, or storm")
    num_alternatives: Optional[int] = Field(2, ge=1, le=3, description="Number of alternate routes")


class RerouteRequest(BaseModel):
    """Request for rerouting recommendation"""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lon: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lon: float = Field(..., ge=-180, le=180)
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Predicted delay probability from model")
    time_of_day: Optional[int] = Field(None, ge=0, le=23)
    weather: Optional[str] = Field("clear")
    user_preference: Optional[str] = Field("balanced", description="speed, safety, or balanced")


class RoutesResponse(BaseModel):
    """Response with route calculations"""
    primary_route: dict
    alternate_routes: List[dict]
    all_routes: List[dict]
    recommended_route: dict
    summary: dict


class RerouteResponse(BaseModel):
    """Response with rerouting recommendation"""
    recommendation: dict
    routes: dict


# ========== API Router ==========

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/health", summary="Routing service health")
async def routing_health():
    """Check if routing service is ready"""
    optimizer = get_optimizer()
    return {
        "status": "ok",
        "optimizer_ready": optimizer.G is not None,
        "message": "Routing service is operational"
    }


@router.post("/routes", response_model=RoutesResponse, summary="Calculate routes")
async def calculate_routes(request: RouteRequest):
    """
    Calculate primary and alternate routes for a trip.

    **Request:**
    - origin_lat/lon: Starting coordinates
    - destination_lat/lon: Ending coordinates
    - delay_probability: Predicted delay (0.0-1.0)
    - time_of_day: Hour for traffic adjustment
    - weather: Environmental conditions
    - num_alternatives: 1-3 alternate routes

    **Response:**
    - primary_route: Shortest path
    - alternate_routes: Alternative options
    - recommended_route: Best option by risk/time balance
    """
    try:
        optimizer = get_optimizer()

        # Load network if not already loaded
        if optimizer.G is None:
            logger.info("Loading street network for routing...")
            success = optimizer.load_network(network_type="drive")
            if not success:
                raise HTTPException(status_code=503, detail="Failed to load routing network")

        # Calculate routes
        routes = optimizer.get_all_routes(
            origin_lat=request.origin_lat,
            origin_lon=request.origin_lon,
            dest_lat=request.destination_lat,
            dest_lon=request.destination_lon,
            num_alternatives=request.num_alternatives,
            delay_probability=request.delay_probability,
            time_of_day=request.time_of_day,
            weather=request.weather
        )

        if not routes["all_routes"]:
            raise HTTPException(status_code=400, detail="No routes found between coordinates")

        return routes

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reroute", response_model=RerouteResponse, summary="Get rerouting recommendation")
async def get_reroute_recommendation(request: RerouteRequest):
    """
    Get recommendation on whether to reroute a trip.

    **Decision Logic:**
    - High delay prob (≥70%) → STRONG_REROUTE if alternative is safer
    - Moderate delay prob (≥50%) → WEAK_REROUTE if time savings ≥5 mins
    - Bad weather/traffic → CONDITIONAL_REROUTE (offer safer alternative)
    - Low delay prob → STICK_PRIMARY

    **Response:**
    - decision: STICK_PRIMARY, WEAK_REROUTE, STRONG_REROUTE, or CONDITIONAL_REROUTE
    - confidence: 0.0-1.0
    - reasoning: Explanation of the decision
    - routes: All calculated routes
    """
    try:
        optimizer = get_optimizer()
        decision_agent = get_decision_agent()

        # Load network if needed
        if optimizer.G is None:
            logger.info("Loading street network for routing...")
            success = optimizer.load_network(network_type="drive")
            if not success:
                raise HTTPException(status_code=503, detail="Failed to load routing network")

        # Calculate routes
        routes = optimizer.get_all_routes(
            origin_lat=request.origin_lat,
            origin_lon=request.origin_lon,
            dest_lat=request.destination_lat,
            dest_lon=request.destination_lon,
            num_alternatives=2,
            delay_probability=request.delay_probability,
            time_of_day=request.time_of_day,
            weather=request.weather
        )

        if not routes["all_routes"]:
            raise HTTPException(status_code=400, detail="No routes found between coordinates")

        # Make decision
        recommendation = decision_agent.decide(
            primary_route=routes["primary_route"],
            alternate_routes=routes["alternate_routes"],
            delay_probability=request.delay_probability,
            time_of_day=request.time_of_day,
            weather=request.weather,
            user_preference=request.user_preference
        )

        return {
            "recommendation": recommendation.to_dict(),
            "routes": routes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reroute recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decision-summary", summary="Decision statistics")
async def get_decision_summary():
    """Get summary of recent rerouting decisions"""
    decision_agent = get_decision_agent()
    return decision_agent.get_decision_summary()
