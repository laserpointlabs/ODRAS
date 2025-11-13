"""
Service initialization module.

Handles initialization of core services like RAG, Redis, etc.
"""

import logging
import redis.asyncio as redis
from typing import Tuple, Optional

from ..services.config import Settings
from ..rag.core.modular_rag_service import ModularRAGService
from ..services.system_indexer import SystemIndexer
from ..services.indexing_service_interface import IndexingServiceInterface

logger = logging.getLogger(__name__)


async def initialize_services(settings: Settings, db) -> Tuple[ModularRAGService, redis.Redis]:
    """
    Initialize core application services.
    
    Args:
        settings: Application settings.
        db: Initialized DatabaseService instance.
        
    Returns:
        A tuple containing the ModularRAGService instance and the Redis client.
    """
    print("🔥 Step 5: Creating service instances...")
    logger.info("📦 Creating service instances...")
    
    # Initialize indexing service if enabled
    indexing_service: Optional[IndexingServiceInterface] = None
    indexing_enabled = getattr(settings, 'system_indexing_enabled', 'true').lower() == 'true'
    
    if indexing_enabled:
        try:
            print("🔥 Step 5.1: Creating system indexer...")
            indexing_service = SystemIndexer(settings)
            logger.info("System indexer initialized")
            print("✅ System indexer created")
        except Exception as e:
            logger.warning(f"Failed to initialize system indexer: {e}")
            print(f"⚠️  System indexer initialization failed: {e}")
            indexing_service = None
    
    print("🔥 Step 6: Creating modular RAG service...")
    rag_service = ModularRAGService(settings, db_service=db, indexing_service=indexing_service)
    print("✅ Modular RAG service created")
    
    print("🔥 Step 7: Connecting to Redis...")
    logger.info("🔗 Connecting to Redis...")
    redis_url = settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379"
    redis_client = redis.from_url(redis_url)
    print("✅ Redis client created")
    
    # Start connection pool monitoring task
    try:
        from ..services.db_monitor import start_db_monitor
        start_db_monitor(db)
        print("✅ Database connection pool monitor started")
        logger.info("✅ Database connection pool pool monitor started")
    except Exception as e:
        print(f"⚠️  Failed to start database monitor: {e}")
        logger.warning(f"Failed to start database monitor: {e}")
    
    return rag_service, redis_client
