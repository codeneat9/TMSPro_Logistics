"""Route model."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Route(Base):
    """Route model for trip alternatives."""
    
    __tablename__ = "routes"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    route_type = Column(String, nullable=False)  # "primary", "alternative_1", "alternative_2"
    
    # Route details
    distance_km = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    polyline = Column(String, nullable=False)  # GeoJSON or encoded polyline
    
    # Predictions
    predicted_delay_minutes = Column(Integer, default=0)
    predicted_cost = Column(Float)
    risk_score = Column(Float)  # 0-1, where 1 is highest risk
    
    # Traffic conditions
    current_traffic_condition = Column(String)  # "clear", "slow", "congested"
    
    # Waypoints
    waypoints_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    trip = relationship("Trip", back_populates="routes")

    def __repr__(self):
        return f"<Route {self.id} - {self.route_type}>"
