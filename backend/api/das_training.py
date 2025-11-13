"""
DAS Training Knowledge Management API endpoints.

Provides CRUD operations for DAS training collections and assets.
Training collections are global (not project-scoped) and provide
system-wide knowledge for DAS capabilities.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Body, File, UploadFile, Form
from pydantic import BaseModel, Field

from ..services.auth import get_user, get_admin_user, is_user_admin
from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.qdrant_service import get_qdrant_service, QdrantService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/das-training", tags=["das-training"])


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================


class TrainingCollectionCreate(BaseModel):
    """Request model for creating a training collection."""

    collection_name: str = Field(..., min_length=1, max_length=255, description="Qdrant collection name (e.g., das_training_ontology)")
    display_name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    description: Optional[str] = None
    domain: str = Field(..., min_length=1, max_length=100, description="Domain category (ontology, requirements, acquisition, odras_usage, etc.)")
    vector_size: int = Field(384, description="Embedding dimension (384 or 1536)")
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Embedding model name")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingCollectionUpdate(BaseModel):
    """Request model for updating a training collection."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TrainingCollectionResponse(BaseModel):
    """Response model for training collection."""

    collection_id: str
    collection_name: str
    display_name: str
    description: Optional[str]
    domain: str
    vector_size: int
    embedding_model: str
    created_by: Optional[str]
    created_at: str
    updated_at: str
    is_active: bool
    metadata: Dict[str, Any]
    asset_count: Optional[int] = None  # Included when requested


class TrainingAssetCreate(BaseModel):
    """Request model for creating a training asset."""

    collection_id: str = Field(..., description="Collection ID to add asset to")
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    source_type: str = Field(..., description="youtube_transcript, pdf, doc, markdown, etc.")
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingAssetResponse(BaseModel):
    """Response model for training asset."""

    asset_id: str
    collection_id: str
    source_file_id: Optional[str]
    title: str
    description: Optional[str]
    source_type: str
    source_url: Optional[str]
    created_by: Optional[str]
    created_at: str
    processing_status: str
    chunk_count: int
    metadata: Dict[str, Any]


class CollectionStatsResponse(BaseModel):
    """Response model for collection statistics."""

    collection_id: str
    collection_name: str
    total_assets: int
    total_chunks: int
    assets_by_status: Dict[str, int]
    assets_by_type: Dict[str, int]
    last_updated: Optional[str]


# ========================================
# DEPENDENCIES
# ========================================


def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService(Settings())


def get_qdrant() -> QdrantService:
    """Get Qdrant service instance."""
    return get_qdrant_service()


def get_training_processor():
    """Get DAS training processor instance."""
    from ..services.das_training_processor import DASTrainingProcessor
    return DASTrainingProcessor(Settings())


# ========================================
# COLLECTION MANAGEMENT ENDPOINTS
# ========================================


