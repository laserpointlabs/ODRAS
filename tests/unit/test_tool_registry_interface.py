"""
Unit tests for ToolRegistryInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.services.tool_registry_interface import (
    ToolRegistryInterface,
    ToolMetadata,
    ToolType,
)


class ConcreteToolRegistry(ToolRegistryInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._counter = 0
    
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
        """Store a tool."""
        tool_id = f"tool_{self._counter}"
        self._counter += 1
        
        tool = ToolMetadata(
            tool_id=tool_id,
            name=name,
            description=description,
            tool_type=tool_type,
            code=code,
            capabilities=capabilities,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        self._tools[tool_id] = tool
        return tool_id
    
    async def find_tool(
        self,
        tool_id: Optional[str] = None,
        name: Optional[str] = None,
        tool_type: Optional[ToolType] = None,
        capability: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> List[ToolMetadata]:
        """Find tools."""
        results = []
        
        for tool in self._tools.values():
            if tool_id and tool.tool_id != tool_id:
                continue
            if name and name.lower() not in tool.name.lower():
                continue
            if tool_type and tool.tool_type != tool_type:
                continue
            if capability and capability not in tool.capabilities:
                continue
            if tags and not all(tag in tool.tags for tag in tags):
                continue
            if created_by and tool.created_by != created_by:
                continue
            
            results.append(tool)
        
        return results
    
    async def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get tool by ID."""
        return self._tools.get(tool_id)
    
    async def update_tool(
        self,
        tool_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update tool."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        
        if name:
            tool.name = name
        if description:
            tool.description = description
        if code:
            tool.code = code
        if tags:
            tool.tags = tags
        if metadata:
            tool.metadata.update(metadata)
        
        return True
    
    async def update_usage(self, tool_id: str, increment: int = 1) -> bool:
        """Update usage."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        
        tool.usage_count += increment
        tool.last_used_at = datetime.now(timezone.utc)
        return True
    
    async def delete_tool(self, tool_id: str) -> bool:
        """Delete tool."""
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False
    
    async def list_tools(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[ToolMetadata]:
        """List tools."""
        tools = list(self._tools.values())
        
        # Sort
        reverse = sort_order == "desc"
        if sort_by == "created_at":
            tools.sort(key=lambda t: t.created_at, reverse=reverse)
        elif sort_by == "usage_count":
            tools.sort(key=lambda t: t.usage_count, reverse=reverse)
        elif sort_by == "name":
            tools.sort(key=lambda t: t.name, reverse=reverse)
        
        # Paginate
        return tools[offset:offset + limit]
    
    async def get_popular_tools(self, limit: int = 10) -> List[ToolMetadata]:
        """Get popular tools."""
        tools = await self.list_tools(sort_by="usage_count", sort_order="desc")
        return tools[:limit]


class TestToolRegistryInterface:
    """Test ToolRegistryInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ToolRegistryInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        registry = ConcreteToolRegistry()
        assert isinstance(registry, ToolRegistryInterface)
        assert isinstance(registry, ABC)
    
    @pytest.mark.asyncio
    async def test_store_tool(self):
        """Test storing a tool."""
        registry = ConcreteToolRegistry()
        
        tool_id = await registry.store_tool(
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.CALCULATOR,
            code="def calculate(): return 1+1",
            capabilities=["calculation"],
            created_by="test-user",
        )
        
        assert tool_id is not None
        assert tool_id.startswith("tool_")
    
    @pytest.mark.asyncio
    async def test_get_tool(self):
        """Test getting a tool."""
        registry = ConcreteToolRegistry()
        
        tool_id = await registry.store_tool(
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.CALCULATOR,
            code="def calculate(): return 1+1",
            capabilities=["calculation"],
            created_by="test-user",
        )
        
        tool = await registry.get_tool(tool_id)
        
        assert tool is not None
        assert tool.name == "Test Tool"
        assert tool.tool_type == ToolType.CALCULATOR
    
    @pytest.mark.asyncio
    async def test_find_tool_by_name(self):
        """Test finding tools by name."""
        registry = ConcreteToolRegistry()
        
        await registry.store_tool(
            name="Calculator Tool",
            description="Calculates things",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        await registry.store_tool(
            name="Data Fetcher",
            description="Fetches data",
            tool_type=ToolType.DATA_FETCHER,
            code="code",
            capabilities=["data_fetching"],
            created_by="user2",
        )
        
        results = await registry.find_tool(name="Calculator")
        
        assert len(results) == 1
        assert results[0].name == "Calculator Tool"
    
    @pytest.mark.asyncio
    async def test_find_tool_by_type(self):
        """Test finding tools by type."""
        registry = ConcreteToolRegistry()
        
        await registry.store_tool(
            name="Tool 1",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        await registry.store_tool(
            name="Tool 2",
            description="Desc",
            tool_type=ToolType.DATA_FETCHER,
            code="code",
            capabilities=["data_fetching"],
            created_by="user2",
        )
        
        results = await registry.find_tool(tool_type=ToolType.CALCULATOR)
        
        assert len(results) == 1
        assert results[0].tool_type == ToolType.CALCULATOR
    
    @pytest.mark.asyncio
    async def test_find_tool_by_capability(self):
        """Test finding tools by capability."""
        registry = ConcreteToolRegistry()
        
        await registry.store_tool(
            name="Tool 1",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation", "math"],
            created_by="user1",
        )
        
        results = await registry.find_tool(capability="calculation")
        
        assert len(results) == 1
        assert "calculation" in results[0].capabilities
    
    @pytest.mark.asyncio
    async def test_update_tool(self):
        """Test updating a tool."""
        registry = ConcreteToolRegistry()
        
        tool_id = await registry.store_tool(
            name="Original Name",
            description="Original desc",
            tool_type=ToolType.CALCULATOR,
            code="original code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        updated = await registry.update_tool(
            tool_id,
            name="Updated Name",
            description="Updated desc",
        )
        
        assert updated is True
        
        tool = await registry.get_tool(tool_id)
        assert tool.name == "Updated Name"
        assert tool.description == "Updated desc"
    
    @pytest.mark.asyncio
    async def test_update_usage(self):
        """Test updating usage statistics."""
        registry = ConcreteToolRegistry()
        
        tool_id = await registry.store_tool(
            name="Test Tool",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        updated = await registry.update_usage(tool_id, increment=5)
        
        assert updated is True
        
        tool = await registry.get_tool(tool_id)
        assert tool.usage_count == 5
        assert tool.last_used_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_tool(self):
        """Test deleting a tool."""
        registry = ConcreteToolRegistry()
        
        tool_id = await registry.store_tool(
            name="Test Tool",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        deleted = await registry.delete_tool(tool_id)
        
        assert deleted is True
        
        tool = await registry.get_tool(tool_id)
        assert tool is None
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        registry = ConcreteToolRegistry()
        
        # Create multiple tools
        for i in range(5):
            await registry.store_tool(
                name=f"Tool {i}",
                description="Desc",
                tool_type=ToolType.CALCULATOR,
                code="code",
                capabilities=["calculation"],
                created_by="user1",
            )
        
        tools = await registry.list_tools(limit=3, offset=0)
        
        assert len(tools) == 3
    
    @pytest.mark.asyncio
    async def test_get_popular_tools(self):
        """Test getting popular tools."""
        registry = ConcreteToolRegistry()
        
        # Create tools with different usage counts
        tool_id1 = await registry.store_tool(
            name="Tool 1",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        tool_id2 = await registry.store_tool(
            name="Tool 2",
            description="Desc",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_by="user1",
        )
        
        await registry.update_usage(tool_id2, increment=10)
        
        popular = await registry.get_popular_tools(limit=10)
        
        assert len(popular) >= 1
        assert popular[0].usage_count >= 10


class TestToolMetadata:
    """Test ToolMetadata."""
    
    def test_create_metadata(self):
        """Test creating tool metadata."""
        metadata = ToolMetadata(
            tool_id="test-1",
            name="Test Tool",
            description="A test",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_at=datetime.now(timezone.utc),
            created_by="user1",
        )
        
        assert metadata.tool_id == "test-1"
        assert metadata.name == "Test Tool"
        assert metadata.tool_type == ToolType.CALCULATOR
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        metadata = ToolMetadata(
            tool_id="test-1",
            name="Test Tool",
            description="A test",
            tool_type=ToolType.CALCULATOR,
            code="code",
            capabilities=["calculation"],
            created_at=datetime.now(timezone.utc),
            created_by="user1",
        )
        
        data = metadata.to_dict()
        
        assert data["tool_id"] == "test-1"
        assert data["name"] == "Test Tool"
        assert data["tool_type"] == ToolType.CALCULATOR.value
