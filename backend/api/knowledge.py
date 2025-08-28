"""
Knowledge Management API endpoints.

Provides CRUD operations for knowledge assets, chunks, and processing jobs.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..services.auth import get_user, get_admin_user, is_user_admin
from ..services.config import Settings
from ..services.db import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# ========================================
# REQUEST/RESPONSE MODELS  
# ========================================

class KnowledgeAssetCreate(BaseModel):
    """Request model for creating a knowledge asset."""
    source_file_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=512)
    document_type: str = Field(default="unknown", pattern="^(requirements|specification|knowledge|reference|unknown)$")
    content_summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_options: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeAssetUpdate(BaseModel):
    """Request model for updating a knowledge asset."""
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    document_type: Optional[str] = Field(None, pattern="^(requirements|specification|knowledge|reference|unknown)$")
    content_summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|processing|failed)$")

class KnowledgeAssetResponse(BaseModel):
    """Response model for knowledge asset."""
    id: str
    source_file_id: Optional[str]
    project_id: str
    title: str
    document_type: str
    content_summary: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: str
    status: str
    processing_stats: Dict[str, Any]
    is_public: bool = False
    made_public_at: Optional[str] = None
    made_public_by: Optional[str] = None

class KnowledgeChunkResponse(BaseModel):
    """Response model for knowledge chunk."""
    id: str
    asset_id: str
    sequence_number: int
    chunk_type: str
    content: str
    token_count: int
    metadata: Dict[str, Any]
    embedding_model: Optional[str]
    qdrant_point_id: Optional[str]
    created_at: str

class ProcessingJobResponse(BaseModel):
    """Response model for processing job."""
    id: str
    asset_id: str
    job_type: str
    status: str
    progress_percent: int
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    metadata: Dict[str, Any]

class KnowledgeListResponse(BaseModel):
    """Response model for knowledge asset list."""
    assets: List[KnowledgeAssetResponse]
    total_count: int
    message: str = "Knowledge assets retrieved successfully"

class PublicAssetRequest(BaseModel):
    """Request model for making an asset public."""
    is_public: bool = Field(..., description="Whether to make the asset public")

class AssetContentResponse(BaseModel):
    """Response model for asset content."""
    id: str
    title: str
    document_type: str
    content: str
    chunks: List[KnowledgeChunkResponse] = []
    total_chunks: int = 0
    total_tokens: int = 0

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_db_service() -> DatabaseService:
    """Get database service dependency."""
    return DatabaseService(Settings())

def get_knowledge_service():
    """Get knowledge service dependency."""
    # For now, we'll use the database service directly
    # In the future, we might create a dedicated KnowledgeService
    return get_db_service()

def format_asset_response(asset_row: Dict) -> KnowledgeAssetResponse:
    """Format database row as KnowledgeAssetResponse."""
    return KnowledgeAssetResponse(
        id=str(asset_row["id"]),
        source_file_id=str(asset_row["source_file_id"]) if asset_row.get("source_file_id") else None,
        project_id=str(asset_row["project_id"]),
        title=asset_row["title"],
        document_type=asset_row["document_type"],
        content_summary=asset_row.get("content_summary"),
        metadata=asset_row.get("metadata", {}),
        created_at=asset_row["created_at"].isoformat() if asset_row.get("created_at") else "",
        updated_at=asset_row["updated_at"].isoformat() if asset_row.get("updated_at") else "",
        version=asset_row.get("version", "1.0.0"),
        status=asset_row.get("status", "active"),
        processing_stats=asset_row.get("processing_stats", {}),
        is_public=asset_row.get("is_public", False),
        made_public_at=asset_row["made_public_at"].isoformat() if asset_row.get("made_public_at") else None,
        made_public_by=asset_row.get("made_public_by")
    )

# ========================================
# KNOWLEDGE ASSET ENDPOINTS
# ========================================

@router.get("/assets", response_model=KnowledgeListResponse)
async def list_knowledge_assets(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query("active", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    List knowledge assets with optional filtering.
    
    Args:
        project_id: Optional project ID filter
        document_type: Optional document type filter  
        status: Status filter (default: active)
        limit: Maximum number of results
        offset: Result offset for pagination
        
    Returns:
        List of knowledge assets with metadata
    """
    try:
        logger.info(f"Listing knowledge assets for user {user.get('user_id')} with filters: project_id={project_id}, type={document_type}, status={status}")
        
        # Build query with filters
        where_clauses = ["1=1"]  # Base condition
        params = []
        
        # Project filter with admin and public assets logic
        if is_user_admin(user):
            # Admins can see all assets
            if project_id:
                where_clauses.append("ka.project_id = %s")
                params.append(project_id)
            # If no project_id specified, admin sees all assets (no additional filter needed)
        else:
            # Regular users see their project assets + public assets
            user_projects = db.list_projects_for_user(user_id=user["user_id"], active=True)
            
            if project_id:
                # Specific project: user's project assets + public assets
                if not db.is_user_member(project_id=project_id, user_id=user["user_id"]):
                    # User not in project, can only see public assets from this project
                    where_clauses.append("ka.project_id = %s AND ka.is_public = TRUE")
                    params.append(project_id)
                else:
                    # User in project, can see all project assets + public assets
                    where_clauses.append("(ka.project_id = %s OR ka.is_public = TRUE)")
                    params.append(project_id)
            else:
                # No project specified: user's accessible projects + public assets
                if not user_projects:
                    # User has no projects, can only see public assets
                    where_clauses.append("ka.is_public = TRUE")
                else:
                    # User has projects, see their projects + public assets
                    project_ids = [str(p["project_id"]) for p in user_projects]
                    placeholders = ",".join(["%s"] * len(project_ids))
                    where_clauses.append(f"(ka.project_id IN ({placeholders}) OR ka.is_public = TRUE)")
                    params.extend(project_ids)
        
        if document_type:
            where_clauses.append("ka.document_type = %s")
            params.append(document_type)
            
        if status:
            where_clauses.append("ka.status = %s")
            params.append(status)
        
        where_sql = " AND ".join(where_clauses)
        
        # Execute query
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get total count
                count_sql = f"SELECT COUNT(*) FROM knowledge_assets ka WHERE {where_sql}"
                cur.execute(count_sql, params)
                total_count = cur.fetchone()[0]
                
                # Get assets with pagination
                assets_sql = f"""
                    SELECT ka.*, f.filename as source_filename
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    WHERE {where_sql}
                    ORDER BY ka.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(assets_sql, params + [limit, offset])
                rows = cur.fetchall()
                
                # Format response
                assets = []
                for row in rows:
                    asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                    assets.append(format_asset_response(asset_dict))
                
                return KnowledgeListResponse(
                    assets=assets,
                    total_count=total_count,
                    message=f"Retrieved {len(assets)} knowledge assets"
                )
        finally:
            db._return(conn)
            
    except Exception as e:
        logger.error(f"Failed to list knowledge assets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge assets: {str(e)}")

@router.post("/assets", response_model=KnowledgeAssetResponse)
async def create_knowledge_asset(
    asset_data: KnowledgeAssetCreate,
    project_id: str = Query(..., description="Project ID"),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    Create a new knowledge asset.
    
    Args:
        asset_data: Knowledge asset creation data
        project_id: Project ID for the asset
        
    Returns:
        Created knowledge asset
    """
    try:
        logger.info(f"Creating knowledge asset '{asset_data.title}' for project {project_id} by user {user.get('user_id')}")
        
        # Verify user has access to project
        if not db.is_user_member(project_id=project_id, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        
        # Verify source file exists if provided
        if asset_data.source_file_id:
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM files WHERE id = %s AND project_id = %s", 
                              (asset_data.source_file_id, project_id))
                    if not cur.fetchone():
                        raise HTTPException(status_code=404, detail="Source file not found or not accessible")
            finally:
                db._return(conn)
        
        # Create knowledge asset
        asset_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_assets 
                    (id, source_file_id, project_id, title, document_type, content_summary, metadata, created_at, updated_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    asset_id,
                    asset_data.source_file_id,
                    project_id,
                    asset_data.title,
                    asset_data.document_type,
                    asset_data.content_summary,
                    asset_data.metadata,
                    now,
                    now,
                    'active'
                ))
                
                row = cur.fetchone()
                asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                conn.commit()
                
                logger.info(f"Created knowledge asset {asset_id} successfully")
                return format_asset_response(asset_dict)
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create knowledge asset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge asset: {str(e)}")

