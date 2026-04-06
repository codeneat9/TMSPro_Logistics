"""Feedback model."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Feedback(Base):
    """Feedback model for trip ratings and reviews."""
    
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    
    # Rating
    rating = Column(Float, nullable=False)  # 1-5 stars
    
    # Review
    comment = Column(String)
    
    # Categories
    punctuality_rating = Column(Integer)  # 1-5
    vehicle_cleanliness_rating = Column(Integer)  # 1-5
    driving_quality_rating = Column(Integer)  # 1-5
    
    # Issues reported
    issues = Column(String)  # Comma-separated: "late", "rude", "damaged", etc.
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="feedback")
    user = relationship("User", foreign_keys=[user_id])
    driver = relationship("Driver", foreign_keys=[driver_id])

    def __repr__(self):
        return f"<Feedback for Trip {self.trip_id}: {self.rating}★>"
