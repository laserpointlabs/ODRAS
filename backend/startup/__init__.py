"""
Startup module for ODRAS application initialization.

This module handles all application startup logic including:
- Database initialization
- Service initialization
- DAS initialization
- Event system setup
- Middleware configuration
- Router registration
"""

from .initialize import initialize_application
from .database import initialize_database
from .services import initialize_services
from .training_data import initialize_training_data
from .das import initialize_das
from .events import initialize_events
from .middleware import configure_middleware
from .routers import register_routers

__all__ = [
    "initialize_application",
    "initialize_database",
    "initialize_services",
    "initialize_training_data",
    "initialize_das",
    "initialize_events",
    "configure_middleware",
    "register_routers",
]
