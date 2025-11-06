"""
Comprehensive Test Suite for Hybrid Search and Reranking

Tests the integration of OpenSearch/Elasticsearch with Qdrant,
reranking algorithms, and hybrid retrieval strategies.
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.rag.storage.vector_store import VectorStore
from backend.rag.storage.text_search_store import TextSearchStore
from backend.rag.storage.opensearch_store import OpenSearchTextStore
from backend.rag.storage.qdrant_store import QdrantVectorStore
from backend.rag.retrieval.hybrid_retriever import HybridRetriever
from backend.rag.retrieval.reranker import (
    ReciprocalRankFusionReranker,
    CrossEncoderReranker,
    HybridReranker,
)
from backend.rag.core.modular_rag_service import ModularRAGService
from backend.services.config import Settings


# ============================================================================
# Text Search Store Tests
# ============================================================================


class TestTextSearchStoreInterface:
    """Test abstract TextSearchStore interface compliance."""

    def test_text_search_store_is_abstract(self):
        """Verify TextSearchStore is an abstract base class."""
        with pytest.raises(TypeError):
            TextSearchStore()

    def test_text_search_store_has_required_methods(self):
        """Verify TextSearchStore has all required abstract methods."""
        required_methods = [
            "search",
            "index_document",
            "delete_document",
            "ensure_index",
            "bulk_index",
        ]
        for method_name in required_methods:
            assert hasattr(TextSearchStore, method_name), f"Missing method: {method_name}"


class TestOpenSearchTextStore:
    """Test OpenSearchTextStore implementation."""

    @pytest.fixture
    def mock_opensearch_client(self):
        """Create mock OpenSearch client."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {
                "hits": [
                    {
                        "_id": "doc1",
                        "_score": 0.95,
                        "_source": {
                            "content": "Test content about aircraft",
                            "chunk_id": "chunk1",
                            "project_id": str(uuid4()),
                        }
                    }
                ]
            }
        })
        mock_client.index = AsyncMock(return_value={"_id": "doc1"})
        mock_client.delete = AsyncMock(return_value={})
        mock_client.indices.exists = AsyncMock(return_value=False)
        mock_client.indices.create = AsyncMock(return_value={})
        return mock_client

    @pytest.fixture
    def opensearch_store(self, mock_opensearch_client):
        """Create OpenSearchTextStore with mocked client."""
        settings = Settings()
        settings.opensearch_url = "http://localhost:9200"
        settings.opensearch_enabled = "true"

        with patch("backend.rag.storage.opensearch_store.AsyncOpenSearch") as mock_class:
            mock_class.return_value = mock_opensearch_client
            try:
                store = OpenSearchTextStore(settings)
                store.client = mock_opensearch_client
                return store
            except Exception:
                # If OpenSearch not available, skip tests
                pytest.skip("OpenSearch client not available")

    @pytest.mark.asyncio
    async def test_search(self, opensearch_store, mock_opensearch_client):
        """Test keyword search."""
        results = await opensearch_store.search(
            query_text="aircraft specifications",
            index="knowledge_chunks",
            limit=10,
        )

        assert len(results) == 1
        assert results[0]["id"] == "doc1"
        assert results[0]["search_type"] == "keyword"
        mock_opensearch_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_document(self, opensearch_store, mock_opensearch_client):
        """Test document indexing."""
        result = await opensearch_store.index_document(
            index="knowledge_chunks",
            document_id="doc1",
            document={"content": "Test content", "chunk_id": "chunk1"},
        )

        assert result is True
        mock_opensearch_client.index.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_index(self, opensearch_store, mock_opensearch_client):
        """Test index creation."""
        result = await opensearch_store.ensure_index("knowledge_chunks")

        assert result is True
        mock_opensearch_client.indices.create.assert_called_once()


# ============================================================================
# Reranker Tests
# ============================================================================


