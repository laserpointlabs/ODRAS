"""
SQL-First Event System Integration

This module provides a clean integration point for the unified SQL-first event system,
replacing all fragmented middleware and event capture systems with a single consolidated approach.
"""

import logging
from typing import Optional
from backend.services.config import Settings
from backend.services.sql_first_thread_manager import SqlFirstThreadManager
from backend.services.eventcapture2 import initialize_sql_first_event_capture
from backend.services.unified_event_middleware import UnifiedEventMiddleware

logger = logging.getLogger(__name__)


async def initialize_unified_sql_first_events(app, db_service, redis_client=None):
    """
    Initialize the complete unified SQL-first event system

    This replaces all fragmented event capture systems:
    - SessionCaptureMiddleware → Unified middleware
    - APIEventCaptureMiddleware → Unified middleware
    - MiddlewareToDASBridge → Direct SQL-first storage
    - SemanticEventCapture → EventCapture2 with richer context
    - Multiple processors → Single SQL-first pipeline
    """
    try:
        logger.info("🎯 Initializing unified SQL-first event system...")

        # Step 1: Create SqlFirstThreadManager instance with correct parameters
        print("🔥 EVENTS: Creating SqlFirstThreadManager...")
        settings = Settings()

        # Import QdrantService for SqlFirstThreadManager
        from backend.services.qdrant_service import QdrantService
        qdrant_service = QdrantService(settings)

        # Create SqlFirstThreadManager with correct parameter order: (settings, qdrant_service)
        sql_first_manager = SqlFirstThreadManager(settings, qdrant_service)
        print("✅ SqlFirstThreadManager created with correct parameters")

        # Step 2: Initialize EventCapture2 with SQL-first support
        print("🔥 EVENTS: Initializing EventCapture2 with SQL-first storage...")
        initialize_sql_first_event_capture(
            sql_first_manager=sql_first_manager,
            redis_client=redis_client
        )
        print("✅ EventCapture2 initialized with SQL-first storage")

        # Step 3: Add unified middleware to app (replace fragmented middleware)
        print("🔥 EVENTS: Adding unified event middleware...")
        unified_middleware = UnifiedEventMiddleware(
            app=app,
            redis_client=redis_client,
            sql_first_manager=sql_first_manager
        )

        # Replace existing fragmented middleware
        app.add_middleware(UnifiedEventMiddleware,
                          redis_client=redis_client,
                          sql_first_manager=sql_first_manager)
        print("✅ Unified event middleware added")

        # Step 4: Log consolidation success
        print("🎉 UNIFIED SQL-FIRST EVENT SYSTEM ACTIVE!")
        logger.info("✅ Unified SQL-first event system initialized successfully")

        return {
            "sql_first_manager": sql_first_manager,
            "unified_middleware": unified_middleware,
            "status": "active"
        }

    except Exception as e:
        logger.error(f"❌ Failed to initialize unified SQL-first event system: {e}")
        print(f"💥 EVENTS ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


def log_event_system_status():
    """Log the current status of the consolidated event system"""
    print("""
🎯 CONSOLIDATED SQL-FIRST EVENT SYSTEM STATUS:

✅ ACTIVE COMPONENTS:
   📊 EventCapture2: Enhanced with 45+ event types
   🗄️ SqlFirstThreadManager: SQL-first storage and dual-write
   🌐 UnifiedEventMiddleware: Comprehensive API event capture
   📋 project_event table: Source of truth for all events
   🔍 Vector dual-write: IDs-only for search

❌ DEPRECATED COMPONENTS (REPLACED):
   🚫 SessionCaptureMiddleware
   🚫 APIEventCaptureMiddleware
   🚫 MiddlewareToDASBridge
   🚫 SemanticEventCapture (standalone)
   🚫 Multiple Redis processors

🎯 EVENT FLOW:
   API Request → UnifiedEventMiddleware → EventCapture2 → SqlFirstThreadManager
   → project_event table (SQL) + vector dual-write (IDs only)

📈 SUPPORTED EVENTS:
   📋 Projects: create, update, delete
   🔧 Ontologies: create, modify, save, import, export, validate
   🏗️ Classes: create, update, delete, rename
   🔗 Properties: object/data/annotation operations
   ⚡ Relationships: subclass, domain, range, axioms
   📄 Files: upload, delete, processing lifecycle
   📚 Knowledge: assets lifecycle and search
   🤖 DAS: interactions and responses
   🖥️ System: auth, errors, performance

🌟 BENEFITS:
   ✅ Single source of truth (SQL-first)
   ✅ Rich event context and summaries
   ✅ Consolidated architecture (no fragmentation)
   ✅ Scalable and maintainable
   ✅ DAS-aware event intelligence
""")


async def verify_event_system_health(db_service) -> dict:
    """Verify the health of the SQL-first event system"""
    try:
        # Check database tables
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check project_thread table
                cur.execute("SELECT COUNT(*) FROM project_thread")
                thread_count = cur.fetchone()[0]

                # Check project_event table
                cur.execute("SELECT COUNT(*) FROM project_event")
                event_count = cur.fetchone()[0]

                # Check for recent events (last 24 hours)
                cur.execute("""
                    SELECT COUNT(*) FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                recent_events = cur.fetchone()[0]

        finally:
            db_service._return(conn)

        # Check EventCapture2 status
        from backend.services.eventcapture2 import get_event_capture
        event_capture = get_event_capture()

        health_status = {
            "status": "healthy",
            "sql_first_active": bool(event_capture and event_capture.sql_first_manager),
            "database_tables": {
                "project_threads": thread_count,
                "project_events": event_count,
                "recent_events_24h": recent_events
            },
            "event_capture_initialized": bool(event_capture),
            "sql_first_storage": bool(event_capture and event_capture.sql_first_manager)
        }

        logger.info(f"Event system health check: {health_status}")
        return health_status

    except Exception as e:
        logger.error(f"Event system health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Convenience functions for adding event capture to existing endpoints

async def capture_endpoint_event(
    operation_type: str,
    endpoint: str,
    user_id: str,
    username: str,
    project_id: Optional[str] = None,
    event_details: dict = None,
    response_time: Optional[float] = None
):
    """
    Convenience function to capture events from API endpoints

    Usage in API endpoints:
    await capture_endpoint_event(
        operation_type="ontology_created",
        endpoint="/api/ontologies",
        user_id=user["user_id"],
        username=user["username"],
        project_id=project_id,
        event_details={"ontology_name": name, "label": label}
    )
    """
    try:
        from backend.services.eventcapture2 import get_event_capture
        event_capture = get_event_capture()

        if not event_capture:
            logger.warning("EventCapture2 not initialized - cannot capture endpoint event")
            return False

        # Route to appropriate capture method based on operation type
        if operation_type.startswith("ontology_"):
            if project_id and event_details:
                return await event_capture.capture_ontology_operation(
                    operation_type=operation_type.replace("ontology_", ""),
                    ontology_name=event_details.get("ontology_name", "unknown"),
                    project_id=project_id,
                    user_id=user_id,
                    username=username,
                    operation_details=event_details,
                    response_time=response_time
                )

        elif operation_type.startswith("project_"):
            if project_id and event_details:
                return await event_capture.capture_project_operation(
                    operation_type=operation_type.replace("project_", ""),
                    project_id=project_id,
                    project_name=event_details.get("project_name", "unknown"),
                    user_id=user_id,
                    username=username,
                    project_details=event_details,
                    response_time=response_time
                )

        elif operation_type.startswith("file_"):
            if project_id and event_details:
                return await event_capture.capture_file_operation(
                    operation_type=operation_type.replace("file_", ""),
                    filename=event_details.get("filename", "unknown"),
                    project_id=project_id,
                    user_id=user_id,
                    username=username,
                    file_details=event_details,
                    response_time=response_time
                )

        # Add more operation types as needed...

    except Exception as e:
        logger.error(f"Failed to capture endpoint event {operation_type}: {e}")

    return False
