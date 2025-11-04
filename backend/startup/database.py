"""
Database initialization module.

Handles database schema verification and setup.
"""

import logging

from ..services.config import Settings

logger = logging.getLogger(__name__)


async def initialize_database(settings: Settings):
    """
    Initialize database connection and ensure schema.
    
    Args:
        settings: Application settings.
        
    Returns:
        Initialized DatabaseService instance.
    """
    print("🔥 Step 2: Initializing database...")
    logger.info("🔥 Step 2: Initializing database...")
    
    try:
        from ..services.db import DatabaseService
        db = DatabaseService(settings)
        print(f"✅ Database connected to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
        logger.info(f"Database connected successfully to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}")
        
        print("🔥 Step 2.1: Verifying RAG SQL-first tables...")
        logger.info("🔧 Verifying RAG SQL-first tables...")
        from ..db.init import ensure_rag_schema_from_settings
        if ensure_rag_schema_from_settings(settings):
            print("✅ RAG SQL-first tables verified/created")
        else:
            print("ℹ️  RAG SQL-first tables already exist (from schema)")
        
        return db
    except Exception as e:
        logger.error(f"Database connection or schema verification failed: {e}")
        print(f"❌ Database connection or schema verification failed: {e}")
        raise  # Re-raise to halt startup if DB is critical
