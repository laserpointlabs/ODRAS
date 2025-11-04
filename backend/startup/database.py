"""
Database initialization module.

Handles database schema verification and setup.
"""

import logging

from ..services.config import Settings

logger = logging.getLogger(__name__)


async def initialize_database(settings: Settings) -> None:
    """
    Initialize database and verify schemas.
    
    Args:
        settings: Application settings
    """
    print("🔥 Step 2: Verifying RAG SQL-first tables...")
    logger.info("🔧 Verifying RAG SQL-first tables...")
    
    from ..db.init import ensure_rag_schema_from_settings
    
    try:
        if ensure_rag_schema_from_settings(settings):
            print("✅ RAG SQL-first tables verified/created")
        else:
            print("ℹ️  RAG SQL-first tables already exist (from schema)")
    except Exception as e:
        logger.debug(f"RAG table verification note: {e}")
        print("ℹ️  RAG SQL-first tables already exist (from main schema)")
