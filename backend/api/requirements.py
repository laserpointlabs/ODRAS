"""
Requirements API endpoints
- Save extracted requirements artifacts to MinIO (JSON, not local)
- List saved requirements (by project or all)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.config import Settings
from ..services.file_storage import FileStorageService


def get_file_storage_service() -> FileStorageService:
    settings = Settings()
    return FileStorageService(settings)


router = APIRouter(prefix="/api/requirements", tags=["requirements"])


class SaveRequirementsRequest(BaseModel):
    file_id: str = Field(..., description="Source file_id the requirements were extracted from")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    requirements: List[str] = Field(default_factory=list, description="List of extracted requirement sentences")
    source_filename: Optional[str] = Field(None, description="Optional source filename for display")
    process_instance_id: Optional[str] = Field(None, description="Optional Camunda process instance ID")


class SaveRequirementsResponse(BaseModel):
    success: bool
    requirements_file_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class RequirementItem(BaseModel):
    requirements_file_id: str
    source_file_id: str
    source_filename: Optional[str] = None
    project_id: Optional[str] = None
    created_at: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)


class RequirementsListResponse(BaseModel):
    success: bool
    total_items: int
    total_requirements: int
    items: List[RequirementItem]


@router.post("/save", response_model=SaveRequirementsResponse)
async def save_requirements(
    body: SaveRequirementsRequest,
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """Save extracted requirements as a JSON artifact in MinIO (no local saves)."""
    try:
        import json

        now = datetime.now(timezone.utc).isoformat()
        artifact: Dict[str, Any] = {
            "kind": "requirements",
            "source_file_id": body.file_id,
            "source_filename": body.source_filename,
            "project_id": body.project_id,
            "process_instance_id": body.process_instance_id,
            "created_at": now,
            "requirements": body.requirements or [],
        }

        content_bytes = json.dumps(artifact, ensure_ascii=False).encode("utf-8")

        # Use a descriptive filename; a new file_id will be assigned by storage
        suggested_name = f"requirements_{body.file_id}_{int(datetime.now().timestamp())}.json"
        # Promote identifiers to tags for easy lookup from metadata
        tags = {"kind": "requirements"}
        if body.file_id:
            tags["source_file_id"] = body.file_id
        if body.process_instance_id:
            tags["process_instance_id"] = body.process_instance_id

        result = await storage_service.store_file(
            content=content_bytes,
            filename=suggested_name,
            content_type="application/json",
            project_id=body.project_id,
            tags=tags,
        )

        if result.get("success"):
            return SaveRequirementsResponse(
                success=True,
                requirements_file_id=result.get("file_id"),
                message="Requirements saved to storage",
            )
        else:
            return SaveRequirementsResponse(success=False, error=result.get("error", "Unknown error"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save requirements: {str(e)}")


@router.get("/", response_model=RequirementsListResponse)
async def list_requirements(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(1000, description="Max artifacts to scan"),
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """List saved requirements artifacts (grouped by saved files)."""
    try:
        import json

        # First, list all stored metadata (backend scans MinIO metadata objects)
        meta_list = await storage_service.list_files(project_id=project_id, limit=limit, offset=0)

        items: List[RequirementItem] = []
        total_requirements = 0

        for meta in meta_list:
            tags = meta.get("tags") or {}
            if tags.get("kind") != "requirements":
                continue

            req_file_id = meta.get("file_id")
            if not req_file_id:
                continue

            # Retrieve JSON artifact content
            data = await storage_service.retrieve_file(req_file_id)
            if not data or "content" not in data:
                continue
            try:
                artifact = json.loads(data["content"].decode("utf-8"))
            except Exception:
                continue

            reqs = artifact.get("requirements", []) or []
            total_requirements += len(reqs)

            items.append(
                RequirementItem(
                    requirements_file_id=req_file_id,
                    source_file_id=artifact.get("source_file_id") or tags.get("source_file_id", ""),
                    source_filename=artifact.get("source_filename") or meta.get("filename"),
                    project_id=artifact.get("project_id") or meta.get("project_id"),
                    created_at=artifact.get("created_at") or meta.get("created_at"),
                    requirements=reqs,
                )
            )

        return RequirementsListResponse(
            success=True, total_items=len(items), total_requirements=total_requirements, items=items
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list requirements: {str(e)}")


