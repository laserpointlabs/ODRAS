"""
Requirements Workbench API

Comprehensive API endpoints for requirements management including:
- Requirements CRUD operations with filtering, sorting, pagination
- Requirements extraction from documents
- Constraints management
- Multi-user notes and collaboration
- DAS integration for requirement reviews
- Publishing and approval workflows
- History and audit trails
"""

import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from fastapi.responses import JSONResponse

from backend.services.requirements_extraction import (
    RequirementsExtractionEngine, 
    ExtractionConfig, 
    ExtractionResult,
    RequirementType,
    ConstraintType
)
from backend.services.db import DatabaseService
from backend.services.config import Settings
from backend.services.das_core_engine import DASCoreEngine
from backend.services.file_storage import FileStorageService
from backend.api.das import get_das_engine
from backend.services.auth import get_user as get_current_user
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/requirements", tags=["requirements"])

# =====================================
# PYDANTIC MODELS
# =====================================

class RequirementCreate(BaseModel):
    """Model for creating a new requirement."""
    requirement_identifier: Optional[str] = None  # Auto-generated if not provided
    requirement_title: str = Field(..., min_length=1, max_length=500)
    requirement_text: str = Field(..., min_length=10)
    requirement_rationale: Optional[str] = None
    requirement_type: str = Field(..., pattern="^(functional|non_functional|performance|safety|security|interface|operational|design|implementation)$")
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    verification_method: Optional[str] = Field(None, pattern="^(test|analysis|inspection|demonstration|review)$")
    verification_criteria: Optional[str] = None
    source_document_id: Optional[str] = None
    source_section: Optional[str] = None
    parent_requirement_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RequirementUpdate(BaseModel):
    """Model for updating a requirement."""
    requirement_title: Optional[str] = Field(None, max_length=500)
    requirement_text: Optional[str] = Field(None, min_length=10)
    requirement_rationale: Optional[str] = None
    requirement_type: Optional[str] = Field(None, pattern="^(functional|non_functional|performance|safety|security|interface|operational|design|implementation)$")
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(critical|high|medium|low)$")
    state: Optional[str] = Field(None, pattern="^(draft|review|approved|published|deprecated|cancelled)$")
    verification_method: Optional[str] = Field(None, pattern="^(test|analysis|inspection|demonstration|review)$")
    verification_criteria: Optional[str] = None
    verification_status: Optional[str] = Field(None, pattern="^(not_started|in_progress|passed|failed|waived)$")
    verification_results: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class RequirementResponse(BaseModel):
    """Response model for requirement data."""
    requirement_id: str
    project_id: str
    requirement_identifier: str
    requirement_title: str
    requirement_text: str
    requirement_rationale: Optional[str]
    requirement_type: str
    category: Optional[str]
    subcategory: Optional[str]
    priority: str
    state: str
    verification_method: Optional[str]
    verification_criteria: Optional[str]
    verification_status: str
    verification_results: Optional[str]
    verification_date: Optional[datetime]
    is_published: bool
    published_at: Optional[datetime]
    source_document_id: Optional[str]
    source_section: Optional[str]
    parent_requirement_id: Optional[str]
    derived_from_requirement_id: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    updated_by: Optional[str]
    updated_at: datetime
    version: int
    extraction_confidence: Optional[float]
    extraction_method: Optional[str]


class RequirementNote(BaseModel):
    """Model for requirement notes."""
    requirement_id: str
    note_text: str = Field(..., min_length=1)
    note_type: str = Field(default="general", pattern="^(general|issue|clarification|change_request|verification|review)$")
    visibility: str = Field(default="project", pattern="^(private|project|public)$")
    references_note_id: Optional[str] = None


class ExtractionJobCreate(BaseModel):
    """Model for creating a requirements extraction job."""
    job_name: str
    source_document_id: str
    config_name: Optional[str] = None  # Use existing config or create default
    extraction_type: str = Field(default="document", pattern="^(document|batch|manual)$")
    
    # Optional custom extraction configuration
    functional_keywords: Optional[List[str]] = None
    performance_keywords: Optional[List[str]] = None
    constraint_keywords: Optional[List[str]] = None
    requirement_patterns: Optional[List[str]] = None
    constraint_patterns: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extract_constraints: bool = True
    document_types: Optional[List[str]] = None
    section_filters: Optional[List[str]] = None


class DASReviewRequest(BaseModel):
    """Model for requesting DAS review of a requirement."""
    review_type: str = Field(default="improvement", pattern="^(improvement|validation|gap_analysis|consistency)$")
    include_context: bool = True
    focus_areas: Optional[List[str]] = None  # Specific areas to focus on