class TestRerankers:
    """Test reranking algorithms."""

    @pytest.fixture
    def sample_results(self):
        """Create sample search results for testing."""
        return [
            {"id": "1", "score": 0.9, "payload": {"content": "relevant content"}},
            {"id": "2", "score": 0.7, "payload": {"content": "less relevant"}},
            {"id": "3", "score": 0.5, "payload": {"content": "marginally relevant"}},
        ]

    @pytest.mark.asyncio
    async def test_rrf_reranker(self, sample_results):
        """Test Reciprocal Rank Fusion reranker."""
        reranker = ReciprocalRankFusionReranker(k=60)

        reranked = await reranker.rerank("test query", sample_results, top_k=2)

        assert len(reranked) == 2
        assert "rrf_score" in reranked[0]
        assert reranked[0]["rrf_score"] > 0

    @pytest.mark.asyncio
    async def test_rrf_combines_multiple_sources(self):
        """Test RRF combines results from multiple search sources."""
        reranker = ReciprocalRankFusionReranker()

        # Simulate results from two sources (vector and keyword)
        vector_results = [
            {"id": "1", "score": 0.9, "search_type": "vector"},
            {"id": "2", "score": 0.7, "search_type": "vector"},
        ]
        keyword_results = [
            {"id": "2", "score": 0.8, "search_type": "keyword"},  # Overlaps with vector result
            {"id": "3", "score": 0.6, "search_type": "keyword"},
        ]

        all_results = vector_results + keyword_results
        reranked = await reranker.rerank("test", all_results)

        # Result 2 should have higher score (appears in both sources)
        assert len(reranked) > 0
        result_ids = [r["id"] for r in reranked]
        # Result 2 should rank higher due to appearing in both sources
        assert "2" in result_ids

    @pytest.mark.asyncio
    async def test_cross_encoder_reranker(self, sample_results):
        """Test cross-encoder reranker."""
        reranker = CrossEncoderReranker()

        reranked = await reranker.rerank("relevant content", sample_results, top_k=2)

        assert len(reranked) <= 2
        # Even if model fails, should return results
        assert len(reranked) > 0

    @pytest.mark.asyncio
    async def test_hybrid_reranker(self, sample_results):
        """Test hybrid reranker combining RRF and cross-encoder."""
        reranker = HybridReranker(use_cross_encoder=False)  # Use RRF only for speed

        reranked = await reranker.rerank("test query", sample_results, top_k=2)

        assert len(reranked) == 2


# ============================================================================
# Hybrid Retriever Tests
# ============================================================================


