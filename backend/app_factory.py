"""
FastAPI Application Factory

Creates and configures the FastAPI application instance.
This centralizes app creation and configuration.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.session_capture import SessionCaptureMiddleware


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(title="ODRAS API", version="0.1.0")
    
    # Configure CORS to allow demo pages and frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8082",  # Demo static server
            "http://localhost:8080",  # Visualization server
            "http://localhost:3000",  # Common dev port
            "http://localhost:5173",  # Vite dev server
            "http://localhost:8000",  # ODRAS API itself
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Add middleware (redis_client will be configured during startup)
    app.add_middleware(SessionCaptureMiddleware, redis_client=None)
    
    return app
