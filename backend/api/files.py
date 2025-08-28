"""
File Storage API endpoints for ODRAS
Provides REST API for file upload, download, and management.
"""

import io
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, Header
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


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
    authorization: Optional[str] = Header(None),
):
    """
    Upload a file to the storage backend.

    Args:
        file: The file to upload
        project_id: Optional project ID to associate with the file
        tags: Optional JSON string of metadata tags

    Returns:
        Upload result with file metadata
    """
    try:
        # Validate project membership
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        # Minimal auth: read user from token (shared in main via services.auth)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ", 1)[1]
        from ..services.auth import TOKENS as AUTH_TOKENS
        user = AUTH_TOKENS.get(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        if not db.is_user_member(project_id=project_id, user_id=user["user_id"]):
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
        )

        if result["success"]:
            metadata = result["metadata"]
            return FileUploadResponse(
                success=True,
                file_id=result["file_id"],
                filename=metadata["filename"],
                size=metadata["size"],
                content_type=metadata["content_type"],
                message="File uploaded successfully",
            )
        else:
            return FileUploadResponse(success=False, error=result["error"])

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return FileUploadResponse(success=False, error=f"Upload failed: {str(e)}")


@router.get("/{file_id}/download")
async def download_file(file_id: str, storage_service: FileStorageService = Depends(get_file_storage_service)):
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
            headers={"Content-Disposition": f"attachment; filename={filename}", "Content-Length": str(len(file_content))},
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

        return {"success": True, "file_id": file_id, "url": url, "expires_in": expires_in}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file URL for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"URL generation failed: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(file_id: str, storage_service: FileStorageService = Depends(get_file_storage_service)):
    """
    Delete a file by ID.

    Args:
        file_id: Unique file identifier

    Returns:
        Deletion result
    """
    try:
        success = await storage_service.delete_file(file_id)

        if success:
            return {"success": True, "message": f"File {file_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found or deletion failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


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

    Returns:
        List of files with metadata
    """
    try:
        # Use the new visibility-aware method
        files = await storage_service.list_files_with_visibility(project_id, include_public, limit, offset)

        # Convert to response format
        file_responses = [FileMetadataResponse(**file_data) for file_data in files]

        return FileListResponse(
            success=True, files=file_responses, total_count=len(file_responses), message="Files retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/storage/info")
async def get_storage_info(storage_service: FileStorageService = Depends(get_file_storage_service)):
    """
    Get information about the current storage configuration.

    Returns:
        Storage backend information and capabilities
    """
    try:
        info = storage_service.get_storage_info()
        return {"success": True, "storage_info": info, "message": "Storage information retrieved successfully"}

    except Exception as e:
        logger.error(f"Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


@router.put("/{file_id}/tags")
async def update_file_tags(file_id: str, body: TagsUpdateRequest, storage_service: FileStorageService = Depends(get_file_storage_service)):
    try:
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
):
    """Server-side fetch by URL and store as a file (MVP)."""
    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        # Fetch bytes
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.content
            # Derive filename from URL
            import urllib.parse as _up
            parsed = _up.urlparse(url)
            name = (parsed.path.split("/")[-1] or "downloaded_file")
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
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error") or "Store failed")
        md = result["metadata"]
        return {"success": True, "file_id": result["file_id"], "filename": md["filename"], "size": md["size"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/batch/upload")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Upload multiple files in a batch operation.

    Args:
        files: List of files to upload
        project_id: Optional project ID to associate with all files

    Returns:
        Results for all uploaded files
    """
    try:
        results = []

        for file in files:
            try:
                content = await file.read()

                result = await storage_service.store_file(
                    content=content, filename=file.filename or "unknown", content_type=file.content_type, project_id=project_id
                )

                if result["success"]:
                    metadata = result["metadata"]
                    results.append(
                        {"filename": file.filename, "success": True, "file_id": result["file_id"], "size": metadata["size"]}
                    )
                else:
                    results.append({"filename": file.filename, "success": False, "error": result["error"]})

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
        # Retrieve stored file content
        file_data = await storage_service.retrieve_file(file_id)
        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found")

        document_content = file_data["content"].decode("utf-8", errors="ignore")
        document_filename = f"uploaded_{file_id}.txt"

        # Camunda config (aligns with backend.main)
        CAMUNDA_BASE_URL = "http://localhost:8080"
        CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

        # Build variables for starting process instance
        variables = {
            "document_content": {"value": document_content, "type": "String"},
            "document_filename": {"value": document_filename, "type": "String"},
            "llm_provider": {"value": (llm_provider or Settings().llm_provider), "type": "String"},
            "llm_model": {"value": (llm_model or Settings().llm_model), "type": "String"},
            "iterations": {"value": iterations, "type": "Integer"},
        }

        start_url = f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis/start"
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
    project_id: Optional[str] = Form(None), storage_service: FileStorageService = Depends(get_file_storage_service)
):
    """
    Scan all stored files (optionally filtered by project) and extract requirement-like
    sentences using the configured keyword list, then save as RDF to Fuseki.
    """
    try:
        files = await storage_service.list_files(project_id=project_id, limit=1000, offset=0)
        if not files:
            return {"success": True, "message": "No files to process", "extracted_count": 0, "triples_written": 0}

        keywords = [k.lower() for k in KEYWORD_CONFIG.keywords]
        min_len = KEYWORD_CONFIG.min_text_length

        def split_sentences(text: str) -> List[str]:
            import re

            # Simple sentence splitter: split on period/exclamation/question + whitespace
            parts = re.split(r"(?<=[.!?])\s+", text)
            return [p.strip() for p in parts if p.strip()]

        # Collect TTL triples
        ttl_lines: List[str] = [
            "@prefix odras: <http://odras.system/ontology#> .",
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
    visibility: str = Form(..., regex="^(private|public)$"),
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
        logger.info(f"Visibility update request: file_id={file_id}, visibility={visibility}, admin_user={admin_user}")
        
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
                "message": f"File visibility updated to {visibility}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update file visibility")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file visibility: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
