"""Analytics model."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Analytics(Base):
    """Analytics model for trip performance data."""
    
    __tablename__ = "analytics"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), unique=True, nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False, index=True)
    
    # Predictions
    predicted_delay_minutes = Column(Integer)
    actual_delay_minutes = Column(Integer)
    
    # Costs
    trip_cost = Column(Float, nullable=False)
    fuel_cost = Column(Float)
    toll_cost = Column(Float)
    driver_earnings = Column(Float)
    
    # Performance
    efficiency_score = Column(Float)  # 0-100
    on_time_percentage = Column(Float)  # 0-100
    route_optimality_score = Column(Float)  # 0-100 (actual vs optimal distance)
    
    # Distance
    total_distance_km = Column(Float)
    optimal_distance_km = Column(Float)
    
    # Time
    total_time_minutes = Column(Integer)
    driving_time_minutes = Column(Integer)
    idle_time_minutes = Column(Integer)
    
    # Vehicle metrics
    average_speed_kmh = Column(Float)
    max_speed_kmh = Column(Float)
    harsh_braking_count = Column(Integer, default=0)
    harsh_acceleration_count = Column(Integer, default=0)
    
    # Environmental
    estimated_carbon_emissions_kg = Column(Float)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    trip = relationship("Trip", back_populates="analytics")
    driver = relationship("Driver", foreign_keys=[driver_id])

    def __repr__(self):
        return f"<Analytics for Trip {self.trip_id}>"
