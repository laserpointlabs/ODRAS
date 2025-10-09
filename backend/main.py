import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import requests
import uvicorn
from fastapi import (
    Body,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Depends,
    Header,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Request
import secrets
import logging
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Import services using absolute imports
from backend.services.config import Settings
from backend.services.db import DatabaseService
from backend.services.namespace_uri_generator import NamespaceURIGenerator
from backend.services.resource_uri_service import get_resource_uri_service
from backend.services.auth import (
    get_user as auth_get_user,
    get_admin_user,
    create_token,
    invalidate_token,
    cleanup_expired_tokens,
)
import os

logger = logging.getLogger(__name__)
# Import API routers
from backend.api.files import router as files_router
from backend.api.ontology import router as ontology_router
from backend.api.workflows import router as workflows_router
from backend.api.embedding_models import router as embedding_models_router
from backend.api.knowledge import router as knowledge_router
from backend.api.das import router as das_router
from backend.api.das2 import router as das2_router
from backend.api.thread_manager import router as thread_manager_router
from backend.api.project_threads import router as project_threads_router
from backend.api.requirements import router as requirements_router
from backend.api.namespace_simple import (
    router as namespace_router,
    public_router as namespace_public_router,
)
from backend.api.prefix_management import router as prefix_router
from backend.api.domain_management import (
    router as domain_router,
    public_router as domain_public_router,
)
from backend.api.session_intelligence import router as session_intelligence_router
from backend.run_registry import RUNS as SHARED_RUNS
from backend.test_review_endpoint import router as test_router

app = FastAPI(title="ODRAS API", version="0.1.0")

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Create session capture middleware during app creation (before startup)
from backend.middleware.session_capture import SessionCaptureMiddleware

# Global middleware instance to be configured during startup
session_middleware = SessionCaptureMiddleware(app, redis_client=None)
app.add_middleware(SessionCaptureMiddleware, redis_client=None)

# Include API routers
app.include_router(test_router)
app.include_router(ontology_router)
app.include_router(files_router)
app.include_router(workflows_router)
app.include_router(embedding_models_router)
app.include_router(knowledge_router)
app.include_router(requirements_router)  # <-- REQUIREMENTS WORKBENCH API
# ⚠️ DAS1 DEPRECATED - DO NOT ENABLE ⚠️
# DAS1 (original DAS) has been replaced by DAS2 with cleaner architecture
# DAS1 endpoints: /api/das/* (DEPRECATED - DO NOT USE)
# DAS2 endpoints: /api/das2/* (CURRENT - USE THIS)
# app.include_router(das_router)  # <-- DO NOT UNCOMMENT THIS LINE
app.include_router(das2_router)    # <-- ACTIVE DAS IMPLEMENTATION
app.include_router(thread_manager_router)  # <-- THREAD MANAGER FOR DEBUGGING
app.include_router(project_threads_router)  # <-- PROJECT THREAD CREATION (UI ONLY)

# Import and include IRI resolution router
from backend.api.iri_resolution import router as iri_router
app.include_router(iri_router)

# Import and include federated access router
from backend.api.federated_access import router as federated_router
app.include_router(federated_router)

# Import and include events management router
from backend.api.events import router as events_router
app.include_router(events_router)

app.include_router(namespace_router)
app.include_router(namespace_public_router)
app.include_router(prefix_router)
app.include_router(domain_router)
app.include_router(domain_public_router)
app.include_router(session_intelligence_router)

# Import and include users router (after app creation to avoid circular import)
from backend.api.users import router as users_router

app.include_router(users_router)

# Configuration instance
settings = Settings()
# Lazily tolerate DB unavailability in CI/import contexts
try:
    db = DatabaseService(settings)
    logger.info(
        f"Database connected successfully to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
    )
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    logger.error(
        f"Database settings: host={settings.postgres_host}, port={settings.postgres_port}, database={settings.postgres_database}, user={settings.postgres_user}"
    )

    # Provide a fallback that raises a 503 on any DB method usage
    class _DBUnavailable:
        def __getattr__(self, _name):
            from fastapi import (
                HTTPException,
            )  # local import to avoid circulars during import

            def _raise(*_args, **_kwargs):
                raise HTTPException(status_code=503, detail="Database unavailable")

            return _raise

    db = _DBUnavailable()

# Camunda configuration
CAMUNDA_BASE_URL = settings.camunda_base_url
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

# Simple in-memory run registry (MVP). Replace with Redis/DB later.
RUNS: Dict[str, Dict] = SHARED_RUNS

# In-memory storage for personas and prompts (MVP). Replace with Redis/DB later.
PERSONAS: List[Dict] = [
    {
        "id": "extractor",
        "name": "Extractor",
        "description": "You extract ontology-grounded entities from requirements.",
        "system_prompt": "You are an expert requirements analyst. Your role is to extract ontology-grounded entities from requirements text. Return ONLY JSON conforming to the provided schema.",
        "is_active": True,
    },
    {
        "id": "reviewer",
        "name": "Reviewer",
        "description": "You validate and correct extracted JSON to fit the schema strictly.",
        "system_prompt": "You are a quality assurance specialist. Your role is to validate and correct extracted JSON to ensure it strictly conforms to the provided schema. Return ONLY JSON conforming to the schema.",
        "is_active": True,
    },
]

PROMPTS: List[Dict] = [
    {
        "id": "default_analysis",
        "name": "Default Analysis",
        "description": "Default prompt for requirement analysis",
        "prompt_template": "Analyze the following requirement and extract key information:\n\nRequirement: {requirement_text}\nCategory: {category}\nSource: {source_file}\nIteration: {iteration}\n\nPlease provide:\n1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)\n2. Constraints and dependencies\n3. Performance requirements\n4. Quality attributes\n5. Confidence level (0.0-1.0)\n\nFormat your response as JSON.",
        "variables": ["requirement_text", "category", "source_file", "iteration"],
        "is_active": True,
    }
]

PROJECTS: List[Dict] = []

get_user = auth_get_user


@app.get("/app", response_class=HTMLResponse)
def ui_restart():
    try:
        with open("frontend/app.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>App not found</h1>", status_code=404)


@app.post("/api/auth/login")
def login(body: Dict):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    # Use new authentication service
    try:
        from backend.services.auth_service import AuthService

        auth_service = AuthService(db)

        # Authenticate user with password
        user = auth_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Generate token
        token = secrets.token_hex(16)

        # Store token in persistent database
        create_token(
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


@app.get("/api/auth/me")
def me(user=Depends(get_user)):
    return user


@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {"database": "connected", "api": "running"},
    }


@app.get("/api/sync/health")
async def sync_health_check(project_id: Optional[str] = None, user=Depends(get_user)):
    """Check vector/SQL synchronization health - CRITICAL for DAS reliability"""
    try:
        from backend.services.vector_sql_sync_monitor import get_sync_monitor

        monitor = get_sync_monitor()
        health_report = await monitor.check_sync_health(project_id)

        return health_report

    except Exception as e:
        logger.error(f"Sync health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync health check failed: {str(e)}")


@app.post("/api/sync/emergency-recovery")
async def emergency_sync_recovery(
    project_id: str = Body(..., description="Project ID to recover"),
    user=Depends(get_admin_user)  # Admin only for safety
):
    """Emergency recovery for vector/SQL desync - fixes DAS 'no information available' issues"""
    try:
        from backend.services.vector_sql_sync_monitor import emergency_das_recovery

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


@app.get("/api/sync/quick-check/{project_id}")
async def quick_sync_check(project_id: str, user=Depends(get_user)):
    """Quick check if DAS will work for a project - prevents 'no information available' surprises"""
    try:
        from backend.services.vector_sql_sync_monitor import check_das_will_work

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


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate the current token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="No token provided")

    token = authorization.split(" ", 1)[1]
    try:
        invalidate_token(token)
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return {"message": "Logged out successfully"}  # Don't reveal errors to client


@app.post("/api/auth/logout-all")
def logout_all():
    """Logout all users by invalidating all tokens (admin operation for clean process)."""
    try:
        # Clear all tokens from database
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM auth_tokens")
            db.commit()

        return {"message": "All users logged out successfully", "tokens_cleared": True}
    except Exception as e:
        logger.error(f"Failed to logout all users: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout all users")


# NOTE: Startup event is consolidated below at line ~768 in on_startup() function
# This section is kept for reference but not used


# NOTE: Shutdown is handled in application lifecycle
# Database monitor cleanup will happen automatically on process exit


@app.get("/api/projects")
def list_projects(state: Optional[str] = None, user=Depends(get_user)):
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


@app.post("/api/projects")
async def create_project(body: Dict, user=Depends(get_user)):
    name = (body.get("name") or "").strip()
    namespace_id = body.get("namespace_id")
    domain = body.get("domain")
    if not name:
        raise HTTPException(status_code=400, detail="Name required")

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
        )

        # Create project thread automatically (NOT via DAS - via direct service call)
        try:
            from backend.api.project_threads import _create_thread_with_das2
            thread_result = await _create_thread_with_das2(proj["project_id"], user["user_id"], user.get("username", "unknown"), name)
            if thread_result["success"]:
                logger.info(f"Created project thread automatically for project '{name}' - {thread_result['message']}")
            else:
                logger.warning(f"Could not create project thread: {thread_result.get('error', 'Unknown error')}")
        except Exception as thread_error:
            logger.warning(f"Project thread creation failed: {thread_error}")
            # Don't fail project creation if thread creation fails

        # EventCapture2: Capture project creation event directly
        try:
            from backend.services.eventcapture2 import get_event_capture
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


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, user=Depends(get_user)):
    """Get individual project details"""
    try:
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


@app.get("/api/projects/{project_id}/namespace")
def get_project_namespace(project_id: str, user=Depends(get_user)):
    """Get project with its namespace information"""
    try:
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


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, body: Dict, user=Depends(get_user)):
    """Update project details"""
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


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user=Depends(get_user)):
    """Hard delete a project and memberships. Does NOT delete external artifacts.

    For now, we perform a hard delete from the DB (projects, memberships). Artifacts like ontologies are not deleted;
    they will simply not show in the user's project tree anymore. We can later implement a migration step to reassign
    artifacts to the user or an archive space.
    """
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
            from backend.services.config import Settings

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


@app.post("/api/projects/{project_id}/archive")
def archive_project(project_id: str, user=Depends(get_user)):
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


@app.post("/api/projects/{project_id}/restore")
def restore_project(project_id: str, user=Depends(get_user)):
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


# Removed duplicate PUT route for /api/projects/{project_id} to avoid overriding the
# comprehensive update endpoint above. The single update endpoint handles renames
# (name) as well as description, domain, and namespace_id.


