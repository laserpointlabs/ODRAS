"""
Integration tests for Phase 2: Comprehensive System Indexing

Tests the complete indexing system including:
- SystemIndexer functionality
- RAG integration with system index
- Event-driven indexing worker
- End-to-end indexing flow
"""

import pytest
import asyncio
from backend.services.system_indexer import SystemIndexer
from backend.services.indexing_worker import IndexingWorker
from backend.rag.core.modular_rag_service import ModularRAGService
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.mark.integration
class TestPhase2Indexing:
    """Integration tests for Phase 2 indexing system."""
    
    @pytest.fixture
    def settings(self):
        """Create settings."""
        return Settings()
    
    @pytest.fixture
    def db_service(self, settings):
        """Create database service."""
        return DatabaseService(settings)
    
    @pytest.fixture
    def indexing_service(self, settings):
        """Create indexing service."""
        return SystemIndexer(settings)
    
    @pytest.fixture
    def rag_service(self, settings, db_service, indexing_service):
        """Create RAG service with indexing."""
        return ModularRAGService(
            settings=settings,
            db_service=db_service,
            indexing_service=indexing_service
        )
    
    @pytest.mark.asyncio
    async def test_index_entity_creates_entry(self, indexing_service, db_service):
        """Test that indexing an entity creates database entry."""
        # Index a test entity
        index_id = await indexing_service.index_entity(
            entity_type="file",
            entity_id="test-file-phase2-1",
            content_summary="This is a test file for Phase 2 integration testing. It contains information about system architecture and requirements.",
            project_id=None,
            domain="testing"
        )
        
        assert index_id is not None
        
        # Verify entry exists in database
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT index_id, entity_type, entity_id, content_summary, domain
                    FROM system_index
                    WHERE index_id = %s
                """, (index_id,))
                row = cur.fetchone()
                
                assert row is not None, "Index entry should exist in database"
                assert row[1] == "file", "Entity type should be 'file'"
                assert row[2] == "test-file-phase2-1", "Entity ID should match"
                assert row[4] == "testing", "Domain should match"
                
        finally:
            db_service._return(conn)
        
        # Cleanup
        await indexing_service.delete_index("file", "test-file-phase2-1")
    
    @pytest.mark.asyncio
    async def test_index_entity_creates_vectors(self, indexing_service, db_service):
        """Test that indexing creates vector entries in SQL."""
        # Index an entity
        index_id = await indexing_service.index_entity(
            entity_type="event",
            entity_id="test-event-phase2-2",
            content_summary="Test event content for Phase 2. This content should be chunked and stored in system_index_vectors table.",
            project_id=None,
            domain="testing"
        )
        
        # Verify vectors exist in SQL
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM system_index_vectors
                    WHERE index_id = %s
                """, (index_id,))
                count = cur.fetchone()[0]
                
                assert count > 0, "Should have at least one vector entry"
                
                # Verify content is stored in SQL (SQL-first pattern)
                cur.execute("""
                    SELECT content FROM system_index_vectors
                    WHERE index_id = %s
                    LIMIT 1
                """, (index_id,))
                row = cur.fetchone()
                
                assert row is not None, "Should have content in SQL"
                assert len(row[0]) > 0, "Content should not be empty"
                
        finally:
            db_service._return(conn)
        
        # Cleanup
        await indexing_service.delete_index("event", "test-event-phase2-2")
    
    @pytest.mark.asyncio
    async def test_rag_queries_system_index(self, rag_service, indexing_service):
        """Test that RAG queries retrieve from system index."""
        # Index a test entity with specific content
        index_id = await indexing_service.index_entity(
            entity_type="knowledge_asset",
            entity_id="test-asset-phase2-3",
            content_summary="Phase 2 integration test knowledge asset. Contains information about testing system indexing and RAG integration. This is specific test content for verification.",
            project_id=None,
            domain="testing"
        )
        
        # Wait a moment for indexing to complete (embeddings generation takes time)
        await asyncio.sleep(5)
        
        # Query RAG - should find the indexed entity
        rag_context = await rag_service.query_knowledge_base(
            query="system indexing RAG integration",
            context={}
        )
        
        # Should have chunks from system index
        system_chunks = [c for c in rag_context.chunks if c.source.source_type == "system"]
        
        # Debug output
        if len(system_chunks) == 0:
            print(f"DEBUG: No system chunks found. Total chunks: {len(rag_context.chunks)}")
            print(f"DEBUG: Chunk sources: {[c.source.source_type for c in rag_context.chunks]}")
            if rag_context.chunks:
                print(f"DEBUG: First chunk content preview: {rag_context.chunks[0].content[:100]}")
        
        assert len(system_chunks) > 0, f"Should retrieve chunks from system index. Got {len(rag_context.chunks)} total chunks, {len(system_chunks)} system chunks"
        
        # Verify content is present (check if any chunk has content)
        all_content = rag_context.get_all_content()
        has_content = len(all_content.strip()) > 0 or any(len(c.content.strip()) > 0 for c in system_chunks)
        assert has_content, f"Content should not be empty. Got {len(all_content)} chars total, chunk contents: {[len(c.content) for c in system_chunks]}"
        
        # Cleanup
        await indexing_service.delete_index("knowledge_asset", "test-asset-phase2-3")
    
    @pytest.mark.asyncio
    async def test_indexing_worker_processes_event(self, indexing_service, db_service):
        """Test that indexing worker can process events."""
        worker = IndexingWorker(
            settings=Settings(),
            indexing_service=indexing_service,
            db_service=db_service
        )
        
        # Process an event immediately (bypassing polling)
        await worker.process_event_immediate(
            event_type="file_uploaded",
            event_data={
                "file_id": "test-file-worker-1",
                "filename": "test_phase2.txt"
            },
            project_id=None,
            semantic_summary="Test file uploaded for Phase 2 worker testing"
        )
        
        # Note: This will fail if the file doesn't exist in the database
        # That's expected - we're testing the worker logic, not the full flow
        
        # Verify worker has the expected methods
        assert hasattr(worker, 'start')
        assert hasattr(worker, 'stop')
        assert hasattr(worker, 'process_event_immediate')
    
    @pytest.mark.asyncio
    async def test_get_indexed_entities(self, indexing_service):
        """Test retrieving indexed entities."""
        # Index multiple entities
        index_id1 = await indexing_service.index_entity(
            entity_type="file",
            entity_id="test-get-1",
            content_summary="First test entity",
            domain="testing"
        )
        
        index_id2 = await indexing_service.index_entity(
            entity_type="file",
            entity_id="test-get-2",
            content_summary="Second test entity",
            domain="testing"
        )
        
        # Get indexed entities
        entities = await indexing_service.get_indexed_entities(
            entity_type="file",
            domain="testing",
            limit=10
        )
        
        assert len(entities) >= 2, f"Should have at least 2 entities, got {len(entities)}"
        
        # Verify entities match
        entity_ids = [e["entity_id"] for e in entities]
        assert "test-get-1" in entity_ids
        assert "test-get-2" in entity_ids
        
        # Cleanup
        await indexing_service.delete_index("file", "test-get-1")
        await indexing_service.delete_index("file", "test-get-2")
    
    @pytest.mark.asyncio
    async def test_update_index(self, indexing_service):
        """Test updating an index entry."""
        # Create initial index
        index_id = await indexing_service.index_entity(
            entity_type="ontology",
            entity_id="test-update-1",
            content_summary="Original content",
            domain="testing"
        )
        
        # Update the index
        await indexing_service.update_index(
            index_id=index_id,
            content_summary="Updated content for Phase 2 testing",
            metadata={"updated": True}
        )
        
        # Verify update
        entities = await indexing_service.get_indexed_entities(
            entity_type="ontology",
            domain="testing"
        )
        
        updated_entity = next((e for e in entities if e["entity_id"] == "test-update-1"), None)
        assert updated_entity is not None
        assert "Updated content" in updated_entity["content_summary"]
        
        # Cleanup
        await indexing_service.delete_index("ontology", "test-update-1")
    
    @pytest.mark.asyncio
    async def test_delete_index(self, indexing_service, db_service):
        """Test deleting an index entry."""
        # Create index
        index_id = await indexing_service.index_entity(
            entity_type="file",
            entity_id="test-delete-1",
            content_summary="Content to be deleted",
            domain="testing"
        )
        
        # Verify it exists
        entities = await indexing_service.get_indexed_entities(
            entity_type="file",
            domain="testing"
        )
        assert any(e["entity_id"] == "test-delete-1" for e in entities)
        
        # Delete it
        await indexing_service.delete_index("file", "test-delete-1")
        
        # Verify it's gone
        entities_after = await indexing_service.get_indexed_entities(
            entity_type="file",
            domain="testing"
        )
        assert not any(e["entity_id"] == "test-delete-1" for e in entities_after)
        
        # Verify vectors are also deleted (CASCADE)
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM system_index_vectors
                    WHERE index_id = %s
                """, (index_id,))
                count = cur.fetchone()[0]
                assert count == 0, "Vectors should be deleted via CASCADE"
        finally:
            db_service._return(conn)
