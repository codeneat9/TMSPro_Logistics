"""
Routes Optimization Endpoints
Provides route generation, alternatives, and predictions
"""

import requests
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import (
    RouteCreate,
    RouteResponse,
    AgentDecisionRequest,
    AgentDecisionResponse,
    AgentDecisionApplyRequest,
    AgentDecisionApplyResponse,
)
from backend.services.routes import RoutesService
from backend.services.decision_agent import DecisionAgentService
from backend.middleware.auth import get_current_user
from backend.models.user import User

router = APIRouter(
    prefix="/api/routes",
    tags=["routes"],
)


@router.get('/address-suggestions', response_model=dict)
async def address_suggestions(
    q: str = Query(..., min_length=2, description='Partial address text'),
    country: str = Query('in', description='Country code for filtering (default: in)'),
):
    """Fetch OSM address suggestions for typeahead inputs using Photon."""
    try:
        response = requests.get(
            'https://photon.komoot.io/api/',
            params={
                'limit': 8,
                'q': q,
            },
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Address provider failed: {exc}')

    items = []
    features = payload.get('features', []) if isinstance(payload, dict) else []
    normalized_country = (country or '').lower()

    for feature in features:
        props = feature.get('properties', {})
        coords = feature.get('geometry', {}).get('coordinates', [None, None])
        if not isinstance(coords, list) or len(coords) < 2:
            continue

        display_parts = [
            props.get('name'),
            props.get('city'),
            props.get('state'),
            props.get('country'),
        ]
        display_name = ', '.join([part for part in display_parts if part])
        place_id = str(props.get('osm_id', ''))

        try:
            lon = float(coords[0])
            lat = float(coords[1])
        except (TypeError, ValueError):
            continue

        country_code = str(props.get('countrycode', '')).lower()

        items.append(
            {
                'id': f'geo-{place_id}',
                'name': display_name,
                'city': props.get('city') or props.get('name') or q,
                'latitude': lat,
                'longitude': lon,
                'country_code': country_code,
            }
        )

    if normalized_country:
        in_country = [item for item in items if item.get('country_code') == normalized_country]
        if in_country:
            items = in_country

    return {'items': items, 'total': len(items), 'query': q}


def _parse_coordinates(value: str) -> tuple[float, float]:
    """Parse coordinates from a `lat,lng` query parameter."""
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise ValueError("Coordinates must be in format: lat,lng")
    lat = float(parts[0])
    lng = float(parts[1])
    if lat < -90 or lat > 90 or lng < -180 or lng > 180:
        raise ValueError("Coordinates out of range")
    return lat, lng


@router.get("", response_model=dict)
async def get_route_options(
    origin: str = Query(..., description="Origin as lat,lng"),
    destination: str = Query(..., description="Destination as lat,lng"),
    alternatives: int = Query(2, ge=0, le=3),
):
    """Fetch optimal route and alternatives using OSRM with fallback."""
    try:
        origin_lat, origin_lng = _parse_coordinates(origin)
        destination_lat, destination_lng = _parse_coordinates(destination)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    options = RoutesService.fetch_routes(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        alternatives=alternatives,
    )

    optimal = next((r for r in options if r.get("route_type") == "optimal"), None)
    alt_items = [r for r in options if r.get("route_type", "").startswith("alternative_")]

    return {
        "optimal": optimal,
        "alternatives": alt_items,
        "total": len(options),
        "origin": origin,
        "destination": destination,
    }


@router.post("", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    route_request: RouteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a route for a trip
    
    - **trip_id**: Trip ID
    - **distance_km**: Distance in kilometers
    - **duration_minutes**: Estimated duration
    - **polyline**: Encoded polyline (Google Maps format)
    - Optional: predicted_delay_minutes, predicted_cost, risk_score
    """
    route = RoutesService.create_route(
        db=db,
        trip_id=route_request.trip_id,
        distance_km=route_request.distance_km,
        duration_minutes=route_request.duration_minutes,
        polyline=route_request.polyline,
        route_type=getattr(route_request, 'route_type', 'optimal'),
        predicted_delay_minutes=getattr(route_request, 'predicted_delay_minutes', 0),
        predicted_cost=getattr(route_request, 'predicted_cost', None),
        risk_score=getattr(route_request, 'risk_score', 0.0)
    )
    
    return route


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: str,
    db: Session = Depends(get_db)
):
    """Get route details"""
    route = RoutesService.get_route(db, route_id)
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    return route


@router.get("/trip/{trip_id}", response_model=dict)
async def get_trip_routes(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """Get all routes for a trip"""
    routes = RoutesService.get_trip_routes(db, trip_id)
    
    optimal = next((r for r in routes if r.route_type == "optimal"), None)
    alternatives = [r for r in routes if r.route_type in ["alternative_1", "alternative_2"]]
    
    return {
        "optimal": optimal,
        "alternatives": alternatives,
        "total": len(routes)
    }


@router.post("/trip/{trip_id}/optimal", response_model=RouteResponse)
async def get_optimal_route(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """Get the optimal route for a trip"""
    route = RoutesService.get_optimal_route(db, trip_id)
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No optimal route found for trip"
        )
    
    return route


@router.post("/trip/{trip_id}/alternatives", response_model=dict)
async def get_alternative_routes(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """Get alternative routes for a trip"""
    alternatives = RoutesService.get_alternative_routes(db, trip_id)
    
    return {
        "items": alternatives,
        "total": len(alternatives)
    }


@router.post("/trip/{trip_id}/select/{route_id}", response_model=dict)
async def select_route(
    trip_id: str,
    route_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Select a specific route for a trip"""
    trip = RoutesService.select_route(db, trip_id, route_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to select route"
        )
    
    return {
        "trip_id": trip.id,
        "selected_route_id": route_id,
        "estimated_delay_minutes": trip.estimated_delay_minutes
    }


@router.post("/predict-delay", response_model=dict)
async def predict_delay(
    trip_id: str = Query(...),
    hour_of_day: int = Query(...),
    day_of_week: int = Query(...),
    distance_km: float = Query(...),
    weather_condition: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Predict delay for a trip
    
    - **hour_of_day**: 0-23
    - **day_of_week**: 0-6 (0=Monday, 6=Sunday)
    - **distance_km**: Distance in kilometers
    - **weather_condition**: Optional (clear, rain, heavy_rain, foggy)
    """
    prediction = RoutesService.predict_delay_profile(
        db=db,
        trip_id=trip_id,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        distance_km=distance_km,
        weather_condition=weather_condition
    )

    return prediction


@router.post("/calculate-risk", response_model=dict)
async def calculate_risk_score(
    trip_id: str = Query(...),
    weather_condition: str = Query(None),
    traffic_condition: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Calculate risk score for a route
    
    - **weather_condition**: Optional (clear, rain, heavy_rain, foggy)
    - **traffic_condition**: Optional (light, moderate, congested)
    
    Returns risk score 0-100
    """
    risk = RoutesService.calculate_risk_score(
        db=db,
        trip_id=trip_id,
        weather_condition=weather_condition,
        traffic_condition=traffic_condition
    )
    
    return {
        "trip_id": trip_id,
        "risk_score": risk
    }


@router.post("/estimate-cost", response_model=dict)
async def estimate_cost(
    distance_km: float = Query(...),
    duration_minutes: int = Query(...),
    vehicle_type: str = Query("standard")
):
    """
    Estimate trip cost
    
    - **distance_km**: Distance in kilometers
    - **duration_minutes**: Estimated duration
    - **vehicle_type**: economy, standard, comfort, premium
    """
    cost = RoutesService.estimate_cost(
        db=None,
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        vehicle_type=vehicle_type
    )
    
    return {
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "vehicle_type": vehicle_type,
        "estimated_cost": cost
    }


@router.post("/agent/decide", response_model=AgentDecisionResponse)
async def decide_route(
    request: AgentDecisionRequest,
    current_user: User = Depends(get_current_user),
):
    """Step 7: Agent-based best route selection and emergency handling."""
    try:
        result = DecisionAgentService.decide(
            route_options=[item.model_dump() for item in request.route_options],
            delay_prediction=request.delay_prediction.model_dump(),
            emergency=request.emergency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return result


@router.post("/agent/decide-and-apply", response_model=AgentDecisionApplyResponse)
async def decide_and_apply_route(
    request: AgentDecisionApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Step 7: Choose and apply route decision to trip with audit persistence."""
    try:
        result = DecisionAgentService.decide_and_apply(
            db=db,
            trip_id=request.trip_id,
            route_options=[item.model_dump() for item in request.route_options],
            delay_prediction=request.delay_prediction.model_dump(),
            emergency=request.emergency,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return result
