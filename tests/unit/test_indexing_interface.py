"""
Unit tests for indexing service interface.

Tests interface contract and mock implementations.
"""

import pytest
from unittest.mock import AsyncMock
from backend.services.indexing_service_interface import IndexingServiceInterface


class MockIndexingService(IndexingServiceInterface):
    """Mock implementation of IndexingServiceInterface for testing."""
    
    def __init__(self):
        self.index_entity_mock = AsyncMock()
        self.update_index_mock = AsyncMock()
        self.delete_index_mock = AsyncMock()
        self.get_indexed_entities_mock = AsyncMock()
    
    async def index_entity(self, entity_type, entity_id, content_summary, **kwargs):
        return await self.index_entity_mock(entity_type, entity_id, content_summary, **kwargs)
    
    async def update_index(self, index_id, **kwargs):
        return await self.update_index_mock(index_id, **kwargs)
    
    async def delete_index(self, entity_type, entity_id):
        return await self.delete_index_mock(entity_type, entity_id)
    
    async def get_indexed_entities(self, **kwargs):
        return await self.get_indexed_entities_mock(**kwargs)


class TestIndexingServiceInterface:
    """Tests for IndexingServiceInterface contract."""
    
    @pytest.mark.asyncio
    async def test_index_entity_returns_index_id(self):
        """Test that index_entity returns an index ID."""
        mock_service = MockIndexingService()
        mock_service.index_entity_mock.return_value = "test-index-id"
        
        result = await mock_service.index_entity(
            entity_type="file",
            entity_id="file-123",
            content_summary="Test content"
        )
        
        assert result == "test-index-id"
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_index_entity_receives_all_parameters(self):
        """Test that index_entity receives all parameters."""
        mock_service = MockIndexingService()
        mock_service.index_entity_mock.return_value = "test-id"
        
        await mock_service.index_entity(
            entity_type="event",
            entity_id="event-456",
            content_summary="Event summary",
            project_id="proj-789",
            entity_uri="http://example.com/event",
            metadata={"key": "value"},
            tags=["tag1", "tag2"],
            domain="requirements"
        )
        
        mock_service.index_entity_mock.assert_called_once()
        call_kwargs = mock_service.index_entity_mock.call_args[1]
        assert call_kwargs.get("project_id") == "proj-789"
        assert call_kwargs.get("entity_uri") == "http://example.com/event"
        assert call_kwargs.get("metadata") == {"key": "value"}
        assert call_kwargs.get("tags") == ["tag1", "tag2"]
        assert call_kwargs.get("domain") == "requirements"
    
    @pytest.mark.asyncio
    async def test_update_index(self):
        """Test that update_index can be called."""
        mock_service = MockIndexingService()
        mock_service.update_index_mock.return_value = None
        
        await mock_service.update_index(
            index_id="test-index-id",
            content_summary="Updated content",
            metadata={"new_key": "new_value"}
        )
        
        mock_service.update_index_mock.assert_called_once()
        call_kwargs = mock_service.update_index_mock.call_args[1]
        assert call_kwargs.get("content_summary") == "Updated content"
        assert call_kwargs.get("metadata") == {"new_key": "new_value"}
    
    @pytest.mark.asyncio
    async def test_delete_index(self):
        """Test that delete_index can be called."""
        mock_service = MockIndexingService()
        mock_service.delete_index_mock.return_value = None
        
        await mock_service.delete_index("file", "file-123")
        
        mock_service.delete_index_mock.assert_called_once_with("file", "file-123")
    
    @pytest.mark.asyncio
    async def test_get_indexed_entities_returns_list(self):
        """Test that get_indexed_entities returns a list."""
        mock_service = MockIndexingService()
        mock_service.get_indexed_entities_mock.return_value = [
            {"index_id": "id1", "entity_type": "file", "entity_id": "file-1"},
            {"index_id": "id2", "entity_type": "event", "entity_id": "event-1"},
        ]
        
        results = await mock_service.get_indexed_entities(entity_type="file")
        
        assert isinstance(results, list)
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_get_indexed_entities_filters(self):
        """Test that get_indexed_entities accepts filter parameters."""
        mock_service = MockIndexingService()
        mock_service.get_indexed_entities_mock.return_value = []
        
        await mock_service.get_indexed_entities(
            entity_type="ontology",
            project_id="proj-123",
            domain="requirements",
            tags=["tag1"],
            limit=50
        )
        
        mock_service.get_indexed_entities_mock.assert_called_once()
        call_kwargs = mock_service.get_indexed_entities_mock.call_args[1]
        assert call_kwargs.get("entity_type") == "ontology"
        assert call_kwargs.get("project_id") == "proj-123"
        assert call_kwargs.get("domain") == "requirements"
        assert call_kwargs.get("tags") == ["tag1"]
        assert call_kwargs.get("limit") == 50
    
    def test_interface_cannot_be_instantiated(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IndexingServiceInterface()
    
    def test_mock_implementation_is_valid(self):
        """Test that MockIndexingService properly implements the interface."""
        service = MockIndexingService()
        assert isinstance(service, IndexingServiceInterface)
        
        # Should have all required methods
        assert hasattr(service, 'index_entity')
        assert hasattr(service, 'update_index')
        assert hasattr(service, 'delete_index')
        assert hasattr(service, 'get_indexed_entities')