@app.on_event("startup")
async def on_startup():
    print("🔥 STARTUP EVENT TRIGGERED")
    logger.info("🔥 STARTUP EVENT TRIGGERED")

    try:
        print("🔥 Step 1: Loading settings...")
        logger.info("🔥 Step 1: Loading settings...")
        Settings()  # loads env
        print("✅ Settings loaded")

        print("🔥 Step 2: Verifying RAG SQL-first tables...")
        logger.info("🔧 Verifying RAG SQL-first tables...")
        from backend.db.init import ensure_rag_schema_from_settings
        try:
            if ensure_rag_schema_from_settings(settings):
                print("✅ RAG SQL-first tables verified/created")
            else:
                print("ℹ️  RAG SQL-first tables already exist (from schema)")
        except Exception as e:
            logger.debug(f"RAG table verification note: {e}")
            print("ℹ️  RAG SQL-first tables already exist (from main schema)")

        print("🔥 Step 3: Starting DAS initialization...")
        logger.info("🚀 Starting DAS initialization...")

        print("🔥 Step 4: Importing services...")
        from backend.api.das import initialize_das_engine
        from backend.services.rag_service import RAGService
        import redis.asyncio as redis
        print("✅ Services imported")

        print("🔥 Step 5: Creating service instances...")
        logger.info("📦 Creating service instances...")
        settings = Settings()
        print("✅ Settings instance created")

        print("🔥 Step 6: Creating RAG service...")
        rag_service = RAGService(settings)
        print("✅ RAG service created")

        print("🔥 Step 7: Connecting to Redis...")
        logger.info("🔗 Connecting to Redis...")
        redis_client = redis.from_url(settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379")
        print("✅ Redis client created")

        print("🔥 Step 8: Initializing DAS...")
        logger.info("🤖 Initializing DAS...")
        await initialize_das_engine(settings, rag_service, db, redis_client)
        print("✅ DAS (Core) initialized")

        print("🔥 Step 8b: Initializing DAS2...")
        logger.info("🤖 Initializing DAS2...")
        from backend.api.das2 import initialize_das2_engine
        await initialize_das2_engine()
        print("✅ DAS2 initialized")

        print("🔥 Step 9: Configuring middleware...")
        logger.info("🔧 Configuring middleware...")
        from backend.middleware.session_capture import set_global_redis_client
        set_global_redis_client(redis_client)
        print("✅ Middleware configured with Redis client")

        print("🔥 Step 10: Initializing semantic capture...")
        logger.info("📊 Initializing semantic capture...")
        from backend.services.semantic_event_capture import initialize_semantic_capture
        await initialize_semantic_capture(redis_client)
        print("✅ Semantic capture initialized")

        print("🔥 Step 11: Setting up event routing...")
        logger.info("🎯 Setting up SQL-first event system...")
        try:
            # Initialize SQL-first event capture WITHOUT adding middleware (already added during app init)
            from backend.services.sql_first_event_integration import initialize_sql_first_event_capture_only

            # Import QdrantService for SqlFirstThreadManager
            from backend.services.qdrant_service import QdrantService
            from backend.services.sql_first_thread_manager import SqlFirstThreadManager
            qdrant_service = QdrantService(settings)

            # Create SqlFirstThreadManager
            sql_first_manager = SqlFirstThreadManager(settings, qdrant_service)

            # Initialize event capture without middleware (middleware already exists)
            initialize_sql_first_event_capture_only(
                sql_first_manager=sql_first_manager,
                redis_client=redis_client
            )

            print(f"✅ SQL-first event capture initialized")

        except Exception as e:
            print(f"❌ Error setting up event system: {e}")
            logger.error(f"Event system error: {e}")
            # Don't fail startup for event system issues
            import traceback
            traceback.print_exc()

        print("🎉 DAS INITIALIZATION COMPLETE!")
        logger.info("✅ DAS initialization complete!")

    except Exception as e:
        print(f"💥 STARTUP FAILED: {e}")
        logger.error(f"❌ Failed to initialize DAS engine: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Don't fail startup if DAS initialization fails

    # Start connection pool monitoring task
    try:
        from backend.services.db_monitor import start_db_monitor
        start_db_monitor(db)
        print("✅ Database connection pool monitor started")
        logger.info("✅ Database connection pool monitor started")
    except Exception as e:
        print(f"⚠️  Failed to start database monitor: {e}")
        logger.warning(f"Failed to start database monitor: {e}")


@app.get("/ontology-editor", response_class=HTMLResponse)
async def ontology_editor():
    """Simple, working ontology editor interface."""
    try:
        with open("frontend/simple-ontology-editor.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Ontology Editor not found</h1><p>Please ensure frontend/simple-ontology-editor.html exists.</p>",
            status_code=404,
        )


@app.get("/session-intelligence-demo", response_class=HTMLResponse)
async def session_intelligence_demo():
    """Session Intelligence demonstration interface."""
    try:
        with open("frontend/session-intelligence-demo.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Session Intelligence Demo not found</h1><p>Please ensure frontend/session-intelligence-demo.html exists.</p>",
            status_code=404,
        )


@app.post("/api/ontology/push-turtle")
async def push_turtle_to_fuseki(turtle_content: str = Body(...)):
    """Push turtle RDF content to Fuseki - bypasses authentication issues"""
    try:
        from backend.services.config import Settings
        from backend.services.persistence import PersistenceLayer

        settings = Settings()
        persistence = PersistenceLayer(settings)

        # Use our existing persistence layer which might handle auth better
        persistence.write_rdf(turtle_content)

        return {"success": True, "message": "Ontology pushed to Fuseki successfully"}

    except Exception:
        # If that fails, try direct approach via Graph Store Protocol
        try:
            from backend.services.config import Settings as _Settings

            s = _Settings()
            base = s.fuseki_url.rstrip("/")
            url = f"{base}/data?default"
            headers = {"Content-Type": "text/turtle"}
            resp = requests.put(
                url, data=turtle_content.encode("utf-8"), headers=headers, timeout=10
            )
            if 200 <= resp.status_code < 300:
                return {
                    "success": True,
                    "message": "Ontology pushed to Fuseki successfully (fallback)",
                }
            else:
                return {
                    "success": False,
                    "error": f"Fuseki returned {resp.status_code}: {resp.text}",
                }
        except Exception as e2:
            return {"success": False, "error": f"Failed to push to Fuseki: {str(e2)}"}


@app.get("/api/ontologies")
async def list_ontologies(project: Optional[str] = None):
    """Discover available ontologies (named graphs with owl:Ontology) from Fuseki.

    Returns a list of { graphIri, label } entries. Optional project filter limits by substring match in graph IRI.
    """
    try:
        # Prefer registry when project is provided
        if project:
            try:
                regs = db.list_ontologies(project_id=project)
                if regs:
                    return {
                        "ontologies": [
                            {
                                "graphIri": r.get("graph_iri"),
                                "label": r.get("label"),
                                "role": r.get("role"),
                                "is_reference": r.get("is_reference", False),
                            }
                            for r in regs
                            if r.get("graph_iri")
                        ]
                    }
            except Exception:
                pass

        s = Settings()
        base = s.fuseki_url.rstrip("/")
        query_url = f"{base}/query"
        # Baseline discovery: graphs with owl:Ontology
        filter_clause = ""
        if project:
            # naive substring filter; safe for MVP
            safe = project.replace('"', '\\"')
            filter_clause = f'FILTER(CONTAINS(STR(?graph), "{safe}"))'
        sparql = (
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT DISTINCT ?graph ?ontology ?label WHERE {\n"
            "  GRAPH ?graph {\n"
            "    ?ontology a owl:Ontology .\n"
            "    OPTIONAL { ?ontology rdfs:label ?label }\n"
            f"    {filter_clause}\n"
            "  }\n"
            "} ORDER BY LCASE(STR(?label))"
        )
        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/sparql-query",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(query_url, content=sparql.encode("utf-8"), headers=headers)
            r.raise_for_status()
            data = r.json()
            rows = data.get("results", {}).get("bindings", [])
            ontologies = []
            for b in rows:
                graph = b.get("graph", {}).get("value")
                label = (b.get("label", {}) or {}).get("value")
                if not label and graph:
                    # Fallback label from IRI tail
                    tail = graph.rsplit("/", 1)[-1]
                    label = tail or graph
                if graph:
                    ontologies.append({"graphIri": graph, "label": label or graph})

            # Fallback: any non-empty named graph if no owl:Ontology found
            if not ontologies:
                sparql2 = "SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } } ORDER BY STR(?graph) LIMIT 200"
                r2 = await client.post(query_url, content=sparql2.encode("utf-8"), headers=headers)
                r2.raise_for_status()
                data2 = r2.json()
                for b in data2.get("results", {}).get("bindings", []):
                    graph = b.get("graph", {}).get("value")
                    if not graph:
                        continue
                    if project and project not in graph:
                        continue
                    tail = graph.rsplit("/", 1)[-1]
                    ontologies.append({"graphIri": graph, "label": tail or graph})

            return {"ontologies": ontologies}
    except httpx.HTTPStatusError as he:
        detail = he.response.text if he.response is not None else str(he)
        raise HTTPException(status_code=500, detail=f"SPARQL error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ontologies: {str(e)}")


@app.post("/api/ontologies")
async def create_ontology(body: Dict, user=Depends(get_user)):
    """Create a new empty ontology as a named graph with owl:Ontology and rdfs:label.

    Body: { project: string, name: string, label?: string, is_reference?: boolean }
    Returns: { graphIri, label }
    """
    project = (body.get("project") or "").strip()
    name = (body.get("name") or "").strip().strip("/")
    label = (body.get("label") or name or "New Ontology").strip()
    is_reference = body.get("is_reference", False)
    if not project or not name:
        raise HTTPException(status_code=400, detail="project and name are required")

    # Only admins can create reference ontologies
    if is_reference and not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Only admins can create reference ontologies")

    # Use centralized URI service for consistent namespace-aware URI generation
    settings = Settings()
    uri_service = get_resource_uri_service(settings, db)
    namespace_generator = NamespaceURIGenerator(settings)  # Always initialize for header generation

    # Validate installation configuration
    config_issues = uri_service.validate_installation_config()
    if config_issues:
        for issue in config_issues:
            logger.warning(f"URI Configuration Issue: {issue}")

    if is_reference:
        # For reference ontologies, use the legacy namespace generator for now
        # TODO: Integrate reference ontology patterns into ResourceURIService
        if project.startswith("core-"):
            graph_iri = namespace_generator.generate_ontology_uri("core", ontology_name=name)
        elif project.startswith("domain-"):
            domain = project.replace("domain-", "")
            graph_iri = namespace_generator.generate_ontology_uri(
                "domain", domain=domain, ontology_name=name
            )
        elif project.startswith("program-"):
            program = project.replace("program-", "")
            graph_iri = namespace_generator.generate_ontology_uri(
                "program", program=program, ontology_name=name
            )
        else:
            # Use standard project-based URI even for reference ontologies
            graph_iri = uri_service.generate_ontology_uri(project, name)
    else:
        # For working ontologies, use the new centralized URI service
        graph_iri = uri_service.generate_ontology_uri(project, name)

        logger.info(f"Generated ontology URI: {graph_iri} for project: {project}, name: {name}")
        logger.info(f"Installation base URI: {settings.installation_base_uri}")

        # Log namespace info for debugging
        namespace_info = uri_service.get_namespace_info(project)
        logger.info(f"Project namespace info: {namespace_info}")

    # Generate proper ontology header
    external_imports = namespace_generator.get_external_namespace_mappings()
    turtle = namespace_generator.generate_ontology_header(
        ontology_uri=graph_iri,
        title=label,
        description=f"Ontology created in ODRAS for {project}",
        version="1.0.0",
        imports=external_imports,
    )
    try:
        # Membership check
        # project here is a plain string id
        # Ensure user is member
        if not db.is_user_member(project_id=project, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        s = Settings()
        base = s.fuseki_url.rstrip("/")
        url = f"{base}/data?graph={graph_iri}"
        headers = {"Content-Type": "text/turtle"}
        auth = (s.fuseki_user, s.fuseki_password) if s.fuseki_user and s.fuseki_password else None
        resp = requests.put(
            url, data=turtle.encode("utf-8"), headers=headers, auth=auth, timeout=20
        )
        if 200 <= resp.status_code < 300:
            # Register in ontologies_registry
            try:
                db.add_ontology(
                    project_id=project,
                    graph_iri=graph_iri,
                    label=label,
                    role="base",
                    is_reference=is_reference,
                )
            except Exception:
                pass

            # EventCapture2: Capture ontology creation event directly
            try:
                from backend.services.eventcapture2 import get_event_capture
                event_capture = get_event_capture()
                if event_capture:
                    await event_capture.capture_ontology_operation(
                        operation_type="created",
                        ontology_name=name,
                        project_id=project,
                        user_id=user["user_id"],
                        username=user.get("username", "unknown"),
                        operation_details={
                            "label": label,
                            "is_reference": is_reference,
                            "graph_iri": graph_iri,
                            "classes_count": 0,
                            "properties_count": 0,
                            "created_via": "gui"
                        }
                    )
                    print(f"🔥 DIRECT: EventCapture2 ontology creation captured for {name}")
            except Exception as e:
                print(f"🔥 DIRECT: EventCapture2 ontology creation failed: {e}")
                logger.warning(f"EventCapture2 ontology creation failed: {e}")

            return {"graphIri": graph_iri, "label": label}
        raise HTTPException(
            status_code=500, detail=f"Fuseki returned {resp.status_code}: {resp.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ontology: {str(e)}")


@app.get("/api/ontologies/reference")
async def list_reference_ontologies(user=Depends(get_user)):
    """List all reference ontologies across all projects."""
    try:
        reference_ontologies = db.list_reference_ontologies()
        return {"reference_ontologies": reference_ontologies}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list reference ontologies: {str(e)}"
        )


@app.get("/api/installation/config")
async def get_installation_config():
    """Get installation configuration for frontend with URI validation."""
    try:
        settings = Settings()
        uri_service = get_resource_uri_service(settings, db)

        # Validate configuration
        config_issues = uri_service.validate_installation_config()

        return {
            "organization": settings.installation_organization,
            "baseUri": settings.installation_base_uri,
            "prefix": settings.installation_prefix,
            "type": settings.installation_type,
            "programOffice": settings.installation_program_office,
            "validation": {"valid": len(config_issues) == 0, "issues": config_issues},
        }
    except Exception as e:
        logger.error(f"Error getting installation config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/db-pool-status")
async def get_db_pool_status():
    """Get database connection pool status for monitoring."""
    try:
        if hasattr(db, 'get_pool_status'):
            return db.get_pool_status()
        else:
            return {"error": "Pool status not available"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/rag-config")
async def get_rag_config(user: Dict = Depends(get_admin_user)):
    """Get current RAG implementation configuration (Admin only)."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT rag_implementation, rag_bpmn_model, rag_model_version
                    FROM installation_config
                    WHERE is_active = TRUE
                    LIMIT 1
                """)
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Installation configuration not found")

                return {
                    "rag_implementation": result[0],
                    "rag_bpmn_model": result[1],
                    "rag_model_version": result[2],
                    "available_implementations": ["hardcoded", "bpmn"]
                }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve RAG configuration: {str(e)}")


@app.get("/api/admin/file-processing-config")
async def get_file_processing_config(user: Dict = Depends(get_admin_user)):
    """Get current file processing configuration (Admin only)."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT file_processing_implementation
                    FROM installation_config
                    WHERE is_active = true
                    LIMIT 1
                """)

                result = cur.fetchone()

                if not result:
                    return {
                        "success": True,
                        "file_processing_implementation": "bpmn"
                    }

                return {
                    "success": True,
                    "file_processing_implementation": result[0] or "bpmn",
                    "available_implementations": ["hardcoded", "bpmn"]
                }
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Failed to retrieve file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file processing configuration: {str(e)}")


@app.put("/api/admin/file-processing-config")
async def update_file_processing_config(
    config: Dict[str, str],
    user: Dict = Depends(get_admin_user)
):
    """Update file processing configuration (Admin only)."""
    try:
        file_processing_implementation = config.get("file_processing_implementation")

        if not file_processing_implementation or file_processing_implementation not in ["hardcoded", "bpmn"]:
            raise HTTPException(
                status_code=400,
                detail="file_processing_implementation must be either 'hardcoded' or 'bpmn'"
            )

        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE installation_config
                    SET file_processing_implementation = %s,
                        updated_at = NOW()
                    WHERE is_active = true
                """, (file_processing_implementation,))

                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="No active installation config found")

            conn.commit()
            logger.info(f"Updated file processing configuration to: {file_processing_implementation}")

            return {
                "success": True,
                "file_processing_implementation": file_processing_implementation,
                "message": f"File processing configuration updated to {file_processing_implementation}"
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update file processing configuration: {str(e)}")


@app.put("/api/admin/rag-config")
async def update_rag_config(
    config: Dict[str, str],
    user: Dict = Depends(get_admin_user)
):
    """Update RAG implementation configuration (Admin only)."""
    try:
        rag_implementation = config.get("rag_implementation")
        rag_bpmn_model = config.get("rag_bpmn_model")
        rag_model_version = config.get("rag_model_version")

        if not rag_implementation or rag_implementation not in ["hardcoded", "bpmn"]:
            raise HTTPException(
                status_code=400,
                detail="rag_implementation must be either 'hardcoded' or 'bpmn'"
            )

        # Validate BPMN-specific fields when BPMN is selected
        if rag_implementation == "bpmn":
            if not rag_bpmn_model:
                raise HTTPException(
                    status_code=400,
                    detail="rag_bpmn_model is required when using BPMN implementation"
                )
            if not rag_model_version:
                raise HTTPException(
                    status_code=400,
                    detail="rag_model_version is required when using BPMN implementation"
                )

        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE installation_config
                    SET rag_implementation = %s, rag_bpmn_model = %s, rag_model_version = %s, updated_at = NOW()
                    WHERE is_active = TRUE
                """, (rag_implementation, rag_bpmn_model, rag_model_version))

                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Installation configuration not found")

                conn.commit()
                logger.info(f"RAG configuration updated to '{rag_implementation}' (model: {rag_bpmn_model}, version: {rag_model_version}) by admin {user.get('username')}")

                return {
                    "success": True,
                    "rag_implementation": rag_implementation,
                    "rag_bpmn_model": rag_bpmn_model,
                    "rag_model_version": rag_model_version,
                    "message": f"RAG configuration updated to {rag_implementation}"
                }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update RAG configuration: {str(e)}")


@app.get("/api/admin/bpmn-models")
async def get_bpmn_models(user: Dict = Depends(get_admin_user)):
    """Get available BPMN models and versions from Camunda (Admin only)."""
    try:
        import httpx

        settings = Settings()
        camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"

        async with httpx.AsyncClient(timeout=30) as client:
            # Get all process definitions
            response = await client.get(f"{camunda_rest}/process-definition")

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch BPMN models from Camunda")

            process_definitions = response.json()

            # Group by process key and collect versions
            models = {}
            for pd in process_definitions:
                key = pd.get('key', '')
                version = pd.get('version', 1)
                name = pd.get('name', key)

                if key not in models:
                    models[key] = {
                        'key': key,
                        'name': name,
                        'versions': [],
                        'description': f"BPMN Process: {name}"
                    }

                models[key]['versions'].append(version)

            # Sort versions for each model
            for model in models.values():
                model['versions'] = sorted(model['versions'], reverse=True)

            return {
                "models": list(models.values()),
                "total_models": len(models)
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Camunda request timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Camunda service unavailable")
    except Exception as e:
        logger.error(f"Failed to fetch BPMN models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch BPMN models: {str(e)}")


@app.get("/api/rag-config")
async def get_rag_config(current_user: dict = Depends(get_user)):
    """Get current RAG configuration (public endpoint for DAS dock)"""
    try:
        # Query installation config using the global db instance
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT rag_implementation, rag_bpmn_model, rag_model_version
                    FROM installation_config
                    WHERE is_active = true
                    LIMIT 1
                """)

                result = cur.fetchone()

                if not result:
                    return {
                        "success": True,
                        "rag_implementation": "hardcoded",
                        "rag_bpmn_model": None,
                        "rag_model_version": None
                    }

                return {
                    "success": True,
                    "rag_implementation": result[0] or "hardcoded",
                    "rag_bpmn_model": result[1],
                    "rag_model_version": result[2]
                }
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Failed to get RAG config: {str(e)}")
        return {
            "success": True,
            "rag_implementation": "hardcoded",
            "rag_bpmn_model": None,
            "rag_model_version": None
        }


@app.get("/api/installation/uri-diagnostics")
async def get_uri_diagnostics(user=Depends(get_user)):
    """Diagnostic endpoint for URI generation issues."""
    try:
        settings = Settings()
        uri_service = get_resource_uri_service(settings, db)

        # Get configuration validation
        config_issues = uri_service.validate_installation_config()

        # Get sample URIs for demonstration
        sample_project_id = "ce1da05a-9a56-4531-aa47-7f030aae2614"  # From logs
        sample_uris = {}

        try:
            sample_uris = {
                "project_uri": uri_service.generate_project_uri(sample_project_id),
                "ontology_uri": uri_service.generate_ontology_uri(
                    sample_project_id, "sample-ontology"
                ),
                "entity_uri": uri_service.generate_ontology_entity_uri(
                    sample_project_id, "sample-ontology", "SampleClass"
                ),
                "file_uri": uri_service.generate_file_uri(sample_project_id, "requirements.pdf"),
                "knowledge_uri": uri_service.generate_knowledge_uri(
                    sample_project_id, "threat-analysis"
                ),
                "admin_uri": uri_service.generate_admin_uri("configs", "fuseki-settings"),
                "shared_uri": uri_service.generate_shared_uri("libraries", "common-vocabularies"),
            }
        except Exception as e:
            logger.warning(f"Failed to generate sample URIs: {e}")

        # Get namespace info for sample project
        namespace_info = uri_service.get_namespace_info(sample_project_id)

        return {
            "installation_config": {
                "base_uri": settings.installation_base_uri,
                "organization": settings.installation_organization,
                "validation": {"valid": len(config_issues) == 0, "issues": config_issues},
            },
            "sample_project_info": namespace_info,
            "sample_uris": sample_uris,
            "expected_pattern": "{base_uri}/{namespace_path}/{project_uuid}/{resource_type}/{resource_name}",
        }
    except Exception as e:
        logger.error(f"Error in URI diagnostics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/ontologies/reference")
async def toggle_reference_ontology(body: Dict, user=Depends(get_admin_user)):
    """Toggle reference status of an ontology. Admin only."""
    graph_iri = (body.get("graph") or "").strip()
    is_reference = body.get("is_reference", False)

    if not graph_iri:
        raise HTTPException(status_code=400, detail="graph parameter is required")

    try:
        # Update the reference status in the database
        result = db.update_ontology_reference_status(graph_iri=graph_iri, is_reference=is_reference)
        if result:
            return {
                "success": True,
                "graph_iri": graph_iri,
                "is_reference": is_reference,
            }
        else:
            raise HTTPException(status_code=404, detail="Ontology not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update reference status: {str(e)}")


@app.post("/api/ontologies/import-url")
async def import_ontology_from_url(body: Dict, user=Depends(get_user)):
    """Import an ontology from a remote URL. Any authenticated user can import, but only admins can set as reference."""
    import httpx
    from rdflib import Graph, RDF
    from rdflib.namespace import OWL, RDFS

    url = body.get("url", "").strip()
    project_id = body.get("project_id", "").strip()
    name = body.get("name", "").strip()
    label = body.get("label", "").strip()

    # Only admins can set ontologies as reference
    is_admin = user.get("is_admin", False)
    if is_admin:
        is_reference = body.get("is_reference", True)  # Default to reference for URL imports
    else:
        is_reference = False  # Non-admins cannot set as reference

    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id parameter is required")

    if not name:
        raise HTTPException(status_code=400, detail="name parameter is required")

    try:
        # Fetch the ontology from the URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text

        # Parse the RDF content
        graph = Graph()
        try:
            # Try to detect format from content-type or content
            content_type = response.headers.get("content-type", "").lower()
            if "xml" in content_type or "rdf" in content_type:
                format = "xml"
            elif "turtle" in content_type or "ttl" in content_type:
                format = "turtle"
            elif "n3" in content_type:
                format = "n3"
            else:
                # Try to auto-detect format
                if content.strip().startswith("<?xml") or content.strip().startswith("<rdf"):
                    format = "xml"
                elif content.strip().startswith("@prefix") or content.strip().startswith("PREFIX"):
                    format = "turtle"
                else:
                    format = "xml"  # Default fallback

            graph.parse(data=content, format=format)
        except Exception as parse_error:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse RDF content: {str(parse_error)}",
            )

        # Extract ontology IRI and label
        ontology_iri = None
        ontology_label = label or name

        # Look for owl:Ontology declarations
        for s, p, o in graph.triples((None, RDF.type, OWL.Ontology)):
            ontology_iri = str(s)
            # Try to get the label
            for label_triple in graph.triples((s, RDFS.label, None)):
                ontology_label = str(label_triple[2])
                break
            break

        if not ontology_iri:
            # If no owl:Ontology found, use the URL as the IRI
            ontology_iri = url

        # Create the graph IRI for our system using installation configuration
        settings = Settings()
        base_uri = settings.installation_base_uri.rstrip("/")
        graph_iri = f"{base_uri}/{project_id}/{name}"

        # Store the ontology in Fuseki using the REST API
        fuseki_url = "http://localhost:3030/odras"
        fuseki_data_url = f"{fuseki_url}/data"

        # Convert graph to turtle format for storage
        turtle_content = graph.serialize(format="turtle")

        # Upload the ontology to Fuseki as a named graph
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{fuseki_data_url}?graph={graph_iri}",
                content=turtle_content,
                headers={"Content-Type": "text/turtle"},
            )
            response.raise_for_status()

        # Register the ontology in our database
        db.add_ontology(
            project_id=project_id,
            graph_iri=graph_iri,
            label=ontology_label,
            role="imported",
            is_reference=is_reference,
        )

        return {
            "success": True,
            "graph_iri": graph_iri,
            "label": ontology_label,
            "original_iri": ontology_iri,
            "source_url": url,
            "is_reference": is_reference,
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch ontology from URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import ontology: {str(e)}")


@app.delete("/api/ontologies")
async def delete_ontology(graph: str, project: Optional[str] = None, user=Depends(get_user)):
    """Delete a named graph (drop ontology)."""
    if not graph:
        raise HTTPException(status_code=400, detail="graph parameter required")
    try:
        # Optional membership check if project provided
        if project and not db.is_user_member(project_id=project, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        s = Settings()
        update_url = f"{s.fuseki_url.rstrip('/')}/update"

        # Delete the main ontology graph
        query = f"DROP GRAPH <{graph}>"
        headers = {"Content-Type": "application/sparql-update"}
        r = requests.post(update_url, data=query.encode("utf-8"), headers=headers, timeout=20)

        # Also delete the associated layout graph if it exists
        layout_graph = f"{graph}#layout"
        layout_query = f"DROP GRAPH <{layout_graph}>"
        try:
            requests.post(
                update_url,
                data=layout_query.encode("utf-8"),
                headers=headers,
                timeout=20,
            )
        except Exception:
            pass  # Layout graph might not exist, that's okay

        if 200 <= r.status_code < 300:
            try:
                db.delete_ontology(graph_iri=graph)
            except Exception:
                pass
            return {"deleted": graph}
        raise HTTPException(status_code=500, detail=f"Fuseki returned {r.status_code}: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ontology: {str(e)}")


@app.put("/api/ontologies/label")
async def relabel_ontology(body: Dict):
    """Update rdfs:label of the ontology node inside the named graph (IRI unchanged)."""
    graph = (body.get("graph") or "").strip()
    label = (body.get("label") or "").strip()
    if not graph or not label:
        raise HTTPException(status_code=400, detail="graph and label are required")
    try:
        s = Settings()
        update_url = f"{s.fuseki_url.rstrip('/')}/update"
        safe_label = label.replace("\\", "\\\\").replace('"', '\\"')
        sparql = (
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            f"DELETE {{ GRAPH <{graph}> {{ ?o rdfs:label ?old }} }}\n"
            f'INSERT {{ GRAPH <{graph}> {{ ?o rdfs:label "{safe_label}" }} }}\n'
            f"WHERE  {{ GRAPH <{graph}> {{ ?o a owl:Ontology . OPTIONAL {{ ?o rdfs:label ?old }} }} }}\n"
        )
        headers = {"Content-Type": "application/sparql-update"}
        auth = (s.fuseki_user, s.fuseki_password) if s.fuseki_user and s.fuseki_password else None
        r = requests.post(
            update_url,
            data=sparql.encode("utf-8"),
            headers=headers,
            timeout=20,
            auth=auth,
        )
        if 200 <= r.status_code < 300:
            return {"graphIri": graph, "label": label}
        raise HTTPException(status_code=500, detail=f"Fuseki returned {r.status_code}: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to relabel ontology: {str(e)}")


@app.post("/api/ontology/save")
async def save_ontology(graph: str, request: Request):
    """Save Turtle content to a specific named graph in Fuseki (Graph Store Protocol)."""
    if not graph:
        raise HTTPException(status_code=400, detail="graph parameter required")
    try:
        ttl_bytes = await request.body()
        if not ttl_bytes:
            raise HTTPException(status_code=400, detail="Empty body; expected Turtle content")
        s = Settings()
        base = s.fuseki_url.rstrip("/")
        # First, DROP the target graph to avoid lingering triples
        try:
            upd_url = f"{base}/update"
            upd_headers = {"Content-Type": "application/sparql-update"}
            drop_q = f"DROP GRAPH <{graph}>"
            requests.post(upd_url, data=drop_q.encode("utf-8"), headers=upd_headers, timeout=15)
        except Exception:
            pass
        # Then write via Graph Store PUT
        url = f"{base}/data"
        headers = {"Content-Type": "text/turtle"}
        auth = (s.fuseki_user, s.fuseki_password) if s.fuseki_user and s.fuseki_password else None
        r = requests.put(
            url,
            params={"graph": graph},
            data=ttl_bytes,
            headers=headers,
            timeout=30,
            auth=auth,
        )
        if 200 <= r.status_code < 300:
            return {"success": True, "graphIri": graph, "message": "Saved to Fuseki"}
        raise HTTPException(status_code=500, detail=f"Fuseki returned {r.status_code}: {r.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save ontology: {str(e)}")


@app.get("/api/ontology/summary")
async def ontology_summary():
    """Return simple class counts summary from Fuseki via SPARQL."""
    try:
        s = Settings()
        base = s.fuseki_url.rstrip("/")
        query_url = f"{base}/query"
        sparql = "SELECT ?type (COUNT(?s) AS ?count) WHERE { ?s a ?type } GROUP BY ?type ORDER BY DESC(?count) LIMIT 100"
        headers = {"Accept": "application/sparql-results+json"}
        params = {"query": sparql}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(query_url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Normalize to { rows: [{ type, count }] }
            vars_ = data.get("head", {}).get("vars", [])
            rows = []
            for b in data.get("results", {}).get("bindings", []):
                type_val = b.get("type", {}).get("value") if "type" in b else None
                count_val = b.get("count", {}).get("value") if "count" in b else None
                rows.append(
                    {
                        "type": type_val,
                        "count": (
                            int(count_val) if count_val and count_val.isdigit() else count_val
                        ),
                    }
                )
            return {"rows": rows, "vars": vars_}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/ontology/sparql")
async def ontology_sparql(body: Dict):
    """Run a SPARQL SELECT query against Fuseki and return JSON results."""
    query = body.get("query") if isinstance(body, dict) else None
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    try:
        s = Settings()
        base = s.fuseki_url.rstrip("/")
        query_url = f"{base}/query"
        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/sparql-query",
        }
        # Prefer POST for longer queries
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(query_url, content=query.encode("utf-8"), headers=headers)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as he:
        detail = he.response.text if he.response is not None else str(he)
        raise HTTPException(status_code=500, detail=f"SPARQL error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL error: {str(e)}")


@app.get("/user-review", response_class=HTMLResponse)
async def user_review_interface(
    taskId: Optional[str] = None, process_instance_id: Optional[str] = None
):
    """Requirements review interface or main interface."""

    # If taskId or process_instance_id is provided and not empty, show the review interface
    if (taskId and taskId.strip()) or (process_instance_id and process_instance_id.strip()):
        from backend.review_interface import generate_review_interface_html

        # Ensure we have non-None values
        task_id_safe = taskId or ""
        process_id_safe = process_instance_id or ""
        return HTMLResponse(content=generate_review_interface_html(task_id_safe, process_id_safe))

    # Otherwise show the main interface
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ODRAS - Ontology-Driven Requirements Analysis System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
            button:hover { background-color: #0056b3; }
            .status { margin-top: 20px; padding: 10px; border-radius: 4px; }
            .status.success { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .status.error { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .status.info { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
            .requirements-grid { display: grid; grid-template-columns: 1fr; gap: 15px; margin-top: 20px; }
            .requirement-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #f9f9f9; }
            .requirement-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
            .requirement-id { font-weight: bold; color: #007bff; }
            .requirement-confidence { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .confidence-high { background: #d4edda; color: #155724; }
            .confidence-medium { background: #fff3cd; color: #856404; }
            .confidence-low { background: #f8d7da; color: #721c24; }
            .requirement-text { margin: 10px 0; line-height: 1.5; }
            .requirement-meta { font-size: 12px; color: #666; }
            .edit-form { display: none; margin-top: 10px; }
            .edit-form.show { display: block; }
            .decision-buttons { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
            .decision-buttons h3 { margin-top: 0; }
            .btn-approve { background-color: #28a745; }
            .btn-edit { background-color: #ffc107; color: #212529; }
            .btn-rerun { background-color: #dc3545; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ODRAS - Ontology-Driven Requirements Analysis System</h1>

            <form id="uploadForm">
                <div class="form-group">
                    <label for="file">Select Document:</label>
                    <input type="file" id="file" name="file" accept=".txt,.md,.pdf" required>
                </div>

                <div class="form-group">
                    <label for="iterations">Monte Carlo Iterations:</label>
                    <input type="number" id="iterations" name="iterations" value="10" min="1" max="100">
                </div>

                <div class="form-group">
                    <label for="llm_provider">LLM Provider:</label>
                    <select id="llm_provider" name="llm_provider">
                        <option value="openai">OpenAI</option>
                        <option value="ollama">Ollama (Local)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="llm_model">LLM Model:</label>
                    <input type="text" id="llm_model" name="llm_model" value="gpt-4o-mini">
                </div>

                <button type="submit">Start Analysis</button>
            </form>

            <div id="status"></div>

            <div id="results" style="display: none;">
                <h2>Analysis Results</h2>
                <div id="resultsContent"></div>
            </div>

            <div id="userReview" class="hidden">
                <h2>Requirements Review</h2>
                <p>Please review the extracted requirements before proceeding to LLM analysis.</p>

                <div id="requirementsGrid" class="requirements-grid"></div>

                <div class="decision-buttons">
                    <h3>Make Your Decision:</h3>
                    <button class="btn-approve" onclick="completeUserTask('approve')">✅ Approve & Continue</button>
                    <button class="btn-edit" onclick="showEditInterface()">✏️ Edit Requirements</button>
                    <button class="btn-rerun" onclick="showRerunInterface()">🔄 Rerun Extraction</button>
                </div>

                <div id="editInterface" class="hidden">
                    <h3>Edit Requirements</h3>
                    <div id="editForms"></div>
                    <button onclick="saveEdits()">Save Edits</button>
                    <button onclick="cancelEdit()">Cancel</button>
                </div>

                <div id="rerunInterface" class="hidden">
                    <h3>Rerun Extraction with New Parameters</h3>
                    <div class="form-group">
                        <label for="confidenceThreshold">Confidence Threshold:</label>
                        <input type="number" id="confidenceThreshold" min="0" max="1" step="0.1" value="0.6">
                    </div>
                    <div class="form-group">
                        <label for="minTextLength">Minimum Text Length:</label>
                        <input type="number" id="minTextLength" min="5" value="15">
                    </div>
                    <div class="form-group">
                        <label for="customPatterns">Custom Patterns (one per line):</label>
                        <textarea id="customPatterns" rows="4" placeholder="Enter custom regex patterns..."></textarea>
                    </div>
                    <button onclick="rerunExtraction()">Rerun Extraction</button>
                    <button onclick="cancelRerun()">Cancel</button>
                </div>
            </div>
        </div>

        <script>
            let currentProcessId = null;
            let currentRequirements = [];

            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData();
                const fileInput = document.getElementById('file');
                const iterationsInput = document.getElementById('iterations');
                const llmProviderInput = document.getElementById('llm_provider');
                const llmModelInput = document.getElementById('llm_model');

                formData.append('file', fileInput.files[0]);
                formData.append('iterations', iterationsInput.value);
                formData.append('llm_provider', llmProviderInput.value);
                formData.append('llm_model', llmModelInput.value);

                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = '<div class="status info">Starting analysis...</div>';

                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const result = await response.json();
                        currentProcessId = result.process_id;
                        statusDiv.innerHTML = `<div class="status success">Analysis started! Run ID: ${result.run_id}</div>`;

                        // Show results section
                        document.getElementById('results').style.display = 'block';
                        document.getElementById('resultsContent').innerHTML = `
                            <p><strong>Run ID:</strong> ${result.run_id}</p>
                            <p><strong>Status:</strong> ${result.status}</p>
                            <p><strong>Process ID:</strong> ${result.process_id}</p>
                            <p><a href="http://localhost:8080/cockpit/default/#/process-instance/${result.process_id}" target="_blank">View in Camunda Cockpit</a></p>
                        `;

                        // Start monitoring for user task
                        setTimeout(() => checkForUserTask(result.process_id), 2000);
                    } else {
                        const error = await response.json();
                        statusDiv.innerHTML = `<div class="status error">Error: ${error.detail}</div>`;
                    }
                } catch (error) {
                    statusDiv.innerHTML = `<div class="status error">Error: ${error.message}</div>`;
                }
            });

            async function checkForUserTask(processId) {
                try {
                    const response = await fetch(`/api/user-tasks/${processId}/status`);
                    if (response.ok) {
                        const status = await response.json();
                        if (status.current_state === 'waiting_for_user_review') {
                            // Show user review interface
                            await loadRequirementsForReview(processId);
                            document.getElementById('userReview').classList.remove('hidden');
                        } else if (status.current_state === 'llm_processing') {
                            document.getElementById('status').innerHTML = '<div class="status info">LLM processing in progress...</div>';
                        } else if (status.current_state === 'storing_results') {
                            document.getElementById('status').innerHTML = '<div class="status info">Storing results...</div>';
                        }
                    }
                } catch (error) {
                    console.error('Error checking user task status:', error);
                }

                // Continue monitoring if not complete
                if (currentProcessId) {
                    setTimeout(() => checkForUserTask(processId), 2000);
                }
            }

            async function loadRequirementsForReview(processId) {
                try {
                    const response = await fetch(`/api/user-tasks/${processId}/requirements`);
                    if (response.ok) {
                        const data = await response.json();
                        currentRequirements = data.requirements;
                        displayRequirements(data.requirements);
                    }
                } catch (error) {
                    console.error('Error loading requirements:', error);
                }
            }

            function displayRequirements(requirements) {
                const grid = document.getElementById('requirementsGrid');
                grid.innerHTML = '';

                requirements.forEach(req => {
                    const card = document.createElement('div');
                    card.className = 'requirement-card';

                    const confidenceClass = req.extraction_confidence >= 0.8 ? 'confidence-high' :
                                          req.extraction_confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';

                    card.innerHTML = `
                        <div class="requirement-header">
                            <span class="requirement-id">${req.id}</span>
                            <span class="requirement-confidence ${confidenceClass}">${(req.extraction_confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div class="requirement-text">${req.text}</div>
                        <div class="requirement-meta">
                            <strong>Category:</strong> ${req.category || 'General'} |
                            <strong>Pattern:</strong> ${req.pattern || 'Unknown'} |
                            <strong>Source:</strong> ${req.source_file || 'Unknown'}
                        </div>
                        <div class="edit-form" id="edit-${req.id}">
                            <textarea rows="3" placeholder="Edit requirement text...">${req.text}</textarea>
                            <input type="text" placeholder="Category" value="${req.category || ''}">
                            <input type="number" min="0" max="1" step="0.1" placeholder="Confidence" value="${req.extraction_confidence || 0.8}">
                        </div>
                    `;

                    grid.appendChild(card);
                });
            }

            function showEditInterface() {
                document.getElementById('editInterface').classList.remove('hidden');
                document.getElementById('rerunInterface').classList.add('hidden');
            }

            function showRerunInterface() {
                document.getElementById('rerunInterface').classList.remove('hidden');
                document.getElementById('editInterface').classList.add('hidden');
            }

            function cancelEdit() {
                document.getElementById('editInterface').classList.add('hidden');
            }

            function cancelRerun() {
                document.getElementById('rerunInterface').classList.add('hidden');
            }

            async function saveEdits() {
                const edits = [];
                currentRequirements.forEach(req => {
                    const editForm = document.getElementById(`edit-${req.id}`);
                    const textarea = editForm.querySelector('textarea');
                    const categoryInput = editForm.querySelector('input[type="text"]');
                    const confidenceInput = editForm.querySelector('input[type="number"]');

                    if (textarea.value !== req.text ||
                        categoryInput.value !== (req.category || '') ||
                        confidenceInput.value !== (req.extraction_confidence || 0.8)) {
                        edits.push({
                            edit_type: 'modify',
                            requirement_id: req.id,
                            field: 'text',
                            new_value: textarea.value
                        });
                        if (categoryInput.value !== (req.category || '')) {
                            edits.push({
                                edit_type: 'modify',
                                requirement_id: req.id,
                                field: 'category',
                                new_value: categoryInput.value
                            });
                        }
                        if (confidenceInput.value !== (req.extraction_confidence || 0.8)) {
                            edits.push({
                                edit_type: 'modify',
                                requirement_id: req.id,
                                field: 'extraction_confidence',
                                new_value: parseFloat(confidenceInput.value)
                            });
                        }
                    }
                });

                if (edits.length > 0) {
                    await completeUserTask('edit', { user_edits: edits });
                } else {
                    alert('No changes detected');
                    cancelEdit();
                }
            }

            async function rerunExtraction() {
                const parameters = {
                    confidence_threshold: parseFloat(document.getElementById('confidenceThreshold').value),
                    min_text_length: parseInt(document.getElementById('minTextLength').value),
                    custom_patterns: document.getElementById('customPatterns').value.split('\\n').filter(p => p.trim())
                };

                await completeUserTask('rerun', { extraction_parameters: parameters });
            }

            async function completeUserTask(decision, additionalData = {}) {
                try {
                    const userDecision = {
                        decision: decision,
                        ...additionalData
                    };

                    const response = await fetch(`/api/user-tasks/${currentProcessId}/complete`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(userDecision)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        document.getElementById('status').innerHTML = `<div class="status success">User task completed: ${decision}</div>`;
                        document.getElementById('userReview').classList.add('hidden');

                        // Continue monitoring
                        setTimeout(() => checkForUserTask(currentProcessId), 2000);
                    } else {
                        const error = await response.json();
                        alert(`Error completing task: ${error.detail}`);
                    }
                } catch (error) {
                    alert(`Error: ${error.message}`);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    iterations: int = Form(10),
    llm_provider: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    user=Depends(get_user),
):
    """Upload document and start Camunda BPMN process."""
    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        if not db.is_user_member(project_id=project_id, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        content = await file.read()
        document_text = content.decode("utf-8", errors="ignore")

        # Ensure filename is never None
        document_filename = file.filename or "unknown_document.txt"

        # Start Camunda BPMN process
        process_id = await start_camunda_process(
            document_content=document_text,
            document_filename=document_filename,
            llm_provider=llm_provider or "openai",
            llm_model=llm_model or "gpt-4o-mini",
            iterations=iterations,
            project_id=project_id,
            user_id=user["user_id"],
        )

        if not process_id:
            raise HTTPException(status_code=500, detail="Failed to start Camunda process")

        # Store run info
        run_id = str(process_id)
        RUNS[run_id] = {
            "status": "started",
            "process_id": process_id,
            "filename": document_filename,
            "iterations": iterations,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "camunda_url": f"{CAMUNDA_BASE_URL}/cockpit/default/#/process-instance/{process_id}",
            "project_id": project_id,
            "user_id": user["user_id"],
        }

        return {"run_id": run_id, "status": "started", "process_id": process_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def start_camunda_process(
    document_content: str,
    document_filename: str,
    llm_provider: str,
    llm_model: str,
    iterations: int,
    project_id: str,
    user_id: str,
) -> Optional[str]:
    """Start a new Camunda BPMN process instance."""

    # First, ensure the BPMN is deployed
    deployment_id = await deploy_bpmn_if_needed()
    if not deployment_id:
        return None

    # Start process instance
    start_url = f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis/start"

    variables = {
        "document_content": {"value": document_content, "type": "String"},
        "document_filename": {"value": document_filename, "type": "String"},
        "llm_provider": {"value": llm_provider, "type": "String"},
        "llm_model": {"value": llm_model, "type": "String"},
        "iterations": {"value": iterations, "type": "Integer"},
        "projectId": {"value": project_id, "type": "String"},
        "userId": {"value": user_id, "type": "String"},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                start_url,
                json={
                    "variables": variables,
                    "businessKey": f"{project_id}:{document_filename}",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("id")
    except Exception as e:
        print(f"Error starting Camunda process: {e}")
        return None


async def deploy_bpmn_if_needed() -> Optional[str]:
    """Deploy BPMN if not already deployed."""
    try:
        # Check if already deployed
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis"
            )
            if response.status_code == 200:
                data = response.json()
                return data[0]["id"] if data else None
    except Exception:
        pass

    # Deploy BPMN
    try:
        bpmn_file_path = "../bpmn/odras_requirements_analysis.bpmn"
        with open(bpmn_file_path, "rb") as f:
            files = {"file": ("odras_requirements_analysis.bpmn", f, "application/xml")}
            data = {"deployment-name": "odras-requirements-analysis"}

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{CAMUNDA_REST_API}/deployment/create", files=files, data=data
                )
                response.raise_for_status()
                data = response.json()
                return data.get("id")
    except Exception as e:
        print(f"Error deploying BPMN: {e}")
        return None


@app.get("/api/runs/{run_id}")
async def get_run_status(run_id: str):
    """Get status of a specific run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id].copy()

    try:
        # Get Camunda process instance status
        process_id = run_info["process_id"]
        status_url = f"{CAMUNDA_REST_API}/process-instance/{process_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(status_url)
            if response.status_code == 200:
                status_info = response.json()

                # Check if completed
                if status_info.get("state") == "completed":
                    run_info["status"] = "completed"

    except Exception as e:
        run_info["camunda_error"] = str(e)

    return run_info


@app.get("/api/camunda/status")
async def get_camunda_status():
    """Get Camunda engine status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Check if REST API is accessible by trying to get engine info
            response = await client.get(f"{CAMUNDA_REST_API}/engine")
            if response.status_code == 200:
                return {
                    "status": "running",
                    "url": CAMUNDA_BASE_URL,
                    "api_url": CAMUNDA_REST_API,
                }
            else:
                # Fallback: Try to check if deployments endpoint works
                response = await client.get(f"{CAMUNDA_REST_API}/deployment")
                if response.status_code == 200:
                    return {
                        "status": "running",
                        "url": CAMUNDA_BASE_URL,
                        "api_url": CAMUNDA_REST_API,
                    }
                else:
                    return {
                        "status": "error",
                        "url": CAMUNDA_BASE_URL,
                        "message": "REST API not responding",
                    }
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "url": CAMUNDA_BASE_URL}


@app.get("/api/ollama/status")
async def get_ollama_status():
    """Get Ollama server status."""
    try:
        settings = Settings()
        base = settings.ollama_url.rstrip("/")
        async with httpx.AsyncClient(timeout=10) as client:
            # Check if Ollama is running by accessing its API
            response = await client.get(f"{base}/api/tags")
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("models", []))
                return {"status": "running", "url": base, "model_count": model_count}
            else:
                return {"status": "error", "url": base, "message": "API not responding"}
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "url": Settings().ollama_url}


@app.get("/api/openai/status")
async def get_openai_status():
    """Get OpenAI API status."""
    try:
        api_key = Settings().openai_api_key
        if not api_key:
            return {"status": "not_configured", "message": "OPENAI_API_KEY not set"}

        headers = {"Authorization": f"Bearer {api_key}"}
        url = "https://api.openai.com/v1/models"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                return {
                    "status": "running",
                    "url": "https://api.openai.com",
                    "model_count": model_count,
                }
            elif response.status_code == 401:
                return {"status": "unauthorized", "message": "Invalid API key"}
            else:
                return {
                    "status": "error",
                    "message": f"API returned status {response.status_code}",
                }
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@app.get("/api/camunda/deployments")
async def get_camunda_deployments():
    """Get list of deployed BPMN processes."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CAMUNDA_REST_API}/deployment")
            if response.status_code == 200:
                return {"deployments": response.json()}
            else:
                return {"deployments": [], "error": "Failed to fetch deployments"}
    except Exception as e:
        return {"deployments": [], "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index():
    # Redirect to the main app since the original interface is deprecated
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/app", status_code=302)
    
    # Original deprecated HTML content (kept for reference)
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>ODRAS MVP - Camunda BPMN</title>
      <style>
        body { font-family: system-ui, Arial, sans-serif; margin: 2rem; }
        .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; max-width: 640px; margin-bottom: 1rem; }
        label { display: block; margin: 0.5rem 0 0.25rem; }
        input[type=file], input[type=number], select, input[name="llm_model"], textarea { width: 100%; padding: 0.5rem; box-sizing: border-box; }
        button { margin-top: 1rem; padding: 0.5rem 1rem; margin-right: 0.5rem; }
        pre { background: #f9fafb; padding: 1rem; border-radius: 6px; overflow-x: auto; }
        .status { padding: 0.5rem; border-radius: 4px; margin: 0.5rem 0; }
        .status.running { background: #dbeafe; color: #1e40af; }
        .status.completed { background: #dcfce7; color: #166534; }
        .status.error { background: #fee2e2; color: #dc2626; }

        /* Tab Styles */
        .tabs { display: flex; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem; }
        .tab-button {
          background: none; border: none; padding: 0.75rem 1.5rem; cursor: pointer;
          border-bottom: 2px solid transparent; margin-right: 0.5rem;
        }
        .tab-button.active {
          border-bottom-color: #3b82f6; color: #3b82f6; font-weight: 600;
        }
        .tab-button:hover { background: #f3f4f6; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .persona-item, .prompt-item {
          border: 1px solid #e5e7eb; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;
          background: #f9fafb;
        }
        .persona-item h4, .prompt-item h4 { margin-top: 0; }
        .persona-controls, .prompt-controls { margin-bottom: 1rem; }
        .test-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }
        .test-input { margin-bottom: 0.5rem; }
        .test-result { background: #f1f5f9; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; }

        /* Compact status badges */
        .status-badge {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.875rem;
          background: #f3f4f6;
          border: 1px solid #e5e7eb;
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
        }
        .status-indicator {
          font-weight: 600;
        }
        .status-badge.online {
          background: #dcfce7;
          border-color: #86efac;
          color: #166534;
        }
        .status-badge.online .status-indicator { color: #16a34a; }
        .status-badge.offline {
          background: #fee2e2;
          border-color: #fca5a5;
          color: #991b1b;
        }
        .status-badge.offline .status-indicator { color: #dc2626; }
        .status-badge.warning {
          background: #fef3c7;
          border-color: #fde047;
          color: #854d0e;
        }
        .status-badge.warning .status-indicator { color: #ca8a04; }
      </style>
    </head>
    <body>
      <h1>ODRAS MVP - Camunda BPMN</h1>

      <div class="card" style="padding: 0.75rem;">
        <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
          <h4 style="margin: 0;">Services:</h4>
          <span id="camunda-status" class="status-badge">Camunda: <span class="status-indicator">...</span></span>
          <span id="ollama-status" class="status-badge">Ollama: <span class="status-indicator">...</span></span>
          <span id="openai-status" class="status-badge">OpenAI: <span class="status-indicator">...</span></span>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tabs">
        <button class="tab-button active" onclick='showTab("upload")'>Upload & Process</button>
        <button class="tab-button" onclick='showTab("personas")'>Personas</button>
        <button class="tab-button" onclick='showTab("prompts")'>Prompts</button>
        <button class="tab-button" onclick='showTab("runs")'>Active Runs</button>
        <button class="tab-button" onclick='showTab("tasks")' id="tasks-tab-button">
          User Tasks <span id="task-count-badge" style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 10px; margin-left: 5px; display: none;">0</span>
        </button>
        <button class="tab-button" onclick='showTab("files")'>Stored Files</button>
      </div>

      <!-- Upload Tab -->
      <div id="upload-tab" class="tab-content active">
        <div class="card">
          <h3>Document Analysis</h3>
          <form id="upload-form">
            <label>Document</label>
            <input type="file" name="file" required />
            <label>Monte Carlo Iterations</label>
            <input type="number" name="iterations" value="10" min="1" />
            <label>LLM Provider</label>
            <select name="llm_provider">
              <option value="">(default)</option>
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama (local)</option>
            </select>
            <label>LLM Model</label>
            <select name="llm_model" id="llm_model">
              <option value="">Select a model...</option>
            </select>
            <button type="submit">Start BPMN Analysis</button>
          </form>
          <div id="result"></div>
        </div>
      </div>

      <!-- Personas Tab -->
      <div id="personas-tab" class="tab-content">
        <div class="card">
          <h3>LLM Personas</h3>
          <div class="persona-controls">
            <button onclick="addPersona()">Add New Persona</button>
            <button onclick="savePersonas()">Save All Personas</button>
            <button onclick="loadPersonas()">Load Personas</button>
          </div>
          <div id="personas-list">
            <!-- Personas will be loaded here -->
          </div>
        </div>
      </div>

      <!-- Prompts Tab -->
      <div id="prompts-tab" class="tab-content">
        <div class="card">
          <h3>Prompt Management</h3>
          <div class="prompt-controls">
            <button onclick="addPrompt()">Add New Prompt</button>
            <button onclick="savePrompts()">Save All Prompts</button>
            <button onclick="loadPrompts()">Load Prompts</button>
          </div>
          <div id="prompts-list">
            <!-- Prompts will be loaded here -->
          </div>
        </div>
      </div>

      <!-- Runs Tab -->
      <div id="runs-tab" class="tab-content">
        <div class="card">
          <h3>Active Runs</h3>
          <div id="runs-list">Loading...</div>
          <button onclick="refreshRuns()">Refresh Runs</button>
        </div>
      </div>

      <!-- Stored Files Tab -->
      <div id="files-tab" class="tab-content">
        <div class="card">
          <h3>Stored Files (MinIO)</h3>
          <p style="color:#666; margin-top:0.25rem;">Uploads are stored in MinIO bucket <strong>odras-files</strong>.</p>
          <form id="batch-upload-form" enctype="multipart/form-data" style="margin-bottom:0.75rem;">
            <div id="dropzone" style="border:2px dashed #93c5fd; background:#f0f7ff; padding:16px; border-radius:8px; text-align:center; cursor:pointer;">
              Drag & drop files here or click to select
            </div>
            <input type="file" name="files" id="batch-files" multiple style="display:none;" />
            <div id="pending-files" style="margin-top:8px; color:#555;"></div>
            <div style="display:flex; gap: 0.5rem; align-items:center; margin-top:8px;">
              <button type="submit">Upload to Storage</button>
              <span id="batch-upload-status" class="status" style="margin-left:8px;"></span>
            </div>
          </form>
          <div id="files-list">No files loaded</div>
        </div>
      </div>

      <!-- User Tasks Tab -->
      <div id="tasks-tab" class="tab-content">
        <div class="card">
          <h3>Pending User Tasks</h3>
          <p style="color: #666; margin-bottom: 20px;">
            Tasks requiring your review or approval in the BPMN workflow.
          </p>
          <div id="user-tasks-list">
            <div style="padding: 20px; text-align: center; color: #999;">
              No pending tasks. Tasks will appear here when a workflow requires user input.
            </div>
          </div>
          <button onclick="refreshUserTasks()" style="margin-top: 20px;">Refresh Tasks</button>
        </div>
      </div>

      <script>
        const form = document.getElementById('upload-form');
        const result = document.getElementById('result');
        const providerSelect = document.querySelector('select[name="llm_provider"]');
        const modelSelect = document.getElementById('llm_model');

        // Check all statuses on page load and set up auto-refresh
        console.log('Page loaded, checking status...');
        setTimeout(() => {
          console.log('Checking all statuses...');
          checkAllStatuses();
          // Auto-refresh status every 10 seconds
          setInterval(checkAllStatuses, 10000);
        }, 100);
        setTimeout(() => {
          console.log('Refreshing runs...');
          refreshRuns();
        }, 200);

        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const data = new FormData(form);
          result.innerHTML = '<div class="status running">Starting BPMN process...</div>';

          const res = await fetch('/api/upload', { method: 'POST', body: data });
          const json = await res.json();

          if (!res.ok) {
            result.innerHTML = `<div class="status error">Error: ${JSON.stringify(json)}</div>`;
            return;
          }

          result.innerHTML = `<div class="status running">BPMN process started: ${json.process_id}</div>`;
          refreshRuns();

          // Poll for completion
          const interval = setInterval(async () => {
            const sres = await fetch(`/api/runs/${json.run_id}`);
            const sjson = await sres.json();

            if (sjson.status === 'completed') {
              result.innerHTML = `<div class="status completed">Process completed! <a href="${sjson.camunda_url}" target="_blank">View in Camunda</a></div>`;
              clearInterval(interval);
              refreshRuns();
            } else if (sjson.camunda_error) {
              result.innerHTML = `<div class="status error">Camunda error: ${sjson.camunda_error}</div>`;
              clearInterval(interval);
            }
          }, 2000);
        });

        providerSelect.addEventListener('change', async () => {
          console.log('Provider changed to:', providerSelect.value);
          const provider = providerSelect.value;

          // Clear the select dropdown
          modelSelect.innerHTML = '<option value="">Loading models...</option>';

          if (!provider) {
            modelSelect.innerHTML = '<option value="">Select a provider first...</option>';
            return;
          }

          try {
            console.log('Fetching models for provider:', provider);
            const res = await fetch(`/api/models/${provider}`);
            const json = await res.json();
            console.log('Models response:', json);

            // Extract model names based on provider format
            let modelNames = [];
            if (json.models && Array.isArray(json.models)) {
              if (provider === 'openai') {
                // OpenAI models have 'id' field
                modelNames = json.models.map(m => {
                  if (typeof m === 'string') return m;
                  return m.id || m.name || '';
                }).filter(Boolean);
              } else if (provider === 'ollama') {
                // Ollama models have 'model' or 'name' field
                modelNames = json.models.map(m => {
                  if (typeof m === 'string') return m;
                  return m.model || m.name || '';
                }).filter(Boolean);
              }
            }

            console.log('Available models:', modelNames);

            // Clear and populate the select dropdown with all models
            modelSelect.innerHTML = '';

            // Add a default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select a model...';
            modelSelect.appendChild(defaultOption);

            // Add all model options
            modelNames.forEach(name => {
              const option = document.createElement('option');
              option.value = name;
              option.textContent = name;
              modelSelect.appendChild(option);
            });

            // Set a default value if models are available
            if (modelNames.length > 0) {
              // For OpenAI, prefer gpt-4o-mini or gpt-3.5-turbo
              if (provider === 'openai') {
                const preferred = modelNames.find(m => m.includes('gpt-4o-mini')) ||
                                modelNames.find(m => m.includes('gpt-3.5-turbo')) ||
                                modelNames[0];
                modelSelect.value = preferred;
              } else {
                // For Ollama, just use the first available model
                modelSelect.value = modelNames[0];
              }
              console.log('Set default model to:', modelSelect.value);
              console.log('Total models in dropdown:', modelNames.length);
            }
          } catch (e) {
            console.error('Error fetching models:', e);
            // On error, show a message in the dropdown
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
          }
        });

        window.checkAllStatuses = async function() {
          // Helper function to update status badge
          function updateStatus(elementId, serviceName, status, details = '') {
            const badge = document.getElementById(elementId);
            const indicator = badge.querySelector('.status-indicator');

            // Remove all status classes
            badge.classList.remove('online', 'offline', 'warning');

            if (status === 'running' || status === 'online') {
              badge.classList.add('online');
              indicator.textContent = '●';
              badge.title = `${serviceName} is running${details ? ': ' + details : ''}`;
            } else if (status === 'offline' || status === 'unreachable') {
              badge.classList.add('offline');
              indicator.textContent = '○';
              badge.title = `${serviceName} is offline${details ? ': ' + details : ''}`;
            } else {
              badge.classList.add('warning');
              indicator.textContent = '◐';
              badge.title = `${serviceName}: ${status}${details ? ' - ' + details : ''}`;
            }
          }

          // Check Camunda status
          try {
            const res = await fetch('/api/camunda/status');
            const json = await res.json();
            updateStatus('camunda-status', 'Camunda', json.status, json.message);
          } catch (e) {
            updateStatus('camunda-status', 'Camunda', 'offline', 'Cannot connect');
          }

          // Check Ollama status
          try {
            const res = await fetch('/api/ollama/status');
            const json = await res.json();
            const details = json.status === 'running' ? `${json.model_count} models` : json.error;
            updateStatus('ollama-status', 'Ollama', json.status, details);
          } catch (e) {
            updateStatus('ollama-status', 'Ollama', 'offline', 'Cannot check status');
          }

          // Check OpenAI status
          try {
            const res = await fetch('/api/openai/status');
            const json = await res.json();
            const details = json.status === 'running' ? `${json.model_count} models` : json.message;
            updateStatus('openai-status', 'OpenAI', json.status, details);
          } catch (e) {
            updateStatus('openai-status', 'OpenAI', 'offline', 'Cannot check status');
          }
        }

        // Keep backward compatibility
        window.checkCamundaStatus = checkAllStatuses;

        // Batch upload handler + drag & drop
        (function(){
          const form = document.getElementById('batch-upload-form');
          if (!form) return;
          const input = document.getElementById('batch-files');
          const dz = document.getElementById('dropzone');
          const pending = document.getElementById('pending-files');
          function updatePending() {
            const files = input.files;
            if (!files || files.length === 0) { pending.textContent = ''; return; }
            const list = Array.from(files).map(f => `${f.name} (${f.size} bytes)`).join(', ');
            pending.textContent = `Selected: ${list}`;
          }
          dz.addEventListener('click', () => input.click());
          dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.style.background = '#e6f0ff'; });
          dz.addEventListener('dragleave', () => { dz.style.background = '#f0f7ff'; });
          dz.addEventListener('drop', (e) => {
            e.preventDefault(); dz.style.background = '#f0f7ff';
            const dt = new DataTransfer();
            Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
            input.files = dt.files;
            updatePending();
          });
          input.addEventListener('change', updatePending);

          form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusEl = document.getElementById('batch-upload-status');
            statusEl.className = 'status running';
            statusEl.textContent = 'Uploading...';
            try {
              const fd = new FormData();
              const files = input.files;
              for (let i=0;i<files.length;i++){ fd.append('files', files[i]); }
              // No project context
              const res = await fetch('/api/files/batch/upload', { method: 'POST', body: fd });
              const json = await res.json();
              if (res.ok && json.success !== false) {
                statusEl.className = 'status completed';
                statusEl.textContent = `Uploaded ${json.summary?.successful_uploads ?? files.length} files`;
                input.value = '';
                pending.textContent = '';
                loadFiles();
              } else {
                statusEl.className = 'status error';
                statusEl.textContent = 'Upload failed';
              }
            } catch (err) {
              statusEl.className = 'status error';
              statusEl.textContent = 'Upload error';
            }
          });
        })();

        window.refreshRuns = async function() {
          const runsDiv = document.getElementById('runs-list');
          try {
            const res = await fetch('/api/runs');
            const json = await res.json();
            if (json.runs && json.runs.length > 0) {
              runsDiv.innerHTML = json.runs.map(run =>
                `<div class="status ${run.status}">${run.filename} - ${run.status} <a href="${run.camunda_url}" target="_blank">View</a></div>`
              ).join('');
            } else {
              runsDiv.innerHTML = '<div>No active runs</div>';
            }
          } catch (e) {
            runsDiv.innerHTML = '<div class="status error">Error loading runs</div>';
          }
        }

        // Refresh User Tasks
        window.refreshUserTasks = async function() {
          const tasksDiv = document.getElementById('user-tasks-list');
          const taskBadge = document.getElementById('task-count-badge');

          try {
            const res = await fetch('/api/user-tasks');
            const json = await res.json();

            if (json.tasks && json.tasks.length > 0) {
              // Update badge
              taskBadge.textContent = json.tasks.length;
              taskBadge.style.display = 'inline-block';

              // Build task cards
              tasksDiv.innerHTML = json.tasks.map(task => `
                <div style="border: 1px solid #007bff; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f0f7ff;">
                  <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #007bff;">${task.name}</h4>
                    <span style="background: #ffc107; color: #000; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                      ${task.taskDefinitionKey}
                    </span>
                  </div>

                  <div style="color: #666; margin-bottom: 10px;">
                    <strong>Process Instance:</strong> ${task.processInstanceId}<br/>
                    <strong>Created:</strong> ${new Date(task.created).toLocaleString()}<br/>
                    ${task.description ? `<strong>Description:</strong> ${task.description}<br/>` : ''}
                  </div>

                  <button onclick="reviewTask('${task.id}')" style="background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                    Review Requirements
                  </button>
                </div>
              `).join('');
            } else {
              tasksDiv.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #999;">
                  No pending tasks. Tasks will appear here when a workflow requires user input.
                </div>
              `;
              // Hide badge
              taskBadge.style.display = 'none';
            }
          } catch (e) {
            tasksDiv.innerHTML = `
              <div style="padding: 20px; text-align: center; color: #dc3545;">
                Error loading tasks: ${e.message}
              </div>
            `;
            taskBadge.style.display = 'none';
          }
        }

        // Review a specific task
        window.reviewTask = async function(taskId) {
          // For now, redirect to the user-review page
          // Later we can implement an inline review interface
          window.location.href = `/user-review?taskId=${taskId}`;
        }

        // Tab Management - Make it global
        window.showTab = function(tabName) {
          console.log('showTab called with:', tabName);

          try {
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.remove('active'));

            // Remove active class from all tab buttons
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => button.classList.remove('active'));

            // Show selected tab content
            const targetTab = document.getElementById(tabName + '-tab');
            if (targetTab) {
              targetTab.classList.add('active');
              console.log('Tab content shown:', tabName);
            } else {
              console.error('Tab content not found:', tabName + '-tab');
            }

            // Add active class to selected tab button
            const activeButton = document.querySelector(`[onclick='showTab("${tabName}")']`);
            if (activeButton) {
              activeButton.classList.add('active');
              console.log('Tab button activated:', tabName);
            } else {
              console.error('Tab button not found for:', tabName);
            }

            // Load content for specific tabs
            if (tabName === 'personas') {
              console.log('Loading personas...');
              loadPersonas();
            } else if (tabName === 'prompts') {
              console.log('Loading prompts...');
              loadPrompts();
          } else if (tabName === 'files') {
            console.log('Loading files...');
            loadFiles();
            }
          } catch (e) {
            console.error('Error in showTab:', e);
          }
        }

        // Persona Management
        let personas = [
          {
            id: 'extractor',
            name: 'Extractor',
            description: 'You extract ontology-grounded entities from requirements.',
            system_prompt: 'You are an expert requirements analyst. Your role is to extract ontology-grounded entities from requirements text. Return ONLY JSON conforming to the provided schema.',
            is_active: true
          },
          {
            id: 'reviewer',
            name: 'Reviewer',
            description: 'You validate and correct extracted JSON to fit the schema strictly.',
            system_prompt: 'You are a quality assurance specialist. Your role is to validate and correct extracted JSON to ensure it strictly conforms to the provided schema. Return ONLY JSON conforming to the schema.',
            is_active: true
          }
        ];

        window.addPersona = function() {
          const newPersona = {
            id: 'persona_' + Date.now(),
            name: 'New Persona',
            description: 'Enter persona description',
            system_prompt: 'Enter system prompt for this persona',
            is_active: true
          };
          personas.push(newPersona);
          renderPersonas();
        }

        function deletePersona(personaId) {
          personas = personas.filter(p => p.id !== personaId);
          renderPersonas();
        }

        function togglePersona(personaId) {
          const persona = personas.find(p => p.id === personaId);
          if (persona) {
            persona.is_active = !persona.is_active;
            renderPersonas();
          }
        }

        window.renderPersonas = function() {
          const container = document.getElementById('personas-list');
          container.innerHTML = personas.map(persona => `
            <div class="persona-item">
              <h4>${persona.name}</h4>
              <div class="form-group">
                <label>Name:</label>
                <input type="text" value="${persona.name}" onchange="updatePersona('${persona.id}', 'name', this.value)">
              </div>
              <div class="form-group">
                <label>Description:</label>
                <input type="text" value="${persona.description}" onchange="updatePersona('${persona.id}', 'description', this.value)">
              </div>
              <div class="form-group">
                <label>System Prompt:</label>
                <textarea rows="4" onchange="updatePersona('${persona.id}', 'system_prompt', this.value)">${persona.system_prompt}</textarea>
              </div>
              <div class="form-group">
                <label>
                  <input type="checkbox" ${persona.is_active ? 'checked' : ''} onchange="togglePersona('${persona.id}')">
                  Active
                </label>
              </div>
              <button onclick="deletePersona('${persona.id}')">Delete</button>
            </div>
          `).join('');
        }

        function updatePersona(personaId, field, value) {
          const persona = personas.find(p => p.id === personaId);
          if (persona) {
            persona[field] = value;
          }
        }

        async function savePersonas() {
          try {
            // Save each persona to the API
            for (const persona of personas) {
              if (persona.id.startsWith('persona_')) {
                // New persona - create it
                await fetch('/api/personas', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(persona)
                });
              } else {
                // Existing persona - update it
                await fetch(`/api/personas/${persona.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(persona)
                });
              }
            }
            alert('Personas saved successfully!');
          } catch (e) {
            alert('Error saving personas: ' + e.message);
          }
        }

        window.loadPersonas = async function() {
          try {
            const response = await fetch('/api/personas');
            const data = await response.json();
            personas = data.personas || personas;
            renderPersonas();
          } catch (e) {
            console.error('Error loading personas:', e);
            // Fallback to default personas
            renderPersonas();
          }
        }

        // Prompt Management
        let prompts = [
          {
            id: 'default_analysis',
            name: 'Default Analysis',
            description: 'Default prompt for requirement analysis',
            prompt_template: 'Analyze the following requirement and extract key information:\\n\\nRequirement: {requirement_text}\\nCategory: {category}\\nSource: {source_file}\\nIteration: {iteration}\\n\\nPlease provide:\\n1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)\\n2. Constraints and dependencies\\n3. Performance requirements\\n4. Quality attributes\\n5. Confidence level (0.0-1.0)\\n\\nFormat your response as JSON.',
            variables: ['requirement_text', 'category', 'source_file', 'iteration'],
            is_active: true
          }
        ];

        function addPrompt() {
          const newPrompt = {
            id: 'prompt_' + Date.now(),
            name: 'New Prompt',
            description: 'Enter prompt description',
            prompt_template: 'Enter prompt template with {variables}',
            variables: ['variable1', 'variable2'],
            is_active: true
          };
          prompts.push(newPrompt);
          renderPrompts();
        }

        function deletePrompt(promptId) {
          prompts = prompts.filter(p => p.id !== promptId);
          renderPrompts();
        }

        function togglePrompt(promptId) {
          const prompt = prompts.find(p => p.id === promptId);
          if (prompt) {
            prompt.is_active = !prompt.is_active;
            renderPrompts();
          }
        }

        window.renderPrompts = function() {
          const container = document.getElementById('prompts-list');
          container.innerHTML = prompts.map(prompt => `
            <div class="prompt-item">
              <h4>${prompt.name}</h4>
              <div class="form-group">
                <label>Name:</label>
                <input type="text" value="${prompt.name}" onchange="updatePrompt('${prompt.id}', 'name', this.value)">
              </div>
              <div class="form-group">
                <label>Description:</label>
                <input type="text" value="${prompt.description}" onchange="updatePrompt('${prompt.id}', 'description', this.value)">
              </div>
              <div class="form-group">
                <label>Prompt Template:</label>
                <textarea rows="6" onchange="updatePrompt('${prompt.id}', 'prompt_template', this.value)">${prompt.prompt_template}</textarea>
              </div>
              <div class="form-group">
                <label>Variables (comma-separated):</label>
                <input type="text" value="${prompt.variables.join(', ')}" onchange="updatePrompt('${prompt.id}', 'variables', this.value.split(',').map(v => v.trim()))">
              </div>
              <div class="form-group">
                <label>
                  <input type="checkbox" ${prompt.is_active ? 'checked' : ''} onchange="togglePrompt('${prompt.id}')">
                  Active
                </label>
              </div>
              <div class="test-section">
                <h5>Test Prompt</h5>
                <div class="test-input">
                  <label>Test Variables (JSON):</label>
                  <textarea rows="3" placeholder='{"requirement_text": "Test requirement", "category": "Test", "source_file": "test.txt", "iteration": 1}'>${JSON.stringify({requirement_text: "Test requirement", category: "Test", source_file: "test.txt", iteration: 1}, null, 2)}</textarea>
                </div>
                <button onclick="testPrompt('${prompt.id}', this.previousElementSibling.querySelector('textarea').value)">Test Prompt</button>
                <div class="test-result" id="test-result-${prompt.id}"></div>
              </div>
              <button onclick="deletePrompt('${prompt.id}')">Delete</button>
            </div>
          `).join('');
        }

        function updatePrompt(promptId, field, value) {
          const prompt = prompts.find(p => p.id === promptId);
          if (prompt) {
            prompt[field] = value;
          }
        }

        async function savePrompts() {
          try {
            // Save each prompt to the API
            for (const prompt of prompts) {
              if (prompt.id.startsWith('prompt_')) {
                // New prompt - create it
                await fetch('/api/prompts', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(prompt)
                });
              } else {
                // Existing prompt - update it
                await fetch(`/api/prompts/${prompt.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(prompt)
                });
              }
            }
            alert('Prompts saved successfully!');
          } catch (e) {
            alert('Error saving prompts: ' + e.message);
          }
        }

        window.loadPrompts = async function() {
          try {
            const response = await fetch('/api/prompts');
            const data = await response.json();
            prompts = data.prompts || prompts;
            renderPrompts();
          } catch (e) {
            console.error('Error loading prompts:', e);
            // Fallback to default prompts
            renderPrompts();
          }
        }

        async function testPrompt(promptId, testVariablesJson) {
          try {
            const testVariables = JSON.parse(testVariablesJson);
            const prompt = prompts.find(p => p.id === promptId);
            if (!prompt) return;

            const resultDiv = document.getElementById(`test-result-${promptId}`);
            resultDiv.innerHTML = '<div class="status running">Testing prompt...</div>';

            // Test with the API
            const response = await fetch(`/api/prompts/${promptId}/test`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(testVariables)
            });

            if (response.ok) {
              const result = await response.json();
              resultDiv.innerHTML = `
                <div class="status completed">
                  <strong>Filled Prompt:</strong><br>
                  <pre>${result.filled_prompt}</pre>
                  <br><strong>Test Variables:</strong><br>
                  <pre>${JSON.stringify(result.test_variables, null, 2)}</pre>
                </div>
              `;
            } else {
              const error = await response.json();
              resultDiv.innerHTML = `<div class="status error">Error: ${error.detail}</div>`;
            }
          } catch (e) {
            const resultDiv = document.getElementById(`test-result-${promptId}`);
            resultDiv.innerHTML = `<div class="status error">Error: ${e.message}</div>`;
          }
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
          console.log('DOM loaded, initializing...');
          try {
            loadPersonas();
            loadPrompts();
            refreshUserTasks();  // Check for user tasks on load
            checkAllStatuses();  // Check service statuses
            console.log('Initialization complete');
          } catch (e) {
            console.error('Error during initialization:', e);
          }

          // Periodically check for updates
          setInterval(checkAllStatuses, 10000);  // Service status every 10 seconds
          setInterval(refreshUserTasks, 30000);  // User tasks every 30 seconds
        });

        // Files Tab helpers
        window.loadFiles = async function() {
          const res = await fetch('/api/files');
          const json = await res.json();
          const el = document.getElementById('files-list');
          if (json.success && json.files && json.files.length) {
            el.innerHTML = json.files.map(f => `
              <div class=\"status\" style=\"display:flex; align-items:center; justify-content:space-between; gap:8px; background:#f9fafb;\">
                <div>
                  <div><strong>${f.filename}</strong></div>
                  <div style=\"font-size:12px; color:#666;\">${f.size} bytes · ${f.file_id}</div>
                </div>
                <button onclick=\"deleteStoredFile('${f.file_id}')\" style=\"background:#dc2626; color:white; border:none; padding:6px 10px; border-radius:4px; cursor:pointer;\">Delete</button>
              </div>
            `).join('');
          } else {
            el.innerHTML = '<div>No files found</div>';
          }
        }

        window.deleteStoredFile = async function(fileId) {
          if (!confirm('Delete this file?')) return;
          const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
          if (res.ok) {
            loadFiles();
          } else {
            alert('Delete failed');
          }
        }

        async function loadKeywordConfig() {
          try {
            const res = await fetch('/api/files/keywords');
            const cfg = await res.json();
            const el = document.getElementById('kw-config');
            el.innerHTML = `
              <div style=\"display:flex; flex-direction:column; gap:6px;\">
                <label>Keywords (comma-separated)</label>
                <input type=\"text\" id=\"kw-list\" value=\"${(cfg.keywords||[]).join(', ')}\"/>
                <div style=\"display:flex; gap:8px;\">
                  <label>Min length</label>
                  <input type=\"number\" id=\"kw-min\" value=\"${cfg.min_text_length||15}\" style=\"width:80px;\" />
                  <label>Context</label>
                  <input type=\"number\" id=\"kw-ctx\" value=\"${cfg.context_window||160}\" style=\"width:80px;\" />
                  <button onclick=\"saveKeywordConfig()\">Save</button>
                </div>
              </div>`;
          } catch (e) { console.error(e); }
        }

        window.saveKeywordConfig = async function() {
          const body = {
            keywords: document.getElementById('kw-list').value.split(',').map(s => s.trim()).filter(Boolean),
            min_text_length: parseInt(document.getElementById('kw-min').value||'15'),
            context_window: parseInt(document.getElementById('kw-ctx').value||'160')
          };
          await fetch('/api/files/keywords', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
          await loadKeywordConfig();
        }

        window.runKeywordExtraction = async function() {
          const project = document.getElementById('files-project').value || '';
          const fd = new FormData();
          if (project) fd.append('project_id', project);
          const res = await fetch('/api/files/extract/keywords', { method: 'POST', body: fd });
          const json = await res.json();
          const el = document.getElementById('kw-result');
          if (json.success) {
            el.className = 'status completed';
            el.textContent = `Extracted ${json.extracted_count} sentences; wrote ${json.triples_written} triples.`;
          } else {
            el.className = 'status error';
            el.textContent = 'Extraction failed';
          }
        }

      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/models/ollama", response_model=dict)
async def list_ollama_models():
    settings = Settings()
    base = settings.ollama_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/api/tags")
            r.raise_for_status()
            data = r.json()
            # Normalize shape
            return {"provider": "ollama", "models": data.get("models", data)}
    except Exception as e:
        return {"provider": "ollama", "error": str(e)}


@app.get("/api/models/openai", response_model=dict)
async def list_openai_models():
    api_key = Settings().openai_api_key
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = "https://api.openai.com/v1/models"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 401:
                return {
                    "provider": "openai",
                    "error": "Unauthorized (set OPENAI_API_KEY)",
                }
            r.raise_for_status()
            data = r.json()
            return {"provider": "openai", "models": data.get("data", [])}
    except Exception as e:
        return {"provider": "openai", "error": str(e)}


@app.get("/api/runs")
async def list_runs():
    """List all runs."""
    return {"runs": list(RUNS.values())}


# Persona Management API
@app.get("/api/personas")
async def list_personas():
    """List all personas."""
    return {"personas": PERSONAS}


@app.post("/api/personas")
async def create_persona(persona: Dict):
    """Create a new persona."""
    new_persona = {
        "id": persona.get("id", f"persona_{int(time.time() * 1000)}"),
        "name": persona.get("name", "New Persona"),
        "description": persona.get("description", ""),
        "system_prompt": persona.get("system_prompt", ""),
        "is_active": persona.get("is_active", True),
    }
    PERSONAS.append(new_persona)
    return {"persona": new_persona, "message": "Persona created successfully"}


@app.put("/api/personas/{persona_id}")
async def update_persona(persona_id: str, persona: Dict):
    """Update an existing persona."""
    for i, existing_persona in enumerate(PERSONAS):
        if existing_persona["id"] == persona_id:
            PERSONAS[i].update(persona)
            return {"persona": PERSONAS[i], "message": "Persona updated successfully"}
    raise HTTPException(status_code=404, detail="Persona not found")


@app.delete("/api/personas/{persona_id}")
async def delete_persona(persona_id: str):
    """Delete a persona."""
    global PERSONAS
    PERSONAS = [p for p in PERSONAS if p["id"] != persona_id]
    return {"message": "Persona deleted successfully"}


# Prompt Management API
@app.get("/api/prompts")
async def list_prompts():
    """List all prompts."""
    return {"prompts": PROMPTS}


@app.post("/api/prompts")
async def create_prompt(prompt: Dict):
    """Create a new prompt."""
    new_prompt = {
        "id": prompt.get("id", f"prompt_{int(time.time() * 1000)}"),
        "name": prompt.get("name", "New Prompt"),
        "description": prompt.get("description", ""),
        "prompt_template": prompt.get("prompt_template", ""),
        "variables": prompt.get("variables", []),
        "is_active": prompt.get("is_active", True),
    }
    PROMPTS.append(new_prompt)
    return {"prompt": new_prompt, "message": "Prompt created successfully"}


@app.put("/api/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: Dict):
    """Update an existing prompt."""
    for i, existing_prompt in enumerate(PROMPTS):
        if existing_prompt["id"] == prompt_id:
            PROMPTS[i].update(prompt)
            return {"prompt": PROMPTS[i], "message": "Prompt updated successfully"}
    raise HTTPException(status_code=404, detail="Prompt not found")


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    global PROMPTS
    PROMPTS = [p for p in PROMPTS if p["id"] != prompt_id]
    return {"message": "Prompt deleted successfully"}


@app.post("/api/prompts/{prompt_id}/test")
async def test_prompt(prompt_id: str, test_data: Dict):
    """Test a prompt with sample variables."""
    prompt = next((p for p in PROMPTS if p["id"] == prompt_id), None)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    try:
        # Fill the prompt template with test variables
        filled_prompt = prompt["prompt_template"]
        for variable in prompt.get("variables", []):
            if variable in test_data:
                filled_prompt = filled_prompt.replace(f"{{{variable}}}", str(test_data[variable]))

        return {
            "prompt_id": prompt_id,
            "filled_prompt": filled_prompt,
            "test_variables": test_data,
            "message": "Prompt filled successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing prompt: {str(e)}")


# User Task Management API for BPMN User Tasks
@app.get("/api/user-tasks")
async def get_all_user_tasks():
    """Get all pending user tasks across all process instances."""
    try:
        # Get all active user tasks from Camunda
        response = requests.get(
            f"{CAMUNDA_REST_API}/task",
            params={
                "processDefinitionKey": "odras_requirements_analysis",
                "taskDefinitionKey": "Task_UserReview",  # Our user review task
                "active": "true",
            },
        )

        if response.status_code == 200:
            tasks = response.json()

            # Format tasks for UI
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append(
                    {
                        "id": task.get("id"),
                        "name": task.get("name", "Review Requirements"),
                        "description": task.get(
                            "description", "Review and approve extracted requirements"
                        ),
                        "taskDefinitionKey": task.get("taskDefinitionKey"),
                        "processInstanceId": task.get("processInstanceId"),
                        "created": task.get("created"),
                        "priority": task.get("priority", 50),
                    }
                )

            return {"tasks": formatted_tasks}
        else:
            return {
                "tasks": [],
                "error": f"Camunda returned status {response.status_code}",
            }

    except Exception as e:
        return {"tasks": [], "error": str(e)}


@app.get("/api/user-tasks/{process_instance_id}")
async def get_user_tasks(process_instance_id: str):
    """Get user tasks for a specific process instance."""
    try:
        # Query Camunda for user tasks
        tasks_url = f"{CAMUNDA_REST_API}/task"
        params = {"processInstanceId": process_instance_id}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(tasks_url, params=params)
            response.raise_for_status()
            tasks = response.json()

            # Filter for user tasks
            user_tasks = [
                task for task in tasks if task.get("taskDefinitionKey") == "Task_UserReview"
            ]

            return {
                "process_instance_id": process_instance_id,
                "user_tasks": user_tasks,
                "total_tasks": len(user_tasks),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user tasks: {str(e)}")


@app.get("/api/user-tasks/{process_instance_id}/requirements")
async def get_requirements_for_review(process_instance_id: str):
    """Get extracted requirements for user review."""
    try:
        # Get process variables to find requirements
        variables_url = f"{CAMUNDA_REST_API}/process-instance/{process_instance_id}/variables"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(variables_url)
            response.raise_for_status()
            variables = response.json()

            # Extract requirements from process variables
            requirements_list = []
            if "requirements_list" in variables:
                requirements_data = variables["requirements_list"]["value"]
                if isinstance(requirements_data, str):
                    requirements_list = json.loads(requirements_data)
                else:
                    requirements_list = requirements_data

            document_content = variables.get("document_content", {}).get("value", "")
            document_filename = variables.get("document_filename", {}).get("value", "unknown")

            return {
                "process_instance_id": process_instance_id,
                "requirements": requirements_list,
                "document_content": document_content,
                "document_filename": document_filename,
                "total_requirements": len(requirements_list),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching requirements: {str(e)}")


@app.post("/api/user-tasks/{process_instance_id}/complete")
async def complete_user_task(process_instance_id: str, user_decision: Dict):
    """Complete a user task with user decision (approve, edit, or rerun)."""
    try:
        # Get the task ID for this process instance
        tasks_url = f"{CAMUNDA_REST_API}/task"
        params = {"processInstanceId": process_instance_id}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(tasks_url, params=params)
            response.raise_for_status()
            tasks = response.json()

            # Find the user review task
            user_task = next(
                (task for task in tasks if task.get("taskDefinitionKey") == "Task_UserReview"),
                None,
            )
            if not user_task:
                raise HTTPException(status_code=404, detail="User review task not found")

            task_id = user_task["id"]

            # Prepare variables based on user decision
            decision = user_decision.get("decision", "approve")
            variables = {"user_choice": {"value": decision, "type": "String"}}

            # Add additional variables based on decision
            if decision == "edit":
                user_edits = user_decision.get("user_edits", [])
                variables["user_edits"] = {
                    "value": json.dumps(user_edits),
                    "type": "String",
                }
            elif decision == "rerun":
                extraction_parameters = user_decision.get("extraction_parameters", {})
                variables["extraction_parameters"] = {
                    "value": json.dumps(extraction_parameters),
                    "type": "String",
                }

            # Complete the task
            complete_url = f"{CAMUNDA_REST_API}/task/{task_id}/complete"
            complete_response = await client.post(complete_url, json={"variables": variables})
            complete_response.raise_for_status()

            # Update run status
            if process_instance_id in RUNS:
                RUNS[process_instance_id]["status"] = f"user_task_completed_{decision}"
                RUNS[process_instance_id]["user_decision"] = user_decision

            return {
                "task_id": task_id,
                "process_instance_id": process_instance_id,
                "decision": decision,
                "status": "completed",
                "message": f"User task completed with decision: {decision}",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing user task: {str(e)}")


@app.get("/api/user-tasks/{process_instance_id}/status")
async def get_user_task_status(process_instance_id: str):
    """Get the current status of user tasks in a process instance."""
    try:
        # Get process instance status
        instance_url = f"{CAMUNDA_REST_API}/process-instance/{process_instance_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(instance_url)
            response.raise_for_status()
            instance = response.json()

            # Get current activities
            activities_url = (
                f"{CAMUNDA_REST_API}/process-instance/{process_instance_id}/activity-instances"
            )
            activities_response = await client.get(activities_url)
            activities_response.raise_for_status()
            activities = activities_response.json()

            # Determine current state
            current_state = "unknown"
            if activities.get("childActivityInstances"):
                for activity in activities["childActivityInstances"]:
                    if activity.get("activityId") == "Task_UserReview":
                        current_state = "waiting_for_user_review"
                    elif activity.get("activityId") == "Gateway_UserChoice":
                        current_state = "user_decision_made"
                    elif activity.get("activityId") == "Task_LLMProcessing":
                        current_state = "llm_processing"
                    elif activity.get("activityId") == "Task_StoreVector":
                        current_state = "storing_results"

            return {
                "process_instance_id": process_instance_id,
                "current_state": current_state,
                "process_status": instance.get("state", "unknown"),
                "business_key": instance.get("businessKey"),
                "start_time": instance.get("startTime"),
                "end_time": instance.get("endTime"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task status: {str(e)}")


def run():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
