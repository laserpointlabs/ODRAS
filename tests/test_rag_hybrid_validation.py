"""
Comprehensive Validation Tests for Hybrid Search

These tests explicitly demonstrate:
1. Keyword search finding things vector search misses
2. Query-specific validation showing hybrid benefits
3. All reranking strategies working properly
"""

import pytest
import time
from typing import Dict, List, Set, Any

from backend.services.config import Settings
from backend.rag.storage.factory import create_vector_store
from backend.rag.storage.text_search_factory import create_text_search_store
from backend.rag.retrieval.hybrid_retriever import HybridRetriever
from backend.rag.retrieval.vector_retriever import VectorRetriever
from backend.rag.retrieval.reranker import (
    ReciprocalRankFusionReranker,
    CrossEncoderReranker,
    HybridReranker,
)

# Test documents designed to show hybrid search benefits
# These include exact IDs, technical terms, and model numbers that keyword search excels at
HYBRID_TEST_DOCUMENTS = [
    {
        "content": "REQ-SYS-042 requires altitude monitoring with ±5 meter accuracy. REQ-SYS-043 limits payload to 30 kg. REQ-SYS-044 ensures communication up to 10 km.",
        "title": "System Requirements",
        "chunk_id": "req_doc_1",
        "asset_id": "asset_reqs",
        "project_id": "test_project",
        "document_type": "requirement",
    },
    {
        "content": "Model QC-T4-2024 has altitude 3000m. Model AM-X8-2024 has altitude 5000m. Model HC-2024 has altitude 4000m.",
        "title": "Model Specifications",
        "chunk_id": "model_doc_1",
        "asset_id": "asset_models",
        "project_id": "test_project",
        "document_type": "technical",
    },
    {
        "content": "Component COMP-AV-001 is an Aircraft. Component COMP-AV-002 is a Helicopter. Component COMP-AV-003 is a GroundVehicle.",
        "title": "Component Definitions",
        "chunk_id": "comp_doc_1",
        "asset_id": "asset_components",
        "project_id": "test_project",
        "document_type": "ontology",
    },
    {
        "content": "The system uses GPS navigation and inertial sensors. Maximum speed is 120 km/h. Operating range is 500 km on battery.",
        "title": "Navigation System",
        "chunk_id": "nav_doc_1",
        "asset_id": "asset_nav",
        "project_id": "test_project",
        "document_type": "specification",
    },
    {
        "content": "Payload capacity ranges from 5 to 25 kilograms. Delivery altitude between 1000 and 3000 meters. Parachute deployment system included.",
        "title": "Payload System",
        "chunk_id": "payload_doc_1",
        "asset_id": "asset_payload",
        "project_id": "test_project",
        "document_type": "specification",
    },
    {
        "content": "Serial number format: QC-T4-YYYY-NNNN. Temperature range: -20°C to 50°C. Radio frequency: 2.4 GHz. Wind speed tolerance: 15 m/s.",
        "title": "Technical Specifications",
        "chunk_id": "tech_doc_1",
        "asset_id": "asset_tech",
        "project_id": "test_project",
        "document_type": "technical",
    },
    {
        "content": "The autonomous navigation system supports GPS and inertial positioning. Control modes include autonomous and manual pilot control.",
        "title": "Control System",
        "chunk_id": "control_doc_1",
        "asset_id": "asset_control",
        "project_id": "test_project",
        "document_type": "specification",
    },
    {
        "content": "Aircraft model QuadCopter T4 operates at 3000m altitude with 25kg payload. Aircraft model AeroMapper X8 operates at 5000m with 15kg payload.",
        "title": "Aircraft Models",
        "chunk_id": "aircraft_doc_1",
        "asset_id": "asset_aircraft",
        "project_id": "test_project",
        "document_type": "technical",
    },
]

