"""
Comprehensive Test Suite for Modular RAG Implementation

Tests all components of the modular RAG architecture:
- Vector store interfaces
- Retriever implementations
- Modular RAG service
- Integration with existing systems
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from backend.rag.storage.vector_store import VectorStore
from backend.rag.storage.qdrant_store import QdrantVectorStore
from backend.rag.storage.factory import create_vector_store
from backend.rag.retrieval.retriever import Retriever
from backend.rag.retrieval.vector_retriever import VectorRetriever
from backend.rag.core.modular_rag_service import ModularRAGService
from backend.services.config import Settings


# ============================================================================
# Vector Store Tests
# ============================================================================


class TestVectorStoreInterface:
    """Test abstract VectorStore interface compliance."""

    def test_vector_store_is_abstract(self):
        """Verify VectorStore is an abstract base class."""
        with pytest.raises(TypeError):
            VectorStore()

    def test_vector_store_has_required_methods(self):
        """Verify VectorStore has all required abstract methods."""
        required_methods = [
            "search",
            "search_by_text",
            "store",
            "ensure_collection",
            "delete_vectors",
            "get_collection_info",
        ]
        for method_name in required_methods:
            assert hasattr(VectorStore, method_name), f"Missing method: {method_name}"


class TestQdrantVectorStore:
    """Test QdrantVectorStore implementation."""

    @pytest.fixture
    def mock_qdrant_service(self):
        """Create mock QdrantService."""
        mock_service = Mock()
        mock_service.search_vectors = Mock(return_value=[])
        mock_service.search_similar_chunks = AsyncMock(return_value=[])
        mock_service.store_vectors = Mock(return_value=[])
        mock_service.ensure_collection = Mock(return_value=True)
        mock_service.delete_vectors = Mock(return_value=True)
        mock_service.get_collection_info = Mock(return_value={})
        return mock_service

    @pytest.fixture
    def qdrant_store(self, mock_qdrant_service):
        """Create QdrantVectorStore with mocked service."""
        settings = Settings()
        store = QdrantVectorStore(settings)
        store.qdrant_service = mock_qdrant_service
        return store

    @pytest.mark.asyncio
    async def test_search_by_text(self, qdrant_store, mock_qdrant_service):
        """Test text-based search."""
        mock_qdrant_service.search_similar_chunks.return_value = [
            {"id": "1", "score": 0.9, "payload": {"content": "test"}}
        ]

        results = await qdrant_store.search_by_text(
            query_text="test query",
            collection="test_collection",
            limit=10,
        )

        assert len(results) == 1
        assert results[0]["id"] == "1"
        mock_qdrant_service.search_similar_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_vectors(self, qdrant_store, mock_qdrant_service):
        """Test vector storage."""
        vectors = [
            {
                "id": "vec1",
                "vector": [0.1, 0.2, 0.3],
                "payload": {"content": "test"},
            }
        ]
        mock_qdrant_service.store_vectors.return_value = ["vec1"]

        stored_ids = await qdrant_store.store(
            collection="test_collection",
            vectors=vectors,
        )

        assert stored_ids == ["vec1"]
        mock_qdrant_service.store_vectors.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection(self, qdrant_store, mock_qdrant_service):
        """Test collection creation."""
        result = await qdrant_store.ensure_collection(
            collection="test_collection",
            vector_size=384,
        )

        assert result is True
        mock_qdrant_service.ensure_collection.assert_called_once()


class TestVectorStoreFactory:
    """Test vector store factory."""

    def test_create_qdrant_store(self):
        """Test factory creates QdrantVectorStore by default."""
        store = create_vector_store()
        assert isinstance(store, QdrantVectorStore)

    def test_create_qdrant_store_explicit(self):
        """Test factory creates QdrantVectorStore when specified."""
        settings = Settings()
        setattr(settings, "vector_store_backend", "qdrant")
        store = create_vector_store(settings)
        assert isinstance(store, QdrantVectorStore)

    def test_factory_raises_for_unknown_backend(self):
        """Test factory raises error for unknown backend."""
        settings = Settings()
        setattr(settings, "vector_store_backend", "unknown")
        with pytest.raises(ValueError):
            create_vector_store(settings)


# ============================================================================
# Retriever Tests
# ============================================================================


class TestRetrieverInterface:
    """Test abstract Retriever interface."""

    def test_retriever_is_abstract(self):
        """Verify Retriever is an abstract base class."""
        with pytest.raises(TypeError):
            Retriever()


class TestVectorRetriever:
    """Test VectorRetriever implementation."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock VectorStore."""
        store = AsyncMock(spec=VectorStore)
        store.search_by_text = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def vector_retriever(self, mock_vector_store):
        """Create VectorRetriever with mocked store."""
        return VectorRetriever(mock_vector_store)

    @pytest.mark.asyncio
    async def test_retrieve(self, vector_retriever, mock_vector_store):
        """Test single collection retrieval."""
        mock_vector_store.search_by_text.return_value = [
            {"id": "1", "score": 0.9, "payload": {"content": "test"}}
        ]

        results = await vector_retriever.retrieve(
            query="test query",
            collection="test_collection",
            limit=10,
        )

        assert len(results) == 1
        mock_vector_store.search_by_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_multiple_collections(self, vector_retriever, mock_vector_store):
        """Test multiple collection retrieval."""
        mock_vector_store.search_by_text.return_value = [
            {"id": "1", "score": 0.9, "payload": {"content": "test"}}
        ]

        results = await vector_retriever.retrieve_multiple_collections(
            query="test query",
            collections=["col1", "col2"],
            limit_per_collection=5,
        )

        assert "col1" in results
        assert "col2" in results
        assert len(results["col1"]) == 1
        assert mock_vector_store.search_by_text.call_count == 2