class RequirementsQueryParams(BaseModel):
    """Query parameters for requirements filtering and sorting."""
    requirement_type: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[str] = None
    verification_status: Optional[str] = None
    is_published: Optional[bool] = None
    source_document_id: Optional[str] = None
    parent_requirement_id: Optional[str] = None
    search: Optional[str] = None  # Text search in title/text/rationale
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None
    updated_since: Optional[datetime] = None
    min_confidence: Optional[float] = None
    
    # Sorting
    sort_by: str = Field(default="created_at", pattern="^(requirement_identifier|requirement_title|requirement_type|priority|state|verification_status|created_at|updated_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    
    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class ConstraintCreate(BaseModel):
    """Model for creating a new constraint."""
    constraint_type: str = Field(..., pattern="^(threshold|objective|kpc|kpp|design|interface|environmental|equation)$")
    constraint_name: str = Field(..., min_length=1, max_length=200)
    constraint_description: str = Field(..., min_length=1)
    value_type: str = Field(default="text", pattern="^(numeric|range|enumeration|boolean|text|equation)$")
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = Field(None, max_length=50)
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    range_unit: Optional[str] = Field(None, max_length=50)
    text_value: Optional[str] = None
    enumeration_values: Optional[List[str]] = None
    equation_expression: Optional[str] = None  # Mathematical expressions for equation constraints
    equation_parameters: Optional[dict] = None  # SysMLv2-lite parameter definitions from ontology
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")


class ConstraintUpdate(BaseModel):
    """Model for updating a constraint."""
    constraint_name: Optional[str] = Field(None, max_length=200)
    constraint_description: Optional[str] = None
    constraint_type: Optional[str] = Field(None, pattern="^(threshold|objective|kpc|kpp|design|interface|environmental|equation)$")
    value_type: Optional[str] = Field(None, pattern="^(numeric|range|enumeration|boolean|text|equation)$")
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = Field(None, max_length=50)
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    range_unit: Optional[str] = Field(None, max_length=50)
    text_value: Optional[str] = None
    enumeration_values: Optional[List[str]] = None
    equation_expression: Optional[str] = None  # Mathematical expressions for equation constraints
    equation_parameters: Optional[dict] = None  # SysMLv2-lite parameter definitions from ontology
    priority: Optional[str] = Field(None, pattern="^(critical|high|medium|low)$")


# =====================================
# DATABASE HELPER FUNCTIONS
# =====================================

def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService(Settings())

def get_file_storage_service() -> FileStorageService:
    """Get file storage service instance."""
    return FileStorageService(Settings())

def get_db_connection():
    """Get raw database connection for complex queries."""
    settings = Settings()
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

def build_requirements_query(params: RequirementsQueryParams, project_id: str) -> Tuple[str, List[Any]]:
    """Build SQL query and parameters for requirements filtering."""
    base_query = """
        SELECT 
            requirement_id,
            project_id,
            requirement_identifier,
            requirement_title,
            requirement_text,
            requirement_rationale,
            requirement_type,
            category,
            subcategory,
            priority,
            state,
            is_immutable,
            source_requirement_id,
            source_project_id,
            source_document_id,
            source_section,
            parent_requirement_id,
            derived_from_requirement_id,
            verification_method,
            verification_criteria,
            verification_status,
            verification_results,
            verification_date,
            is_published,
            published_at,
            published_by,
            tags,
            metadata,
            created_by,
            created_at,
            updated_by,
            updated_at,
            version,
            extraction_confidence,
            extraction_method,
            extraction_job_id,
            source_project_iri,
            source_namespace_path,
            source_namespace_prefix
        FROM requirements_enhanced
        WHERE project_id = %s
    """
    
    where_conditions = []
    query_params = [project_id]
    
    if params.requirement_type:
        where_conditions.append("requirement_type = %s")
        query_params.append(params.requirement_type)
    
    if params.category:
        where_conditions.append("category = %s")
        query_params.append(params.category)
    
    if params.state:
        where_conditions.append("state = %s")
        query_params.append(params.state)
    
    if params.priority:
        where_conditions.append("priority = %s")
        query_params.append(params.priority)
    
    if params.verification_status:
        where_conditions.append("verification_status = %s")
        query_params.append(params.verification_status)
    
    if params.is_published is not None:
        where_conditions.append("is_published = %s")
        query_params.append(params.is_published)
    
    if params.source_document_id:
        where_conditions.append("source_document_id = %s")
        query_params.append(params.source_document_id)
    
    if params.parent_requirement_id:
        where_conditions.append("parent_requirement_id = %s")
        query_params.append(params.parent_requirement_id)
    
    if params.search:
        search_condition = """(
            requirement_title ILIKE %s OR 
            requirement_text ILIKE %s OR 
            requirement_rationale ILIKE %s OR
            requirement_identifier ILIKE %s
        )"""
        where_conditions.append(search_condition)
        search_param = f"%{params.search}%"
        query_params.extend([search_param, search_param, search_param, search_param])
    
    if params.tags:
        # Check if any of the provided tags exist in the tags JSON array
        tag_conditions = []
        for tag in params.tags:
            tag_conditions.append("tags ? %s")
            query_params.append(tag)
        where_conditions.append(f"({' OR '.join(tag_conditions)})")
    
    if params.created_by:
        where_conditions.append("created_by::text = %s")
        query_params.append(params.created_by)
    
    if params.updated_since:
        where_conditions.append("updated_at >= %s")
        query_params.append(params.updated_since)
    
    if params.min_confidence:
        where_conditions.append("extraction_confidence >= %s")
        query_params.append(params.min_confidence)
    
    # Build final query
    if where_conditions:
        base_query += " AND " + " AND ".join(where_conditions)
    
    # Add sorting
    base_query += f" ORDER BY {params.sort_by} {params.sort_order.upper()}"
    
    # Add pagination
    base_query += " LIMIT %s OFFSET %s"
    query_params.append(params.page_size)
    query_params.append((params.page - 1) * params.page_size)
    
    return base_query, query_params

# =====================================
# REQUIREMENTS CRUD ENDPOINTS
# =====================================

@router.get("/projects/{project_id}/requirements", response_model=Dict[str, Any])
async def list_requirements(
    project_id: str,
    params: RequirementsQueryParams = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """List requirements for a project with filtering, sorting, and pagination."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check project access
            cursor.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                [project_id, current_user["user_id"]]
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this project"
                )
            
            # Build and execute query
            query, query_params = build_requirements_query(params, project_id)
            cursor.execute(query, query_params)
            requirements = cursor.fetchall()
            
            # Get total count for pagination
            count_query = """
                SELECT COUNT(*) as total
                FROM requirements_enhanced
                WHERE project_id = %s
            """
            count_params = [project_id]
            
            # Apply same filters for count (excluding pagination)
            if params.requirement_type:
                count_query += " AND requirement_type = %s"
                count_params.append(params.requirement_type)
            # ... add other filters as needed
            
            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()["total"]
            
            return {
                "requirements": [dict(req) for req in requirements],
                "pagination": {
                    "page": params.page,
                    "page_size": params.page_size,
                    "total_items": total_count,
                    "total_pages": (total_count + params.page_size - 1) // params.page_size
                },
                "filters_applied": {
                    "requirement_type": params.requirement_type,
                    "category": params.category,
                    "state": params.state,
                    "priority": params.priority,
                    "search": params.search
                }
            }
            
    except Exception as e:
        logger.error(f"Error listing requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list requirements: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/projects/{project_id}/requirements/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific requirement with full details."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT r.*, f.filename as source_document_name
                FROM requirements_enhanced r
                LEFT JOIN files f ON r.source_document_id = f.id
                WHERE r.project_id = %s AND r.requirement_id = %s
            """, [project_id, requirement_id])
            
            requirement = cursor.fetchone()
            if not requirement:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found"
                )
            
            return dict(requirement)
            
    except Exception as e:
        logger.error(f"Error getting requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get requirement: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/projects/{project_id}/requirements", response_model=RequirementResponse)