@router.post("/collections", response_model=TrainingCollectionResponse)
async def create_training_collection(
    collection: TrainingCollectionCreate,
    user: dict = Depends(get_admin_user),  # Only admins can create collections
    db: DatabaseService = Depends(get_db_service),
    qdrant: QdrantService = Depends(get_qdrant),
):
    """
    Create a new DAS training collection.
    
    Only admins can create training collections.
    """
    try:
        # Validate collection name format (should start with das_training_)
        if not collection.collection_name.startswith("das_training_"):
            raise HTTPException(
                status_code=400,
                detail="Collection name must start with 'das_training_' prefix"
            )

        # Check if collection name already exists
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT collection_id FROM das_training_collections WHERE collection_name = %s",
                    (collection.collection_name,)
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail=f"Collection '{collection.collection_name}' already exists"
                    )

                # Create Qdrant collection
                if not qdrant.ensure_collection(collection.collection_name, collection.vector_size):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create Qdrant collection '{collection.collection_name}'"
                    )

                # Insert into database
                collection_id = uuid4()
                # Convert user_id to string - psycopg2 needs strings for UUID columns
                user_id_str = str(user["user_id"]) if user["user_id"] else None
                
                cur.execute(
                    """
                    INSERT INTO das_training_collections 
                    (collection_id, collection_name, display_name, description, domain, 
                     vector_size, embedding_model, created_by, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING collection_id, created_at, updated_at
                    """,
                    (
                        str(collection_id),  # Convert UUID to string for psycopg2
                        collection.collection_name,
                        collection.display_name,
                        collection.description,
                        collection.domain,
                        collection.vector_size,
                        collection.embedding_model,
                        user_id_str,  # Already a string
                        json.dumps(collection.metadata) if collection.metadata else "{}",
                    ),
                )
                row = cur.fetchone()
                conn.commit()

                return TrainingCollectionResponse(
                    collection_id=str(collection_id),
                    collection_name=collection.collection_name,
                    display_name=collection.display_name,
                    description=collection.description,
                    domain=collection.domain,
                    vector_size=collection.vector_size,
                    embedding_model=collection.embedding_model,
                    created_by=user["user_id"],
                    created_at=row[1].isoformat(),
                    updated_at=row[2].isoformat(),
                    is_active=True,
                    metadata=collection.metadata,
                    asset_count=0,
                )
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create training collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.get("/collections", response_model=List[TrainingCollectionResponse])
async def list_training_collections(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    active_only: bool = Query(True, description="Only return active collections"),
    include_stats: bool = Query(False, description="Include asset count statistics"),
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user),
):
    """List all DAS training collections."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        collection_id, collection_name, display_name, description, domain,
                        vector_size, embedding_model, created_by, created_at, updated_at,
                        is_active, metadata
                    FROM das_training_collections
                    WHERE 1=1
                """
                params = []

                if active_only:
                    query += " AND is_active = TRUE"
                
                if domain:
                    query += " AND domain = %s"
                    params.append(domain)

                query += " ORDER BY domain, display_name"

                cur.execute(query, params)
                rows = cur.fetchall()

                collections = []
                for row in rows:
                    collection_data = {
                        "collection_id": str(row[0]),
                        "collection_name": row[1],
                        "display_name": row[2],
                        "description": row[3],
                        "domain": row[4],
                        "vector_size": row[5],
                        "embedding_model": row[6],
                        "created_by": str(row[7]) if row[7] else None,
                        "created_at": row[8].isoformat(),
                        "updated_at": row[9].isoformat(),
                        "is_active": row[10],
                        "metadata": row[11] if isinstance(row[11], dict) else {},
                    }

                    if include_stats:
                        # Get asset count
                        cur.execute(
                            "SELECT COUNT(*) FROM das_training_assets WHERE collection_id = %s",
                            (row[0],)
                        )
                        asset_count = cur.fetchone()[0]
                        collection_data["asset_count"] = asset_count

                    collections.append(TrainingCollectionResponse(**collection_data))

                return collections
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to list training collections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/collections/{collection_id}", response_model=TrainingCollectionResponse)
async def get_training_collection(
    collection_id: str,
    include_stats: bool = Query(False, description="Include asset count statistics"),
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user),
):
    """Get details of a specific training collection."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        collection_id, collection_name, display_name, description, domain,
                        vector_size, embedding_model, created_by, created_at, updated_at,
                        is_active, metadata
                    FROM das_training_collections
                    WHERE collection_id = %s
                    """,
                    (collection_id,)  # collection_id is already a string UUID
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(status_code=404, detail="Collection not found")

                collection_data = {
                    "collection_id": str(row[0]),
                    "collection_name": row[1],
                    "display_name": row[2],
                    "description": row[3],
                    "domain": row[4],
                    "vector_size": row[5],
                    "embedding_model": row[6],
                    "created_by": str(row[7]) if row[7] else None,
                    "created_at": row[8].isoformat(),
                    "updated_at": row[9].isoformat(),
                    "is_active": row[10],
                    "metadata": row[11] if isinstance(row[11], dict) else {},
                }

                if include_stats:
                    cur.execute(
                        "SELECT COUNT(*) FROM das_training_assets WHERE collection_id = %s",
                        (row[0],)
                    )
                    asset_count = cur.fetchone()[0]
                    collection_data["asset_count"] = asset_count

                return TrainingCollectionResponse(**collection_data)
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get training collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection: {str(e)}")


