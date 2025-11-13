"""
Knowledge Management API endpoints.

Provides CRUD operations for knowledge assets, chunks, and processing jobs.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..services.auth import get_user, get_admin_user, is_user_admin
from ..services.config import Settings
from ..services.db import DatabaseService
from ..rag.core.modular_rag_service import ModularRAGService

# Global RAG service instance (initialized on first use)
_rag_service_instance = None

def get_rag_service() -> ModularRAGService:
    """Get or create ModularRAGService instance."""
    global _rag_service_instance
    if _rag_service_instance is None:
        settings = Settings()
        db = DatabaseService(settings)
        _rag_service_instance = ModularRAGService(settings, db_service=db)
    return _rag_service_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# ========================================
# REQUEST/RESPONSE MODELS
# ========================================


class KnowledgeAssetCreate(BaseModel):
    """Request model for creating a knowledge asset."""

    source_file_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=512)
    document_type: str = Field(
        default="unknown",
        pattern="^(requirements|specification|knowledge|reference|unknown)$",
    )
    content_summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_options: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeAssetUpdate(BaseModel):
    """Request model for updating a knowledge asset."""

    title: Optional[str] = Field(None, min_length=1, max_length=512)
    document_type: Optional[str] = Field(
        None, pattern="^(requirements|specification|knowledge|reference|unknown)$"
    )
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
    chunks: Optional[List["KnowledgeChunkResponse"]] = None  # Include chunks when requested


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


class RAGQueryRequest(BaseModel):
    """Request model for RAG queries."""

    question: str = Field(
        ...,
        description="The question to ask the knowledge base",
        min_length=3,
        max_length=500,
    )
    project_id: Optional[str] = Field(None, description="Optional project scope for the query")
    max_chunks: int = Field(
        5, description="Maximum number of relevant chunks to retrieve", ge=1, le=20
    )
    similarity_threshold: float = Field(
        0.5, description="Minimum similarity score for relevance", ge=0.1, le=1.0
    )
    include_metadata: bool = Field(True, description="Include source metadata in response")
    response_style: str = Field("comprehensive", description="Response style")


class RAGSourceInfo(BaseModel):
    """Source information for RAG responses."""

    asset_id: str
    title: str
    document_type: str
    chunk_id: Optional[str] = None
    relevance_score: float


class RAGQueryResponse(BaseModel):
    """Response model for RAG queries."""

    success: bool
    response: Optional[str] = None
    confidence: Optional[str] = None
    sources: List[RAGSourceInfo] = []
    query: str
    chunks_found: int = 0
    response_style: Optional[str] = None
    generated_at: str
    model_used: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


class QuerySuggestionsResponse(BaseModel):
    """Response model for query suggestions."""

    suggestions: List[str]
    project_id: Optional[str] = None


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
        source_file_id=(
            str(asset_row["source_file_id"]) if asset_row.get("source_file_id") else None
        ),
        project_id=str(asset_row["project_id"]),
        title=asset_row["title"],
        document_type=asset_row["document_type"],
        content_summary=asset_row.get("content_summary"),
        metadata=asset_row.get("metadata", {}),
        created_at=(asset_row["created_at"].isoformat() if asset_row.get("created_at") else ""),
        updated_at=(asset_row["updated_at"].isoformat() if asset_row.get("updated_at") else ""),
        version=asset_row.get("version", "1.0.0"),
        status=asset_row.get("status", "active"),
        processing_stats=asset_row.get("processing_stats", {}),
        is_public=asset_row.get("is_public", False),
        made_public_at=(
            asset_row["made_public_at"].isoformat() if asset_row.get("made_public_at") else None
        ),
        made_public_by=asset_row.get("made_public_by"),
        chunks=asset_row.get("chunks"),  # Include chunks if present
    )


# ========================================
# KNOWLEDGE ASSET ENDPOINTS
# ========================================


@router.get("/admin/assets", response_model=KnowledgeListResponse)
async def list_all_knowledge_assets_admin(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query("active", description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    title_contains: Optional[str] = Query(None, description="Filter by title containing text"),
    traceability_status: Optional[str] = Query(None, description="Filter by traceability status (linked, orphaned, archived)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    db: DatabaseService = Depends(get_knowledge_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """
    List ALL knowledge assets across all users (Admin only).

    This endpoint allows admins to view and manage all knowledge assets
    in the system regardless of project ownership.
    """
    try:
        logger.info(f"Admin {admin_user.get('user_id')} listing all knowledge assets")

        # Build query with filters - no project restrictions for admin
        where_clauses = ["1=1"]  # Base condition
        params = []

        if project_id:
            where_clauses.append("ka.project_id = %s")
            params.append(project_id)

        if document_type:
            where_clauses.append("ka.document_type = %s")
            params.append(document_type)

        if status:
            where_clauses.append("ka.status = %s")
            params.append(status)

        if user_id:
            where_clauses.append("f.created_by = %s")
            params.append(user_id)

        if title_contains:
            where_clauses.append("ka.title ILIKE %s")
            params.append(f"%{title_contains}%")

        if traceability_status:
            where_clauses.append("ka.traceability_status = %s")
            params.append(traceability_status)

        where_sql = " AND ".join(where_clauses)

        # Execute query
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get total count
                count_sql = f"""
                    SELECT COUNT(*)
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    LEFT JOIN public.users u ON f.created_by = u.user_id::text
                    WHERE {where_sql}
                """
                cur.execute(count_sql, params)
                total_count = cur.fetchone()[0]

                # Get assets with pagination and user info
                assets_sql = f"""
                    SELECT ka.*, f.filename as source_filename, f.created_by as file_owner,
                           u.username as owner_username, u.display_name as owner_display_name
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    LEFT JOIN public.users u ON f.created_by = u.user_id::text
                    WHERE {where_sql}
                    ORDER BY ka.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(assets_sql, params + [limit, offset])
                rows = cur.fetchall()

                # Format response with owner information
                assets = []
                for row in rows:
                    asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                    asset_response = format_asset_response(asset_dict)

                    # Add owner information for admin view
                    asset_response.metadata = asset_response.metadata or {}
                    asset_response.metadata.update({
                        "owner_user_id": asset_dict.get("file_owner"),
                        "owner_username": asset_dict.get("owner_username"),
                        "owner_display_name": asset_dict.get("owner_display_name")
                    })

                    assets.append(asset_response)

                return KnowledgeListResponse(
                    assets=assets,
                    total_count=total_count,
                    message=f"Retrieved {len(assets)} knowledge assets (Admin view)",
                )
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to list all knowledge assets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge assets: {str(e)}")