async def create_requirement(
    project_id: str,
    requirement: RequirementCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify project access
            cursor.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                [project_id, current_user["user_id"]]
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this project"
                )
            
            # Create requirement with auto-generated ID and identifier
            new_req_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO requirements_enhanced (
                    requirement_id,
                    project_id,
                    requirement_identifier,
                    requirement_title,
                    requirement_text,
                    requirement_rationale,
                    requirement_type,
                    category,
                    subcategory,
                    priority,
                    verification_method,
                    verification_criteria,
                    source_document_id,
                    source_section,
                    parent_requirement_id,
                    tags,
                    metadata,
                    created_by,
                    updated_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING *
            """, [
                new_req_id,
                project_id,
                requirement.requirement_identifier,
                requirement.requirement_title,
                requirement.requirement_text,
                requirement.requirement_rationale,
                requirement.requirement_type,
                requirement.category,
                requirement.subcategory,
                requirement.priority,
                requirement.verification_method,
                requirement.verification_criteria,
                requirement.source_document_id,
                requirement.source_section,
                requirement.parent_requirement_id,
                json.dumps(requirement.tags),
                json.dumps(requirement.metadata),
                current_user["user_id"],
                current_user["user_id"]
            ])
            
            created_requirement = cursor.fetchone()
            conn.commit()
            
            logger.info(f"Created requirement {created_requirement['requirement_identifier']} in project {project_id}")
            
            return dict(created_requirement)
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create requirement: {str(e)}"
        )
    finally:
        conn.close()


@router.put("/projects/{project_id}/requirements/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    project_id: str,
    requirement_id: str,
    requirement: RequirementUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if requirement exists and user has access
            cursor.execute(
                "SELECT * FROM requirements_enhanced WHERE project_id = %s AND requirement_id = %s",
                [project_id, requirement_id]
            )
            existing_req = cursor.fetchone()
            if not existing_req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found"
                )
            
            # Build dynamic update query
            update_fields = []
            update_values = []
            
            for field, value in requirement.dict(exclude_unset=True).items():
                if value is not None:
                    if field in ["tags", "metadata"]:
                        update_fields.append(f"{field} = %s")
                        update_values.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = %s")
                        update_values.append(value)
            
            if not update_fields:
                # No updates provided
                return dict(existing_req)
            
            # Add updated_by and updated_at
            update_fields.extend(["updated_by = %s", "updated_at = NOW()"])
            update_values.append(current_user["user_id"])
            
            # Execute update
            update_query = f"""
                UPDATE requirements_enhanced 
                SET {', '.join(update_fields)}
                WHERE project_id = %s AND requirement_id = %s
                RETURNING *
            """
            update_values.extend([project_id, requirement_id])
            
            cursor.execute(update_query, update_values)
            updated_requirement = cursor.fetchone()
            conn.commit()
            
            logger.info(f"Updated requirement {requirement_id} in project {project_id}")
            
            return dict(updated_requirement)
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update requirement: {str(e)}"
        )
    finally:
        conn.close()


@router.delete("/projects/{project_id}/requirements/{requirement_id}")
async def delete_requirement(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a requirement (soft delete by setting state to cancelled)."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if requirement exists
            cursor.execute(
                "SELECT requirement_identifier FROM requirements_enhanced WHERE project_id = %s AND requirement_id = %s",
                [project_id, requirement_id]
            )
            existing_req = cursor.fetchone()
            if not existing_req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found"
                )
            
            # Soft delete by setting state to cancelled
            cursor.execute("""
                UPDATE requirements_enhanced 
                SET state = 'cancelled', updated_by = %s, updated_at = NOW()
                WHERE project_id = %s AND requirement_id = %s
            """, [current_user["user_id"], project_id, requirement_id])
            
            conn.commit()
            
            logger.info(f"Deleted requirement {existing_req['requirement_identifier']} in project {project_id}")
            
            return {"message": "Requirement deleted successfully"}
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete requirement: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# REQUIREMENTS EXTRACTION ENDPOINTS
# =====================================

@router.post("/projects/{project_id}/extract", response_model=Dict[str, Any])
async def start_extraction_job(
    project_id: str,
    extraction_request: ExtractionJobCreate,
    current_user: dict = Depends(get_current_user),
    file_storage: FileStorageService = Depends(get_file_storage_service)
):
    """Start a requirements extraction job from a document."""
    
    conn = get_db_connection()
    extraction_engine = RequirementsExtractionEngine()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify project access
            cursor.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                [project_id, current_user["user_id"]]
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this project"
                )
            
            # Get document metadata
            cursor.execute(
                "SELECT * FROM files WHERE id = %s AND project_id = %s",
                [extraction_request.source_document_id, project_id]
            )
            document = cursor.fetchone()
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            # Create extraction job record
            job_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO requirements_extraction_jobs (
                    job_id, project_id, job_name, source_document_id,
                    extraction_type, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                job_id, project_id, extraction_request.job_name,
                extraction_request.source_document_id,
                extraction_request.extraction_type, "running",
                current_user["user_id"]
            ])
            
            # Update job status
            cursor.execute(
                "UPDATE requirements_extraction_jobs SET started_at = NOW(), status = 'running' WHERE job_id = %s",
                [job_id]
            )
            conn.commit()
            
            # Extract document text content using FileStorageService
            try:
                file_content_bytes = await file_storage.get_file_content(extraction_request.source_document_id)
                if file_content_bytes:
                    document_text = file_content_bytes.decode("utf-8")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Document has no extractable content"
                    )
            except Exception as e:
                logger.error(f"Failed to retrieve file content: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to retrieve document content: {str(e)}"
                )
            
            # Configure extraction
            config = ExtractionConfig()
            if extraction_request.functional_keywords:
                config.functional_keywords = extraction_request.functional_keywords
            if extraction_request.performance_keywords:
                config.performance_keywords = extraction_request.performance_keywords
            if extraction_request.constraint_keywords:
                config.constraint_keywords = extraction_request.constraint_keywords
            if extraction_request.min_confidence:
                config.min_confidence = extraction_request.min_confidence
            config.extract_constraints = extraction_request.extract_constraints
            
            # Perform extraction
            extraction_result = extraction_engine.extract_requirements_from_document(
                document_text=document_text,
                config=config,
                document_filename=document["filename"],
                project_id=project_id
            )
            
            # Store extracted requirements
            requirements_created = 0
            constraints_created = 0
            
            for req in extraction_result.requirements:
                if req.confidence >= config.min_confidence:
                    req_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO requirements_enhanced (
                            requirement_id, project_id, requirement_title, requirement_text,
                            requirement_type, category, subcategory, priority,
                            source_document_id, source_section,
                            extraction_confidence, extraction_method, extraction_job_id,
                            created_by, updated_by, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        req_id, project_id,
                        req.title or req.text[:100],
                        req.text,
                        req.requirement_type.value,
                        req.category,
                        req.subcategory,
                        req.priority,
                        extraction_request.source_document_id,
                        req.source_section,
                        req.confidence,
                        "ai_extraction",
                        job_id,
                        current_user["user_id"],
                        current_user["user_id"],
                        json.dumps(req.metadata)
                    ])
                    requirements_created += 1
                    
                    # Store associated constraints
                    for constraint in req.constraints:
                        constraint_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO requirements_constraints (
                                constraint_id, requirement_id, constraint_type,
                                constraint_name, constraint_description, value_type,
                                numeric_value, numeric_unit, text_value,
                                created_by
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            constraint_id, req_id, constraint.constraint_type.value,
                            constraint.name, constraint.description, constraint.value_type,
                            constraint.numeric_value, constraint.numeric_unit, constraint.text_value,
                            current_user["user_id"]
                        ])
                        constraints_created += 1
            
            # Update job completion status
            cursor.execute("""
                UPDATE requirements_extraction_jobs 
                SET status = 'completed', completed_at = NOW(),
                    requirements_found = %s, constraints_found = %s,
                    requirements_created = %s, constraints_created = %s,
                    processing_duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))
                WHERE job_id = %s
            """, [
                len(extraction_result.requirements),
                len(extraction_result.constraints),
                requirements_created,
                constraints_created,
                job_id
            ])
            
            conn.commit()
            
            logger.info(f"Extraction job {job_id} completed: {requirements_created} requirements, {constraints_created} constraints created")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "requirements_found": len(extraction_result.requirements),
                "constraints_found": len(extraction_result.constraints),
                "requirements_created": requirements_created,
                "constraints_created": constraints_created,
                "processing_stats": extraction_result.processing_stats
            }
            
    except Exception as e:
        conn.rollback()
        # Update job status to failed
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE requirements_extraction_jobs 
                    SET status = 'failed', error_message = %s, completed_at = NOW()
                    WHERE job_id = %s
                """, [str(e), job_id])
                conn.commit()
        except:
            pass
        
        logger.error(f"Error in extraction job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction job failed: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/projects/{project_id}/extraction-jobs", response_model=List[Dict[str, Any]])