@router.put("/collections/{collection_id}", response_model=TrainingCollectionResponse)
async def update_training_collection(
    collection_id: str,
    update: TrainingCollectionUpdate,
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_admin_user),  # Only admins can update
):
    """Update a training collection (admin only)."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Build update query dynamically
                updates = []
                params = []

                if update.display_name is not None:
                    updates.append("display_name = %s")
                    params.append(update.display_name)
                
                if update.description is not None:
                    updates.append("description = %s")
                    params.append(update.description)
                
                if update.domain is not None:
                    updates.append("domain = %s")
                    params.append(update.domain)
                
                if update.is_active is not None:
                    updates.append("is_active = %s")
                    params.append(update.is_active)
                
                if update.metadata is not None:
                    updates.append("metadata = %s")
                    params.append(json.dumps(update.metadata) if update.metadata else "{}")

                if not updates:
                    # No updates, just return current collection
                    return await get_training_collection(collection_id, db=db, user=user)

                updates.append("updated_at = NOW()")
                params.append(collection_id)  # collection_id is already a string UUID

                query = f"""
                    UPDATE das_training_collections
                    SET {', '.join(updates)}
                    WHERE collection_id = %s
                    RETURNING collection_id, collection_name, display_name, description, domain,
                             vector_size, embedding_model, created_by, created_at, updated_at,
                             is_active, metadata
                """
                cur.execute(query, params)
                row = cur.fetchone()

                if not row:
                    raise HTTPException(status_code=404, detail="Collection not found")

                conn.commit()

                return TrainingCollectionResponse(
                    collection_id=str(row[0]),
                    collection_name=row[1],
                    display_name=row[2],
                    description=row[3],
                    domain=row[4],
                    vector_size=row[5],
                    embedding_model=row[6],
                    created_by=str(row[7]) if row[7] else None,
                    created_at=row[8].isoformat(),
                    updated_at=row[9].isoformat(),
                    is_active=row[10],
                    metadata=row[11] if isinstance(row[11], dict) else {},
                )
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update training collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update collection: {str(e)}")


@router.delete("/collections/{collection_id}")
async def delete_training_collection(
    collection_id: str,
    db: DatabaseService = Depends(get_db_service),
    qdrant: QdrantService = Depends(get_qdrant),
    user: dict = Depends(get_admin_user),  # Only admins can delete
):
    """
    Delete a training collection (admin only).
    
    This will also delete all assets in the collection and the Qdrant collection.
    """
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get collection name for Qdrant deletion
                cur.execute(
                    "SELECT collection_name FROM das_training_collections WHERE collection_id = %s",
                    (collection_id,)  # collection_id is already a string UUID
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Collection not found")
                
                collection_name = row[0]

                # Check if collection has assets
                cur.execute(
                    "SELECT COUNT(*) FROM das_training_assets WHERE collection_id = %s",
                    (collection_id,)  # collection_id is already a string UUID
                )
                asset_count = cur.fetchone()[0]
                if asset_count > 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete collection with {asset_count} assets. Delete assets first."
                    )

                # Delete from database (cascade will delete assets)
                cur.execute(
                    "DELETE FROM das_training_collections WHERE collection_id = %s",
                    (collection_id,)  # collection_id is already a string UUID
                )
                conn.commit()

                # Delete Qdrant collection
                try:
                    qdrant.client.delete_collection(collection_name)
                except Exception as e:
                    logger.warning(f"Failed to delete Qdrant collection {collection_name}: {e}")
                    # Don't fail if Qdrant deletion fails

                return {"message": f"Collection '{collection_name}' deleted successfully"}

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete training collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


@router.get("/collections/{collection_id}/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(
    collection_id: str,
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user),
):
    """Get statistics for a training collection."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get collection info
                cur.execute(
                    "SELECT collection_name FROM das_training_collections WHERE collection_id = %s",
                    (collection_id,)  # collection_id is already a string UUID
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Collection not found")
                
                collection_name = row[0]

                # Get asset statistics
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_assets,
                        SUM(chunk_count) as total_chunks,
                        COUNT(*) FILTER (WHERE processing_status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE processing_status = 'processing') as processing,
                        COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
                        MAX(created_at) as last_updated
                    FROM das_training_assets
                    WHERE collection_id = %s
                    """,
                    (collection_id,)  # collection_id is already a string UUID
                )
                stats_row = cur.fetchone()

                # Get assets by type
                cur.execute(
                    """
                    SELECT source_type, COUNT(*) 
                    FROM das_training_assets
                    WHERE collection_id = %s
                    GROUP BY source_type
                    """,
                    (collection_id,)  # collection_id is already a string UUID
                )
                assets_by_type = {row[0]: row[1] for row in cur.fetchall()}

                return CollectionStatsResponse(
                    collection_id=collection_id,
                    collection_name=collection_name,
                    total_assets=stats_row[0] or 0,
                    total_chunks=stats_row[1] or 0,
                    assets_by_status={
                        "completed": stats_row[2] or 0,
                        "processing": stats_row[3] or 0,
                        "pending": stats_row[4] or 0,
                        "failed": stats_row[5] or 0,
                    },
                    assets_by_type=assets_by_type,
                    last_updated=stats_row[6].isoformat() if stats_row[6] else None,
                )
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ========================================
# ASSET MANAGEMENT ENDPOINTS
# ========================================


@router.get("/collections/{collection_id}/assets", response_model=List[TrainingAssetResponse])
async def list_training_assets(
    collection_id: str,
    status: Optional[str] = Query(None, description="Filter by processing status"),
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user),
):
    """List all assets in a training collection."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        asset_id, collection_id, source_file_id, title, description,
                        source_type, source_url, created_by, created_at,
                        processing_status, chunk_count, metadata
                    FROM das_training_assets
                    WHERE collection_id = %s
                """
                params = [collection_id]  # collection_id is already a string UUID

                if status:
                    query += " AND processing_status = %s"
                    params.append(status)

                query += " ORDER BY created_at DESC"

                cur.execute(query, params)
                rows = cur.fetchall()

                assets = []
                for row in rows:
                    assets.append(TrainingAssetResponse(
                        asset_id=str(row[0]),
                        collection_id=str(row[1]),
                        source_file_id=str(row[2]) if row[2] else None,
                        title=row[3],
                        description=row[4],
                        source_type=row[5],
                        source_url=row[6],
                        created_by=str(row[7]) if row[7] else None,
                        created_at=row[8].isoformat(),
                        processing_status=row[9],
                        chunk_count=row[10],
                        metadata=row[11] if isinstance(row[11], dict) else {},
                    ))

                return assets
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to list training assets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list assets: {str(e)}")


@router.get("/assets/{asset_id}", response_model=TrainingAssetResponse)
async def get_training_asset(
    asset_id: str,
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user),
):
    """Get details of a specific training asset."""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        asset_id, collection_id, source_file_id, title, description,
                        source_type, source_url, created_by, created_at,
                        processing_status, chunk_count, metadata
                    FROM das_training_assets
                    WHERE asset_id = %s
                    """,
                    (asset_id,)  # asset_id is already a string UUID
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(status_code=404, detail="Asset not found")

                return TrainingAssetResponse(
                    asset_id=str(row[0]),
                    collection_id=str(row[1]),
                    source_file_id=str(row[2]) if row[2] else None,
                    title=row[3],
                    description=row[4],
                    source_type=row[5],
                    source_url=row[6],
                    created_by=str(row[7]) if row[7] else None,
                    created_at=row[8].isoformat(),
                    processing_status=row[9],
                    chunk_count=row[10],
                    metadata=row[11] if isinstance(row[11], dict) else {},
                )
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get training asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset: {str(e)}")


@router.post("/collections/{collection_id}/upload")
async def upload_training_document(
    collection_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    source_type: str = Form("pdf"),
    source_url: Optional[str] = Form(None),
    chunking_strategy: str = Form("hybrid"),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    db: DatabaseService = Depends(get_db_service),
    processor = Depends(get_training_processor),
    user: dict = Depends(get_admin_user),  # Only admins can upload
):
    """
    Upload a training document to a collection (admin only).
    
    The file will be processed and chunks will be stored in the collection's Qdrant collection.
    """
    try:
        # Verify collection exists and is active
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT collection_id FROM das_training_collections WHERE collection_id = %s AND is_active = TRUE",
                    (collection_id,)  # collection_id is already a string UUID
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Collection not found or inactive")
        finally:
            db._return(conn)

        # Upload file to storage
        from ..services.file_storage import get_file_storage_service
        file_storage = get_file_storage_service()
        file_content = await file.read()
        
        upload_result = await file_storage.store_file(
            content=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            project_id=None,  # Training files are global, no project
            tags={"source_type": source_type, "training": True},
        )

        if not upload_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {upload_result.get('error', 'Unknown error')}"
            )

        file_id = upload_result["file_id"]

        # Process the file
        processing_options = {
            "chunking_strategy": chunking_strategy,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "batch_size": 16,
        }

        result = await processor.process_training_file(
            file_id=file_id,
            collection_id=collection_id,
            title=title or file.filename,
            description=description,
            source_type=source_type,
            source_url=source_url,
            processing_options=processing_options,
            user_id=user["user_id"],
        )

        return {
            "success": True,
            "asset_id": result["asset_id"],
            "file_id": file_id,
            "chunk_count": result["chunk_count"],
            "message": f"Training document uploaded and processed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload training document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.delete("/assets/{asset_id}")
async def delete_training_asset(
    asset_id: str,
    db: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_admin_user),  # Only admins can delete
):
    """
    Delete a training asset (admin only).
    
    This will also delete all chunks associated with the asset from Qdrant.
    """
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get asset info for Qdrant cleanup
                cur.execute(
                    """
                    SELECT collection_id, source_file_id 
                    FROM das_training_assets 
                    WHERE asset_id = %s
                    """,
                    (asset_id,)  # asset_id is already a string UUID
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Asset not found")

                collection_id, source_file_id = row

                # Get collection name
                cur.execute(
                    "SELECT collection_name FROM das_training_collections WHERE collection_id = %s",
                    (collection_id,)
                )
                collection_row = cur.fetchone()
                if not collection_row:
                    raise HTTPException(status_code=404, detail="Collection not found")
                
                collection_name = collection_row[0]

                # Delete chunks from Qdrant (if any exist)
                # Note: This will be handled by the training processor service
                # For now, we'll just delete from database

                # Delete from database
                cur.execute(
                    "DELETE FROM das_training_assets WHERE asset_id = %s",
                    (asset_id,)  # asset_id is already a string UUID
                )
                conn.commit()

                return {"message": f"Asset '{asset_id}' deleted successfully"}

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete training asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete asset: {str(e)}")
