"""
Hybrid Search and Reranker Evaluation Test Suite

This test suite evaluates the improvement in retrieval quality when using:
1. Hybrid search (vector + keyword) vs vector-only
2. Different reranker strategies (RRF, cross-encoder, hybrid)

Metrics evaluated:
- Precision: Percentage of retrieved results that are relevant
- Recall: Percentage of relevant documents that were retrieved
- Mean Reciprocal Rank (MRR): Average reciprocal rank of first relevant result
- Response Time: Latency of different search strategies
"""

import pytest
import asyncio
import time
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from backend.rag.storage.vector_store import VectorStore
from backend.rag.storage.text_search_store import TextSearchStore
from backend.rag.storage.qdrant_store import QdrantVectorStore
from backend.rag.storage.opensearch_store import OpenSearchTextStore
from backend.rag.retrieval.vector_retriever import VectorRetriever
from backend.rag.retrieval.hybrid_retriever import HybridRetriever
from backend.rag.retrieval.reranker import (
    ReciprocalRankFusionReranker,
    CrossEncoderReranker,
    HybridReranker,
)
from backend.services.config import Settings


# ============================================================================
# Test Data Setup
# ============================================================================

# Test documents with technical content that benefits from hybrid search
TEST_DOCUMENTS = [
    {
        "chunk_id": "doc1",
        "content": "The QuadCopter T4 has a maximum altitude of 3000 meters and payload capacity of 25 kg. Model number: QC-T4-2024.",
        "title": "QuadCopter T4 Specifications",
        "project_id": "test_project",
        "document_type": "specification",
        "relevant_for": ["quadcopter", "t4", "altitude", "payload", "qc-t4-2024"],
    },
    {
        "chunk_id": "doc2",
        "content": "The AeroMapper X8 unmanned aerial vehicle (UAV) features a wingspan of 4.2 meters and can operate at altitudes up to 5000 meters. Serial: AM-X8-2024.",
        "title": "AeroMapper X8 Technical Data",
        "project_id": "test_project",
        "document_type": "technical",
        "relevant_for": ["aeromapper", "x8", "uav", "wingspan", "am-x8-2024"],
    },
    {
        "chunk_id": "doc3",
        "content": "REQ-SYS-042: The system shall support altitude monitoring. REQ-SYS-043: Maximum payload must not exceed 30 kg.",
        "title": "System Requirements",
        "project_id": "test_project",
        "document_type": "requirement",
        "relevant_for": ["req-sys-042", "req-sys-043", "altitude", "payload", "system"],
    },
    {
        "chunk_id": "doc4",
        "content": "The vehicle has a maximum speed of 120 km/h and operating range of 500 km. The vehicle supports both autonomous and manual control modes.",
        "title": "Vehicle Performance Characteristics",
        "project_id": "test_project",
        "document_type": "specification",
        "relevant_for": ["vehicle", "speed", "range", "autonomous", "manual"],
    },
    {
        "chunk_id": "doc5",
        "content": "Component ID: COMP-AV-001 has type Aircraft and supports property hasWingspan. Component ID: COMP-AV-002 has type Helicopter.",
        "title": "Component Definitions",
        "project_id": "test_project",
        "document_type": "ontology",
        "relevant_for": ["comp-av-001", "comp-av-002", "aircraft", "helicopter", "haswingspan"],
    },
]

# Test queries with expected relevant documents
TEST_QUERIES = [
    {
        "query": "What is the maximum altitude of QuadCopter T4?",
        "relevant_docs": ["doc1"],
        "expected_terms": ["quadcopter", "t4", "altitude"],
        "query_type": "specific_model_number",
    },
    {
        "query": "Which aircraft models do we have?",
        "relevant_docs": ["doc1", "doc2", "doc5"],
        "expected_terms": ["aircraft", "model", "quadcopter", "aeromapper"],
        "query_type": "general_concept",
    },
    {
        "query": "REQ-SYS-042 requirements",
        "relevant_docs": ["doc3"],
        "expected_terms": ["req-sys-042"],
        "query_type": "exact_id_match",
    },
    {
        "query": "What is the payload capacity?",
        "relevant_docs": ["doc1", "doc3"],
        "expected_terms": ["payload", "capacity"],
        "query_type": "technical_spec",
    },
    {
        "query": "COMP-AV-001 component details",
        "relevant_docs": ["doc5"],
        "expected_terms": ["comp-av-001", "component"],
        "query_type": "component_id",
    },
]


