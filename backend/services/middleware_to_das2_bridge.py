"""
DAS Middleware Bridge - Simple Event Capture
Just captures events to project threads, no complex processing
"""

import logging
from typing import Dict, Optional

from .project_thread_manager import ProjectEventType

logger = logging.getLogger(__name__)


class DASMiddlewareBridge:
    """
    Simple middleware bridge for DAS
    Only captures events if project thread exists
    """

    def __init__(self, das_engine):
        self.das_engine = das_engine
        logger.info("DAS Middleware Bridge initialized")

    async def capture_semantic_event(
        self,
        semantic_action: str,
        project_id: str,
        username: str,
        request_details: Dict
    ) -> bool:
        """
        Simple event capture - only if project thread exists
        """
        try:
            if not self.das_engine:
                return False

            # Get user ID
            user_id = await self._get_user_id_from_username(username)
            if not user_id:
                logger.warning(f"Could not get user_id for username: {username}")
                return False

            # Check if project thread exists (don't create one)
            project_thread = await self.das_engine.project_manager.get_project_thread_by_project_id(project_id)
            if not project_thread:
                logger.info(f"No project thread for project {project_id} - skipping event capture")
                return False

            # Simple event mapping
            event_type_map = {
                "Created project": ProjectEventType.DAS_COMMAND,
                "Uploaded file": ProjectEventType.DOCUMENT_UPLOADED,
                "Created ontology": ProjectEventType.ONTOLOGY_CREATED,
                "Modified ontology": ProjectEventType.ONTOLOGY_MODIFIED,
                "Interacted with DAS": ProjectEventType.DAS_QUESTION
            }

            event_type = event_type_map.get(semantic_action, ProjectEventType.DAS_COMMAND)

            # Capture simple event
            await self.das_engine.project_manager.capture_project_event(
                project_id=project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=user_id,
                event_type=event_type,
                event_data={
                    "semantic_action": semantic_action,
                    "request_details": request_details,
                    "captured_by": "das_middleware"
                }
            )

            logger.info(f"DAS: Captured event '{semantic_action}' for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"DAS event capture failed: {e}")
            return False

    async def _get_user_id_from_username(self, username: str) -> Optional[str]:
        """Get user ID from username"""
        try:
            if not self.das_engine:
                return None

            # Use database service to lookup user
            db_service = self.das_engine.rag_service.db_service  # Reuse existing service

            conn = db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                    result = cur.fetchone()
                    return str(result[0]) if result else None
            finally:
                db_service._return(conn)

        except Exception as e:
            logger.error(f"Error getting user_id for username {username}: {e}")
            return None
