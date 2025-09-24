"""
DAS API endpoints for the Digital Assistance System

Provides REST API endpoints for DAS functionality including chat, session management,
command execution, and suggestions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services.das_core_engine import DASCoreEngine, DASResponse, DASProjectThread
from ..services.session_manager import SessionManager, SessionContext, SessionEvent
from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.db import DatabaseService
from ..services.auth import get_user as get_current_user

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/das", tags=["DAS"])

# Global DAS engine and session manager instances (will be initialized in main.py)
das_engine: Optional[DASCoreEngine] = None
session_manager: Optional[SessionManager] = None


# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")
    project_thread_id: Optional[str] = Field(None, description="Existing project thread ID")
    project_id: Optional[str] = Field(None, description="Current project ID for context")
    ontology_id: Optional[str] = Field(None, description="Current ontology ID for context")
    workbench: Optional[str] = Field(None, description="Current workbench (ontology, files, knowledge, etc.)")


class ChatResponse(BaseModel):
    message: str
    confidence: str
    intent: str
    suggestions: List[Dict[str, Any]] = []
    commands: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class ProjectThreadCreateRequest(BaseModel):
    project_id: str = Field(..., description="Project ID for the thread")


class ProjectThreadResponse(BaseModel):
    project_thread_id: str
    user_id: str
    project_id: str
    start_time: str
    status: str


class CommandExecuteRequest(BaseModel):
    command: Dict[str, Any] = Field(..., description="Command to execute")
    session_id: str = Field(..., description="Session ID")


class SuggestionResponse(BaseModel):
    id: str
    title: str
    description: str
    action: str
    confidence: str
    category: str


# Dependency to get DAS engine
async def get_das_engine() -> DASCoreEngine:
    """Get the global DAS engine instance"""
    if das_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DAS engine not initialized"
        )
    return das_engine


# Chat endpoints
@router.post("/chat/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Send a message to DAS and get a response
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Get or create project thread
        if request.project_thread_id:
            session = await engine.get_project_thread(request.project_thread_id)
            if not session:
                # Project thread not found, return 404
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project thread {request.project_thread_id} not found. Project threads are created when projects are created."
                )
            else:
                # Update project thread with current context if provided
                if session_manager and (request.ontology_id or request.workbench):
                    context_updates = {}
                    if request.ontology_id:
                        context_updates["active_ontology"] = request.ontology_id
                    if request.workbench:
                        context_updates["current_workbench"] = request.workbench

                    if context_updates:
                        await session_manager.update_session_context(session.project_thread_id, context_updates)
                        logger.info(f"Updated DAS project thread context: {context_updates}")
        else:
            # No project thread ID provided - need existing project with thread
            if not request.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project ID is required to access DAS functionality"
                )

            # Try to get legacy session, but don't fail if not found
            # The new intelligent processing will handle project threads properly
            session = await engine.get_project_thread_by_project_id(request.project_id)

            # Set additional context if provided
            if session_manager and (request.ontology_id or request.workbench):
                context_updates = {}
                if request.ontology_id:
                    context_updates["active_ontology"] = request.ontology_id
                if request.workbench:
                    context_updates["current_workbench"] = request.workbench

                if context_updates:
                    await session_manager.update_session_context(session.project_thread_id, context_updates)

        # Process message with project intelligence
        current_context = {
            "project_id": request.project_id,
            "ontology_id": request.ontology_id,
            "workbench": request.workbench
        }

        # Use simple processing - just project context + RAG, no hard-coded intelligence
        response = await engine.process_message_simple(
            request.project_id or (session.project_id if session else request.project_id),
            request.message,
            user_id,
            current_context
        )

        # Convert to API response
        # Convert string suggestions to dictionary format
        suggestions_dict = []
        if response.suggestions:
            for i, suggestion in enumerate(response.suggestions):
                suggestions_dict.append({
                    "id": f"suggestion_{i}",
                    "text": suggestion,
                    "type": "suggestion"
                })

        return ChatResponse(
            message=response.message,
            confidence=response.confidence.value,
            intent=response.intent.value,
            suggestions=suggestions_dict,
            commands=response.commands or [],
            artifacts=response.artifacts or [],
            metadata=response.metadata or {}
        )

    except HTTPException:
        # Re-raise HTTPExceptions (like our 404s) without modification
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )




@router.get("/project-thread/{project_thread_id}/history")
async def get_project_thread_history(
    project_thread_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get chat history for a project thread
    """
    try:
        session = await engine.get_project_thread(project_thread_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project thread not found"
            )

        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project thread"
            )

        # Get conversation history from session context
        history = []
        for entry in session.context.get("conversation_history", []):
            history.append({
                "type": "user",
                "message": entry.get("user_message"),
                "timestamp": entry.get("timestamp")
            })
            history.append({
                "type": "das",
                "message": entry.get("das_response"),
                "metadata": {"intent": entry.get("intent")},
                "timestamp": entry.get("timestamp")
            })

        return {"project_thread_id": project_thread_id, "history": history}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project thread history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project thread history: {str(e)}"
        )


