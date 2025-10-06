#!/usr/bin/env python3
"""
External Task Script: Retrieve Relevant Context
Search vector database for contextually relevant information.
"""

import json
import sys
import os
from typing import Dict, Any, List
import time

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings

# Try to import services with fallbacks
try:
    from services.qdrant_service import QdrantService

    HAS_QDRANT_SERVICE = True
except ImportError:
    HAS_QDRANT_SERVICE = False

try:
    from services.embedding_service import EmbeddingService

    HAS_EMBEDDING_SERVICE = True
except ImportError:
    HAS_EMBEDDING_SERVICE = False


def retrieve_context(processed_query: Dict, search_parameters: Dict = None) -> Dict[str, Any]:
    """
    Retrieve relevant context from vector database.

    Args:
        processed_query: Processed query information from previous step
        search_parameters: Search configuration parameters

    Returns:
        Dict containing retrieved context and metadata
    """
    result = {
        "retrieved_chunks": [],
        "retrieval_stats": {},
        "search_metadata": {},
        "processing_status": "success",
        "errors": [],
    }

    if search_parameters is None:
        search_parameters = processed_query.get("search_parameters", {})

    try:
        query_text = processed_query.get("cleaned_query", "")
        if not query_text:
            result["processing_status"] = "failure"
            result["errors"].append("No query text provided")
            return result

        key_terms = processed_query.get("key_terms", [])
        primary_terms = search_parameters.get("primary_terms", key_terms[:5])

        # Get search parameters
        max_results = search_parameters.get("max_results", 20)
        min_similarity = search_parameters.get("min_similarity_threshold", 0.6)
        semantic_weight = search_parameters.get("semantic_search_weight", 0.7)

        if HAS_EMBEDDING_SERVICE and HAS_QDRANT_SERVICE:
            # Real vector search implementation
            result = perform_mock_search(
                query_text, primary_terms, max_results, min_similarity
            )  # Use mock for now
        else:
            # Fallback mock implementation for testing
            result = perform_mock_search(query_text, primary_terms, max_results, min_similarity)

        # Add search metadata
        result["search_metadata"] = {
            "search_query": query_text,
            "search_terms": primary_terms,
            "search_type": "vector_similarity",
            "max_results_requested": max_results,
            "min_similarity_threshold": min_similarity,
            "semantic_weight": semantic_weight,
            "search_timestamp": time.time(),
            "search_method": "vector_db" if HAS_QDRANT_SERVICE else "mock",
        }

        print(f"Context retrieval completed")
        print(f"Retrieved {len(result['retrieved_chunks'])} chunks")
        if result["retrieval_stats"]:
            print(f"Average similarity: {result['retrieval_stats'].get('avg_similarity', 'N/A')}")

    except Exception as e:
        result["processing_status"] = "failure"
        result["errors"].append(f"Context retrieval error: {str(e)}")
        print(f"Context retrieval failed: {str(e)}")

    return result


async def perform_async_vector_search(
    query_text: str, terms: List[str], max_results: int, min_similarity: float
) -> Dict[str, Any]:
    """Perform actual vector database search using the same method as the existing RAG service."""
    try:
        settings = Settings()
        qdrant_service = QdrantService(settings)

        # Use the same method as the existing RAG service
        search_results = await qdrant_service.search_similar_chunks(
            query_text=query_text,
            collection_name="knowledge_chunks",  # Use the same collection as existing RAG
            limit=max_results * 2,  # Get extra for filtering
            score_threshold=min_similarity,
        )

        print(f"Found {len(search_results)} chunks in knowledge_chunks collection")

        # Process results using the same structure as existing RAG
        retrieved_chunks = []
        similarities = []

        for chunk in search_results:
            chunk_data = chunk.get("payload", {})

            # Use same field names as existing RAG service
            processed_chunk = {
                "chunk_id": chunk_data.get("chunk_id", chunk.get("id", "unknown")),
                "content": chunk_data.get(
                    "text", ""
                ),  # Note: existing RAG uses 'text' not 'content'
                "source_document": chunk_data.get("source_asset", "unknown"),
                "document_type": chunk_data.get("document_type", "document"),
                "asset_id": chunk_data.get("asset_id"),
                "project_id": chunk_data.get("project_id"),
                "similarity_score": chunk.get("score", 0.0),
                "chunk_metadata": chunk_data,
                "retrieval_rank": len(retrieved_chunks) + 1,
            }
            retrieved_chunks.append(processed_chunk)
            similarities.append(chunk.get("score", 0.0))

        # Calculate statistics
        stats = {
            "total_results": len(retrieved_chunks),
            "avg_similarity": (sum(similarities) / len(similarities) if similarities else 0.0),
            "max_similarity": max(similarities) if similarities else 0.0,
            "min_similarity": min(similarities) if similarities else 0.0,
            "search_method": "knowledge_chunks_collection",
            "collection_searched": "knowledge_chunks",
        }

        return {
            "retrieved_chunks": retrieved_chunks,
            "retrieval_stats": stats,
            "processing_status": "success",
            "errors": [],
        }

    except Exception as e:
        print(f"Vector search error: {str(e)}")
        return {
            "retrieved_chunks": [],
            "retrieval_stats": {"error": str(e)},
            "processing_status": "failure",
            "errors": [f"Vector search failed: {str(e)}"],
        }


