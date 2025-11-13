"""
Integration tests for KnowledgeReviewWorker.

Tests with real knowledge base data.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.workers.knowledge_review_worker import KnowledgeReviewWorker
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def worker():
    """Create KnowledgeReviewWorker instance."""
    settings = Settings()
    db_service = DatabaseService(settings)
    return KnowledgeReviewWorker(settings, db_service=db_service)


@pytest.mark.integration
class TestKnowledgeReviewWorkerIntegration:
    """Integration tests for KnowledgeReviewWorker."""
    
    @pytest.mark.asyncio
    async def test_review_by_domain_real_data(self, worker):
        """Test reviewing knowledge by domain with real data."""
        results = await worker._review_by_domain()
        
        # Should return results (may be empty if no data)
        assert isinstance(results, dict)
        
        # If we have data, verify structure
        if results:
            for key, value in results.items():
                assert "domain" in value
                assert "knowledge_type" in value
                assert "chunk_count" in value
                assert isinstance(value["chunk_count"], int)
    
    @pytest.mark.asyncio
    async def test_identify_unused_chunks_real_data(self, worker):
        """Test identifying unused chunks with real data."""
        unused = await worker._identify_unused_chunks()
        
        # Should return a list (may be empty)
        assert isinstance(unused, list)
        
        # If we have unused chunks, verify structure
        if unused:
            for chunk in unused:
                assert "chunk_id" in chunk
                assert "domain" in chunk
                assert "days_since_creation" in chunk
                assert chunk["days_since_creation"] is not None
    
    @pytest.mark.asyncio
    async def test_identify_low_quality_chunks_real_data(self, worker):
        """Test identifying low-quality chunks with real data."""
        low_quality = await worker._identify_low_quality_chunks()
        
        # Should return a list (may be empty)
        assert isinstance(low_quality, list)
        
        # If we have low-quality chunks, verify structure
        if low_quality:
            for chunk in low_quality:
                assert "chunk_id" in chunk
                assert "quality_issue" in chunk
                assert chunk["quality_issue"] in ["too_short", "too_long"]
    
    @pytest.mark.asyncio
    async def test_detect_knowledge_gaps_real_data(self, worker):
        """Test detecting knowledge gaps with real data."""
        gaps = await worker._detect_knowledge_gaps()
        
        # Should return a list (may be empty)
        assert isinstance(gaps, list)
        
        # If we have gaps, verify structure
        if gaps:
            for gap in gaps:
                assert "domain" in gap
                assert "gap_reason" in gap
                assert gap["gap_reason"] == "insufficient_coverage"
    
    @pytest.mark.asyncio
    async def test_execute_scheduled_task_real_data(self, worker):
        """Test executing scheduled review task with real data."""
        result = await worker._execute_scheduled_task()
        
        # Should return a result dictionary
        assert isinstance(result, dict)
        assert "reviewed_domains" in result
        assert "unused_chunks" in result
        assert "low_quality_chunks" in result
        assert "knowledge_gaps" in result
        assert "recommendations" in result
        assert "timestamp" in result
        
        # Verify counts are non-negative
        assert result["reviewed_domains"] >= 0
        assert result["unused_chunks"] >= 0
        assert result["low_quality_chunks"] >= 0
        assert result["knowledge_gaps"] >= 0
        assert result["recommendations"] >= 0
    
    @pytest.mark.asyncio
    async def test_track_chunk_access(self, worker):
        """Test tracking chunk access with real database."""
        # Create a test chunk first
        conn = worker.db_service._conn()
        try:
            test_chunk_id = str(uuid4())
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO das_knowledge_chunks
                    (chunk_id, content, knowledge_type, domain, project_id, tags, metadata,
                     token_count, embedding_model, qdrant_collection, sequence_number, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    test_chunk_id,
                    "Test content for access tracking",
                    "training",
                    "testing",
                    None,
                    [],
                    json.dumps({"title": "Test Chunk"}),
                    10,
                    "all-MiniLM-L6-v2",
                    "das_knowledge",
                    0,
                ))
                conn.commit()
            
            # Track access
            event = {
                "type": "knowledge.chunk.accessed",
                "payload": {"chunk_id": test_chunk_id},
            }
            await worker._handle_event(event)
            
            # Verify access count was updated
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT metadata FROM das_knowledge_chunks WHERE chunk_id = %s
                """, (test_chunk_id,))
                row = cur.fetchone()
                assert row is not None
                metadata = row[0]
                # Metadata is JSONB, so it's already a dict
                if isinstance(metadata, dict):
                    assert "access_count" in metadata
                    assert metadata["access_count"] == 1
                    assert "last_accessed" in metadata
                else:
                    # If it's a string, parse it
                    metadata_dict = json.loads(metadata) if isinstance(metadata, str) else {}
                    assert "access_count" in metadata_dict
                    assert metadata_dict["access_count"] == 1
            
            # Clean up
            with conn.cursor() as cur:
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (test_chunk_id,))
                conn.commit()
        finally:
            worker.db_service._return(conn)
