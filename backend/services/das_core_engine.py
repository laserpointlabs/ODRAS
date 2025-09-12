"""
DAS Core Engine - Central orchestration for the Digital Assistance System

This module implements the core DAS functionality including conversation management,
intent recognition, context management, and session management.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .config import Settings
from .rag_service import RAGService
from .das_rag_service import DASRAGService
from .db import DatabaseService

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents that DAS can recognize"""
    QUESTION = "question"
    COMMAND = "command"
    GUIDANCE_REQUEST = "guidance_request"
    WORKFLOW_EXECUTION = "workflow_execution"
    FILE_OPERATION = "file_operation"
    ONTOLOGY_OPERATION = "ontology_operation"
    ANALYSIS_REQUEST = "analysis_request"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence levels for DAS responses"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ActivityEvent:
    """Represents a user activity event for session tracking"""
    event_id: str
    session_id: str
    user_id: str
    activity_type: str
    timestamp: datetime
    data: Dict[str, Any]
    context: Dict[str, Any] = None

    def to_json(self) -> str:
        """Convert to JSON string for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ActivityEvent':
        """Create from JSON string"""
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class DASSession:
    """Represents a DAS user session"""
    session_id: str
    user_id: str
    start_time: datetime
    last_activity: datetime
    current_context: Dict[str, Any]
    activity_log: List[ActivityEvent]
    session_summary: str
    user_preferences: Dict[str, Any]
    active_project: Optional[str]
    permissions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'current_context': self.current_context,
            'activity_log': [event.to_json() for event in self.activity_log],
            'session_summary': self.session_summary,
            'user_preferences': self.user_preferences,
            'active_project': self.active_project,
            'permissions': self.permissions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DASSession':
        """Create from dictionary"""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['activity_log'] = [ActivityEvent.from_json(event) for event in data['activity_log']]
        return cls(**data)


@dataclass
class DASResponse:
    """Represents a DAS response to user input"""
    message: str
    confidence: ConfidenceLevel
    intent: IntentType
    suggestions: List[Dict[str, Any]] = None
    commands: List[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.commands is None:
            self.commands = []
        if self.artifacts is None:
            self.artifacts = []
        if self.metadata is None:
            self.metadata = {}


class IntentRecognizer:
    """Recognizes user intent from natural language input"""

    def __init__(self, settings: Settings):
        self.settings = settings
        # Intent patterns - can be enhanced with ML models later
        self.intent_patterns = {
            IntentType.QUESTION: [
                "what", "how", "why", "when", "where", "explain", "tell me",
                "can you help", "i need to understand", "what does"
            ],
            IntentType.COMMAND: [
                "create", "delete", "update", "run", "execute", "start", "stop",
                "generate", "analyze", "process", "upload", "download"
            ],
            IntentType.GUIDANCE_REQUEST: [
                "how do i", "show me how", "guide me", "help me with",
                "i want to learn", "tutorial", "step by step"
            ],
            IntentType.WORKFLOW_EXECUTION: [
                "run workflow", "execute process", "start analysis",
                "process document", "analyze requirements"
            ],
            IntentType.FILE_OPERATION: [
                "upload file", "download", "delete file", "organize files",
                "file management", "document"
            ],
            IntentType.ONTOLOGY_OPERATION: [
                "ontology", "class", "relationship", "property", "schema",
                "create class", "add relationship"
            ],
            IntentType.ANALYSIS_REQUEST: [
                "analyze", "analysis", "requirements analysis", "sensitivity",
                "impact assessment", "conceptual model"
            ]
        }

    async def recognize_intent(self, user_input: str, context: Dict[str, Any] = None) -> Tuple[IntentType, float]:
        """
        Recognize user intent from input text
        
        Returns:
            Tuple of (intent_type, confidence_score)
        """
        user_input_lower = user_input.lower()
        
        # Simple keyword-based recognition (can be enhanced with ML)
        intent_scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in user_input_lower:
                    score += 1
            
            if score > 0:
                intent_scores[intent_type] = score / len(patterns)
        
        if not intent_scores:
            return IntentType.UNKNOWN, 0.0
        
        # Return intent with highest score
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        return best_intent[0], best_intent[1]


class ContextManager:
    """Manages conversation and session context"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.context_cache = {}

    async def build_context(self, session: DASSession, user_input: str) -> Dict[str, Any]:
        """
        Build comprehensive context for DAS processing
        """
        context = {
            "session_context": {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "active_project": session.active_project,
                "user_preferences": session.user_preferences,
                "recent_activities": [event.data for event in session.activity_log[-5:]]
            },
            "conversation_context": {
                "current_input": user_input,
                "session_summary": session.session_summary,
                "current_context": session.current_context
            },
            "system_context": {
                "timestamp": datetime.now().isoformat(),
                "available_commands": await self.get_available_commands(session),
                "user_permissions": session.permissions
            }
        }
        
        return context

    async def get_available_commands(self, session: DASSession) -> List[Dict[str, Any]]:
        """
        Get list of commands available to the user based on permissions
        """
        # This would integrate with your existing permission system
        # For now, return basic commands
        return [
            {
                "command": "retrieve_ontology",
                "description": "Retrieve an ontology by ID",
                "category": "ontology_management"
            },
            {
                "command": "create_class",
                "description": "Create a new class in an ontology",
                "category": "ontology_management"
            },
            {
                "command": "run_analysis",
                "description": "Run requirements analysis on a document",
                "category": "analysis_workflows"
            },
            {
                "command": "upload_document",
                "description": "Upload a document for processing",
                "category": "file_operations"
            }
        ]


