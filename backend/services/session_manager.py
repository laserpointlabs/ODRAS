"""
Session Manager for DAS - Comprehensive session lifecycle management

This service manages user sessions from login to logout, capturing events and maintaining
context that enables DAS to understand what the user is doing and provide intelligent assistance.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Current session context that DAS needs to know"""
    session_id: str
    user_id: str
    project_id: Optional[str] = None
    active_ontology: Optional[str] = None
    session_goals: Optional[str] = None
    start_time: datetime = None
    last_activity: datetime = None
    current_workbench: str = "ontology"  # ontology, files, knowledge, etc.
    recent_documents: List[str] = None
    recent_analyses: List[str] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.recent_documents is None:
            self.recent_documents = []
        if self.recent_analyses is None:
            self.recent_analyses = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        
        # Convert None values to empty strings for Redis compatibility
        for key, value in data.items():
            if value is None:
                data[key] = ""
            elif isinstance(value, list) and not value:
                data[key] = "[]"
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionContext':
        """Create from dictionary stored in Redis"""
        # Convert back from Redis format
        converted_data = {}
        for key, value in data.items():
            if value == "":
                converted_data[key] = None
            elif key in ['recent_documents', 'recent_analyses'] and isinstance(value, str):
                try:
                    converted_data[key] = json.loads(value) if value != "[]" else []
                except json.JSONDecodeError:
                    converted_data[key] = []
            else:
                converted_data[key] = value
        
        converted_data['start_time'] = datetime.fromisoformat(converted_data['start_time'])
        converted_data['last_activity'] = datetime.fromisoformat(converted_data['last_activity'])
        return cls(**converted_data)


