"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.config import settings
from backend.database import init_db
from backend.routes import auth, trips, drivers, locations, routes, websocket, notifications
from backend.websocket.manager import manager

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    try:
        await manager.startup()
    except Exception as e:
        logger.warning(f"WebSocket manager startup warning: {e}")
    
    yield
    
    # Shutdown
    try:
        await manager.shutdown()
    except Exception as e:
        logger.warning(f"WebSocket manager shutdown warning: {e}")

    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Include routers
app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(drivers.router)
app.include_router(locations.router)
app.include_router(routes.router)
app.include_router(websocket.router)
app.include_router(notifications.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "api_docs": "/docs",
        "version": settings.APP_VERSION,
    }


# Global exception handler
@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request, exc):
    """Handle database exceptions."""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Database error", "detail": "An error occurred while processing your request"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


logger.info(f"FastAPI application initialized: {settings.APP_NAME} ({settings.ENVIRONMENT})")
