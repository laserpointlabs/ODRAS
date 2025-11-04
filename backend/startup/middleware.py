"""
Middleware configuration module.
"""

import logging

logger = logging.getLogger(__name__)


def configure_middleware(redis_client) -> None:
    """
    Configure application middleware.
    
    Args:
        redis_client: Redis client for session management
    """
    print("🔥 Step 9: Configuring middleware...")
    logger.info("🔧 Configuring middleware...")
    
    from ..middleware.session_capture import set_global_redis_client
    
    set_global_redis_client(redis_client)
    print("✅ Middleware configured with Redis client")
