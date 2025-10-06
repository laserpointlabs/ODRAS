"""
DAS2 API - Simple Digital Assistant API ✅ CURRENT ACTIVE VERSION

This is the CURRENT and RECOMMENDED DAS implementation.
Use this for all new development and projects.

✅ Simple, clean architecture
✅ Direct context + LLM approach
✅ Easy to debug and maintain
✅ Better performance than DAS1
✅ NO complex intelligence layers, just context + LLM

API Endpoints:
- POST /api/das2/chat - Send message to DAS
- GET /api/das2/project/{project_id}/thread - Get project thread
- GET /api/das2/project/{project_id}/history - Get conversation history

⚠️ DO NOT USE DAS1 (/api/das/*) - it's deprecated
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

        # Use unified streaming method and collect all chunks for non-streaming response
        full_response = ""
        final_metadata = {}
        sources = []

        async for chunk in engine.process_message_stream(
            project_id=request.project_id,
            message=request.message,
            user_id=user_id,
            project_thread_id=request.project_thread_id
        ):
            if chunk.get("type") == "content":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "done":
                final_metadata = chunk.get("metadata", {})
                sources = final_metadata.get("sources", [])
            elif chunk.get("type") == "error":
                raise HTTPException(status_code=500, detail=chunk.get("message", "Unknown error"))

        return DAS2ChatResponse(
            message=full_response,
            sources=sources,
            metadata=final_metadata
        )

    except Exception as e:
        logger.error(f"DAS2 chat error: {e}")
        raise HTTPException(status_code=500, detail=f"DAS2 error: {str(e)}")


@router.post("/chat/stream")
async def das2_chat_stream(
    request: DAS2ChatRequest,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    DAS2 Chat Streaming - Streams response as it's generated
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio

    async def generate_stream():
        try:
            user_id = user.get("user_id")
            if not user_id:
                yield f"data: {json.dumps({'type': 'error', 'message': 'User not authenticated'})}\n\n"
                return

            print(f"DAS2_API_STREAM: Processing message='{request.message}' for project={request.project_id}")

            # Process with DAS2 engine and stream the response
            response_stream = engine.process_message_stream(
                project_id=request.project_id,
                message=request.message,
                user_id=user_id,
                project_thread_id=request.project_thread_id
            )

            # Stream the response
            async for chunk in response_stream:
                yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"DAS2 stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/project/{project_id}/thread")
async def get_das2_project_thread(
    project_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """Get project thread info for DAS2 (SQL-first compatible)"""
    try:
        # Get project context using SQL-first approach
        project_context = await engine.project_manager.get_project_thread_by_project_id(project_id)

        if not project_context or "error" in project_context:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}. Create a project first."
            )

        # Handle both SQL-first context format and direct thread format
        if "project_thread" in project_context:
            # From get_project_context format
            thread_data = project_context["project_thread"]
            conversation_count = len(project_context.get("conversation_history", []))
            events_count = len(project_context.get("recent_events", []))
        else:
            # Direct thread format
            thread_data = project_context
            conversation_count = 0  # Will be loaded separately
            events_count = 0  # Will be loaded separately

        return {
            "project_thread_id": thread_data["project_thread_id"],
            "project_id": thread_data["project_id"],
            "created_at": thread_data["created_at"].isoformat() if hasattr(thread_data["created_at"], "isoformat") else str(thread_data["created_at"]),
            "conversation_count": conversation_count,
            "events_count": events_count,
            "sql_first": True
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
    """Get conversation history for project (SQL-first compatible)"""
    try:
        project_context = await engine.project_manager.get_project_thread_by_project_id(project_id)

        if not project_context or "error" in project_context:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}"
            )

        # Handle SQL-first format (debug what we're getting)
        if "project_thread" in project_context:
            # SQL-first format
            print(f"🔍 DAS2_HISTORY_DEBUG: Found project_thread in context")
            print(f"   Context keys: {list(project_context.keys())}")

            conversation_history = project_context.get("conversation_history", [])
            project_thread_id = project_context["project_thread"]["project_thread_id"]

            print(f"🔍 DAS2_HISTORY_DEBUG: SQL-first conversation data")
            print(f"   Raw conversations from context: {len(conversation_history)}")
            print(f"   Thread ID: {project_thread_id}")

            if conversation_history:
                print(f"   First conversation keys: {list(conversation_history[0].keys())}")
            else:
                print(f"   ❌ No conversation_history in project_context")

            # The conversation_history is ALREADY formatted by SQL-first manager
            print(f"🔍 DAS2_HISTORY_DEBUG: Processing formatted conversations")
            print(f"   Formatted conversations count: {len(conversation_history)}")

            if conversation_history:
                print(f"   First formatted conversation keys: {list(conversation_history[0].keys())}")
                print(f"   Has user_message: {'user_message' in conversation_history[0]}")
                print(f"   Has das_response: {'das_response' in conversation_history[0]}")

            # Convert formatted conversation to DAS history format (what DAS dock expects)
            history = []
            for conv in conversation_history:
                # Handle already-formatted conversation pairs
                if conv.get("user_message"):
                    # User message
                    history.append({
                        "type": "user",
                        "message": conv["user_message"],
                        "timestamp": conv.get("timestamp"),
                        "sql_first": True
                    })

                    # Assistant response (if present)
                    if conv.get("das_response"):
                        # Prepare metadata in DAS dock expected format
                        rag_context = conv.get("rag_context", {})
                        metadata = {
                            "confidence": "medium",  # Default confidence
                            "sources": rag_context.get("sources", []),  # ← DAS dock expects this field
                            "chunks_found": rag_context.get("chunks_found", 0),
                            "sql_first": True,
                            "processing_time": conv.get("processing_time", 0)
                        }

                        print(f"🔍 DAS2_HISTORY_DEBUG: Assistant response metadata")
                        print(f"   Sources count: {len(metadata['sources'])}")
                        print(f"   Chunks found: {metadata['chunks_found']}")

                        history.append({
                            "type": "das",
                            "message": conv["das_response"],
                            "timestamp": conv.get("timestamp"),
                            "metadata": metadata,  # ← Properly formatted for DAS dock
                            "sql_first": True
                        })

            print(f"🔍 DAS2_HISTORY_DEBUG: Created {len(history)} history entries for DAS dock")
        else:
            # Legacy format fallback
            conversation_history = getattr(project_context, 'conversation_history', [])
            project_thread_id = getattr(project_context, 'project_thread_id', 'unknown')
            history = conversation_history

        return {
            "history": history,
            "project_id": project_id,
            "project_thread_id": project_thread_id,
            "sql_first": "project_thread" in project_context if project_context else False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DAS2 history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/project/{project_id}/conversation/last")
async def delete_last_conversation(
    project_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """Delete the last conversation entry (user message + DAS response) from project thread"""
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        print(f"DAS2_DELETE: Deleting last conversation for project {project_id}")

        # Get project thread
        project_context = await engine.project_manager.get_project_thread_by_project_id(project_id)
        if not project_context or "error" in project_context:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}"
            )

        project_thread_id = None
        if "project_thread" in project_context:
            project_thread_id = project_context["project_thread"]["project_thread_id"]
        else:
            project_thread_id = getattr(project_context, 'project_thread_id', None)

        if not project_thread_id:
            raise HTTPException(
                status_code=404,
                detail="Project thread ID not found"
            )

        # Delete the last conversation entry (user + assistant pair)
        success = await engine.project_manager.delete_last_conversation(project_thread_id)

        if success:
            return {"success": True, "message": "Last conversation deleted successfully"}
        else:
            return {"success": False, "message": "No conversation to delete"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting last conversation: {e}")
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

        # Project manager (SQL-first implementation)
        from ..services.sql_first_thread_manager import SqlFirstThreadManager
        project_manager = SqlFirstThreadManager(settings, qdrant_service)

        # Create DAS2 engine
        das2_engine = DAS2CoreEngine(settings, rag_service, project_manager, db_service)

        logger.info("DAS2 Engine initialized successfully - SIMPLE APPROACH")

    except Exception as e:
        logger.error(f"Failed to initialize DAS2 engine: {e}")
        raise
