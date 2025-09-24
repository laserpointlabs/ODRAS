"""
Middleware-to-DAS Bridge - Routes middleware events to existing ProjectThreadManager

This bridge connects the middleware event capture system to the existing
DAS ProjectThreadManager, ensuring all UI events are captured in project threads.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .project_thread_manager import ProjectEventType

logger = logging.getLogger(__name__)


class MiddlewareToDASBridge:
    """
    Bridge service that processes middleware events and routes them to DAS ProjectThreadManager
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.processing = False

    async def start_processing(self):
        """Start processing middleware events and routing to DAS"""
        self.processing = True
        logger.info("🔗 Middleware-to-DAS bridge started - monitoring api_events queue")

        while self.processing:
            try:
                # Get events from middleware queue
                event_data = await self.redis.brpop("api_events", timeout=1)

                if event_data:
                    event_json = event_data[1]
                    event = json.loads(event_json)

                    logger.info(f"🔗 Bridge processing event: {event.get('semantic_action', 'unknown')}")

                    # Route to DAS ProjectThreadManager
                    success = await self._route_event_to_das(event)
                    if success:
                        logger.info(f"✅ Successfully routed event to DAS")
                    else:
                        logger.warning(f"❌ Failed to route event to DAS")

            except Exception as e:
                logger.error(f"Error in middleware-to-DAS bridge: {e}")
                await asyncio.sleep(1)

    async def _route_event_to_das(self, middleware_event: Dict[str, Any]) -> bool:
        """Route middleware event to DAS ProjectThreadManager"""
        try:
            # Extract event details
            username = middleware_event.get("username")
            semantic_action = middleware_event.get("semantic_action")
            context = middleware_event.get("context", {})
            metadata = middleware_event.get("metadata", {})

            if not username:
                logger.debug("Skipping event without username")
                return False

            # Extract project ID from context
            project_id = self._extract_project_id(context, metadata)
            if not project_id:
                logger.debug(f"Skipping event without project context: {semantic_action}")
                return False

            # Map middleware event to DAS event type
            das_event_type = self._map_to_das_event_type(metadata.get("type", ""))
            if not das_event_type:
                logger.debug(f"Skipping unmapped event type: {metadata.get('type')}")
                return False

            logger.info(f"🔗 Routing event: {semantic_action} → project {project_id[:8]}... → {das_event_type.value}")

            # Get DAS engine to access ProjectThreadManager
            from backend.api.das import das_engine
            if not das_engine or not das_engine.project_manager:
                logger.warning("DAS engine or project manager not available")
                return False

            # Get user ID (DAS system expects user_id, not username)
            user_id = await self._get_user_id_from_username(username)
            if not user_id:
                logger.warning(f"Could not get user_id for username: {username}")
                return False

            # Get existing project thread
            project_thread = await das_engine.project_manager.get_project_thread_by_project_id(project_id)
            if not project_thread:
                logger.warning(f"No project thread found for project {project_id} - skipping event capture")
                return False

            # Capture event in DAS system
            await das_engine.project_manager.capture_project_event(
                project_id=project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=user_id,
                event_type=das_event_type,
                event_data={
                    "semantic_action": semantic_action,
                    "original_context": context,
                    "original_metadata": metadata,
                    "response_time": middleware_event.get("response_time"),
                    "timestamp": middleware_event.get("timestamp")
                },
                context_snapshot=context
            )

            logger.debug(f"Routed middleware event to DAS: {semantic_action} → {das_event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Error routing event to DAS: {e}")
            return False

    def _extract_project_id(self, context: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[str]:
        """Extract project ID from event context"""
        # Try context first
        project_id = context.get("project_id")
        if project_id:
            return project_id

        # Try metadata
        project_id = metadata.get("project_id")
        if project_id:
            return project_id

        # Try to extract from graph URL
        graph = metadata.get("graph", "")
        if graph and "/core/" in graph and "/ontologies/" in graph:
            try:
                parts = graph.split("/core/")[1].split("/ontologies/")[0]
                return parts if parts else None
            except:
                pass

        return None

    def _map_to_das_event_type(self, middleware_type: str) -> Optional[ProjectEventType]:
        """Map middleware event type to DAS ProjectEventType"""
        mapping = {
            "ontology_layout": ProjectEventType.ONTOLOGY_MODIFIED,
            "ontology_save": ProjectEventType.ONTOLOGY_MODIFIED,
            "ontology_class_creation": ProjectEventType.CLASS_CREATED,
            "project_create": ProjectEventType.DAS_COMMAND,  # Project creation as command
            "project_update": ProjectEventType.DAS_COMMAND,
            "file_upload": ProjectEventType.DOCUMENT_UPLOADED,
            "file_delete": ProjectEventType.DAS_COMMAND,
            "knowledge_search": ProjectEventType.DAS_QUESTION,
            "knowledge_create": ProjectEventType.DAS_COMMAND,
            "workflow_start": ProjectEventType.WORKFLOW_EXECUTED,
            "das_chat": ProjectEventType.DAS_QUESTION,
            "das_session_start": ProjectEventType.DAS_COMMAND
        }

        return mapping.get(middleware_type)

    async def _get_user_id_from_username(self, username: str) -> Optional[str]:
        """Get user_id from username using the database"""
        try:
            from backend.services.db import DatabaseService
            from backend.services.config import Settings

            settings = Settings()
            db = DatabaseService(settings)

            # Simple query to get user_id from username
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM public.users WHERE username = %s", (username,))
                    result = cur.fetchone()
                    return result[0] if result else None
            finally:
                db._return(conn)

        except Exception as e:
            logger.error(f"Error getting user_id for username {username}: {e}")
            return None

    def stop_processing(self):
        """Stop processing events"""
        self.processing = False
        logger.info("Middleware-to-DAS bridge stopped")


# Global bridge instance
middleware_bridge: Optional[MiddlewareToDASBridge] = None


async def initialize_middleware_bridge(redis_client):
    """Initialize the middleware-to-DAS bridge"""
    print("🔗 BRIDGE INIT: Starting middleware bridge initialization...")
    global middleware_bridge
    middleware_bridge = MiddlewareToDASBridge(redis_client)
    print(f"🔗 BRIDGE INIT: Created bridge instance: {middleware_bridge}")

    # Start processing in background
    task = asyncio.create_task(middleware_bridge.start_processing())
    logger.info(f"Middleware-to-DAS bridge initialized, task created: {task}")

    # Give the task a moment to start
    await asyncio.sleep(0.1)
    logger.info("Middleware-to-DAS bridge startup completed")
