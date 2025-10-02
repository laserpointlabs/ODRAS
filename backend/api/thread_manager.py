"""
Thread Manager API - Debug and Manage DAS Project Threads

Provides CRUD operations for conversation history debugging and management.
Allows inspection of prompts, context, and conversation entries.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..services.das2_core_engine import DAS2CoreEngine
from ..services.project_thread_manager import ProjectThreadManager
from ..services.config import Settings
from ..services.rag_service import RAGService
from ..services.auth import get_user

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/thread-manager", tags=["Thread Manager"])

# Request/Response Models
class ConversationEntry(BaseModel):
    timestamp: str
    user_message: str
    das_response: str
    prompt_context: Optional[str] = None
    rag_context: Optional[Dict[str, Any]] = None
    project_context: Optional[Dict[str, Any]] = None
    thread_metadata: Optional[Dict[str, Any]] = None

class ThreadOverview(BaseModel):
    project_thread_id: str
    project_id: str
    project_name: Optional[str] = None
    created_at: str
    last_activity: str
    conversation_count: int
    project_events_count: int
    current_workbench: Optional[str] = None

class ConversationUpdate(BaseModel):
    user_message: Optional[str] = None
    das_response: Optional[str] = None

class PromptTestRequest(BaseModel):
    custom_prompt: str
    project_id: str
    simulate_only: bool = True

# Global engine instance - reuse DAS2 engine
das2_engine: Optional[DAS2CoreEngine] = None

async def get_das2_engine() -> DAS2CoreEngine:
    """Get DAS2 engine dependency"""
    global das2_engine
    if not das2_engine:
        # Initialize if needed
        from ..api.das2 import das2_engine as shared_engine
        das2_engine = shared_engine
        if not das2_engine:
            raise HTTPException(status_code=503, detail="DAS2 engine not initialized")
    return das2_engine


@router.get("/threads", response_model=List[ThreadOverview])
async def list_project_threads(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    List all project threads for debugging.
    Optionally filter by project_id.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get project manager from DAS2 engine
        project_manager = engine.project_manager
        if not project_manager:
            raise HTTPException(status_code=503, detail="Project manager not available")

        # Use SQL-first thread manager to list threads
        project_manager = engine.project_manager

        # Check if we're using SQL-first manager
        if hasattr(project_manager, 'list_threads'):
            threads_data = await project_manager.list_threads(project_id=project_id)

            # Convert to ThreadOverview format
            threads = []
            for thread_data in threads_data:
                thread_overview = ThreadOverview(
                    project_thread_id=thread_data["project_thread_id"],
                    project_id=thread_data["project_id"],
                    created_by=thread_data["created_by"],
                    created_at=thread_data["created_at"],
                    last_activity=thread_data["last_activity"],
                    status=thread_data.get("status", "active"),
                    current_workbench=thread_data.get("current_workbench", "unknown"),
                    conversation_count=thread_data.get("conversation_count", 0),
                    project_events_count=thread_data.get("project_events_count", 0)
                )
                threads.append(thread_overview)

            logger.info(f"Listed {len(threads)} threads for project {project_id}")
            return threads
        else:
            # Legacy fallback
            logger.warning("Using legacy thread manager - limited functionality")
            return []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}")


@router.get("/threads/{project_thread_id}", response_model=Dict[str, Any])
async def get_project_thread_details(
    project_thread_id: str,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Get complete project thread details including full conversation history.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get project thread (SQL-first format)
        project_thread = await engine.project_manager.get_project_thread(project_thread_id)
        if not project_thread:
            raise HTTPException(status_code=404, detail="Project thread not found")

        # Get project details for context
        project_details = None
        if engine.db_service:
            try:
                project_details = engine.db_service.get_project_comprehensive(project_thread["project_id"])
            except Exception as e:
                logger.warning(f"Could not get project details: {e}")

        # Return data in expected format (SQL-first manager already formats correctly)
        result = {
            **project_thread,  # Spread the SQL-first formatted data
            "project_details": project_details
        }

        logger.info(f"Retrieved thread details for {project_thread_id} - SQL-first: {result.get('sql_first', False)}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get thread details: {str(e)}")


@router.get("/threads/{project_thread_id}/conversation/{entry_index}")
async def get_conversation_entry(
    project_thread_id: str,
    entry_index: int,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Get specific conversation entry with full prompt context for debugging.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get project thread (SQL-first format)
        project_thread = await engine.project_manager.get_project_thread(project_thread_id)
        if not project_thread:
            raise HTTPException(status_code=404, detail="Project thread not found")

        # Get conversation history (SQL-first format)
        conversation_history = project_thread.get("conversation_history", [])

        # Check entry index
        if entry_index < 0 or entry_index >= len(conversation_history):
            raise HTTPException(status_code=404, detail="Conversation entry not found")

        entry = conversation_history[entry_index]

        return {
            "entry_index": entry_index,
            "entry": entry,
            "total_entries": len(conversation_history),
            "project_thread_id": project_thread_id,
            "sql_first": project_thread.get("sql_first", False)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation entry: {str(e)}")


@router.put("/threads/{project_thread_id}/conversation/{entry_index}")
async def update_conversation_entry(
    project_thread_id: str,
    entry_index: int,
    update_data: ConversationUpdate,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Update a conversation entry for debugging/testing purposes.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get project thread
        project_thread = await engine.project_manager.get_project_thread(project_thread_id)
        if not project_thread:
            raise HTTPException(status_code=404, detail="Project thread not found")

        # Check entry index
        if entry_index < 0 or entry_index >= len(project_thread.conversation_history):
            raise HTTPException(status_code=404, detail="Conversation entry not found")

        # Update entry
        entry = project_thread.conversation_history[entry_index]
        if update_data.user_message is not None:
            entry["user_message"] = update_data.user_message
        if update_data.das_response is not None:
            entry["das_response"] = update_data.das_response

        # Add update metadata
        entry["updated_at"] = datetime.now().isoformat()
        entry["updated_by"] = user_id

        # Persist changes
        await engine.project_manager._persist_project_thread(project_thread)

        return {
            "success": True,
            "updated_entry": entry,
            "entry_index": entry_index
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update conversation entry: {str(e)}")


@router.delete("/threads/{project_thread_id}/conversation/{entry_index}")
async def delete_conversation_entry(
    project_thread_id: str,
    entry_index: int,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Delete a conversation entry for cleaning up test data.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get project thread
        project_thread = await engine.project_manager.get_project_thread(project_thread_id)
        if not project_thread:
            raise HTTPException(status_code=404, detail="Project thread not found")

        # Check entry index
        if entry_index < 0 or entry_index >= len(project_thread.conversation_history):
            raise HTTPException(status_code=404, detail="Conversation entry not found")

        # Remove entry
        deleted_entry = project_thread.conversation_history.pop(entry_index)

        # Persist changes
        await engine.project_manager._persist_project_thread(project_thread)

        return {
            "success": True,
            "deleted_entry": deleted_entry,
            "remaining_entries": len(project_thread.conversation_history)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation entry: {str(e)}")


@router.post("/threads/{project_thread_id}/test-prompt")
async def test_custom_prompt(
    project_thread_id: str,
    request: PromptTestRequest,
    user: dict = Depends(get_user),
    engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Test a custom prompt with current project context.
    Useful for debugging prompt engineering.
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        if request.simulate_only:
            # Just return what the prompt would be without calling LLM
            return {
                "simulated": True,
                "custom_prompt": request.custom_prompt,
                "project_id": request.project_id,
                "would_call_llm": True,
                "note": "Set simulate_only=false to actually call LLM"
            }
        else:
            # Actually call LLM with custom prompt
            # This is a simplified implementation - you'd want more sophisticated handling
            response_text = await engine._call_llm_directly(request.custom_prompt)

            return {
                "simulated": False,
                "custom_prompt": request.custom_prompt,
                "llm_response": response_text,
                "project_id": request.project_id,
                "timestamp": datetime.now().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing custom prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test custom prompt: {str(e)}")
