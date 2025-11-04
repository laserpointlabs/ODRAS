"""
FastAPI Application Factory

Creates and configures the FastAPI application instance.
This centralizes app creation and configuration.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.middleware.session_capture import SessionCaptureMiddleware


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(title="ODRAS API", version="0.1.0")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Add middleware (redis_client will be configured during startup)
    app.add_middleware(SessionCaptureMiddleware, redis_client=None)
    
    return app
