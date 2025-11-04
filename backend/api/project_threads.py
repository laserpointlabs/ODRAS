"""
Project Thread Management API - UI-Only Thread Creation

This endpoint should ONLY be called by the UI when the user explicitly requests DAS functionality.
DAS systems should NEVER call these endpoints - they only work with existing project threads.

Architecture:
✅ UI creates project via /api/projects (DB only)
✅ UI separately calls /api/project-threads (if user wants DAS)
✅ DAS systems only work with existing threads, never create them
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.config import Settings
from ..services.auth import get_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project-threads", tags=["project-threads"])


class CreateProjectThreadRequest(BaseModel):
    project_id: str


class ProjectThreadResponse(BaseModel):
    success: bool
    project_thread_id: Optional[str] = None
    project_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/", response_model=ProjectThreadResponse)
async def create_project_thread(
    request: CreateProjectThreadRequest,
    user: dict = Depends(get_user)
):
    """
    Create project thread for DAS functionality

    ⚠️  IMPORTANT: This should ONLY be called by the UI when user explicitly requests DAS
    ⚠️  DAS systems should NEVER call this endpoint
    """
    try:
        user_id = user.get("user_id")
        username = user.get("username", "unknown")

        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        project_id = request.project_id

        # Verify project exists and user has access
        from ..services.db import DatabaseService
        settings = Settings()
        db = DatabaseService(settings)

        # Check project access
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.name, p.description, p.domain
                    FROM projects p
                    JOIN project_members pm ON p.project_id = pm.project_id
                    WHERE p.project_id = %s AND pm.user_id = %s AND p.is_active = true
                """, (project_id, user_id))

                project = cur.fetchone()
                if not project:
                    raise HTTPException(
                        status_code=404,
                        detail="Project not found or access denied"
                    )
        finally:
            db._return(conn)

        project_name = project[0] if project else "Unknown Project"

        # Try DAS2 first (preferred)
        thread_result = await _create_thread_with_das(project_id, user_id, username, project_name)
        if thread_result["success"]:
            return ProjectThreadResponse(**thread_result)

        # Fallback to DAS1 if DAS2 not available
        thread_result = await _create_thread_with_das1(project_id, user_id, username, project_name)
        if thread_result["success"]:
            return ProjectThreadResponse(**thread_result)

        # Neither DAS system available
        return ProjectThreadResponse(
            success=False,
            error="DAS functionality not available - neither DAS1 nor DAS2 initialized"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project thread: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project thread: {str(e)}")


async def _create_thread_with_das(project_id: str, user_id: str, username: str, project_name: str) -> Dict[str, Any]:
    """Try to create project thread with DAS"""
    try:
        from backend.api.das import das_engine

        if not das_engine or not das_engine.project_manager:
            return {"success": False, "error": "DAS not available"}

        # Check if thread already exists (SQL-first format)
        existing_context = await das_engine.project_manager.get_project_thread_by_project_id(project_id)
        if existing_context and "error" not in existing_context:
            # Extract thread ID from SQL-first format
            if "project_thread" in existing_context:
                existing_thread_id = existing_context["project_thread"]["project_thread_id"]
            else:
                existing_thread_id = existing_context.get("project_thread_id")

            if existing_thread_id:
                logger.info(f"Project thread already exists for project {project_id}")
                return {
                    "success": True,
                    "project_thread_id": existing_thread_id,
                    "project_id": project_id,
                    "message": f"Project thread already exists for '{project_name}'"
                }

        # Create new project thread (SQL-first format)
        thread_context = await das_engine.project_manager.create_project_thread(
            project_id=project_id,
            user_id=user_id
        )

        # SQL-first manager returns dict, not object
        if isinstance(thread_context, dict):
            project_thread_id = thread_context.get('project_thread_id')
        else:
            project_thread_id = getattr(thread_context, 'project_thread_id', None)

        logger.info(f"Created DAS project thread {project_thread_id} for project {project_id}")

        return {
            "success": True,
            "project_thread_id": project_thread_id,
            "project_id": project_id,
            "message": f"DAS functionality enabled for '{project_name}' (DAS2)"
        }

    except Exception as e:
        logger.warning(f"Failed to create thread with DAS2: {e}")
        return {"success": False, "error": f"DAS2 creation failed: {str(e)}"}


async def _create_thread_with_das1(project_id: str, user_id: str, username: str, project_name: str) -> Dict[str, Any]:
    """Try to create project thread with DAS1 (fallback)"""
    try:
        from backend.api.das import das_engine

        if not das_engine or not das_engine.project_manager:
            return {"success": False, "error": "DAS1 not available"}

        # Check if thread already exists
        existing_thread = await das_engine.project_manager.get_project_thread_by_project_id(project_id)
        if existing_thread:
            logger.info(f"Project thread already exists for project {project_id}")
            return {
                "success": True,
                "project_thread_id": existing_thread.project_thread_id,
                "project_id": project_id,
                "message": f"Project thread already exists for '{project_name}'"
            }

        # Create new project thread
        thread_context = await das_engine.project_manager.create_project_thread(
            project_id=project_id,
            user_id=user_id
        )

        logger.info(f"Created DAS1 project thread {thread_context.project_thread_id} for project {project_id}")

        return {
            "success": True,
            "project_thread_id": thread_context.project_thread_id,
            "project_id": project_id,
            "message": f"DAS functionality enabled for '{project_name}' (DAS1)"
        }

    except Exception as e:
        logger.warning(f"Failed to create thread with DAS1: {e}")
        return {"success": False, "error": f"DAS1 creation failed: {str(e)}"}


@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project_thread_info(
    project_id: str,
    user: dict = Depends(get_user)
):
    """Get project thread information"""
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Try DAS first
        das_info = await _get_thread_info_das(project_id, user_id)
        if das_info.get("found"):
            return ProjectThreadInfoResponse(**das_info)

        # Try DAS1
        das1_info = await _get_thread_info_das1(project_id, user_id)
        if das1_info["found"]:
            return das1_info

        # No thread found in either system
        return {
            "found": False,
            "project_id": project_id,
            "message": "No project thread found - DAS functionality not enabled for this project"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project thread info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_thread_info_das(project_id: str, user_id: str) -> Dict[str, Any]:
    """Get project thread info from DAS"""
    try:
        from backend.api.das import das_engine

        if not das_engine or not das_engine.project_manager:
            return {"found": False}

        thread_context = await das_engine.project_manager.get_project_thread_by_project_id(project_id)
        if not thread_context:
            return {"found": False}

        return {
            "found": True,
            "project_thread_id": thread_context.project_thread_id,
            "project_id": project_id,
            "created_at": thread_context.created_at.isoformat(),
            "conversation_count": len(thread_context.conversation_history),
            "events_count": len(thread_context.project_events),
            "das_version": "DAS2",
            "last_activity": thread_context.last_activity.isoformat()
        }

    except Exception as e:
        logger.warning(f"Failed to get DAS2 thread info: {e}")
        return {"found": False}


async def _get_thread_info_das1(project_id: str, user_id: str) -> Dict[str, Any]:
    """Get project thread info from DAS1"""
    try:
        from backend.api.das import das_engine

        if not das_engine or not das_engine.project_manager:
            return {"found": False}

        thread_context = await das_engine.project_manager.get_project_thread_by_project_id(project_id)
        if not thread_context:
            return {"found": False}

        return {
            "found": True,
            "project_thread_id": thread_context.project_thread_id,
            "project_id": project_id,
            "created_at": thread_context.created_at.isoformat(),
            "conversation_count": len(thread_context.conversation_history),
            "events_count": len(thread_context.project_events),
            "das_version": "DAS1",
            "last_activity": thread_context.last_activity.isoformat()
        }

    except Exception as e:
        logger.warning(f"Failed to get DAS1 thread info: {e}")
        return {"found": False}
