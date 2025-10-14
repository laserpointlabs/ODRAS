"""
File Storage API endpoints for ODRAS
Provides REST API for file upload, download, and management.
"""

import io
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    Header,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.file_storage import FileStorageService
from ..services.persistence import PersistenceLayer
from ..services.auth import get_admin_user, get_user

logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class FileUploadResponse(BaseModel):
    success: bool
    file_id: Optional[str] = None
    filename: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    knowledge_asset_id: Optional[str] = None  # Include knowledge asset ID
    message: Optional[str] = None
    error: Optional[str] = None


class FileMetadataResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int
    hash_md5: str
    hash_sha256: str
    storage_path: str
    project_id: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
    visibility: str = "private"  # "private" or "public"
    created_by: Optional[str] = None  # User ID of file owner
    iri: Optional[str] = None  # Installation-specific IRI


class FileListResponse(BaseModel):
    success: bool
    files: List[FileMetadataResponse]
    total_count: int
    message: Optional[str] = None


class TagsUpdateRequest(BaseModel):
    tags: Dict[str, Any]


class KeywordConfig(BaseModel):
    keywords: List[str] = Field(
        default_factory=lambda: [
            "shall",
            "must",
            "should",
            "will",
            "capability",
            "performance",
            "latency",
            "throughput",
            "reliability",
            "interface",
            "function",
        ]
    )
    min_text_length: int = 15
    context_window: int = 160


# Create router
router = APIRouter(prefix="/api/files", tags=["files"])


def get_file_storage_service() -> FileStorageService:
    """Dependency to get FileStorageService instance."""
    settings = Settings()
    return FileStorageService(settings)


def get_db_service() -> DatabaseService:
    return DatabaseService(Settings())


