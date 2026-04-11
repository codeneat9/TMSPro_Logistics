"""
WebSocket Handlers
Handles WebSocket connection logic for real-time features
"""

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio
from backend.websocket.manager import manager
from backend.services.auth import AuthService
from backend.services.locations import LocationsService
from backend.config import settings


def _validate_coordinates(latitude, longitude) -> None:
    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude are required")
    if latitude < -90 or latitude > 90:
        raise ValueError("latitude out of range")
    if longitude < -180 or longitude > 180:
        raise ValueError("longitude out of range")


async def handle_trip_tracking(
    websocket: WebSocket,
    trip_id: str,
    user_id: str,
    db: Session
):
    """
    Handle WebSocket connection for trip tracking
    Allows customers and drivers to track trip in real-time
    """
    await manager.connect(websocket, f"trip_{trip_id}", user_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "timeout", "message": "idle timeout"})
                break
            
            # Handle different message types
            if data.get("type") == "location_update":
                # Driver sending location update
                latitude = data.get("latitude")
                longitude = data.get("longitude")
                speed_kmh = data.get("speed_kmh")
                heading = data.get("heading")

                try:
                    _validate_coordinates(latitude, longitude)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                
                # Record location
                LocationsService.record_location(
                    db=db,
                    trip_id=trip_id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=speed_kmh,
                    heading=heading
                )
                
                # Broadcast to all in trip room
                await manager.broadcast_location_update(
                    trip_id=trip_id,
                    driver_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=speed_kmh,
                    heading=heading
                )
            
            elif data.get("type") == "get_active_drivers":
                # Customer requesting list of active drivers
                drivers = manager.get_active_drivers()
                await websocket.send_json({
                    "type": "active_drivers",
                    "drivers": drivers
                })
            
            elif data.get("type") == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, f"trip_{trip_id}", user_id)
    except Exception:
        manager.disconnect(websocket, f"trip_{trip_id}", user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


async def handle_driver_tracking(
    websocket: WebSocket,
    driver_id: str,
    user_id: str,
    db: Session
):
    """
    Handle WebSocket connection for driver real-time tracking
    Allows drivers to stream their location and receive updates
    """
    await manager.connect(websocket, f"driver_{driver_id}", user_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "timeout", "message": "idle timeout"})
                break
            
            if data.get("type") == "location_stream":
                # Driver sending continuous location updates
                trip_id = data.get("trip_id")
                latitude = data.get("latitude")
                longitude = data.get("longitude")
                speed_kmh = data.get("speed_kmh")
                heading = data.get("heading")

                try:
                    _validate_coordinates(latitude, longitude)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                
                # Record location
                LocationsService.record_location(
                    db=db,
                    trip_id=trip_id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=speed_kmh,
                    heading=heading
                )
                
                # Broadcast location update
                await manager.broadcast_location_update(
                    trip_id=trip_id,
                    driver_id=driver_id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=speed_kmh,
                    heading=heading
                )
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "location_received",
                    "trip_id": trip_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            elif data.get("type") == "status_update":
                # Driver status change
                status = data.get("status")
                await manager.broadcast_driver_status_update(driver_id, status)
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, f"driver_{driver_id}", user_id)
    except Exception:
        manager.disconnect(websocket, f"driver_{driver_id}", user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


async def handle_notifications(
    websocket: WebSocket,
    user_id: str
):
    """
    Handle WebSocket connection for user notifications
    Allows users to receive real-time notifications
    """
    await manager.connect(websocket, f"notifications_{user_id}", user_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "timeout", "message": "idle timeout"})
                break
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "subscribe":
                # User confirming subscription
                await websocket.send_json({
                    "type": "subscription_confirmed",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, f"notifications_{user_id}", user_id)
    except Exception:
        manager.disconnect(websocket, f"notifications_{user_id}", user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


def parse_token(token: str) -> str:
    """Extract user_id from JWT token"""
    try:
        payload = AuthService.verify_token(token)
        if payload:
            return str(payload.get("sub"))
        return None
    except Exception:
        return None
