"""
DAS (Digital Assistant System) initialization module.
"""

import logging

logger = logging.getLogger(__name__)


async def initialize_das(settings, services, db) -> None:
    """
    Initialize the Digital Assistant System.
    
    Args:
        settings: Application settings.
        services: Tuple of initialized services (e.g., RAGService, Redis client).
        db: Database service instance.
    """
    print("🔥 Step 8: Initializing DAS...")
    logger.info("🤖 Initializing DAS...")
    try:
        from ..api.das import initialize_das_engine
        await initialize_das_engine()
        print("✅ DAS initialized")
    except Exception as e:
        print(f"💥 DAS INITIALIZATION FAILED: {e}")
        logger.error(f"❌ Failed to initialize DAS engine: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Don't fail startup if DAS initialization fails, but log it