async def _get_file_processing_config(db_service: DatabaseService) -> Dict[str, str]:
    """Get file processing configuration from database."""
    try:
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT file_processing_implementation
                    FROM installation_config
                    WHERE is_active = true
                    LIMIT 1
                """)

                result = cur.fetchone()

                if result:
                    return {"file_processing_implementation": result[0] or "bpmn"}
                else:
                    return {"file_processing_implementation": "bpmn"}

        finally:
            db_service._return(conn)

    except Exception as e:
        logger.warning(f"Failed to get file processing config: {e}")
        return {"file_processing_implementation": "bpmn"}


async def _process_file_hardcoded(
    file_id: str,
    project_id: str,
    final_doc_type: str,
    embedding_model: str,
    final_chunking: str
) -> str:
    """Process file using hardcoded SQL-first approach with complete knowledge asset lifecycle."""
    try:
        logger.info(f"🔧 Starting COMPLETE hardcoded SQL-first processing for file {file_id}")

        # STEP 1-3: Use our SQL-first IngestionWorker (text extraction, chunking, embedding, SQL-first storage)
        from ..services.ingestion_worker import IngestionWorker
        from ..services.config import Settings

        settings = Settings()
        worker = IngestionWorker(settings)

        # Prepare parameters for hardcoded processing
        params = {
            'chunking': {
                'strategy': final_chunking,
                'chunk_size': 512,
                'overlap': 50
            },
            'embedding': {
                'modelId': embedding_model,
                'batchSize': 16
            }
        }

        logger.info(f"📄 Steps 1-3: SQL-first RAG processing with params: {params}")

        # Process file with SQL-first approach (creates doc + doc_chunk + vectors)
        result = await worker.ingest_files([file_id], params)

        if not (result.get('success') and result.get('successful', 0) > 0):
            logger.error(f"❌ SQL-first RAG processing failed for file {file_id}: {result}")
            raise Exception(f"SQL-first RAG processing failed: {result.get('results', [{}])[0].get('error', 'Unknown error')}")

        logger.info(f"✅ Steps 1-3: SQL-first RAG processing successful for file {file_id}")

        # STEP 4: Create Knowledge Asset (missing from our implementation!)
        logger.info(f"📄 Step 4: Creating knowledge asset for UI workbench...")
        knowledge_asset_id = await _create_knowledge_asset_hardcoded(
            file_id=file_id,
            project_id=project_id,
            document_type=final_doc_type
        )
        logger.info(f"✅ Step 4: Knowledge asset created: {knowledge_asset_id}")

        # STEP 5: Link chunks to knowledge asset AND update vectors with asset_id
        logger.info(f"📄 Step 5: Linking chunks to knowledge asset and updating vectors...")
        await _link_chunks_to_asset_hardcoded(file_id, knowledge_asset_id)

        # STEP 5b: Update SQL-first vectors to include asset_id (for source generation)
        logger.info(f"📄 Step 5b: Adding asset_id to SQL-first vectors for source references...")
        await _update_vectors_with_asset_id(file_id, knowledge_asset_id)

        logger.info(f"✅ Step 5: Chunks linked and vectors updated with asset_id")

        # STEP 6: Activate Knowledge Asset (make visible in UI)
        logger.info(f"📄 Step 6: Activating knowledge asset...")
        await _activate_knowledge_asset_hardcoded(knowledge_asset_id)
        logger.info(f"✅ Step 6: Knowledge asset activated - visible in Knowledge Management workbench")

        return f"hardcoded_process_{file_id}"  # Return process ID for tracking

    except Exception as e:
        logger.error(f"Complete hardcoded processing failed: {e}")
        raise


async def _create_knowledge_asset_hardcoded(file_id: str, project_id: str, document_type: str) -> str:
    """Create knowledge asset record (Step 4 of BPMN workflow)."""
    try:
        from ..services.db import DatabaseService
        import uuid
        import json  # Fix for 'json' is not defined

        db_service = DatabaseService(Settings())
        knowledge_asset_id = str(uuid.uuid4())

        # Get file metadata for asset creation
        from ..services.file_storage import FileStorageService
        storage_service = FileStorageService(Settings())
        file_metadata = await storage_service.get_file_metadata(file_id)

        filename = file_metadata.get('filename', 'unknown')
        title = filename.rsplit('.', 1)[0] if '.' in filename else filename  # Remove extension

        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_assets (
                        id, source_file_id, project_id, title, document_type,
                        content_summary, metadata, version, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    knowledge_asset_id,
                    file_id,
                    project_id,
                    title,
                    document_type,
                    f"Knowledge asset created from {filename} using hardcoded SQL-first processing",
                    json.dumps({"processing_method": "hardcoded_sql_first", "created_by": "hardcoded_processor"}),
                    "1.0.0",
                    "processing"  # Will be activated in step 6
                ))
            conn.commit()
            logger.info(f"Created knowledge asset {knowledge_asset_id} for file {file_id}")
            return knowledge_asset_id

        finally:
            db_service._return(conn)

    except Exception as e:
        logger.error(f"Failed to create knowledge asset: {e}")
        raise


async def _link_chunks_to_asset_hardcoded(file_id: str, knowledge_asset_id: str):
    """Link doc_chunks to knowledge asset (Step 5)."""
    try:
        from ..services.db import DatabaseService

        db_service = DatabaseService(Settings())
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get doc_id for this file
                cur.execute("SELECT doc_id FROM doc WHERE filename = (SELECT filename FROM files WHERE id = %s)", (file_id,))
                doc_result = cur.fetchone()

                if doc_result:
                    doc_id = doc_result[0]

                    # Create knowledge_chunks entries that reference both doc_chunks and knowledge_asset
                    cur.execute("""
                        INSERT INTO knowledge_chunks (id, asset_id, sequence_number, chunk_type, content, token_count, metadata, created_at)
                        SELECT
                            gen_random_uuid(),
                            %s,
                            chunk_index,
                            'text',
                            text,
                            LENGTH(text) / 4,  -- Rough token estimate
                            ('{"source": "hardcoded_sql_first", "doc_chunk_id": "' || chunk_id || '"}')::jsonb,
                            NOW()
                        FROM doc_chunk
                        WHERE doc_id = %s
                        ORDER BY chunk_index
                    """, (knowledge_asset_id, doc_id))

                    chunks_linked = cur.rowcount
                    logger.info(f"Linked {chunks_linked} chunks to knowledge asset {knowledge_asset_id}")

            conn.commit()

        finally:
            db_service._return(conn)

    except Exception as e:
        logger.error(f"Failed to link chunks to asset: {e}")
        raise


async def _activate_knowledge_asset_hardcoded(knowledge_asset_id: str):
    """Activate knowledge asset (Step 6 - make visible in UI)."""
    try:
        from ..services.db import DatabaseService

        db_service = DatabaseService(Settings())
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE knowledge_assets
                    SET
                        status = 'active',
                        processing_stats = jsonb_build_object('processing_method', 'hardcoded_sql_first', 'activated_at', NOW()::text),
                        updated_at = NOW()
                    WHERE id = %s
                """, (knowledge_asset_id,))

                if cur.rowcount > 0:
                    logger.info(f"Activated knowledge asset {knowledge_asset_id} - now visible in Knowledge Management workbench")
                else:
                    logger.warning(f"No knowledge asset found to activate: {knowledge_asset_id}")

            conn.commit()

        finally:
            db_service._return(conn)

    except Exception as e:
        logger.error(f"Failed to activate knowledge asset: {e}")
        raise


