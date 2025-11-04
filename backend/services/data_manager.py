"""
Workbench Data Manager

Centralized service for workbench data access, providing:
- Unified query interface for all workbenches
- Standardized filtering, sorting, and pagination
- Transaction management
- Error handling and validation
- Caching where appropriate
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy import text
import json

from backend.services.db import DatabaseService
from backend.services.config import Settings
from backend.schemas.workbench_data import (
    WorkbenchType,
    WorkbenchQueryRequest,
    WorkbenchQueryResponse,
    WorkbenchCreateRequest,
    WorkbenchUpdateRequest,
    WorkbenchDeleteRequest,
    WorkbenchOperationResponse,
    FilterCriteria,
    FilterOperator,
    SortCriteria,
    SortOrder,
    PaginationParams,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)


class WorkbenchDataManager:
    """
    Centralized data manager for all workbench operations.
    
    Provides a unified interface for:
    - Querying workbench data with filtering, sorting, pagination
    - Creating, updating, and deleting workbench items
    - Managing transactions
    - Handling errors consistently
    """
    
    def __init__(self, db_service: DatabaseService, settings: Settings):
        """
        Initialize the data manager.
        
        Args:
            db_service: Database service instance
            settings: Application settings
        """
        self.db = db_service
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Workbench-specific query builders
        self._query_builders = {
            WorkbenchType.REQUIREMENTS: self._build_requirements_query,
            WorkbenchType.INDIVIDUALS: self._build_individuals_query,
            WorkbenchType.FILES: self._build_files_query,
            WorkbenchType.KNOWLEDGE: self._build_knowledge_query,
        }
    
    async def query_workbench_data(
        self,
        request: WorkbenchQueryRequest,
        user_id: str
    ) -> WorkbenchQueryResponse:
        """
        Query workbench data with filtering, sorting, and pagination.
        
        Args:
            request: Query request with filters, sort, pagination
            user_id: User ID for access control
            
        Returns:
            Query response with paginated data
        """
        try:
            # Validate project access
            if not await self._verify_project_access(request.project_id, user_id):
                raise ValueError(f"Access denied to project {request.project_id}")
            
            # Get query builder for workbench type
            query_builder = self._query_builders.get(request.workbench_type)
            if not query_builder:
                raise ValueError(f"Unsupported workbench type: {request.workbench_type}")
            
            # Build and execute query
            query, count_query, params = query_builder(request, user_id)
            
            # Execute count query for total
            total_count = await self._execute_count_query(count_query, params)
            
            # Execute data query
            items = await self._execute_data_query(query, params)
            
            # Calculate pagination metadata
            total_pages = (total_count + request.pagination.page_size - 1) // request.pagination.page_size
            has_next = request.pagination.page < total_pages
            has_previous = request.pagination.page > 1
            
            paginated_data = PaginatedResponse(
                items=items,
                total_count=total_count,
                page=request.pagination.page,
                page_size=request.pagination.page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous
            )
            
            return WorkbenchQueryResponse(
                success=True,
                data=paginated_data,
                metadata={"workbench_type": request.workbench_type.value} if request.include_metadata else None,
                message=None
            )
            
        except Exception as e:
            self.logger.error(f"Error querying workbench data: {e}", exc_info=True)
            return WorkbenchQueryResponse(
                success=False,
                data=PaginatedResponse(items=[], total_count=0, page=1, page_size=20, total_pages=0, has_next=False, has_previous=False),
                message=f"Query failed: {str(e)}"
            )
    
    async def create_workbench_item(
        self,
        request: WorkbenchCreateRequest,
        user_id: str
    ) -> WorkbenchOperationResponse:
        """
        Create a new workbench item.
        
        Args:
            request: Create request with data
            user_id: User ID creating the item
            
        Returns:
            Operation response with item ID
        """
        try:
            # Validate project access
            if not await self._verify_project_access(request.project_id, user_id):
                raise ValueError(f"Access denied to project {request.project_id}")
            
            # Route to workbench-specific create handler
            item_id = await self._create_item_by_type(request, user_id)
            
            return WorkbenchOperationResponse(
                success=True,
                item_id=item_id,
                message=f"Item created successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error creating workbench item: {e}", exc_info=True)
            return WorkbenchOperationResponse(
                success=False,
                error=str(e)
            )
    
    async def update_workbench_item(
        self,
        request: WorkbenchUpdateRequest,
        user_id: str
    ) -> WorkbenchOperationResponse:
        """
        Update an existing workbench item.
        
        Args:
            request: Update request with data
            user_id: User ID updating the item
            
        Returns:
            Operation response
        """
        try:
            # Validate project access
            if not await self._verify_project_access(request.project_id, user_id):
                raise ValueError(f"Access denied to project {request.project_id}")
            
            # Route to workbench-specific update handler
            await self._update_item_by_type(request, user_id)
            
            return WorkbenchOperationResponse(
                success=True,
                item_id=request.item_id,
                message=f"Item updated successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating workbench item: {e}", exc_info=True)
            return WorkbenchOperationResponse(
                success=False,
                error=str(e)
            )
    
    async def delete_workbench_item(
        self,
        request: WorkbenchDeleteRequest,
        user_id: str
    ) -> WorkbenchOperationResponse:
        """
        Delete a workbench item.
        
        Args:
            request: Delete request
            user_id: User ID deleting the item
            
        Returns:
            Operation response
        """
        try:
            # Validate project access
            if not await self._verify_project_access(request.project_id, user_id):
                raise ValueError(f"Access denied to project {request.project_id}")
            
            # Route to workbench-specific delete handler
            await self._delete_item_by_type(request, user_id)
            
            return WorkbenchOperationResponse(
                success=True,
                item_id=request.item_id,
                message=f"Item deleted successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error deleting workbench item: {e}", exc_info=True)
            return WorkbenchOperationResponse(
                success=False,
                error=str(e)
            )
    
    # =====================================
    # INTERNAL HELPER METHODS
    # =====================================
    
    async def _verify_project_access(self, project_id: str, user_id: str) -> bool:
        """Verify user has access to the project"""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM project_members
                    WHERE project_id = %s AND user_id = %s
                """, (project_id, user_id))
                return cur.fetchone() is not None
        finally:
            self.db._return(conn)
    
    def _build_requirements_query(
        self,
        request: WorkbenchQueryRequest,
        user_id: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Build SQL query for requirements workbench"""
        base_query = """
            SELECT r.*, u.username as created_by_username
            FROM requirements r
            LEFT JOIN users u ON r.created_by = u.user_id
            WHERE r.project_id = %(project_id)s
        """
        
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS subquery"
        
        # Apply filters
        where_conditions = ["r.project_id = %(project_id)s"]
        params = {"project_id": request.project_id}
        
        for i, filter_crit in enumerate(request.filters):
            condition, param_name = self._build_filter_condition(filter_crit, f"filter_{i}")
            where_conditions.append(condition)
            params[param_name] = filter_crit.value
        
        # Apply search query
        if request.search_query:
            where_conditions.append(
                "(r.requirement_title ILIKE %(search)s OR r.requirement_text ILIKE %(search)s)"
            )
            params["search"] = f"%{request.search_query}%"
        
        # Build WHERE clause
        where_clause = " AND ".join(where_conditions)
        base_query = base_query.replace("WHERE r.project_id = %(project_id)s", f"WHERE {where_clause}")
        
        # Apply sorting
        order_by = []
        if request.sort:
            for sort_crit in request.sort:
                order_by.append(f"r.{sort_crit.field} {sort_crit.order.value.upper()}")
        else:
            order_by.append("r.updated_at DESC")  # Default sort
        
        order_clause = f"ORDER BY {', '.join(order_by)}"
        
        # Apply pagination
        offset = (request.pagination.page - 1) * request.pagination.page_size
        limit_clause = f"LIMIT {request.pagination.page_size} OFFSET {offset}"
        
        final_query = f"{base_query} {order_clause} {limit_clause}"
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS subquery"
        
        return final_query, count_query, params
    
    def _build_individuals_query(
        self,
        request: WorkbenchQueryRequest,
        user_id: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Build SQL query for individuals workbench"""
        # Placeholder - implement based on individuals table structure
        raise NotImplementedError("Individuals query builder not yet implemented")
    
    def _build_files_query(
        self,
        request: WorkbenchQueryRequest,
        user_id: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Build SQL query for files workbench"""
        base_query = """
            SELECT f.*, u.username as uploaded_by_username
            FROM files f
            LEFT JOIN users u ON f.uploaded_by = u.user_id
            WHERE f.project_id = %(project_id)s
        """
        
        where_conditions = ["f.project_id = %(project_id)s"]
        params = {"project_id": request.project_id}
        
        # Apply filters
        for i, filter_crit in enumerate(request.filters):
            condition, param_name = self._build_filter_condition(filter_crit, f"filter_{i}")
            where_conditions.append(condition)
            params[param_name] = filter_crit.value
        
        # Apply search
        if request.search_query:
            where_conditions.append("f.filename ILIKE %(search)s")
            params["search"] = f"%{request.search_query}%"
        
        where_clause = " AND ".join(where_conditions)
        base_query = base_query.replace("WHERE f.project_id = %(project_id)s", f"WHERE {where_clause}")
        
        # Sorting
        order_by = []
        if request.sort:
            for sort_crit in request.sort:
                order_by.append(f"f.{sort_crit.field} {sort_crit.order.value.upper()}")
        else:
            order_by.append("f.uploaded_at DESC")
        
        order_clause = f"ORDER BY {', '.join(order_by)}"
        
        # Pagination
        offset = (request.pagination.page - 1) * request.pagination.page_size
        limit_clause = f"LIMIT {request.pagination.page_size} OFFSET {offset}"
        
        final_query = f"{base_query} {order_clause} {limit_clause}"
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS subquery"
        
        return final_query, count_query, params
    
    def _build_knowledge_query(
        self,
        request: WorkbenchQueryRequest,
        user_id: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Build SQL query for knowledge workbench"""
        # Placeholder - implement based on knowledge_assets table structure
        raise NotImplementedError("Knowledge query builder not yet implemented")
    
    def _build_filter_condition(self, filter_crit: FilterCriteria, param_prefix: str) -> Tuple[str, str]:
        """Build SQL WHERE condition from filter criteria"""
        field = filter_crit.field
        operator = filter_crit.operator
        param_name = f"{param_prefix}_{field}"
        
        if operator == FilterOperator.EQUALS:
            return f"{field} = %({param_name})s", param_name
        elif operator == FilterOperator.NOT_EQUALS:
            return f"{field} != %({param_name})s", param_name
        elif operator == FilterOperator.CONTAINS:
            return f"{field} ILIKE %({param_name})s", param_name.replace("_", "_")
        elif operator == FilterOperator.STARTS_WITH:
            return f"{field} ILIKE %({param_name})s", param_name.replace("_", "_")
        elif operator == FilterOperator.ENDS_WITH:
            return f"{field} ILIKE %({param_name})s", param_name.replace("_", "_")
        elif operator == FilterOperator.GREATER_THAN:
            return f"{field} > %({param_name})s", param_name
        elif operator == FilterOperator.LESS_THAN:
            return f"{field} < %({param_name})s", param_name
        elif operator == FilterOperator.IN:
            return f"{field} = ANY(%({param_name})s)", param_name
        elif operator == FilterOperator.IS_NULL:
            return f"{field} IS NULL", param_name
        elif operator == FilterOperator.IS_NOT_NULL:
            return f"{field} IS NOT NULL", param_name
        else:
            raise ValueError(f"Unsupported filter operator: {operator}")
    
    async def _execute_count_query(self, query: str, params: Dict[str, Any]) -> int:
        """Execute count query and return total count"""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                return result[0] if result else 0
        finally:
            self.db._return(conn)
    
    async def _execute_data_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute data query and return results"""
        import psycopg2.extras
        conn = self.db._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            self.db._return(conn)
    
    async def _create_item_by_type(self, request: WorkbenchCreateRequest, user_id: str) -> str:
        """Route create request to workbench-specific handler"""
        if request.workbench_type == WorkbenchType.REQUIREMENTS:
            return await self._create_requirement(request, user_id)
        elif request.workbench_type == WorkbenchType.FILES:
            return await self._create_file(request, user_id)
        else:
            raise ValueError(f"Create not implemented for workbench type: {request.workbench_type}")
    
    async def _update_item_by_type(self, request: WorkbenchUpdateRequest, user_id: str) -> None:
        """Route update request to workbench-specific handler"""
        if request.workbench_type == WorkbenchType.REQUIREMENTS:
            await self._update_requirement(request, user_id)
        elif request.workbench_type == WorkbenchType.FILES:
            await self._update_file(request, user_id)
        else:
            raise ValueError(f"Update not implemented for workbench type: {request.workbench_type}")
    
    async def _delete_item_by_type(self, request: WorkbenchDeleteRequest, user_id: str) -> None:
        """Route delete request to workbench-specific handler"""
        if request.workbench_type == WorkbenchType.REQUIREMENTS:
            await self._delete_requirement(request, user_id)
        elif request.workbench_type == WorkbenchType.FILES:
            await self._delete_file(request, user_id)
        else:
            raise ValueError(f"Delete not implemented for workbench type: {request.workbench_type}")
    
    # Workbench-specific CRUD handlers (simplified - can be expanded)
    async def _create_requirement(self, request: WorkbenchCreateRequest, user_id: str) -> str:
        """Create a requirement"""
        import uuid
        requirement_id = str(uuid.uuid4())
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO requirements (
                        requirement_id, project_id, requirement_identifier,
                        requirement_title, requirement_text, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    requirement_id,
                    request.project_id,
                    request.data.get("requirement_identifier"),
                    request.data.get("requirement_title"),
                    request.data.get("requirement_text"),
                    user_id
                ))
                conn.commit()
                return requirement_id
        finally:
            self.db._return(conn)
    
    async def _update_requirement(self, request: WorkbenchUpdateRequest, user_id: str) -> None:
        """Update a requirement"""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                # Build dynamic UPDATE query based on provided data
                set_clauses = []
                params = []
                for key, value in request.data.items():
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
                
                params.append(request.item_id)
                params.append(request.project_id)
                
                query = f"""
                    UPDATE requirements
                    SET {', '.join(set_clauses)}, updated_at = NOW()
                    WHERE requirement_id = %s AND project_id = %s
                """
                cur.execute(query, params)
                conn.commit()
        finally:
            self.db._return(conn)
    
    async def _delete_requirement(self, request: WorkbenchDeleteRequest, user_id: str) -> None:
        """Delete a requirement"""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                if request.cascade:
                    # Delete related items (e.g., constraints, notes)
                    cur.execute("""
                        DELETE FROM requirement_constraints
                        WHERE requirement_id = %s
                    """, (request.item_id,))
                
                cur.execute("""
                    DELETE FROM requirements
                    WHERE requirement_id = %s AND project_id = %s
                """, (request.item_id, request.project_id))
                conn.commit()
        finally:
            self.db._return(conn)
    
    async def _create_file(self, request: WorkbenchCreateRequest, user_id: str) -> str:
        """Create a file record"""
        raise NotImplementedError("File creation via data manager not yet implemented")
    
    async def _update_file(self, request: WorkbenchUpdateRequest, user_id: str) -> None:
        """Update a file record"""
        raise NotImplementedError("File update via data manager not yet implemented")
    
    async def _delete_file(self, request: WorkbenchDeleteRequest, user_id: str) -> None:
        """Delete a file record"""
        raise NotImplementedError("File deletion via data manager not yet implemented")


def get_data_manager(db_service: DatabaseService, settings: Settings) -> WorkbenchDataManager:
    """Get or create data manager instance"""
    return WorkbenchDataManager(db_service, settings)