class ConversationManager:
    """Manages conversation flow and response generation"""

    def __init__(self, settings: Settings, rag_service: RAGService, das_rag_service: DASRAGService):
        self.settings = settings
        self.rag_service = rag_service
        self.das_rag_service = das_rag_service
        self.intent_recognizer = IntentRecognizer(settings)
        self.context_manager = ContextManager(settings)

    async def process_user_input(
        self, 
        user_input: str, 
        session: DASSession,
        user_id: str
    ) -> DASResponse:
        """
        Process user input and generate appropriate response
        """
        try:
            # Recognize intent
            intent, intent_confidence = await self.intent_recognizer.recognize_intent(user_input)
            
            # Build context
            context = await self.context_manager.build_context(session, user_input)
            
            # Generate response based on intent
            if intent == IntentType.QUESTION:
                response = await self._handle_question(user_input, context, session)
            elif intent == IntentType.COMMAND:
                response = await self._handle_command(user_input, context, session)
            elif intent == IntentType.GUIDANCE_REQUEST:
                response = await self._handle_guidance_request(user_input, context, session)
            elif intent == IntentType.WORKFLOW_EXECUTION:
                response = await self._handle_workflow_execution(user_input, context, session)
            else:
                response = await self._handle_general_query(user_input, context, session)
            
            # Set intent and confidence
            response.intent = intent
            response.confidence = self._determine_confidence_level(intent_confidence)
            
            # Add metadata (merge with existing metadata from handlers)
            existing_metadata = response.metadata or {}
            response.metadata = {
                **existing_metadata,  # Preserve sources and other metadata from handlers
                "intent_confidence": intent_confidence,
                "processing_time": datetime.now().isoformat(),
                "session_id": session.session_id,
                "context_used": bool(context)
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return DASResponse(
                message="I apologize, but I encountered an error processing your request. Please try again.",
                confidence=ConfidenceLevel.LOW,
                intent=IntentType.UNKNOWN,
                metadata={"error": str(e)}
            )

    async def _handle_question(self, user_input: str, context: Dict[str, Any], session: DASSession) -> DASResponse:
        """Handle question-type queries using enhanced DAS RAG"""
        try:
            # Use enhanced DAS RAG service
            rag_response = await self.das_rag_service.query_das_knowledge(
                question=user_input,
                context=context,
                max_chunks=5,
                include_instructions=True,
                include_general_knowledge=True
            )
            
            return DASResponse(
                message=rag_response.get("answer", "I couldn't find relevant information to answer your question."),
                confidence=self._convert_confidence_level(rag_response.get("confidence", 0)),
                intent=IntentType.QUESTION,
                metadata={
                    "sources": rag_response.get("sources", []),
                    "rag_confidence": rag_response.get("confidence", 0),
                    "instruction_results": rag_response.get("instruction_results", []),
                    "llm_used": rag_response.get("llm_used", False),
                    "model": rag_response.get("model", "unknown")
                }
            )
        except Exception as e:
            logger.error(f"Error in DAS RAG query: {e}")
            return DASResponse(
                message="I'm having trouble accessing the knowledge base right now. Please try again later.",
                confidence=ConfidenceLevel.LOW,
                intent=IntentType.QUESTION
            )

    async def _handle_command(self, user_input: str, context: Dict[str, Any], session: DASSession) -> DASResponse:
        """Handle command-type requests"""
        # This would integrate with your command execution framework
        return DASResponse(
            message="I understand you want to execute a command. Command execution will be implemented in the next phase.",
            confidence=ConfidenceLevel.MEDIUM,
            intent=IntentType.COMMAND,
            suggestions=[
                {
                    "title": "Available Commands",
                    "description": "View list of available commands",
                    "action": "list_commands"
                }
            ]
        )

    async def _handle_guidance_request(self, user_input: str, context: Dict[str, Any], session: DASSession) -> DASResponse:
        """Handle guidance and tutorial requests"""
        return DASResponse(
            message="I'd be happy to guide you through that process. Step-by-step guidance will be available in the next phase.",
            confidence=ConfidenceLevel.MEDIUM,
            intent=IntentType.GUIDANCE_REQUEST,
            suggestions=[
                {
                    "title": "Get Help",
                    "description": "Access the help documentation",
                    "action": "show_help"
                }
            ]
        )

    async def _handle_workflow_execution(self, user_input: str, context: Dict[str, Any], session: DASSession) -> DASResponse:
        """Handle workflow execution requests"""
        return DASResponse(
            message="I can help you execute workflows. Workflow execution will be integrated with your BPMN system in the next phase.",
            confidence=ConfidenceLevel.MEDIUM,
            intent=IntentType.WORKFLOW_EXECUTION,
            suggestions=[
                {
                    "title": "Available Workflows",
                    "description": "View available BPMN workflows",
                    "action": "list_workflows"
                }
            ]
        )

    async def _handle_general_query(self, user_input: str, context: Dict[str, Any], session: DASSession) -> DASResponse:
        """Handle general queries using RAG"""
        return await self._handle_question(user_input, context, session)

    def _determine_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Convert numeric confidence to enum"""
        if confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _convert_confidence_level(self, confidence) -> ConfidenceLevel:
        """Convert various confidence formats to ConfidenceLevel enum"""
        if isinstance(confidence, str):
            confidence_lower = confidence.lower()
            if confidence_lower in ['high', 'very high']:
                return ConfidenceLevel.HIGH
            elif confidence_lower in ['medium', 'moderate']:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
        elif isinstance(confidence, (int, float)):
            if confidence >= 0.7:
                return ConfidenceLevel.HIGH
            elif confidence >= 0.4:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.MEDIUM


class DASCoreEngine:
    """
    Main DAS Core Engine that orchestrates all DAS functionality
    """

    def __init__(self, settings: Settings, rag_service: RAGService, db_service: DatabaseService):
        self.settings = settings
        self.rag_service = rag_service
        self.db_service = db_service
        
        # Initialize DAS RAG service
        from .qdrant_service import QdrantService
        qdrant_service = QdrantService(settings)
        self.das_rag_service = DASRAGService(settings, rag_service, qdrant_service, db_service)
        
        self.conversation_manager = ConversationManager(settings, rag_service, self.das_rag_service)
        self.active_sessions = {}  # In-memory session cache

    async def initialize(self) -> bool:
        """
        Initialize the DAS engine and instruction collection
        """
        try:
            # Initialize instruction collection
            success = await self.das_rag_service.initialize_instruction_collection()
            if success:
                logger.info("DAS engine initialized successfully")
            else:
                logger.warning("DAS engine initialized but instruction collection failed")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DAS engine: {e}")
            return False

    async def start_session(self, user_id: str, project_id: Optional[str] = None) -> DASSession:
        """
        Start a new DAS session for a user
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = DASSession(
            session_id=session_id,
            user_id=user_id,
            start_time=now,
            last_activity=now,
            current_context={},
            activity_log=[],
            session_summary="",
            user_preferences={},
            active_project=project_id,
            permissions={}  # Would integrate with your auth system
        )
        
        # Store in memory cache
        self.active_sessions[session_id] = session
        
        # Log session start
        await self._log_activity(session, "session_start", {"project_id": project_id})
        
        logger.info(f"Started DAS session {session_id} for user {user_id}")
        return session

    async def process_message(
        self, 
        session_id: str, 
        user_input: str, 
        user_id: str
    ) -> DASResponse:
        """
        Process a user message and return DAS response
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session activity
        session.last_activity = datetime.now()
        
        # Log user input
        await self._log_activity(session, "user_input", {"input": user_input})
        
        # Process through conversation manager
        response = await self.conversation_manager.process_user_input(user_input, session, user_id)
        
        # Log response
        await self._log_activity(session, "das_response", {
            "response": response.message,
            "intent": response.intent.value,
            "confidence": response.confidence.value
        })
        
        return response

    async def get_session(self, session_id: str) -> Optional[DASSession]:
        """
        Get session by ID
        """
        return self.active_sessions.get(session_id)

    async def end_session(self, session_id: str) -> bool:
        """
        End a DAS session
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            await self._log_activity(session, "session_end", {})
            del self.active_sessions[session_id]
            logger.info(f"Ended DAS session {session_id}")
            return True
        return False

    async def _log_activity(self, session: DASSession, activity_type: str, data: Dict[str, Any]):
        """
        Log an activity event for the session
        """
        event = ActivityEvent(
            event_id=str(uuid.uuid4()),
            session_id=session.session_id,
            user_id=session.user_id,
            activity_type=activity_type,
            timestamp=datetime.now(),
            data=data,
            context=session.current_context
        )
        
        session.activity_log.append(event)
        
        # Keep only last 100 activities to prevent memory bloat
        if len(session.activity_log) > 100:
            session.activity_log = session.activity_log[-100:]
