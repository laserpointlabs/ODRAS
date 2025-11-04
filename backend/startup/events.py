"""
Event system initialization module.

Handles semantic event capture and SQL-first event integration.
"""

import logging

from ..services.config import Settings

logger = logging.getLogger(__name__)


async def initialize_events(settings: Settings, redis_client) -> None:
    """
    Initialize event capture systems.
    
    Args:
        settings: Application settings
        redis_client: Redis client for event processing
    """
    print("🔥 Step 10: Initializing semantic capture...")
    logger.info("📊 Initializing semantic capture...")
    
    from ..services.semantic_event_capture import initialize_semantic_capture
    
    await initialize_semantic_capture(redis_client)
    print("✅ Semantic capture initialized")
    
    print("🔥 Step 11: Setting up event routing...")
    logger.info("🎯 Setting up SQL-first event system...")
    
    try:
        # Initialize SQL-first event capture WITHOUT adding middleware (already added during app init)
        from ..services.sql_first_event_integration import initialize_sql_first_event_capture_only
        from ..services.qdrant_service import QdrantService
        from ..services.sql_first_thread_manager import SqlFirstThreadManager
        
        qdrant_service = QdrantService(settings)
        sql_first_manager = SqlFirstThreadManager(settings, qdrant_service)
        
        # Initialize event capture without middleware (middleware already exists)
        initialize_sql_first_event_capture_only(
            sql_first_manager=sql_first_manager,
            redis_client=redis_client
        )
        
        print(f"✅ SQL-first event capture initialized")
        logger.info("✅ SQL-first event capture initialized")
    except Exception as e:
        logger.error(f"Failed to initialize SQL-first event capture: {e}")
        print(f"⚠️  SQL-first event capture failed: {e}")
