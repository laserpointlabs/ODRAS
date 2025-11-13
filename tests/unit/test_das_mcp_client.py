"""
Unit tests for DASMCPClient.

Tests MCP client with mocked servers.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from backend.services.das_mcp_client import DASMCPClient
from backend.services.mcp_client_interface import MCPServerStatus, MCPTool, MCPCallResult
from backend.services.config import Settings


@pytest.fixture
def settings():
    """Create settings instance."""
    return Settings()


@pytest.fixture
def mcp_client(settings):
    """Create MCP client."""
    return DASMCPClient(settings)


class TestDASMCPClient:
    """Test DASMCPClient."""
    
    @pytest.mark.asyncio
    async def test_discover_servers(self, mcp_client):
        """Test discovering servers."""
        with patch.object(mcp_client, '_load_servers_from_db', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []
            
            servers = await mcp_client.discover_servers()
            
            assert isinstance(servers, list)
    
    @pytest.mark.asyncio
    async def test_get_server_info(self, mcp_client):
        """Test getting server info."""
        # Mock server cache
        from backend.services.mcp_client_interface import MCPServerInfo
        
        mock_server = MCPServerInfo(
            server_id="server-1",
            name="Test Server",
            description="Test",
            endpoint="http://localhost:8000",
            status=MCPServerStatus.AVAILABLE,
            capabilities=[],
            tools=[],
        )
        mcp_client._server_cache["server-1"] = mock_server
        
        server = await mcp_client.get_server_info("server-1")
        
        assert server is not None
        assert server.name == "Test Server"
    
    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mcp_client):
        """Test calling a non-existent tool."""
        result = await mcp_client.call_tool("nonexistent_tool", {})
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, mcp_client):
        """Test getting capabilities."""
        with patch.object(mcp_client, 'discover_servers', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = []
            
            capabilities = await mcp_client.get_capabilities()
            
            assert isinstance(capabilities, dict)
    
    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_client):
        """Test listing tools."""
        with patch.object(mcp_client, 'discover_servers', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = []
            
            tools = await mcp_client.list_tools()
            
            assert isinstance(tools, list)
    
    @pytest.mark.asyncio
    async def test_register_server(self, mcp_client):
        """Test registering a server."""
        with patch.object(mcp_client.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            server_id = await mcp_client.register_server(
                name="test_server",
                endpoint="http://localhost:8000/mcp",
                description="Test server",
            )
            
            assert server_id is not None
    
    @pytest.mark.asyncio
    async def test_unregister_server(self, mcp_client):
        """Test unregistering a server."""
        with patch.object(mcp_client.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            mock_cursor.rowcount = 1
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            unregistered = await mcp_client.unregister_server("test_server")
            
            assert unregistered is True
    
    @pytest.mark.asyncio
    async def test_get_server_status(self, mcp_client):
        """Test getting server status."""
        with patch.object(mcp_client, 'get_server_info', new_callable=AsyncMock) as mock_get:
            from backend.services.mcp_client_interface import MCPServerInfo
            
            mock_get.return_value = MCPServerInfo(
                server_id="server-1",
                name="Test",
                description="Test",
                endpoint="http://localhost",
                status=MCPServerStatus.AVAILABLE,
                capabilities=[],
                tools=[],
            )
            
            status = await mcp_client.get_server_status("server-1")
            
            assert status == MCPServerStatus.AVAILABLE
