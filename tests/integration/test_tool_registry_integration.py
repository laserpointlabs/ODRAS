"""
Integration tests for DASToolRegistry.

Tests with real database storage and retrieval.
"""

import pytest
from datetime import datetime, timezone

from backend.services.das_tool_registry import DASToolRegistry
from backend.services.tool_registry_interface import ToolType
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def registry():
    """Create DASToolRegistry instance."""
    settings = Settings()
    db_service = DatabaseService(settings)
    return DASToolRegistry(settings, db_service=db_service)


@pytest.mark.integration
class TestDASToolRegistryIntegration:
    """Integration tests for DASToolRegistry."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_tool(self, registry):
        """Test storing and retrieving a tool."""
        tool_id = await registry.store_tool(
            name="Test Calculator",
            description="Adds two numbers",
            tool_type=ToolType.CALCULATOR,
            code="def add(a, b): return a + b",
            capabilities=["calculation", "addition"],
            created_by="test-user",
            tags=["math", "basic"],
        )
        
        assert tool_id is not None
        
        # Retrieve the tool
        tool = await registry.get_tool(tool_id)
        
        assert tool is not None
        assert tool.name == "Test Calculator"
        assert tool.tool_type == ToolType.CALCULATOR
        assert "calculation" in tool.capabilities
        assert "math" in tool.tags
        
        # Clean up
        await registry.delete_tool(tool_id)
    
    @pytest.mark.asyncio
    async def test_find_tools_by_capability(self, registry):
        """Test finding tools by capability."""
        # Store multiple tools
        tool_id1 = await registry.store_tool(
            name="Calculator Tool",
            description="Calculates",
            tool_type=ToolType.CALCULATOR,
            code="code1",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        tool_id2 = await registry.store_tool(
            name="Data Fetcher",
            description="Fetches data",
            tool_type=ToolType.DATA_FETCHER,
            code="code2",
            capabilities=["data_fetching"],
            created_by="user2",
        )
        
        # Find by capability
        calculators = await registry.find_tool(capability="calculation")
        
        assert len(calculators) >= 1
        assert any(t.tool_id == tool_id1 for t in calculators)
        
        # Clean up
        await registry.delete_tool(tool_id1)
        await registry.delete_tool(tool_id2)
    
    @pytest.mark.asyncio
    async def test_update_tool(self, registry):
        """Test updating a tool."""
        tool_id = await registry.store_tool(
            name="Original Name",
            description="Original",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        # Update tool
        updated = await registry.update_tool(
            tool_id,
            name="Updated Name",
            description="Updated",
        )
        
        assert updated is True
        
        # Verify update
        tool = await registry.get_tool(tool_id)
        assert tool.name == "Updated Name"
        assert tool.description == "Updated"
        
        # Clean up
        await registry.delete_tool(tool_id)
    
    @pytest.mark.asyncio
    async def test_update_usage(self, registry):
        """Test updating usage statistics."""
        tool_id = await registry.store_tool(
            name="Test Tool",
            description="Test",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        # Update usage
        updated = await registry.update_usage(tool_id, increment=5)
        
        assert updated is True
        
        # Verify usage count
        tool = await registry.get_tool(tool_id)
        assert tool.usage_count == 5
        assert tool.last_used_at is not None
        
        # Clean up
        await registry.delete_tool(tool_id)
    
    @pytest.mark.asyncio
    async def test_list_tools(self, registry):
        """Test listing tools."""
        # Store a few tools
        tool_ids = []
        for i in range(3):
            tool_id = await registry.store_tool(
                name=f"Tool {i}",
                description=f"Tool {i} description",
                tool_type=ToolType.CALCULATOR,
                code=f"code{i}",
                capabilities=["calculation"],
                created_by="user1",
            )
            tool_ids.append(tool_id)
        
        # List tools
        tools = await registry.list_tools(limit=10, offset=0)
        
        assert len(tools) >= 3
        
        # Clean up
        for tool_id in tool_ids:
            await registry.delete_tool(tool_id)
    
    @pytest.mark.asyncio
    async def test_get_popular_tools(self, registry):
        """Test getting popular tools."""
        # Store tools with different usage counts
        tool_id1 = await registry.store_tool(
            name="Popular Tool",
            description="Popular",
            tool_type=ToolType.CALCULATOR,
            code="code1",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        tool_id2 = await registry.store_tool(
            name="Unpopular Tool",
            description="Unpopular",
            tool_type=ToolType.CALCULATOR,
            code="code2",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        # Update usage for tool1
        await registry.update_usage(tool_id1, increment=10)
        
        # Get popular tools
        popular = await registry.get_popular_tools(limit=10)
        
        assert len(popular) >= 1
        # Most popular should be first
        if popular:
            assert popular[0].usage_count >= 10
        
        # Clean up
        await registry.delete_tool(tool_id1)
        await registry.delete_tool(tool_id2)
