"""
WebSocket Routes
Provides WebSocket endpoints for real-time features
"""

from fastapi import APIRouter, WebSocket, Query, Depends, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.websocket.handlers import (
    handle_trip_tracking,
    handle_driver_tracking,
  handle_notifications,
)
from backend.services.auth import AuthService
from backend.models.user import User, UserRole
from backend.models.driver import Driver
from backend.models.trip import Trip

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)


def _get_authenticated_user(token: str, db: Session) -> User | None:
  payload = AuthService.verify_token(token)
  if not payload:
    return None

  user_id = payload.get("sub")
  if not user_id:
    return None

  return db.query(User).filter(User.id == str(user_id)).first()


@router.websocket("/trip/{trip_id}")
async def websocket_trip_tracking(
    websocket: WebSocket,
    trip_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time trip tracking
    
    Connect to: ws://localhost:8000/ws/trip/{trip_id}?token={jwt_token}
    
    Message types:
    - location_update: Send driver location
      {"type": "location_update", "latitude": 40.7128, "longitude": -74.0060, "speed_kmh": 45, "heading": 90}
    - get_active_drivers: Get list of active drivers
      {"type": "get_active_drivers"}
    - ping: Keep-alive
      {"type": "ping"}
    
    Server broadcasts:
    - location_update: Driver location changed
    - trip_status_update: Trip status changed
    - pong: Response to ping
    """
    user = _get_authenticated_user(token, db)
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return

    is_admin_like = user.role in [UserRole.ADMIN, UserRole.COMPANY]
    is_customer_owner = str(trip.user_id) == str(user.id)
    is_assigned_driver = bool(trip.driver_id) and str(trip.driver_id) == str(user.id)
    if not (is_admin_like or is_customer_owner or is_assigned_driver):
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return

    await handle_trip_tracking(websocket, trip_id, str(user.id), db)


@router.websocket("/driver/{driver_id}")
async def websocket_driver_tracking(
    websocket: WebSocket,
    driver_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for driver real-time location streaming
    
    Connect to: ws://localhost:8000/ws/driver/{driver_id}?token={jwt_token}
    
    Message types:
    - location_stream: Send continuous location updates
      {"type": "location_stream", "trip_id": "trip_123", "latitude": 40.7128, "longitude": -74.0060, "speed_kmh": 45, "heading": 90}
    - status_update: Send driver status change
      {"type": "status_update", "status": "online"}
    - ping: Keep-alive
      {"type": "ping"}
    
    Server broadcasts:
    - location_received: Acknowledgment of location update
    - driver_status_update: Driver status changed
    - pong: Response to ping
    """
    user = _get_authenticated_user(token, db)
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    is_admin_like = user.role in [UserRole.ADMIN, UserRole.COMPANY]
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return

    owns_driver_channel = str(driver.user_id) == str(user.id)
    if not (is_admin_like or owns_driver_channel):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await handle_driver_tracking(websocket, driver_id, str(user.id), db)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
  token: str = Query(...),
  db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for user notifications
    
    Connect to: ws://localhost:8000/ws/notifications?token={jwt_token}
    
    Message types:
    - ping: Keep-alive
      {"type": "ping"}
    - subscribe: Confirm subscription to notifications
      {"type": "subscribe"}
    
    Server broadcasts:
    - notification: New notification
      {"type": "notification", "notification_type": "trip_accepted", "title": "...", "message": "..."}
    - pong: Response to ping
    """
    user = _get_authenticated_user(token, db)
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await handle_notifications(websocket, str(user.id))


@router.websocket("/trackings/active")
async def websocket_active_drivers(
    websocket: WebSocket,
  token: str = Query(...),
  db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for viewing active drivers in real-time
    
    Connect to: ws://localhost:8000/ws/trackings/active?token={jwt_token}
    
    Server broadcasts active drivers every few seconds:
    - active_drivers: List of currently tracked drivers
      {"type": "active_drivers", "drivers": [{"driver_id": "...", "latitude": 40.7128, "longitude": -74.0060, ...}]}
    """
    user = _get_authenticated_user(token, db)
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Restrict global active-driver stream to customer/company/admin roles.
    if user.role not in [UserRole.CUSTOMER, UserRole.COMPANY, UserRole.ADMIN]:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return
    
    from backend.websocket.manager import manager
    import asyncio
    
    await manager.connect(websocket, "active_trackers", str(user.id))
    
    try:
        while True:
            # Send active drivers list every 5 seconds
            await asyncio.sleep(5)
            drivers = manager.get_active_drivers()
            
            try:
                await websocket.send_json({
                    "type": "active_drivers",
                    "drivers": drivers,
                    "count": len(drivers)
                })
            except Exception:
                break
    
    except Exception:
        manager.disconnect(websocket, "active_trackers", str(user.id))
        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
