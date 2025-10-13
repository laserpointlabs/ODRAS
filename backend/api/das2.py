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
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.das2_core_engine import DAS2CoreEngine, DAS2Response
from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.project_thread_manager import ProjectThreadManager
from ..services.auth import get_user
from ..services.db import DatabaseService

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
            
            # Monitor connection pool before processing
            try:
                settings = Settings()
                db_service = DatabaseService(settings)
                pool_status = db_service.get_pool_status()
                logger.info(f"🔍 DAS2_STREAM: Pool status before - In use: {pool_status.get('connections_in_use', 0)}/{pool_status.get('maxconn', 40)}")
                
                if pool_status.get('leaked_connections', 0) > 0:
                    logger.warning(f"⚠️ DAS2_STREAM: {pool_status['leaked_connections']} potentially leaked connections detected")
            except Exception as e:
                logger.warning(f"Failed to check pool status: {e}")

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
                
            # Monitor connection pool after processing
            try:
                post_pool_status = db_service.get_pool_status()
                logger.info(f"🔍 DAS2_STREAM: Pool status after - In use: {post_pool_status.get('connections_in_use', 0)}/{post_pool_status.get('maxconn', 40)}")
                
                # Detect connection leaks (increase in connections during request)
                pre_connections = pool_status.get('connections_in_use', 0)
                post_connections = post_pool_status.get('connections_in_use', 0)
                if post_connections > pre_connections:
                    logger.warning(f"🚨 DAS2_STREAM: Possible connection leak - increased from {pre_connections} to {post_connections}")
            except Exception as e:
                logger.warning(f"Failed to check pool status after processing: {e}")

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


