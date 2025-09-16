"""
Project Thread Manager - Comprehensive project-based DAS intelligence

This service manages project threads with full context awareness, event capture,
and cross-project learning capabilities.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectEventType(Enum):
    """Types of project events that can be captured"""
    # DAS Interactions
    DAS_QUESTION = "das_question"
    DAS_COMMAND = "das_command" 
    DAS_RESPONSE = "das_response"
    
    # Ontology Operations
    ONTOLOGY_CREATED = "ontology_created"
    ONTOLOGY_MODIFIED = "ontology_modified"
    CLASS_CREATED = "class_created"
    RELATIONSHIP_ADDED = "relationship_added"
    
    # Document Operations
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_ANALYZED = "document_analyzed"
    
    # Analysis Operations
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    
    # Requirements Operations
    REQUIREMENTS_EXTRACTED = "requirements_extracted"
    REQUIREMENTS_VALIDATED = "requirements_validated"
    
    # Workflow Operations
    WORKFLOW_EXECUTED = "workflow_executed"
    WORKFLOW_COMPLETED = "workflow_completed"
    
    # Context Operations
    WORKBENCH_CHANGED = "workbench_changed"
    PROJECT_GOAL_SET = "project_goal_set"


@dataclass
class ProjectEvent:
    """Individual project event for comprehensive tracking"""
    event_id: str
    project_id: str
    project_thread_id: str
    user_id: str
    timestamp: datetime
    event_type: ProjectEventType
    event_data: Dict[str, Any]
    context_snapshot: Dict[str, Any]
    semantic_summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'event_id': self.event_id,
            'project_id': self.project_id,
            'project_thread_id': self.project_thread_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'event_data': self.event_data,
            'context_snapshot': self.context_snapshot,
            'semantic_summary': self.semantic_summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = ProjectEventType(data['event_type'])
        return cls(**data)


@dataclass
class ProjectThreadContext:
    """Comprehensive project thread context"""
    # Basic Info
    project_thread_id: str
    project_id: str
    created_by: str
    created_at: datetime
    last_activity: datetime
    
    # Conversation Context
    conversation_history: List[Dict[str, Any]]
    
    # Project Context
    project_events: List[Dict[str, Any]]
    active_ontologies: List[str]
    recent_documents: List[str]
    current_workbench: str
    project_goals: Optional[str]
    
    # Intelligence Context
    key_decisions: List[Dict[str, Any]]
    learned_patterns: List[Dict[str, Any]]
    contextual_references: Dict[str, Any]  # For "that class" type references
    
    # Cross-Project Context
    similar_projects: List[str]
    applied_patterns: List[str]
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_activity, str):
            self.last_activity = datetime.fromisoformat(self.last_activity)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectThreadContext':
        """Create from dictionary"""
        return cls(**data)


class ProjectThreadManager:
    """
    Manages project threads with comprehensive intelligence and context awareness
    """
    
    def __init__(self, settings, redis_client, qdrant_service):
        self.settings = settings
        self.redis = redis_client  # Optional cache
        self.qdrant = qdrant_service  # Primary storage
        self.project_threads: Dict[str, ProjectThreadContext] = {}
        self.event_queue = "project_events"
        self.thread_prefix = "project_thread"
        self.collection_name = "project_threads"
        
        if not qdrant_service:
            raise RuntimeError("Qdrant service required for project thread storage")
        
        logger.info(f"Project Thread Manager initialized - Vector store: Primary, Redis: {'Cache enabled' if redis_client else 'Cache disabled'}")
    
    async def get_or_create_project_thread(self, project_id: str, user_id: str) -> ProjectThreadContext:
        """
        Get existing project thread or create new one
        Each project has exactly one thread that persists across user sessions
        """
        try:
            # First check if project thread already exists
            existing_thread = await self._find_project_thread(project_id)
            if existing_thread:
                # Update last activity and return
                existing_thread.last_activity = datetime.now()
                await self._persist_project_thread(existing_thread)
                logger.info(f"Retrieved existing project thread {existing_thread.project_thread_id} for project {project_id}")
                return existing_thread
            
            # Create new project thread
            project_thread_id = str(uuid.uuid4())
            
            thread_context = ProjectThreadContext(
                project_thread_id=project_thread_id,
                project_id=project_id,
                created_by=user_id,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                conversation_history=[],
                project_events=[],
                active_ontologies=[],
                recent_documents=[],
                current_workbench="ontology",
                project_goals=None,
                key_decisions=[],
                learned_patterns=[],
                contextual_references={},
                similar_projects=[],
                applied_patterns=[]
            )
            
            # Store in memory and persist to vector store
            self.project_threads[project_thread_id] = thread_context
            await self._persist_project_thread(thread_context)
            
            # Capture thread creation event
            await self.capture_project_event(
                project_id=project_id,
                project_thread_id=project_thread_id,
                user_id=user_id,
                event_type=ProjectEventType.DAS_COMMAND,
                event_data={
                    "action": "project_thread_created",
                    "created_by": user_id,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Created new project thread {project_thread_id} for project {project_id}")
            return thread_context
            
        except Exception as e:
            logger.error(f"Error getting/creating project thread for project {project_id}: {e}")
            raise
    
    async def get_project_thread(self, project_thread_id: str) -> Optional[ProjectThreadContext]:
        """Get project thread by ID"""
        try:
            # Check memory cache first
            if project_thread_id in self.project_threads:
                return self.project_threads[project_thread_id]
            
            # Load from persistent storage (vector store + Redis cache)
            thread_context = await self._load_project_thread(project_thread_id)
            if thread_context:
                # Cache in memory
                self.project_threads[project_thread_id] = thread_context
                return thread_context
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting project thread {project_thread_id}: {e}")
            return None
    
    async def capture_project_event(
        self, 
        project_id: str,
        project_thread_id: str,
        user_id: str,
        event_type: ProjectEventType,
        event_data: Dict[str, Any],
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Capture a project event for learning and context awareness
        """
        try:
            event = ProjectEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                project_thread_id=project_thread_id,
                user_id=user_id,
                timestamp=datetime.now(),
                event_type=event_type,
                event_data=event_data,
                context_snapshot=context_snapshot or {}
            )
            
            # Add to Redis queue for background processing
            await self.redis.lpush(self.event_queue, json.dumps(event.to_dict()))
            
            # Update project thread context immediately
            await self._update_thread_context_from_event(event)
            
            # Publish for real-time monitoring
            await self.redis.publish(f"project_watch:{project_id}", json.dumps(event.to_dict()))
            
            logger.debug(f"Captured project event {event_type.value} for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to capture project event {event_type.value} for project {project_id}: {e}")
            return False
    
    async def add_contextual_reference(
        self, 
        project_thread_id: str, 
        reference_type: str, 
        reference_data: Dict[str, Any]
    ):
        """
        Add contextual reference for 'that class', 'this ontology' type understanding
        """
        try:
            thread_context = await self.get_project_thread(project_thread_id)
            if not thread_context:
                return False
            
            # Store reference with timestamp for recency
            reference_key = f"{reference_type}_{datetime.now().timestamp()}"
            thread_context.contextual_references[reference_key] = {
                "type": reference_type,
                "data": reference_data,
                "timestamp": datetime.now().isoformat(),
                "context": reference_data.get("context", "")
            }
            
            # Keep only last 50 references to avoid memory bloat
            if len(thread_context.contextual_references) > 50:
                # Remove oldest references
                sorted_refs = sorted(
                    thread_context.contextual_references.items(),
                    key=lambda x: x[1]["timestamp"]
                )
                for old_key, _ in sorted_refs[:-50]:
                    del thread_context.contextual_references[old_key]
            
            await self._persist_project_thread(thread_context)
            return True
            
        except Exception as e:
            logger.error(f"Failed to add contextual reference: {e}")
            return False
    
    async def resolve_contextual_reference(
        self, 
        project_thread_id: str, 
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve contextual references like 'that class', 'this document'
        """
        try:
            thread_context = await self.get_project_thread(project_thread_id)
            if not thread_context:
                return None
            
            query_lower = query.lower()
            
            # Look for recent references that match the query context
            recent_refs = sorted(
                thread_context.contextual_references.items(),
                key=lambda x: x[1]["timestamp"],
                reverse=True
            )
            
            for ref_key, ref_data in recent_refs[:10]:  # Check last 10 references
                ref_type = ref_data["type"]
                ref_context = ref_data.get("context", "").lower()
                
                # Simple matching logic - can be enhanced with NLP
                if ("class" in query_lower and ref_type == "ontology_class") or \
                   ("ontology" in query_lower and ref_type == "ontology") or \
                   ("document" in query_lower and ref_type == "document") or \
                   ("analysis" in query_lower and ref_type == "analysis"):
                    return ref_data["data"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to resolve contextual reference: {e}")
            return None
    
    async def get_project_intelligence(self, project_thread_id: str) -> Dict[str, Any]:
        """
        Get comprehensive project intelligence for DAS responses
        """
        try:
            thread_context = await self.get_project_thread(project_thread_id)
            if not thread_context:
                return {}
            
            # Build comprehensive intelligence context
            intelligence = {
                "project_id": thread_context.project_id,
                "project_age": (datetime.now() - thread_context.created_at).days,
                "activity_level": len(thread_context.project_events),
                "current_focus": thread_context.current_workbench,
                "active_ontologies": thread_context.active_ontologies,
                "recent_documents": thread_context.recent_documents[-5:],  # Last 5
                "project_goals": thread_context.project_goals,
                "key_decisions": thread_context.key_decisions[-3:],  # Last 3
                "contextual_references": thread_context.contextual_references,
                "conversation_context": thread_context.conversation_history[-5:],  # Last 5
                "learned_patterns": thread_context.learned_patterns,
                "similar_projects": thread_context.similar_projects
            }
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Failed to get project intelligence: {e}")
            return {}
    
    async def _find_project_thread(self, project_id: str) -> Optional[ProjectThreadContext]:
        """Find existing project thread by project ID using vector store"""
        try:
            # Search in vector store for project thread by project_id
            search_results = await self.qdrant.search_similar_chunks(
                query_text=f"project_id:{project_id}",
                collection_name=self.collection_name,
                limit=1,
                score_threshold=0.1
            )
            
            if search_results:
                # Found existing project thread
                payload = search_results[0].get("payload", {})
                thread_data = payload.get("thread_data", {})
                
                if thread_data and thread_data.get("project_id") == project_id:
                    logger.info(f"Found existing project thread for project {project_id}")
                    return ProjectThreadContext.from_dict(thread_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find project thread for project {project_id}: {e}")
            return None
    
    async def _persist_project_thread(self, thread_context: ProjectThreadContext):
        """Persist project thread to vector store (primary) and Redis (cache)"""
        try:
            thread_data = thread_context.to_dict()
            
            # Create searchable text for the thread
            searchable_text = self._create_thread_searchable_text(thread_context)
            
            # Generate embedding for the thread
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode([searchable_text])[0].tolist()
            
            # Store in vector store (primary storage)
            vector_data = [{
                "id": thread_context.project_thread_id,
                "vector": embedding,
                "payload": {
                    "project_thread_id": thread_context.project_thread_id,
                    "project_id": thread_context.project_id,
                    "created_by": thread_context.created_by,
                    "created_at": thread_context.created_at.isoformat(),
                    "last_activity": thread_context.last_activity.isoformat(),
                    "thread_data": thread_data,
                    "searchable_text": searchable_text
                }
            }]
            
            stored_ids = self.qdrant.store_vectors(self.collection_name, vector_data)
            logger.info(f"Stored project thread {thread_context.project_thread_id} in vector store")
            
            # Also cache in Redis if available (for performance)
            if self.redis:
                thread_json = json.dumps(thread_data)
                await self.redis.set(
                    f"{self.thread_prefix}:{thread_context.project_thread_id}",
                    thread_json,
                    ex=86400 * 7  # 7 days cache
                )
                # Create project index for fast lookup
                await self.redis.set(f"project_index:{thread_context.project_id}", thread_context.project_thread_id, ex=86400 * 7)
            
        except Exception as e:
            logger.error(f"Failed to persist project thread {thread_context.project_thread_id}: {e}")
            raise
    
    def _create_thread_searchable_text(self, thread_context: ProjectThreadContext) -> str:
        """Create searchable text representation of project thread"""
        try:
            parts = [
                f"project_id:{thread_context.project_id}",
                f"created_by:{thread_context.created_by}",
                f"workbench:{thread_context.current_workbench}",
            ]
            
            if thread_context.project_goals:
                parts.append(f"goals:{thread_context.project_goals}")
            
            if thread_context.active_ontologies:
                parts.append(f"ontologies:{','.join(thread_context.active_ontologies)}")
            
            # Add recent conversation topics
            if thread_context.conversation_history:
                recent_topics = []
                for conv in thread_context.conversation_history[-5:]:
                    user_msg = conv.get("user_message", "")
                    if user_msg:
                        recent_topics.append(user_msg[:50])  # First 50 chars
                
                if recent_topics:
                    parts.append(f"recent_topics:{' '.join(recent_topics)}")
            
            return " | ".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to create searchable text: {e}")
            return f"project_id:{thread_context.project_id}"
    
    async def _load_project_thread(self, project_thread_id: str) -> Optional[ProjectThreadContext]:
        """Load project thread from vector store (primary) or Redis (cache)"""
        try:
            # Try Redis cache first (if available)
            if self.redis:
                thread_json = await self.redis.get(f"{self.thread_prefix}:{project_thread_id}")
                if thread_json:
                    thread_data = json.loads(thread_json)
                    logger.debug(f"Loaded project thread {project_thread_id} from Redis cache")
                    return ProjectThreadContext.from_dict(thread_data)
            
            # Load from vector store (primary storage)
            try:
                # Get the specific point by ID
                points = self.qdrant.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[project_thread_id],
                    with_payload=True
                )
                
                if points:
                    payload = points[0].payload
                    thread_data = payload.get("thread_data", {})
                    
                    if thread_data:
                        logger.info(f"Loaded project thread {project_thread_id} from vector store")
                        
                        # Cache in Redis if available
                        if self.redis:
                            await self.redis.set(
                                f"{self.thread_prefix}:{project_thread_id}",
                                json.dumps(thread_data),
                                ex=86400 * 7
                            )
                        
                        return ProjectThreadContext.from_dict(thread_data)
                
            except Exception as e:
                logger.warning(f"Failed to load from vector store: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load project thread {project_thread_id}: {e}")
            return None
    
    async def _update_thread_context_from_event(self, event: ProjectEvent):
        """Update project thread context based on event"""
        try:
            thread_context = await self.get_project_thread(event.project_thread_id)
            if not thread_context:
                return
            
            # Update last activity
            thread_context.last_activity = event.timestamp
            
            # Add event to project events (keep last 100)
            event_summary = {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "summary": event.semantic_summary or f"{event.event_type.value} event",
                "key_data": event.event_data
            }
            
            thread_context.project_events.append(event_summary)
            if len(thread_context.project_events) > 100:
                thread_context.project_events = thread_context.project_events[-100:]
            
            # Update specific context based on event type
            if event.event_type == ProjectEventType.ONTOLOGY_CREATED:
                ontology_id = event.event_data.get("ontology_id")
                if ontology_id and ontology_id not in thread_context.active_ontologies:
                    thread_context.active_ontologies.append(ontology_id)
            
            elif event.event_type == ProjectEventType.DOCUMENT_UPLOADED:
                doc_id = event.event_data.get("document_id")
                if doc_id:
                    thread_context.recent_documents.insert(0, doc_id)
                    thread_context.recent_documents = thread_context.recent_documents[:20]  # Keep last 20
            
            elif event.event_type == ProjectEventType.WORKBENCH_CHANGED:
                thread_context.current_workbench = event.event_data.get("workbench", "ontology")
            
            elif event.event_type == ProjectEventType.PROJECT_GOAL_SET:
                thread_context.project_goals = event.event_data.get("goals")
            
            # Persist updated context
            await self._persist_project_thread(thread_context)
            
        except Exception as e:
            logger.error(f"Failed to update thread context from event: {e}")
