"""
DAS Tool Registry Implementation

Implements ToolRegistryInterface to store and manage runtime-generated tools.
Stores successful generated tools in PostgreSQL for reuse by DAS.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .tool_registry_interface import (
    ToolRegistryInterface,
    ToolMetadata,
    ToolType,
)
from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class DASToolRegistry(ToolRegistryInterface):
    """
    Tool registry implementation using PostgreSQL.
    
    Stores dynamically generated tools for reuse, reducing the need to
    regenerate code for similar tasks.
    """
    
    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        """Initialize DAS tool registry."""
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
    
    async def store_tool(
        self,
        name: str,
        description: str,
        tool_type: ToolType,
        code: str,
        capabilities: List[str],
        created_by: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new tool in the database.
        
        Args:
            name: Tool name
            description: Tool description
            tool_type: Type of tool
            code: Generated code
            capabilities: List of capabilities
            created_by: Creator identifier
            tags: Optional tags
            metadata: Optional metadata
            
        Returns:
            Tool ID string
        """
        tool_id = str(uuid4())
        conn = self.db_service._conn()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO das_runtime_tools
                    (tool_id, name, description, tool_type, code, capabilities,
                     created_by, tags, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                """, (
                    tool_id,
                    name,
                    description,
                    tool_type.value,
                    code,
                    capabilities,
                    created_by,
                    tags or [],
                    json.dumps(metadata or {}),
                ))
                conn.commit()
            
            logger.info(f"Stored tool '{name}' (ID: {tool_id})")
            return tool_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store tool: {e}")
            raise
        finally:
            self.db_service._return(conn)
    
    async def find_tool(
        self,
        tool_id: Optional[str] = None,
        name: Optional[str] = None,
        tool_type: Optional[ToolType] = None,
        capability: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> List[ToolMetadata]:
        """
        Find tools matching criteria.
        
        Args:
            tool_id: Specific tool ID
            name: Tool name (partial match)
            tool_type: Filter by tool type
            capability: Filter by capability
            tags: Filter by tags (all must match)
            created_by: Filter by creator
            
        Returns:
            List of matching ToolMetadata objects
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Build query dynamically based on filters
                conditions = ["is_active = TRUE"]
                params = []
                
                if tool_id:
                    conditions.append("tool_id = %s")
                    params.append(tool_id)
                
                if name:
                    conditions.append("LOWER(name) LIKE %s")
                    params.append(f"%{name.lower()}%")
                
                if tool_type:
                    conditions.append("tool_type = %s")
                    params.append(tool_type.value)
                
                if capability:
                    conditions.append("%s = ANY(capabilities)")
                    params.append(capability)
                
                if tags:
                    for tag in tags:
                        conditions.append("%s = ANY(tags)")
                        params.append(tag)
                
                if created_by:
                    conditions.append("created_by = %s")
                    params.append(created_by)
                
                query = f"""
                    SELECT 
                        tool_id, name, description, tool_type, code, capabilities,
                        created_by, created_at, usage_count, last_used_at, tags, metadata
                    FROM das_runtime_tools
                    WHERE {' AND '.join(conditions)}
                    ORDER BY usage_count DESC, created_at DESC
                """
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                tools = []
                for row in rows:
                    tool_id, name, description, tool_type_str, code, capabilities, \
                    created_by, created_at, usage_count, last_used_at, tags, metadata = row
                    
                    tool_type = ToolType(tool_type_str)
                    
                    tool = ToolMetadata(
                        tool_id=str(tool_id),
                        name=name,
                        description=description or "",
                        tool_type=tool_type,
                        code=code,
                        capabilities=capabilities or [],
                        created_at=created_at,
                        created_by=created_by,
                        usage_count=usage_count or 0,
                        last_used_at=last_used_at,
                        tags=tags or [],
                        metadata=metadata or {},
                    )
                    tools.append(tool)
                
                return tools
        finally:
            self.db_service._return(conn)
    
    async def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """
        Get a specific tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            ToolMetadata if found, None otherwise
        """
        tools = await self.find_tool(tool_id=tool_id)
        return tools[0] if tools else None
    
    async def update_tool(
        self,
        tool_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update tool metadata.
        
        Args:
            tool_id: Tool identifier
            name: New name (optional)
            description: New description (optional)
            code: New code (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if updated, False if not found
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                
                if code is not None:
                    updates.append("code = %s")
                    params.append(code)
                
                if tags is not None:
                    updates.append("tags = %s")
                    params.append(tags)
                
                if metadata is not None:
                    updates.append("metadata = metadata || %s::jsonb")
                    params.append(json.dumps(metadata))
                
                if not updates:
                    return False
                
                updates.append("updated_at = NOW()")
                params.append(tool_id)
                
                query = f"""
                    UPDATE das_runtime_tools
                    SET {', '.join(updates)}
                    WHERE tool_id = %s AND is_active = TRUE
                """
                
                cur.execute(query, params)
                conn.commit()
                
                return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update tool {tool_id}: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def update_usage(
        self,
        tool_id: str,
        increment: int = 1
    ) -> bool:
        """
        Update tool usage statistics.
        
        Args:
            tool_id: Tool identifier
            increment: Usage count increment (default: 1)
            
        Returns:
            True if updated, False if not found
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE das_runtime_tools
                    SET 
                        usage_count = usage_count + %s,
                        last_used_at = NOW(),
                        updated_at = NOW()
                    WHERE tool_id = %s AND is_active = TRUE
                """, (increment, tool_id))
                conn.commit()
                
                return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update usage for tool {tool_id}: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool (soft delete by setting is_active = FALSE).
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            True if deleted, False if not found
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE das_runtime_tools
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE tool_id = %s
                """, (tool_id,))
                conn.commit()
                
                return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete tool {tool_id}: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def list_tools(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[ToolMetadata]:
        """
        List tools with pagination.
        
        Args:
            limit: Maximum number of tools to return
            offset: Offset for pagination
            sort_by: Field to sort by (created_at, usage_count, name)
            sort_order: Sort order (asc, desc)
            
        Returns:
            List of ToolMetadata objects
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Validate sort_by
                valid_sort_fields = {
                    "created_at": "created_at",
                    "usage_count": "usage_count",
                    "name": "name",
                    "last_used_at": "last_used_at",
                }
                sort_field = valid_sort_fields.get(sort_by, "created_at")
                sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
                
                cur.execute(f"""
                    SELECT 
                        tool_id, name, description, tool_type, code, capabilities,
                        created_by, created_at, usage_count, last_used_at, tags, metadata
                    FROM das_runtime_tools
                    WHERE is_active = TRUE
                    ORDER BY {sort_field} {sort_dir}
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                
                rows = cur.fetchall()
                
                tools = []
                for row in rows:
                    tool_id, name, description, tool_type_str, code, capabilities, \
                    created_by, created_at, usage_count, last_used_at, tags, metadata = row
                    
                    tool_type = ToolType(tool_type_str)
                    
                    tool = ToolMetadata(
                        tool_id=str(tool_id),
                        name=name,
                        description=description or "",
                        tool_type=tool_type,
                        code=code,
                        capabilities=capabilities or [],
                        created_at=created_at,
                        created_by=created_by,
                        usage_count=usage_count or 0,
                        last_used_at=last_used_at,
                        tags=tags or [],
                        metadata=metadata or {},
                    )
                    tools.append(tool)
                
                return tools
        finally:
            self.db_service._return(conn)
    
    async def get_popular_tools(
        self,
        limit: int = 10
    ) -> List[ToolMetadata]:
        """
        Get most popular tools by usage count.
        
        Args:
            limit: Maximum number of tools to return
            
        Returns:
            List of ToolMetadata objects sorted by usage count
        """
        return await self.list_tools(
            limit=limit,
            offset=0,
            sort_by="usage_count",
            sort_order="desc"
        )