# ============================================================================
# Modular RAG Service Tests
# ============================================================================


class TestModularRAGService:
    """Test ModularRAGService with mocked dependencies."""

    @pytest.fixture
    def mock_retriever(self):
        """Create mock retriever."""
        retriever = AsyncMock(spec=Retriever)
        retriever.retrieve_multiple_collections = AsyncMock(return_value={
            "knowledge_chunks": [
                {
                    "id": "1",
                    "score": 0.9,
                    "payload": {
                        "chunk_id": str(uuid4()),
                        "asset_id": str(uuid4()),
                        "project_id": str(uuid4()),
                        "content": "Test content about aircraft",
                    },
                }
            ],
            "knowledge_chunks_768": [],
        })
        return retriever

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        db = Mock()
        db.is_user_member = Mock(return_value=True)
        db._conn = Mock(return_value=Mock())
        db._return = Mock()
        return db

    @pytest.fixture
    def mock_llm_team(self):
        """Create mock LLM team."""
        llm = AsyncMock()
        llm.generate_response = AsyncMock(return_value={"content": "Test response"})
        return llm

    @pytest.fixture
    def rag_service(self, mock_retriever, mock_db_service, mock_llm_team):
        """Create ModularRAGService with mocked dependencies."""
        settings = Settings()
        service = ModularRAGService(
            settings=settings,
            retriever=mock_retriever,
            db_service=mock_db_service,
            llm_team=mock_llm_team,
        )
        return service

    @pytest.mark.asyncio
    async def test_query_knowledge_base(self, rag_service):
        """Test basic query functionality."""
        result = await rag_service.query_knowledge_base(
            question="What is an aircraft?",
            user_id=str(uuid4()),
            max_chunks=5,
        )

        assert result["success"] is True
        assert "response" in result
        assert result["chunks_found"] > 0

    @pytest.mark.asyncio
    async def test_query_with_project_filter(self, rag_service, mock_retriever):
        """Test query with project filtering."""
        project_id = str(uuid4())
        result = await rag_service.query_knowledge_base(
            question="Test question",
            project_id=project_id,
            user_id=str(uuid4()),
        )

        assert result["success"] is True
        # Verify metadata filter was passed
        call_args = mock_retriever.retrieve_multiple_collections.call_args
        assert call_args[1]["metadata_filter"]["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_query_no_results(self, rag_service, mock_retriever):
        """Test query when no results found."""
        mock_retriever.retrieve_multiple_collections.return_value = {
            "knowledge_chunks": [],
            "knowledge_chunks_768": [],
        }

        result = await rag_service.query_knowledge_base(
            question="Nonexistent topic",
            user_id=str(uuid4()),
        )

        assert result["success"] is True
        assert result["chunks_found"] == 0
        assert "couldn't find" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_response_styles(self, rag_service):
        """Test different response styles."""
        for style in ["comprehensive", "concise", "technical"]:
            result = await rag_service.query_knowledge_base(
                question="Test question",
                user_id=str(uuid4()),
                response_style=style,
            )
            assert result["response_style"] == style

    @pytest.mark.asyncio
    async def test_sql_read_through_enabled(self, rag_service, mock_db_service):
        """Test SQL read-through enrichment."""
        # Set SQL read-through enabled
        rag_service.sql_read_through = True

        # Mock SQL query results
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"chunk_id": "test-id", "text": "SQL content"}
        ]
        mock_db_service._conn.return_value = mock_conn

        # Mock get_chunks_by_ids at module level
        from backend import db
        db.queries.get_chunks_by_ids = Mock(return_value=[
            {"chunk_id": "test-id", "text": "SQL content"}
        ])

        result = await rag_service.query_knowledge_base(
            question="Test question",
            user_id=str(uuid4()),
        )

        assert result["success"] is True


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestRAGIntegration:
    """Integration tests requiring real services (marked for CI)."""

    @pytest.mark.asyncio
    async def test_end_to_end_rag_query(self):
        """Test end-to-end RAG query with real services."""
        # This test requires:
        # - ODRAS API running
        # - Qdrant running
        # - Test project with knowledge assets
        # - DAS service account

        import httpx

        # Authenticate
        async with httpx.AsyncClient(timeout=30.0) as client:
            login_resp = await client.post(
                "http://localhost:8000/api/auth/login",
                json={
                    "username": "das_service",
                    "password": "das_service_2024!",
                },
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["token"]

            # Create test project
            project_resp = await client.post(
                "http://localhost:8000/api/projects",
                json={"name": f"RAG Test {uuid4()}"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert project_resp.status_code == 200
            project_id = project_resp.json()["project"]["project_id"]

            # Test RAG query via API
            rag_resp = await client.post(
                "http://localhost:8000/api/knowledge/query",
                json={
                    "question": "What is the test project?",
                    "project_id": project_id,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should succeed (even if no results)
            assert rag_resp.status_code == 200
            rag_data = rag_resp.json()
            assert "response" in rag_data or "error" in rag_data

    @pytest.mark.asyncio
    async def test_modular_rag_service_with_real_components(self):
        """Test ModularRAGService with real (non-mocked) components."""
        settings = Settings()

        # Create service with real components
        service = ModularRAGService(settings)

        # Test query (may not have data, but should not crash)
        result = await service.query_knowledge_base(
            question="Test question",
            user_id="test_user",
            max_chunks=5,
        )

        # Should return valid result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "response" in result or "error" in result


# ============================================================================
# Test Configuration
# ============================================================================

pytest_plugins = ["pytest_asyncio"]

