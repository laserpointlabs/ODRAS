"""
DAS2 API - Simple Digital Assistant API
NO complex intelligence, just context + LLM
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.das2_core_engine import DAS2CoreEngine, DAS2Response
from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.project_thread_manager import ProjectThreadManager
from ..services.auth import get_user

logger = logging.getLogger(__name__)

# Simple request models
class DAS2ChatRequest(BaseModel):
    message: str
    project_id: str
    project_thread_id: Optional[str] = None

class DAS2ChatResponse(BaseModel):
    message: str
    sources: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

# Router
router = APIRouter(prefix="/api/das2", tags=["DAS2"])

# Global engine instance
das2_engine: Optional[DAS2CoreEngine] = None


async def get_das2_engine() -> DAS2CoreEngine:
    """Get DAS2 engine dependency"""
    global das2_engine
    if not das2_engine:
        raise HTTPException(status_code=503, detail="DAS2 not initialized")
    return das2_engine


@router.post("/chat", response_model=DAS2ChatResponse)
async def das2_chat(
    request: DAS2ChatRequest,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    DAS2 Chat - Simple approach
    Sends ALL context to LLM and returns response with sources
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        print(f"DAS2_API: Processing message='{request.message}' for project={request.project_id}")

        # Process with DAS2 engine (simple approach)
        response = await engine.process_message(
            project_id=request.project_id,
            message=request.message,
            user_id=user_id,
            project_thread_id=request.project_thread_id
        )

        return DAS2ChatResponse(
            message=response.message,
            sources=response.sources,
            metadata=response.metadata
        )

    except Exception as e:
        logger.error(f"DAS2 chat error: {e}")
        raise HTTPException(status_code=500, detail=f"DAS2 error: {str(e)}")


@router.get("/project/{project_id}/thread")
async def get_das2_project_thread(
    project_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """Get project thread info for DAS2"""
    try:
        project_thread = await engine.project_manager.get_project_thread_by_project_id(project_id)

        if not project_thread:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}. Create a project first."
            )

        return {
            "project_thread_id": project_thread.project_thread_id,
            "project_id": project_thread.project_id,
            "created_at": project_thread.created_at.isoformat(),
            "conversation_count": len(project_thread.conversation_history),
            "events_count": len(project_thread.project_events)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DAS2 thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/history")
async def get_das2_conversation_history(
    project_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """Get conversation history for project"""
    try:
        project_thread = await engine.project_manager.get_project_thread_by_project_id(project_id)

        if not project_thread:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}"
            )

        return {
            "history": project_thread.conversation_history,
            "project_id": project_id,
            "project_thread_id": project_thread.project_thread_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DAS2 history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Initialize DAS2 engine
async def initialize_das2_engine():
    """Initialize DAS2 engine with required services"""
    global das2_engine

    try:
        # Import here to avoid circular imports
        from ..services.qdrant_service import QdrantService
        from ..services.db import DatabaseService
        import redis.asyncio as redis

        settings = Settings()

        # Initialize services
        qdrant_service = QdrantService(settings)
        db_service = DatabaseService(settings)
        rag_service = RAGService(settings)

        # Redis (optional)
        redis_client = None
        try:
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            logger.info("DAS2: Redis connected")
        except Exception as e:
            logger.warning(f"DAS2: Redis not available: {e}")

        # Project manager (reuse existing)
        project_manager = ProjectThreadManager(settings, redis_client, qdrant_service)

        # Create DAS2 engine
        das2_engine = DAS2CoreEngine(settings, rag_service, project_manager)

        logger.info("DAS2 Engine initialized successfully - SIMPLE APPROACH")

    except Exception as e:
        logger.error(f"Failed to initialize DAS2 engine: {e}")
        raise
