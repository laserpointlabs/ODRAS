"""
Main application initialization orchestrator.

Coordinates all startup activities in the correct order.
"""

import logging

from fastapi import FastAPI

from ..services.config import Settings
from .database import initialize_database
from .services import initialize_services
from .das import initialize_das
from .events import initialize_events
from .middleware import configure_middleware

logger = logging.getLogger(__name__)


async def initialize_application(app: FastAPI) -> None:
    """
    Initialize the entire ODRAS application.
    
    This function orchestrates all startup activities:
    1. Load settings
    2. Initialize database
    3. Initialize services (RAG, Redis)
    4. Initialize DAS
    5. Configure middleware
    6. Initialize event systems
    
    Args:
        app: FastAPI application instance
    """
    print("🔥 STARTUP EVENT TRIGGERED")
    logger.info("🔥 STARTUP EVENT TRIGGERED")
    
    try:
        print("🔥 Step 1: Loading settings...")
        logger.info("🔥 Step 1: Loading settings...")
        settings = Settings()  # loads env
        print("✅ Settings loaded")
        
        # Step 2: Initialize database
        await initialize_database(settings)
        
        print("🔥 Step 3: Starting DAS initialization...")
        logger.info("🚀 Starting DAS initialization...")
        
        print("🔥 Step 4: Importing services...")
        from ..services.rag_service import RAGService
        import redis.asyncio as redis
        print("✅ Services imported")
        
        print("🔥 Step 5: Creating service instances...")
        logger.info("📦 Creating service instances...")
        print("✅ Settings instance created")
        
        # Step 6-7: Initialize services
        rag_service, redis_client = await initialize_services(settings)
        
        # Step 8: Initialize DAS
        await initialize_das()
        
        # Step 9: Configure middleware
        configure_middleware(redis_client)
        
        # Step 10-11: Initialize events
        await initialize_events(settings, redis_client)
        
        print("🎉 Application initialization complete!")
        logger.info("🎉 Application initialization complete!")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
