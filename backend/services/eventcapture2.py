"""
EventCapture2 - Enhanced Event Capture System with Rich Context

Key Architecture Principles:
✅ Events captured even when no project thread exists yet
✅ Rich, descriptive event summaries (not generic ones)
✅ DAS systems NEVER create project threads - only UI can do this
✅ Works with both DAS1 and DAS2 depending on what's active
✅ Non-blocking - API performance not affected by event capture
✅ Fault-tolerant - system works even if event capture fails
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events EventCapture2 can capture"""
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    ONTOLOGY_CREATED = "ontology_created"
    ONTOLOGY_MODIFIED = "ontology_modified"
    ONTOLOGY_SAVED = "ontology_saved"
    CLASS_CREATED = "class_created"
    PROPERTY_CREATED = "property_created"
    FILE_UPLOADED = "file_uploaded"
    FILE_DELETED = "file_deleted"
    WORKFLOW_STARTED = "workflow_started"
    KNOWLEDGE_ASSET_CREATED = "knowledge_asset_created"
    KNOWLEDGE_ASSET_UPDATED = "knowledge_asset_updated"
    KNOWLEDGE_ASSET_DELETED = "knowledge_asset_deleted"
    KNOWLEDGE_ASSET_PUBLISHED = "knowledge_asset_published"
    KNOWLEDGE_SEARCHED = "knowledge_searched"
    KNOWLEDGE_RAG_QUERY = "knowledge_rag_query"
    DAS_INTERACTION = "das_interaction"


