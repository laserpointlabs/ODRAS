"""
Real-World RAG Performance Evaluation

This test suite evaluates actual performance improvements using real services:
- Base RAG (vector-only with Qdrant)
- Hybrid Search (vector + keyword)
- Hybrid Search with Rerankers

Tests use real Qdrant and OpenSearch services to measure actual improvements
in retrieval quality for technical queries.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from uuid import uuid4, UUID

from backend.services.config import Settings
from backend.services.qdrant_service import QdrantService
from backend.services.embedding_service import EmbeddingService
from backend.rag.storage.vector_store import VectorStore
from backend.rag.storage.qdrant_store import QdrantVectorStore
from backend.rag.storage.text_search_store import TextSearchStore
from backend.rag.storage.opensearch_store import OpenSearchTextStore
from backend.rag.storage.factory import create_vector_store
from backend.rag.storage.text_search_factory import create_text_search_store
from backend.rag.retrieval.vector_retriever import VectorRetriever
from backend.rag.retrieval.hybrid_retriever import HybridRetriever
from backend.rag.retrieval.reranker import (
    ReciprocalRankFusionReranker,
    CrossEncoderReranker,
    HybridReranker,
)
from backend.rag.core.modular_rag_service import ModularRAGService


# ============================================================================
# Real Test Documents (Technical Content)
# ============================================================================

REAL_TEST_DOCUMENTS = [
    {
        "content": "The QuadCopter T4 unmanned aerial vehicle has a maximum operational altitude of 3000 meters above sea level. The system payload capacity is 25 kilograms. The model number is QC-T4-2024 and the serial number format is QC-T4-YYYY-NNNN.",
        "title": "QuadCopter T4 Specifications",
        "document_type": "specification",
        "chunk_id": "real_doc_1",
        "asset_id": "asset_quadcopter_t4",
        "project_id": "test_project",
        "metadata": {
            "model": "QuadCopter T4",
            "model_number": "QC-T4-2024",
            "altitude": "3000 meters",
            "payload": "25 kg",
        },
    },
    {
        "content": "The AeroMapper X8 is a fixed-wing unmanned aerial vehicle (UAV) with a wingspan of 4.2 meters. Maximum altitude capability is 5000 meters. The aircraft can carry a payload of 15 kilograms. Serial number: AM-X8-2024.",
        "title": "AeroMapper X8 Technical Data Sheet",
        "document_type": "technical",
        "chunk_id": "real_doc_2",
        "asset_id": "asset_aeromapper_x8",
        "project_id": "test_project",
        "metadata": {
            "model": "AeroMapper X8",
            "model_number": "AM-X8-2024",
            "wingspan": "4.2 meters",
            "altitude": "5000 meters",
            "payload": "15 kg",
        },
    },
    {
        "content": "REQ-SYS-042: The system shall support real-time altitude monitoring with accuracy of ±5 meters. REQ-SYS-043: The maximum payload capacity shall not exceed 30 kilograms. REQ-SYS-044: The system shall maintain communication link at distances up to 10 kilometers.",
        "title": "System Requirements Document",
        "document_type": "requirement",
        "chunk_id": "real_doc_3",
        "asset_id": "asset_requirements",
        "project_id": "test_project",
        "metadata": {
            "req_ids": ["REQ-SYS-042", "REQ-SYS-043", "REQ-SYS-044"],
            "altitude": "monitoring",
            "payload": "30 kg",
            "communication": "10 km",
        },
    },
    {
        "content": "Component ID COMP-AV-001 is classified as Aircraft type with property hasWingspan. Component ID COMP-AV-002 is classified as Helicopter type. Component ID COMP-AV-003 is classified as GroundVehicle type.",
        "title": "Component Ontology Definitions",
        "document_type": "ontology",
        "chunk_id": "real_doc_4",
        "asset_id": "asset_components",
        "project_id": "test_project",
        "metadata": {
            "components": ["COMP-AV-001", "COMP-AV-002", "COMP-AV-003"],
            "types": ["Aircraft", "Helicopter", "GroundVehicle"],
        },
    },
    {
        "content": "The vehicle control system supports both autonomous navigation and manual pilot control modes. Maximum speed is 120 kilometers per hour. Operating range is 500 kilometers on a single battery charge. The system uses GPS and inertial navigation for positioning.",
        "title": "Vehicle Control System Specifications",
        "document_type": "specification",
        "chunk_id": "real_doc_5",
        "asset_id": "asset_vehicle_control",
        "project_id": "test_project",
        "metadata": {
            "control_modes": ["autonomous", "manual"],
            "speed": "120 km/h",
            "range": "500 km",
            "navigation": ["GPS", "inertial"],
        },
    },
    {
        "content": "The payload delivery mechanism can release packages at altitudes between 1000 and 3000 meters. Package weight capacity ranges from 5 to 25 kilograms. The mechanism includes a parachute deployment system for safe landing.",
        "title": "Payload Delivery System",
        "document_type": "specification",
        "chunk_id": "real_doc_6",
        "asset_id": "asset_payload",
        "project_id": "test_project",
        "metadata": {
            "altitude_range": "1000-3000 meters",
            "weight_capacity": "5-25 kg",
            "parachute": "deployment system",
        },
    },
]

# Test queries with expected relevant documents
TEST_QUERIES = [
    {
        "query": "What is the maximum altitude of QuadCopter T4?",
        "expected_docs": ["real_doc_1"],
        "query_type": "specific_model",
        "should_benefit_from": "keyword",  # Exact model number match
    },
    {
        "query": "Which aircraft models do we have?",
        "expected_docs": ["real_doc_1", "real_doc_2", "real_doc_4"],
        "query_type": "general_concept",
        "should_benefit_from": "hybrid",  # Both semantic and keyword
        "keywords": ["aircraft", "models", "QuadCopter", "AeroMapper"],  # Keywords that should match
        "note": "Hybrid should find all 3: keyword search for 'aircraft' + vector for 'models'",
    },
    {
        "query": "REQ-SYS-042",
        "expected_docs": ["real_doc_3"],
        "query_type": "exact_id",
        "should_benefit_from": "keyword",  # Exact ID match - keyword search should excel
        "keywords": ["REQ-SYS-042"],  # Exact keyword match
    },
    {
        "query": "What is the payload capacity?",
        "expected_docs": ["real_doc_1", "real_doc_3", "real_doc_6"],
        "query_type": "technical_spec",
        "should_benefit_from": "hybrid",
        "keywords": ["payload", "capacity", "kilograms", "kg"],  # Keyword search should match
        "note": "Keyword search for 'payload capacity' should find all 3 docs",
    },
    {
        "query": "COMP-AV-001 component",
        "expected_docs": ["real_doc_4"],
        "query_type": "component_id",
        "should_benefit_from": "keyword",  # Exact component ID
    },
    {
        "query": "autonomous navigation control system",
        "expected_docs": ["real_doc_5"],
        "query_type": "semantic_concept",
        "should_benefit_from": "vector",  # Semantic similarity
    },
]


# ============================================================================
# Evaluation Metrics
# ============================================================================

def calculate_metrics(retrieved_ids: List[str], expected_docs: Set[str], top_k: int = 10) -> Dict[str, float]:
    """Calculate precision, recall, MRR, and NDCG."""
    # Deduplicate retrieved IDs (keep first occurrence)
    seen = set()
    deduplicated_retrieved = []
    for doc_id in retrieved_ids:
        if doc_id not in seen:
            seen.add(doc_id)
            deduplicated_retrieved.append(doc_id)
    
    retrieved_top_k = deduplicated_retrieved[:top_k]
    
    # Precision@K: Percentage of retrieved results that are relevant
    relevant_retrieved = sum(1 for doc_id in retrieved_top_k if doc_id in expected_docs)
    precision = relevant_retrieved / len(retrieved_top_k) if retrieved_top_k else 0.0
    
    # Recall@K: Percentage of relevant documents that were retrieved (should be <= 1.0)
    recall = relevant_retrieved / len(expected_docs) if expected_docs else 1.0
    # Cap recall at 1.0 (can't recall more than 100% of relevant docs)
    recall = min(recall, 1.0)
    
    # MRR (Mean Reciprocal Rank): 1/rank of first relevant result
    mrr = 0.0
    for rank, doc_id in enumerate(deduplicated_retrieved, start=1):
        if doc_id in expected_docs:
            mrr = 1.0 / rank
            break
    
    # NDCG@K (simplified)
    dcg = sum(1.0 / (rank + 1) for rank, doc_id in enumerate(retrieved_top_k, start=1) if doc_id in expected_docs)
    ideal_dcg = sum(1.0 / (i + 1) for i in range(min(len(expected_docs), len(retrieved_top_k))))
    ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "mrr": mrr,
        "ndcg": ndcg,
        "relevant_found": relevant_retrieved,
        "total_expected": len(expected_docs),
        "total_retrieved": len(retrieved_top_k),
        "unique_retrieved": len(deduplicated_retrieved),
    }


# ============================================================================
# Test Setup and Teardown
# ============================================================================

@pytest.fixture(scope="module")
async def setup_test_data():
    """Set up test documents in Qdrant and OpenSearch."""
    settings = Settings()
    
    # Initialize services
    qdrant_service = QdrantService(settings)
    embedding_service = EmbeddingService(settings)
    
    # Ensure collection exists
    qdrant_service.ensure_collection("knowledge_chunks", vector_size=384)
    
    # Index documents in Qdrant
    print("\n📝 Indexing test documents in Qdrant...")
    chunk_id_to_uuid = {}  # Map chunk_id to UUID for retrieval
    for doc in REAL_TEST_DOCUMENTS:
        embeddings = embedding_service.generate_embeddings([doc["content"]])
        embedding = embeddings[0] if embeddings else None
        if embedding:
            # Generate UUID for Qdrant (requires UUID or integer)
            point_uuid = uuid4()
            chunk_id_to_uuid[doc["chunk_id"]] = str(point_uuid)
            
            # Store chunk_id in payload for retrieval
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
    
    print(f"✅ Indexed {len(REAL_TEST_DOCUMENTS)} documents in Qdrant")
    
    # Try to index in OpenSearch if available
    text_store = create_text_search_store(settings)
    opensearch_available = False
    if text_store:
        try:
            await text_store.ensure_index("knowledge_chunks")
            print("📝 Indexing test documents in OpenSearch...")
            
            for doc in REAL_TEST_DOCUMENTS:
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
            
            opensearch_available = True
            print(f"✅ Indexed {len(REAL_TEST_DOCUMENTS)} documents in OpenSearch")
        except Exception as e:
            print(f"⚠️  OpenSearch not available: {e}")
    
    yield {
        "qdrant_service": qdrant_service,
        "embedding_service": embedding_service,
        "text_store": text_store,
        "opensearch_available": opensearch_available,
        "chunk_id_to_uuid": chunk_id_to_uuid,
    }
    
    # Cleanup (optional - can leave test data for debugging)
    # print("\n🧹 Cleaning up test data...")
    # for doc in REAL_TEST_DOCUMENTS:
    #     qdrant_service.delete_vectors("knowledge_chunks", [doc["chunk_id"]])
    #     if text_store and opensearch_available:
    #         await text_store.delete_document("knowledge_chunks", doc["chunk_id"])


# ============================================================================
# Real-World Performance Evaluation
# ============================================================================

class TestRealWorldRAGEvaluation:
    """Evaluate real-world RAG performance with actual services."""

    @pytest.mark.asyncio
    async def test_base_rag_vector_only(self, setup_test_data):
        """Test base RAG with vector-only search (Qdrant)."""
        settings = Settings()
        vector_store = create_vector_store(settings)
        retriever = VectorRetriever(vector_store)
        
        results_by_query = {}
        total_time = 0.0
        
        print("\n" + "="*80)
        print("🔍 BASE RAG (Vector-Only) Evaluation")
        print("="*80)
        
        for test_query in TEST_QUERIES:
            start_time = time.time()
            search_results = await retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Extract chunk_id from results (may be in payload)
            retrieved_ids = []
            for r in search_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                retrieved_ids.append(chunk_id)
            
            expected_docs = set(test_query["expected_docs"])
            
            metrics = calculate_metrics(retrieved_ids, expected_docs)
            metrics["time"] = elapsed
            
            results_by_query[test_query["query"]] = metrics
            
            # Count search sources if available (after reranking, results may be "hybrid")
            vector_count = len([r for r in search_results if r.get("search_type") == "vector"])
            keyword_count = len([r for r in search_results if r.get("search_type") == "keyword"])
            hybrid_count = len([r for r in search_results if r.get("search_type") == "hybrid"])
            
            print(f"\n📋 Query: {test_query['query']}")
            print(f"   Type: {test_query['query_type']}")
            unique_retrieved = len(set(retrieved_ids))
            print(f"   Retrieved: {len(retrieved_ids)} docs (unique: {unique_retrieved})")
            print(f"   Expected: {expected_docs} ({len(expected_docs)} docs)")
            found_docs = [d for d in retrieved_ids if d in expected_docs]
            unique_found = list(set(found_docs))
            print(f"   Found: {unique_found} ({len(unique_found)}/{len(expected_docs)} relevant docs)")
            print(f"   Precision: {metrics['precision']:.3f} ({metrics['relevant_found']}/{metrics['total_retrieved']} relevant)")
            print(f"   Recall: {metrics['recall']:.3f} ({metrics['relevant_found']}/{metrics['total_expected']} relevant docs found)")
            print(f"   MRR: {metrics['mrr']:.3f}")
            print(f"   Time: {elapsed:.4f}s")
            if vector_count > 0 or keyword_count > 0 or hybrid_count > 0:
                if hybrid_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword + {hybrid_count} hybrid (combined)")
                    print(f"   ✅ Hybrid search active (both sources contributing)")
                elif vector_count > 0 and keyword_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword results")
                    print(f"   ✅ Both sources active")
                elif vector_count == 0 and keyword_count > 0:
                    print(f"   Search sources: {keyword_count} keyword results")
                    print(f"   ⚠️  Only keyword results (vector search may have failed)")
                elif keyword_count == 0 and vector_count > 0:
                    print(f"   Search sources: {vector_count} vector results")
                    print(f"   ⚠️  Only vector results (keyword search may have failed)")
                    
            # Show missing expected docs
            missing = expected_docs - set(retrieved_ids)
            if missing:
                print(f"   ❌ Missing expected docs: {missing}")
        
        # Calculate averages
        avg_metrics = {
            "precision": sum(r["precision"] for r in results_by_query.values()) / len(results_by_query),
            "recall": sum(r["recall"] for r in results_by_query.values()) / len(results_by_query),
            "mrr": sum(r["mrr"] for r in results_by_query.values()) / len(results_by_query),
            "ndcg": sum(r["ndcg"] for r in results_by_query.values()) / len(results_by_query),
            "time": total_time / len(results_by_query),
        }
        
        print(f"\n📊 BASE RAG AVERAGE METRICS:")
        print(f"   Precision: {avg_metrics['precision']:.3f}")
        print(f"   Recall: {avg_metrics['recall']:.3f}")
        print(f"   MRR: {avg_metrics['mrr']:.3f}")
        print(f"   NDCG: {avg_metrics['ndcg']:.3f}")
        print(f"   Avg Time: {avg_metrics['time']:.4f}s")
        
        results_by_query["_summary"] = avg_metrics
        return results_by_query

    @pytest.mark.asyncio
    async def test_hybrid_search_no_rerank(self, setup_test_data):
        """Test hybrid search without reranking."""
        if not setup_test_data["opensearch_available"]:
            pytest.skip("OpenSearch not available for hybrid search test")
        
        settings = Settings()
        settings.rag_hybrid_search = "true"
        settings.opensearch_enabled = "true"
        
        vector_store = create_vector_store(settings)
        text_store = setup_test_data["text_store"]
        
        retriever = HybridRetriever(
            vector_store=vector_store,
            text_search_store=text_store,
            reranker=None,  # No reranking
        )
        
        results_by_query = {}
        total_time = 0.0
        
        print("\n" + "="*80)
        print("🔍 HYBRID SEARCH (No Reranking) Evaluation")
        print("="*80)
        
        for test_query in TEST_QUERIES:
            start_time = time.time()
            search_results = await retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Extract chunk_id from results (may be in payload)
            retrieved_ids = []
            for r in search_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                retrieved_ids.append(chunk_id)
            
            expected_docs = set(test_query["expected_docs"])
            
            metrics = calculate_metrics(retrieved_ids, expected_docs)
            metrics["time"] = elapsed
            
            results_by_query[test_query["query"]] = metrics
            
            # Count search sources if available (after reranking, results may be "hybrid")
            vector_count = len([r for r in search_results if r.get("search_type") == "vector"])
            keyword_count = len([r for r in search_results if r.get("search_type") == "keyword"])
            hybrid_count = len([r for r in search_results if r.get("search_type") == "hybrid"])
            
            print(f"\n📋 Query: {test_query['query']}")
            print(f"   Type: {test_query['query_type']}")
            unique_retrieved = len(set(retrieved_ids))
            print(f"   Retrieved: {len(retrieved_ids)} docs (unique: {unique_retrieved})")
            print(f"   Expected: {expected_docs} ({len(expected_docs)} docs)")
            found_docs = [d for d in retrieved_ids if d in expected_docs]
            unique_found = list(set(found_docs))
            print(f"   Found: {unique_found} ({len(unique_found)}/{len(expected_docs)} relevant docs)")
            print(f"   Precision: {metrics['precision']:.3f} ({metrics['relevant_found']}/{metrics['total_retrieved']} relevant)")
            print(f"   Recall: {metrics['recall']:.3f} ({metrics['relevant_found']}/{metrics['total_expected']} relevant docs found)")
            print(f"   MRR: {metrics['mrr']:.3f}")
            print(f"   Time: {elapsed:.4f}s")
            if vector_count > 0 or keyword_count > 0 or hybrid_count > 0:
                if hybrid_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword + {hybrid_count} hybrid (combined)")
                    print(f"   ✅ Hybrid search active (both sources contributing)")
                elif vector_count > 0 and keyword_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword results")
                    print(f"   ✅ Both sources active")
                elif vector_count == 0 and keyword_count > 0:
                    print(f"   Search sources: {keyword_count} keyword results")
                    print(f"   ⚠️  Only keyword results (vector search may have failed)")
                elif keyword_count == 0 and vector_count > 0:
                    print(f"   Search sources: {vector_count} vector results")
                    print(f"   ⚠️  Only vector results (keyword search may have failed)")
                    
            # Show missing expected docs
            missing = expected_docs - set(retrieved_ids)
            if missing:
                print(f"   ❌ Missing expected docs: {missing}")
        
        # Calculate averages
        avg_metrics = {
            "precision": sum(r["precision"] for r in results_by_query.values()) / len(results_by_query),
            "recall": sum(r["recall"] for r in results_by_query.values()) / len(results_by_query),
            "mrr": sum(r["mrr"] for r in results_by_query.values()) / len(results_by_query),
            "ndcg": sum(r["ndcg"] for r in results_by_query.values()) / len(results_by_query),
            "time": total_time / len(results_by_query),
        }
        
        print(f"\n📊 HYBRID SEARCH (No Rerank) AVERAGE METRICS:")
        print(f"   Precision: {avg_metrics['precision']:.3f}")
        print(f"   Recall: {avg_metrics['recall']:.3f}")
        print(f"   MRR: {avg_metrics['mrr']:.3f}")
        print(f"   NDCG: {avg_metrics['ndcg']:.3f}")
        print(f"   Avg Time: {avg_metrics['time']:.4f}s")
        
        results_by_query["_summary"] = avg_metrics
        return results_by_query

    @pytest.mark.asyncio
    async def test_hybrid_search_with_reranker(self, setup_test_data):
        """Test hybrid search with RRF reranking."""
        if not setup_test_data["opensearch_available"]:
            pytest.skip("OpenSearch not available for hybrid search test")
        
        settings = Settings()
        settings.rag_hybrid_search = "true"
        settings.opensearch_enabled = "true"
        
        vector_store = create_vector_store(settings)
        text_store = setup_test_data["text_store"]
        
        retriever = HybridRetriever(
            vector_store=vector_store,
            text_search_store=text_store,
            reranker=ReciprocalRankFusionReranker(k=60),
        )
        
        results_by_query = {}
        total_time = 0.0
        
        print("\n" + "="*80)
        print("🔍 HYBRID SEARCH (with RRF Reranker) Evaluation")
        print("="*80)
        
        for test_query in TEST_QUERIES:
            start_time = time.time()
            search_results = await retriever.retrieve(
                query=test_query["query"],
                collection="knowledge_chunks",
                limit=10,
                score_threshold=0.3,
            )
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Extract chunk_id from results (may be in payload)
            retrieved_ids = []
            for r in search_results:
                payload = r.get("payload", {})
                chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or r.get("id")
                retrieved_ids.append(chunk_id)
            
            expected_docs = set(test_query["expected_docs"])
            
            metrics = calculate_metrics(retrieved_ids, expected_docs)
            metrics["time"] = elapsed
            
            results_by_query[test_query["query"]] = metrics
            
            # Count search sources if available (after reranking, results may be "hybrid")
            vector_count = len([r for r in search_results if r.get("search_type") == "vector"])
            keyword_count = len([r for r in search_results if r.get("search_type") == "keyword"])
            hybrid_count = len([r for r in search_results if r.get("search_type") == "hybrid"])
            
            print(f"\n📋 Query: {test_query['query']}")
            print(f"   Type: {test_query['query_type']}")
            unique_retrieved = len(set(retrieved_ids))
            print(f"   Retrieved: {len(retrieved_ids)} docs (unique: {unique_retrieved})")
            print(f"   Expected: {expected_docs} ({len(expected_docs)} docs)")
            found_docs = [d for d in retrieved_ids if d in expected_docs]
            unique_found = list(set(found_docs))
            print(f"   Found: {unique_found} ({len(unique_found)}/{len(expected_docs)} relevant docs)")
            print(f"   Precision: {metrics['precision']:.3f} ({metrics['relevant_found']}/{metrics['total_retrieved']} relevant)")
            print(f"   Recall: {metrics['recall']:.3f} ({metrics['relevant_found']}/{metrics['total_expected']} relevant docs found)")
            print(f"   MRR: {metrics['mrr']:.3f}")
            print(f"   Time: {elapsed:.4f}s")
            if vector_count > 0 or keyword_count > 0 or hybrid_count > 0:
                if hybrid_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword + {hybrid_count} hybrid (combined)")
                    print(f"   ✅ Hybrid search active (both sources contributing)")
                elif vector_count > 0 and keyword_count > 0:
                    print(f"   Search sources: {vector_count} vector + {keyword_count} keyword results")
                    print(f"   ✅ Both sources active")
                elif vector_count == 0 and keyword_count > 0:
                    print(f"   Search sources: {keyword_count} keyword results")
                    print(f"   ⚠️  Only keyword results (vector search may have failed)")
                elif keyword_count == 0 and vector_count > 0:
                    print(f"   Search sources: {vector_count} vector results")
                    print(f"   ⚠️  Only vector results (keyword search may have failed)")
                    
            # Show missing expected docs
            missing = expected_docs - set(retrieved_ids)
            if missing:
                print(f"   ❌ Missing expected docs: {missing}")
        
        # Calculate averages
        avg_metrics = {
            "precision": sum(r["precision"] for r in results_by_query.values()) / len(results_by_query),
            "recall": sum(r["recall"] for r in results_by_query.values()) / len(results_by_query),
            "mrr": sum(r["mrr"] for r in results_by_query.values()) / len(results_by_query),
            "ndcg": sum(r["ndcg"] for r in results_by_query.values()) / len(results_by_query),
            "time": total_time / len(results_by_query),
        }
        
        print(f"\n📊 HYBRID SEARCH (RRF) AVERAGE METRICS:")
        print(f"   Precision: {avg_metrics['precision']:.3f}")
        print(f"   Recall: {avg_metrics['recall']:.3f}")
        print(f"   MRR: {avg_metrics['mrr']:.3f}")
        print(f"   NDCG: {avg_metrics['ndcg']:.3f}")
        print(f"   Avg Time: {avg_metrics['time']:.4f}s")
        
        results_by_query["_summary"] = avg_metrics
        return results_by_query

    @pytest.mark.asyncio
    async def test_comprehensive_comparison(self, setup_test_data):
        """Run Base RAG and Hybrid Search with Reranking, then compare results."""
        print("\n" + "="*80)
        print("🚀 COMPREHENSIVE RAG PERFORMANCE COMPARISON")
        print("="*80)
        print("\nThis test will:")
        print("  1. Run Base RAG (vector-only with Qdrant)")
        print("  2. Run Hybrid Search with RRF Reranking (Qdrant + OpenSearch)")
        print("  3. Compare results and show improvements\n")
        
        # Step 1: Run Base RAG
        print("\n" + "="*80)
        print("STEP 1: Running Base RAG (Vector-Only)")
        print("="*80)
        base_results = await self.test_base_rag_vector_only(setup_test_data)
        base_summary = base_results["_summary"]
        
        # Step 2: Run Hybrid Search with Reranking
        print("\n" + "="*80)
        print("STEP 2: Running Hybrid Search with RRF Reranking")
        print("="*80)
        
        if not setup_test_data["opensearch_available"]:
            print("\n⚠️  OpenSearch not available - cannot run hybrid search test")
            print("\nTo enable hybrid search:")
            print("  1. Start OpenSearch: docker-compose up -d opensearch")
            print("  2. Set environment: export OPENSEARCH_ENABLED=true")
            print("  3. Set environment: export RAG_HYBRID_SEARCH=true")
            print("  4. Re-run this test")
            
            print("\n" + "="*80)
            print("📊 BASE RAG RESULTS (Hybrid Search Unavailable)")
            print("="*80)
            print(f"   Precision: {base_summary['precision']:.3f}")
            print(f"   Recall: {base_summary['recall']:.3f}")
            print(f"   MRR: {base_summary['mrr']:.3f}")
            print(f"   NDCG: {base_summary['ndcg']:.3f}")
            print(f"   Avg Time: {base_summary['time']:.4f}s")
            print("\n" + "="*80)
            return
        
        try:
            hybrid_rerank_results = await self.test_hybrid_search_with_reranker(setup_test_data)
            hybrid_summary = hybrid_rerank_results["_summary"]
        except Exception as e:
            print(f"\n❌ Hybrid search test failed: {e}")
            print(f"   Error details: {type(e).__name__}: {str(e)}")
            print("\n" + "="*80)
            print("📊 BASE RAG RESULTS (Hybrid Search Failed)")
            print("="*80)
            print(f"   Precision: {base_summary['precision']:.3f}")
            print(f"   Recall: {base_summary['recall']:.3f}")
            print(f"   MRR: {base_summary['mrr']:.3f}")
            print(f"   NDCG: {base_summary['ndcg']:.3f}")
            print(f"   Avg Time: {base_summary['time']:.4f}s")
            print("\n" + "="*80)
            return
        
        # Step 3: Compare Results
        print("\n" + "="*80)
        print("STEP 3: COMPARING RESULTS")
        print("="*80)
        
        # Detailed comparison table
        print(f"\n{'Metric':<25} {'Base RAG':<20} {'Hybrid (RRF)':<20} {'Improvement':<20} {'% Change':<15}")
        print("-" * 100)
        
        # Precision
        precision_diff = hybrid_summary['precision'] - base_summary['precision']
        precision_pct = (precision_diff / base_summary['precision'] * 100) if base_summary['precision'] > 0 else 0
        print(f"{'Precision@10':<25} {base_summary['precision']:<20.3f} {hybrid_summary['precision']:<20.3f} "
              f"{precision_diff:+.3f}{' ':<16} {precision_pct:+.1f}%")
        
        # Recall
        recall_diff = hybrid_summary['recall'] - base_summary['recall']
        recall_pct = (recall_diff / base_summary['recall'] * 100) if base_summary['recall'] > 0 else 0
        print(f"{'Recall@10':<25} {base_summary['recall']:<20.3f} {hybrid_summary['recall']:<20.3f} "
              f"{recall_diff:+.3f}{' ':<16} {recall_pct:+.1f}%")
        
        # MRR
        mrr_diff = hybrid_summary['mrr'] - base_summary['mrr']
        mrr_pct = (mrr_diff / base_summary['mrr'] * 100) if base_summary['mrr'] > 0 else 0
        print(f"{'MRR':<25} {base_summary['mrr']:<20.3f} {hybrid_summary['mrr']:<20.3f} "
              f"{mrr_diff:+.3f}{' ':<16} {mrr_pct:+.1f}%")
        
        # NDCG
        ndcg_diff = hybrid_summary['ndcg'] - base_summary['ndcg']
        ndcg_pct = (ndcg_diff / base_summary['ndcg'] * 100) if base_summary['ndcg'] > 0 else 0
        print(f"{'NDCG@10':<25} {base_summary['ndcg']:<20.3f} {hybrid_summary['ndcg']:<20.3f} "
              f"{ndcg_diff:+.3f}{' ':<16} {ndcg_pct:+.1f}%")
        
        # Time
        time_diff = hybrid_summary['time'] - base_summary['time']
        time_pct = (time_diff / base_summary['time'] * 100) if base_summary['time'] > 0 else 0
        print(f"{'Avg Time (s)':<25} {base_summary['time']:<20.4f} {hybrid_summary['time']:<20.4f} "
              f"{time_diff:+.4f}{' ':<16} {time_pct:+.1f}%")
        
        # Query-by-query comparison
        print("\n" + "="*80)
        print("QUERY-BY-QUERY COMPARISON")
        print("="*80)
        print(f"{'Query':<50} {'Base MRR':<15} {'Hybrid MRR':<15} {'Improvement':<15}")
        print("-" * 100)
        
        for test_query in TEST_QUERIES:
            query = test_query["query"]
            base_query_result = base_results.get(query, {})
            hybrid_query_result = hybrid_rerank_results.get(query, {})
            
            base_mrr = base_query_result.get("mrr", 0.0)
            hybrid_mrr = hybrid_query_result.get("mrr", 0.0)
            improvement = hybrid_mrr - base_mrr
            
            # Truncate query if too long
            display_query = query[:47] + "..." if len(query) > 50 else query
            
            print(f"{display_query:<50} {base_mrr:<15.3f} {hybrid_mrr:<15.3f} {improvement:+.3f}")
        
        # Summary
        print("\n" + "="*80)
        print("🎯 KEY FINDINGS")
        print("="*80)
        
        # Clear improvement assessment
        clear_benefit = recall_diff > 0.05 or mrr_diff > 0.05 or ndcg_diff > 0.05
        
        if clear_benefit:
            print("✅ Hybrid search provides CLEAR BENEFITS")
            if recall_diff > 0.05:
                print(f"   📈 Recall improved by {recall_pct:+.1f}% ({recall_diff:+.3f})")
                print(f"      → Finding more relevant documents")
            if mrr_diff > 0.05:
                print(f"   📈 MRR improved by {mrr_pct:+.1f}% ({mrr_diff:+.3f})")
                print(f"      → Relevant results appear higher in rankings")
            if ndcg_diff > 0.05:
                print(f"   📈 NDCG improved by {ndcg_pct:+.1f}% ({ndcg_diff:+.3f})")
                print(f"      → Better ranking quality")
        elif recall_diff > 0 or mrr_diff > 0:
            print("⚠️  Hybrid search shows MODEST IMPROVEMENT")
            if recall_diff > 0:
                print(f"   Recall: {recall_pct:+.1f}% ({recall_diff:+.3f})")
            if mrr_diff > 0:
                print(f"   MRR: {mrr_pct:+.1f}% ({mrr_diff:+.3f})")
        else:
            print("➖ Hybrid search did not show improvement")
            print("   This may indicate:")
            print("     - Test data is too small/simple")
            print("     - Queries don't benefit from keyword search")
            print("     - Reranking needs tuning")
        
        # Performance impact
        if time_diff < -0.1:
            print(f"\n⚡ Performance: {abs(time_pct):.1f}% FASTER ({time_diff:.4f}s improvement)")
        elif time_diff > 0.1:
            print(f"\n⏱️  Performance: {time_pct:+.1f}% slower (+{time_diff:.4f}s)")
            if clear_benefit:
                print("   Trade-off: Better results worth the latency")
        else:
            print(f"\n⚡ Performance: Similar ({time_diff:+.4f}s)")
        
        # Precision trade-off analysis
        if precision_diff < -0.1:
            print(f"\n⚠️  Precision decreased by {abs(precision_pct):.1f}%")
            if recall_diff > 0.1:
                print("   This is EXPECTED: Hybrid search finds more results (higher recall)")
                print("   but some may be less relevant (lower precision)")
                print("   → Reranking should help filter to most relevant")
        
        print("\n" + "="*80)
        print("💡 RECOMMENDATION")
        print("="*80)
        
        if clear_benefit and time_diff < 0.5:
            print("✅ STRONGLY RECOMMENDED for production")
            print(f"   Hybrid search provides clear benefits with minimal latency impact")
            print(f"   Key wins:")
            if recall_diff > 0.05:
                print(f"     ✓ {recall_pct:+.1f}% better recall")
            if mrr_diff > 0.05:
                print(f"     ✓ {mrr_pct:+.1f}% better MRR")
            if time_diff < 0:
                print(f"     ✓ {abs(time_pct):.1f}% faster")
        elif clear_benefit:
            print("✅ RECOMMENDED for production")
            print(f"   Benefits outweigh latency cost")
            print(f"   Consider: Optimize OpenSearch queries or use async batching")
        elif recall_diff > 0.02 or mrr_diff > 0.02:
            print("⚠️  CONDITIONALLY RECOMMENDED")
            print("   Modest improvements - test with production data")
            print("   Consider: Tune reranking parameters or add more test data")
        else:
            print("⚠️  NOT RECOMMENDED based on this test")
            print("   Hybrid search did not show clear benefits")
            print("   Next steps:")
            print("     1. Test with larger, more diverse dataset")
            print("     2. Try different reranking strategies")
            print("     3. Tune OpenSearch query parameters")
            print("     4. Verify keyword search is working correctly")
        
        print("\n" + "="*80)


pytest_plugins = ["pytest_asyncio"]
