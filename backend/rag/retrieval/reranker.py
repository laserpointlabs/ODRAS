"""
Reranker Module for RAG

Provides reranking capabilities to improve retrieval quality by combining
results from multiple sources (vector search, keyword search) and reordering
them based on relevance.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Abstract interface for reranking algorithms."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results based on query relevance.

        Args:
            query: Original query text
            results: List of search results with scores
            top_k: Optional limit for final results

        Returns:
            Reranked list of results
        """
        pass


class ReciprocalRankFusionReranker(Reranker):
    """
    Reciprocal Rank Fusion (RRF) reranker.

    Combines results from multiple search systems (vector, keyword) using RRF algorithm.
    This is a simple but effective method for hybrid search.
    """

    def __init__(self, k: int = 60):
        """
        Initialize RRF reranker.

        Args:
            k: RRF constant (typical values: 60-100)
        """
        self.k = k
        logger.info(f"RRF reranker initialized with k={k}")

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using Reciprocal Rank Fusion.

        RRF score = Σ (1 / (k + rank_i)) for each result list
        """
        if not results:
            return []

        # Group results by chunk_id to handle duplicates
        chunk_scores = defaultdict(lambda: {"score": 0.0, "result": None, "ranks": [], "search_types": set()})

        # Calculate RRF scores
        # IMPORTANT: Use payload chunk_id for matching, not top-level id
        # (OpenSearch uses chunk_id as id, Qdrant uses UUID as id)
        for rank, result in enumerate(results, start=1):
            payload = result.get("payload", {})
            chunk_id = payload.get("original_chunk_id") or payload.get("chunk_id") or result.get("id")
            if not chunk_id:
                chunk_id = f"unknown_{rank}"  # Fallback for results without IDs

            # RRF score component
            rrf_score = 1.0 / (self.k + rank)

            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id]["result"] = result

            chunk_scores[chunk_id]["score"] += rrf_score
            chunk_scores[chunk_id]["ranks"].append(rank)
            
            # Track search types
            search_type = result.get("search_type")
            if search_type:
                chunk_scores[chunk_id]["search_types"].add(search_type)

        # Convert to list and sort by RRF score
        reranked = []
        for chunk_id, data in chunk_scores.items():
            result = data["result"].copy()
            result["rrf_score"] = data["score"]
            result["original_ranks"] = data["ranks"]
            
            # Preserve search_type - if multiple types, mark as hybrid
            search_types = data["search_types"]
            if len(search_types) > 1:
                result["search_type"] = "hybrid"
            elif len(search_types) == 1:
                result["search_type"] = list(search_types)[0]
            # If no search_type, keep original (may be None)
            
            reranked.append(result)

        # Sort by RRF score (descending)
        reranked.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Apply top_k limit (deduplication already handled by grouping)
        if top_k:
            reranked = reranked[:top_k]

        logger.debug(f"RRF reranked {len(results)} results to {len(reranked)} reranked results")
        return reranked


class CrossEncoderReranker(Reranker):
    """
    Cross-encoder reranker using sentence transformers.

    Provides more accurate reranking but requires model inference.
    This is a heavier but more accurate approach than RRF.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Lazy load the cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Cross-encoder reranker initialized with model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, cross-encoder reranking disabled")
            self.model = None
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder model: {e}")
            self.model = None

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank results using cross-encoder model."""
        if not self.model or not results:
            # Fallback to simple score-based sorting
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return results[:top_k] if top_k else results

        try:
            # Extract text content from results
            pairs = []
            for result in results:
                payload = result.get("payload", {})
                text = payload.get("content") or payload.get("text") or ""
                pairs.append([query, text])

            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)

            # Update results with cross-encoder scores
            for i, result in enumerate(results):
                result["cross_encoder_score"] = float(scores[i])
                result["rerank_score"] = float(scores[i])  # Primary score for sorting

            # Sort by cross-encoder score
            reranked = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)

            # Limit to top_k if specified
            if top_k:
                reranked = reranked[:top_k]

            logger.debug(f"Cross-encoder reranked {len(results)} results to {len(reranked)} top results")
            return reranked

        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            # Fallback to original scores
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return results[:top_k] if top_k else results


class HybridReranker(Reranker):
    """
    Hybrid reranker that combines multiple reranking strategies.

    Can combine RRF for multi-source fusion and cross-encoder for final reranking.
    """

    def __init__(self, use_cross_encoder: bool = False):
        """
        Initialize hybrid reranker.

        Args:
            use_cross_encoder: Whether to use cross-encoder for final reranking
        """
        self.rrf = ReciprocalRankFusionReranker()
        self.cross_encoder = CrossEncoderReranker() if use_cross_encoder else None
        logger.info(f"Hybrid reranker initialized (cross-encoder: {use_cross_encoder})")

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Apply hybrid reranking (RRF + optional cross-encoder)."""
        # First apply RRF to combine multiple sources
        rrf_results = await self.rrf.rerank(query, results, top_k=None)

        # Optionally apply cross-encoder for final reranking
        if self.cross_encoder and self.cross_encoder.model:
            final_results = await self.cross_encoder.rerank(query, rrf_results, top_k=top_k)
        else:
            final_results = rrf_results[:top_k] if top_k else rrf_results

        return final_results