@dataclass
class EnhancedEvent:
    """Enhanced event with rich context and meaningful summary"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: str
    username: str
    project_id: Optional[str]

    # Rich context fields
    summary: str  # Human-readable, descriptive summary
    details: Dict[str, Any]  # Structured details
    context: Dict[str, Any]  # Additional context

    # Performance tracking
    response_time: Optional[float] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = EventType(data['event_type'])
        return cls(**data)


class EventCapture2:
    """
    EventCapture2 - Enhanced event capture with rich context

    Features:
    - Rich, descriptive event summaries
    - Non-blocking event capture
    - Works with or without project threads
    - Fault-tolerant design
    - Integrates with both DAS1 and DAS2
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.event_queue = "eventcapture2_events"
        logger.info("EventCapture2 initialized - Enhanced event capture ready")

    async def capture_project_created(
        self,
        project_id: str,
        project_name: str,
        user_id: str,
        username: str,
        project_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture project creation with rich context"""
        try:
            # Build rich summary with user attribution
            summary = f"{username} created project '{project_name}'"
            if project_details.get('domain'):
                summary += f" in {project_details['domain']} domain"
            if project_details.get('description'):
                summary += f" with description"

            event = EnhancedEvent(
                event_id=f"proj_create_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.PROJECT_CREATED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "project_name": project_name,
                    "domain": project_details.get('domain'),
                    "description": project_details.get('description'),
                    "namespace_id": project_details.get('namespace_id')
                },
                context={"workbench": "project"},
                response_time=response_time,
                endpoint="/api/projects",
                method="POST"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture project creation: {e}")
            return False

    async def capture_ontology_operation(
        self,
        operation_type: str,  # "created", "modified", "saved"
        ontology_name: str,
        project_id: str,
        user_id: str,
        username: str,
        operation_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture ontology operations with rich context"""
        try:
            # Map operation type to event type
            event_type_map = {
                "created": EventType.ONTOLOGY_CREATED,
                "modified": EventType.ONTOLOGY_MODIFIED,
                "saved": EventType.ONTOLOGY_SAVED
            }

            event_type = event_type_map.get(operation_type, EventType.ONTOLOGY_MODIFIED)

            # Build rich summary with user attribution
            if operation_type == "created":
                summary = f"{username} created ontology '{ontology_name}'"
                if operation_details.get('is_reference'):
                    summary += " (reference ontology)"
            elif operation_type == "modified":
                # Check if this is a specific class/property addition
                if operation_details.get('operation') == 'class_added':
                    class_name = operation_details.get('class_name', 'Unknown')
                    class_comment = operation_details.get('class_comment', '')
                    if class_comment:
                        summary = f"{username} added class '{class_name}' to '{ontology_name}' ontology ({class_comment})"
                    else:
                        summary = f"{username} added class '{class_name}' to '{ontology_name}' ontology"
                else:
                    # General modification
                    changes = []
                    if operation_details.get('classes_count'):
                        changes.append(f"{operation_details['classes_count']} classes")
                    if operation_details.get('properties_count'):
                        changes.append(f"{operation_details['properties_count']} properties")
                    if operation_details.get('relationships_modified'):
                        changes.append("relationships")

                    if changes:
                        summary = f"{username} modified '{ontology_name}' ontology: {', '.join(changes)}"
                    else:
                        summary = f"{username} modified '{ontology_name}' ontology layout"
            else:  # saved
                summary = f"{username} saved ontology '{ontology_name}'"

            event = EnhancedEvent(
                event_id=f"onto_{operation_type}_{int(datetime.now().timestamp() * 1000)}",
                event_type=event_type,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "ontology_name": ontology_name,
                    "operation": operation_type,
                    **operation_details
                },
                context={"workbench": "ontology"},
                response_time=response_time
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture ontology operation: {e}")
            return False

    async def capture_file_operation(
        self,
        operation_type: str,  # "uploaded", "deleted"
        filename: str,
        project_id: str,
        user_id: str,
        username: str,
        file_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture file operations with rich context"""
        try:
            event_type_map = {
                "uploaded": EventType.FILE_UPLOADED,
                "deleted": EventType.FILE_DELETED
            }

            event_type = event_type_map.get(operation_type, EventType.FILE_UPLOADED)

            # Build rich summary with user attribution
            if operation_type == "uploaded":
                summary = f"{username} uploaded '{filename}'"
                if file_details.get('size'):
                    size_mb = file_details['size'] / (1024 * 1024)
                    if size_mb > 1:
                        summary += f" ({size_mb:.1f} MB)"
                    else:
                        summary += f" ({file_details['size'] / 1024:.1f} KB)"
                if file_details.get('content_type'):
                    content_type = file_details['content_type']
                    if 'pdf' in content_type.lower():
                        summary += " - PDF document"
                    elif 'word' in content_type.lower() or 'document' in content_type.lower():
                        summary += " - Word document"
                    elif 'text' in content_type.lower():
                        summary += " - Text file"
            else:  # deleted
                summary = f"{username} deleted file '{filename}'"

            event = EnhancedEvent(
                event_id=f"file_{operation_type}_{int(datetime.now().timestamp() * 1000)}",
                event_type=event_type,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "filename": filename,
                    "operation": operation_type,
                    **file_details
                },
                context={"workbench": "files"},
                response_time=response_time
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture file operation: {e}")
            return False

    async def capture_workflow_started(
        self,
        process_key: str,
        project_id: Optional[str],
        user_id: str,
        username: str,
        workflow_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture workflow execution with rich context"""
        try:
            # Build rich summary based on process key
            workflow_names = {
                "ingestion_pipeline": "document ingestion",
                "rag_query_process": "RAG knowledge query",
                "requirements_extraction": "requirements extraction",
                "odras_requirements_analysis": "requirements analysis",
                "knowledge_enrichment": "knowledge enrichment"
            }

            workflow_name = workflow_names.get(process_key, process_key.replace('_', ' '))
            summary = f"{username} started {workflow_name} workflow"

            if workflow_details.get('fileIds'):
                file_count = len(workflow_details['fileIds'])
                summary += f" with {file_count} file{'s' if file_count != 1 else ''}"

            event = EnhancedEvent(
                event_id=f"workflow_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.WORKFLOW_STARTED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "process_key": process_key,
                    "workflow_name": workflow_name,
                    **workflow_details
                },
                context={"workbench": "workflows"},
                response_time=response_time,
                endpoint="/api/workflows/start",
                method="POST"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture workflow start: {e}")
            return False

    async def capture_das_interaction(
        self,
        interaction_type: str,  # "question", "chat", "session_start"
        project_id: str,
        user_id: str,
        username: str,
        interaction_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture DAS interactions with rich context"""
        try:
            # Build rich summary with user attribution
            if interaction_type == "question":
                message = interaction_details.get('message', '')
                summary = f"{username} asked DAS: \"{message[:50]}{'...' if len(message) > 50 else ''}\""
                if interaction_details.get('sources_count'):
                    summary += f" (found {interaction_details['sources_count']} sources)"
            elif interaction_type == "chat":
                summary = f"{username} interacted with DAS assistant"
            else:
                summary = f"{username} started DAS session"

            event = EnhancedEvent(
                event_id=f"das_{interaction_type}_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.DAS_INTERACTION,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "interaction_type": interaction_type,
                    **interaction_details
                },
                context={"workbench": "das"},
                response_time=response_time
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture DAS interaction: {e}")
            return False

    async def capture_knowledge_asset_created(
        self,
        asset_id: str,
        title: str,
        project_id: str,
        user_id: str,
        username: str,
        asset_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture knowledge asset creation with rich context"""
        try:
            # Build rich summary with user attribution
            summary = f"{username} created knowledge asset '{title}'"

            document_type = asset_details.get('document_type', 'unknown')
            if document_type != 'unknown':
                summary += f" ({document_type})"

            if asset_details.get('source_file_id'):
                summary += " from uploaded file"

            if asset_details.get('content_summary'):
                content_preview = asset_details['content_summary'][:50]
                summary += f" - {content_preview}{'...' if len(asset_details['content_summary']) > 50 else ''}"

            event = EnhancedEvent(
                event_id=f"knowledge_create_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.KNOWLEDGE_ASSET_CREATED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "asset_id": asset_id,
                    "title": title,
                    **asset_details
                },
                context={"workbench": "knowledge"},
                response_time=response_time,
                endpoint="/api/knowledge/assets",
                method="POST"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture knowledge asset creation: {e}")
            return False

    async def capture_knowledge_search(
        self,
        search_query: str,
        project_id: Optional[str],
        user_id: str,
        username: str,
        search_results: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture knowledge search with rich context"""
        try:
            # Build rich summary with user attribution
            results_count = search_results.get('results_count', 0)
            summary = f"{username} searched knowledge: \"{search_query[:50]}{'...' if len(search_query) > 50 else ''}\""

            if results_count > 0:
                summary += f" (found {results_count} results)"
            else:
                summary += " (no results)"

            event = EnhancedEvent(
                event_id=f"knowledge_search_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.KNOWLEDGE_SEARCHED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "search_query": search_query,
                    "results_count": results_count,
                    **search_results
                },
                context={"workbench": "knowledge"},
                response_time=response_time,
                endpoint="/api/knowledge/search",
                method="POST"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture knowledge search: {e}")
            return False

    async def capture_knowledge_rag_query(
        self,
        query: str,
        project_id: Optional[str],
        user_id: str,
        username: str,
        query_results: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture RAG knowledge queries with rich context"""
        try:
            # Build rich summary with user attribution
            chunks_found = query_results.get('chunks_found', 0)
            summary = f"{username} made RAG query: \"{query[:50]}{'...' if len(query) > 50 else ''}\""

            if chunks_found > 0:
                summary += f" (found {chunks_found} knowledge chunks)"

                # Add source information if available
                sources = query_results.get('sources', [])
                if sources:
                    source_titles = [s.get('title', 'Unknown') for s in sources[:2]]
                    summary += f" from {', '.join(source_titles)}"
                    if len(sources) > 2:
                        summary += f" and {len(sources) - 2} more"
            else:
                summary += " (no relevant knowledge found)"

            event = EnhancedEvent(
                event_id=f"rag_query_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.KNOWLEDGE_RAG_QUERY,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "query": query,
                    "chunks_found": chunks_found,
                    **query_results
                },
                context={"workbench": "knowledge"},
                response_time=response_time,
                endpoint="/api/knowledge/query",
                method="POST"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture RAG query: {e}")
            return False

    async def capture_knowledge_asset_updated(
        self,
        asset_id: str,
        project_id: str,
        user_id: str,
        username: str,
        update_details: Dict[str, Any],
        response_time: Optional[float] = None
    ) -> bool:
        """Capture knowledge asset updates with rich context"""
        try:
            # Build rich summary
            updated_fields = []
            if update_details.get('title'):
                updated_fields.append('title')
            if update_details.get('document_type'):
                updated_fields.append('document type')
            if update_details.get('content_summary'):
                updated_fields.append('content summary')
            if update_details.get('status'):
                updated_fields.append('status')

            if updated_fields:
                summary = f"{username} updated knowledge asset: {', '.join(updated_fields)}"
            else:
                summary = f"{username} updated knowledge asset"

            if update_details.get('title'):
                summary += f" - '{update_details['title']}'"

            event = EnhancedEvent(
                event_id=f"knowledge_update_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.KNOWLEDGE_ASSET_UPDATED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "asset_id": asset_id,
                    "updated_fields": updated_fields,
                    **update_details
                },
                context={"workbench": "knowledge"},
                response_time=response_time,
                endpoint=f"/api/knowledge/assets/{asset_id}",
                method="PUT"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture knowledge asset update: {e}")
            return False

    async def capture_knowledge_asset_published(
        self,
        asset_id: str,
        asset_title: str,
        project_id: str,
        user_id: str,
        username: str,
        response_time: Optional[float] = None
    ) -> bool:
        """Capture knowledge asset publishing with rich context"""
        try:
            summary = f"{username} published knowledge asset '{asset_title}' for organization-wide access"

            event = EnhancedEvent(
                event_id=f"knowledge_publish_{int(datetime.now().timestamp() * 1000)}",
                event_type=EventType.KNOWLEDGE_ASSET_PUBLISHED,
                timestamp=datetime.now(),
                user_id=user_id,
                username=username,
                project_id=project_id,
                summary=summary,
                details={
                    "asset_id": asset_id,
                    "asset_title": asset_title,
                    "visibility": "public"
                },
                context={"workbench": "knowledge"},
                response_time=response_time,
                endpoint=f"/api/knowledge/assets/{asset_id}/public",
                method="PUT"
            )

            return await self._queue_event(event)

        except Exception as e:
            logger.error(f"Failed to capture knowledge asset publishing: {e}")
            return False

    async def _queue_event(self, event: EnhancedEvent) -> bool:
        """Queue event for background processing"""
        try:
            print(f"🔥 EVENTCAPTURE2 QUEUE: Attempting to queue event - {event.summary}")
            print(f"🔥 EVENTCAPTURE2 QUEUE: Redis client available: {bool(self.redis)}")

            if self.redis:
                event_json = json.dumps(event.to_dict())
                result = await self.redis.lpush(self.event_queue, event_json)
                print(f"🔥 EVENTCAPTURE2 QUEUE: Successfully queued event - Redis result: {result}")
                logger.debug(f"EventCapture2: Queued event - {event.summary}")
                return True
            else:
                print(f"🔥 EVENTCAPTURE2 QUEUE: No Redis available - event not queued")
                logger.warning("EventCapture2: No Redis available - event not queued")
                return False

        except Exception as e:
            print(f"🔥 EVENTCAPTURE2 QUEUE: Failed to queue event: {e}")
            logger.error(f"Failed to queue event: {e}")
            return False

    async def process_queued_events(self) -> int:
        """Process queued events and route them to available DAS systems"""
        processed = 0

        if not self.redis:
            logger.warning("EventCapture2: No Redis available for event processing")
            return 0

        try:
            while True:
                # Get next event from queue
                event_data = await self.redis.brpop(self.event_queue, timeout=1)

                if not event_data:
                    break  # No more events

                event_json = event_data[1]
                if isinstance(event_json, bytes):
                    event_json = event_json.decode('utf-8')

                event_dict = json.loads(event_json)
                event = EnhancedEvent.from_dict(event_dict)

                # Try to route event to available DAS system
                routed = await self._route_event_to_das(event)

                if routed:
                    logger.debug(f"EventCapture2: Successfully routed event - {event.summary}")
                else:
                    logger.debug(f"EventCapture2: Event not routed (no project thread) - {event.summary}")

                processed += 1

        except Exception as e:
            logger.error(f"Error processing queued events: {e}")

        return processed

    async def _route_event_to_das(self, event: EnhancedEvent) -> bool:
        """Route event to available DAS system (DAS1 or DAS2)"""
        try:
            # Only route events that have a project_id
            if not event.project_id:
                return False

            # Try DAS2 first (preferred)
            das2_success = await self._route_to_das2(event)
            if das2_success:
                return True

            # Fallback to DAS1 if available
            das1_success = await self._route_to_das1(event)
            return das1_success

        except Exception as e:
            logger.error(f"Error routing event to DAS: {e}")
            return False

    async def _route_to_das2(self, event: EnhancedEvent) -> bool:
        """Route event to DAS2 system"""
        try:
            from backend.api.das2 import das2_engine

            if not das2_engine or not das2_engine.project_manager:
                return False

            # Check if project thread exists (don't create one)
            project_thread = await das2_engine.project_manager.get_project_thread_by_project_id(event.project_id)
            if not project_thread:
                return False  # No project thread, can't route event

            # Map EventCapture2 events to ProjectThread events
            from backend.services.project_thread_manager import ProjectEventType

            event_type_map = {
                EventType.PROJECT_CREATED: ProjectEventType.DAS_COMMAND,
                EventType.ONTOLOGY_CREATED: ProjectEventType.ONTOLOGY_CREATED,
                EventType.ONTOLOGY_MODIFIED: ProjectEventType.ONTOLOGY_MODIFIED,
                EventType.FILE_UPLOADED: ProjectEventType.DOCUMENT_UPLOADED,
                EventType.WORKFLOW_STARTED: ProjectEventType.WORKFLOW_EXECUTED,
                EventType.DAS_INTERACTION: ProjectEventType.DAS_QUESTION
            }

            project_event_type = event_type_map.get(event.event_type, ProjectEventType.DAS_COMMAND)

            # Capture in project thread with rich summary
            await das2_engine.project_manager.capture_project_event(
                project_id=event.project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=event.user_id,
                event_type=project_event_type,
                event_data={
                    "semantic_summary": event.summary,  # Rich summary from EventCapture2
                    "eventcapture2_details": event.details,
                    "captured_by": "eventcapture2",
                    "original_timestamp": event.timestamp.isoformat()
                }
            )

            logger.debug(f"EventCapture2: Routed to DAS2 - {event.summary}")
            return True

        except Exception as e:
            logger.debug(f"Failed to route to DAS2: {e}")
            return False

    async def _route_to_das1(self, event: EnhancedEvent) -> bool:
        """Route event to DAS1 system (fallback)"""
        try:
            from backend.api.das import das_engine

            if not das_engine or not das_engine.project_manager:
                return False

            # Check if project thread exists (don't create one)
            project_thread = await das_engine.project_manager.get_project_thread_by_project_id(event.project_id)
            if not project_thread:
                return False  # No project thread, can't route event

            # Map EventCapture2 events to ProjectThread events
            from backend.services.project_thread_manager import ProjectEventType

            event_type_map = {
                EventType.PROJECT_CREATED: ProjectEventType.DAS_COMMAND,
                EventType.ONTOLOGY_CREATED: ProjectEventType.ONTOLOGY_CREATED,
                EventType.ONTOLOGY_MODIFIED: ProjectEventType.ONTOLOGY_MODIFIED,
                EventType.FILE_UPLOADED: ProjectEventType.DOCUMENT_UPLOADED,
                EventType.WORKFLOW_STARTED: ProjectEventType.WORKFLOW_EXECUTED,
                EventType.DAS_INTERACTION: ProjectEventType.DAS_QUESTION
            }

            project_event_type = event_type_map.get(event.event_type, ProjectEventType.DAS_COMMAND)

            # Capture in project thread with rich summary
            await das_engine.project_manager.capture_project_event(
                project_id=event.project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=event.user_id,
                event_type=project_event_type,
                event_data={
                    "semantic_summary": event.summary,  # Rich summary from EventCapture2
                    "eventcapture2_details": event.details,
                    "captured_by": "eventcapture2",
                    "original_timestamp": event.timestamp.isoformat()
                }
            )

            logger.debug(f"EventCapture2: Routed to DAS1 - {event.summary}")
            return True

        except Exception as e:
            logger.debug(f"Failed to route to DAS1: {e}")
            return False


# Global EventCapture2 instance
event_capture: Optional[EventCapture2] = None

def get_event_capture() -> Optional[EventCapture2]:
    """Get global EventCapture2 instance"""
    return event_capture

def initialize_event_capture(redis_client=None):
    """Initialize global EventCapture2 instance"""
    global event_capture
    event_capture = EventCapture2(redis_client)
    logger.info("EventCapture2 global instance initialized")