async def _update_vectors_with_asset_id(file_id: str, knowledge_asset_id: str):
    """Update SQL-first vectors to include asset_id for source generation (Step 5b)."""
    try:
        from ..services.db import DatabaseService
        from ..services.qdrant_service import QdrantService

        db_service = DatabaseService(Settings())
        qdrant_service = QdrantService(Settings())

        logger.info(f"🔧 Step 5b: Adding asset_id to vectors for source references")
        print(f"🔧 ASSET_ID_DEBUG: Starting asset_id update for file {file_id}")
        print(f"   Knowledge asset ID: {knowledge_asset_id}")

        # Get all chunk_ids for this file from our SQL-first storage
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get doc_id for this file
                cur.execute("SELECT doc_id FROM doc WHERE filename = (SELECT filename FROM files WHERE id = %s)", (file_id,))
                doc_result = cur.fetchone()

                if doc_result:
                    doc_id = doc_result[0]
                    print(f"🔍 ASSET_ID_DEBUG: Found doc_id {doc_id} for file {file_id}")

                    # Get all chunk_ids for this doc
                    cur.execute("SELECT chunk_id FROM doc_chunk WHERE doc_id = %s ORDER BY chunk_index", (doc_id,))
                    chunk_results = cur.fetchall()

                    chunk_ids = [row[0] for row in chunk_results]
                    print(f"✅ ASSET_ID_DEBUG: Found {len(chunk_ids)} chunk_ids to update")

                    # Use set_payload to safely add asset_id to each vector
                    updated_count = 0
                    for chunk_id in chunk_ids:
                        try:
                            print(f"🔧 ASSET_ID_DEBUG: Adding asset_id to chunk {chunk_id}")

                            # Use set_payload method (safer than upsert)
                            result = qdrant_service.client.set_payload(
                                collection_name='knowledge_chunks',
                                payload={'asset_id': knowledge_asset_id},
                                points=[chunk_id],
                                wait=True
                            )

                            updated_count += 1
                            print(f"✅ ASSET_ID_DEBUG: Updated chunk {chunk_id} with asset_id")

                        except Exception as ve:
                            print(f"❌ ASSET_ID_DEBUG: Failed to update chunk {chunk_id}: {ve}")
                            logger.warning(f"Failed to update chunk {chunk_id} with asset_id: {ve}")

                    logger.info(f"✅ Step 5b: Updated {updated_count}/{len(chunk_ids)} vectors with asset_id")
                    print(f"✅ ASSET_ID_DEBUG: Complete - {updated_count} vectors updated with asset_id")

                    if updated_count == len(chunk_ids):
                        print(f"🎉 ASSET_ID_DEBUG: All vectors successfully updated - sources will work!")
                    else:
                        print(f"⚠️ ASSET_ID_DEBUG: {len(chunk_ids) - updated_count} vectors failed to update")

                else:
                    print(f"❌ ASSET_ID_DEBUG: No doc_id found for file {file_id}")
                    logger.error(f"No doc_id found for file {file_id}")

        finally:
            db_service._return(conn)

    except Exception as e:
        print(f"❌ ASSET_ID_DEBUG: Asset_id update failed: {e}")
        logger.error(f"Failed to update vectors with asset_id: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise - let the upload succeed even if asset_id update fails


def _detect_file_type_and_strategy(filename: str, content_type: str = None) -> Dict[str, str]:
    """
    Intelligently detect document type and optimal processing strategy based on file.

    Returns:
        Dict with 'document_type' and 'chunking_strategy'
    """
    filename_lower = filename.lower()

    # Document type detection
    if any(filename_lower.endswith(ext) for ext in [".pdf", ".doc", ".docx"]):
        document_type = "document"
        chunking_strategy = "semantic"  # Better for documents
    elif any(filename_lower.endswith(ext) for ext in [".txt", ".md", ".rst"]):
        document_type = "text"
        chunking_strategy = "hybrid"  # Balanced approach
    elif any(filename_lower.endswith(ext) for ext in [".json", ".xml", ".yml", ".yaml"]):
        document_type = "structured"
        chunking_strategy = "fixed"  # Preserve structure
    elif any(filename_lower.endswith(ext) for ext in [".py", ".js", ".java", ".cpp", ".c"]):
        document_type = "code"
        chunking_strategy = "fixed"  # Preserve code blocks
    elif any(filename_lower.endswith(ext) for ext in [".csv", ".xlsx", ".xls"]):
        document_type = "data"
        chunking_strategy = "fixed"  # Preserve tabular structure
    elif "requirements" in filename_lower or "specification" in filename_lower:
        document_type = "requirements"
        chunking_strategy = "semantic"  # Extract requirement relationships
    elif any(term in filename_lower for term in ["manual", "guide", "procedure"]):
        document_type = "knowledge"
        chunking_strategy = "semantic"  # Extract procedural knowledge
    else:
        document_type = "unknown"
        chunking_strategy = "hybrid"  # Safe default

    return {"document_type": document_type, "chunking_strategy": chunking_strategy}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    process_for_knowledge: Optional[bool] = Form(True),  # Auto-process for knowledge (default True)
    embedding_model: Optional[str] = Form(
        "all-MiniLM-L6-v2"
    ),  # Embedding model for knowledge processing
    chunking_strategy: Optional[str] = Form("hybrid"),  # Chunking strategy for knowledge processing
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
    authorization: Optional[str] = Header(None),
):
    """
    Upload a file to the storage backend with automatic knowledge processing.

    All uploaded files are automatically processed for knowledge management
    with intelligent defaults based on file type and content.

    Args:
        file: The file to upload
        project_id: Optional project ID to associate with the file
        tags: Optional JSON string of metadata tags
        embedding_model: Embedding model to use for knowledge processing (default: all-MiniLM-L6-v2)
        chunking_strategy: Chunking strategy for knowledge processing (fixed/semantic/hybrid, default: hybrid)

    Returns:
        Upload result with file metadata and knowledge asset ID
    """
    try:
        # Validate project membership
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        # Minimal auth: read user from token (shared in main via services.auth)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ", 1)[1]
        from ..services.auth import get_user

        user = get_user(authorization)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")

        # Read file content
        content = await file.read()

        # Parse tags if provided
        file_tags = {}
        if tags:
            import json

            try:
                file_tags = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in tags parameter: {tags}")

        # Store file
        result = await storage_service.store_file(
            content=content,
            filename=file.filename or "unknown",
            content_type=file.content_type,
            project_id=project_id,
            tags=file_tags,
            created_by=user["user_id"],  # Track file ownership
        )

        if result["success"]:
            metadata = result["metadata"]
            file_id = result["file_id"]

            # Automatic knowledge processing - only if enabled
            knowledge_asset_id = None
            if process_for_knowledge:
                try:
                    # Use the proven working knowledge transformation service
                    from ..services.knowledge_transformation import (
                        get_knowledge_transformation_service,
                    )

                    # Intelligent file type detection and processing strategy
                    file_detection = _detect_file_type_and_strategy(
                        file.filename, file.content_type
                    )

                    # Use detected type or tag override
                    detected_doc_type = file_detection["document_type"]
                    final_doc_type = (
                        file_tags.get("docType", detected_doc_type)
                        if file_tags
                        else detected_doc_type
                    )

                    # Use detected strategy or user preference
                    detected_chunking = file_detection["chunking_strategy"]
                    final_chunking = chunking_strategy or detected_chunking

                    logger.info(
                        f"🤖 Auto-detected: {final_doc_type} document, {final_chunking} chunking"
                    )

                    # Prepare processing options
                    processing_options = {
                        "document_type": final_doc_type,
                        "embedding_model": embedding_model or "all-MiniLM-L6-v2",
                        "chunking_strategy": final_chunking,
                        "chunk_size": 512,
                        "chunk_overlap": 50,
                        "extract_relationships": True,
                    }

                    # Check file processing configuration to decide between hardcoded and BPMN
                    file_processing_config = await _get_file_processing_config(db)
                    file_processing_implementation = file_processing_config.get("file_processing_implementation", "bpmn")

                    logger.info(f"🔧 File processing mode: {file_processing_implementation}")

                    if file_processing_implementation == "hardcoded":
                        # Use SQL-first hardcoded processing
                        logger.info(f"📄 Using HARDCODED processing for file {file_id}")
                        process_instance_id = await _process_file_hardcoded(
                            file_id=file_id,
                            project_id=project_id,
                            final_doc_type=final_doc_type,
                            embedding_model=embedding_model,
                            final_chunking=final_chunking
                        )

                        response_message = f"File uploaded and processed successfully using hardcoded SQL-first approach (process: {process_instance_id})"

                    else:
                        # Use BPMN workflow (original behavior)
                        logger.info(f"📄 Using BPMN WORKFLOW processing for file {file_id}")
                        import httpx

                        camunda_url = "http://localhost:8080/engine-rest"
                        start_url = (
                            f"{camunda_url}/process-definition/key/automatic_knowledge_processing/start"
                        )

                        payload = {
                            "variables": {
                                "file_id": {"value": file_id, "type": "String"},
                                "project_id": {"value": project_id, "type": "String"},
                                "filename": {"value": file.filename, "type": "String"},
                                "document_type": {
                                    "value": final_doc_type,
                                    "type": "String",
                                },
                                "embedding_model": {
                                    "value": embedding_model or "all-MiniLM-L6-v2",
                                    "type": "String",
                                },
                                "chunking_strategy": {
                                    "value": final_chunking,
                                    "type": "String",
                                },
                                "chunk_size": {"value": 512, "type": "Integer"},
                            }
                        }

                        async with httpx.AsyncClient(timeout=10) as client:  # Shorter timeout
                            response = await client.post(start_url, json=payload)
                            response.raise_for_status()
                            data = response.json()

                        process_instance_id = data.get("id")
                        response_message = "File uploaded and BPMN knowledge processing started (workflow: " + (process_instance_id or "unknown") + ")"

                        logger.info(
                            f"🔄 Started BPMN knowledge processing workflow: {process_instance_id} for file {file_id}"
                        )

                except Exception as e:
                    logger.error(f"❌ Knowledge processing failed for file {file_id}: {str(e)}")
                    # Don't fail the upload if processing fails
                    process_instance_id = f"failed_{file_id}"
                    response_message = f"File uploaded but {file_processing_implementation} processing failed - check logs"

            # EventCapture2: Capture file upload event
            try:
                from ..services.eventcapture2 import get_event_capture
                event_capture = get_event_capture()
                if event_capture:
                    await event_capture.capture_file_operation(
                        operation_type="uploaded",
                        filename=metadata["filename"],
                        project_id=project_id,
                        user_id=user["user_id"],
                        username=user.get("username", "unknown"),
                        file_details={
                            "file_id": file_id,
                            "size": metadata["size"],
                            "content_type": metadata["content_type"],
                            "hash_md5": metadata.get("hash_md5"),
                            "knowledge_processing": bool(process_instance_id),
                            "workflow_id": process_instance_id
                        }
                    )
                    print(f"🔥 DIRECT: EventCapture2 file upload captured - {metadata['filename']} ({metadata['size']} bytes)")
            except Exception as e:
                print(f"🔥 DIRECT: EventCapture2 file upload failed: {e}")
                logger.warning(f"EventCapture2 file upload failed: {e}")

            # Response message already set in if/else block above - no need to override

            return FileUploadResponse(
                success=True,
                file_id=file_id,
                filename=metadata["filename"],
                size=metadata["size"],
                content_type=metadata["content_type"],
                knowledge_asset_id=process_instance_id,  # Include process instance ID (hardcoded or BPMN)
                message=response_message,
            )
        else:
            return FileUploadResponse(success=False, error=result["error"])

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return FileUploadResponse(success=False, error=f"Upload failed: {str(e)}")


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Download a file by ID.

    Args:
        file_id: Unique file identifier

    Returns:
        File content as streaming response
    """
    try:
        # Retrieve file
        file_data = await storage_service.retrieve_file(file_id)

        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Create streaming response
        file_content = file_data["content"]
        file_stream = io.BytesIO(file_content)

        # Determine content type and filename
        content_type = "application/octet-stream"
        filename = f"file_{file_id}"

        # You might want to retrieve actual metadata here if available

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/{file_id}/url")
async def get_file_url(
    file_id: str,
    expires_in: int = Query(3600, description="URL expiration time in seconds"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Get a URL for file access (presigned URL for MinIO, API endpoint for others).

    Args:
        file_id: Unique file identifier
        expires_in: URL expiration time in seconds

    Returns:
        File access URL
    """
    try:
        url = await storage_service.get_file_url(file_id, expires_in)

        if url is None:
            raise HTTPException(status_code=404, detail="File not found or URL generation failed")

        return {
            "success": True,
            "file_id": file_id,
            "url": url,
            "expires_in": expires_in,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file URL for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"URL generation failed: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    delete_knowledge_assets: bool = Query(False, description="Whether to also delete associated knowledge assets"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    user: Dict = Depends(get_user),  # Add user authentication
):
    """
    Delete a file by ID (owner or admin only).

    Args:
        file_id: Unique file identifier
        user: Authenticated user

    Returns:
        Deletion result
    """
    try:
        # Check file ownership
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        is_admin = user.get("is_admin", False)
        file_created_by = file_metadata.get("created_by")
        user_id = user["user_id"]
        is_owner = file_created_by == user_id

        # Debug logging
        logger.info(
            f"File deletion auth check: file_id={file_id}, user_id={user_id}, is_admin={is_admin}"
        )
        logger.info(
            f"File metadata created_by: {repr(file_created_by)} (type: {type(file_created_by)})"
        )
        logger.info(f"User ID: {repr(user_id)} (type: {type(user_id)})")
        logger.info(f"Is owner: {is_owner}, Is admin: {is_admin}")

        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")

        # Check for associated knowledge assets before deletion
        from ..services.db import DatabaseService
        from ..services.config import Settings

        db = DatabaseService(Settings())
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                # Get knowledge assets for this file
                cur.execute("""
                    SELECT ka.id, ka.title, ka.created_at, ka.traceability_status
                    FROM knowledge_assets ka
                    WHERE ka.source_file_id = %s
                """, (file_id,))

                knowledge_assets = cur.fetchall()

                if knowledge_assets and not delete_knowledge_assets:
                    # If user didn't explicitly choose to delete knowledge assets,
                    # apply smart defaults based on asset age
                    from datetime import datetime, timezone, timedelta
                    now = datetime.now(timezone.utc)

                    recent_assets = []
                    old_assets = []

                    for asset in knowledge_assets:
                        asset_age = now - asset[2]  # created_at is index 2
                        if asset_age.days <= 30:
                            recent_assets.append(asset)
                        else:
                            old_assets.append(asset)

                    # Smart default: preserve recent assets, can delete old ones
                    if recent_assets:
                        # File has recent knowledge assets - preserve them by default
                        logger.info(f"File {file_id} has {len(recent_assets)} recent knowledge assets - preserving as orphaned")

                        # Delete file but preserve knowledge assets (they'll become orphaned)
                        success = await storage_service.delete_file(file_id)

                        if success:
                            return {
                                "success": True,
                                "message": f"File deleted, {len(knowledge_assets)} knowledge asset(s) preserved as orphaned",
                                "orphaned_assets": len(knowledge_assets),
                                "deletion_strategy": "preserve_knowledge"
                            }
                    else:
                        # Only old assets - can delete both
                        logger.info(f"File {file_id} has only old knowledge assets - deleting both file and assets")

                        # Delete knowledge assets first
                        for asset in knowledge_assets:
                            cur.execute("DELETE FROM knowledge_assets WHERE id = %s", (asset[0],))

                        conn.commit()

                        # Then delete file
                        success = await storage_service.delete_file(file_id)

                        if success:
                            return {
                                "success": True,
                                "message": f"File and {len(knowledge_assets)} old knowledge asset(s) deleted",
                                "deleted_assets": len(knowledge_assets),
                                "deletion_strategy": "delete_both"
                            }

                elif delete_knowledge_assets:
                    # User explicitly chose to delete knowledge assets
                    logger.info(f"File {file_id} - user chose to delete {len(knowledge_assets)} knowledge assets")

                    # Delete knowledge assets first
                    for asset in knowledge_assets:
                        cur.execute("DELETE FROM knowledge_assets WHERE id = %s", (asset[0],))

                    conn.commit()

                    # Then delete file
                    success = await storage_service.delete_file(file_id)

                    if success:
                        return {
                            "success": True,
                            "message": f"File and {len(knowledge_assets)} knowledge asset(s) deleted",
                            "deleted_assets": len(knowledge_assets),
                            "deletion_strategy": "delete_both_explicit"
                        }
                else:
                    # No knowledge assets - simple file deletion
                    success = await storage_service.delete_file(file_id)

                    if success:
                        return {
                            "success": True,
                            "message": f"File {file_id} deleted successfully",
                            "deletion_strategy": "file_only"
                        }

                # If we get here, deletion failed
                raise HTTPException(status_code=500, detail="File deletion failed")

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/{file_id}/knowledge-assets")
async def check_file_knowledge_assets(
    file_id: str,
    user: Dict = Depends(get_user),
):
    """
    Check if a file has associated knowledge assets.

    Returns information about knowledge assets that would be affected by file deletion.
    """
    try:
        from ..services.db import DatabaseService
        from ..services.config import Settings

        db = DatabaseService(Settings())
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                # Check for knowledge assets linked to this file
                cur.execute("""
                    SELECT ka.id, ka.title, ka.document_type, ka.status, ka.created_at,
                           ka.traceability_status
                    FROM knowledge_assets ka
                    WHERE ka.source_file_id = %s
                    ORDER BY ka.created_at DESC
                """, (file_id,))

                rows = cur.fetchall()
                assets = []

                for row in rows:
                    asset_dict = dict(zip([desc[0] for desc in cur.description], row))
                    assets.append({
                        "id": str(asset_dict["id"]),
                        "title": asset_dict["title"],
                        "document_type": asset_dict["document_type"],
                        "status": asset_dict["status"],
                        "created_at": asset_dict["created_at"].isoformat() if asset_dict["created_at"] else None,
                        "traceability_status": asset_dict.get("traceability_status", "linked")
                    })

                return {
                    "file_id": file_id,
                    "has_knowledge_assets": len(assets) > 0,
                    "asset_count": len(assets),
                    "assets": assets,
                    "deletion_impact": {
                        "will_orphan": len(assets),
                        "recommendation": "preserve" if len(assets) > 0 else "delete_both"
                    }
                }

        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to check knowledge assets for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check knowledge assets: {str(e)}")


