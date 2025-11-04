"""
ODRAS Main Application Entry Point

This module has been refactored to use modular components:
- backend/app_factory.py: Application creation
- backend/startup/: Startup initialization modules
- backend/api/core.py: Core API endpoints (auth, health, sync, projects)
- backend/api/*: Feature-specific API routers
"""

import logging
from typing import Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse

from backend.app_factory import create_app
from backend.startup import initialize_application, register_routers
from backend.api.core import set_db_instance, get_user
from backend.services.config import Settings
from backend.services.db import DatabaseService

logger = logging.getLogger(__name__)

# Create application using factory
app = create_app()

# Initialize database connection
settings = Settings()
try:
    db = DatabaseService(settings)
    logger.info(
        f"Database connected successfully to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
    )
    # Set database instance for core API
    set_db_instance(db)
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    logger.error(
        f"Database settings: host={settings.postgres_host}, port={settings.postgres_port}, "
        f"database={settings.postgres_database}, user={settings.postgres_user}"
    )

    # Provide a fallback that raises a 503 on any DB method usage
    class _DBUnavailable:
        def __getattr__(self, _name):
            def _raise(*_args, **_kwargs):
                raise HTTPException(status_code=503, detail="Database unavailable")
            return _raise

    db = _DBUnavailable()

# Camunda configuration
CAMUNDA_BASE_URL = settings.camunda_base_url
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

# Register all API routers
register_routers(app)

# UI Routes
@app.get("/app", response_class=HTMLResponse)
def ui_restart():
    """Serve the main ODRAS application UI"""
    try:
        with open("frontend/app.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>App not found</h1>", status_code=404)


@app.get("/ontology-editor", response_class=HTMLResponse)
def ontology_editor():
    """Serve the ontology editor UI"""
    try:
        with open("frontend/ontology-editor.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Ontology editor not found</h1>", status_code=404)


@app.get("/session-intelligence-demo", response_class=HTMLResponse)
def session_intelligence_demo():
    """Serve the session intelligence demo UI"""
    try:
        with open("frontend/session-intelligence-demo.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Session intelligence demo not found</h1>", status_code=404)


@app.get("/cqmt-workbench", response_class=HTMLResponse)
def cqmt_workbench():
    """Serve the CQ/MT workbench UI"""
    try:
        with open("frontend/cqmt-workbench.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>CQ/MT workbench not found</h1>", status_code=404)


# System Configuration Endpoints
@app.get("/api/installation/config")
def get_installation_config(user=Depends(get_user)):
    """Get installation configuration"""
    return {
        "camunda_base_url": CAMUNDA_BASE_URL,
        "postgres_host": settings.postgres_host,
        "postgres_port": settings.postgres_port,
        "postgres_database": settings.postgres_database,
    }


@app.get("/api/system/db-pool-status")
async def get_db_pool_status(user=Depends(get_user)):
    """Get database connection pool status for monitoring."""
    try:
        if hasattr(db, 'get_pool_status'):
            return db.get_pool_status()
        else:
            return {"error": "Pool status not available"}
    except Exception as e:
        return {"error": str(e)}


# Admin Configuration Endpoints
@app.get("/api/admin/rag-config")
async def get_rag_config(user: Dict = Depends(get_user)):
    """Get current RAG implementation configuration (Admin only)."""
    from backend.services.auth import get_admin_user
    admin_user = get_admin_user()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve RAG configuration: {str(e)}")


@app.get("/api/admin/file-processing-config")
async def get_file_processing_config(user: Dict = Depends(get_user)):
    """Get current file processing configuration (Admin only)."""
    from backend.services.auth import get_admin_user
    admin_user = get_admin_user()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
            db._return(conn)
    
    except Exception as e:
        logger.error(f"Failed to retrieve file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file processing configuration: {str(e)}")


@app.put("/api/admin/file-processing-config")
async def update_file_processing_config(
    config: Dict[str, str],
    user: Dict = Depends(get_user)
):
    """Update file processing configuration (Admin only)."""
    from backend.services.auth import get_admin_user
    admin_user = get_admin_user()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
            db._return(conn)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update file processing configuration: {str(e)}")


@app.put("/api/admin/rag-config")
async def update_rag_config(
    config: Dict[str, str],
    user: Dict = Depends(get_user)
):
    """Update RAG implementation configuration (Admin only)."""
    from backend.services.auth import get_admin_user
    admin_user = get_admin_user()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update RAG configuration: {str(e)}")


# BPMN Workflow Endpoints (user task management)
@app.get("/api/user-tasks/{process_instance_id}/status")
async def get_user_task_status(process_instance_id: str, user=Depends(get_user)):
    """Get status of a user task in a BPMN workflow"""
    try:
        import httpx
        
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


# Startup event handler
@app.on_event("startup")
async def on_startup():
    """Initialize application on startup"""
    await initialize_application(app)


def run():
    """Run the application"""
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
