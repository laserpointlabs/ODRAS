"""
DAS Simple API - Clean implementation aligned with session thread architecture

Provides basic DAS chat functionality using existing RAG service with session thread integration.
No overcomplicated engines or canned responses.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.db import DatabaseService
from ..services.auth import get_user as get_current_user

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/das", tags=["DAS"])

# Global instances
rag_service: Optional[RAGService] = None
redis_client = None
session_thread_service = None


# Request/Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")
    session_thread_id: Optional[str] = Field(None, description="Current session thread ID")
    project_id: Optional[str] = Field(None, description="Current project ID for context")
    ontology_id: Optional[str] = Field(None, description="Current ontology ID for context")
    workbench: Optional[str] = Field(None, description="Current workbench")


class ChatResponse(BaseModel):
    message: str
    confidence: str
    session_thread_id: str
    metadata: Dict[str, Any] = {}


class SessionThreadResponse(BaseModel):
    session_thread_id: str
    username: str
    start_time: str
    status: str


# Simple session thread management
async def create_session_thread(username: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new session thread for user"""
    session_thread_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Store in Redis
    thread_data = {
        "session_thread_id": session_thread_id,
        "username": username,
        "start_time": start_time.isoformat(),
        "project_id": project_id,
        "events": [],
        "session_goals": None,
        "status": "active"
    }
    
    if redis_client:
        await redis_client.set(
            f"session_thread:{session_thread_id}",
            json.dumps(thread_data),
            ex=86400  # 24 hours
        )
        
        # Log session start event
        await log_session_event(
            session_thread_id=session_thread_id,
            event_type="session_start",
            event_data={"username": username, "project_id": project_id}
        )
    
    logger.info(f"Created session thread {session_thread_id} for user {username}")
    return thread_data


async def log_session_event(session_thread_id: str, event_type: str, event_data: Dict[str, Any]):
    """Log an event to the session thread"""
    if not redis_client:
        return
        
    event = {
        "event_id": str(uuid.uuid4()),
        "session_thread_id": session_thread_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "event_data": event_data
    }
    
    # Add to Redis event queue for background processing
    await redis_client.lpush("session_events", json.dumps(event))
    logger.debug(f"Logged event {event_type} for session thread {session_thread_id}")


# API Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat_with_das(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Simple DAS chat using existing RAG service
    """
    try:
        username = current_user.get("username")
        user_id = current_user.get("user_id")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Get or create session thread
        session_thread_id = request.session_thread_id
        if not session_thread_id:
            thread_data = await create_session_thread(username, request.project_id)
            session_thread_id = thread_data["session_thread_id"]
        
        # Log user message
        await log_session_event(
            session_thread_id=session_thread_id,
            event_type="user_message",
            event_data={
                "message": request.message,
                "project_id": request.project_id,
                "ontology_id": request.ontology_id,
                "workbench": request.workbench
            }
        )
        
        # Use existing RAG service (no complex DAS engine)
        if rag_service:
            rag_response = await rag_service.query_knowledge_base(
                question=request.message,
                project_id=request.project_id,
                user_id=user_id,
                max_chunks=5,
                similarity_threshold=0.3,
                include_metadata=True,
                response_style="comprehensive"
            )
            
            response_message = rag_response.get("response", "I couldn't process your request.")
            confidence = rag_response.get("confidence", "low")
            
        else:
            response_message = "DAS service not available"
            confidence = "low"
        
        # Log DAS response
        await log_session_event(
            session_thread_id=session_thread_id,
            event_type="das_response", 
            event_data={
                "response": response_message,
                "confidence": confidence
            }
        )
        
        return ChatResponse(
            message=response_message,
            confidence=confidence,
            session_thread_id=session_thread_id,
            metadata={
                "processing_time": datetime.now().isoformat(),
                "rag_used": bool(rag_service)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in DAS chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DAS error: {str(e)}"
        )


@router.post("/session/start", response_model=SessionThreadResponse)
async def start_session_thread(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Start a new session thread"""
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        thread_data = await create_session_thread(username, project_id)
        
        return SessionThreadResponse(
            session_thread_id=thread_data["session_thread_id"],
            username=thread_data["username"],
            start_time=thread_data["start_time"],
            status=thread_data["status"]
        )
        
    except Exception as e:
        logger.error(f"Error starting session thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting session thread: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """DAS health check"""
    return {
        "status": "healthy",
        "service": "DAS Simple",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@router.get("/llm/health")
async def llm_health_check():
    """LLM health check endpoint (for frontend compatibility)"""
    try:
        # Test LLM connectivity if available
        if rag_service:
            return {
                "status": "healthy",
                "service": "LLM",
                "provider": "integrated_with_rag",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unavailable",
                "service": "LLM", 
                "error": "RAG service not initialized",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "LLM",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Initialize function
async def initialize_simple_das(settings: Settings, rag_svc: RAGService, redis_client_instance):
    """Initialize simple DAS with existing services"""
    global rag_service, redis_client, session_thread_service
    rag_service = rag_svc
    redis_client = redis_client_instance
    
    # Initialize session thread service
    from ..services.session_thread_service import SessionThreadService
    session_thread_service = SessionThreadService(settings, redis_client_instance)
    
    logger.info("Simple DAS initialized successfully")
