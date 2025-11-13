"""
Hybrid Retriever Implementation

Combines vector similarity search (Qdrant) with full-text/keyword search (OpenSearch)
to provide comprehensive retrieval capabilities.
"""

import logging
from typing import Any, Dict, List, Optional
import asyncio

from .retriever import Retriever
from ..storage.vector_store import VectorStore
from ..storage.text_search_store import TextSearchStore
from .reranker import Reranker, ReciprocalRankFusionReranker

logger = logging.getLogger(__name__)


class HybridRetriever(Retriever):
    """
    Hybrid retriever combining vector and keyword search.

    Performs parallel searches across:
    - Vector store (Qdrant) for semantic similarity
    - Text search store (OpenSearch) for keyword matching

    Then combines results using reranking (RRF by default).
    """

    def __init__(
        self,
        vector_store: VectorStore,
        text_search_store: Optional[TextSearchStore] = None,
        reranker: Optional[Reranker] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        """
        Initialize hybrid retriever.

        Args:
            vector_store: Vector store for semantic search (required)
            text_search_store: Text search store for keyword search (optional)
            reranker: Reranker for combining results (defaults to RRF)
            vector_weight: Weight for vector search results (0.0-1.0)
            keyword_weight: Weight for keyword search results (0.0-1.0)
        """
        self.vector_store = vector_store
        self.text_search_store = text_search_store
        self.reranker = reranker or ReciprocalRankFusionReranker()
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

        logger.info(
            f"HybridRetriever initialized (vector: {vector_weight}, keyword: {keyword_weight}, "
            f"text_search: {text_search_store is not None})"
        )

    async def retrieve(
        self,
        query: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve using hybrid search (vector + keyword if available)."""
        try:
            # Perform parallel searches
            tasks = []

            # Vector search (always performed)
            vector_task = self.vector_store.search_by_text(
                query_text=query,
                collection=collection,
                limit=limit * 2,  # Get more results for reranking
                score_threshold=score_threshold,
                metadata_filter=metadata_filter,
            )
            tasks.append(("vector", vector_task))

            # Keyword search (if text search store available)
            if self.text_search_store:
                keyword_task = self.text_search_store.search(
                    query_text=query,
                    index=collection,  # Use same collection/index name
                    limit=limit * 2,
                    metadata_filter=metadata_filter,
                )
                tasks.append(("keyword", keyword_task))

            # Execute searches in parallel
            results_dict = {}
            if tasks:
                search_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
                for (search_type, _), results in zip(tasks, search_results):
                    if isinstance(results, Exception):
                        logger.error(f"{search_type} search failed: {type(results).__name__}: {results}")
                        import traceback
                        logger.debug(f"{search_type} search traceback: {traceback.format_exc()}")
                        results_dict[search_type] = []
                    else:
                        results_dict[search_type] = results
                        logger.debug(f"{search_type} search returned {len(results)} results")

            # Combine results
            all_results = []
            for search_type, results in results_dict.items():
                # Add search type metadata
                for result in results:
                    result["search_type"] = search_type
                    # Normalize score field
                    if "score" not in result:
                        result["score"] = result.get("_score", 0.0)
                all_results.extend(results)

            # Deduplicate by chunk_id (prefer keeping both vector and keyword results for reranking)
            seen_chunks = {}
            unique_results = []
            for result in all_results:
                chunk_id = result.get("id") or result.get("payload", {}).get("chunk_id") or result.get("payload", {}).get("original_chunk_id")
                if chunk_id:
                    # Keep track of both search types for same chunk (needed for RRF)
                    if chunk_id not in seen_chunks:
                        seen_chunks[chunk_id] = []
                    seen_chunks[chunk_id].append(result)
                else:
                    # No chunk_id - add directly
                    unique_results.append(result)
            
            # Flatten: keep all results for reranking (RRF will combine them)
            for chunk_id, results in seen_chunks.items():
                unique_results.extend(results)

            # Apply reranking to combine results from different sources
            # Request more results from reranker to account for deduplication
            if len(results_dict) > 1 and self.reranker:
                # Request 2x limit to ensure we have enough after deduplication
                reranked = await self.reranker.rerank(query, unique_results, top_k=limit * 2)
                
                # Final deduplication after reranking (keep best result per chunk)
                # Preserve search_type by merging results from both sources
                final_results = []
                seen_final = {}  # chunk_id -> result dict
                for result in reranked:
                    # Extract chunk_id from payload (consistent with RRF matching logic)
                    payload = result.get("payload", {})
                    chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or result.get("id")
                    if chunk_id:
                        if chunk_id not in seen_final:
                            seen_final[chunk_id] = result
                        else:
                            # Merge search types if we have results from both sources
                            existing = seen_final[chunk_id]
                            existing_type = existing.get("search_type", "unknown")
                            new_type = result.get("search_type", "unknown")
                            if existing_type != new_type and existing_type != "hybrid" and new_type != "hybrid":
                                # Mark as hybrid if from both sources
                                existing["search_type"] = "hybrid"
                                # Combine RRF scores when both sources found the same chunk
                                existing["rrf_score"] = existing.get("rrf_score", 0) + result.get("rrf_score", 0)
                            # Keep the one with higher score (or merged hybrid if both)
                            existing_score = existing.get("rrf_score", existing.get("score", 0))
                            new_score = result.get("rrf_score", result.get("score", 0))
                            if new_score > existing_score:
                                seen_final[chunk_id] = result
                    else:
                        final_results.append(result)
                
                # Convert dict to list and sort by score (reranked should already be sorted)
                final_list = list(seen_final.values())
                final_list.sort(key=lambda x: x.get("rrf_score", x.get("score", 0)), reverse=True)
                final_results.extend(final_list)
                
                logger.debug(
                    f"Hybrid search: {len(results_dict.get('vector', []))} vector + "
                    f"{len(results_dict.get('keyword', []))} keyword → "
                    f"{len(reranked)} reranked → {len(final_results)} final deduplicated results"
                )
                return final_results[:limit]
            else:
                # Single source or no reranker - deduplicate and sort by score
                final_results = []
                seen_final = set()
                for result in unique_results:
                    chunk_id = result.get("id") or result.get("payload", {}).get("chunk_id") or result.get("payload", {}).get("original_chunk_id")
                    if chunk_id and chunk_id not in seen_final:
                        seen_final.add(chunk_id)
                        final_results.append(result)
                    elif not chunk_id:
                        final_results.append(result)
                
                final_results.sort(key=lambda x: x.get("score", 0), reverse=True)
                return final_results[:limit]

        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            # Fallback to vector-only search
            return await self.vector_store.search_by_text(
                query_text=query,
                collection=collection,
                limit=limit,
                score_threshold=score_threshold,
                metadata_filter=metadata_filter,
            )

    async def retrieve_multiple_collections(
        self,
        query: str,
        collections: List[str],
        limit_per_collection: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve from multiple collections using hybrid search."""
        results = {}
        for collection in collections:
            try:
                collection_results = await self.retrieve(
                    query=query,
                    collection=collection,
                    limit=limit_per_collection,
                    score_threshold=score_threshold,
                    metadata_filter=metadata_filter,
                )
                results[collection] = collection_results
            except Exception as e:
                logger.warning(f"Failed to retrieve from {collection}: {e}")
                results[collection] = []

        return results