@router.get("/assets", response_model=KnowledgeListResponse)
async def list_knowledge_assets(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query("active", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user),
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
        logger.info(
            f"Listing knowledge assets for user {user.get('user_id')} with filters: project_id={project_id}, type={document_type}, status={status}"
        )

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
                    where_clauses.append(
                        f"(ka.project_id IN ({placeholders}) OR ka.is_public = TRUE)"
                    )
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
                    message=f"Retrieved {len(assets)} knowledge assets",
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
    user: Dict = Depends(get_user),
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
        logger.info(
            f"Creating knowledge asset '{asset_data.title}' for project {project_id} by user {user.get('user_id')}"
        )

        # Verify user has access to project (admin users have access to all projects)
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")

        # Verify source file exists if provided
        if asset_data.source_file_id:
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM files WHERE id = %s AND project_id = %s",
                        (asset_data.source_file_id, project_id),
                    )
                    if not cur.fetchone():
                        raise HTTPException(
                            status_code=404,
                            detail="Source file not found or not accessible",
                        )
            finally:
                db._return(conn)

        # Create knowledge asset
        asset_id = str(uuid4())
        now = datetime.now(timezone.utc)

        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_assets
                    (id, source_file_id, project_id, title, document_type, content_summary, metadata, created_at, updated_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """,
                    (
                        asset_id,
                        asset_data.source_file_id,
                        project_id,
                        asset_data.title,
                        asset_data.document_type,
                        asset_data.content_summary,
                        json.dumps(asset_data.metadata),
                        now,
                        now,
                        "active",
                    ),
                )

                row = cur.fetchone()
                asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                conn.commit()

                logger.info(f"Created knowledge asset {asset_id} successfully")

                # EventCapture2: Capture knowledge asset creation event
                try:
                    from ..services.eventcapture2 import get_event_capture
                    event_capture = get_event_capture()
                    if event_capture:
                        await event_capture.capture_knowledge_asset_created(
                            asset_id=asset_id,
                            title=asset_data.title,
                            project_id=project_id,
                            user_id=user["user_id"],
                            username=user.get("username", "unknown"),
                            asset_details={
                                "document_type": asset_data.document_type,
                                "source_file_id": asset_data.source_file_id,
                                "content_summary": asset_data.content_summary,
                                "metadata": asset_data.metadata,
                                "status": "active"
                            }
                        )
                        print(f"🔥 DIRECT: EventCapture2 knowledge asset creation captured - {asset_data.title}")
                except Exception as e:
                    print(f"🔥 DIRECT: EventCapture2 knowledge asset creation failed: {e}")
                    logger.warning(f"EventCapture2 knowledge asset creation failed: {e}")

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
    user: Dict = Depends(get_user),
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
                cur.execute(
                    """
                    SELECT ka.*, f.filename as source_filename
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    JOIN project_members pm ON ka.project_id = pm.project_id
                    WHERE ka.id = %s AND pm.user_id = %s
                """,
                    (asset_id, user["user_id"]),
                )

                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail="Knowledge asset not found or not accessible",
                    )

                asset_dict = dict(zip([desc[0] for desc in cur.description], row))

                # Get chunks if requested
                if include_chunks:
                    cur.execute(
                        """
                        SELECT * FROM knowledge_chunks
                        WHERE asset_id = %s
                        ORDER BY sequence_number
                    """,
                        (asset_id,),
                    )

                    chunk_rows = cur.fetchall()
                    chunks = []
                    for chunk_row in chunk_rows:
                        chunk_dict = dict(zip([desc[0] for desc in cur.description], chunk_row))
                        chunks.append(
                            KnowledgeChunkResponse(
                                id=str(chunk_dict["id"]),
                                asset_id=str(chunk_dict["asset_id"]),
                                sequence_number=chunk_dict["sequence_number"],
                                chunk_type=chunk_dict["chunk_type"],
                                content=chunk_dict["content"],
                                token_count=chunk_dict.get("token_count", 0),
                                metadata=chunk_dict.get("metadata", {}),
                                embedding_model=chunk_dict.get("embedding_model"),
                                qdrant_point_id=(
                                    str(chunk_dict["qdrant_point_id"])
                                    if chunk_dict.get("qdrant_point_id")
                                    else None
                                ),
                                created_at=(
                                    chunk_dict["created_at"].isoformat()
                                    if chunk_dict.get("created_at")
                                    else ""
                                ),
                            )
                        )

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
    user: Dict = Depends(get_user),
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
                cur.execute(
                    """
                    SELECT ka.* FROM knowledge_assets ka
                    JOIN project_members pm ON ka.project_id = pm.project_id
                    WHERE ka.id = %s AND pm.user_id = %s
                """,
                    (asset_id, user["user_id"]),
                )

                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail="Knowledge asset not found or not accessible",
                    )

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
                    params.append(json.dumps(asset_data.metadata))

                if asset_data.status is not None:
                    updates.append("status = %s")
                    params.append(asset_data.status)

                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")

                updates.append("updated_at = %s")
                params.append(datetime.now(timezone.utc))
                params.append(asset_id)

                update_sql = (
                    f"UPDATE knowledge_assets SET {', '.join(updates)} WHERE id = %s RETURNING *"
                )
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
    user: Dict = Depends(get_user),
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
                    cur.execute(
                        "SELECT ka.* FROM knowledge_assets ka WHERE ka.id = %s",
                        (asset_id,),
                    )
                else:
                    # Regular users can only delete assets in their projects (not public assets they can view)
                    cur.execute(
                        """
                        SELECT ka.* FROM knowledge_assets ka
                        JOIN project_members pm ON ka.project_id = pm.project_id
                        WHERE ka.id = %s AND pm.user_id = %s
                    """,
                        (asset_id, user["user_id"]),
                    )

                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail="Knowledge asset not found or not accessible",
                    )

                # Delete asset (cascades to chunks, relationships, jobs)
                cur.execute("DELETE FROM knowledge_assets WHERE id = %s", (asset_id,))

                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Knowledge asset not found")

                conn.commit()
                logger.info(f"Deleted knowledge asset {asset_id} successfully")

                return {
                    "success": True,
                    "message": f"Knowledge asset {asset_id} deleted successfully",
                }

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
    user: Dict = Depends(get_user),
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
                    cur.execute(
                        "SELECT ka.* FROM knowledge_assets ka WHERE ka.id = %s",
                        (asset_id,),
                    )
                else:
                    # Regular users: their projects + public assets
                    cur.execute(
                        """
                        SELECT ka.* FROM knowledge_assets ka
                        LEFT JOIN project_members pm ON ka.project_id = pm.project_id AND pm.user_id = %s
                        WHERE ka.id = %s AND (pm.user_id IS NOT NULL OR ka.is_public = TRUE)
                    """,
                        (user["user_id"], asset_id),
                    )

                asset_row = cur.fetchone()
                if not asset_row:
                    raise HTTPException(
                        status_code=404,
                        detail="Knowledge asset not found or not accessible",
                    )

                asset_dict = dict(zip([desc[0] for desc in cur.description], asset_row))

                # Get all chunks for this asset
                cur.execute(
                    """
                    SELECT * FROM knowledge_chunks
                    WHERE asset_id = %s
                    ORDER BY sequence_number
                """,
                    (asset_id,),
                )

                chunk_rows = cur.fetchall()
                chunks = []
                total_tokens = 0

                for chunk_row in chunk_rows:
                    chunk_dict = dict(zip([desc[0] for desc in cur.description], chunk_row))
                    chunks.append(
                        KnowledgeChunkResponse(
                            id=str(chunk_dict["id"]),
                            asset_id=str(chunk_dict["asset_id"]),
                            sequence_number=chunk_dict["sequence_number"],
                            chunk_type=chunk_dict["chunk_type"],
                            content=chunk_dict["content"],
                            token_count=chunk_dict.get("token_count", 0),
                            metadata=chunk_dict.get("metadata", {}),
                            embedding_model=chunk_dict.get("embedding_model"),
                            qdrant_point_id=(
                                str(chunk_dict["qdrant_point_id"])
                                if chunk_dict.get("qdrant_point_id")
                                else None
                            ),
                            created_at=(
                                chunk_dict["created_at"].isoformat()
                                if chunk_dict.get("created_at")
                                else ""
                            ),
                        )
                    )
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
                    total_tokens=total_tokens,
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
    user: Dict = Depends(get_admin_user),  # Admin only
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
        logger.info(
            f"Setting public status for asset {asset_id} to {public_request.is_public} by admin {user.get('user_id')}"
        )

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
                    cur.execute(
                        """
                        UPDATE knowledge_assets
                        SET is_public = %s, made_public_at = %s, made_public_by = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING *
                    """,
                        (True, now, user["user_id"], now, asset_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE knowledge_assets
                        SET is_public = %s, made_public_at = NULL, made_public_by = NULL, updated_at = %s
                        WHERE id = %s
                        RETURNING *
                    """,
                        (False, now, asset_id),
                    )

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
    user: Dict = Depends(get_admin_user),  # Admin only for force delete
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

                return {
                    "success": True,
                    "message": f"Knowledge asset '{asset_title}' permanently deleted",
                }

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force delete asset {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete asset: {str(e)}")


@router.delete("/admin/cleanup-unknown")
async def cleanup_unknown_assets(
    dry_run: bool = Query(True, description="If true, only count assets to delete without actually deleting them"),
    db: DatabaseService = Depends(get_knowledge_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """
    Clean up knowledge assets with unknown or problematic titles (Admin only).

    This endpoint identifies and optionally deletes assets with:
    - title = "unknown"
    - title = ""
    - title is NULL
    - source_file_id is NULL (orphaned knowledge assets)
    - document_type = "unknown" and title looks auto-generated

    Args:
        dry_run: If true, only returns count without deleting

    Returns:
        Summary of cleanup operation
    """
    try:
        logger.info(f"Admin {admin_user.get('user_id')} starting unknown assets cleanup (dry_run={dry_run})")

        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Find problematic assets
                cleanup_sql = """
                    SELECT ka.id, ka.title, ka.document_type, ka.project_id,
                           f.filename as source_filename, f.created_by as file_owner,
                           u.username as owner_username
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    LEFT JOIN public.users u ON f.created_by = u.user_id::text
                    WHERE
                        ka.title = 'unknown' OR
                        ka.title = '' OR
                        ka.title IS NULL OR
                        ka.source_file_id IS NULL OR
                        (ka.document_type = 'unknown' AND (
                            ka.title LIKE 'Asset %' OR
                            ka.title LIKE 'Document %' OR
                            ka.title LIKE 'File %'
                        ))
                    ORDER BY ka.created_at DESC
                """

                cur.execute(cleanup_sql)
                problematic_assets = cur.fetchall()

                asset_details = []
                for row in problematic_assets:
                    asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                    asset_details.append({
                        "id": str(asset_dict["id"]),
                        "title": asset_dict["title"] or "(null)",
                        "document_type": asset_dict["document_type"],
                        "project_id": str(asset_dict["project_id"]) if asset_dict["project_id"] else None,
                        "source_filename": asset_dict["source_filename"],
                        "owner_username": asset_dict["owner_username"]
                    })

                deleted_count = 0
                if not dry_run and problematic_assets:
                    # Actually delete the assets
                    asset_ids = [str(row[0]) for row in problematic_assets]
                    placeholders = ','.join(['%s'] * len(asset_ids))
                    delete_sql = f"DELETE FROM knowledge_assets WHERE id IN ({placeholders})"

                    cur.execute(delete_sql, asset_ids)
                    deleted_count = cur.rowcount
                    conn.commit()

                    logger.info(f"Deleted {deleted_count} problematic knowledge assets")

                return {
                    "success": True,
                    "dry_run": dry_run,
                    "found_count": len(problematic_assets),
                    "deleted_count": deleted_count,
                    "message": f"{'Found' if dry_run else 'Deleted'} {len(problematic_assets)} problematic knowledge assets",
                    "assets": asset_details if dry_run else None
                }

        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to cleanup unknown assets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# ========================================
# PROCESSING JOBS ENDPOINTS
# ========================================


@router.get("/jobs", response_model=List[ProcessingJobResponse])
async def list_processing_jobs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user),
):
    """List processing jobs with optional filtering."""
    try:
        logger.info(f"Listing processing jobs for user {user.get('user_id')}")

        # Build query with filters
        where_clauses = ["1=1"]
        params = []

        # Project filter with user access check
        if project_id:
            if not user.get("is_admin", False) and not db.is_user_member(
                project_id=project_id, user_id=user["user_id"]
            ):
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
                    jobs.append(
                        ProcessingJobResponse(
                            id=str(job_dict["id"]),
                            asset_id=str(job_dict["asset_id"]),
                            job_type=job_dict["job_type"],
                            status=job_dict["status"],
                            progress_percent=job_dict.get("progress_percent", 0),
                            error_message=job_dict.get("error_message"),
                            started_at=(
                                job_dict["started_at"].isoformat()
                                if job_dict.get("started_at")
                                else None
                            ),
                            completed_at=(
                                job_dict["completed_at"].isoformat()
                                if job_dict.get("completed_at")
                                else None
                            ),
                            created_at=(
                                job_dict["created_at"].isoformat()
                                if job_dict.get("created_at")
                                else ""
                            ),
                            metadata=job_dict.get("metadata", {}),
                        )
                    )

                database_jobs = jobs

        finally:
            db._return(conn)

        # Get active Camunda workflows for reprocessing
        camunda_jobs = []
        try:
            import httpx
            CAMUNDA_BASE_URL = "http://localhost:8080"
            CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

            async with httpx.AsyncClient(timeout=10) as client:
                # Query active process instances for knowledge processing workflows
                response = await client.get(
                    f"{CAMUNDA_REST_API}/process-instance",
                    params={
                        "processDefinitionKey": "automatic_knowledge_processing",
                        "active": "true"
                    }
                )

                if response.status_code == 200:
                    active_processes = response.json()

                    for process in active_processes:
                        try:
                            # Get process variables to extract file info
                            vars_response = await client.get(
                                f"{CAMUNDA_REST_API}/process-instance/{process['id']}/variables"
                            )

                            if vars_response.status_code == 200:
                                variables = vars_response.json()
                                file_id = variables.get("file_id", {}).get("value", "unknown")
                                filename = variables.get("filename", {}).get("value", "unknown")
                                doc_type = variables.get("document_type", {}).get("value", "unknown")

                                # Create a synthetic job response for the Camunda workflow
                                camunda_job = ProcessingJobResponse(
                                    id=f"camunda-{process['id']}",
                                    asset_id=f"processing-{file_id}",
                                    job_type="reprocessing",
                                    status="running",
                                    progress_percent=50,  # Assume 50% for active workflows
                                    created_at=process.get("startTime", ""),
                                    started_at=process.get("startTime", ""),
                                    completed_at=None,
                                    error_message=None,
                                    metadata={
                                        "file_id": file_id,
                                        "filename": filename,
                                        "document_type": doc_type,
                                        "process_instance_id": process["id"],
                                        "source": "camunda"
                                    }
                                )
                                camunda_jobs.append(camunda_job)
                        except Exception as e:
                            logger.warning(f"Failed to process Camunda workflow {process['id']}: {e}")
                            continue

        except Exception as e:
            logger.warning(f"Failed to query Camunda processes: {e}")
            # Continue without Camunda jobs if the query fails

        # Combine database jobs and Camunda jobs
        all_jobs = database_jobs + camunda_jobs

        # Sort by created_at and limit
        all_jobs.sort(key=lambda x: x.created_at or "", reverse=True)
        return all_jobs[:limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list processing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list processing jobs: {str(e)}")


# ========================================
# SEARCH ENDPOINTS
# ========================================


class KnowledgeSearchRequest(BaseModel):
    """Request model for knowledge search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    project_id: Optional[str] = Field(None, description="Filter by project ID")
    document_types: Optional[List[str]] = Field(None, description="Filter by document types")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    include_metadata: bool = Field(True, description="Include chunk metadata in results")


class KnowledgeSearchResult(BaseModel):
    """Individual search result."""

    chunk_id: str
    asset_id: str
    score: float
    content: str
    chunk_metadata: Dict[str, Any]
    asset_metadata: Dict[str, Any]


class KnowledgeSearchResponse(BaseModel):
    """Response model for knowledge search."""

    results: List[KnowledgeSearchResult]
    query: str
    total_found: int
    search_time_ms: float
    message: str = "Search completed successfully"


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    search_request: KnowledgeSearchRequest,
    db: DatabaseService = Depends(get_knowledge_service),
    user: Dict = Depends(get_user),
):
    """
    Search knowledge base using semantic similarity.

    Args:
        search_request: Search parameters and filters

    Returns:
        Ranked search results with similarity scores
    """
    import time

    start_time = time.time()

    try:
        logger.info(f"Searching knowledge for user {user.get('user_id')}: '{search_request.query}'")

        # Get embedding service and generate query embedding
        from ..services.embedding_service import get_embedding_service
        from ..services.qdrant_service import get_qdrant_service

        embedding_service = get_embedding_service()
        qdrant_service = get_qdrant_service()

        # Generate query embedding
        query_embedding = embedding_service.generate_embeddings([search_request.query])
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        query_vector = query_embedding[0]

        # Build search filters
        search_filters = {}

        # Project access control
        if is_user_admin(user):
            # Admin can search all projects
            if search_request.project_id:
                search_filters["project_id"] = search_request.project_id
        else:
            # Regular users can only search their projects + public assets
            user_projects = db.list_projects_for_user(user_id=user["user_id"], active=True)
            accessible_project_ids = [str(p["project_id"]) for p in user_projects]

            if search_request.project_id:
                if search_request.project_id in accessible_project_ids:
                    search_filters["project_id"] = search_request.project_id
                else:
                    # User requested a project they don't have access to
                    raise HTTPException(
                        status_code=403,
                        detail="Not authorized to search in this project",
                    )
            else:
                # Search across all accessible projects
                search_filters["project_ids"] = accessible_project_ids

        # Document type filter
        if search_request.document_types:
            search_filters["document_types"] = search_request.document_types

        # Perform vector search in Qdrant
        qdrant_results = qdrant_service.search_vectors(
            collection_name="knowledge_chunks",
            query_vector=query_vector,
            limit=search_request.limit,
            score_threshold=search_request.min_score,
            metadata_filter=search_filters,
        )

        # Get detailed information for results from database
        results = []
        chunk_ids = [
            result["payload"]["chunk_id"]
            for result in qdrant_results
            if result.get("payload", {}).get("chunk_id")
        ]

        if chunk_ids:
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    # Get chunk and asset details
                    placeholders = ",".join(["%s"] * len(chunk_ids))
                    cur.execute(
                        f"""
                        SELECT
                            kc.id as chunk_id,
                            kc.asset_id,
                            kc.content,
                            kc.metadata as chunk_metadata,
                            ka.title as asset_title,
                            ka.document_type,
                            ka.project_id,
                            ka.metadata as asset_metadata
                        FROM knowledge_chunks kc
                        JOIN knowledge_assets ka ON kc.asset_id = ka.id
                        WHERE kc.id IN ({placeholders})
                    """,
                        chunk_ids,
                    )

                    chunk_details = {}
                    for row in cur.fetchall():
                        chunk_dict = dict(zip([desc[0] for desc in cur.description], row))
                        chunk_details[str(chunk_dict["chunk_id"])] = chunk_dict

                    # Build results with scores
                    for qdrant_result in qdrant_results:
                        chunk_id = qdrant_result["payload"].get("chunk_id")
                        if chunk_id and chunk_id in chunk_details:
                            chunk_info = chunk_details[chunk_id]

                            results.append(
                                KnowledgeSearchResult(
                                    chunk_id=chunk_id,
                                    asset_id=str(chunk_info["asset_id"]),
                                    score=qdrant_result["score"],
                                    content=chunk_info["content"],
                                    chunk_metadata=chunk_info.get("chunk_metadata", {}),
                                    asset_metadata={
                                        "title": chunk_info["asset_title"],
                                        "document_type": chunk_info["document_type"],
                                        "project_id": str(chunk_info["project_id"]),
                                        **chunk_info.get("asset_metadata", {}),
                                    },
                                )
                            )

            finally:
                db._return(conn)

        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        logger.info(f"Search completed: {len(results)} results in {search_time:.2f}ms")

        return KnowledgeSearchResponse(
            results=results,
            query=search_request.query,
            total_found=len(results),
            search_time_ms=round(search_time, 2),
            message=f"Found {len(results)} results in {search_time:.2f}ms",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Knowledge search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ========================================
# HEALTH CHECK
# ========================================

# ========================================
# RAG (RETRIEVAL AUGMENTED GENERATION) ENDPOINTS
# ========================================


@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge_base(request: RAGQueryRequest, user: Dict = Depends(get_user)):
    """
    Query the knowledge base using RAG (Retrieval Augmented Generation).

    This endpoint combines vector similarity search with LLM generation to provide
    contextual answers based on the user's knowledge assets.

    Args:
        request: RAG query request with question and parameters

    Returns:
        Generated response with sources and metadata
    """
    try:
        logger.info(f"Processing RAG query from user {user.get('user_id')}: '{request.question}'")

        # Get RAG service
        rag_service = get_rag_service()

        # Execute RAG query (using legacy method for backward compatibility)
        result = await rag_service.query_knowledge_base_legacy(
            question=request.question,
            project_id=request.project_id,
            user_id=user["user_id"],
            max_chunks=request.max_chunks,
            similarity_threshold=request.similarity_threshold,
            include_metadata=request.include_metadata,
            response_style=request.response_style,
        )

        # Convert sources to proper response format
        if result.get("sources"):
            formatted_sources = []
            for source in result["sources"]:
                formatted_sources.append(
                    RAGSourceInfo(
                        asset_id=source["asset_id"],
                        title=source["title"],
                        document_type=source["document_type"],
                        chunk_id=source.get("chunk_id"),
                        relevance_score=source["relevance_score"],
                    )
                )
            result["sources"] = formatted_sources

        return RAGQueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@router.post("/query-workflow", response_model=RAGQueryResponse)
async def query_knowledge_base_workflow(request: RAGQueryRequest, user: Dict = Depends(get_user)):
    """
    Query the knowledge base using RAG workflow (rag_query_process).

    This endpoint uses the Camunda workflow engine to process RAG queries through
    the complete pipeline: Query Processing → Context Retrieval → LLM Generation → Response.

    Args:
        request: RAG query request with question and parameters

    Returns:
        Generated response with sources and metadata
    """
    import httpx
    import time

    try:
        logger.info(f"Processing RAG workflow query from user {user.get('user_id')}: '{request.question}'")

        # Get settings
        from ..services.config import Settings
        settings = Settings()

        # Prepare workflow request
        from ..api.workflows import RAGQueryRequest as WorkflowRAGRequest

        workflow_request = WorkflowRAGRequest(
            query=request.question,
            max_results=request.max_chunks,
            similarity_threshold=request.similarity_threshold,
            user_context={
                "project_id": request.project_id,
                "response_style": request.response_style,
                "include_metadata": request.include_metadata,
                "user_id": user["user_id"]
            }
        )

        # Start the workflow
        from ..api.workflows import start_rag_query
        workflow_response = await start_rag_query(workflow_request, authorization="Bearer dummy")

        if not workflow_response.success:
            raise HTTPException(status_code=500, detail="Failed to start RAG workflow")

        process_instance_id = workflow_response.process_instance_id

        # Poll for completion with timeout
        max_wait_time = 120  # 120 seconds timeout
        poll_interval = 1   # Poll every second
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                # Get workflow status
                from ..api.workflows import get_rag_query_status
                status_response = await get_rag_query_status(process_instance_id, authorization="Bearer dummy")

                if status_response.get("status") == "completed":
                    # Extract final response
                    final_response = status_response.get("final_response")
                    if final_response:
                        # Parse the workflow response
                        if isinstance(final_response, str):
                            try:
                                final_response = json.loads(final_response)
                            except json.JSONDecodeError:
                                # If it's not JSON, treat as plain text response
                                final_response = {
                                    "success": True,
                                    "response": final_response,
                                    "confidence": "medium",
                                    "sources": [],
                                    "query": request.question,
                                    "chunks_found": 0,
                                    "response_style": request.response_style,
                                    "generated_at": datetime.utcnow().isoformat(),
                                    "model_used": "workflow",
                                    "provider": "rag_query_process"
                                }

                        # Extract metadata from workflow variables (properly extracted by workflows.py)
                        workflow_variables = status_response.get("variables", {})
                        sources = []
                        chunks_found = 0
                        confidence = "medium"  # Default

                        # Get confidence from properly extracted workflow variables
                        if "llm_confidence" in workflow_variables:
                            confidence = workflow_variables["llm_confidence"]
                            print(f"API: Extracted llm_confidence = {confidence}")
                        elif "confidence" in workflow_variables:
                            confidence = workflow_variables["confidence"]
                            print(f"API: Extracted confidence = {confidence}")
                        else:
                            print("API: confidence/llm_confidence not found in workflow_variables")

                        # Get chunks_found from properly extracted workflow variables
                        if "chunks_found" in workflow_variables:
                            chunks_found = workflow_variables["chunks_found"]
                            print(f"API: Extracted chunks_found = {chunks_found}")
                        else:
                            print("API: chunks_found not found in workflow_variables")

                        # Get sources from properly extracted workflow variables
                        if "sources" in workflow_variables:
                            sources_data = workflow_variables["sources"]
                            if isinstance(sources_data, list):
                                sources = sources_data

                        # Fallback: extract from response text if workflow variables don't work
                        if not chunks_found or not sources:
                            response_text = None
                            if isinstance(final_response, dict):
                                response_text = final_response.get("response") or final_response.get("final_response")
                            elif isinstance(final_response, str):
                                response_text = final_response

                            if response_text:
                                # Count contexts as fallback
                                if not chunks_found:
                                    chunks_found = response_text.count('[Context ')
                                    print(f"API FALLBACK: Using text parsing for chunks_found={chunks_found}")

                                # Extract sources from Sources section as fallback
                                if not sources and 'Sources:' in response_text:
                                    import re
                                    source_matches = re.findall(r'\[(\d+)\] ([^\n]+)', response_text)
                                    for i, (num, source_name) in enumerate(source_matches):
                                        sources.append({
                                            "asset_id": f"workflow_source_{i}",
                                            "title": source_name.strip(),
                                            "document_type": "document",
                                            "chunk_id": None,
                                            "relevance_score": 0.8,
                                        })
                                    print(f"API FALLBACK: Using text parsing for {len(sources)} sources")

                        # Ensure required fields
                        if not final_response.get("success"):
                            final_response["success"] = True
                        if not final_response.get("query"):
                            final_response["query"] = request.question
                        if not final_response.get("generated_at"):
                            final_response["generated_at"] = datetime.utcnow().isoformat()
                        # Set the extracted metadata
                        final_response["chunks_found"] = chunks_found
                        final_response["sources"] = sources

                        # Only set confidence if we actually got it from LLM, otherwise null
                        if confidence and confidence != "medium":  # medium is our default fallback
                            final_response["confidence"] = confidence
                        else:
                            final_response["confidence"] = None  # Unknown confidence
                        if not final_response.get("model_used"):
                            final_response["model_used"] = "workflow"
                        if not final_response.get("provider"):
                            final_response["provider"] = "rag_query_process"

                        return RAGQueryResponse(**final_response)
                    else:
                        raise HTTPException(status_code=500, detail="Workflow completed but no response generated")

                elif status_response.get("status") == "failed":
                    error_msg = status_response.get("error", "Workflow failed")
                    raise HTTPException(status_code=500, detail=f"RAG workflow failed: {error_msg}")

                # Still running, wait and poll again
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Error polling workflow status: {str(e)}")
                await asyncio.sleep(poll_interval)

        # Timeout reached
        raise HTTPException(status_code=408, detail="RAG workflow timed out")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG workflow query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process workflow query: {str(e)}")


@router.get("/query/suggestions", response_model=QuerySuggestionsResponse)
async def get_query_suggestions(
    project_id: Optional[str] = Query(None, description="Optional project ID to scope suggestions"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of suggestions"),
    user: Dict = Depends(get_user),
):
    """
    Get suggested queries based on the available knowledge assets.

    Args:
        project_id: Optional project scope
        limit: Maximum number of suggestions to return

    Returns:
        List of suggested queries
    """
    try:
        logger.info(f"Getting query suggestions for user {user.get('user_id')}")

        # Get RAG service
        rag_service = get_rag_service()

        # Get suggestions (using legacy method for backward compatibility)
        suggestions = await rag_service.get_query_suggestions_legacy(
            project_id=project_id, user_id=user["user_id"], limit=limit
        )

        return QuerySuggestionsResponse(suggestions=suggestions, project_id=project_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/search/semantic")
async def semantic_search_chunks(
    query: str = Body(..., description="Search query text"),
    project_id: Optional[str] = Body(None, description="Optional project scope"),
    limit: int = Body(10, ge=1, le=50, description="Maximum results to return"),
    score_threshold: float = Body(0.7, ge=0.0, le=1.0, description="Minimum similarity score"),
    user: Dict = Depends(get_user),
):
    """
    Perform semantic search on knowledge chunks without LLM generation.

    This endpoint provides direct access to vector similarity search results
    for users who want to see raw search results.

    Args:
        query: The search query text
        project_id: Optional project scope
        limit: Maximum number of results
        score_threshold: Minimum similarity score

    Returns:
        List of matching knowledge chunks with scores
    """
    try:
        logger.info(f"Processing semantic search for user {user.get('user_id')}: '{query}'")

        # Get RAG service for reusing chunk retrieval logic
        rag_service = get_rag_service()

        # Retrieve relevant chunks
        chunks = await rag_service._retrieve_relevant_chunks(
            question=query,
            project_id=project_id,
            user_id=user["user_id"],
            max_chunks=limit,
            similarity_threshold=score_threshold,
        )

        # Format results
        results = []
        for chunk in chunks:
            chunk_data = chunk.get("payload", {})
            results.append(
                {
                    "chunk_id": chunk_data.get("chunk_id"),
                    "content": chunk_data.get("text", ""),
                    "score": chunk.get("score", 0.0),
                    "asset_id": chunk_data.get("asset_id"),
                    "asset_title": chunk_data.get("source_asset", "Unknown"),
                    "document_type": chunk_data.get("document_type", "document"),
                    "project_id": chunk_data.get("project_id"),
                }
            )

        return {
            "success": True,
            "query": query,
            "results": results,
            "total_found": len(results),
            "score_threshold": score_threshold,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def knowledge_health():
    """Health check endpoint for knowledge management API."""
    return {
        "status": "healthy",
        "service": "knowledge-management-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