async def list_extraction_jobs(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List requirements extraction jobs for a project."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ej.*, f.filename as document_name
                FROM requirements_extraction_jobs ej
                LEFT JOIN files f ON ej.source_document_id = f.id
                WHERE ej.project_id = %s
                ORDER BY ej.created_at DESC
            """, [project_id])
            
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]
            
    except Exception as e:
        logger.error(f"Error listing extraction jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list extraction jobs: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# DAS INTEGRATION ENDPOINTS
# =====================================

@router.post("/projects/{project_id}/requirements/{requirement_id}/das-review")
async def request_das_review(
    project_id: str,
    requirement_id: str,
    review_request: DASReviewRequest,
    current_user: dict = Depends(get_current_user),
    das_engine: DASCoreEngine = Depends(get_das_engine)
):
    """Request DAS AI review of a requirement with improvement suggestions."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get requirement details
            cursor.execute(
                "SELECT * FROM requirements_enhanced WHERE project_id = %s AND requirement_id = %s",
                [project_id, requirement_id]
            )
            requirement = cursor.fetchone()
            if not requirement:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found"
                )
            
            # Prepare DAS context
            context = {
                "requirement_text": requirement["requirement_text"],
                "requirement_type": requirement["requirement_type"],
                "category": requirement.get("category"),
                "priority": requirement["priority"],
                "verification_method": requirement.get("verification_method"),
                "review_type": review_request.review_type
            }
            
            if review_request.include_context:
                # Get related requirements for context
                cursor.execute("""
                    SELECT requirement_text, requirement_type 
                    FROM requirements_enhanced 
                    WHERE project_id = %s AND requirement_id != %s 
                    AND (category = %s OR parent_requirement_id = %s)
                    LIMIT 5
                """, [project_id, requirement_id, requirement.get("category"), requirement.get("parent_requirement_id")])
                related_reqs = cursor.fetchall()
                context["related_requirements"] = [dict(req) for req in related_reqs]
            
            # Create DAS review prompt based on review type
            if review_request.review_type == "improvement":
                prompt = f"""
                Please review this requirement and provide improvement suggestions:

                Requirement: {requirement['requirement_text']}
                Type: {requirement['requirement_type']}
                Category: {requirement.get('category', 'N/A')}
                
                Focus on:
                - Clarity and precision of language
                - Testability and verifiability  
                - Completeness of acceptance criteria
                - Proper use of modal verbs (shall, must, will)
                - Consistency with requirements engineering best practices
                
                Provide specific suggestions for improvement and a rewritten version if needed.
                """
            elif review_request.review_type == "validation":
                prompt = f"""
                Please validate this requirement against systems engineering best practices:

                Requirement: {requirement['requirement_text']}
                Type: {requirement['requirement_type']}
                
                Check for:
                - Proper requirement structure and syntax
                - Ambiguity or unclear language
                - Missing acceptance criteria
                - Appropriate level of detail
                - Consistency with requirement type classification
                
                Identify any issues and suggest corrections.
                """
            else:
                prompt = f"""
                Please analyze this requirement:

                Requirement: {requirement['requirement_text']}
                Type: {requirement['requirement_type']}
                Analysis Type: {review_request.review_type}
                
                Provide insights and recommendations for improvement.
                """
            
            # Execute DAS analysis using DAS2 streaming approach
            full_response = ""
            final_metadata = {}
            sources = []

            async for chunk in das_engine.process_message_stream(
                project_id=project_id,
                message=prompt,
                user_id=current_user["user_id"]
            ):
                if chunk.get("type") == "content":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "done":
                    final_metadata = chunk.get("metadata", {})
                    sources = final_metadata.get("sources", [])
                elif chunk.get("type") == "error":
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"DAS analysis failed: {chunk.get('message', 'Unknown error')}"
                    )

            # Parse DAS response to extract structured feedback
            response_text = full_response
            suggestions = []
            issues_found = []
            improvement_areas = []
            suggested_text = None
            
            # Simple parsing of DAS response - could be enhanced with NLP
            
            if "suggestion" in response_text.lower():
                # Extract suggestions (basic implementation)
                lines = response_text.split('\n')
                for line in lines:
                    if 'suggest' in line.lower() or 'recommend' in line.lower():
                        suggestions.append(line.strip())
            
            if "issue" in response_text.lower() or "problem" in response_text.lower():
                lines = response_text.split('\n')
                for line in lines:
                    if 'issue' in line.lower() or 'problem' in line.lower():
                        issues_found.append(line.strip())
            
            # Store DAS review
            review_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO requirements_das_reviews (
                    review_id, requirement_id, review_type, original_text,
                    suggested_text, das_confidence, improvement_areas,
                    issues_found, suggestions, review_context, reviewed_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                review_id, requirement_id, review_request.review_type,
                requirement["requirement_text"], suggested_text,
                0.8,  # Default confidence
                json.dumps(improvement_areas),
                json.dumps(issues_found),
                json.dumps(suggestions),
                json.dumps(context),
                current_user["user_id"]
            ])
            
            conn.commit()
            
            return {
                "review_id": review_id,
                "review_type": review_request.review_type,
                "das_response": response_text,
                "suggestions": suggestions,
                "issues_found": issues_found,
                "improvement_areas": improvement_areas,
                "sources": sources,
                "metadata": final_metadata,
                "confidence": 0.8
            }
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in DAS review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DAS review failed: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# NOTES AND COLLABORATION ENDPOINTS  
# =====================================