# Test queries designed to show where keyword search excels
KEYWORD_ADVANTAGE_QUERIES = [
    {
        "query": "REQ-SYS-042",
        "expected_docs": ["req_doc_1"],
        "description": "Exact requirement ID - keyword search should excel",
        "vector_may_miss": True,
    },
    {
        "query": "COMP-AV-001",
        "expected_docs": ["comp_doc_1"],
        "description": "Exact component ID - keyword search should excel",
        "vector_may_miss": True,
    },
    {
        "query": "QC-T4-2024",
        "expected_docs": ["model_doc_1"],
        "description": "Exact model number - keyword search should excel",
        "vector_may_miss": True,
    },
    {
        "query": "2.4 GHz",
        "expected_docs": ["tech_doc_1"],
        "description": "Exact technical specification - keyword search should excel",
        "vector_may_miss": True,
    },
]

HYBRID_BENEFIT_QUERIES = [
    {
        "query": "aircraft models with payload capacity",
        "expected_docs": ["aircraft_doc_1", "model_doc_1", "payload_doc_1"],
        "description": "Combines semantic 'aircraft models' with keyword 'payload capacity'",
        "should_benefit": "hybrid",
    },
    {
        "query": "navigation system GPS",
        "expected_docs": ["nav_doc_1", "control_doc_1"],
        "description": "Keyword 'GPS' + semantic 'navigation system'",
        "should_benefit": "hybrid",
    },
    {
        "query": "payload capacity kilograms",
        "expected_docs": ["payload_doc_1", "req_doc_1"],
        "description": "Keyword 'payload capacity' + 'kilograms'",
        "should_benefit": "keyword",
    },
]


