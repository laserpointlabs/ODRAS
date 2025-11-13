"""
Tool Registry Interface

Abstract interface for storing and managing runtime-generated tools.
Enables DAS to store, retrieve, and track usage of dynamically generated code tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class ToolType(Enum):
    """Types of tools that can be registered."""
    DATA_FETCHER = "data_fetcher"  # Tools for fetching data
    CALCULATOR = "calculator"  # Tools for calculations
    TRANSFORMER = "transformer"  # Tools for data transformation
    WORKFLOW = "workflow"  # Tools for workflow automation
    KNOWLEDGE_CREATOR = "knowledge_creator"  # Tools for creating knowledge
    CUSTOM = "custom"  # Custom tools


class ToolMetadata:
    """Metadata for a registered tool."""
    
    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        tool_type: ToolType,
        code: str,
        capabilities: List[str],
        created_at: datetime,
        created_by: str,
        usage_count: int = 0,
        last_used_at: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize tool metadata.
        
        Args:
            tool_id: Unique tool identifier
            name: Human-readable tool name
            description: Tool description
            tool_type: Type of tool
            code: Generated code for the tool
            capabilities: List of capabilities this tool provides
            created_at: Creation timestamp
            created_by: User/entity that created the tool
            usage_count: Number of times tool has been used
            last_used_at: Last usage timestamp
            tags: Optional tags for categorization
            metadata: Additional metadata
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.code = code
        self.capabilities = capabilities
        self.created_at = created_at
        self.created_by = created_by
        self.usage_count = usage_count
        self.last_used_at = last_used_at
        self.tags = tags or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "code": self.code,
            "capabilities": self.capabilities,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }


class ToolRegistryInterface(ABC):
    """
    Abstract interface for tool storage and management.
    
    Enables DAS to:
    - Store dynamically generated tools
    - Retrieve tools by various criteria
    - Track tool usage
    - Update tool metadata
    """
    
    @abstractmethod
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
        Store a new tool.
        
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """
        Get a specific tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            ToolMetadata if found, None otherwise
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