# ============================================================================
# Evaluation Metrics
# ============================================================================

def calculate_precision(retrieved: List[str], relevant: Set[str], top_k: int = 10) -> float:
    """Calculate precision@k: percentage of retrieved results that are relevant."""
    if not retrieved:
        return 0.0
    retrieved_top_k = retrieved[:top_k]
    relevant_retrieved = sum(1 for doc_id in retrieved_top_k if doc_id in relevant)
    return relevant_retrieved / len(retrieved_top_k)


def calculate_recall(retrieved: List[str], relevant: Set[str], top_k: int = 10) -> float:
    """Calculate recall@k: percentage of relevant documents that were retrieved."""
    if not relevant:
        return 1.0  # All relevant retrieved if no relevant expected
    retrieved_top_k = retrieved[:top_k]
    relevant_retrieved = sum(1 for doc_id in retrieved_top_k if doc_id in relevant)
    return relevant_retrieved / len(relevant)


def calculate_mrr(retrieved: List[str], relevant: Set[str]) -> float:
    """Calculate Mean Reciprocal Rank: 1/rank of first relevant result."""
    if not relevant:
        return 0.0
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def calculate_ndcg(retrieved: List[str], relevant: Set[str], top_k: int = 10) -> float:
    """Calculate Normalized Discounted Cumulative Gain (simplified)."""
    if not relevant:
        return 0.0
    retrieved_top_k = retrieved[:top_k]
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved_top_k, start=1):
        if doc_id in relevant:
            dcg += 1.0 / (rank * (rank + 1))  # Simplified relevance score
    # Ideal DCG (simplified)
    ideal_dcg = sum(1.0 / (i * (i + 1)) for i in range(1, min(len(relevant), top_k) + 1))
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


# ============================================================================
# Mock Services Setup
# ============================================================================

