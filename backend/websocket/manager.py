"""
WebSocket Connection Manager
Handles WebSocket connections and broadcasting of real-time updates
"""

import json
from typing import Dict, Set, List
from fastapi import WebSocket
from datetime import datetime, timezone
from backend.websocket.redis_bridge import RedisBridge


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Active connections: {room_id: set(WebSocket)}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # User connections: {user_id: set(WebSocket)}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Reverse lookup for cleanup
        self.connection_users: Dict[WebSocket, str] = {}
        # Driver tracking: {driver_id: {trip_id, last_location, timestamp}}
        self.driver_tracking: Dict[str, dict] = {}
        self.redis_bridge = RedisBridge()

    async def startup(self):
        """Initialize optional cross-instance fanout resources."""
        await self.redis_bridge.startup(self)

    async def shutdown(self):
        """Shutdown optional fanout resources."""
        await self.redis_bridge.shutdown()
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        
        self.active_connections[room_id].add(websocket)
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
    
    def disconnect(self, websocket: WebSocket, room_id: str, user_id: str = None):
        """Close a WebSocket connection"""
        resolved_user_id = user_id or self.connection_users.get(websocket)

        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        if resolved_user_id and resolved_user_id in self.user_connections:
            self.user_connections[resolved_user_id].discard(websocket)
            if not self.user_connections[resolved_user_id]:
                del self.user_connections[resolved_user_id]

        if websocket in self.connection_users:
            del self.connection_users[websocket]
        
        # Clean up driver tracking if driver disconnects
        if resolved_user_id and resolved_user_id in self.driver_tracking:
            del self.driver_tracking[resolved_user_id]
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict,
        exclude_user: str = None,
        publish: bool = True,
    ):
        """Broadcast message to all users in a room"""
        if publish:
            await self.redis_bridge.publish_room(room_id, message)

        if room_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[room_id]:
            try:
                # Check if we should exclude this user
                if exclude_user:
                    # We need a way to track which user owns which connection
                    # For now, send to all
                    pass
                
                await connection.send_json(message)
            except Exception as e:
                # Connection closed or error
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.active_connections[room_id].discard(connection)
            user_id = self.connection_users.get(connection)
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            if connection in self.connection_users:
                del self.connection_users[connection]
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to a specific user"""
        if user_id in self.user_connections:
            disconnected = set()
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            for connection in disconnected:
                self.user_connections[user_id].discard(connection)
                if connection in self.connection_users:
                    del self.connection_users[connection]

            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def broadcast_location_update(
        self,
        trip_id: str,
        driver_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: float = None,
        heading: float = None,
        timestamp: str = None
    ):
        """Broadcast driver location update to all interested parties"""
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        message = {
            "type": "location_update",
            "trip_id": trip_id,
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": speed_kmh,
            "heading": heading,
            "timestamp": timestamp
        }
        
        # Update driver tracking
        if driver_id not in self.driver_tracking:
            self.driver_tracking[driver_id] = {}
        
        self.driver_tracking[driver_id].update({
            "trip_id": trip_id,
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": speed_kmh,
            "heading": heading,
            "timestamp": timestamp
        })
        
        # Broadcast to trip room
        await self.broadcast_to_room(f"trip_{trip_id}", message)
    
    async def broadcast_trip_status_update(
        self,
        trip_id: str,
        status: str,
        estimated_arrival: str = None,
        estimated_delay_minutes: int = None
    ):
        """Broadcast trip status change"""
        message = {
            "type": "trip_status_update",
            "trip_id": trip_id,
            "status": status,
            "estimated_arrival": estimated_arrival,
            "estimated_delay_minutes": estimated_delay_minutes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_room(f"trip_{trip_id}", message)
    
    async def broadcast_driver_status_update(
        self,
        driver_id: str,
        status: str
    ):
        """Broadcast driver status change"""
        message = {
            "type": "driver_status_update",
            "driver_id": driver_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast to driver room
        await self.broadcast_to_room(f"driver_{driver_id}", message)
    
    async def broadcast_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        trip_id: str = None,
        data: dict = None
    ):
        """Send notification to a specific user"""
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "trip_id": trip_id,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_to_user(user_id, notification)
    
    def get_active_drivers(self) -> List[dict]:
        """Get list of currently active drivers with their tracking info"""
        return [
            {
                "driver_id": driver_id,
                **tracking_info
            }
            for driver_id, tracking_info in self.driver_tracking.items()
        ]
    
    def get_driver_location(self, driver_id: str) -> dict:
        """Get current location of a driver"""
        return self.driver_tracking.get(driver_id, {})
    
    async def close_room(self, room_id: str):
        """Close all connections in a room"""
        if room_id in self.active_connections:
            for connection in list(self.active_connections[room_id]):
                try:
                    await connection.close()
                except Exception:
                    pass
            
            del self.active_connections[room_id]


# Global connection manager instance
manager = ConnectionManager()
