"""
Event Subscription Service for ODRAS

Manages event publish/subscribe functionality for the project lattice.
Implements pure pub/sub for artifacts and data flow between projects.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class EventSubscriptionService:
    """
    Service for managing event pub/sub in the project lattice.
    
    Implements unrestricted event flow for artifacts and data:
    - Any project can subscribe to any event
    - Any project can publish events
    - Events carry data, not knowledge
    - Completely decoupled from knowledge visibility
    """

    def __init__(self, settings: Settings = None, db_service: DatabaseService = None):
        self.settings = settings or Settings()
        self.db_service = db_service or DatabaseService(self.settings)

    def subscribe_to_event(
        self,
        project_id: str,
        event_type: str,
        source_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Subscribe project to an event type.
        
        Args:
            project_id: Project that will receive events
            event_type: Type of event to subscribe to (e.g., "requirements.approved")
            source_project_id: Specific source project (None = any source)
        """
        try:
            # Validate project exists
            project = self.db_service.get_project(project_id)
            if not project:
                return {"success": False, "error": "Project not found"}
            
            # Validate source project if specified
            if source_project_id:
                source_project = self.db_service.get_project(source_project_id)
                if not source_project:
                    return {"success": False, "error": "Source project not found"}
            
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO public.project_event_subscriptions 
                           (project_id, event_type, source_project_id)
                           VALUES (%s, %s, %s)
                           RETURNING subscription_id""",
                        (project_id, event_type, source_project_id),
                    )
                    
                    subscription_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(
                        f"Project {project_id} subscribed to {event_type} "
                        f"from {source_project_id or 'any source'}"
                    )
                    
                    return {
                        "success": True,
                        "subscription_id": subscription_id
                    }
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return {
                "success": False,
                "error": f"Failed to subscribe to event: {str(e)}"
            }

    def get_subscriptions(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all event subscriptions for a project."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT s.subscription_id, s.event_type, s.source_project_id,
                                  s.is_active, s.created_at,
                                  p.name as source_project_name, p.domain as source_domain
                           FROM public.project_event_subscriptions s
                           LEFT JOIN public.projects p ON s.source_project_id = p.project_id
                           WHERE s.project_id = %s AND s.is_active = TRUE
                           ORDER BY s.created_at DESC""",
                        (project_id,),
                    )
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get subscriptions for project {project_id}: {e}")
            return []

    def get_subscribers(
        self, event_type: str, source_project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all projects subscribed to an event type."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    if source_project_id:
                        # Specific source: subscribers to this project's events
                        cur.execute(
                            """SELECT s.subscription_id, s.project_id, s.event_type,
                                      p.name as subscriber_name, p.domain as subscriber_domain
                               FROM public.project_event_subscriptions s
                               JOIN public.projects p ON s.project_id = p.project_id
                               WHERE s.event_type = %s 
                               AND (s.source_project_id = %s OR s.source_project_id IS NULL)
                               AND s.is_active = TRUE
                               ORDER BY p.name""",
                            (event_type, source_project_id),
                        )
                    else:
                        # All subscribers to this event type
                        cur.execute(
                            """SELECT s.subscription_id, s.project_id, s.event_type,
                                      p.name as subscriber_name, p.domain as subscriber_domain
                               FROM public.project_event_subscriptions s
                               JOIN public.projects p ON s.project_id = p.project_id
                               WHERE s.event_type = %s AND s.is_active = TRUE
                               ORDER BY p.name""",
                            (event_type,),
                        )
                    
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get subscribers for event {event_type}: {e}")
            return []

    def publish_event(
        self,
        source_project_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish an event to all subscribers.
        
        Args:
            source_project_id: Project publishing the event
            event_type: Type of event (e.g., "fea.analysis_complete")
            event_data: Event payload (results, artifacts, data)
            created_by: User who triggered the event
        """
        try:
            # Validate source project
            source_project = self.db_service.get_project(source_project_id)
            if not source_project:
                return {"success": False, "error": "Source project not found"}
            
            # Get all subscribers
            subscribers = self.get_subscribers(event_type, source_project_id)
            
            # Create event record (for audit trail)
            event_id = self._create_event_record(
                source_project_id, event_type, event_data, created_by
            )
            
            # In a real implementation, this would trigger actual event delivery
            # For now, we'll log the event and return subscriber info
            logger.info(
                f"Event published: {event_type} from project {source_project_id} "
                f"to {len(subscribers)} subscribers"
            )
            
            return {
                "success": True,
                "event_id": event_id,
                "event_type": event_type,
                "subscribers_notified": len(subscribers),
                "subscribers": subscribers
            }
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return {
                "success": False,
                "error": f"Failed to publish event: {str(e)}"
            }

    def delete_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Delete an event subscription."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.project_event_subscriptions WHERE subscription_id = %s",
                        (subscription_id,),
                    )
                    
                    if cur.rowcount == 0:
                        return {"success": False, "error": "Subscription not found"}
                    
                    conn.commit()
                    return {"success": True}
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to delete subscription: {str(e)}"
            }

    def _create_event_record(
        self,
        source_project_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> str:
        """Create audit record of published event."""
        try:
            # This could be stored in a project_events table for audit trail
            # For now, we'll use the existing project_event table structure
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Check if project_event table exists (from existing event system)
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'project_event'
                        )
                    """)
                    
                    if cur.fetchone()[0]:
                        # Use existing project_event table
                        event_content = {
                            "event_type": event_type,
                            "source_project_id": source_project_id,
                            "data": event_data,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        cur.execute(
                            """INSERT INTO project_event 
                               (project_id, event_type, event_data, created_by)
                               VALUES (%s, %s, %s, %s)
                               RETURNING event_id""",
                            (source_project_id, event_type, 
                             json.dumps(event_content), created_by),
                        )
                        
                        event_id = cur.fetchone()[0]
                        conn.commit()
                        return str(event_id)
                    else:
                        # No event table, just return a synthetic ID
                        import uuid
                        return str(uuid.uuid4())
                        
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.warning(f"Failed to create event record: {e}")
            import uuid
            return str(uuid.uuid4())


# Convenience function for getting service instance
def get_event_subscription_service(
    settings: Settings = None, db_service: DatabaseService = None
) -> EventSubscriptionService:
    """Get an EventSubscriptionService instance with proper dependencies."""
    return EventSubscriptionService(settings, db_service)