@router.get("/", response_model=FileListResponse)
async def list_files(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    include_public: bool = Query(False, description="Include public files from other projects"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Result offset for pagination"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    List files with optional filtering and visibility support.

    Args:
        project_id: Optional project ID filter
        include_public: Include public files from other projects (requires project_id)
        limit: Maximum number of results
        offset: Result offset for pagination
        user: Authenticated user (required)

    Returns:
        List of files with metadata
    """
    try:
        # Direct database query like assumptions API - no user filtering for tree view
        files = await storage_service.list_files(
            project_id=project_id,
            limit=limit,
            offset=offset
        )

        # Convert to response format
        file_responses = [FileMetadataResponse(**file_data) for file_data in files]

        return FileListResponse(
            success=True,
            files=file_responses,
            total_count=len(file_responses),
            message="Files retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/admin/all", response_model=FileListResponse)
async def list_all_files_admin(
    limit: int = Query(1000, description="Maximum number of results"),
    offset: int = Query(0, description="Result offset for pagination"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
    admin_user: Dict = Depends(get_admin_user),  # Admin only
):
    """
    List ALL files across all projects (Admin only).

    This endpoint allows admins to see all files in the system
    regardless of project membership for cleanup and management.
    """
    try:
        logger.info(f"Admin {admin_user.get('user_id')} listing all files")

        # Get all files without project filtering
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Get all files with user information
                cur.execute("""
                    SELECT f.id as file_id, f.filename, f.content_type, f.file_size as size,
                           f.hash_md5, f.hash_sha256, f.storage_path, f.created_at, f.updated_at,
                           f.metadata, f.iri, f.created_by, f.project_id,
                           u.username as owner_username, u.display_name as owner_display_name
                    FROM files f
                    LEFT JOIN public.users u ON f.created_by = u.user_id::text
                    WHERE f.is_deleted = FALSE OR f.is_deleted IS NULL
                    ORDER BY f.created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))

                rows = cur.fetchall()

                # Convert to response format
                files = []
                for row in rows:
                    row_dict = dict(zip([desc[0] for desc in cur.description], row))
                    metadata = row_dict.get("metadata") or {}

                    # Parse metadata JSON if it's a string
                    if isinstance(metadata, str):
                        import json
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}

                    file_data = {
                        "file_id": str(row_dict["file_id"]),
                        "filename": row_dict["filename"],
                        "content_type": row_dict["content_type"],
                        "size": row_dict["size"],
                        "hash_md5": row_dict["hash_md5"],
                        "hash_sha256": row_dict["hash_sha256"],
                        "storage_path": row_dict["storage_path"],
                        "created_at": row_dict["created_at"].isoformat() if row_dict["created_at"] else "",
                        "updated_at": row_dict["updated_at"].isoformat() if row_dict["updated_at"] else "",
                        "project_id": str(row_dict["project_id"]) if row_dict["project_id"] else None,
                        "tags": metadata.get("tags", {}),
                        "visibility": metadata.get("visibility", "private"),
                        "created_by": row_dict["created_by"],
                        "iri": row_dict["iri"],
                        # Add owner info for admin view (these won't be in the Pydantic model but will be in the dict)
                        "owner_username": row_dict["owner_username"],
                        "owner_display_name": row_dict["owner_display_name"]
                    }
                    files.append(file_data)

                return {
                    "success": True,
                    "files": files,  # Return raw dicts instead of Pydantic models to include extra fields
                    "total_count": len(files),
                    "message": f"Retrieved {len(files)} files (Admin view)",
                }

        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Failed to list all files for admin: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/storage/info")
