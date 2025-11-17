"""
Core API endpoints for ODRAS.

Provides authentication, health checks, sync operations, and project management.
"""

import logging
import secrets
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Header
from pydantic import BaseModel

from ..services.auth import get_user as auth_get_user, get_admin_user
from ..services.db import DatabaseService
from ..services.config import Settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["core"])

# Global database instance (will be set during app initialization)
db: Optional[DatabaseService] = None


def set_db_instance(database_service: DatabaseService):
    """Set the global database instance (called during app initialization)"""
    global db
    db = database_service


def get_db_service() -> DatabaseService:
    """Get the global database instance"""
    global db
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db


# Use auth_get_user directly as dependency
get_user = auth_get_user




# Authentication endpoints
@router.post("/api/auth/login")
def login(body: Dict):
    """Login and get authentication token"""
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    # Use new authentication service
    try:
        from ..services.auth_service import AuthService

        if not db:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        auth_service = AuthService(db)

        # Authenticate user with password
        user = auth_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Generate token
        token = secrets.token_hex(16)

        # Store token in persistent database (using auth service)
        from ..services.auth import create_token as auth_create_token
        auth_create_token(
            user_id=user["user_id"],
            username=user["username"],
            is_admin=user["is_admin"],
            token=token,
        )

        return {"token": token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/api/auth/me")
def me(user=Depends(get_user)):
    """Get current user information"""
    return user


@router.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate the current token"""
    if not authorization:
        raise HTTPException(status_code=400, detail="No authorization header provided")
    
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="No token provided")

    token = authorization.split(" ", 1)[1]
    try:
        from ..services.auth import invalidate_token as auth_invalidate_token
        auth_invalidate_token(token)
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return {"message": "Logged out successfully"}  # Don't reveal errors to client


@router.post("/api/auth/logout-all")
def logout_all():
    """Logout all users by invalidating all tokens (admin operation for clean process)"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        # Clear all tokens from database
        conn = db._conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM auth_tokens")
                conn.commit()
        finally:
            db._return(conn)

        return {"message": "All users logged out successfully", "tokens_cleared": True}
    except Exception as e:
        logger.error(f"Failed to logout all users: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout all users")


# Health check endpoints
@router.get("/api/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {"database": "connected", "api": "running"},
    }


@router.get("/api/sync/health")
async def sync_health_check(project_id: Optional[str] = None, user=Depends(get_user)):
    """Check vector/SQL synchronization health - CRITICAL for DAS reliability"""
    try:
        from ..services.vector_sql_sync_monitor import get_sync_monitor

        monitor = get_sync_monitor()
        health_report = await monitor.check_sync_health(project_id)

        return health_report

    except Exception as e:
        logger.error(f"Sync health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync health check failed: {str(e)}")


@router.post("/api/sync/emergency-recovery")
async def emergency_sync_recovery(
    project_id: str = Body(..., description="Project ID to recover"),
    user=Depends(get_admin_user)  # Admin only for safety
):
    """Emergency recovery for vector/SQL desync - fixes DAS 'no information available' issues"""
    try:
        from ..services.vector_sql_sync_monitor import emergency_das_recovery

        recovery_result = await emergency_das_recovery(project_id)

        if recovery_result["success"]:
            return {
                "success": True,
                "message": f"Recovered {recovery_result['recovered_chunks']} chunks for project {project_id}",
                "details": recovery_result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Recovery failed: {recovery_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Emergency sync recovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency recovery failed: {str(e)}")


@router.get("/api/sync/quick-check/{project_id}")
async def quick_sync_check(project_id: str, user=Depends(get_user)):
    """Quick check if DAS will work for a project - prevents 'no information available' surprises"""
    try:
        from ..services.vector_sql_sync_monitor import check_das_will_work

        will_work = await check_das_will_work(project_id)

        return {
            "project_id": project_id,
            "das_will_work": will_work,
            "status": "ready" if will_work else "sync_issue",
            "message": "DAS ready" if will_work else "⚠️ DAS may return 'no information available' - vector store sync issue detected"
        }

    except Exception as e:
        logger.error(f"Quick sync check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick check failed: {str(e)}")


# Project management endpoints
@router.get("/api/projects")
def list_projects(state: Optional[str] = None, user=Depends(get_user)):
    """List projects for the current user"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        active = True
        if state == "archived":
            active = False
        elif state == "all":
            active = None
        rows = db.list_projects_for_user(user_id=user["user_id"], active=active)
        return {"projects": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects")
async def create_project(body: Dict, user=Depends(get_user)):
    """Create a new project"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    name = (body.get("name") or "").strip()
    namespace_id = body.get("namespace_id")
    domain = body.get("domain")
    project_level = body.get("project_level")
    parent_project_id = body.get("parent_project_id")
    tenant_id = body.get("tenant_id")
    
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    
    # Validate project level if provided
    if project_level is not None:
        if not isinstance(project_level, int) or project_level not in [0, 1, 2, 3]:
            raise HTTPException(
                status_code=400, 
                detail="Project level must be 0 (L0), 1 (L1), 2 (L2), or 3 (L3)"
            )

    # Validate namespace if provided
    if namespace_id:
        try:
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM namespace_registry WHERE id = %s AND status = 'released'",
                        (namespace_id,),
                    )
                    if not cur.fetchone():
                        raise HTTPException(
                            status_code=400,
                            detail="Namespace not found or not released",
                        )
            finally:
                db._return(conn)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error validating namespace: {e}")

    try:
        proj = db.create_project(
            name=name,
            owner_user_id=user["user_id"],
            description=(body.get("description") or None),
            namespace_id=namespace_id,
            domain=domain,
            project_level=project_level,
            parent_project_id=parent_project_id,
            tenant_id=tenant_id,
        )

        # Create project thread automatically (NOT via DAS - via direct service call)
        try:
            from ..api.project_threads import _create_thread_with_das
            thread_result = await _create_thread_with_das(proj["project_id"], user["user_id"], user.get("username", "unknown"), name)
            if thread_result["success"]:
                logger.info(f"Created project thread automatically for project '{name}' - {thread_result['message']}")
            else:
                logger.warning(f"Could not create project thread: {thread_result.get('error', 'Unknown error')}")
        except Exception as thread_error:
            logger.warning(f"Project thread creation failed: {thread_error}")
            # Don't fail project creation if thread creation fails

        # EventCapture2: Capture project creation event directly
        try:
            from ..services.eventcapture2 import get_event_capture
            event_capture = get_event_capture()
            if event_capture:
                print(f"🔥 DIRECT EVENT CAPTURE: Attempting project creation event")
                success = await event_capture.capture_project_created(
                    project_id=proj["project_id"],
                    project_name=name,
                    user_id=user["user_id"],
                    username=user.get("username", "unknown"),
                    project_details={
                        "description": body.get("description"),
                        "domain": domain,
                        "namespace_id": namespace_id
                    }
                )
                print(f"🔥 DIRECT EVENT CAPTURE: Project creation result = {success}")
            else:
                print(f"🔥 DIRECT EVENT CAPTURE: EventCapture2 not available")
        except Exception as e:
            print(f"🔥 DIRECT EVENT CAPTURE: Project creation failed: {e}")
            logger.warning(f"EventCapture2 project creation failed: {e}")
            import traceback
            traceback.print_exc()

        return {"project": proj}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, user=Depends(get_user)):
    """Get individual project details"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        from psycopg2.extras import RealDictCursor
        
        conn = db._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get project with namespace details and creator username
                cur.execute(
                    """
                    SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at,
                           p.is_active, p.namespace_id, p.domain, p.created_by,
                           n.path as namespace_path, n.status as namespace_status,
                           u.username as created_by_username
                    FROM public.projects p
                    LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                    LEFT JOIN public.users u ON u.user_id = p.created_by
                    WHERE p.project_id = %s
                """,
                    (project_id,),
                )
                project = cur.fetchone()
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")

                # Check if user has access to this project (admin users have access to all projects)
                if not user.get("is_admin", False):
                    cur.execute(
                        """
                        SELECT role FROM public.project_members
                        WHERE project_id = %s AND user_id = %s
                    """,
                        (project_id, user["user_id"]),
                    )
                    membership = cur.fetchone()
                    if not membership:
                        raise HTTPException(status_code=403, detail="Access denied")

                return {"project": dict(project)}
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects/{project_id}/namespace")
def get_project_namespace(project_id: str, user=Depends(get_user)):
    """Get project with its namespace information"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        from psycopg2.extras import RealDictCursor
        
        conn = db._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get project with namespace details and creator username
                cur.execute(
                    """
                    SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at,
                           p.is_active, p.namespace_id, p.domain, p.created_by,
                           n.path as namespace_path, n.status as namespace_status,
                           u.username as created_by_username
                    FROM public.projects p
                    LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                    LEFT JOIN public.users u ON u.user_id = p.created_by
                    WHERE p.project_id = %s
                """,
                    (project_id,),
                )
                project = cur.fetchone()
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")

                # Check if user has access to this project (admin users have access to all projects)
                if not user.get("is_admin", False):
                    cur.execute(
                        """
                        SELECT role FROM public.project_members
                        WHERE project_id = %s AND user_id = %s
                    """,
                        (project_id, user["user_id"]),
                    )
                    membership = cur.fetchone()
                    if not membership:
                        raise HTTPException(status_code=403, detail="Access denied")

                return dict(project)
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/projects/{project_id}")
def update_project(project_id: str, body: Dict, user=Depends(get_user)):
    """Update project details"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        # Check if user has access to this project (admin users have access to all projects)
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get user role for permission check (admin users can update any project)
        if not user.get("is_admin", False):
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT role FROM public.project_members
                        WHERE project_id = %s AND user_id = %s
                    """,
                        (project_id, user["user_id"]),
                    )
                    membership = cur.fetchone()
                    if not membership:
                        raise HTTPException(status_code=403, detail="Access denied")

                    # Allow owners and editors to update projects
                    role = membership[0]
                    if role not in ("owner", "editor"):
                        raise HTTPException(
                            status_code=403,
                            detail="Only project owners or editors can update projects",
                        )
            finally:
                db._return(conn)

        # Use the database service update method
        result = db.update_project(
            project_id=project_id,
            name=body.get("name", "").strip() if body.get("name") else None,
            description=body.get("description") if body.get("description") else None,
            domain=body.get("domain") if body.get("domain") else None,
            namespace_id=body.get("namespace_id") if body.get("namespace_id") else None,
        )

        return {"project": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user=Depends(get_user)):
    """Hard delete a project and memberships. Does NOT delete external artifacts.

    For now, we perform a hard delete from the DB (projects, memberships). Artifacts like ontologies are not deleted;
    they will simply not show in the user's project tree anymore. We can later implement a migration step to reassign
    artifacts to the user or an archive space.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        # Ensure user is a member/owner; admin users can delete any project
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Delete in order to respect foreign key constraints
                # 1. Delete project members
                cur.execute(
                    "DELETE FROM public.project_members WHERE project_id = %s",
                    (project_id,),
                )

                # 2. Delete knowledge assets (will cascade to chunks, relationships, jobs)
                cur.execute(
                    "DELETE FROM public.knowledge_assets WHERE project_id = %s",
                    (project_id,),
                )

                # 3. Delete files associated with the project
                cur.execute(
                    "DELETE FROM public.files WHERE project_id = %s",
                    (project_id,),
                )

                # 4. Finally delete the project itself
                cur.execute("DELETE FROM public.projects WHERE project_id = %s", (project_id,))

                conn.commit()
                logger.info(f"Deleted project {project_id} and all associated data from PostgreSQL")
        finally:
            db._return(conn)

        # Clean up project thread from Redis and vector store
        try:
            # Direct cleanup without depending on DAS engine
            import redis.asyncio as redis
            from ..services.config import Settings

            settings = Settings()
            redis_client = redis.from_url(settings.redis_url)

            # Get project thread ID from Redis index
            project_thread_id = await redis_client.get(f"project_index:{project_id}")
            if project_thread_id:
                project_thread_id = project_thread_id.decode()

                # Delete from Redis
                await redis_client.delete(f"project_thread:{project_thread_id}")
                await redis_client.delete(f"project_index:{project_id}")

                # Delete from vector store using correct Qdrant API
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "http://localhost:6333/collections/project_threads/points/delete",
                            headers={"Content-Type": "application/json"},
                            json={"points": [project_thread_id]}
                        )
                        if response.status_code == 200:
                            logger.info(f"Deleted project thread {project_thread_id} from vector store")
                        else:
                            logger.warning(f"Vector store deletion response: {response.status_code} {response.text}")
                except Exception as vector_error:
                    logger.warning(f"Could not delete from vector store: {vector_error}")

                logger.info(f"Cleaned up project thread {project_thread_id} for deleted project {project_id}")
            else:
                logger.info(f"No project thread found for project {project_id}")

            await redis_client.close()

        except Exception as cleanup_error:
            logger.warning(f"Could not clean up project thread: {cleanup_error}")
            # Don't fail project deletion if thread cleanup fails

        return {"deleted": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects/{project_id}/archive")
def archive_project(project_id: str, user=Depends(get_user)):
    """Archive a project"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")
        db.archive_project(project_id)
        return {"archived": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects/{project_id}/restore")
def restore_project(project_id: str, user=Depends(get_user)):
    """Restore an archived project"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")
        db.restore_project(project_id)
        return {"restored": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
