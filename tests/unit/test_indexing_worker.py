"""
Unit tests for indexing worker.

Tests worker logic with mocked event sources.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from backend.services.indexing_worker import IndexingWorker
from backend.services.config import Settings


class TestIndexingWorker:
    """Tests for IndexingWorker."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Settings()
    
    @pytest.fixture
    def mock_indexing_service(self):
        """Create mock indexing service."""
        service = MagicMock()
        service.index_entity = AsyncMock(return_value="test-index-id")
        service.update_index = AsyncMock()
        service.delete_index = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        db = MagicMock()
        db._conn = MagicMock(return_value=MagicMock())
        db._return = MagicMock()
        return db
    
    @pytest.fixture
    def worker(self, mock_settings, mock_indexing_service, mock_db_service):
        """Create indexing worker with mocked dependencies."""
        return IndexingWorker(
            settings=mock_settings,
            indexing_service=mock_indexing_service,
            db_service=mock_db_service
        )
    
    @pytest.mark.asyncio
    async def test_process_file_event(self, worker, mock_indexing_service, mock_db_service):
        """Test processing file upload event."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            "file-123",
            "test.pdf",
            "application/pdf",
            {"description": "Test file"},
            ["tag1", "tag2"]
        )
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_db_service._conn.return_value = mock_conn
        
        await worker._index_file_event(
            event_id="event-1",
            project_id="proj-123",
            event_data={"file_id": "file-123"},
            semantic_summary="File uploaded: test.pdf"
        )
        
        mock_indexing_service.index_entity.assert_called_once()
        call_kwargs = mock_indexing_service.index_entity.call_args[1]
        assert call_kwargs["entity_type"] == "file"
        assert call_kwargs["entity_id"] == "file-123"
        assert call_kwargs["project_id"] == "proj-123"
    
    @pytest.mark.asyncio
    async def test_process_ontology_event(self, worker, mock_indexing_service, mock_db_service):
        """Test processing ontology event."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            "http://example.com/ontology",
            "Test Ontology",
            "base"
        )
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_db_service._conn.return_value = mock_conn
        
        await worker._index_ontology_event(
            event_id="event-2",
            project_id="proj-123",
            event_data={"graph_iri": "http://example.com/ontology"},
            semantic_summary="Ontology created"
        )
        
        mock_indexing_service.index_entity.assert_called_once()
        call_kwargs = mock_indexing_service.index_entity.call_args[1]
        assert call_kwargs["entity_type"] == "ontology"
        assert call_kwargs["entity_uri"] == "http://example.com/ontology"
    
    @pytest.mark.asyncio
    async def test_process_event_immediate(self, worker):
        """Test immediate event processing."""
        # Mock the _process_event method
        worker._process_event = AsyncMock()
        
        await worker.process_event_immediate(
            event_type="file_uploaded",
            event_data={"file_id": "file-123"},
            project_id="proj-123",
            semantic_summary="File uploaded"
        )
        
        worker._process_event.assert_called_once()
        # Verify event_type was passed correctly
        call_kwargs = worker._process_event.call_args[1]
        assert call_kwargs["event_type"] == "file_uploaded"
    
    def test_worker_implements_interface_pattern(self, worker):
        """Test that worker follows interface pattern."""
        assert hasattr(worker, 'start')
        assert hasattr(worker, 'stop')
        assert hasattr(worker, 'process_event_immediate')
