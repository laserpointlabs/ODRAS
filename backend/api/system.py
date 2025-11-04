"""
System Configuration API Module

Handles system-level configuration and status endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from backend.api.core import get_user, get_db_service
from backend.services.config import Settings
from backend.services.db import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/installation/config")
def get_installation_config(user=Depends(get_user)):
    """Get installation configuration"""
    settings = Settings()
    return {
        "camunda_base_url": settings.camunda_base_url,
        "postgres_host": settings.postgres_host,
        "postgres_port": settings.postgres_port,
        "postgres_database": settings.postgres_database,
    }


@router.get("/system/db-pool-status")
async def get_db_pool_status(user=Depends(get_user)):
    """Get database connection pool status for monitoring."""
    try:
        db = get_db_service()
        if hasattr(db, 'get_pool_status'):
            return db.get_pool_status()
        else:
            return {"error": "Pool status not available"}
    except Exception as e:
        return {"error": str(e)}

