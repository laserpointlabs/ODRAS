"""
DAS Core Engine - Advanced Digital Assistant with RAG Integration and Session Learning

This is the comprehensive DAS engine that provides advanced agent capabilities,
integrates with the RAG query process, and learns from session interactions.
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .config import Settings
from .rag_service import RAGService
from .db import DatabaseService
from .session_manager import SessionManager, SessionContext
from .project_thread_manager import ProjectThreadManager, ProjectThreadContext, ProjectEvent, ProjectEventType
from .project_intelligence_service import ProjectIntelligenceService

logger = logging.getLogger(__name__)


class DASIntent(Enum):
    """DAS intent classification"""
    QUESTION = "question"
    COMMAND = "command"
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    CONVERSATION_MEMORY = "conversation_memory"  # "What did I ask?", "What were we talking about?"
    UNKNOWN = "unknown"


class DASConfidence(Enum):
    """DAS confidence levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DASResponse:
    """DAS response object"""
    message: str
    confidence: DASConfidence = DASConfidence.MEDIUM
    intent: DASIntent = DASIntent.UNKNOWN
    suggestions: Optional[List[str]] = None
    commands: Optional[List[Dict[str, Any]]] = None
    artifacts: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DASProjectThread:
    """DAS project thread object"""
    project_thread_id: str
    user_id: str
    project_id: str
    started_at: datetime = None
    last_activity: datetime = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.context is None:
            self.context = {}