# Project thread discovery and management endpoints
@router.get("/project/{project_id}/thread", response_model=ProjectThreadResponse)
async def get_project_thread_by_project_id(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get or create project thread for a project - this is the main entry point
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Use the intelligent system to get or create project thread
        if hasattr(engine, 'process_message_with_intelligence'):
            # New system: get or create via project manager
            if not engine.project_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Project intelligence not initialized - check Redis/Qdrant connections"
                )

            project_thread = await engine.project_manager.get_project_thread_by_project_id(project_id)
            if not project_thread:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No project thread found for project {project_id}. Project threads are created when projects are created."
                )

            return ProjectThreadResponse(
                project_thread_id=project_thread.project_thread_id,
                user_id=project_thread.created_by,
                project_id=project_thread.project_id,
                start_time=project_thread.created_at.isoformat(),
                status="active"
            )
        else:
            # Legacy system fallback
            session = await engine.get_project_thread_by_project_id(project_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No project thread found for project {project_id}. Project threads are created when projects are created."
                )

            return ProjectThreadResponse(
                project_thread_id=session.project_thread_id,
                user_id=session.user_id,
                project_id=session.project_id,
                start_time=session.started_at.isoformat(),
                status="active"
            )

    except HTTPException:
        # Re-raise HTTPExceptions (like our 404s) without modification
        raise
    except Exception as e:
        logger.error(f"Error getting project thread for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting project thread: {str(e)}"
        )


@router.get("/project/{project_id}/thread/history")
async def get_project_thread_history_by_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get conversation history for a project's thread
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Get the project thread
        if hasattr(engine, 'process_message_with_intelligence') and engine.project_manager:
            project_thread = await engine.project_manager.get_project_thread_by_project_id(project_id)
            if not project_thread:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No project thread found for project {project_id}. Project threads are created when projects are created."
                )

            # Build conversation history from both conversation_history AND project_events
            history = []

            # First, add conversations from project_events (where they're actually stored)
            for event in project_thread.project_events:
                if event.get("event_type") == "das_question":
                    event_data = event.get("key_data", {})
                    user_msg = event_data.get("user_message")
                    das_response = event_data.get("das_response")
                    timestamp = event.get("timestamp")
                    intent = event_data.get("intent", "question")

                    if user_msg and das_response:
                        history.append({
                            "type": "user",
                            "message": user_msg,
                            "timestamp": timestamp
                        })
                        history.append({
                            "type": "das",
                            "message": das_response,
                            "metadata": {
                                "intent": intent,
                                "source": "knowledge_base"
                            },
                            "timestamp": timestamp
                        })

            # Then add any additional entries from conversation_history (conversation memory, etc.)
            for entry in project_thread.conversation_history:
                # Skip if this conversation is already in project_events
                user_msg = entry.get("user_message")
                if not any(event.get("key_data", {}).get("user_message") == user_msg
                          for event in project_thread.project_events
                          if event.get("event_type") == "das_question"):

                    history.append({
                        "type": "user",
                        "message": entry.get("user_message"),
                        "timestamp": entry.get("timestamp")
                    })
                    history.append({
                        "type": "das",
                        "message": entry.get("das_response"),
                        "metadata": {
                            "intent": entry.get("intent"),
                            "source": entry.get("source", "conversation_memory")
                        },
                        "timestamp": entry.get("timestamp")
                    })

            # Sort by timestamp to maintain chronological order
            history.sort(key=lambda x: x.get("timestamp", ""))

            return {
                "project_id": project_id,
                "project_thread_id": project_thread.project_thread_id,
                "history": history
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Project intelligence not available"
            )

    except HTTPException:
        # Re-raise HTTPExceptions (like our 404s) without modification
        raise
    except Exception as e:
        logger.error(f"Error getting project thread history for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting project thread history: {str(e)}"
        )