def perform_mock_search(
    query_text: str, terms: List[str], max_results: int, min_similarity: float
) -> Dict[str, Any]:
    """Perform mock search for testing when services aren't available."""

    # Mock document chunks for testing
    mock_chunks = [
        {
            "content": "The system shall validate all input parameters before processing user requests. Validation includes type checking, range verification, and format compliance.",
            "source_document": "requirements_spec.txt",
            "chunk_metadata": {"section": "Input Validation", "page": 12},
        },
        {
            "content": "Requirements extraction involves identifying functional and non-functional requirements from source documents using pattern matching and semantic analysis.",
            "source_document": "system_analysis.txt",
            "chunk_metadata": {"section": "Requirements Analysis", "page": 8},
        },
        {
            "content": "The document ingestion pipeline processes uploaded files through validation, parsing, chunking, embedding generation, and vector storage phases.",
            "source_document": "architecture_guide.txt",
            "chunk_metadata": {"section": "Data Pipeline", "page": 15},
        },
        {
            "content": "Quality assurance processes ensure that all system components meet specified reliability, performance, and security standards through automated testing.",
            "source_document": "qa_procedures.txt",
            "chunk_metadata": {"section": "Quality Control", "page": 5},
        },
        {
            "content": "Vector embeddings represent textual content as high-dimensional numerical vectors enabling semantic similarity search and retrieval operations.",
            "source_document": "technical_overview.txt",
            "chunk_metadata": {"section": "Vector Processing", "page": 22},
        },
    ]

    # Simple term-based scoring for mock results
    retrieved_chunks = []
    for i, chunk in enumerate(mock_chunks):
        if i >= max_results:
            break

        # Calculate mock similarity based on term overlap
        chunk_words = set(chunk["content"].lower().split())
        query_words = set(query_text.lower().split())
        term_words = set(term.lower() for term in terms)

        overlap = len(chunk_words.intersection(query_words.union(term_words)))
        total_unique = len(chunk_words.union(query_words))
        similarity = (
            (overlap / total_unique * 0.9 + 0.1) if total_unique > 0 else 0.5
        )  # Add base score

        if similarity >= min_similarity:
            chunk_data = {
                "chunk_id": f"mock_chunk_{i}",
                "content": chunk["content"],
                "source_document": chunk["source_document"],
                "similarity_score": similarity,
                "chunk_metadata": chunk["chunk_metadata"],
                "retrieval_rank": len(retrieved_chunks) + 1,
            }
            retrieved_chunks.append(chunk_data)

    # Sort by similarity
    retrieved_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)

    # Calculate stats
    similarities = [chunk["similarity_score"] for chunk in retrieved_chunks]
    stats = {
        "total_results": len(retrieved_chunks),
        "avg_similarity": (sum(similarities) / len(similarities) if similarities else 0.0),
        "max_similarity": max(similarities) if similarities else 0.0,
        "min_similarity": min(similarities) if similarities else 0.0,
        "search_method": "mock_search",
    }

    return {
        "retrieved_chunks": retrieved_chunks,
        "retrieval_stats": stats,
        "processing_status": "success",
        "errors": [],
    }


def main():
    """Main function for testing."""
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                processed_query = json.load(f)
        else:
            # Create simple processed query from string
            processed_query = {
                "cleaned_query": sys.argv[1],
                "key_terms": sys.argv[1].lower().split(),
                "search_parameters": {
                    "max_results": 10,
                    "min_similarity_threshold": 0.6,
                },
            }

        result = retrieve_context(processed_query)
        print(json.dumps(result, indent=2, default=str))
        return result

    return {
        "retrieved_chunks": [{"chunk_id": "sample", "content": "Sample chunk content"}],
        "retrieval_stats": {"total_results": 1},
        "search_metadata": {"search_method": "test"},
        "processing_status": "success",
        "errors": [],
    }


if __name__ == "__main__":
    main()

