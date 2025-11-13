"""
MCP Client Interface

Abstract interface for Model Context Protocol (MCP) operations.
Enables DAS to discover and interact with MCP servers for specialized operations.

MCP (Model Context Protocol) is a standardized protocol for exposing tools
and data to LLMs, allowing dynamic discovery and execution of domain-specific operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class MCPServerStatus(Enum):
    """Status of an MCP server."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    UNKNOWN = "unknown"


class MCPTool:
    """Represents an MCP tool capability."""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP tool.
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool inputs
            server_name: Name of MCP server providing this tool
            metadata: Additional metadata
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name,
            "metadata": self.metadata,
        }


class MCPServerInfo:
    """Information about an MCP server."""
    
    def __init__(
        self,
        server_id: str,
        name: str,
        description: str,
        endpoint: str,
        status: MCPServerStatus,
        capabilities: List[str],
        tools: List[MCPTool],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP server info.
        
        Args:
            server_id: Unique server identifier
            name: Server name
            description: Server description
            endpoint: Server endpoint URL
            status: Server status
            capabilities: List of server capabilities
            tools: List of available tools
            metadata: Additional metadata
        """
        self.server_id = server_id
        self.name = name
        self.description = description
        self.endpoint = endpoint
        self.status = status
        self.capabilities = capabilities
        self.tools = tools
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_id": self.server_id,
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "tools": [tool.to_dict() for tool in self.tools],
            "metadata": self.metadata,
        }


class MCPCallResult:
    """Result from calling an MCP tool."""
    
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        result: Any,
        success: bool = True,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP call result.
        
        Args:
            tool_name: Name of tool that was called
            server_name: Name of server that executed the tool
            result: Tool execution result
            success: Whether call was successful
            error: Error message if call failed
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata
        """
        self.tool_name = tool_name
        self.server_name = server_name
        self.result = result
        self.success = success
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class MCPClientInterface(ABC):
    """
    Abstract interface for MCP client operations.
    
    Enables DAS to discover and interact with MCP servers for specialized
    domain operations (ontology queries, project events, knowledge assets, etc.).
    """
    
    @abstractmethod
    async def discover_servers(self, refresh: bool = False) -> List[MCPServerInfo]:
        """
        Discover available MCP servers.
        
        Args:
            refresh: Force refresh of server list (ignore cache)
            
        Returns:
            List of discovered MCP server information
        """
        pass
    
    @abstractmethod
    async def get_server_info(self, server_id_or_name: str) -> Optional[MCPServerInfo]:
        """
        Get information about a specific MCP server.
        
        Args:
            server_id_or_name: Server ID or name
            
        Returns:
            MCPServerInfo if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_id_or_name: Optional[str] = None,
    ) -> MCPCallResult:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments (must match tool's input schema)
            server_id_or_name: Optional server ID/name (auto-discover if not provided)
            
        Returns:
            MCPCallResult with execution result
        """
        pass
    
    @abstractmethod
    async def get_capabilities(self, server_id_or_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get capabilities of MCP servers.
        
        Args:
            server_id_or_name: Optional server ID/name (all servers if not provided)
            
        Returns:
            Dictionary mapping server names to their capabilities
        """
        pass
    
    @abstractmethod
    async def list_tools(
        self,
        server_id_or_name: Optional[str] = None,
        capability_filter: Optional[str] = None,
    ) -> List[MCPTool]:
        """
        List available MCP tools.
        
        Args:
            server_id_or_name: Optional server ID/name (all servers if not provided)
            capability_filter: Optional capability to filter by
            
        Returns:
            List of available MCP tools
        """
        pass
    
    @abstractmethod
    async def register_server(
        self,
        name: str,
        endpoint: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a new MCP server.
        
        Args:
            name: Server name
            endpoint: Server endpoint URL
            description: Optional server description
            metadata: Optional metadata
            
        Returns:
            Server ID string
        """
        pass
    
    @abstractmethod
    async def unregister_server(self, server_id_or_name: str) -> bool:
        """
        Unregister an MCP server.
        
        Args:
            server_id_or_name: Server ID or name
            
        Returns:
            True if unregistered, False if not found
        """
        pass
    
    @abstractmethod
    async def get_server_status(self, server_id_or_name: str) -> MCPServerStatus:
        """
        Get status of an MCP server.
        
        Args:
            server_id_or_name: Server ID or name
            
        Returns:
            MCPServerStatus enum value
        """
        pass