@router.post("/project-thread/start", response_model=ProjectThreadResponse)
async def start_project_thread(
    request: ProjectThreadCreateRequest,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Start a new DAS project thread
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        session = await engine.start_project_thread(user_id, request.project_id)

        return ProjectThreadResponse(
            project_thread_id=session.project_thread_id,
            user_id=session.user_id,
            project_id=session.project_id,
            start_time=session.started_at.isoformat(),
            status="active"
        )

    except Exception as e:
        logger.error(f"Error starting project thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting project thread: {str(e)}"
        )


@router.get("/project-thread/{project_thread_id}", response_model=ProjectThreadResponse)
async def get_project_thread(
    project_thread_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get project thread information
    """
    try:
        session = await engine.get_project_thread(project_thread_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project thread not found"
            )

        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project thread"
            )

        return ProjectThreadResponse(
            project_thread_id=session.project_thread_id,
            user_id=session.user_id,
            project_id=session.project_id,
            start_time=session.started_at.isoformat(),
            status="active"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project thread: {str(e)}"
        )




# Command execution endpoints
@router.post("/commands/execute")
async def execute_command(
    request: CommandExecuteRequest,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Execute a DAS command
    """
    try:
        # For now, return a placeholder response
        # This will be implemented when we add command execution
        return {
            "success": False,
            "message": "Command execution not yet implemented",
            "command": request.command,
            "session_id": request.session_id
        }

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing command: {str(e)}"
        )


@router.get("/commands/templates")
async def get_command_templates(
    current_user: dict = Depends(get_current_user)
):
    """
    Get available command templates
    """
    try:
        # Return basic command templates
        templates = [
            {
                "command": "retrieve_ontology",
                "type": "api_call",
                "endpoint": "/api/ontologies/{ontology_id}",
                "method": "GET",
                "description": "Retrieve ontology by ID",
                "category": "ontology_management"
            },
            {
                "command": "create_class",
                "type": "api_call",
                "endpoint": "/api/ontologies/{ontology_id}/classes",
                "method": "POST",
                "description": "Create new class in ontology",
                "category": "ontology_management"
            },
            {
                "command": "run_analysis",
                "type": "workflow",
                "workflow_id": "requirements_analysis_workflow",
                "description": "Run full requirements analysis on document",
                "category": "analysis_workflows"
            },
            {
                "command": "upload_document",
                "type": "api_call",
                "endpoint": "/api/files/upload",
                "method": "POST",
                "description": "Upload a document for processing",
                "category": "file_operations"
            }
        ]

        return {"templates": templates}

    except Exception as e:
        logger.error(f"Error getting command templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving command templates: {str(e)}"
        )


# Suggestions endpoints
# @router.get("/suggestions/{session_id}")
# async def get_suggestions(
#     session_id: str,
#     current_user: dict = Depends(get_current_user),
#     engine: DASCoreEngine = Depends(get_das_engine)
# ):
#     """
#     Get suggestions for a session
#     """
#     try:
#         session = await engine.get_session(session_id)
#         if not session:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Session not found"
#             )
#
#         # Check user access
#         if session.user_id != current_user.get("user_id"):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Access denied to this session"
#             )
#
#         # For now, return basic suggestions based on session context
#         suggestions = []
#
#         if session.active_project:
#             suggestions.append({
#                 "id": "analyze_project",
#                 "title": "Analyze Project",
#                 "description": "Run requirements analysis on your active project",
#                 "action": "run_analysis",
#                 "confidence": "high",
#                 "category": "analysis_workflows"
#             })
#
#         suggestions.extend([
#             {
#                 "id": "browse_ontologies",
#                 "title": "Browse Ontologies",
#                 "description": "View available ontologies in the system",
#                 "action": "list_ontologies",
#                 "confidence": "medium",
#                 "category": "ontology_management"
#             },
#             {
#                 "id": "upload_document",
#                 "title": "Upload Document",
#                 "description": "Upload a new document for analysis",
#                 "action": "upload_document",
#                 "confidence": "medium",
#                 "category": "file_operations"
#             }
#         ])
#
#         return {"suggestions": suggestions}
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting suggestions: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error retrieving suggestions: {str(e)}"
#         )


# Health check endpoints
@router.get("/health")
async def health_check():
    """
    DAS health check endpoint
    """
    return {
        "status": "healthy",
        "service": "DAS",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/llm/health")
async def llm_health_check():
    """
    LLM health check endpoint
    """
    try:
        from ..services.config import Settings
        from ..services.llm_team import LLMTeam

        settings = Settings()
        llm_team = LLMTeam(settings)

        # Test LLM connectivity with a simple query
        test_response = await llm_team.analyze_requirement(
            requirement_text="Test connectivity",
            ontology_json_schema={"type": "object", "properties": {"test": {"type": "string"}}},
            custom_personas=[{
                "name": "System Health Checker",
                "system_prompt": "You are a system health checker. Respond with a simple test message.",
                "is_active": True
            }]
        )

        return {
            "status": "healthy",
            "service": "LLM",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "timestamp": datetime.now().isoformat(),
            "test_response": test_response.get("analysis", "Connected")[:100] + "..." if test_response else "No response"
        }
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "LLM",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Session management endpoints
@router.post("/session/create")
async def create_session(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new session when user logs in or starts working
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Create session using session manager
        if session_manager:
            session_context = await session_manager.create_session(user_id, project_id)

            return {
                "session_id": session_context.session_id,
                "user_id": session_context.user_id,
                "project_id": session_context.project_id,
                "start_time": session_context.start_time.isoformat(),
                "goal_setting_prompt": "Hi! I'm DAS, your session assistant. What would you like to accomplish today? (Optional - this helps me prepare relevant information and assist you better)"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


class SessionGoalsRequest(BaseModel):
    goals: str = Field(..., description="User's session goals")

@router.post("/session/{session_id}/goals")
async def set_session_goals(
    session_id: str,
    request: SessionGoalsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Set goals for the session
    """
    try:
        if session_manager:
            success = await session_manager.set_session_goals(session_id, request.goals)
            if success:
                return {
                    "success": True,
                    "message": f"Session goals set. I'm preparing relevant context for: {request.goals}",
                    "session_id": session_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error setting session goals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting session goals: {str(e)}"
        )


class SessionEventRequest(BaseModel):
    event_type: str = Field(..., description="Type of event")
    event_data: dict = Field(..., description="Event data")

@router.post("/session/{session_id}/events")
async def capture_session_event(
    session_id: str,
    request: SessionEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture a session event (called by frontend when user does something)
    """
    try:
        if session_manager:
            success = await session_manager.capture_event(session_id, request.event_type, request.event_data)
            return {"success": success, "event_type": request.event_type}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing session event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


@router.get("/session/{session_id}/context")
async def get_session_context(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get current session context for DAS
    """
    try:
        if session_manager:
            context = await session_manager.get_session_context(session_id)
            if context:
                return context.to_dict()
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error getting session context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting session context: {str(e)}"
        )


@router.get("/session/{session_id}/activity")
async def get_session_activity_summary(
    session_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent activity summary for DAS context awareness
    """
    try:
        if session_manager:
            activity_summary = await session_manager.get_recent_activity_summary(session_id, limit)
            return activity_summary
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error getting session activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting session activity: {str(e)}"
        )


# Enhanced event capture endpoints for frontend integration
class OntologySelectionRequest(BaseModel):
    ontology_id: str = Field(..., description="Selected ontology ID")
    ontology_name: str = Field(None, description="Ontology display name")

@router.post("/session/{session_id}/events/ontology-selected")
async def capture_ontology_selection(
    session_id: str,
    request: OntologySelectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture ontology selection event
    """
    try:
        if session_manager:
            success = await session_manager.capture_ontology_selection(
                session_id, request.ontology_id, request.ontology_name
            )
            return {
                "success": success,
                "event_type": "ontology_selected",
                "ontology_id": request.ontology_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing ontology selection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


class DocumentUploadEventRequest(BaseModel):
    document_id: str = Field(..., description="Uploaded document ID")
    filename: str = Field(..., description="Original filename")
    document_type: str = Field(None, description="Type of document")
    file_size: int = Field(None, description="File size in bytes")

@router.post("/session/{session_id}/events/document-uploaded")
async def capture_document_upload_event(
    session_id: str,
    request: DocumentUploadEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture document upload event
    """
    try:
        if session_manager:
            success = await session_manager.capture_document_upload(
                session_id,
                request.document_id,
                request.filename,
                request.document_type,
                request.file_size
            )
            return {
                "success": success,
                "event_type": "document_uploaded",
                "document_id": request.document_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing document upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


class WorkbenchChangeRequest(BaseModel):
    workbench: str = Field(..., description="New workbench name")
    previous_workbench: str = Field(None, description="Previous workbench name")

@router.post("/session/{session_id}/events/workbench-changed")
async def capture_workbench_change(
    session_id: str,
    request: WorkbenchChangeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture workbench change event
    """
    try:
        if session_manager:
            success = await session_manager.capture_workbench_change(
                session_id, request.workbench, request.previous_workbench
            )
            return {
                "success": success,
                "event_type": "workbench_changed",
                "workbench": request.workbench
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing workbench change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


class AnalysisEventRequest(BaseModel):
    analysis_type: str = Field(..., description="Type of analysis")
    target_id: str = Field(..., description="Target document/ontology ID")
    target_type: str = Field("document", description="Type of target")
    results_summary: dict = Field(None, description="Analysis results summary")

@router.post("/session/{session_id}/events/analysis-started")
async def capture_analysis_started_event(
    session_id: str,
    request: AnalysisEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture analysis started event
    """
    try:
        if session_manager:
            success = await session_manager.capture_analysis_started(
                session_id,
                request.analysis_type,
                request.target_id,
                request.target_type
            )
            return {
                "success": success,
                "event_type": "analysis_started",
                "analysis_type": request.analysis_type
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing analysis started: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


@router.post("/session/{session_id}/events/analysis-completed")
async def capture_analysis_completed_event(
    session_id: str,
    request: AnalysisEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture analysis completed event
    """
    try:
        if session_manager:
            success = await session_manager.capture_analysis_completed(
                session_id,
                request.analysis_type,
                request.target_id,
                request.results_summary
            )
            return {
                "success": success,
                "event_type": "analysis_completed",
                "analysis_type": request.analysis_type
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session manager not initialized"
            )

    except Exception as e:
        logger.error(f"Error capturing analysis completed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error capturing event: {str(e)}"
        )


@router.delete("/project/{project_id}/thread/last-message")
async def remove_last_message_from_thread(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Remove the last message pair (user + DAS) from project thread for edit & retry
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )

        # Get the project thread
        if hasattr(engine, 'project_manager') and engine.project_manager:
            project_thread = await engine.project_manager.get_project_thread_by_project_id(project_id)
            if not project_thread:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No project thread found for project {project_id}. Project threads are created when projects are created."
                )

            # Remove last conversation entry if it exists
            if project_thread.conversation_history:
                removed_entry = project_thread.conversation_history.pop()

                # Persist the updated thread
                await engine.project_manager._persist_project_thread(project_thread)

                return {
                    "success": True,
                    "removed_message": removed_entry.get("user_message", ""),
                    "remaining_entries": len(project_thread.conversation_history)
                }
            else:
                return {
                    "success": False,
                    "message": "No conversation history to remove"
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Project intelligence not available"
            )

    except HTTPException:
        # Re-raise HTTPExceptions (like our 404s) without modification
        raise
    except Exception as e:
        logger.error(f"Error removing last message from project thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing message: {str(e)}"
        )


# Initialize DAS engine function
async def initialize_das_engine(settings: Settings, rag_service: RAGService, db_service: DatabaseService, redis_client):
    """
    Initialize the global DAS engine and session manager instances
    """
    global das_engine, session_manager
    try:
        # Get qdrant service from rag_service for project intelligence
        qdrant_service = rag_service.qdrant_service if hasattr(rag_service, 'qdrant_service') else None

        das_engine = DASCoreEngine(settings, rag_service, db_service, redis_client, qdrant_service)
        session_manager = SessionManager(settings, redis_client)
        logger.info("DAS engine and session manager initialized with project intelligence")
    except Exception as e:
        logger.error(f"Failed to initialize DAS engine: {e}")
        raise
