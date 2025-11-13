"""
Unit tests for SystemIndexer.

Tests indexing logic with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.system_indexer import SystemIndexer
from backend.services.config import Settings


class TestSystemIndexer:
    """Tests for SystemIndexer."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Settings()
    
    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        db = MagicMock()
        db._conn = MagicMock(return_value=MagicMock())
        db._return = MagicMock()
        return db
    
    @pytest.fixture
    def mock_qdrant_service(self):
        """Create mock Qdrant service."""
        qdrant = MagicMock()
        qdrant.ensure_collection = MagicMock()
        qdrant.store_vectors = MagicMock(return_value=["vector-id-1"])
        qdrant.delete_vectors = MagicMock()
        return qdrant
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        embedding = MagicMock()
        embedding.get_model_info = MagicMock(return_value={"dimensions": 384})
        embedding.generate_embeddings = MagicMock(return_value=[[0.1] * 384, [0.2] * 384])
        return embedding
    
    @pytest.fixture
    def mock_chunking_service(self):
        """Create mock chunking service."""
        chunking = MagicMock()
        
        # Mock chunk object
        class MockChunk:
            def __init__(self, text):
                self.text = text
                self.metadata = {}
        
        chunking.chunk_text = MagicMock(return_value=[
            MockChunk("Chunk 1 content"),
            MockChunk("Chunk 2 content")
        ])
        return chunking
    
    @pytest.fixture
    def indexer(self, mock_settings, mock_db_service, mock_qdrant_service, 
                mock_embedding_service, mock_chunking_service):
        """Create SystemIndexer with mocked dependencies."""
        with patch('backend.services.system_indexer.DatabaseService', return_value=mock_db_service), \
             patch('backend.services.system_indexer.get_qdrant_service', return_value=mock_qdrant_service), \
             patch('backend.services.system_indexer.get_embedding_service', return_value=mock_embedding_service), \
             patch('backend.services.system_indexer.get_chunking_service', return_value=mock_chunking_service):
            return SystemIndexer(mock_settings)
    
    @pytest.mark.asyncio
    async def test_index_entity_creates_index_entry(self, indexer, mock_db_service):
        """Test that index_entity creates a database entry."""
        # Mock cursor and connection
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing entry
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [('index_id',), ('entity_type',), ('entity_id',)]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_conn.commit = MagicMock()
        
        mock_db_service._conn.return_value = mock_conn
        
        result = await indexer.index_entity(
            entity_type="file",
            entity_id="file-123",
            content_summary="Test content"
        )
        
        assert result is not None
        assert isinstance(result, str)
        mock_cursor.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_index_entity_updates_existing(self, indexer, mock_db_service):
        """Test that index_entity updates existing entry."""
        # Mock cursor to return existing entry
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("existing-index-id",)
        mock_cursor.fetchall.return_value = []
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_conn.commit = MagicMock()
        
        mock_db_service._conn.return_value = mock_conn
        
        # Mock update_index
        indexer.update_index = AsyncMock()
        
        result = await indexer.index_entity(
            entity_type="file",
            entity_id="file-123",
            content_summary="Updated content"
        )
        
        assert result == "existing-index-id"
        indexer.update_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_index(self, indexer, mock_db_service):
        """Test that delete_index removes entry."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("index-id-123",)
        mock_cursor.fetchall.return_value = []  # No vectors
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_conn.commit = MagicMock()
        
        mock_db_service._conn.return_value = mock_conn
        
        # Mock _delete_vectors
        indexer._delete_vectors = AsyncMock()
        
        await indexer.delete_index("file", "file-123")
        
        indexer._delete_vectors.assert_called_once_with("index-id-123")
        mock_cursor.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_indexed_entities(self, indexer, mock_db_service):
        """Test that get_indexed_entities returns filtered results."""
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('index_id',), ('entity_type',), ('entity_id',), ('metadata',)
        ]
        mock_cursor.fetchall.return_value = [
            ("id1", "file", "file-1", '{"key": "value"}'),
            ("id2", "event", "event-1", '{}'),
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        
        mock_db_service._conn.return_value = mock_conn
        
        results = await indexer.get_indexed_entities(entity_type="file")
        
        assert len(results) == 2
        assert results[0]["entity_type"] == "file"
    
    def test_indexer_implements_interface(self, indexer):
        """Test that SystemIndexer implements IndexingServiceInterface."""
        from backend.services.indexing_service_interface import IndexingServiceInterface
        assert isinstance(indexer, IndexingServiceInterface)
