"""
Workbench Data Schemas

Pydantic models for standardized data exchange between workbenches and the backend.
Provides common data structures for all workbench operations.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# =====================================
# COMMON ENUMS
# =====================================

class WorkbenchType(str, Enum):
    """Supported workbench types"""
    PROJECT = "project"
    ONTOLOGY = "ontology"
    CONCEPTUALIZER = "conceptualizer"
    FILES = "files"
    KNOWLEDGE = "knowledge"
    REQUIREMENTS = "requirements"
    GRAPH = "graph"
    RAG = "rag"
    PROCESS = "process"
    THREAD = "thread"
    PLAYGROUND = "playground"
    ANALYSIS = "analysis"
    SETTINGS = "settings"
    ADMIN = "admin"
    EVENTS = "events"


class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    """Filter operators for data queries"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


# =====================================
# COMMON REQUEST/RESPONSE MODELS
# =====================================

class FilterCriteria(BaseModel):
    """Filter criteria for querying data"""
    field: str = Field(..., description="Field name to filter on")
    operator: FilterOperator = Field(FilterOperator.EQUALS, description="Filter operator")
    value: Union[str, int, float, bool, List[Any]] = Field(..., description="Filter value(s)")
    
    @validator('value')
    def validate_value(cls, v, values):
        """Validate value matches operator requirements"""
        operator = values.get('operator')
        if operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
            if not isinstance(v, list):
                raise ValueError(f"Operator {operator} requires a list value")
        return v


class SortCriteria(BaseModel):
    """Sort criteria for querying data"""
    field: str = Field(..., description="Field name to sort on")
    order: SortOrder = Field(SortOrder.ASC, description="Sort order")


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")


class WorkbenchQueryRequest(BaseModel):
    """Generic query request for workbench data"""
    project_id: str = Field(..., description="Project ID to query")
    workbench_type: WorkbenchType = Field(..., description="Type of workbench")
    filters: List[FilterCriteria] = Field(default_factory=list, description="Filter criteria")
    sort: List[SortCriteria] = Field(default_factory=list, description="Sort criteria")
    pagination: PaginationParams = Field(default_factory=PaginationParams, description="Pagination parameters")
    search_query: Optional[str] = Field(None, description="Full-text search query")
    include_metadata: bool = Field(False, description="Include metadata in response")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Dict[str, Any]] = Field(..., description="List of items")
    total_count: int = Field(..., description="Total number of items (before pagination)")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class WorkbenchQueryResponse(BaseModel):
    """Generic query response for workbench data"""
    success: bool = Field(True, description="Whether the query succeeded")
    data: PaginatedResponse = Field(..., description="Paginated data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    message: Optional[str] = Field(None, description="Optional message")


class WorkbenchCreateRequest(BaseModel):
    """Generic create request for workbench data"""
    project_id: str = Field(..., description="Project ID")
    workbench_type: WorkbenchType = Field(..., description="Type of workbench")
    data: Dict[str, Any] = Field(..., description="Data to create")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class WorkbenchUpdateRequest(BaseModel):
    """Generic update request for workbench data"""
    project_id: str = Field(..., description="Project ID")
    workbench_type: WorkbenchType = Field(..., description="Type of workbench")
    item_id: str = Field(..., description="ID of item to update")
    data: Dict[str, Any] = Field(..., description="Data to update")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class WorkbenchDeleteRequest(BaseModel):
    """Generic delete request for workbench data"""
    project_id: str = Field(..., description="Project ID")
    workbench_type: WorkbenchType = Field(..., description="Type of workbench")
    item_id: str = Field(..., description="ID of item to delete")
    cascade: bool = Field(False, description="Whether to cascade delete related items")


class WorkbenchOperationResponse(BaseModel):
    """Generic operation response (create/update/delete)"""
    success: bool = Field(..., description="Whether the operation succeeded")
    item_id: Optional[str] = Field(None, description="ID of affected item")
    message: Optional[str] = Field(None, description="Optional message")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# =====================================
# WORKBENCH-SPECIFIC MODELS
# =====================================

class RequirementsWorkbenchData(BaseModel):
    """Requirements workbench specific data structure"""
    requirement_id: str
    project_id: str
    requirement_identifier: str
    requirement_title: str
    requirement_text: str
    requirement_type: str
    priority: str
    state: str
    verification_method: Optional[str] = None
    verification_status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndividualsWorkbenchData(BaseModel):
    """Individuals workbench specific data structure"""
    individual_id: str
    project_id: str
    class_name: str
    individual_name: str
    graph_iri: Optional[str] = None
    uri: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    created_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OntologyWorkbenchData(BaseModel):
    """Ontology workbench specific data structure"""
    ontology_id: str
    project_id: str
    graph_iri: str
    label: str
    reference: Optional[str] = None
    imported_from: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FilesWorkbenchData(BaseModel):
    """Files workbench specific data structure"""
    file_id: str
    project_id: str
    filename: str
    file_type: str
    file_size: int
    mime_type: Optional[str] = None
    storage_path: str
    status: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    uploaded_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeWorkbenchData(BaseModel):
    """Knowledge workbench specific data structure"""
    asset_id: str
    project_id: str
    asset_name: str
    asset_type: str
    source_file_id: Optional[str] = None
    content_summary: Optional[str] = None
    chunk_count: int
    total_tokens: int
    is_public: bool
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =====================================
# WORKBENCH METADATA
# =====================================

class WorkbenchMetadata(BaseModel):
    """Metadata about a workbench"""
    workbench_type: WorkbenchType
    display_name: str
    description: str
    supported_operations: List[str] = Field(default_factory=list, description="e.g., ['create', 'read', 'update', 'delete']")
    supported_filters: List[str] = Field(default_factory=list, description="Field names that can be filtered")
    supported_sorts: List[str] = Field(default_factory=list, description="Field names that can be sorted")
    default_sort: Optional[SortCriteria] = None
    default_page_size: int = 20
    max_page_size: int = 100


class WorkbenchRegistry(BaseModel):
    """Registry of all available workbenches"""
    workbenches: List[WorkbenchMetadata] = Field(default_factory=list)
    
    def get_workbench(self, workbench_type: WorkbenchType) -> Optional[WorkbenchMetadata]:
        """Get metadata for a specific workbench"""
        for wb in self.workbenches:
            if wb.workbench_type == workbench_type:
                return wb
        return None