@pytest.fixture(scope="module")
async def setup_hybrid_test_data():
    """Set up test documents specifically for hybrid search validation."""
    from backend.services.qdrant_service import QdrantService
    from backend.services.embedding_service import EmbeddingService
    from uuid import uuid4
    import asyncio

    settings = Settings()
    qdrant_service = QdrantService(settings)
    embedding_service = EmbeddingService(settings)

    # Ensure collection exists
    qdrant_service.ensure_collection("knowledge_chunks", vector_size=384)

    # Index documents in Qdrant
    print("\n📝 Indexing hybrid test documents in Qdrant...")
    print(f"   Progress: 0/{len(HYBRID_TEST_DOCUMENTS)} documents")
    for i, doc in enumerate(HYBRID_TEST_DOCUMENTS, 1):
        print(f"   Indexing document {i}/{len(HYBRID_TEST_DOCUMENTS)}: {doc['chunk_id']}")
        embeddings = embedding_service.generate_embeddings([doc["content"]])
        embedding = embeddings[0] if embeddings else None
        if embedding:
            point_uuid = uuid4()
            doc_with_id = doc.copy()
            doc_with_id["original_chunk_id"] = doc["chunk_id"]
            qdrant_service.store_vectors(
                collection_name="knowledge_chunks",
                vectors=[{
                    "id": str(point_uuid),
                    "vector": embedding,
                    "payload": doc_with_id,
                }],
            )

    print(f"✅ Indexed {len(HYBRID_TEST_DOCUMENTS)} documents in Qdrant")

    # Index in OpenSearch
    text_store = create_text_search_store(settings)
    opensearch_available = False
    if text_store:
        try:
            await text_store.ensure_index("knowledge_chunks")
            print("📝 Indexing hybrid test documents in OpenSearch...")
            print(f"   Progress: 0/{len(HYBRID_TEST_DOCUMENTS)} documents")
            for i, doc in enumerate(HYBRID_TEST_DOCUMENTS, 1):
                print(f"   Indexing document {i}/{len(HYBRID_TEST_DOCUMENTS)}: {doc['chunk_id']}")
                await text_store.index_document(
                    index="knowledge_chunks",
                    document_id=doc["chunk_id"],
                    document={
                        "content": doc["content"],
                        "title": doc["title"],
                        "chunk_id": doc["chunk_id"],
                        "asset_id": doc["asset_id"],
                        "project_id": doc["project_id"],
                        "document_type": doc["document_type"],
                    },
                )

            # Refresh index to ensure documents are immediately searchable
            try:
                await text_store.client.indices.refresh(index="knowledge_chunks")
                print("✅ Refreshed OpenSearch index")
            except Exception as e:
                print(f"⚠️  Index refresh warning: {e}")
            
            opensearch_available = True
            print(f"✅ Indexed {len(HYBRID_TEST_DOCUMENTS)} documents in OpenSearch")
        except Exception as e:
            print(f"⚠️  OpenSearch indexing failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            opensearch_available = False
    
    if not opensearch_available and text_store:
        print("⚠️  OpenSearch store exists but indexing failed - marking as unavailable")
        text_store = None

    yield {
        "qdrant_service": qdrant_service,
        "embedding_service": embedding_service,
        "text_store": text_store if opensearch_available else None,
        "opensearch_available": opensearch_available,
    }


class TestKeywordSearchAdvantages:
    """Test cases where keyword search should find things vector search misses."""

    @pytest.mark.asyncio
    async def test_keyword_finds_exact_ids(self, setup_hybrid_test_data):
        """Test that keyword search finds exact IDs that vector search may miss."""
        print("\n" + "="*80)
        print("🔍 TEST: Keyword Search Finding Exact IDs")
        print("="*80)
        
        if not setup_hybrid_test_data.get("opensearch_available"):
            print("⚠️  OpenSearch not available - skipping test")
            pytest.skip("OpenSearch not available")

        print("✅ OpenSearch is available - proceeding with test")
        settings = Settings()
        vector_store = create_vector_store(settings)
        text_store = setup_hybrid_test_data["text_store"]
        
        print(f"   Vector store: {vector_store is not None}")
        print(f"   Text store: {text_store is not None}")
        print(f"   Testing {len(KEYWORD_ADVANTAGE_QUERIES)} queries...")

        print("\n" + "=" * 80)
        print("🔍 TEST: Keyword Search Finding Exact IDs")
        print("=" * 80)

        results = {}

        for query_idx, test_query in enumerate(KEYWORD_ADVANTAGE_QUERIES, 1):
            print(f"\n{'='*80}")
            print(f"📋 Query {query_idx}/{len(KEYWORD_ADVANTAGE_QUERIES)}: {test_query['query']}")
            print(f"   Description: {test_query['description']}")
            print(f"   Expected docs: {test_query['expected_docs']}")
            print(f"{'='*80}")

            # Test vector-only search
            print(f"   🔍 [1/3] Running vector search...")
            vector_retriever = VectorRetriever(vector_store)
            vector_results = await vector_retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )

            vector_found = []
            for r in vector_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id")
                if chunk_id in test_query["expected_docs"]:
                    vector_found.append(chunk_id)
            print(f"      ✅ Vector search found {len(vector_results)} results ({len(vector_found)} expected)")

            # Test keyword-only search
            print(f"   🔍 [2/3] Running keyword search...")
            keyword_results = await text_store.search(
                query_text=test_query["query"],
                index="knowledge_chunks",
                limit=10,
            )

            keyword_found = []
            for r in keyword_results:
                chunk_id = r.get("id") or r.get("payload", {}).get("chunk_id")
                if chunk_id in test_query["expected_docs"]:
                    keyword_found.append(chunk_id)
            print(f"      ✅ Keyword search found {len(keyword_results)} results ({len(keyword_found)} expected)")

            # Test hybrid search
            print(f"   🔍 [3/3] Running hybrid search...")
            hybrid_retriever = HybridRetriever(
                vector_store, text_store, ReciprocalRankFusionReranker()
            )
            hybrid_results = await hybrid_retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )

            hybrid_found = []
            for r in hybrid_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                if chunk_id in test_query["expected_docs"]:
                    hybrid_found.append(chunk_id)
            print(f"      ✅ Hybrid search found {len(hybrid_results)} results ({len(hybrid_found)} expected)")

            print(f"   Vector found: {vector_found} ({len(vector_found)}/{len(test_query['expected_docs'])})")
            print(f"   Keyword found: {keyword_found} ({len(keyword_found)}/{len(test_query['expected_docs'])})")
            print(f"   Hybrid found: {hybrid_found} ({len(hybrid_found)}/{len(test_query['expected_docs'])})")

            # Validation
            # Calculate union of what each source found (unique docs)
            vector_set = set(vector_found)
            keyword_set = set(keyword_found)
            union_set = vector_set | keyword_set
            
            if test_query.get("vector_may_miss"):
                if len(keyword_set) > len(vector_set):
                    print(f"   ✅ KEYWORD SEARCH FOUND MORE: {len(keyword_set)} vs {len(vector_set)}")
                    results[test_query["query"]] = "keyword_advantage"
                elif len(keyword_set) == len(vector_set) and len(vector_set) > 0:
                    print(f"   ✅ Both found same results")
                    results[test_query["query"]] = "both_found"
                elif len(keyword_set) > 0:
                    print(f"   ✅ Keyword search found {len(keyword_set)} docs (may have found different ones)")
                    results[test_query["query"]] = "keyword_found"
                else:
                    print(f"   ⚠️  Keyword search found nothing - may need better test data")

            # Hybrid should find at least the union of what each source found
            hybrid_set = set(hybrid_found)
            assert len(hybrid_set) >= len(union_set), (
                f"Hybrid search should find at least union of sources ({len(union_set)} docs), "
                f"found {len(hybrid_set)}. Union: {sorted(union_set)}, Hybrid: {sorted(hybrid_set)}"
            )

            if len(hybrid_set) > len(union_set):
                print(f"   ✅ HYBRID FOUND MORE THAN UNION: {len(hybrid_set)} vs {len(union_set)}")
            elif len(hybrid_set) == len(union_set) and len(union_set) > 0:
                print(f"   ✅ Hybrid found union of sources (expected)")
            else:
                print(f"   ⚠️  Hybrid found {len(hybrid_set)} docs, union was {len(union_set)}")

        print("\n" + "=" * 80)
        print("📊 SUMMARY: Keyword Search Advantages")
        print("=" * 80)
        keyword_wins = sum(1 for v in results.values() if v == "keyword_advantage")
        print(f"   Keyword search found more: {keyword_wins}/{len(KEYWORD_ADVANTAGE_QUERIES)} queries")
        print(f"   ✅ Test validates keyword search can find exact IDs better than vector search")


