"""
Unit tests for KnowledgeReviewWorker.

Tests knowledge review logic with mocked data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from backend.workers.knowledge_review_worker import KnowledgeReviewWorker
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
def worker(mock_db_service):
    """Create KnowledgeReviewWorker instance."""
    settings = Settings()
    return KnowledgeReviewWorker(settings, db_service=mock_db_service)


class TestKnowledgeReviewWorker:
    """Test KnowledgeReviewWorker."""
    
    def test_worker_properties(self, worker):
        """Test worker properties."""
        assert worker.worker_name == "knowledge-review-worker"
        assert worker.worker_type == "review"
        assert worker.schedule_interval == 86400  # 24 hours
        assert "knowledge.chunk.accessed" in worker.subscribed_events
    
    @pytest.mark.asyncio
    async def test_handle_chunk_access_event(self, worker):
        """Test handling chunk access event."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup context manager for cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock metadata query
        mock_cursor.fetchone.return_value = ({"access_count": 5},)
        mock_cursor.execute.return_value = None
        
        worker.db_service._conn.return_value = mock_conn
        
        event = {
            "type": "knowledge.chunk.accessed",
            "payload": {"chunk_id": "test-chunk-id"},
        }
        
        await worker._handle_event(event)
        
        # Verify metadata was updated
        assert mock_cursor.execute.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_review_by_domain(self, worker):
        """Test reviewing knowledge by domain."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup context manager for cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock domain review query results
        mock_cursor.fetchall.return_value = [
            ("ontology", "training", 50, 200.5, datetime.now(timezone.utc), datetime.now(timezone.utc)),
            ("requirements", "project", 30, 150.0, datetime.now(timezone.utc), datetime.now(timezone.utc)),
        ]
        
        worker.db_service._conn.return_value = mock_conn
        
        results = await worker._review_by_domain()
        
        assert len(results) == 2
        assert "ontology:training" in results
        assert "requirements:project" in results
        assert results["ontology:training"]["chunk_count"] == 50
    
    @pytest.mark.asyncio
    async def test_identify_unused_chunks(self, worker):
        """Test identifying unused chunks."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup context manager for cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock unused chunks query results
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        mock_cursor.fetchall.return_value = [
            ("chunk-1", "ontology", "training", old_date, 200, "Test Title"),
        ]
        
        worker.db_service._conn.return_value = mock_conn
        
        unused = await worker._identify_unused_chunks()
        
        assert len(unused) == 1
        assert unused[0]["chunk_id"] == "chunk-1"
        assert unused[0]["domain"] == "ontology"
        assert unused[0]["days_since_creation"] is not None
    
    @pytest.mark.asyncio
    async def test_identify_low_quality_chunks(self, worker):
        """Test identifying low-quality chunks."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup context manager for cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock low-quality chunks (too short)
        mock_cursor.fetchall.return_value = [
            ("chunk-1", "ontology", "training", 30, 500, "Short Chunk"),
            ("chunk-2", "requirements", "project", 2500, 10000, "Long Chunk"),
        ]
        
        worker.db_service._conn.return_value = mock_conn
        
        low_quality = await worker._identify_low_quality_chunks()
        
        assert len(low_quality) == 2
        assert low_quality[0]["quality_issue"] == "too_short"
        assert low_quality[1]["quality_issue"] == "too_long"
    
    @pytest.mark.asyncio
    async def test_detect_knowledge_gaps(self, worker):
        """Test detecting knowledge gaps."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Setup context manager for cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock knowledge gaps query results
        mock_cursor.fetchall.return_value = [
            ("acquisition", "training", 5, 1),
        ]
        
        worker.db_service._conn.return_value = mock_conn
        
        gaps = await worker._detect_knowledge_gaps()
        
        assert len(gaps) == 1
        assert gaps[0]["domain"] == "acquisition"
        assert gaps[0]["gap_reason"] == "insufficient_coverage"
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, worker):
        """Test generating recommendations."""
        unused_chunks = [
            {"chunk_id": "chunk-1", "domain": "ontology"},
            {"chunk_id": "chunk-2", "domain": "requirements"},
        ]
        
        low_quality_chunks = [
            {"chunk_id": "chunk-3", "domain": "ontology", "quality_issue": "too_short"},
        ]
        
        knowledge_gaps = [
            {"domain": "acquisition", "knowledge_type": "training"},
        ]
        
        review_results = {
            "ontology:training": {"chunk_count": 50},
        }
        
        recommendations = await worker._generate_recommendations(
            unused_chunks=unused_chunks,
            low_quality_chunks=low_quality_chunks,
            knowledge_gaps=knowledge_gaps,
            review_results=review_results,
        )
        
        assert len(recommendations) == 3
        assert any(r["type"] == "unused_chunks" for r in recommendations)
        assert any(r["type"] == "low_quality_chunks" for r in recommendations)
        assert any(r["type"] == "knowledge_gaps" for r in recommendations)
        
        # Check priorities
        unused_rec = next(r for r in recommendations if r["type"] == "unused_chunks")
        assert unused_rec["priority"] == "medium"
        
        low_quality_rec = next(r for r in recommendations if r["type"] == "low_quality_chunks")
        assert low_quality_rec["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_execute_scheduled_task(self, worker):
        """Test executing scheduled review task."""
        # Mock all review methods
        with patch.object(worker, '_review_by_domain', new_callable=AsyncMock) as mock_review, \
             patch.object(worker, '_identify_unused_chunks', new_callable=AsyncMock) as mock_unused, \
             patch.object(worker, '_identify_low_quality_chunks', new_callable=AsyncMock) as mock_low_quality, \
             patch.object(worker, '_detect_knowledge_gaps', new_callable=AsyncMock) as mock_gaps, \
             patch.object(worker, '_generate_recommendations', new_callable=AsyncMock) as mock_recommendations, \
             patch.object(worker, '_store_recommendations', new_callable=AsyncMock) as mock_store:
            
            mock_review.return_value = {}
            mock_unused.return_value = []
            mock_low_quality.return_value = []
            mock_gaps.return_value = []
            mock_recommendations.return_value = []
            
            result = await worker._execute_scheduled_task()
            
            assert result is not None
            assert "reviewed_domains" in result
            assert "unused_chunks" in result
            assert "low_quality_chunks" in result
            assert "knowledge_gaps" in result
            assert "recommendations" in result
            
            # Verify all methods were called
            mock_review.assert_called_once()
            mock_unused.assert_called_once()
            mock_low_quality.assert_called_once()
            mock_gaps.assert_called_once()
            mock_recommendations.assert_called_once()
            mock_store.assert_called_once()
