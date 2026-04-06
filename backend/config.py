"""Application configuration and environment variables."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "TMSPro Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production

    # Database - Supabase PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/tmspro"
    )

    # Redis - Upstash
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )

    # Firebase
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY", "")
    FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 30

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:19000",  # Expo
    ]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_HEADERS: list = ["*"]

    # WebSocket
    WEBSOCKET_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
    ]

    # API
    API_PREFIX: str = "/api"
    API_TITLE: str = "TMSPro API"
    API_DESCRIPTION: str = "Real-time Transportation Management System API"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Optional services
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN", None)
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER", None)
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)

    # Feature flags
    ENABLE_LOCATION_STREAMING: bool = True
    ENABLE_REROUTE_RECOMMENDATIONS: bool = True
    ENABLE_DELAY_PREDICTIONS: bool = True
    ENABLE_GEOFENCING: bool = True

    class Config:
        env_file = ".env.backend"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export for convenience
settings = get_settings()
