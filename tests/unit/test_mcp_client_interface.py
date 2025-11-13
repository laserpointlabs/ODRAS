"""
Unit tests for MCPClientInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from unittest.mock import Mock, AsyncMock

from backend.services.mcp_client_interface import (
    MCPClientInterface,
    MCPServerInfo,
    MCPServerStatus,
    MCPTool,
    MCPCallResult,
)


class ConcreteMCPClient(MCPClientInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._servers = {}
        self._tools = {}
    
    async def discover_servers(self, refresh=False):
        """Discover servers."""
        return list(self._servers.values())
    
    async def get_server_info(self, server_id_or_name):
        """Get server info."""
        return self._servers.get(server_id_or_name)
    
    async def call_tool(self, tool_name, arguments, server_id_or_name=None):
        """Call tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return MCPCallResult(
                tool_name=tool_name,
                server_name="unknown",
                result=None,
                success=False,
                error="Tool not found",
            )
        
        return MCPCallResult(
            tool_name=tool_name,
            server_name=tool.server_name,
            result={"result": "success"},
        )
    
    async def get_capabilities(self, server_id_or_name=None):
        """Get capabilities."""
        return {"test_server": ["capability1", "capability2"]}
    
    async def list_tools(self, server_id_or_name=None, capability_filter=None):
        """List tools."""
        return list(self._tools.values())
    
    async def register_server(self, name, endpoint, description=None, metadata=None):
        """Register server."""
        server_id = f"server_{name}"
        server = MCPServerInfo(
            server_id=server_id,
            name=name,
            description=description or "",
            endpoint=endpoint,
            status=MCPServerStatus.AVAILABLE,
            capabilities=[],
            tools=[],
            metadata=metadata,
        )
        self._servers[server_id] = server
        self._servers[name] = server
        return server_id
    
    async def unregister_server(self, server_id_or_name):
        """Unregister server."""
        if server_id_or_name in self._servers:
            del self._servers[server_id_or_name]
            return True
        return False
    
    async def get_server_status(self, server_id_or_name):
        """Get server status."""
        server = self._servers.get(server_id_or_name)
        if server:
            return server.status
        return MCPServerStatus.UNKNOWN


class TestMCPClientInterface:
    """Test MCPClientInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MCPClientInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        client = ConcreteMCPClient()
        assert isinstance(client, MCPClientInterface)
        assert isinstance(client, ABC)
    
    @pytest.mark.asyncio
    async def test_discover_servers(self):
        """Test discovering servers."""
        client = ConcreteMCPClient()
        
        servers = await client.discover_servers()
        
        assert isinstance(servers, list)
    
    @pytest.mark.asyncio
    async def test_register_server(self):
        """Test registering a server."""
        client = ConcreteMCPClient()
        
        server_id = await client.register_server(
            name="test_server",
            endpoint="http://localhost:8000/mcp",
            description="Test MCP server",
        )
        
        assert server_id is not None
        
        server = await client.get_server_info("test_server")
        assert server is not None
        assert server.name == "test_server"
    
    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling a tool."""
        client = ConcreteMCPClient()
        
        # Register a tool
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            server_name="test_server",
        )
        client._tools["test_tool"] = tool
        
        result = await client.call_tool("test_tool", {})
        
        assert result.success is True
        assert result.tool_name == "test_tool"
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self):
        """Test getting capabilities."""
        client = ConcreteMCPClient()
        
        capabilities = await client.get_capabilities()
        
        assert isinstance(capabilities, dict)
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        client = ConcreteMCPClient()
        
        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={},
            server_name="test_server",
        )
        client._tools["test_tool"] = tool
        
        tools = await client.list_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
    
    @pytest.mark.asyncio
    async def test_unregister_server(self):
        """Test unregistering a server."""
        client = ConcreteMCPClient()
        
        server_id = await client.register_server("test", "http://localhost")
        unregistered = await client.unregister_server(server_id)
        
        assert unregistered is True
        
        server = await client.get_server_info(server_id)
        assert server is None
    
    @pytest.mark.asyncio
    async def test_get_server_status(self):
        """Test getting server status."""
        client = ConcreteMCPClient()
        
        server_id = await client.register_server("test", "http://localhost")
        status = await client.get_server_status(server_id)
        
        assert isinstance(status, MCPServerStatus)
        assert status == MCPServerStatus.AVAILABLE


class TestMCPTool:
    """Test MCPTool."""
    
    def test_create_tool(self):
        """Test creating a tool."""
        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={"type": "object"},
            server_name="test_server",
        )
        
        assert tool.name == "test_tool"
        assert tool.server_name == "test_server"
    
    def test_tool_to_dict(self):
        """Test converting tool to dictionary."""
        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={},
            server_name="test_server",
        )
        
        data = tool.to_dict()
        assert data["name"] == "test_tool"


class TestMCPServerInfo:
    """Test MCPServerInfo."""
    
    def test_create_server_info(self):
        """Test creating server info."""
        server = MCPServerInfo(
            server_id="server-1",
            name="Test Server",
            description="Test",
            endpoint="http://localhost:8000",
            status=MCPServerStatus.AVAILABLE,
            capabilities=["cap1"],
            tools=[],
        )
        
        assert server.server_id == "server-1"
        assert server.status == MCPServerStatus.AVAILABLE
    
    def test_server_info_to_dict(self):
        """Test converting server info to dictionary."""
        server = MCPServerInfo(
            server_id="server-1",
            name="Test",
            description="Test",
            endpoint="http://localhost",
            status=MCPServerStatus.AVAILABLE,
            capabilities=[],
            tools=[],
        )
        
        data = server.to_dict()
        assert data["server_id"] == "server-1"
        assert data["status"] == "available"


class TestMCPCallResult:
    """Test MCPCallResult."""
    
    def test_create_result(self):
        """Test creating a call result."""
        result = MCPCallResult(
            tool_name="test_tool",
            server_name="test_server",
            result={"data": "test"},
        )
        
        assert result.success is True
        assert result.tool_name == "test_tool"
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = MCPCallResult(
            tool_name="test_tool",
            server_name="test_server",
            result="success",
        )
        
        data = result.to_dict()
        assert data["tool_name"] == "test_tool"
        assert data["success"] is True
