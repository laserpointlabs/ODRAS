"""
DAS MCP Client Implementation

Implements MCPClientInterface for discovering and interacting with MCP servers.
Supports flexible MCP server registration and discovery for domain-specific operations.

MCP servers can be registered by admins/SMEs for specialized operations like:
- Ontology queries
- Project events
- Knowledge assets
- Requirements analysis
- Custom domain operations
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx
import time

from .mcp_client_interface import (
    MCPClientInterface,
    MCPServerInfo,
    MCPServerStatus,
    MCPTool,
    MCPCallResult,
)
from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class DASMCPClient(MCPClientInterface):
    """
    DAS MCP client implementation.
    
    Discovers and interacts with MCP servers for specialized domain operations.
    Supports flexible server registration and caching of server capabilities.
    """
    
    def __init__(
        self,
        settings: Settings,
        db_service: Optional[DatabaseService] = None,
    ):
        """
        Initialize MCP client.
        
        Args:
            settings: Application settings
            db_service: Optional database service
        """
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
        self._server_cache: Dict[str, MCPServerInfo] = {}
        self._tool_cache: Dict[str, MCPTool] = {}
    
    async def discover_servers(self, refresh: bool = False) -> List[MCPServerInfo]:
        """
        Discover available MCP servers.
        
        Args:
            refresh: Force refresh (ignore cache)
            
        Returns:
            List of discovered MCP server information
        """
        if not refresh and self._server_cache:
            return list(self._server_cache.values())
        
        # Load from database
        servers = await self._load_servers_from_db()
        
        # Discover capabilities for each server
        discovered_servers = []
        for server in servers:
            try:
                # Try to discover server capabilities
                server_info = await self._discover_server_capabilities(server)
                discovered_servers.append(server_info)
                self._server_cache[server_info.server_id] = server_info
                self._server_cache[server_info.name] = server_info
            except Exception as e:
                logger.warning(f"Failed to discover capabilities for server {server['name']}: {e}")
                # Still add server but mark as unavailable
                server_info = MCPServerInfo(
                    server_id=server['server_id'],
                    name=server['name'],
                    description=server['description'],
                    endpoint=server['endpoint'],
                    status=MCPServerStatus.UNAVAILABLE,
                    capabilities=server.get('capabilities', []),
                    tools=[],
                    metadata=server.get('metadata', {}),
                )
                discovered_servers.append(server_info)
        
        return discovered_servers
    
    async def _load_servers_from_db(self) -> List[Dict[str, Any]]:
        """Load MCP servers from database."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        server_id, name, description, endpoint, server_type,
                        capabilities, tools_cache, status, metadata
                    FROM das_mcp_servers
                    WHERE is_active = TRUE
                    ORDER BY name ASC
                """)
                
                rows = cur.fetchall()
                servers = []
                for row in rows:
                    server_id, name, description, endpoint, server_type, \
                    capabilities, tools_cache, status, metadata = row
                    
                    servers.append({
                        "server_id": str(server_id),
                        "name": name,
                        "description": description,
                        "endpoint": endpoint,
                        "server_type": server_type,
                        "capabilities": capabilities or [],
                        "tools_cache": tools_cache or {},
                        "status": status,
                        "metadata": metadata or {},
                    })
                
                return servers
        except Exception as e:
            logger.error(f"Failed to load MCP servers from database: {e}")
            return []
        finally:
            self.db_service._return(conn)
    
    async def _discover_server_capabilities(self, server: Dict[str, Any]) -> MCPServerInfo:
        """
        Discover capabilities of an MCP server.
        
        Args:
            server: Server dictionary from database
            
        Returns:
            MCPServerInfo with discovered capabilities
        """
        endpoint = server['endpoint']
        
        try:
            # Try to call MCP discovery endpoint
            # Standard MCP protocol: POST /mcp/discover or GET /mcp/capabilities
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try discovery endpoint
                try:
                    response = await client.get(f"{endpoint}/mcp/capabilities")
                    if response.status_code == 200:
                        data = response.json()
                        capabilities = data.get("capabilities", [])
                        tools_data = data.get("tools", [])
                        
                        tools = []
                        for tool_data in tools_data:
                            tool = MCPTool(
                                name=tool_data.get("name", ""),
                                description=tool_data.get("description", ""),
                                input_schema=tool_data.get("input_schema", {}),
                                server_name=server['name'],
                                metadata=tool_data.get("metadata", {}),
                            )
                            tools.append(tool)
                            self._tool_cache[f"{server['name']}:{tool.name}"] = tool
                        
                        status = MCPServerStatus.AVAILABLE
                    else:
                        # Server exists but discovery failed
                        capabilities = server.get('capabilities', [])
                        tools = []
                        status = MCPServerStatus.UNAVAILABLE
                except httpx.RequestError:
                    # Server not reachable
                    capabilities = server.get('capabilities', [])
                    tools = []
                    status = MCPServerStatus.UNAVAILABLE
        except Exception as e:
            logger.warning(f"Error discovering server {server['name']}: {e}")
            capabilities = server.get('capabilities', [])
            tools = []
            status = MCPServerStatus.UNAVAILABLE
        
        return MCPServerInfo(
            server_id=server['server_id'],
            name=server['name'],
            description=server['description'],
            endpoint=server['endpoint'],
            status=status,
            capabilities=capabilities,
            tools=tools,
            metadata=server.get('metadata', {}),
        )
    
    async def get_server_info(self, server_id_or_name: str) -> Optional[MCPServerInfo]:
        """Get information about a specific MCP server."""
        # Check cache first
        if server_id_or_name in self._server_cache:
            return self._server_cache[server_id_or_name]
        
        # Discover servers if cache is empty
        await self.discover_servers()
        
        return self._server_cache.get(server_id_or_name)
    
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
            arguments: Tool arguments
            server_id_or_name: Optional server ID/name
            
        Returns:
            MCPCallResult with execution result
        """
        start_time = time.time()
        
        # Find tool
        tool = None
        server_info = None
        
        if server_id_or_name:
            server_info = await self.get_server_info(server_id_or_name)
            if server_info:
                for t in server_info.tools:
                    if t.name == tool_name:
                        tool = t
                        break
        else:
            # Search all servers for tool
            servers = await self.discover_servers()
            for server in servers:
                for t in server.tools:
                    if t.name == tool_name:
                        tool = t
                        server_info = server
                        break
                if tool:
                    break
        
        if not tool or not server_info:
            return MCPCallResult(
                tool_name=tool_name,
                server_name=server_id_or_name or "unknown",
                result=None,
                success=False,
                error=f"Tool '{tool_name}' not found",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Call tool via MCP protocol
        try:
            endpoint = server_info.endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Standard MCP protocol: POST /mcp/tools/{tool_name}/call
                response = await client.post(
                    f"{endpoint}/mcp/tools/{tool_name}/call",
                    json={"arguments": arguments},
                    headers={"Content-Type": "application/json"},
                )
                
                response.raise_for_status()
                result_data = response.json()
                
                execution_time = (time.time() - start_time) * 1000
                
                return MCPCallResult(
                    tool_name=tool_name,
                    server_name=server_info.name,
                    result=result_data.get("result"),
                    success=True,
                    execution_time_ms=execution_time,
                    metadata=result_data.get("metadata", {}),
                )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"MCP tool call failed for {tool_name}: {e}")
            
            return MCPCallResult(
                tool_name=tool_name,
                server_name=server_info.name if server_info else "unknown",
                result=None,
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    async def get_capabilities(self, server_id_or_name: Optional[str] = None) -> Dict[str, Any]:
        """Get capabilities of MCP servers."""
        if server_id_or_name:
            server_info = await self.get_server_info(server_id_or_name)
            if server_info:
                return {
                    server_info.name: {
                        "capabilities": server_info.capabilities,
                        "tools": [t.name for t in server_info.tools],
                    }
                }
            return {}
        
        # Get all servers
        servers = await self.discover_servers()
        capabilities = {}
        for server in servers:
            capabilities[server.name] = {
                "capabilities": server.capabilities,
                "tools": [t.name for t in server.tools],
            }
        
        return capabilities
    
    async def list_tools(
        self,
        server_id_or_name: Optional[str] = None,
        capability_filter: Optional[str] = None,
    ) -> List[MCPTool]:
        """List available MCP tools."""
        if server_id_or_name:
            server_info = await self.get_server_info(server_id_or_name)
            if server_info:
                tools = server_info.tools
                if capability_filter:
                    tools = [
                        t for t in tools
                        if capability_filter in server_info.capabilities
                    ]
                return tools
            return []
        
        # Get all tools from all servers
        servers = await self.discover_servers()
        all_tools = []
        for server in servers:
            if capability_filter:
                if capability_filter in server.capabilities:
                    all_tools.extend(server.tools)
            else:
                all_tools.extend(server.tools)
        
        return all_tools
    
    async def register_server(
        self,
        name: str,
        endpoint: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Register a new MCP server."""
        import uuid
        server_id = str(uuid.uuid4())
        conn = self.db_service._conn()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO das_mcp_servers
                    (server_id, name, description, endpoint, metadata, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, NOW())
                """, (
                    server_id,
                    name,
                    description or "",
                    endpoint,
                    json.dumps(metadata or {}),
                    "system",  # TODO: Get actual user from context
                ))
                conn.commit()
            
            logger.info(f"Registered MCP server '{name}' (ID: {server_id})")
            
            # Clear cache to force refresh
            self._server_cache.clear()
            
            return server_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to register MCP server: {e}")
            raise
        finally:
            self.db_service._return(conn)
    
    async def unregister_server(self, server_id_or_name: str) -> bool:
        """Unregister an MCP server."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try UUID first, then name
                try:
                    UUID(server_id_or_name)
                    cur.execute("""
                        UPDATE das_mcp_servers
                        SET is_active = FALSE, updated_at = NOW()
                        WHERE server_id = %s
                    """, (server_id_or_name,))
                except ValueError:
                    cur.execute("""
                        UPDATE das_mcp_servers
                        SET is_active = FALSE, updated_at = NOW()
                        WHERE name = %s
                    """, (server_id_or_name,))
                
                conn.commit()
                success = cur.rowcount > 0
                
                if success:
                    # Remove from cache
                    if server_id_or_name in self._server_cache:
                        del self._server_cache[server_id_or_name]
                
                return success
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to unregister MCP server: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def get_server_status(self, server_id_or_name: str) -> MCPServerStatus:
        """Get status of an MCP server."""
        server_info = await self.get_server_info(server_id_or_name)
        if server_info:
            return server_info.status
        return MCPServerStatus.UNKNOWN
