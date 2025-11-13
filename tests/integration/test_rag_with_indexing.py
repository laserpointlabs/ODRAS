"""
Integration tests for RAG with system indexing.

Tests RAG integration with IndexingServiceInterface using real services.
"""

import pytest
from backend.rag.core.modular_rag_service import ModularRAGService
from backend.services.system_indexer import SystemIndexer
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.mark.integration
class TestRAGWithIndexing:
    """Tests for RAG integration with system indexing."""
    
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
    async def test_rag_queries_system_index(self, rag_service, indexing_service):
        """Test that RAG queries system index when available."""
        # Index a test entity
        index_id = await indexing_service.index_entity(
            entity_type="file",
            entity_id="test-file-123",
            content_summary="This is a test file about system architecture and requirements.",
            project_id=None,  # Global entity
            domain="requirements"
        )
        
        assert index_id is not None
        
        # Query RAG - should find the indexed entity
        rag_context = await rag_service.query_knowledge_base(
            query="system architecture",
            context={}
        )
        
        # Should have at least one chunk from system index
        system_chunks = [c for c in rag_context.chunks if c.source.source_type == "system"]
        assert len(system_chunks) > 0, "Should retrieve chunks from system index"
        
        # Cleanup
        await indexing_service.delete_index("file", "test-file-123")
    
    @pytest.mark.asyncio
    async def test_rag_system_index_with_project_filter(self, rag_service, indexing_service, db_service):
        """Test that RAG filters system index by project when project_id provided."""
        # Get a test project ID
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM projects LIMIT 1")
                row = cur.fetchone()
                if not row:
                    pytest.skip("No projects available for testing")
                project_id = str(row[0])
        finally:
            db_service._return(conn)
        
        # Index entity with project_id
        index_id = await indexing_service.index_entity(
            entity_type="event",
            entity_id="test-event-456",
            content_summary="Project-specific event about requirements analysis.",
            project_id=project_id,
            domain="requirements"
        )
        
        # Query with project_id - should find it
        rag_context = await rag_service.query_knowledge_base(
            query="requirements analysis",
            context={"project_id": project_id}
        )
        
        system_chunks = [c for c in rag_context.chunks if c.source.source_type == "system"]
        assert len(system_chunks) > 0, "Should retrieve project-scoped system chunks"
        
        # Cleanup
        await indexing_service.delete_index("event", "test-event-456")
    
    @pytest.mark.asyncio
    async def test_rag_without_indexing_service(self, settings, db_service):
        """Test that RAG works without indexing service (backward compatibility)."""
        rag_service = ModularRAGService(
            settings=settings,
            db_service=db_service,
            indexing_service=None  # No indexing service
        )
        
        # Should work without errors
        rag_context = await rag_service.query_knowledge_base(
            query="test query",
            context={}
        )
        
        assert rag_context is not None
        # Should not have system chunks
        system_chunks = [c for c in rag_context.chunks if c.source.source_type == "system"]
        assert len(system_chunks) == 0, "Should not have system chunks without indexing service"