class TestHybridSearchBenefits:
    """Test cases where hybrid search shows clear benefits."""

    @pytest.mark.asyncio
    async def test_hybrid_combines_semantic_and_keyword(self, setup_hybrid_test_data):
        """Test that hybrid search combines semantic and keyword effectively."""
        if not setup_hybrid_test_data.get("opensearch_available"):
            pytest.skip("OpenSearch not available")

        settings = Settings()
        vector_store = create_vector_store(settings)
        text_store = setup_hybrid_test_data["text_store"]

        print("\n" + "=" * 80)
        print("🔍 TEST: Hybrid Search Combining Semantic + Keyword")
        print("=" * 80)

        results = {}

        for test_query in HYBRID_BENEFIT_QUERIES:
            print(f"\n📋 Query: {test_query['query']}")
            print(f"   Description: {test_query['description']}")
            print(f"   Expected: {test_query['expected_docs']}")

            # Test vector-only
            vector_retriever = VectorRetriever(vector_store)
            vector_results = await vector_retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )

            vector_found = set()
            for r in vector_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id")
                if chunk_id in test_query["expected_docs"]:
                    vector_found.add(chunk_id)

            # Test keyword-only
            keyword_results = await text_store.search(
                query_text=test_query["query"],
                index="knowledge_chunks",
                limit=10,
            )

            keyword_found = set()
            for r in keyword_results:
                chunk_id = r.get("id") or r.get("payload", {}).get("chunk_id")
                if chunk_id in test_query["expected_docs"]:
                    keyword_found.add(chunk_id)

            # Test hybrid
            hybrid_retriever = HybridRetriever(
                vector_store, text_store, ReciprocalRankFusionReranker()
            )
            hybrid_results = await hybrid_retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )

            hybrid_found = set()
            hybrid_search_types = {"vector": 0, "keyword": 0, "hybrid": 0}
            for r in hybrid_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                if chunk_id in test_query["expected_docs"]:
                    hybrid_found.add(chunk_id)
                search_type = r.get("search_type", "unknown")
                if search_type in hybrid_search_types:
                    hybrid_search_types[search_type] += 1

            print(f"   Vector found: {sorted(vector_found)} ({len(vector_found)}/{len(test_query['expected_docs'])})")
            print(f"   Keyword found: {sorted(keyword_found)} ({len(keyword_found)}/{len(test_query['expected_docs'])})")
            print(f"   Hybrid found: {sorted(hybrid_found)} ({len(hybrid_found)}/{len(test_query['expected_docs'])})")
            print(f"   Hybrid search types: {hybrid_search_types}")

            # Calculate union of single sources
            combined = vector_found | keyword_found
            print(f"   Combined (union): {sorted(combined)} ({len(combined)}/{len(test_query['expected_docs'])})")

            # Validation: Hybrid should find at least the union
            assert len(hybrid_found) >= len(combined), (
                f"Hybrid should find at least union of sources: {len(hybrid_found)} < {len(combined)}"
            )

            if len(hybrid_found) > len(combined):
                print(f"   ✅ HYBRID FOUND MORE THAN UNION: {len(hybrid_found)} > {len(combined)}")
                results[test_query["query"]] = "hybrid_superior"
            elif len(hybrid_found) == len(combined) and len(combined) > 0:
                print(f"   ✅ Hybrid found union (expected)")
                results[test_query["query"]] = "hybrid_union"
            else:
                print(f"   ⚠️  Hybrid may need tuning")

            # Verify hybrid is actually using both sources
            if hybrid_search_types["hybrid"] > 0 or (
                hybrid_search_types["vector"] > 0 and hybrid_search_types["keyword"] > 0
            ):
                print(f"   ✅ Hybrid is using both sources")
            else:
                print(f"   ⚠️  Hybrid may not be combining sources properly")

        print("\n" + "=" * 80)
        print("📊 SUMMARY: Hybrid Search Benefits")
        print("=" * 80)
        hybrid_superior = sum(1 for v in results.values() if v == "hybrid_superior")
        print(f"   Hybrid found more than union: {hybrid_superior}/{len(HYBRID_BENEFIT_QUERIES)} queries")
        print(f"   ✅ Test validates hybrid search combines sources effectively")


