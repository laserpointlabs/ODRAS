"""
Session Thread Service - Simple session thread management for DAS

Manages session threads as LLM-style conversation threads containing all user activity.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .config import Settings
from .qdrant_service import QdrantService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class SessionThread:
    """Session thread containing all user activity for a work session"""
    session_thread_id: str
    username: str
    start_time: datetime
    end_time: Optional[datetime] = None
    session_goals: Optional[str] = None
    project_id: Optional[str] = None
    events: List[Dict[str, Any]] = None
    status: str = "active"  # active, ended, summarized
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionThread':
        """Create from dictionary"""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)
    
    def to_searchable_content(self) -> str:
        """Convert thread to searchable text for embedding"""
        content_parts = [
            f"User: {self.username}",
            f"Session Goals: {self.session_goals or 'Not specified'}",
            f"Project: {self.project_id or 'Not specified'}",
            f"Duration: {self._calculate_duration()} minutes",
            f"Events: {len(self.events)} activities"
        ]
        
        # Add event summaries
        if self.events:
            content_parts.append("Activities:")
            for event in self.events[-10:]:  # Last 10 events
                event_type = event.get("event_type", "unknown")
                event_data = event.get("event_data", {})
                if event_type == "user_message":
                    content_parts.append(f"- User asked: {event_data.get('message', '')}")
                elif event_type == "das_response":
                    content_parts.append(f"- DAS responded about: {event_data.get('response', '')[:100]}")
                elif event_type == "api_call":
                    content_parts.append(f"- API call: {event_data.get('method', '')} {event_data.get('endpoint', '')}")
                else:
                    content_parts.append(f"- {event_type}: {str(event_data)[:100]}")
        
        return "\n".join(content_parts)
    
    def _calculate_duration(self) -> float:
        """Calculate session duration in minutes"""
        end = self.end_time or datetime.now()
        duration = end - self.start_time
        return duration.total_seconds() / 60


class SessionThreadService:
    """
    Simple service for managing session threads
    """
    
    def __init__(self, settings: Settings, redis_client):
        self.settings = settings
        self.redis = redis_client
        self.qdrant_service = QdrantService(settings)
        self.embedding_service = EmbeddingService(settings)
        self.collection_name = "session_threads"
        
        # Ensure collection exists
        self.qdrant_service.ensure_collection(
            collection_name=self.collection_name,
            vector_size=384,
            distance="Cosine"
        )
    
    async def create_session_thread(
        self, 
        username: str, 
        project_id: Optional[str] = None,
        session_goals: Optional[str] = None
    ) -> SessionThread:
        """Create a new session thread"""
        session_thread = SessionThread(
            session_thread_id=str(uuid.uuid4()),
            username=username,
            start_time=datetime.now(),
            project_id=project_id,
            session_goals=session_goals
        )
        
        # Store in Redis for active session
        await self.redis.set(
            f"session_thread:{session_thread.session_thread_id}",
            json.dumps(session_thread.to_dict()),
            ex=86400  # 24 hours
        )
        
        logger.info(f"Created session thread {session_thread.session_thread_id} for {username}")
        return session_thread
    
    async def get_session_thread(self, session_thread_id: str) -> Optional[SessionThread]:
        """Get session thread by ID"""
        try:
            thread_json = await self.redis.get(f"session_thread:{session_thread_id}")
            if thread_json:
                thread_data = json.loads(thread_json)
                return SessionThread.from_dict(thread_data)
            return None
        except Exception as e:
            logger.error(f"Error getting session thread {session_thread_id}: {e}")
            return None
    
    async def add_event_to_thread(
        self, 
        session_thread_id: str, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Add an event to the session thread"""
        try:
            session_thread = await self.get_session_thread(session_thread_id)
            if not session_thread:
                logger.warning(f"Session thread {session_thread_id} not found")
                return False
            
            # Add event
            event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "event_data": event_data
            }
            
            session_thread.events.append(event)
            
            # Update in Redis
            await self.redis.set(
                f"session_thread:{session_thread_id}",
                json.dumps(session_thread.to_dict()),
                ex=86400
            )
            
            # Also queue for background processing
            await self.redis.lpush("session_events", json.dumps(event))
            
            logger.debug(f"Added event {event_type} to session thread {session_thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding event to session thread: {e}")
            return False
    
    async def end_session_thread(self, session_thread_id: str) -> bool:
        """End a session thread and prepare for embedding"""
        try:
            session_thread = await self.get_session_thread(session_thread_id)
            if not session_thread:
                return False
            
            # Mark as ended
            session_thread.end_time = datetime.now()
            session_thread.status = "ended"
            
            # Update in Redis
            await self.redis.set(
                f"session_thread:{session_thread_id}",
                json.dumps(session_thread.to_dict()),
                ex=86400
            )
            
            # Queue for embedding
            await self.redis.lpush("threads_to_embed", session_thread_id)
            
            logger.info(f"Ended session thread {session_thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending session thread: {e}")
            return False
    
    async def embed_session_thread(self, session_thread_id: str) -> bool:
        """Embed a completed session thread in the vector collection"""
        try:
            session_thread = await self.get_session_thread(session_thread_id)
            if not session_thread:
                return False
            
            # Generate embedding for the thread
            searchable_content = session_thread.to_searchable_content()
            embedding = self.embedding_service.generate_embeddings([searchable_content])
            
            # Store in Qdrant
            point = {
                "id": session_thread_id,
                "vector": embedding[0],
                "payload": {
                    **session_thread.to_dict(),
                    "searchable_content": searchable_content
                }
            }
            
            self.qdrant_service.store_vectors(
                collection_name=self.collection_name,
                vectors=[point]
            )
            
            # Mark as embedded
            session_thread.status = "embedded"
            await self.redis.set(
                f"session_thread:{session_thread_id}",
                json.dumps(session_thread.to_dict()),
                ex=86400
            )
            
            logger.info(f"Embedded session thread {session_thread_id} in vector collection")
            return True
            
        except Exception as e:
            logger.error(f"Error embedding session thread: {e}")
            return False
    
    async def search_user_threads(
        self, 
        username: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search session threads for a specific user"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embeddings([query])
            
            # Search with user filter
            results = self.qdrant_service.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding[0],
                limit=limit * 2,  # Get more results to filter
                score_threshold=0.3
            )
            
            # Filter by username
            user_results = []
            for result in results:
                payload = result.get("payload", {})
                if payload.get("username") == username:
                    user_results.append({
                        "session_thread_id": payload.get("session_thread_id"),
                        "start_time": payload.get("start_time"),
                        "session_goals": payload.get("session_goals"),
                        "project_id": payload.get("project_id"),
                        "event_count": len(payload.get("events", [])),
                        "score": result.get("score", 0),
                        "content": payload.get("searchable_content", "")[:200]
                    })
                    
                    if len(user_results) >= limit:
                        break
            
            return user_results
            
        except Exception as e:
            logger.error(f"Error searching user threads: {e}")
            return []


# Global service instance
session_thread_service: Optional[SessionThreadService] = None


async def initialize_session_thread_service(settings: Settings, redis_client_instance):
    """Initialize the session thread service"""
    global session_thread_service
    session_thread_service = SessionThreadService(settings, redis_client_instance)
    logger.info("Session thread service initialized")




