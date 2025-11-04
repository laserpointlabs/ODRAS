"""
ODRAS Main Application Entry Point

This module has been refactored to use modular components:
- backend/app_factory.py: Application creation
- backend/startup/: Startup initialization modules
- backend/api/core.py: Core API endpoints (auth, health, sync, projects)
- backend/api/*: Feature-specific API routers
"""

import logging

from backend.app_factory import create_app
from backend.startup import initialize_application, register_routers
from backend.api.core import set_db_instance
from backend.services.config import Settings
from backend.services.db import DatabaseService

logger = logging.getLogger(__name__)

# Create application using factory
app = create_app()

# Initialize database connection early (before routers need it)
settings = Settings()
try:
    db = DatabaseService(settings)
    logger.info(
        f"Database connected successfully to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
    )
    # Set database instance for core API
    set_db_instance(db)
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    logger.error(
        f"Database settings: host={settings.postgres_host}, port={settings.postgres_port}, "
        f"database={settings.postgres_database}, user={settings.postgres_user}"
    )
    # Database will be initialized in startup event handler
    set_db_instance(None)

# Register all API routers
register_routers(app)


# Startup event handler
@app.on_event("startup")
async def on_startup():
    """Initialize application on startup"""
    await initialize_application(app)


def run():
    """Run the application"""
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