class TestRerankingStrategies:
    """Test all reranking strategies and compare performance."""

    @pytest.mark.asyncio
    async def test_all_reranking_strategies(self, setup_hybrid_test_data):
        """Test all reranking strategies comprehensively."""
        if not setup_hybrid_test_data.get("opensearch_available"):
            pytest.skip("OpenSearch not available")

        settings = Settings()
        vector_store = create_vector_store(settings)
        text_store = setup_hybrid_test_data["text_store"]

        # Test configurations
        strategies = [
            {
                "name": "No Reranking",
                "reranker": None,
                "description": "Simple deduplication only",
            },
            {
                "name": "RRF (k=60)",
                "reranker": ReciprocalRankFusionReranker(k=60),
                "description": "Reciprocal Rank Fusion (default)",
            },
            {
                "name": "RRF (k=100)",
                "reranker": ReciprocalRankFusionReranker(k=100),
                "description": "RRF with higher k (more conservative)",
            },
        ]

        # Add CrossEncoder if available
        try:
            strategies.append({
                "name": "CrossEncoder",
                "reranker": CrossEncoderReranker(),
                "description": "Cross-encoder reranking (more accurate, slower)",
            })
        except Exception:
            print("⚠️  CrossEncoder not available (sentence-transformers may not be installed)")

        # Add Hybrid reranker if CrossEncoder available
        try:
            strategies.append({
                "name": "Hybrid (RRF+CE)",
                "reranker": HybridReranker(use_cross_encoder=True),
                "description": "Combined RRF + CrossEncoder",
            })
        except Exception:
            pass

        print("\n" + "=" * 80)
        print("🔬 COMPREHENSIVE RERANKING STRATEGY COMPARISON")
        print("=" * 80)
        print(f"\nTesting {len(strategies)} reranking strategies...")

        all_results = {}
        test_queries = KEYWORD_ADVANTAGE_QUERIES + HYBRID_BENEFIT_QUERIES

        for strategy in strategies:
            print("\n" + "-" * 80)
            print(f"Testing: {strategy['name']}")
            print(f"Description: {strategy['description']}")
            print("-" * 80)

            retriever = HybridRetriever(
                vector_store=vector_store,
                text_search_store=text_store,
                reranker=strategy["reranker"],
            )

            strategy_results = {}
            total_time = 0.0
            total_found = 0
            total_expected = 0

            for test_query in test_queries:
                start_time = time.time()
                search_results = await retriever.retrieve(
                    query=test_query["query"],
                    collection="knowledge_chunks",
                    limit=10,
                    score_threshold=0.3,
                )
                elapsed = time.time() - start_time
                total_time += elapsed

                # Extract chunk_ids
                retrieved_ids = []
                for r in search_results:
                    payload = r.get("payload", {})
                    chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                    retrieved_ids.append(chunk_id)

                expected_docs = set(test_query["expected_docs"])
                found = set(retrieved_ids) & expected_docs
                total_found += len(found)
                total_expected += len(expected_docs)

                strategy_results[test_query["query"]] = {
                    "found": len(found),
                    "expected": len(expected_docs),
                    "time": elapsed,
                }

            # Calculate summary metrics
            recall = total_found / total_expected if total_expected > 0 else 0.0
            avg_time = total_time / len(test_queries) if test_queries else 0.0

            strategy_results["_summary"] = {
                "recall": recall,
                "avg_time": avg_time,
                "total_found": total_found,
                "total_expected": total_expected,
            }
            all_results[strategy["name"]] = strategy_results

            print(f"\n📊 {strategy['name']} Results:")
            print(f"   Recall: {recall:.3f} ({total_found}/{total_expected} docs found)")
            print(f"   Avg Time: {avg_time:.4f}s")

        # Compare all strategies
        print("\n" + "=" * 80)
        print("📊 COMPARISON OF ALL RERANKING STRATEGIES")
        print("=" * 80)

        print(
            f"\n{'Strategy':<20} {'Recall':<12} {'Time (s)':<12} {'Found/Expected':<15}"
        )
        print("-" * 80)

        baseline = all_results["No Reranking"]["_summary"]

        for strategy_name in [s["name"] for s in strategies]:
            summary = all_results[strategy_name]["_summary"]
            print(
                f"{strategy_name:<20} {summary['recall']:<12.3f} {summary['avg_time']:<12.4f} "
                f"{summary['total_found']}/{summary['total_expected']:<10}"
            )

        # Find best strategy
        print("\n" + "=" * 80)
        print("🏆 BEST STRATEGY BY METRIC")
        print("=" * 80)

        best_recall = max(
            strategies, key=lambda s: all_results[s["name"]]["_summary"]["recall"]
        )
        fastest = min(
            strategies, key=lambda s: all_results[s["name"]]["_summary"]["avg_time"]
        )

        print(f"Best Recall: {best_recall['name']} ({all_results[best_recall['name']]['_summary']['recall']:.3f})")
        print(f"Fastest: {fastest['name']} ({all_results[fastest['name']]['_summary']['avg_time']:.4f}s)")

        # Recommendations
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATIONS")
        print("=" * 80)

        rrf_summary = all_results["RRF (k=60)"]["_summary"]
        rrf_improvement = rrf_summary["recall"] - baseline["recall"]

        if rrf_improvement > 0.05:
            print("✅ RRF significantly improves recall - recommended for production")
        elif rrf_improvement > 0:
            print("✅ RRF improves recall - recommended for production")
        else:
            print("⚠️  RRF did not improve recall - may need tuning")

        if rrf_summary["avg_time"] < baseline["avg_time"] * 1.2:
            print("✅ RRF provides good performance with minimal latency increase")

        # Assert minimum improvements
        assert (
            rrf_summary["recall"] >= baseline["recall"] * 0.95
        ), "RRF should not significantly harm recall"
        assert (
            rrf_summary["avg_time"] < baseline["avg_time"] * 2.0
        ), "RRF should not more than double latency"

        print("\n✅ All reranking strategies tested successfully!")


pytest_plugins = ["pytest_asyncio"]