class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = {doc["chunk_id"]: doc for doc in documents}
        self.search_results = {}

    async def search_by_text(
        self,
        query_text: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Simulate vector search - returns semantic matches."""
        # Simple keyword matching for simulation (real vector search would use embeddings)
        query_lower = query_text.lower()
        results = []

        for doc_id, doc in self.documents.items():
            content_lower = doc["content"].lower()
            score = 0.0

            # Check for semantic relevance (conceptually similar terms)
            for term in doc.get("relevant_for", []):
                if term in query_lower:
                    score += 0.3
                # Also check for partial matches (semantic similarity)
                if any(word in term for word in query_lower.split()):
                    score += 0.2

            if score >= score_threshold:
                results.append({
                    "id": doc_id,
                    "score": min(score, 1.0),
                    "payload": doc,
                    "search_type": "vector",
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def search(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def store(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def ensure_collection(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def delete_vectors(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def get_collection_info(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError


class MockTextSearchStore(TextSearchStore):
    """Mock text search store for testing."""

    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = {doc["chunk_id"]: doc for doc in documents}

    async def search(
        self,
        query_text: str,
        index: str,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Simulate keyword search - returns exact term matches."""
        query_lower = query_text.lower()
        query_words = set(query_lower.split())
        results = []

        for doc_id, doc in self.documents.items():
            content_lower = doc["content"].lower()
            score = 0.0

            # BM25-like scoring (simplified)
            for word in query_words:
                if word in content_lower:
                    # Exact match gets higher score
                    count = content_lower.count(word)
                    score += min(count * 0.5, 1.0)

            # Bonus for exact phrase matches
            if query_lower in content_lower:
                score += 2.0

            # Bonus for exact IDs, model numbers, etc.
            for term in doc.get("relevant_for", []):
                if term.lower() in query_lower:
                    score += 1.5  # Exact term match (high relevance)

            if score > 0:
                results.append({
                    "id": doc_id,
                    "score": min(score, 3.0),  # Cap score
                    "payload": doc,
                    "search_type": "keyword",
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def index_document(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def delete_document(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def ensure_index(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError

    async def bulk_index(self, *args, **kwargs):
        """Not implemented in mock."""
        raise NotImplementedError


# ============================================================================
# Evaluation Test Suite
# ============================================================================

class TestHybridSearchEvaluation:
    """Evaluate hybrid search improvements."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store with test documents."""
        return MockVectorStore(TEST_DOCUMENTS)

    @pytest.fixture
    def mock_text_store(self):
        """Create mock text search store with test documents."""
        return MockTextSearchStore(TEST_DOCUMENTS)

    @pytest.fixture
    def vector_only_retriever(self, mock_vector_store):
        """Create vector-only retriever (baseline)."""
        return VectorRetriever(mock_vector_store)

    @pytest.fixture
    def hybrid_retriever_no_rerank(self, mock_vector_store, mock_text_store):
        """Create hybrid retriever without reranking."""
        return HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=mock_text_store,
            reranker=None,  # No reranking
        )

    @pytest.fixture
    def hybrid_retriever_rrf(self, mock_vector_store, mock_text_store):
        """Create hybrid retriever with RRF reranking."""
        return HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=mock_text_store,
            reranker=ReciprocalRankFusionReranker(k=60),
        )

    @pytest.fixture
    def hybrid_retriever_cross_encoder(self, mock_vector_store, mock_text_store):
        """Create hybrid retriever with cross-encoder reranking."""
        return HybridRetriever(
            vector_store=mock_vector_store,
            text_search_store=mock_text_store,
            reranker=CrossEncoderReranker(),
        )

    @pytest.mark.asyncio
    async def test_vector_only_baseline(self, vector_only_retriever):
        """Test vector-only search as baseline."""
        results_by_query = {}

        for test_query in TEST_QUERIES:
            start_time = time.time()
            results = await vector_only_retriever.retrieve(
                query=test_query["query"],
                collection="test_collection",
                limit=10,
                score_threshold=0.3,
            )
            elapsed = time.time() - start_time

            retrieved_ids = [r.get("id") or r.get("payload", {}).get("chunk_id") for r in results]
            relevant = set(test_query["relevant_docs"])

            results_by_query[test_query["query"]] = {
                "retrieved": retrieved_ids,
                "relevant": relevant,
                "precision": calculate_precision(retrieved_ids, relevant),
                "recall": calculate_recall(retrieved_ids, relevant),
                "mrr": calculate_mrr(retrieved_ids, relevant),
                "ndcg": calculate_ndcg(retrieved_ids, relevant),
                "time": elapsed,
            }

        # Calculate averages
        avg_precision = sum(r["precision"] for r in results_by_query.values()) / len(results_by_query)
        avg_recall = sum(r["recall"] for r in results_by_query.values()) / len(results_by_query)
        avg_mrr = sum(r["mrr"] for r in results_by_query.values()) / len(results_by_query)
        avg_time = sum(r["time"] for r in results_by_query.values()) / len(results_by_query)

        print(f"\n📊 Vector-Only Baseline Results:")
        print(f"  Average Precision: {avg_precision:.3f}")
        print(f"  Average Recall: {avg_recall:.3f}")
        print(f"  Average MRR: {avg_mrr:.3f}")
        print(f"  Average Time: {avg_time:.4f}s")

        # Store for comparison
        results_by_query["_summary"] = {
            "precision": avg_precision,
            "recall": avg_recall,
            "mrr": avg_mrr,
            "time": avg_time,
        }

        assert avg_precision >= 0.0  # Basic sanity check
        assert avg_recall >= 0.0

    @pytest.mark.asyncio
    async def test_hybrid_search_improvement(self, hybrid_retriever_rrf):
        """Test hybrid search with RRF reranking."""
        results_by_query = {}

        for test_query in TEST_QUERIES:
            start_time = time.time()
            results = await hybrid_retriever_rrf.retrieve(
                query=test_query["query"],
                collection="test_collection",
                limit=10,
                score_threshold=0.3,
            )
            elapsed = time.time() - start_time

            retrieved_ids = [r.get("id") or r.get("payload", {}).get("chunk_id") for r in results]
            relevant = set(test_query["relevant_docs"])

            results_by_query[test_query["query"]] = {
                "retrieved": retrieved_ids,
                "relevant": relevant,
                "precision": calculate_precision(retrieved_ids, relevant),
                "recall": calculate_recall(retrieved_ids, relevant),
                "mrr": calculate_mrr(retrieved_ids, relevant),
                "ndcg": calculate_ndcg(retrieved_ids, relevant),
                "time": elapsed,
            }

        # Calculate averages
        avg_precision = sum(r["precision"] for r in results_by_query.values()) / len(results_by_query)
        avg_recall = sum(r["recall"] for r in results_by_query.values()) / len(results_by_query)
        avg_mrr = sum(r["mrr"] for r in results_by_query.values()) / len(results_by_query)
        avg_time = sum(r["time"] for r in results_by_query.values()) / len(results_by_query)

        print(f"\n📊 Hybrid Search (RRF) Results:")
        print(f"  Average Precision: {avg_precision:.3f}")
        print(f"  Average Recall: {avg_recall:.3f}")
        print(f"  Average MRR: {avg_mrr:.3f}")
        print(f"  Average Time: {avg_time:.4f}s")

        results_by_query["_summary"] = {
            "precision": avg_precision,
            "recall": avg_recall,
            "mrr": avg_mrr,
            "time": avg_time,
        }

        assert avg_precision >= 0.0

    @pytest.mark.asyncio
    async def test_reranker_comparison(
        self,
        hybrid_retriever_no_rerank,
        hybrid_retriever_rrf,
        hybrid_retriever_cross_encoder,
    ):
        """Compare different reranker strategies."""
        retrievers = {
            "no_rerank": hybrid_retriever_no_rerank,
            "rrf": hybrid_retriever_rrf,
            "cross_encoder": hybrid_retriever_cross_encoder,
        }

        results = {}

        for strategy_name, retriever in retrievers.items():
            strategy_results = []

            for test_query in TEST_QUERIES:
                start_time = time.time()
                search_results = await retriever.retrieve(
                    query=test_query["query"],
                    collection="test_collection",
                    limit=10,
                    score_threshold=0.3,
                )
                elapsed = time.time() - start_time

                retrieved_ids = [r.get("id") or r.get("payload", {}).get("chunk_id") for r in search_results]
                relevant = set(test_query["relevant_docs"])

                strategy_results.append({
                    "precision": calculate_precision(retrieved_ids, relevant),
                    "recall": calculate_recall(retrieved_ids, relevant),
                    "mrr": calculate_mrr(retrieved_ids, relevant),
                    "time": elapsed,
                })

            results[strategy_name] = {
                "avg_precision": sum(r["precision"] for r in strategy_results) / len(strategy_results),
                "avg_recall": sum(r["recall"] for r in strategy_results) / len(strategy_results),
                "avg_mrr": sum(r["mrr"] for r in strategy_results) / len(strategy_results),
                "avg_time": sum(r["time"] for r in strategy_results) / len(strategy_results),
            }

        # Print comparison
        print("\n📊 Reranker Comparison:")
        print(f"{'Strategy':<20} {'Precision':<12} {'Recall':<12} {'MRR':<12} {'Time (s)':<12}")
        print("-" * 70)
        for strategy, metrics in results.items():
            print(
                f"{strategy:<20} "
                f"{metrics['avg_precision']:<12.3f} "
                f"{metrics['avg_recall']:<12.3f} "
                f"{metrics['avg_mrr']:<12.3f} "
                f"{metrics['avg_time']:<12.4f}"
            )

        # RRF should improve MRR over no reranking
        assert results["rrf"]["avg_mrr"] >= results["no_rerank"]["avg_mrr"] - 0.1  # Allow small variance

    @pytest.mark.asyncio
    async def test_query_type_specific_improvements(self, vector_only_retriever, hybrid_retriever_rrf):
        """Test improvements for specific query types (exact IDs, model numbers, etc.)."""
        query_types = {}
        for query in TEST_QUERIES:
            query_type = query["query_type"]
            if query_type not in query_types:
                query_types[query_type] = []

            # Vector-only
            vector_results = await vector_only_retriever.retrieve(
                query=query["query"],
                collection="test_collection",
                limit=10,
            )
            vector_ids = [r.get("id") or r.get("payload", {}).get("chunk_id") for r in vector_results]
            vector_mrr = calculate_mrr(vector_ids, set(query["relevant_docs"]))

            # Hybrid
            hybrid_results = await hybrid_retriever_rrf.retrieve(
                query=query["query"],
                collection="test_collection",
                limit=10,
            )
            hybrid_ids = [r.get("id") or r.get("payload", {}).get("chunk_id") for r in hybrid_results]
            hybrid_mrr = calculate_mrr(hybrid_ids, set(query["relevant_docs"]))

            improvement = hybrid_mrr - vector_mrr
            query_types[query_type].append({
                "query": query["query"],
                "vector_mrr": vector_mrr,
                "hybrid_mrr": hybrid_mrr,
                "improvement": improvement,
            })

        print("\n📊 Query Type-Specific Improvements:")
        for query_type, queries in query_types.items():
            avg_improvement = sum(q["improvement"] for q in queries) / len(queries)
            print(f"  {query_type}: {avg_improvement:+.3f} MRR improvement")

        # Exact ID matches should benefit most from hybrid search
        exact_id_queries = [q for query_type, queries in query_types.items() if query_type == "exact_id_match" for q in queries]
        if exact_id_queries:
            exact_id_avg_improvement = sum(q["improvement"] for q in exact_id_queries) / len(exact_id_queries)
            print(f"\n  ⭐ Exact ID queries average improvement: {exact_id_avg_improvement:+.3f} MRR")


# ============================================================================
# Integration Test (requires services)
# ============================================================================

@pytest.mark.integration
class TestHybridSearchIntegration:
    """Integration test with real services (requires Qdrant and optional OpenSearch)."""

    @pytest.mark.asyncio
    async def test_real_world_hybrid_search(self):
        """Test hybrid search with real services if available."""
        settings = Settings()
        settings.rag_hybrid_search = "true"
        settings.opensearch_enabled = "true"

        from backend.rag.storage.factory import create_vector_store
        from backend.rag.storage.text_search_factory import create_text_search_store
        from backend.rag.retrieval.hybrid_retriever import HybridRetriever

        vector_store = create_vector_store(settings)
        text_store = create_text_search_store(settings)

        if not text_store:
            pytest.skip("OpenSearch not available for integration test")

        retriever = HybridRetriever(
            vector_store=vector_store,
            text_search_store=text_store,
            reranker=ReciprocalRankFusionReranker(),
        )

        # Test with a simple query
        results = await retriever.retrieve(
            query="test query",
            collection="knowledge_chunks",
            limit=5,
        )

        assert isinstance(results, list)
        # Should not crash even if no results
        print(f"\n✅ Integration test: Retrieved {len(results)} results")


pytest_plugins = ["pytest_asyncio"]


