"""
Service initialization module.

Handles initialization of core services like RAG, Redis, etc.
"""

import logging
import redis.asyncio as redis
from typing import Tuple

from ..services.config import Settings
from ..services.rag_service import RAGService

logger = logging.getLogger(__name__)


async def initialize_services(settings: Settings) -> Tuple[RAGService, redis.Redis]:
    """
    Initialize core services.
    
    Args:
        settings: Application settings
        
    Returns:
        Tuple of (rag_service, redis_client)
    """
    print("🔥 Step 6: Creating RAG service...")
    rag_service = RAGService(settings)
    print("✅ RAG service created")
    
    print("🔥 Step 7: Connecting to Redis...")
    logger.info("🔗 Connecting to Redis...")
    redis_url = settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379"
    redis_client = redis.from_url(redis_url)
    print("✅ Redis client created")
    
    return rag_service, redis_client