async def get_storage_info(
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Get information about the current storage configuration.

    Returns:
        Storage backend information and capabilities
    """
    try:
        info = storage_service.get_storage_info()
        return {
            "success": True,
            "storage_info": info,
            "message": "Storage information retrieved successfully",
        }

    except Exception as e:
        logger.error(f"Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


@router.put("/{file_id}/tags")
async def update_file_tags(
    file_id: str,
    body: TagsUpdateRequest,
    storage_service: FileStorageService = Depends(get_file_storage_service),
    user: Dict = Depends(get_user),  # Add user authentication
):
    try:
        # Check file ownership
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        is_admin = user.get("is_admin", False)
        is_owner = file_metadata.get("created_by") == user["user_id"]

        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Not authorized to edit this file")

        ok = await storage_service.update_file_tags(file_id, body.tags or {})
        if not ok:
            raise HTTPException(status_code=404, detail="File metadata not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tags update failed: {str(e)}")


@router.post("/import-url")
async def import_file_by_url(
    url: str = Form(...),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
    user: Dict = Depends(get_user),  # Add user authentication
):
    """Server-side fetch by URL and store as a file (MVP)."""
    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        # Check project membership
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")
        # Fetch bytes
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.content
            # Derive filename from URL
            import urllib.parse as _up

            parsed = _up.urlparse(url)
            name = parsed.path.split("/")[-1] or "downloaded_file"
        file_tags = {}
        if tags:
            import json

            try:
                file_tags = json.loads(tags)
            except json.JSONDecodeError:
                file_tags = {}
        result = await storage_service.store_file(
            content=content,
            filename=name,
            content_type=None,
            project_id=project_id,
            tags=file_tags,
            created_by=user["user_id"],  # Track file ownership
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error") or "Store failed")
        md = result["metadata"]
        return {
            "success": True,
            "file_id": result["file_id"],
            "filename": md["filename"],
            "size": md["size"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch/upload")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
    user: Dict = Depends(get_user),  # Add user authentication
):
    """
    Upload multiple files in a batch operation.

    Args:
        files: List of files to upload
        project_id: Required project ID to associate with all files
        user: Authenticated user

    Returns:
        Results for all uploaded files
    """
    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        # Check project membership
        if not user.get("is_admin", False) and not db.is_user_member(
            project_id=project_id, user_id=user["user_id"]
        ):
            raise HTTPException(status_code=403, detail="Not a member of project")

        results = []

        for file in files:
            try:
                content = await file.read()

                result = await storage_service.store_file(
                    content=content,
                    filename=file.filename or "unknown",
                    content_type=file.content_type,
                    project_id=project_id,
                    created_by=user["user_id"],  # Track file ownership
                )

                if result["success"]:
                    metadata = result["metadata"]
                    results.append(
                        {
                            "filename": file.filename,
                            "success": True,
                            "file_id": result["file_id"],
                            "size": metadata["size"],
                        }
                    )
                else:
                    results.append(
                        {
                            "filename": file.filename,
                            "success": False,
                            "error": result["error"],
                        }
                    )

            except Exception as e:
                results.append({"filename": file.filename, "success": False, "error": str(e)})

        # Calculate summary statistics
        successful_uploads = sum(1 for r in results if r["success"])
        total_uploads = len(results)

        return {
            "success": True,
            "results": results,
            "summary": {
                "total_files": total_uploads,
                "successful_uploads": successful_uploads,
                "failed_uploads": total_uploads - successful_uploads,
            },
            "message": f"Batch upload completed: {successful_uploads}/{total_uploads} files uploaded successfully",
        }

    except Exception as e:
        logger.error(f"Failed batch upload: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.post("/{file_id}/process")
async def process_uploaded_file(
    file_id: str,
    processing_type: str = Form("extract_requirements"),
    llm_provider: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    iterations: int = Form(10),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    user: Dict = Depends(get_user),  # Add user authentication
):
    """
    Trigger processing of an uploaded file (e.g., requirements extraction) by starting the Camunda BPMN process.

    Args:
        file_id: Unique file identifier
        processing_type: Type of processing to perform (currently ignored, default extract_requirements)
        llm_provider: Optional LLM provider override
        llm_model: Optional LLM model override
        iterations: Monte Carlo iterations

    Returns:
        Processing initiation result including Camunda process instance info
    """
    try:
        # Check file ownership and permissions
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        is_admin = user.get("is_admin", False)
        is_owner = file_metadata.get("created_by") == user["user_id"]

        # For project-based files, check project membership
        project_id = file_metadata.get("project_id")
        has_project_access = False
        if project_id:
            # Import db service to check project membership
            from ..services.db import DatabaseService
            from ..services.config import Settings

            db = DatabaseService(Settings())
            has_project_access = is_admin or db.is_user_member(
                project_id=project_id, user_id=user["user_id"]
            )

        if not (is_admin or is_owner or has_project_access):
            raise HTTPException(status_code=403, detail="Not authorized to process this file")

        # Retrieve stored file content
        file_data = await storage_service.retrieve_file(file_id)
        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found")

        document_content = file_data["content"].decode("utf-8", errors="ignore")
        document_filename = f"uploaded_{file_id}.txt"

        # Camunda config (aligns with backend.main)
        CAMUNDA_BASE_URL = "http://localhost:8080"
        CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

        # Get document type from file metadata/tags, with intelligent fallback
        file_tags = file_metadata.get("tags", {})
        stored_doc_type = file_tags.get("docType")

        # If no stored type, detect from filename
        if not stored_doc_type or stored_doc_type == "unknown":
            filename = file_metadata.get("filename", "unknown")
            file_detection = _detect_file_type_and_strategy(filename, file_metadata.get("content_type"))
            detected_doc_type = file_detection["document_type"]
            final_doc_type = detected_doc_type if detected_doc_type != "unknown" else "knowledge"
        else:
            final_doc_type = stored_doc_type

        # Build variables for starting process instance (match upload format)
        variables = {
            "file_id": {"value": file_id, "type": "String"},
            "project_id": {"value": file_metadata.get("project_id"), "type": "String"},
            "filename": {"value": file_metadata.get("filename", "unknown"), "type": "String"},
            "document_type": {"value": final_doc_type, "type": "String"},
            "embedding_model": {"value": "all-MiniLM-L6-v2", "type": "String"},
            "chunking_strategy": {"value": "smart_default", "type": "String"},
            "llm_provider": {
                "value": (llm_provider or Settings().llm_provider),
                "type": "String",
            },
            "llm_model": {
                "value": (llm_model or Settings().llm_model),
                "type": "String",
            },
        }

        start_url = (
            f"{CAMUNDA_REST_API}/process-definition/key/automatic_knowledge_processing/start"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(start_url, json={"variables": variables})
            response.raise_for_status()
            data = response.json()

        process_instance_id = data.get("id")
        return {
            "success": True,
            "file_id": file_id,
            "processing_type": processing_type,
            "process_instance_id": process_instance_id,
            "camunda_url": f"{CAMUNDA_BASE_URL}/cockpit/default/#/process-instance/{process_instance_id}",
            "message": "Camunda process started from stored file",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


KEYWORD_CONFIG: KeywordConfig = KeywordConfig()


@router.get("/keywords", response_model=KeywordConfig)
async def get_keywords():
    return KEYWORD_CONFIG


@router.put("/keywords", response_model=KeywordConfig)
async def update_keywords(config: KeywordConfig):
    global KEYWORD_CONFIG
    KEYWORD_CONFIG = config
    return KEYWORD_CONFIG


@router.post("/extract/keywords")
async def extract_requirements_by_keywords(
    project_id: Optional[str] = Form(None),
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Scan all stored files (optionally filtered by project) and extract requirement-like
    sentences using the configured keyword list, then save as RDF to Fuseki.
    """
    try:
        files = await storage_service.list_files(project_id=project_id, limit=1000, offset=0)
        if not files:
            return {
                "success": True,
                "message": "No files to process",
                "extracted_count": 0,
                "triples_written": 0,
            }

        keywords = [k.lower() for k in KEYWORD_CONFIG.keywords]
        min_len = KEYWORD_CONFIG.min_text_length

        def split_sentences(text: str) -> List[str]:
            import re

            # Simple sentence splitter: split on period/exclamation/question + whitespace
            parts = re.split(r"(?<=[.!?])\s+", text)
            return [p.strip() for p in parts if p.strip()]

        # Collect TTL triples
        from backend.services.config import Settings

        settings = Settings()
        base_uri = settings.installation_base_uri.rstrip("/")

        ttl_lines: List[str] = [
            f"@prefix odras: <{base_uri}/ontology#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
        ]
        extracted_count = 0

        for meta in files:
            fid = meta.get("file_id")
            if not fid:
                continue
            data = await storage_service.retrieve_file(fid)
            if not data or "content" not in data:
                continue
            text = data["content"].decode("utf-8", errors="ignore")
            for sent in split_sentences(text):
                if len(sent) < min_len:
                    continue
                low = sent.lower()
                if any(k in low for k in keywords):
                    extracted_count += 1
                    rid = f"req_{fid}_{extracted_count}"
                    # Clean the text for RDF
                    clean_text = sent.replace("\\", " ").replace('"', '\\"')
                    ttl_lines.extend(
                        [
                            f"odras:{rid} rdf:type odras:Requirement .",
                            f'odras:{rid} odras:text "{clean_text}" .',
                            f"odras:{rid} odras:sourceFile \"{meta.get('filename','unknown')}\" .",
                            "",
                        ]
                    )

        triples_written = 0
        if extracted_count > 0:
            persistence = PersistenceLayer(Settings())
            ttl_content = "\n".join(ttl_lines)
            persistence.write_rdf(ttl_content)
            triples_written = len([ln for ln in ttl_lines if ln.endswith(" .")])

        return {
            "success": True,
            "project_id": project_id,
            "config": KEYWORD_CONFIG.dict(),
            "file_count": len(files),
            "extracted_count": extracted_count,
            "triples_written": triples_written,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.put("/{file_id}/visibility")
async def update_file_visibility(
    file_id: str,
    visibility: str = Form(..., pattern="^(private|public)$"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """
    Update file visibility (admin only).

    Args:
        file_id: Unique file identifier
        visibility: "private" or "public"

    Returns:
        Success response with updated visibility
    """
    try:
        logger.info(
            f"Visibility update request: file_id={file_id}, visibility={visibility}, admin_user={admin_user}"
        )

        # Check if file exists first
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            logger.error(f"File not found: {file_id}")
            raise HTTPException(status_code=404, detail="File not found")

        logger.info(f"Current file metadata: {file_metadata}")

        # Update visibility
        success = await storage_service.update_file_visibility(file_id, visibility)
        logger.info(f"Visibility update result: success={success}")

        if success:
            return {
                "success": True,
                "file_id": file_id,
                "visibility": visibility,
                "message": f"File visibility updated to {visibility}",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update file visibility")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file visibility: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
