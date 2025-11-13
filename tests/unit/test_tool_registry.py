"""
Unit tests for DASToolRegistry.

Tests CRUD operations with mocked database.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from backend.services.das_tool_registry import DASToolRegistry
from backend.services.tool_registry_interface import ToolType
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def mock_db_service():
    """Create mock database service."""
    db = Mock(spec=DatabaseService)
    db._conn = Mock()
    db._return = Mock()
    return db


@pytest.fixture
def registry(mock_db_service):
    """Create DASToolRegistry instance."""
    settings = Settings()
    return DASToolRegistry(settings, db_service=mock_db_service)


class TestDASToolRegistry:
    """Test DASToolRegistry."""
    
    @pytest.mark.asyncio
    async def test_store_tool(self, registry):
        """Test storing a tool."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_conn.commit.return_value = None
        
        registry.db_service._conn.return_value = mock_conn
        
        tool_id = await registry.store_tool(
            name="Test Calculator",
            description="Adds numbers",
            tool_type=ToolType.CALCULATOR,
            code="def add(a, b): return a + b",
            capabilities=["calculation"],
            created_by="test-user",
        )
        
        assert tool_id is not None
        assert mock_cursor.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_tool(self, registry):
        """Test getting a tool."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database row
        from uuid import uuid4
        test_tool_id = str(uuid4())
        mock_cursor.fetchall.return_value = [(
            test_tool_id,
            "Test Tool",
            "Description",
            "calculator",
            "code",
            ["calculation"],
            "user1",
            datetime.now(timezone.utc),
            5,
            datetime.now(timezone.utc),
            [],
            {},
        )]
        
        registry.db_service._conn.return_value = mock_conn
        
        tool = await registry.get_tool(test_tool_id)
        
        assert tool is not None
        assert tool.name == "Test Tool"
        assert tool.tool_type == ToolType.CALCULATOR
    
    @pytest.mark.asyncio
    async def test_find_tool_by_name(self, registry):
        """Test finding tools by name."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [(
            "tool-1",
            "Calculator Tool",
            "Desc",
            "calculator",
            "code",
            ["calculation"],
            "user1",
            datetime.now(timezone.utc),
            0,
            None,
            [],
            {},
        )]
        
        registry.db_service._conn.return_value = mock_conn
        
        tools = await registry.find_tool(name="Calculator")
        
        assert len(tools) == 1
        assert "Calculator" in tools[0].name
    
    @pytest.mark.asyncio
    async def test_update_tool(self, registry):
        """Test updating a tool."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        mock_conn.commit.return_value = None
        
        registry.db_service._conn.return_value = mock_conn
        
        updated = await registry.update_tool(
            "tool-1",
            name="Updated Name",
            description="Updated desc",
        )
        
        assert updated is True
        assert mock_cursor.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_update_usage(self, registry):
        """Test updating usage statistics."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        mock_conn.commit.return_value = None
        
        registry.db_service._conn.return_value = mock_conn
        
        updated = await registry.update_usage("tool-1", increment=5)
        
        assert updated is True
        assert mock_cursor.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_delete_tool(self, registry):
        """Test deleting a tool."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        mock_conn.commit.return_value = None
        
        registry.db_service._conn.return_value = mock_conn
        
        deleted = await registry.delete_tool("tool-1")
        
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_list_tools(self, registry):
        """Test listing tools."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = []
        
        registry.db_service._conn.return_value = mock_conn
        
        tools = await registry.list_tools(limit=10, offset=0)
        
        assert isinstance(tools, list)
        assert mock_cursor.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_popular_tools(self, registry):
        """Test getting popular tools."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = []
        
        registry.db_service._conn.return_value = mock_conn
        
        popular = await registry.get_popular_tools(limit=10)
        
        assert isinstance(popular, list)