@dataclass
class SessionEvent:
    """Individual session event for tracking user activities"""
    event_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    event_type: str
    event_data: Dict[str, Any]
    context_snapshot: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'event_id': self.event_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'event_data': self.event_data,
            'context_snapshot': self.context_snapshot
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class SessionManager:
    """
    Manages user sessions with comprehensive context tracking and event capture
    """

    def __init__(self, settings: Settings, redis_client):
        self.settings = settings
        self.redis = redis_client
        self.event_queue = "session_events"
        self.session_prefix = "session"
        
    async def create_session(self, user_id: str, project_id: Optional[str] = None) -> SessionContext:
        """
        Create a new session when user logs in
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Create session context
            session_context = SessionContext(
                session_id=session_id,
                user_id=user_id,
                project_id=project_id,
                start_time=datetime.now(),
                last_activity=datetime.now()
            )
            
            # Store session in Redis
            await self._store_session_context(session_context)
            
            # Log session creation event
            await self.capture_event(
                session_id=session_id,
                event_type="session_start",
                event_data={
                    "user_id": user_id,
                    "project_id": project_id,
                    "login_time": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_context
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise

    async def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """
        Get current session context
        """
        try:
            session_json = await self.redis.get(f"{self.session_prefix}:{session_id}:context")
            if session_json:
                session_data = json.loads(session_json)
                return SessionContext.from_dict(session_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session context for {session_id}: {e}")
            return None

    async def update_session_context(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session context (e.g., when user selects ontology, changes project)
        """
        try:
            session_context = await self.get_session_context(session_id)
            if not session_context:
                logger.warning(f"Session {session_id} not found for context update")
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(session_context, key):
                    setattr(session_context, key, value)
            
            session_context.last_activity = datetime.now()
            
            # Store updated context
            await self._store_session_context(session_context)
            
            # Log context update event
            await self.capture_event(
                session_id=session_id,
                event_type="context_update",
                event_data=updates
            )
            
            logger.info(f"Updated session context for {session_id}: {updates}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session context for {session_id}: {e}")
            return False

    async def capture_event(self, session_id: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Capture a session event and add to processing queue
        """
        try:
            # Get current session context for snapshot
            session_context = await self.get_session_context(session_id)
            context_snapshot = session_context.to_dict() if session_context else {}
            
            # Create event
            event = SessionEvent(
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=context_snapshot.get('user_id', 'unknown'),
                timestamp=datetime.now(),
                event_type=event_type,
                event_data=event_data,
                context_snapshot=context_snapshot
            )
            
            # Add to Redis queue for processing
            await self.redis.lpush(self.event_queue, json.dumps(event.to_dict()))
            
            # Also publish for real-time DAS monitoring
            await self.redis.publish(f"das_watch:{session_id}", json.dumps(event.to_dict()))
            
            # Update session last activity
            if session_context:
                session_context.last_activity = datetime.now()
                await self._store_session_context(session_context)
            
            logger.debug(f"Captured event {event_type} for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to capture event {event_type} for session {session_id}: {e}")
            return False

    async def _store_session_context(self, context: SessionContext):
        """
        Store session context in Redis as JSON string
        """
        context_json = json.dumps(context.to_dict())
        await self.redis.set(
            f"{self.session_prefix}:{context.session_id}:context",
            context_json,
            ex=86400  # 24 hour expiration
        )

    async def get_session_events(self, session_id: str, limit: int = 50) -> List[SessionEvent]:
        """
        Get recent session events
        """
        try:
            event_data_list = await self.redis.lrange(
                f"{self.session_prefix}:{session_id}:events", 0, limit - 1
            )
            
            events = []
            for event_data in event_data_list:
                try:
                    event_dict = json.loads(event_data)
                    events.append(SessionEvent.from_dict(event_dict))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse event data: {event_data}")
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get session events for {session_id}: {e}")
            return []

    async def end_session(self, session_id: str) -> bool:
        """
        End session and clean up
        """
        try:
            # Capture session end event
            await self.capture_event(
                session_id=session_id,
                event_type="session_end",
                event_data={
                    "end_time": datetime.now().isoformat(),
                    "duration": await self._calculate_session_duration(session_id)
                }
            )
            
            # Keep session data for analysis but mark as ended
            session_context = await self.get_session_context(session_id)
            if session_context:
                await self.update_session_context(session_id, {"session_ended": True})
            
            logger.info(f"Ended session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False

    async def _calculate_session_duration(self, session_id: str) -> float:
        """
        Calculate session duration in minutes
        """
        session_context = await self.get_session_context(session_id)
        if session_context:
            duration = datetime.now() - session_context.start_time
            return duration.total_seconds() / 60
        return 0.0

    # Session context helpers for DAS
    async def get_active_ontology(self, session_id: str) -> Optional[str]:
        """
        Get the currently active ontology for this session
        """
        context = await self.get_session_context(session_id)
        return context.active_ontology if context else None

    async def get_session_goals(self, session_id: str) -> Optional[str]:
        """
        Get the stated goals for this session
        """
        context = await self.get_session_context(session_id)
        return context.session_goals if context else None

    async def set_session_goals(self, session_id: str, goals: str) -> bool:
        """
        Set session goals when user provides them
        """
        return await self.update_session_context(session_id, {"session_goals": goals})

    async def set_active_ontology(self, session_id: str, ontology_id: str) -> bool:
        """
        Set the active ontology when user selects one
        """
        return await self.update_session_context(session_id, {"active_ontology": ontology_id})

    async def set_active_project(self, session_id: str, project_id: str) -> bool:
        """
        Set the active project when user selects one
        """
        success = await self.update_session_context(session_id, {"project_id": project_id})
        if success:
            await self.capture_event(
                session_id=session_id,
                event_type="project_selected",
                event_data={"project_id": project_id}
            )
        return success

    # Enhanced event capture methods for DAS intelligence
    async def capture_ontology_selection(self, session_id: str, ontology_id: str, ontology_name: str = None) -> bool:
        """
        Capture when user selects an ontology to work with
        """
        success = await self.set_active_ontology(session_id, ontology_id)
        if success:
            await self.capture_event(
                session_id=session_id,
                event_type="ontology_selected",
                event_data={
                    "ontology_id": ontology_id,
                    "ontology_name": ontology_name or ontology_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
        return success

    async def capture_document_upload(
        self, 
        session_id: str, 
        document_id: str, 
        filename: str, 
        document_type: str = None,
        file_size: int = None
    ) -> bool:
        """
        Capture when user uploads a document
        """
        return await self.capture_event(
            session_id=session_id,
            event_type="document_uploaded",
            event_data={
                "document_id": document_id,
                "filename": filename,
                "document_type": document_type,
                "file_size": file_size,
                "upload_time": datetime.now().isoformat()
            }
        )

    async def capture_ontology_modification(
        self, 
        session_id: str, 
        ontology_id: str, 
        modification_type: str,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Capture ontology modifications (class creation, relationship addition, etc.)
        """
        return await self.capture_event(
            session_id=session_id,
            event_type="ontology_modified",
            event_data={
                "ontology_id": ontology_id,
                "modification_type": modification_type,  # "class_created", "relationship_added", etc.
                "details": details or {},
                "modification_time": datetime.now().isoformat()
            }
        )

    async def capture_analysis_started(
        self, 
        session_id: str, 
        analysis_type: str,
        target_id: str,
        target_type: str = "document"
    ) -> bool:
        """
        Capture when user starts an analysis workflow
        """
        return await self.capture_event(
            session_id=session_id,
            event_type="analysis_started",
            event_data={
                "analysis_type": analysis_type,
                "target_id": target_id,
                "target_type": target_type,
                "start_time": datetime.now().isoformat()
            }
        )

    async def capture_analysis_completed(
        self, 
        session_id: str, 
        analysis_type: str,
        target_id: str,
        results_summary: Dict[str, Any] = None
    ) -> bool:
        """
        Capture when an analysis workflow completes
        """
        return await self.capture_event(
            session_id=session_id,
            event_type="analysis_completed",
            event_data={
                "analysis_type": analysis_type,
                "target_id": target_id,
                "results_summary": results_summary or {},
                "completion_time": datetime.now().isoformat()
            }
        )

    async def capture_das_interaction(
        self, 
        session_id: str, 
        interaction_type: str,
        user_input: str,
        das_response: str = None,
        command_executed: str = None
    ) -> bool:
        """
        Capture DAS interactions for learning and improvement
        """
        return await self.capture_event(
            session_id=session_id,
            event_type=f"das_{interaction_type}",  # das_question, das_command, das_autonomous_action
            event_data={
                "interaction_type": interaction_type,
                "user_input": user_input,
                "das_response": das_response,
                "command_executed": command_executed,
                "interaction_time": datetime.now().isoformat()
            }
        )

    async def capture_workbench_change(self, session_id: str, workbench: str, previous_workbench: str = None) -> bool:
        """
        Capture when user switches between workbenches (ontology, files, knowledge, etc.)
        """
        success = await self.update_session_context(session_id, {"current_workbench": workbench})
        if success:
            await self.capture_event(
                session_id=session_id,
                event_type="workbench_changed",
                event_data={
                    "new_workbench": workbench,
                    "previous_workbench": previous_workbench,
                    "change_time": datetime.now().isoformat()
                }
            )
        return success

    async def capture_user_goal_setting(self, session_id: str, goals: str) -> bool:
        """
        Capture when user sets or updates their session goals
        """
        success = await self.set_session_goals(session_id, goals)
        if success:
            await self.capture_event(
                session_id=session_id,
                event_type="session_goals_set",
                event_data={
                    "goals": goals,
                    "goal_setting_time": datetime.now().isoformat()
                }
            )
        return success

    async def get_recent_activity_summary(self, session_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a summary of recent user activity for DAS context
        """
        try:
            events = await self.get_session_events(session_id, limit)
            
            # Categorize events
            activity_summary = {
                "total_events": len(events),
                "recent_documents": [],
                "recent_ontologies": [],
                "recent_analyses": [],
                "current_focus": None,
                "activity_pattern": []
            }
            
            for event in events:
                if event.event_type == "document_uploaded":
                    activity_summary["recent_documents"].append({
                        "document_id": event.event_data.get("document_id"),
                        "filename": event.event_data.get("filename"),
                        "upload_time": event.timestamp.isoformat()
                    })
                
                elif event.event_type == "ontology_selected":
                    activity_summary["recent_ontologies"].append({
                        "ontology_id": event.event_data.get("ontology_id"),
                        "ontology_name": event.event_data.get("ontology_name"),
                        "selection_time": event.timestamp.isoformat()
                    })
                
                elif event.event_type == "analysis_started":
                    activity_summary["recent_analyses"].append({
                        "analysis_type": event.event_data.get("analysis_type"),
                        "target_id": event.event_data.get("target_id"),
                        "start_time": event.timestamp.isoformat()
                    })
                
                activity_summary["activity_pattern"].append({
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat()
                })
            
            # Determine current focus based on recent activity
            if activity_summary["recent_analyses"]:
                activity_summary["current_focus"] = "analysis"
            elif activity_summary["recent_ontologies"]:
                activity_summary["current_focus"] = "ontology_management"
            elif activity_summary["recent_documents"]:
                activity_summary["current_focus"] = "document_processing"
            else:
                activity_summary["current_focus"] = "exploration"
            
            return activity_summary
            
        except Exception as e:
            logger.error(f"Failed to get activity summary for {session_id}: {e}")
            return {"error": str(e), "total_events": 0}


class SessionEventProcessor:
    """
    Processes session events from Redis queue
    """

    def __init__(self, redis_client, session_manager):
        self.redis = redis_client
        self.session_manager = session_manager
        self.event_queue = "session_events"

    async def start_processing(self):
        """
        Start processing session events from Redis queue
        """
        logger.info("Starting session event processor...")
        
        while True:
            try:
                # Blocking pop from queue (waits for events)
                event_data = await self.redis.brpop(self.event_queue, timeout=1)
                
                if event_data:
                    event_json = event_data[1]
                    event_dict = json.loads(event_json)
                    event = SessionEvent.from_dict(event_dict)
                    
                    # Process the event
                    await self._process_event(event)
                    
            except Exception as e:
                logger.error(f"Error processing session event: {e}")
                await asyncio.sleep(1)

    async def _process_event(self, event: SessionEvent):
        """
        Process individual session event
        """
        try:
            # Store event in session history
            await self.redis.lpush(
                f"session:{event.session_id}:events",
                json.dumps(event.to_dict())
            )
            
            # Keep only last 100 events per session
            await self.redis.ltrim(f"session:{event.session_id}:events", 0, 99)
            
            # Update session context based on event
            await self._update_context_from_event(event)
            
            # Check for DAS intervention opportunities
            await self._check_das_opportunities(event)
            
            logger.debug(f"Processed event {event.event_type} for session {event.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")

    async def _update_context_from_event(self, event: SessionEvent):
        """
        Update session context based on event type
        """
        updates = {}
        
        if event.event_type == "ontology_selected":
            updates["active_ontology"] = event.event_data.get("ontology_id")
            
        elif event.event_type == "project_selected":
            updates["project_id"] = event.event_data.get("project_id")
            
        elif event.event_type == "workbench_changed":
            updates["current_workbench"] = event.event_data.get("workbench")
            
        elif event.event_type == "document_uploaded":
            # Add to recent documents list
            session_context = await self.session_manager.get_session_context(event.session_id)
            if session_context:
                recent_docs = session_context.recent_documents or []
                recent_docs.insert(0, event.event_data.get("document_id"))
                updates["recent_documents"] = recent_docs[:10]  # Keep last 10
        
        if updates:
            await self.session_manager.update_session_context(event.session_id, updates)

    async def _check_das_opportunities(self, event: SessionEvent):
        """
        Check if DAS should provide proactive assistance based on this event
        """
        # Simple rules for when DAS should speak up
        opportunities = []
        
        if event.event_type == "document_uploaded":
            opportunities.append({
                "type": "document_analysis_offer",
                "message": "I can analyze that document and extract key requirements if you'd like.",
                "confidence": 0.8
            })
            
        elif event.event_type == "ontology_created":
            opportunities.append({
                "type": "ontology_population_offer", 
                "message": "I can help populate your ontology with standard classes and relationships.",
                "confidence": 0.9
            })
            
        elif event.event_type == "multiple_classes_created":
            if event.event_data.get("count", 0) >= 3:
                opportunities.append({
                    "type": "relationship_creation_offer",
                    "message": "I notice you've created several classes. Should I help establish relationships between them?",
                    "confidence": 0.7
                })
        
        # Store opportunities for DAS to present
        for opportunity in opportunities:
            await self.redis.lpush(
                f"das:{event.session_id}:opportunities",
                json.dumps(opportunity)
            )
            await self.redis.expire(f"das:{event.session_id}:opportunities", 300)  # 5 min expiry


# Common event types that should be captured
COMMON_EVENT_TYPES = {
    # Session lifecycle
    "session_start": "User logged in and started session",
    "session_end": "User ended session",
    "session_goals_set": "User provided session goals",
    
    # Navigation and context
    "project_selected": "User selected a project",
    "ontology_selected": "User selected an ontology to work with", 
    "workbench_changed": "User switched to different workbench",
    
    # Document operations
    "document_uploaded": "User uploaded a document",
    "document_analyzed": "User ran analysis on a document",
    "document_downloaded": "User downloaded a document",
    
    # Ontology operations
    "ontology_created": "User created a new ontology",
    "class_created": "User created an ontology class",
    "relationship_created": "User created a relationship",
    "ontology_modified": "User modified ontology structure",
    
    # Analysis operations
    "analysis_started": "User started an analysis workflow",
    "analysis_completed": "Analysis workflow completed",
    "query_executed": "User executed a query",
    
    # DAS interactions
    "das_question": "User asked DAS a question",
    "das_command": "User gave DAS a command to execute",
    "das_suggestion_accepted": "User accepted a DAS suggestion",
    "das_autonomous_action": "DAS executed an autonomous action"
}
