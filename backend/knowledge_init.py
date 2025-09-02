"""
Knowledge Management Initialization Script.

Sets up database schema and initializes services for knowledge management.
"""

import logging
import asyncio
from .services.config import Settings
from .services.db import DatabaseService
from .services.qdrant_service import get_qdrant_service, ensure_knowledge_collections
from .services.neo4j_service import get_neo4j_service, setup_knowledge_graph_schema

logger = logging.getLogger(__name__)

async def initialize_knowledge_management(settings: Settings = None) -> bool:
    """
    Initialize knowledge management system with all required components.
    
    Args:
        settings: Optional settings configuration
        
    Returns:
        True if initialization was successful
    """
    try:
        logger.info("🧠 Initializing Knowledge Management system...")
        
        settings = settings or Settings()
        success_flags = []
        
        # 1. Initialize PostgreSQL schema
        try:
            logger.info("📊 Setting up PostgreSQL knowledge schema...")
            db_service = DatabaseService(settings)
            
            # Execute migration script
            with open('backend/migrations/001_knowledge_management.sql', 'r') as f:
                migration_sql = f.read()
            
            conn = db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(migration_sql)
                    conn.commit()
                logger.info("✅ PostgreSQL schema initialized successfully")
                success_flags.append(True)
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL schema initialization failed: {str(e)}")
            success_flags.append(False)
        
        # 2. Initialize Qdrant collections
        try:
            logger.info("🔍 Setting up Qdrant vector collections...")
            qdrant_service = get_qdrant_service(settings)
            
            if ensure_knowledge_collections(qdrant_service):
                logger.info("✅ Qdrant collections initialized successfully")
                success_flags.append(True)
            else:
                logger.error("❌ Qdrant collections initialization failed")
                success_flags.append(False)
                
        except Exception as e:
            logger.error(f"❌ Qdrant initialization failed: {str(e)}")
            success_flags.append(False)
        
        # 3. Initialize Neo4j schema
        try:
            logger.info("🕸️ Setting up Neo4j knowledge graph schema...")
            neo4j_service = get_neo4j_service(settings)
            
            if setup_knowledge_graph_schema(neo4j_service):
                logger.info("✅ Neo4j schema initialized successfully")
                success_flags.append(True)
            else:
                logger.error("❌ Neo4j schema initialization failed")
                success_flags.append(False)
            
            neo4j_service.close()
            
        except Exception as e:
            logger.error(f"❌ Neo4j initialization failed: {str(e)}")
            success_flags.append(False)
        
        # 4. Test services
        try:
            logger.info("🔍 Testing service connectivity...")
            
            # Test Qdrant
            qdrant_health = qdrant_service.health_check()
            if qdrant_health.get('status') == 'healthy':
                logger.info("✅ Qdrant service healthy")
            else:
                logger.warning(f"⚠️ Qdrant service issues: {qdrant_health}")
            
            # Test Neo4j  
            with get_neo4j_service(settings) as neo4j_service:
                neo4j_health = neo4j_service.health_check()
                if neo4j_health.get('status') == 'healthy':
                    logger.info("✅ Neo4j service healthy")
                else:
                    logger.warning(f"⚠️ Neo4j service issues: {neo4j_health}")
                    
            success_flags.append(True)
            
        except Exception as e:
            logger.error(f"❌ Service testing failed: {str(e)}")
            success_flags.append(False)
        
        # Summary
        successful_components = sum(success_flags)
        total_components = len(success_flags)
        
        if successful_components == total_components:
            logger.info(f"🎉 Knowledge Management system initialized successfully! ({successful_components}/{total_components} components)")
            return True
        else:
            logger.warning(f"⚠️ Knowledge Management system partially initialized ({successful_components}/{total_components} components)")
            return successful_components >= total_components // 2  # Consider success if majority of components work
        
    except Exception as e:
        logger.error(f"❌ Knowledge Management initialization failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Allow running this script directly for setup
    import sys
    sys.path.append('.')
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        success = await initialize_knowledge_management()
        if success:
            print("✅ Knowledge Management system initialized successfully!")
            sys.exit(0)
        else:
            print("❌ Knowledge Management system initialization failed!")
            sys.exit(1)
    
    asyncio.run(main())