@router.get("/assets/{asset_id}", response_model=KnowledgeAssetResponse)
async def get_knowledge_asset(
    asset_id: str,
    include_chunks: bool = Query(False, description="Include chunks in response"),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    Get a specific knowledge asset by ID.
    
    Args:
        asset_id: Knowledge asset ID
        include_chunks: Whether to include chunks in response
        
    Returns:
        Knowledge asset details
    """
    try:
        logger.info(f"Getting knowledge asset {asset_id} for user {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get asset with project membership check
                cur.execute("""
                    SELECT ka.*, f.filename as source_filename
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    JOIN project_members pm ON ka.project_id = pm.project_id
                    WHERE ka.id = %s AND pm.user_id = %s
                """, (asset_id, user["user_id"]))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found or not accessible")
                
                asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                
                # Get chunks if requested
                if include_chunks:
                    cur.execute("""
                        SELECT * FROM knowledge_chunks 
                        WHERE asset_id = %s 
                        ORDER BY sequence_number
                    """, (asset_id,))
                    
                    chunk_rows = cur.fetchall()
                    chunks = []
                    for chunk_row in chunk_rows:
                        chunk_dict = dict(zip([desc[0] for desc in cur.description], chunk_row))
                        chunks.append(KnowledgeChunkResponse(
                            id=str(chunk_dict["id"]),
                            asset_id=str(chunk_dict["asset_id"]),
                            sequence_number=chunk_dict["sequence_number"],
                            chunk_type=chunk_dict["chunk_type"],
                            content=chunk_dict["content"],
                            token_count=chunk_dict.get("token_count", 0),
                            metadata=chunk_dict.get("metadata", {}),
                            embedding_model=chunk_dict.get("embedding_model"),
                            qdrant_point_id=str(chunk_dict["qdrant_point_id"]) if chunk_dict.get("qdrant_point_id") else None,
                            created_at=chunk_dict["created_at"].isoformat() if chunk_dict.get("created_at") else ""
                        ))
                    
                    # Add chunks to response metadata
                    asset_dict["chunks"] = chunks
                
                return format_asset_response(asset_dict)
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge asset: {str(e)}")

@router.put("/assets/{asset_id}", response_model=KnowledgeAssetResponse)
async def update_knowledge_asset(
    asset_id: str,
    asset_data: KnowledgeAssetUpdate,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    Update a knowledge asset.
    
    Args:
        asset_id: Knowledge asset ID
        asset_data: Update data
        
    Returns:
        Updated knowledge asset
    """
    try:
        logger.info(f"Updating knowledge asset {asset_id} by user {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Verify asset exists and user has access
                cur.execute("""
                    SELECT ka.* FROM knowledge_assets ka
                    JOIN project_members pm ON ka.project_id = pm.project_id
                    WHERE ka.id = %s AND pm.user_id = %s
                """, (asset_id, user["user_id"]))
                
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Knowledge asset not found or not accessible")
                
                # Build update query dynamically
                updates = []
                params = []
                
                if asset_data.title is not None:
                    updates.append("title = %s")
                    params.append(asset_data.title)
                    
                if asset_data.document_type is not None:
                    updates.append("document_type = %s")
                    params.append(asset_data.document_type)
                    
                if asset_data.content_summary is not None:
                    updates.append("content_summary = %s")
                    params.append(asset_data.content_summary)
                    
                if asset_data.metadata is not None:
                    updates.append("metadata = %s")
                    params.append(asset_data.metadata)
                    
                if asset_data.status is not None:
                    updates.append("status = %s")
                    params.append(asset_data.status)
                
                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")
                
                updates.append("updated_at = %s")
                params.append(datetime.now(timezone.utc))
                params.append(asset_id)
                
                update_sql = f"UPDATE knowledge_assets SET {', '.join(updates)} WHERE id = %s RETURNING *"
                cur.execute(update_sql, params)
                
                row = cur.fetchone()
                asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                conn.commit()
                
                logger.info(f"Updated knowledge asset {asset_id} successfully")
                return format_asset_response(asset_dict)
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update knowledge asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update knowledge asset: {str(e)}")

@router.delete("/assets/{asset_id}")
async def delete_knowledge_asset(
    asset_id: str,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    Delete a knowledge asset and all related data.
    
    Args:
        asset_id: Knowledge asset ID
        
    Returns:
        Deletion confirmation
    """
    try:
        logger.info(f"Deleting knowledge asset {asset_id} by user {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Verify asset exists and user has access
                if is_user_admin(user):
                    # Admin can delete any asset
                    cur.execute("SELECT ka.* FROM knowledge_assets ka WHERE ka.id = %s", (asset_id,))
                else:
                    # Regular users can only delete assets in their projects (not public assets they can view)
                    cur.execute("""
                        SELECT ka.* FROM knowledge_assets ka
                        JOIN project_members pm ON ka.project_id = pm.project_id
                        WHERE ka.id = %s AND pm.user_id = %s
                    """, (asset_id, user["user_id"]))
                
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Knowledge asset not found or not accessible")
                
                # Delete asset (cascades to chunks, relationships, jobs)
                cur.execute("DELETE FROM knowledge_assets WHERE id = %s", (asset_id,))
                
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found")
                
                conn.commit()
                logger.info(f"Deleted knowledge asset {asset_id} successfully")
                
                return {"success": True, "message": f"Knowledge asset {asset_id} deleted successfully"}
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge asset: {str(e)}")

@router.get("/assets/{asset_id}/content", response_model=AssetContentResponse)
async def get_knowledge_asset_content(
    asset_id: str,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """
    Get full content of a knowledge asset with all chunks.
    
    Args:
        asset_id: Knowledge asset ID
        
    Returns:
        Asset content with all chunks
    """
    try:
        logger.info(f"Getting content for knowledge asset {asset_id} by user {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get asset with access control (same logic as get_knowledge_asset)
                if is_user_admin(user):
                    # Admin can see all assets
                    cur.execute("SELECT ka.* FROM knowledge_assets ka WHERE ka.id = %s", (asset_id,))
                else:
                    # Regular users: their projects + public assets
                    cur.execute("""
                        SELECT ka.* FROM knowledge_assets ka
                        LEFT JOIN project_members pm ON ka.project_id = pm.project_id AND pm.user_id = %s
                        WHERE ka.id = %s AND (pm.user_id IS NOT NULL OR ka.is_public = TRUE)
                    """, (user["user_id"], asset_id))
                
                asset_row = cur.fetchone()
                if not asset_row:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found or not accessible")
                
                asset_dict = dict(zip([desc[0] for desc in cur.description], asset_row))
                
                # Get all chunks for this asset
                cur.execute("""
                    SELECT * FROM knowledge_chunks 
                    WHERE asset_id = %s 
                    ORDER BY sequence_number
                """, (asset_id,))
                
                chunk_rows = cur.fetchall()
                chunks = []
                total_tokens = 0
                
                for chunk_row in chunk_rows:
                    chunk_dict = dict(zip([desc[0] for desc in cur.description], chunk_row))
                    chunks.append(KnowledgeChunkResponse(
                        id=str(chunk_dict["id"]),
                        asset_id=str(chunk_dict["asset_id"]),
                        sequence_number=chunk_dict["sequence_number"],
                        chunk_type=chunk_dict["chunk_type"],
                        content=chunk_dict["content"],
                        token_count=chunk_dict.get("token_count", 0),
                        metadata=chunk_dict.get("metadata", {}),
                        embedding_model=chunk_dict.get("embedding_model"),
                        qdrant_point_id=str(chunk_dict["qdrant_point_id"]) if chunk_dict.get("qdrant_point_id") else None,
                        created_at=chunk_dict["created_at"].isoformat() if chunk_dict.get("created_at") else ""
                    ))
                    total_tokens += chunk_dict.get("token_count", 0)
                
                # Combine all chunk content
                full_content = "\n\n".join([chunk.content for chunk in chunks])
                
                return AssetContentResponse(
                    id=str(asset_dict["id"]),
                    title=asset_dict["title"],
                    document_type=asset_dict["document_type"],
                    content=full_content,
                    chunks=chunks,
                    total_chunks=len(chunks),
                    total_tokens=total_tokens
                )
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content for asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset content: {str(e)}")

@router.put("/assets/{asset_id}/public", response_model=KnowledgeAssetResponse)
async def set_asset_public_status(
    asset_id: str,
    public_request: PublicAssetRequest,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_admin_user)  # Admin only
):
    """
    Set public status of a knowledge asset (Admin only).
    
    Args:
        asset_id: Knowledge asset ID
        public_request: Public status request
        
    Returns:
        Updated knowledge asset
    """
    try:
        logger.info(f"Setting public status for asset {asset_id} to {public_request.is_public} by admin {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Verify asset exists
                cur.execute("SELECT id FROM knowledge_assets WHERE id = %s", (asset_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Knowledge asset not found")
                
                # Update public status
                now = datetime.now(timezone.utc)
                if public_request.is_public:
                    cur.execute("""
                        UPDATE knowledge_assets 
                        SET is_public = %s, made_public_at = %s, made_public_by = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING *
                    """, (True, now, user["user_id"], now, asset_id))
                else:
                    cur.execute("""
                        UPDATE knowledge_assets 
                        SET is_public = %s, made_public_at = NULL, made_public_by = NULL, updated_at = %s
                        WHERE id = %s
                        RETURNING *
                    """, (False, now, asset_id))
                
                row = cur.fetchone()
                asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                conn.commit()
                
                status = "public" if public_request.is_public else "private"
                logger.info(f"Successfully set asset {asset_id} as {status}")
                
                return format_asset_response(asset_dict)
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set public status for asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update asset: {str(e)}")

@router.delete("/assets/{asset_id}/force")
async def force_delete_knowledge_asset(
    asset_id: str,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_admin_user)  # Admin only for force delete
):
    """
    Force delete a knowledge asset (Admin only).
    
    This deletes the asset, all chunks, embeddings, and relationships.
    Regular users can only soft-delete their own assets.
    
    Args:
        asset_id: Knowledge asset ID
        
    Returns:
        Deletion confirmation
    """
    try:
        logger.info(f"Force deleting knowledge asset {asset_id} by admin {user.get('user_id')}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Verify asset exists
                cur.execute("SELECT id, title FROM knowledge_assets WHERE id = %s", (asset_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found")
                
                asset_title = result[1]
                
                # Delete asset (cascades to chunks, relationships, jobs)
                cur.execute("DELETE FROM knowledge_assets WHERE id = %s", (asset_id,))
                
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found")
                
                conn.commit()
                logger.info(f"Force deleted knowledge asset {asset_id} ({asset_title}) by admin")
                
                return {"success": True, "message": f"Knowledge asset '{asset_title}' permanently deleted"}
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force delete asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete asset: {str(e)}")

# ========================================
# PROCESSING JOBS ENDPOINTS
# ========================================

@router.get("/jobs", response_model=List[ProcessingJobResponse])
async def list_processing_jobs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user)
):
    """List processing jobs with optional filtering."""
    try:
        logger.info(f"Listing processing jobs for user {user.get('user_id')}")
        
        # Build query with filters
        where_clauses = ["1=1"]
        params = []
        
        # Project filter with user access check
        if project_id:
            if not db.is_user_member(project_id=project_id, user_id=user["user_id"]):
                raise HTTPException(status_code=403, detail="Not a member of project")
            where_clauses.append("ka.project_id = %s")
            params.append(project_id)
        else:
            # Get user's accessible projects
            user_projects = db.list_projects_for_user(user_id=user["user_id"], active=True)
            if not user_projects:
                return []
            
            project_ids = [str(p["project_id"]) for p in user_projects]
            placeholders = ",".join(["%s"] * len(project_ids))
            where_clauses.append(f"ka.project_id IN ({placeholders})")
            params.extend(project_ids)
        
        if status:
            where_clauses.append("kpj.status = %s")
            params.append(status)
        
        where_sql = " AND ".join(where_clauses)
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                jobs_sql = f"""
                    SELECT kpj.* FROM knowledge_processing_jobs kpj
                    JOIN knowledge_assets ka ON kpj.asset_id = ka.id
                    WHERE {where_sql}
                    ORDER BY kpj.created_at DESC
                    LIMIT %s
                """
                cur.execute(jobs_sql, params + [limit])
                rows = cur.fetchall()
                
                jobs = []
                for row in rows:
                    job_dict = dict(zip([desc[0] for desc in cur.description], row))
                    jobs.append(ProcessingJobResponse(
                        id=str(job_dict["id"]),
                        asset_id=str(job_dict["asset_id"]),
                        job_type=job_dict["job_type"],
                        status=job_dict["status"],
                        progress_percent=job_dict.get("progress_percent", 0),
                        error_message=job_dict.get("error_message"),
                        started_at=job_dict["started_at"].isoformat() if job_dict.get("started_at") else None,
                        completed_at=job_dict["completed_at"].isoformat() if job_dict.get("completed_at") else None,
                        created_at=job_dict["created_at"].isoformat() if job_dict.get("created_at") else "",
                        metadata=job_dict.get("metadata", {})
                    ))
                
                return jobs
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list processing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list processing jobs: {str(e)}")

# ========================================
# HEALTH CHECK
# ========================================

@router.get("/health")
async def knowledge_health():
    """Health check endpoint for knowledge management API."""
    return {
        "status": "healthy",
        "service": "knowledge-management-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