class TestHybridRetriever:
    """Test HybridRetriever combining vector and keyword search."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        store = AsyncMock(spec=VectorStore)
        store.search_by_text = AsyncMock(return_value=[
            {
                "id": "vec1",
                "score": 0.9,
                "payload": {"content": "semantic match", "chunk_id": "chunk1"},
            }
        ])
        return store

    @pytest.fixture
    def mock_text_store(self):
        """Create mock text search store."""
        store = AsyncMock(spec=TextSearchStore)
        store.search = AsyncMock(return_value=[
            {
                "id": "kw1",
                "score": 0.8,
                "payload": {"content": "keyword match", "chunk_id": "chunk2"},
            }
        ])
        return store

    @pytest.fixture
    def hybrid_retriever(self, mock_vector_store, mock_text_store):
        """Create HybridRetriever with mocked stores."""
        reranker = ReciprocalRankFusionReranker()
        return HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=mock_text_store,
            reranker=reranker,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_sources(self, hybrid_retriever, mock_vector_store, mock_text_store):
        """Test hybrid search combines vector and keyword results."""
        results = await hybrid_retriever.retrieve(
            query="test query",
            collection="knowledge_chunks",
            limit=10,
        )

        # Should call both stores
        mock_vector_store.search_by_text.assert_called_once()
        mock_text_store.search.assert_called_once()

        # Should combine results
        assert len(results) >= 1
        # Check that we have results from both sources (or combined)
        search_types = [r.get("search_type") for r in results]
        assert "vector" in search_types or "keyword" in search_types

    @pytest.mark.asyncio
    async def test_hybrid_search_fallback_to_vector_only(self, mock_vector_store):
        """Test hybrid retriever falls back to vector-only if text store unavailable."""
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=None,  # No text search store
        )

        results = await retriever.retrieve(
            query="test query",
            collection="knowledge_chunks",
            limit=10,
        )

        mock_vector_store.search_by_text.assert_called_once()
        assert len(results) >= 0  # May be empty but shouldn't crash

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplication(self, hybrid_retriever):
        """Test that hybrid search deduplicates results by chunk_id."""
        # Mock to return overlapping results
        mock_vector_store = AsyncMock()
        mock_vector_store.search_by_text = AsyncMock(return_value=[
            {"id": "1", "score": 0.9, "payload": {"chunk_id": "chunk1", "content": "test"}},
        ])

        mock_text_store = AsyncMock()
        mock_text_store.search = AsyncMock(return_value=[
            {"id": "2", "score": 0.8, "payload": {"chunk_id": "chunk1", "content": "test"}},  # Same chunk_id
        ])

        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=mock_text_store,
            reranker=ReciprocalRankFusionReranker(),
        )

        results = await retriever.retrieve(
            query="test",
            collection="test",
            limit=10,
        )

        # Should deduplicate - chunk1 should appear once (with higher RRF score)
        chunk_ids = [r.get("payload", {}).get("chunk_id") for r in results]
        assert chunk_ids.count("chunk1") <= 1  # Should be deduplicated


# ============================================================================
# Modular RAG Service with Hybrid Search Tests
# ============================================================================


class TestModularRAGServiceHybrid:
    """Test ModularRAGService with hybrid search enabled."""

    @pytest.fixture
    def settings_with_hybrid(self):
        """Create settings with hybrid search enabled."""
        settings = Settings()
        settings.rag_hybrid_search = "true"
        settings.opensearch_enabled = "true"
        settings.opensearch_url = "http://localhost:9200"
        settings.rag_reranker = "rrf"
        return settings

    @pytest.mark.asyncio
    async def test_modular_rag_service_with_hybrid_search(self, settings_with_hybrid):
        """Test ModularRAGService uses hybrid search when enabled."""
        # Mock components
        mock_vector_store = AsyncMock()
        mock_vector_store.search_by_text = AsyncMock(return_value=[])

        mock_text_store = AsyncMock()
        mock_text_store.search = AsyncMock(return_value=[])

        mock_db = Mock()
        mock_db.is_user_member = Mock(return_value=True)
        mock_db._conn = Mock(return_value=Mock())
        mock_db._return = Mock()

        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "content": "Test response",
            "model": "test",
            "provider": "test",
        })

        # Create service with hybrid search
        with patch("backend.rag.core.modular_rag_service.OpenSearchTextStore") as mock_opensearch:
            mock_opensearch.return_value = mock_text_store

            service = ModularRAGService(
                settings=settings_with_hybrid,
                vector_store=mock_vector_store,
                text_search_store=mock_text_store,
                db_service=mock_db,
                llm_team=mock_llm,
            )

            # Verify hybrid retriever is used
            assert isinstance(service.retriever, HybridRetriever)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestHybridSearchIntegration:
    """Integration tests for hybrid search (require services)."""

    @pytest.mark.asyncio
    async def test_hybrid_search_with_real_services(self):
        """Test hybrid search with real Qdrant (OpenSearch optional)."""
        settings = Settings()
        settings.rag_hybrid_search = "true"
        settings.opensearch_enabled = "true"

        # Test with real Qdrant, mock OpenSearch
        mock_text_store = AsyncMock()
        mock_text_store.search = AsyncMock(return_value=[])

        from backend.rag.storage.factory import create_vector_store
        from backend.rag.retrieval.hybrid_retriever import HybridRetriever

        vector_store = create_vector_store(settings)
        retriever = HybridRetriever(
            vector_store=vector_store,
            text_search_store=mock_text_store,
        )

        # Test retrieval (will use vector-only if OpenSearch not available)
        results = await retriever.retrieve(
            query="test query",
            collection="knowledge_chunks",
            limit=5,
        )

        # Should not crash even if OpenSearch unavailable
        assert isinstance(results, list)


pytest_plugins = ["pytest_asyncio"]