@router.get("/project/{project_id}/prompt-context")
async def get_prompt_context(
    project_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Get the DAS prompt context for a project without running LLMs.
    This endpoint shows exactly what context would be sent to the LLM.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        print(f"DAS2_PROMPT_CONTEXT: Getting prompt context for project {project_id}")

        # Get project thread context (same as streaming method)
        project_context = await engine.project_manager.get_project_context(project_id)
        if not project_context or "error" in project_context:
            raise HTTPException(
                status_code=404,
                detail=f"No project thread found for project {project_id}"
            )

        # Extract components
        conversation_history = project_context.get("conversation_history", [])
        recent_events = project_context.get("recent_events", [])
        project_metadata = project_context.get("project_metadata", {})

        # Build context sections (same as streaming method)
        context_sections = []

        # Add conversation history
        if conversation_history:
            context_sections.append("CONVERSATION HISTORY:")

            # Handle both new format (conversation pairs) and legacy format
            if isinstance(conversation_history, list) and conversation_history and isinstance(conversation_history[0], dict):
                if "user_message" in conversation_history[0] and "das_response" in conversation_history[0]:
                    # New format: conversation pairs
                    for conv in conversation_history[-10:]:
                        user_msg = conv.get("user_message", "")
                        das_response = conv.get("das_response", "")
                        if user_msg:
                            context_sections.append(f"User: {user_msg}")
                        if das_response:
                            context_sections.append(f"DAS: {das_response}")
                        context_sections.append("")
                else:
                    # Legacy format: individual role/content messages
                    for conv in conversation_history[-10:]:
                        role = conv.get("role", "")
                        content = conv.get("content", "")
                        if role and content:
                            if role == "user":
                                context_sections.append(f"User: {content}")
                            elif role == "assistant":
                                context_sections.append(f"DAS: {content}")
                            context_sections.append("")

        # Add project context
        context_sections.append("PROJECT CONTEXT:")

        # Get comprehensive project details
        project_details = None
        if hasattr(engine, 'db_service') and engine.db_service:
            try:
                project_details = engine.db_service.get_project_comprehensive(project_id)
            except Exception as e:
                print(f"DAS2_PROMPT_CONTEXT: Failed to get project details: {e}")
        elif hasattr(engine.project_manager, 'db_service') and engine.project_manager.db_service:
            try:
                project_details = engine.project_manager.db_service.get_project_comprehensive(project_id)
            except Exception as e:
                print(f"DAS2_PROMPT_CONTEXT: Failed to get project details via project_manager: {e}")

        if project_details:
            context_sections.append(f"Project: {project_details.get('name', 'Unknown')} (ID: {project_id})")

            if project_details.get('description'):
                context_sections.append(f"Description: {project_details.get('description')}")

            if project_details.get('domain'):
                context_sections.append(f"Domain: {project_details.get('domain')}")

            if project_details.get('creator_username'):
                context_sections.append(f"Created by: {project_details.get('creator_username')}")

            if project_details.get('created_at'):
                context_sections.append(f"Created: {project_details.get('created_at')}")

            # Namespace information
            if project_details.get('namespace_name'):
                context_sections.append(f"Namespace: {project_details.get('namespace_name')} ({project_details.get('namespace_path', 'N/A')})")
                if project_details.get('namespace_description'):
                    context_sections.append(f"Namespace description: {project_details.get('namespace_description')}")
                if project_details.get('namespace_status'):
                    context_sections.append(f"Namespace status: {project_details.get('namespace_status')}")

            # Project URI
            if project_details.get('project_uri'):
                context_sections.append(f"Project URI: {project_details.get('project_uri')}")
        else:
            context_sections.append(f"Project ID: {project_id} (details unavailable)")

        # Add comprehensive project metadata
        if project_metadata:
            # Files in project
            files = project_metadata.get('files', [])
            if files:
                context_sections.append("PROJECT FILES:")
                for file_info in files:
                    title = file_info.get('title', 'Unknown')
                    doc_type = file_info.get('document_type', 'document')
                    filename = file_info.get('filename', 'unknown')
                    context_sections.append(f"• {title} ({doc_type}) - {filename}")

            # Ontologies in project with full details from Fuseki
            ontologies = project_metadata.get('ontologies', [])
            if ontologies:
                context_sections.append("PROJECT ONTOLOGIES:")
                for ontology_info in ontologies:
                    graph_iri = ontology_info.get('graph_iri')
                    label = ontology_info.get('label', 'Unknown Ontology')
                    role = ontology_info.get('role', 'base')

                    context_sections.append(f"  {label} ({role}):")

                    # Fetch comprehensive ontology details
                    if graph_iri:
                        try:
                            ontology_details = await engine._fetch_ontology_details(graph_iri)
                            if ontology_details:
                                engine._add_ontology_content_to_context(context_sections, ontology_details, "    ")
                        except Exception as e:
                            print(f"DAS2_PROMPT_CONTEXT: Failed to fetch ontology details for {graph_iri}: {e}")
                            context_sections.append("    [Ontology details unavailable]")

        # Add recent project activity
        if recent_events:
            context_sections.append("RECENT PROJECT ACTIVITY:")
            for event in recent_events[-20:]:  # Last 20 events
                event_type = event.get("event_type", "")
                summary = event.get("summary", "")
                timestamp = event.get("timestamp", "")
                if event_type and summary:
                    if timestamp:
                        context_sections.append(f"• {event_type}: {summary} ({timestamp})")
                    else:
                        context_sections.append(f"• {event_type}: {summary}")

        # Build the complete context
        full_context = "\n".join(context_sections)

        # Build the complete prompt that would be sent to LLM
        complete_prompt = f"""You are DAS, a digital assistant for this project. Answer the user's question using ALL the context provided.

IMPORTANT INSTRUCTIONS:
1. ALWAYS use the provided context as the authoritative source
2. If information is in the context, state it confidently
3. If information is NOT in the context, clearly say "I don't have that information"
4. For ambiguous pronouns (it, its, that) without clear context, ask for clarification
5. For comprehensive queries (tables, lists), include ALL relevant information
6. For questions outside this project's domain, politely redirect
7. NEVER contradict previous responses - be consistent
8. When context is unclear or missing, ask specific clarifying questions

{full_context}

USER QUESTION: [User's question would go here]

Provide a natural, helpful response using whatever context is relevant. Reference conversation history for "what did I ask" type questions. Use knowledge from documents when relevant. Be conversational."""

        return {
            "project_id": project_id,
            "context_sections": context_sections,
            "full_context": full_context,
            "complete_prompt": complete_prompt,
            "context_stats": {
                "total_sections": len(context_sections),
                "conversation_entries": len(conversation_history),
                "recent_events": len(recent_events),
                "ontologies": len(project_metadata.get('ontologies', [])),
                "files": len(project_metadata.get('files', [])),
                "context_length": len(full_context),
                "prompt_length": len(complete_prompt)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt context: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/connections")
async def get_connection_health(user: dict = Depends(get_user)):
    """
    Get database connection pool health status for DAS monitoring
    """
    try:
        settings = Settings()
        db_service = DatabaseService(settings)
        
        pool_status = db_service.get_pool_status()
        
        # Add warnings for potential issues
        warnings = []
        if pool_status.get("leaked_connections", 0) > 0:
            warnings.append(f"{pool_status['leaked_connections']} potentially leaked connections detected")
            
        if pool_status.get("connections_in_use", 0) > (pool_status.get("maxconn", 40) * 0.8):
            warnings.append(f"High connection usage: {pool_status['connections_in_use']}/{pool_status['maxconn']}")
        
        return {
            "status": "healthy" if not warnings else "warning",
            "pool_status": pool_status,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting connection health: {e}")
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