class DASCoreEngine:
    """
    Advanced DAS Core Engine with RAG integration and project thread management

    This engine provides:
    - Advanced conversational AI capabilities
    - Deep RAG integration for knowledge queries
    - Project thread context awareness and learning
    - Vector store integration for experience learning
    - Intelligent command execution
    - Contextual suggestions and assistance
    """

    def __init__(self, settings: Settings, rag_service: RAGService, db_service: DatabaseService, redis_client=None, qdrant_service=None):
        self.settings = settings
        self.rag_service = rag_service
        self.db_service = db_service
        self.redis = redis_client
        self.qdrant = qdrant_service

        # Initialize project intelligence services
        if not qdrant_service:
            raise RuntimeError("Qdrant service required for project intelligence - vector store is primary storage")

        self.project_manager = ProjectThreadManager(settings, redis_client, qdrant_service)
        self.project_intelligence = ProjectIntelligenceService(settings, redis_client, qdrant_service, rag_service)

        logger.info(f"Project intelligence initialized - Redis: {'Available' if redis_client else 'Not available (cache disabled)'}")

        # Legacy support - will be phased out
        self.project_threads: Dict[str, DASProjectThread] = {}

        logger.info("DAS Core Engine initialized with comprehensive project intelligence")

    async def get_or_create_project_thread(self, user_id: str, project_id: str) -> DASProjectThread:
        """Get existing project thread or create new one"""
        # First, try to find existing project thread for this project
        existing_thread = await self._find_project_thread_by_project_id(project_id)
        if existing_thread:
            logger.info(f"Found existing project thread {existing_thread.project_thread_id} for project {project_id}")
            return existing_thread

        # No existing thread, create new one
        return await self.start_project_thread(user_id, project_id)

    async def start_project_thread(self, user_id: str, project_id: str) -> DASProjectThread:
        """Start a new DAS project thread with full context awareness"""
        project_thread_id = str(uuid.uuid4())

        project_thread = DASProjectThread(
            project_thread_id=project_thread_id,
            user_id=user_id,
            project_id=project_id,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            context={
                "project_id": project_id,
                "conversation_history": [],
                "learned_preferences": {},
                "active_workflows": []
            }
        )

        self.project_threads[project_thread_id] = project_thread

        # Persist to Redis if available
        if self.redis:
            await self._persist_project_thread(project_thread)
            # Also create project ID index for discovery
            await self.redis.set(f"das_project_index:{project_id}", project_thread_id, ex=86400 * 7)

        # Log project thread creation for analytics
        logger.info(f"Created DAS project thread {project_thread_id} for project {project_id} by user {user_id}")
        return project_thread

    async def get_project_thread(self, project_thread_id: str) -> Optional[DASProjectThread]:
        """Get existing DAS project thread"""
        # First check memory cache
        project_thread = self.project_threads.get(project_thread_id)
        if project_thread:
            project_thread.last_activity = datetime.now()
            return project_thread

        # If not in memory, try to load from Redis
        if self.redis:
            project_thread = await self._load_project_thread(project_thread_id)
            if project_thread:
                self.project_threads[project_thread_id] = project_thread
                project_thread.last_activity = datetime.now()
                return project_thread

        return None

    async def process_message_with_intelligence(
        self,
        project_id: str,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DASResponse:
        """
        Process message with full project intelligence and contextual understanding
        """
        try:
            if not self.project_manager:
                raise RuntimeError("ProjectThreadManager not initialized - check Redis connection")

            if not self.project_intelligence:
                raise RuntimeError("ProjectIntelligenceService not initialized - check Redis/Qdrant connection")

            # Get or create project thread using new system
            project_thread = await self.project_manager.get_or_create_project_thread(project_id, user_id)

            # Resolve contextual references ("that class", "this ontology")
            contextual_ref = None
            if any(term in message.lower() for term in ["that ", "this ", "the "]):
                contextual_ref = await self.project_intelligence.resolve_contextual_reference(
                    project_thread, message
                )
                if contextual_ref:
                    logger.info(f"Resolved contextual reference: {contextual_ref}")

            # Enhance query with project context and resolved references
            enhanced_query = await self.project_intelligence.enhance_query_with_context(
                project_thread, message
            )

            if contextual_ref:
                enhanced_query += f" | Referring to: {contextual_ref.get('name', '')} ({contextual_ref.get('type', '')})"

            # Analyze intent
            intent = self._analyze_intent(message)

            # Handle conversation memory queries with LLM + context
            if intent == DASIntent.CONVERSATION_MEMORY:
                return await self._handle_conversation_memory_with_llm(
                    message, project_thread, user_id, intent, enhanced_query
                )

            # Query RAG with enhanced context for knowledge questions
            # Convert project thread to dict for context
            project_thread_dict = project_thread.to_dict() if hasattr(project_thread, 'to_dict') else {
                'project_id': project_thread.project_id,
                'project_thread_id': project_thread.project_thread_id,
                'created_at': project_thread.created_at.isoformat() if hasattr(project_thread.created_at, 'isoformat') else str(project_thread.created_at),
                'last_activity': project_thread.last_activity.isoformat() if hasattr(project_thread.last_activity, 'isoformat') else str(project_thread.last_activity),
                'thread_data': project_thread.context
            }

            rag_response = await self.rag_service.query_knowledge_base(
                question=enhanced_query,
                project_id=project_id,
                project_thread_context=project_thread_dict,
                user_id=user_id,
                max_chunks=3,  # Fewer chunks for more focused responses
                similarity_threshold=0.5,  # Higher threshold for precision
                include_metadata=True,
                response_style="comprehensive"
            )

            # Generate intelligent response with contextual awareness
            response_message = await self._generate_contextual_response(
                message=message,
                rag_response=rag_response,
                project_thread=project_thread,
                intent=intent,
                contextual_ref=contextual_ref
            )

            # Generate project-aware suggestions
            suggestions = await self.project_intelligence.get_project_suggestions(
                project_thread, message
            )

            # Update conversation history
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "das_response": response_message,
                "intent": intent.value,
                "contextual_reference": contextual_ref,
                "project_context": context
            }

            project_thread.conversation_history.append(conversation_entry)

            # CRITICAL: Persist the updated project thread to vector store
            await self.project_manager._persist_project_thread(project_thread)
            logger.info(f"Persisted conversation to project thread {project_thread.project_thread_id}")

            # Update contextual references for future use
            await self.project_intelligence.update_contextual_references(
                project_thread, message, response_message
            )

            # Capture project event for learning
            await self.project_manager.capture_project_event(
                project_id=project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=user_id,
                event_type=ProjectEventType.DAS_QUESTION,
                event_data={
                    "user_message": message,
                    "das_response": response_message,
                    "intent": intent.value,
                    "contextual_reference": contextual_ref,
                    "rag_sources": rag_response.get("sources", [])
                }
            )

            # Calculate confidence
            confidence = self._calculate_confidence(rag_response, intent)

            # Convert suggestions to strings for compatibility
            suggestion_strings = [s.get("title", s.get("description", "")) for s in suggestions]

            return DASResponse(
                message=response_message,
                confidence=confidence,
                intent=intent,
                suggestions=suggestion_strings,
                session_id=project_thread.project_thread_id,
                metadata={
                    "rag_chunks_used": rag_response.get("chunks_found", 0),
                    "sources": rag_response.get("sources", []),
                    "contextual_reference": contextual_ref,
                    "project_intelligence": True,
                    "processing_time": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error processing message with intelligence: {e}")
            # NO FALLBACK - expose the actual error
            raise RuntimeError(f"Project intelligence processing failed: {e}") from e

    async def process_message(
        self,
        project_thread_id: str,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DASResponse:
        """
        Process a message with advanced DAS capabilities and RAG integration
        """
        try:
            project_thread = await self.get_project_thread(project_thread_id)
            if not project_thread:
                raise ValueError(f"Project thread {project_thread_id} not found")

            # Analyze message intent
            intent = self._analyze_intent(message)

            # Get project thread context and history for enhanced RAG
            project_context = await self._get_enhanced_context(project_thread, context)

            # Process with RAG integration
            rag_response = await self._process_with_rag(
                message=message,
                project_thread=project_thread,
                context=project_context,
                user_id=user_id
            )

            # Generate intelligent response
            response_message = await self._generate_intelligent_response(
                message=message,
                rag_response=rag_response,
                project_thread=project_thread,
                intent=intent
            )

            # Generate contextual suggestions
            suggestions = await self._generate_suggestions(project_thread, message, rag_response)

            # Update project thread history
            project_thread.context["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "das_response": response_message,
                "intent": intent.value,
                "context": project_context
            })

            # Capture learning data
            await self._capture_learning_data(project_thread, message, response_message, context)

            # Determine confidence
            confidence = self._calculate_confidence(rag_response, intent)

            return DASResponse(
                message=response_message,
                confidence=confidence,
                intent=intent,
                suggestions=suggestions,
                session_id=project_thread_id,
                metadata={
                    "rag_chunks_used": rag_response.get("chunks_found", 0),
                    "sources": rag_response.get("sources", []),
                    "project_context": project_context,
                    "processing_time": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error processing message in project thread {project_thread_id}: {e}")
            return DASResponse(
                message="I encountered an error processing your request. Please try again.",
                confidence=DASConfidence.LOW,
                intent=DASIntent.UNKNOWN,
                session_id=project_thread_id
            )

    async def _get_enhanced_context(
        self,
        project_thread: DASProjectThread,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get enhanced context including project thread history and learned patterns"""
        context = {
            "project_id": project_thread.project_id,
            "thread_duration": (datetime.now() - project_thread.started_at).total_seconds() / 60,
            "conversation_turns": len(project_thread.context.get("conversation_history", [])),
            "user_preferences": project_thread.context.get("learned_preferences", {}),
            "recent_activity": project_thread.context.get("conversation_history", [])[-3:],  # Last 3 interactions
        }

        if additional_context:
            context.update(additional_context)

        return context

    async def _process_with_rag(
        self,
        message: str,
        project_thread: DASProjectThread,
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Process message with advanced RAG integration"""
        if not self.rag_service:
            return {"response": "RAG service not available", "chunks": [], "confidence": "low"}

        try:
            # Enhanced RAG query with project thread context
            enhanced_query = await self._enhance_query_with_context(message, project_thread, context)

            rag_response = await self.rag_service.query_knowledge_base(
                question=enhanced_query,
                project_id=project_thread.project_id,
                user_id=user_id,
                max_chunks=5,   # Fewer, more relevant chunks
                similarity_threshold=0.5,  # Higher threshold for more precise matching
                include_metadata=True,
                response_style="comprehensive"
            )

            return rag_response

        except Exception as e:
            logger.error(f"Error in RAG processing: {e}")
            return {"response": f"RAG processing error: {str(e)}", "chunks": [], "confidence": "low"}

    async def _enhance_query_with_context(
        self,
        message: str,
        project_thread: DASProjectThread,
        context: Dict[str, Any]
    ) -> str:
        """Enhance the user query with project thread context for better RAG results"""
        enhanced_parts = [message]

        # Add project context
        if project_thread.project_id:
            enhanced_parts.append(f"Project context: {project_thread.project_id}")

        # Add recent conversation context
        recent_history = context.get("recent_activity", [])
        if recent_history:
            recent_topics = []
            for interaction in recent_history:
                if "user_message" in interaction:
                    recent_topics.append(interaction["user_message"][:50])
            if recent_topics:
                enhanced_parts.append(f"Recent discussion topics: {'; '.join(recent_topics)}")

        return " | ".join(enhanced_parts)

    async def _generate_intelligent_response(
        self,
        message: str,
        rag_response: Dict[str, Any],
        project_thread: DASProjectThread,
        intent: DASIntent
    ) -> str:
        """Generate intelligent response combining RAG results with project thread awareness"""
        base_response = rag_response.get("response", "I don't have enough information to help with that.")

        # Enhance response based on intent and project thread context
        if intent == DASIntent.GREETING:
            if project_thread.context.get("conversation_history"):
                return f"Welcome back! I see we've been working together on project {project_thread.project_id}. {base_response}"
            else:
                return f"Hello! I'm DAS, your digital assistant for project {project_thread.project_id}. {base_response}"

        elif intent == DASIntent.QUESTION:
            chunks_count = rag_response.get("chunks_found", 0)
            if chunks_count > 0:
                confidence_note = f"Based on {chunks_count} relevant sources from your project knowledge base: {base_response}"
                return confidence_note
            else:
                return f"I don't have specific information about that in your current project knowledge. {base_response}"

        elif intent == DASIntent.COMMAND:
            return f"I understand you want to execute a command. {base_response} Would you like me to help you with the implementation?"

        else:
            return base_response

    async def _generate_suggestions(
        self,
        project_thread: DASProjectThread,
        message: str,
        rag_response: Dict[str, Any]
    ) -> List[str]:
        """Generate contextual suggestions based on current interaction"""
        suggestions = []

        # RAG-based suggestions
        chunks = rag_response.get("chunks", [])
        if chunks:
            # Suggest related topics from RAG chunks
            for chunk in chunks[:2]:  # Top 2 chunks
                metadata = chunk.get("metadata", {})
                if "filename" in metadata:
                    suggestions.append(f"Explore more about {metadata['filename']}")

        # Project thread-based suggestions
        history = project_thread.context.get("conversation_history", [])
        if len(history) > 2:
            suggestions.append("Review our previous discussion")
            suggestions.append("Summarize what we've covered so far")

        # Intent-based suggestions
        if "ontology" in message.lower():
            suggestions.extend([
                "Show me the ontology structure",
                "Help me create ontology classes",
                "Analyze ontology relationships"
            ])

        if "document" in message.lower() or "file" in message.lower():
            suggestions.extend([
                "Upload a new document for analysis",
                "Search through existing documents",
                "Extract requirements from documents"
            ])

        return suggestions[:5]  # Limit to 5 suggestions

    async def _capture_learning_data(
        self,
        project_thread: DASProjectThread,
        user_message: str,
        das_response: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Capture interaction data for learning and improvement"""
        try:
            # Add interaction to project thread conversation history
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": user_message,
                "das_response": das_response,
                "context": context or {},
                "project_id": project_thread.project_id,
                "interaction_quality": "pending_feedback"
            }

            if "conversation_history" not in project_thread.context:
                project_thread.context["conversation_history"] = []

            project_thread.context["conversation_history"].append(conversation_entry)
            project_thread.last_activity = datetime.now()

            # Persist updated project thread
            if self.redis:
                await self._persist_project_thread(project_thread)

            logger.debug(f"Captured learning data for project thread {project_thread.project_thread_id}")
        except Exception as e:
            logger.warning(f"Could not capture learning data: {e}")

    async def _persist_project_thread(self, project_thread: DASProjectThread):
        """Persist project thread to Redis"""
        try:
            if not self.redis:
                return

            thread_data = {
                "project_thread_id": project_thread.project_thread_id,
                "user_id": project_thread.user_id,
                "project_id": project_thread.project_id,
                "started_at": project_thread.started_at.isoformat(),
                "last_activity": project_thread.last_activity.isoformat(),
                "context": project_thread.context
            }

            await self.redis.set(
                f"das_project_thread:{project_thread.project_thread_id}",
                json.dumps(thread_data),
                ex=86400 * 7  # 7 days expiration
            )

        except Exception as e:
            logger.warning(f"Failed to persist project thread {project_thread.project_thread_id}: {e}")

    async def _load_project_thread(self, project_thread_id: str) -> Optional[DASProjectThread]:
        """Load project thread from Redis"""
        try:
            if not self.redis:
                return None

            thread_json = await self.redis.get(f"das_project_thread:{project_thread_id}")
            if not thread_json:
                return None

            thread_data = json.loads(thread_json)

            return DASProjectThread(
                project_thread_id=thread_data["project_thread_id"],
                user_id=thread_data["user_id"],
                project_id=thread_data["project_id"],
                started_at=datetime.fromisoformat(thread_data["started_at"]),
                last_activity=datetime.fromisoformat(thread_data["last_activity"]),
                context=thread_data["context"]
            )

        except Exception as e:
            logger.warning(f"Failed to load project thread {project_thread_id}: {e}")
            return None

    async def _find_project_thread_by_project_id(self, project_id: str) -> Optional[DASProjectThread]:
        """Find existing project thread for a project ID"""
        try:
            if not self.redis:
                # Check memory cache only
                for thread in self.project_threads.values():
                    if thread.project_id == project_id:
                        return thread
                return None

            # Check Redis index
            project_thread_id = await self.redis.get(f"das_project_index:{project_id}")
            if project_thread_id:
                project_thread_id = project_thread_id.decode('utf-8') if isinstance(project_thread_id, bytes) else project_thread_id
                return await self.get_project_thread(project_thread_id)

            return None

        except Exception as e:
            logger.warning(f"Failed to find project thread for project {project_id}: {e}")
            return None

    async def _generate_contextual_response(
        self,
        message: str,
        rag_response: Dict[str, Any],
        project_thread: ProjectThreadContext,
        intent: DASIntent,
        contextual_ref: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response with full contextual awareness
        """
        try:
            base_response = rag_response.get("response", "I don't have information about that.")

            # If we resolved a contextual reference, enhance the response
            if contextual_ref:
                ref_name = contextual_ref.get("name", "")
                ref_type = contextual_ref.get("type", "")

                if ref_type == "ontology_class":
                    base_response = f"Regarding the {ref_name} class: {base_response}"
                elif ref_type == "ontology":
                    base_response = f"For the {ref_name} ontology: {base_response}"
                elif ref_type == "document":
                    base_response = f"About the {ref_name} document: {base_response}"

            # Add project context if relevant
            if intent == DASIntent.QUESTION and project_thread.project_goals:
                if any(term in message.lower() for term in ["goal", "objective", "purpose"]):
                    base_response += f"\n\nNote: Your project goals are: {project_thread.project_goals}"

            return base_response

        except Exception as e:
            logger.error(f"Failed to generate contextual response: {e}")
            return rag_response.get("response", "I encountered an error generating the response.")

    async def _handle_conversation_memory_with_llm(
        self,
        message: str,
        project_thread: ProjectThreadContext,
        user_id: str,
        intent: DASIntent,
        enhanced_query: str
    ) -> DASResponse:
        """
        Handle conversation memory queries by sending conversation context to LLM
        """
        try:
            # Get FULL conversation context from both conversation_history AND project_events
            all_conversations = []

            # Add conversations from project_events (where most conversations are stored)
            for event in project_thread.project_events:
                if event.get("event_type") == "das_question":
                    event_data = event.get("key_data", {})
                    user_msg = event_data.get("user_message")
                    das_response = event_data.get("das_response")
                    timestamp = event.get("timestamp")

                    if user_msg and das_response:
                        all_conversations.append({
                            "timestamp": timestamp,
                            "user_message": user_msg,
                            "das_response": das_response,
                            "source": "project_event"
                        })

            # Add conversations from conversation_history
            for conv in project_thread.conversation_history:
                all_conversations.append(conv)

            # Sort by timestamp
            all_conversations.sort(key=lambda x: x.get("timestamp", ""))

            if not all_conversations:
                # No conversation history - send to LLM with context
                llm_query = f"""
                User asks: "{message}"

                Conversation context: This is the first interaction in this project thread.

                Please respond naturally to the user's question about conversation history.
                """
            else:
                # Build conversation context for LLM using FULL conversation data
                recent_conversations = all_conversations[-5:]  # Last 5 exchanges
                context_lines = []

                for conv in recent_conversations:
                    user_msg = conv.get("user_message", "")
                    das_msg = conv.get("das_response", "")
                    timestamp = conv.get("timestamp", "")

                    context_lines.append(f"User: {user_msg}")
                    context_lines.append(f"DAS: {das_msg}")

                conversation_context = "\n".join(context_lines)

                llm_query = f"""
                User asks: "{message}"

                Recent conversation history:
                {conversation_context}

                Please respond to the user's question about our conversation history. Be specific and helpful.
                """

            # Send to LLM team for intelligent response
            logger.info(f"Sending conversation memory query to LLM: {llm_query[:200]}...")

            llm_response = await self.rag_service.llm_team.analyze_requirement(
                requirement_text=llm_query,
                ontology_json_schema={"type": "object"},  # Minimal schema
                custom_personas=[{
                    "name": "Conversation Assistant",
                    "system_prompt": "You are a helpful assistant that can recall and discuss conversation history. Be natural and conversational. Answer the user's question about the conversation directly.",
                    "is_active": True
                }]
            )

            logger.info(f"LLM response for conversation memory: {llm_response}")

            # Extract response with better error handling
            if llm_response and "analysis" in llm_response:
                response_message = llm_response["analysis"]
            elif llm_response and isinstance(llm_response, str):
                response_message = llm_response
            else:
                # If LLM fails, provide a helpful response based on conversation history
                if all_conversations:
                    last_interaction = all_conversations[-1]
                    last_question = last_interaction.get("user_message", "")
                    response_message = f'You just asked: "{last_question}"'
                else:
                    response_message = "This is our first interaction in this project."

            # Update conversation history
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "das_response": response_message,
                "intent": intent.value,
                "source": "conversation_memory_llm"
            }

            project_thread.conversation_history.append(conversation_entry)

            # CRITICAL: Persist the updated project thread to vector store
            await self.project_manager._persist_project_thread(project_thread)
            logger.info(f"Persisted conversation memory to project thread {project_thread.project_thread_id}")

            return DASResponse(
                message=response_message,
                confidence=DASConfidence.HIGH,  # High confidence for conversation memory
                intent=intent,
                suggestions=["Continue our previous discussion", "Ask me something new"],
                session_id=project_thread.project_thread_id,
                metadata={
                    "source": "conversation_memory_llm",
                    "conversation_length": len(all_conversations),
                    "processing_time": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Failed to handle conversation memory with LLM: {e}")
            raise RuntimeError(f"Conversation memory LLM processing failed: {e}") from e

    def _analyze_intent(self, message: str) -> DASIntent:
        """Analyze message intent using simple heuristics"""
        message_lower = message.lower().strip()

        # Conversation memory patterns - check FIRST
        if any(memory in message_lower for memory in [
            "what did i", "what was i", "what were we", "what did we",
            "just ask", "just said", "just discuss", "previous",
            "before", "earlier", "last question", "my last"
        ]):
            return DASIntent.CONVERSATION_MEMORY

        # Greeting patterns
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return DASIntent.GREETING

        # Command patterns
        if any(command in message_lower for command in ["create", "generate", "build", "make", "execute", "run", "start"]):
            return DASIntent.COMMAND

        # Question patterns
        if any(question in message_lower for question in ["what", "how", "why", "when", "where", "which", "can you", "could you", "?"]):
            return DASIntent.QUESTION

        # Clarification patterns
        if any(clarify in message_lower for clarify in ["explain", "clarify", "elaborate", "more details", "tell me more"]):
            return DASIntent.CLARIFICATION

        return DASIntent.UNKNOWN

    def _calculate_confidence(self, rag_response: Dict[str, Any], intent: DASIntent) -> DASConfidence:
        """Calculate confidence based on RAG results and intent"""
        chunks_count = rag_response.get("chunks_found", 0)
        rag_confidence = rag_response.get("confidence", "low")
        sources = rag_response.get("sources", [])

        # Check for high-quality matches (high similarity scores)
        high_quality_match = False
        very_high_quality_match = False
        if sources:
            max_relevance = 0
            for source in sources:
                relevance_score = source.get("relevance_score", 0)
                max_relevance = max(max_relevance, relevance_score)

            # Very high quality: >60% relevance
            if max_relevance > 0.6:
                very_high_quality_match = True
                high_quality_match = True
            # High quality: >50% relevance
            elif max_relevance > 0.5:
                high_quality_match = True

        # High confidence conditions
        if very_high_quality_match and rag_confidence in ["high", "medium"]:
            return DASConfidence.HIGH

        if high_quality_match and rag_confidence == "high" and chunks_count == 1:
            return DASConfidence.HIGH  # Perfect single match

        if chunks_count >= 3 and rag_confidence == "high":
            return DASConfidence.HIGH

        # Medium confidence conditions
        if high_quality_match and rag_confidence in ["medium"]:
            return DASConfidence.MEDIUM

        if chunks_count >= 1 and rag_confidence != "low":
            return DASConfidence.MEDIUM

        if intent in [DASIntent.GREETING, DASIntent.CLARIFICATION, DASIntent.CONVERSATION_MEMORY]:
            return DASConfidence.HIGH

        # Default to low confidence
        return DASConfidence.LOW

    async def get_project_thread_suggestions(self, project_thread_id: str) -> List[str]:
        """Get suggestions for a specific project thread"""
        project_thread = await self.get_project_thread(project_thread_id)
        if not project_thread:
            return []

        suggestions = []
        history = project_thread.context.get("conversation_history", [])

        if not history:
            suggestions = [
                "Ask me about your project requirements",
                "Upload documents for analysis",
                "Create or modify ontologies",
                "Search your knowledge base"
            ]
        else:
            # Context-aware suggestions based on recent activity
            recent_topics = set()
            for interaction in history[-3:]:
                user_msg = interaction.get("user_message", "").lower()
                if "ontology" in user_msg:
                    recent_topics.add("ontology")
                if "document" in user_msg:
                    recent_topics.add("document")
                if "requirement" in user_msg:
                    recent_topics.add("requirement")

            if "ontology" in recent_topics:
                suggestions.extend([
                    "Visualize the ontology structure",
                    "Validate ontology consistency",
                    "Export ontology to different formats"
                ])

            if "document" in recent_topics:
                suggestions.extend([
                    "Extract more requirements from documents",
                    "Compare documents for consistency",
                    "Generate document summaries"
                ])

        return suggestions[:5]

    async def execute_command(
        self,
        project_thread_id: str,
        command: str,
        parameters: Dict[str, Any] = None
    ) -> DASResponse:
        """Execute a DAS command with project thread context"""
        project_thread = await self.get_project_thread(project_thread_id)
        if not project_thread:
            return DASResponse(
                message="Project thread not found. Please start a new project thread.",
                confidence=DASConfidence.LOW,
                intent=DASIntent.COMMAND
            )

        # Command execution logic would go here
        # For now, return a placeholder response
        return DASResponse(
            message=f"Command '{command}' execution is not yet implemented.",
            confidence=DASConfidence.MEDIUM,
            intent=DASIntent.COMMAND,
            session_id=project_thread_id,
            suggestions=["Try asking a question instead", "Upload a document for analysis"]
        )
