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

from ..services.das_core_engine import DASCoreEngine, DASResponse, DASSession
from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.db import DatabaseService
from ..services.auth import get_user as get_current_user

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/das", tags=["DAS"])

# Global DAS engine instance (will be initialized in main.py)
das_engine: Optional[DASCoreEngine] = None


# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")
    session_id: Optional[str] = Field(None, description="Existing session ID")


class ChatResponse(BaseModel):
    message: str
    confidence: str
    intent: str
    suggestions: List[Dict[str, Any]] = []
    commands: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class SessionCreateRequest(BaseModel):
    project_id: Optional[str] = Field(None, description="Active project ID")


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    start_time: str
    active_project: Optional[str]
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
        
        # Get or create session
        if request.session_id:
            session = await engine.get_session(request.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
        else:
            # Create new session
            session = await engine.start_session(user_id)
        
        # Process message
        response = await engine.process_message(
            session.session_id, 
            request.message, 
            user_id
        )
        
        # Convert to API response
        return ChatResponse(
            message=response.message,
            confidence=response.confidence.value,
            intent=response.intent.value,
            suggestions=response.suggestions or [],
            commands=response.commands or [],
            artifacts=response.artifacts or [],
            metadata=response.metadata or {}
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get chat history for a session
    """
    try:
        session = await engine.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        # Return activity log as chat history
        history = []
        for activity in session.activity_log:
            if activity.activity_type in ["user_input", "das_response"]:
                history.append({
                    "type": activity.activity_type,
                    "timestamp": activity.timestamp.isoformat(),
                    "data": activity.data
                })
        
        return {"session_id": session_id, "history": history}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chat history: {str(e)}"
        )


# Session management endpoints
@router.post("/session/start", response_model=SessionResponse)
async def start_session(
    request: SessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Start a new DAS session
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        session = await engine.start_session(user_id, request.project_id)
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            start_time=session.start_time.isoformat(),
            active_project=session.active_project,
            status="active"
        )
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting session: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get session information
    """
    try:
        session = await engine.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            start_time=session.start_time.isoformat(),
            active_project=session.active_project,
            status="active"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def end_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    End a DAS session
    """
    try:
        session = await engine.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        success = await engine.end_session(session_id)
        
        return {"success": success, "message": "Session ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
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
@router.get("/suggestions/{session_id}")
async def get_suggestions(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    engine: DASCoreEngine = Depends(get_das_engine)
):
    """
    Get suggestions for a session
    """
    try:
        session = await engine.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check user access
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        # For now, return basic suggestions based on session context
        suggestions = []
        
        if session.active_project:
            suggestions.append({
                "id": "analyze_project",
                "title": "Analyze Project",
                "description": "Run requirements analysis on your active project",
                "action": "run_analysis",
                "confidence": "high",
                "category": "analysis_workflows"
            })
        
        suggestions.extend([
            {
                "id": "browse_ontologies",
                "title": "Browse Ontologies",
                "description": "View available ontologies in the system",
                "action": "list_ontologies",
                "confidence": "medium",
                "category": "ontology_management"
            },
            {
                "id": "upload_document",
                "title": "Upload Document",
                "description": "Upload a new document for analysis",
                "action": "upload_document",
                "confidence": "medium",
                "category": "file_operations"
            }
        ])
        
        return {"suggestions": suggestions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving suggestions: {str(e)}"
        )


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


# Initialize DAS engine function
async def initialize_das_engine(settings: Settings, rag_service: RAGService, db_service: DatabaseService):
    """
    Initialize the global DAS engine instance
    """
    global das_engine
    try:
        das_engine = DASCoreEngine(settings, rag_service, db_service)
        logger.info("DAS engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DAS engine: {e}")
        raise