@router.post("/projects/{project_id}/requirements/{requirement_id}/notes")
async def create_requirement_note(
    project_id: str,
    requirement_id: str,
    note: RequirementNote,
    current_user: dict = Depends(get_current_user)
):
    """Add a note to a requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify requirement exists
            cursor.execute(
                "SELECT 1 FROM requirements_enhanced WHERE project_id = %s AND requirement_id = %s",
                [project_id, requirement_id]
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found"
                )
            
            # Create note
            note_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO requirements_notes (
                    note_id, requirement_id, note_text, note_type,
                    visibility, references_note_id, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, [
                note_id, requirement_id, note.note_text, note.note_type,
                note.visibility, note.references_note_id, current_user["user_id"]
            ])
            
            created_note = cursor.fetchone()
            conn.commit()
            
            return dict(created_note)
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating note: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/projects/{project_id}/requirements/{requirement_id}/notes")
async def list_requirement_notes(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List notes for a requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT n.*, u.display_name as created_by_name
                FROM requirements_notes n
                LEFT JOIN users u ON n.created_by = u.user_id
                WHERE n.requirement_id = %s 
                AND (n.visibility = 'public' OR n.visibility = 'project' OR n.created_by = %s)
                ORDER BY n.created_at ASC
            """, [requirement_id, current_user["user_id"]])
            
            notes = cursor.fetchall()
            return [dict(note) for note in notes]
            
    except Exception as e:
        logger.error(f"Error listing notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list notes: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# CONSTRAINTS MANAGEMENT ENDPOINTS
# =====================================

@router.get("/projects/{project_id}/requirements/{requirement_id}/constraints")
async def list_requirement_constraints(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List constraints for a specific requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify project access and requirement exists
            cursor.execute("""
                SELECT 1 FROM project_members pm
                JOIN requirements_enhanced re ON re.project_id = pm.project_id
                WHERE pm.project_id = %s AND pm.user_id = %s AND re.requirement_id = %s
            """, [project_id, current_user["user_id"], requirement_id])
            
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Requirement not found or access denied")
            
            # Get constraints for this requirement
            cursor.execute("""
                SELECT 
                    constraint_id, constraint_type, constraint_name, constraint_description,
                    value_type, numeric_value, numeric_unit, range_min, range_max, range_unit,
                    text_value, enumeration_values, equation_expression, equation_parameters, 
                    priority, source_document_id, created_at, updated_at, created_by
                FROM requirements_constraints
                WHERE requirement_id = %s
                ORDER BY priority DESC, constraint_type, constraint_name
            """, [requirement_id])
            
            constraints = cursor.fetchall()
            return [dict(constraint) for constraint in constraints]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing constraints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list constraints: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/projects/{project_id}/requirements/{requirement_id}/constraints")
async def create_requirement_constraint(
    project_id: str,
    requirement_id: str,
    constraint: ConstraintCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new constraint for a requirement."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify project access and requirement exists
            cursor.execute("""
                SELECT 1 FROM project_members pm
                JOIN requirements_enhanced re ON re.project_id = pm.project_id
                WHERE pm.project_id = %s AND pm.user_id = %s AND re.requirement_id = %s
            """, [project_id, current_user["user_id"], requirement_id])
            
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Requirement not found or access denied")
            
            # Create new constraint
            constraint_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO requirements_constraints (
                    constraint_id, requirement_id, constraint_type, constraint_name, constraint_description,
                    value_type, numeric_value, numeric_unit, range_min, range_max, range_unit,
                    text_value, enumeration_values, equation_expression, equation_parameters, priority, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, [
                constraint_id, requirement_id, constraint.constraint_type, constraint.constraint_name,
                constraint.constraint_description, constraint.value_type, constraint.numeric_value,
                constraint.numeric_unit, constraint.range_min, constraint.range_max, constraint.range_unit,
                constraint.text_value, 
                json.dumps(constraint.enumeration_values) if constraint.enumeration_values else None,
                constraint.equation_expression, 
                json.dumps(constraint.equation_parameters) if constraint.equation_parameters else None,
                constraint.priority, current_user["user_id"]
            ])
            
            created_constraint = cursor.fetchone()
            conn.commit()
            
            logger.info(f"Created constraint {created_constraint['constraint_name']} for requirement {requirement_id}")
            return dict(created_constraint)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating constraint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create constraint: {str(e)}"
        )
    finally:
        conn.close()


@router.put("/projects/{project_id}/requirements/{requirement_id}/constraints/{constraint_id}")
async def update_requirement_constraint(
    project_id: str,
    requirement_id: str,
    constraint_id: str,
    constraint: ConstraintUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing constraint."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify constraint exists and user has access
            cursor.execute("""
                SELECT rc.* FROM requirements_constraints rc
                JOIN requirements_enhanced re ON rc.requirement_id = re.requirement_id
                JOIN project_members pm ON re.project_id = pm.project_id
                WHERE rc.constraint_id = %s AND re.requirement_id = %s AND pm.project_id = %s AND pm.user_id = %s
            """, [constraint_id, requirement_id, project_id, current_user["user_id"]])
            
            existing_constraint = cursor.fetchone()
            if not existing_constraint:
                raise HTTPException(status_code=404, detail="Constraint not found or access denied")
            
            # Build update query
            update_fields = []
            update_values = []
            
            for field, value in constraint.dict(exclude_unset=True).items():
                if value is not None:
                    if field in ["enumeration_values", "equation_parameters"]:
                        update_fields.append(f"{field} = %s")
                        update_values.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = %s")
                        update_values.append(value)
            
            if not update_fields:
                # No updates provided
                return dict(existing_constraint)
            
            # Add updated_at
            update_fields.append("updated_at = NOW()")
            update_values.append(constraint_id)
            
            update_query = f"""
                UPDATE requirements_constraints 
                SET {', '.join(update_fields)}
                WHERE constraint_id = %s
                RETURNING *
            """
            
            cursor.execute(update_query, update_values)
            updated_constraint = cursor.fetchone()
            
            if not updated_constraint:
                raise HTTPException(status_code=404, detail="Failed to update constraint")
            
            conn.commit()
            logger.info(f"Updated constraint {updated_constraint['constraint_name']} for requirement {requirement_id}")
            
            return dict(updated_constraint)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating constraint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update constraint: {str(e)}"
        )
    finally:
        conn.close()


@router.delete("/projects/{project_id}/requirements/{requirement_id}/constraints/{constraint_id}")
async def delete_requirement_constraint(
    project_id: str,
    requirement_id: str,
    constraint_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a constraint."""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify constraint exists and user has access
            cursor.execute("""
                SELECT rc.constraint_name FROM requirements_constraints rc
                JOIN requirements_enhanced re ON rc.requirement_id = re.requirement_id
                JOIN project_members pm ON re.project_id = pm.project_id
                WHERE rc.constraint_id = %s AND re.requirement_id = %s AND pm.project_id = %s AND pm.user_id = %s
            """, [constraint_id, requirement_id, project_id, current_user["user_id"]])
            
            constraint = cursor.fetchone()
            if not constraint:
                raise HTTPException(status_code=404, detail="Constraint not found or access denied")
            
            # Delete the constraint
            cursor.execute("DELETE FROM requirements_constraints WHERE constraint_id = %s", [constraint_id])
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Constraint not found")
            
            conn.commit()
            logger.info(f"Deleted constraint {constraint['constraint_name']} from requirement {requirement_id}")
            
            return {"message": "Constraint deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting constraint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete constraint: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# PUBLISHING ENDPOINTS
# =====================================

class PublishRequirementRequest(BaseModel):
    """Model for publishing a requirement."""
    force: bool = Field(default=False, description="Force publish even if not approved")
    published_by: Optional[str] = None

class BatchPublishRequest(BaseModel):
    """Model for batch publishing requirements."""
    requirement_ids: List[str] = Field(..., min_items=1, max_items=50)
    force: bool = Field(default=False, description="Force publish even if not approved")
    published_by: Optional[str] = None

@router.post("/projects/{project_id}/requirements/{requirement_id}/publish")
async def publish_requirement(
    project_id: str,
    requirement_id: str,
    request: PublishRequirementRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish a single requirement.
    
    Publishing moves a requirement to 'published' state and sets publication metadata.
    Typically requires approval first unless force=True.
    """
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if requirement exists and user has access
            cursor.execute("""
                SELECT r.requirement_id, r.state, r.requirement_title, p.name
                FROM requirements_enhanced r
                JOIN projects p ON r.project_id = p.project_id
                WHERE r.requirement_id = %s AND r.project_id = %s
            """, (requirement_id, project_id))
            
            requirement = cursor.fetchone()
            if not requirement:
                raise HTTPException(status_code=404, detail="Requirement not found")
            
            # Validate publishing conditions
            if requirement['state'] not in ['approved', 'published'] and not request.force:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot publish requirement in '{requirement['state']}' state. Requirements must be 'approved' before publishing (use force=true to override)"
                )
            
            # Update requirement to published state
            now = datetime.now(timezone.utc)
            published_by_id = current_user.get('user_id')
            
            cursor.execute("""
                UPDATE requirements_enhanced 
                SET state = 'published',
                    is_published = true,
                    published_at = %s,
                    published_by = %s,
                    updated_at = %s,
                    updated_by = %s,
                    version = version + 1
                WHERE requirement_id = %s AND project_id = %s
                RETURNING requirement_identifier, requirement_title, state, published_at, published_by
            """, (now, published_by_id, now, current_user.get('user_id'), requirement_id, project_id))
            
            result = cursor.fetchone()
            conn.commit()
            
            logger.info(f"Published requirement {result['requirement_identifier']} by {current_user.get('username', 'unknown')}")
            
            return {
                "success": True,
                "message": f"Requirement {result['requirement_identifier']} published successfully",
                "requirement_id": requirement_id,
                "requirement_identifier": result['requirement_identifier'],
                "published_at": result['published_at'],
                "published_by": result['published_by']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish requirement: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/projects/{project_id}/requirements/{requirement_id}/unpublish")
async def unpublish_requirement(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Unpublish a requirement (revert to approved state).
    """
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if requirement exists and is published
            cursor.execute("""
                SELECT requirement_id, state, requirement_identifier
                FROM requirements_enhanced
                WHERE requirement_id = %s AND project_id = %s AND state = 'published'
            """, (requirement_id, project_id))
            
            requirement = cursor.fetchone()
            if not requirement:
                raise HTTPException(status_code=404, detail="Published requirement not found")
            
            # Revert to approved state
            now = datetime.now(timezone.utc)
            
            cursor.execute("""
                UPDATE requirements_enhanced 
                SET state = 'approved',
                    is_published = false,
                    published_at = NULL,
                    published_by = NULL,
                    updated_at = %s,
                    updated_by = %s,
                    version = version + 1
                WHERE requirement_id = %s AND project_id = %s
                RETURNING requirement_identifier, state
            """, (now, current_user.get('user_id'), requirement_id, project_id))
            
            result = cursor.fetchone()
            conn.commit()
            
            logger.info(f"Unpublished requirement {result['requirement_identifier']}")
            
            return {
                "success": True,
                "message": f"Requirement {result['requirement_identifier']} unpublished successfully",
                "requirement_id": requirement_id,
                "new_state": result['state']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unpublishing requirement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpublish requirement: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/projects/{project_id}/requirements/batch-publish")
async def batch_publish_requirements(
    project_id: str,
    request: BatchPublishRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish multiple requirements in a single operation.
    """
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            published_requirements = []
            skipped_requirements = []
            
            for req_id in request.requirement_ids:
                try:
                    # Check requirement state
                    cursor.execute("""
                        SELECT requirement_id, state, requirement_identifier, requirement_title
                        FROM requirements_enhanced
                        WHERE requirement_id = %s AND project_id = %s
                    """, (req_id, project_id))
                    
                    requirement = cursor.fetchone()
                    if not requirement:
                        skipped_requirements.append({
                            "requirement_id": req_id,
                            "reason": "Requirement not found"
                        })
                        continue
                    
                    # Validate publishing conditions
                    if requirement['state'] not in ['approved', 'published'] and not request.force:
                        skipped_requirements.append({
                            "requirement_id": req_id,
                            "requirement_identifier": requirement['requirement_identifier'],
                            "reason": f"Cannot publish requirement in '{requirement['state']}' state (use force=true to override)"
                        })
                        continue
                    
                    if requirement['state'] == 'published':
                        skipped_requirements.append({
                            "requirement_id": req_id,
                            "requirement_identifier": requirement['requirement_identifier'],
                            "reason": "Already published"
                        })
                        continue
                    
                    # Publish the requirement
                    now = datetime.now(timezone.utc)
                    published_by_id = current_user.get('user_id')
                    
                    cursor.execute("""
                        UPDATE requirements_enhanced 
                        SET state = 'published',
                            is_published = true,
                            published_at = %s,
                            published_by = %s,
                            updated_at = %s,
                            updated_by = %s,
                            version = version + 1
                        WHERE requirement_id = %s AND project_id = %s
                        RETURNING requirement_identifier, requirement_title
                    """, (now, published_by_id, now, current_user.get('user_id'), req_id, project_id))
                    
                    result = cursor.fetchone()
                    
                    published_requirements.append({
                        "requirement_id": req_id,
                        "requirement_identifier": result['requirement_identifier'],
                        "requirement_title": result['requirement_title'],
                        "published_at": now,
                        "published_by": current_user.get('username', 'unknown')
                    })
                    
                except Exception as e:
                    skipped_requirements.append({
                        "requirement_id": req_id,
                        "reason": f"Error: {str(e)}"
                    })
            
            conn.commit()
            
            logger.info(f"Batch published {len(published_requirements)} requirements, skipped {len(skipped_requirements)}")
            
            return {
                "success": True,
                "message": f"Published {len(published_requirements)} requirements, skipped {len(skipped_requirements)}",
                "published": published_requirements,
                "skipped": skipped_requirements,
                "summary": {
                    "total_requested": len(request.requirement_ids),
                    "published_count": len(published_requirements),
                    "skipped_count": len(skipped_requirements)
                }
            }
            
    except Exception as e:
        logger.error(f"Error in batch publish: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch publish requirements: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/projects/{project_id}/published-requirements")
async def list_published_requirements(
    project_id: str,
    target_project_id: str = Query(None, description="Target project ID to filter out already imported requirements"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    List all published requirements for a project, optionally filtering out those already imported in target project.
    """
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Build query to optionally filter out already imported requirements
            base_query = """
                SELECT requirement_id, requirement_identifier, requirement_title, 
                       requirement_type, priority, published_at, published_by,
                       verification_status, verification_method
                FROM requirements_enhanced
                WHERE project_id = %s AND state = 'published'
            """
            
            params = [project_id]
            
            # Filter out requirements already imported in target project
            if target_project_id:
                base_query += """
                    AND requirement_id NOT IN (
                        SELECT source_requirement_id 
                        FROM requirements_enhanced 
                        WHERE project_id = %s 
                        AND source_project_id = %s 
                        AND state = 'imported'
                        AND source_requirement_id IS NOT NULL
                    )
                """
                params.extend([target_project_id, project_id])
            
            base_query += " ORDER BY published_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(base_query, params)
            
            requirements = cursor.fetchall()
            
            # Get total count
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM requirements_enhanced
                WHERE project_id = %s AND state = 'published'
            """, (project_id,))
            
            total_count = cursor.fetchone()['total']
            
            return {
                "requirements": [dict(req) for req in requirements],
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(requirements) < total_count
                }
            }
            
    except Exception as e:
        logger.error(f"Error listing published requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list published requirements: {str(e)}"
        )
    finally:
        conn.close()


# =====================================
# IMPORT ENDPOINTS
# =====================================

class ImportRequirementsRequest(BaseModel):
    """Model for importing requirements from another project."""
    source_project_id: str = Field(..., description="Source project ID to import from")
    requirement_ids: List[str] = Field(..., min_items=1, max_items=50, description="List of requirement IDs to import")

@router.get("/projects/published-summary")
async def get_projects_with_published_requirements(
    current_user: dict = Depends(get_current_user)
) -> List[dict]:
    """Get summary of projects that have published requirements."""
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get projects with published requirements that user has access to
            cursor.execute("""
                SELECT DISTINCT p.project_id, p.name, COUNT(r.requirement_id) as published_count
                FROM projects p 
                JOIN project_members pm ON p.project_id = pm.project_id
                JOIN requirements_enhanced r ON p.project_id = r.project_id
                WHERE pm.user_id = %s 
                AND r.state = 'published'
                AND r.is_published = true
                GROUP BY p.project_id, p.name
                ORDER BY p.name
            """, (current_user["user_id"],))
            
            results = cursor.fetchall()
            
            projects = []
            for row in results:
                projects.append({
                    "project_id": row["project_id"],
                    "name": row["name"],
                    "published_count": row["published_count"]
                })
            
            return projects
            
    except Exception as e:
        logger.error(f"Error fetching projects with published requirements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")
    finally:
        conn.close()

@router.post("/projects/{project_id}/import")
async def import_requirements(
    project_id: str,
    import_request: ImportRequirementsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Import published requirements from another project, preserving original IDs and adding full traceability."""
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify user has access to target project
            cursor.execute("""
                SELECT 1 FROM project_members 
                WHERE project_id = %s AND user_id = %s
            """, (project_id, current_user["user_id"]))
            
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to target project")
            
            # Verify user has access to source project
            cursor.execute("""
                SELECT 1 FROM project_members 
                WHERE project_id = %s AND user_id = %s
            """, (import_request.source_project_id, current_user["user_id"]))
            
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to source project")
            
            # Get source project traceability information
            cursor.execute("""
                SELECT p.name, p.iri, p.namespace_id, nr.path as namespace_path, nr.prefix
                FROM projects p 
                LEFT JOIN namespace_registry nr ON p.namespace_id = nr.id
                WHERE p.project_id = %s
            """, (import_request.source_project_id,))
            
            source_project_info = cursor.fetchone()
            if not source_project_info:
                raise HTTPException(status_code=404, detail="Source project not found")
            
            imported_count = 0
            failed_imports = []
            
            for req_id in import_request.requirement_ids:
                try:
                    # Get the source requirement with complete details
                    cursor.execute("""
                        SELECT r.*
                        FROM requirements_enhanced r
                        WHERE r.requirement_id = %s 
                        AND r.project_id = %s 
                        AND r.state = 'published' 
                        AND r.is_published = true
                    """, (req_id, import_request.source_project_id))
                    
                    source_req = cursor.fetchone()
                    if not source_req:
                        failed_imports.append({"requirement_id": req_id, "reason": "Not found or not published"})
                        continue
                    
                    # Check if requirement with this ID already exists in target project
                    cursor.execute("""
                        SELECT requirement_id FROM requirements_enhanced 
                        WHERE project_id = %s AND requirement_id = %s
                    """, (project_id, req_id))
                    
                    if cursor.fetchone():
                        failed_imports.append({"requirement_id": req_id, "reason": "Requirement ID already exists in target project"})
                        continue
                    
                    # Check if this requirement was already imported from this source
                    cursor.execute("""
                        SELECT requirement_id FROM requirements_enhanced 
                        WHERE project_id = %s 
                        AND source_requirement_id = %s 
                        AND source_project_id = %s
                    """, (project_id, req_id, import_request.source_project_id))
                    
                    if cursor.fetchone():
                        failed_imports.append({"requirement_id": req_id, "reason": "Already imported from this source"})
                        continue
                    
                    # Generate prefixed identifier for traceability and conflict avoidance  
                    now = datetime.now(timezone.utc)
                    new_req_id = str(uuid.uuid4())  # New UUID for target project
                    original_identifier = source_req["requirement_identifier"]  # e.g., "REQ-001"
                    source_project_prefix = source_project_info["name"]  # e.g., "core.me"
                    prefixed_identifier = f"{source_project_prefix}.{original_identifier}"  # e.g., "core.me.REQ-001"
                    
                    cursor.execute("""
                        INSERT INTO requirements_enhanced (
                            requirement_id, project_id, requirement_identifier,
                            requirement_title, requirement_text, requirement_type,
                            priority, state, is_immutable, source_requirement_id, 
                            source_project_id, source_project_iri, source_namespace_path, source_namespace_prefix,
                            created_at, updated_at, created_by, updated_by,
                            version, requirement_rationale, verification_criteria, verification_method,
                            verification_status, tags, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        new_req_id, project_id, prefixed_identifier,
                        source_req["requirement_title"], source_req["requirement_text"], source_req["requirement_type"],
                        source_req["priority"], 'imported', True, req_id,
                        import_request.source_project_id, source_project_info["iri"], source_project_info["namespace_path"], source_project_info["prefix"],
                        now, now, current_user["user_id"], current_user["user_id"],
                        source_req["version"] or 1, source_req["requirement_rationale"] or '', source_req["verification_criteria"] or '', source_req["verification_method"] or 'review',
                        'not_started', json.dumps(source_req["tags"] or []), json.dumps(source_req["metadata"] or {})
                    ))
                    
                    # Import constraints preserving original constraint IDs
                    cursor.execute("""
                        SELECT * FROM requirements_constraints 
                        WHERE requirement_id = %s
                    """, (req_id,))
                    
                    constraints = cursor.fetchall()
                    for constraint in constraints:
                        # PRESERVE original constraint ID 
                        original_constraint_id = constraint["constraint_id"]
                        cursor.execute("""
                            INSERT INTO requirements_constraints (
                                constraint_id, requirement_id, constraint_type, constraint_name,
                                constraint_description, value_type, numeric_value, numeric_unit,
                                range_min, range_max, range_unit, text_value, enumeration_values,
                                measurement_method, tolerance, tolerance_unit, priority,
                                equation_expression, equation_parameters,
                                created_at, updated_at, created_by, updated_by
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            original_constraint_id, new_req_id, constraint["constraint_type"], constraint["constraint_name"], 
                            constraint["constraint_description"], constraint["value_type"], constraint["numeric_value"], 
                            constraint["numeric_unit"], constraint["range_min"], constraint["range_max"], 
                            constraint["range_unit"], constraint["text_value"], json.dumps(constraint["enumeration_values"]) if constraint["enumeration_values"] else None, 
                            constraint["measurement_method"], constraint["tolerance"], constraint["tolerance_unit"], 
                            constraint["priority"], constraint["equation_expression"], json.dumps(constraint["equation_parameters"]) if constraint["equation_parameters"] else None,
                            now, now, current_user["user_id"], current_user["user_id"]
                        ))
                    
                    # Log the import with full traceability
                    cursor.execute("""
                        INSERT INTO requirements_history (
                            history_id, requirement_id, change_type, changed_by, changed_at, old_value, new_value
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                            str(uuid.uuid4()), new_req_id, 'created',
                        current_user["user_id"], now,
                        json.dumps({
                            "source_requirement_id": req_id, 
                            "source_project": import_request.source_project_id,
                            "source_project_name": source_project_info["name"],
                            "source_namespace": source_project_info["namespace_path"]
                        }),
                        json.dumps({
                            "imported_id": original_identifier, 
                            "state": "imported",
                            "is_immutable": True,
                            "preserved_original_id": True
                        })
                    ))
                    
                    imported_count += 1
                    
                except Exception as import_error:
                    logger.error(f"Error importing requirement {req_id}: {import_error}")
                    failed_imports.append({"requirement_id": req_id, "reason": str(import_error)})
                    continue
            
            conn.commit()
            
            logger.info(f"Successfully imported {imported_count} requirements into project {project_id}")
            
            response = {
                "imported_count": imported_count,
                "total_requested": len(import_request.requirement_ids),
                "success": imported_count > 0
            }
            
            if failed_imports:
                response["failed_imports"] = failed_imports
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing requirements: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/projects/{project_id}/requirements/{requirement_id}/import")
async def unimport_requirement(
    project_id: str,
    requirement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove an imported requirement and its constraints from the current project."""
    db = get_db_service()
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify user has access to project
            cursor.execute("""
                SELECT 1 FROM project_members 
                WHERE project_id = %s AND user_id = %s
            """, (project_id, current_user["user_id"]))
            
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to project")
            
            # Verify the requirement exists, is imported, and is immutable
            cursor.execute("""
                SELECT r.requirement_identifier, r.requirement_title, r.state, r.is_immutable,
                       r.source_requirement_id, r.source_project_id, 
                       sp.name as source_project_name, r.source_namespace_path
                FROM requirements_enhanced r
                LEFT JOIN projects sp ON r.source_project_id = sp.project_id
                WHERE r.requirement_id = %s AND r.project_id = %s
            """, (requirement_id, project_id))
            
            requirement = cursor.fetchone()
            if not requirement:
                raise HTTPException(status_code=404, detail="Requirement not found")
            
            if requirement["state"] != "imported" or not requirement["is_immutable"]:
                raise HTTPException(status_code=400, detail="Only imported requirements can be un-imported")
            
            # Log the un-import action BEFORE deletion (to avoid FK constraint violation)
            now = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO requirements_history (
                    history_id, requirement_id, change_type, changed_by, changed_at, old_value, new_value
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                str(uuid.uuid4()), requirement_id, 'deprecated',
                current_user["user_id"], now,
                json.dumps({
                    "requirement_identifier": requirement["requirement_identifier"],
                    "requirement_title": requirement["requirement_title"],
                    "source_project": requirement["source_project_name"],
                    "source_namespace": requirement["source_namespace_path"]
                }),
                json.dumps({"reason": "Un-imported by user"})
            ))
            
            # Delete constraints first (due to foreign key constraints)
            cursor.execute("""
                DELETE FROM requirements_constraints 
                WHERE requirement_id = %s
            """, (requirement_id,))
            
            # Delete the imported requirement
            cursor.execute("""
                DELETE FROM requirements_enhanced 
                WHERE requirement_id = %s AND project_id = %s
            """, (requirement_id, project_id))
            
            conn.commit()
            
            logger.info(f"Successfully un-imported requirement {requirement['requirement_identifier']} from project {project_id}")
            
            return {
                "requirement_id": requirement_id,
                "requirement_identifier": requirement["requirement_identifier"],
                "requirement_title": requirement["requirement_title"],
                "source_project": requirement["source_project_name"],
                "message": f"Successfully un-imported requirement {requirement['requirement_identifier']}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error un-importing requirement: {e}")
        raise HTTPException(status_code=500, detail=f"Un-import failed: {str(e)}")
    finally:
        conn.close()
