"""
Vector Retriever Implementation

Uses vector similarity search for knowledge retrieval.
"""

import logging
from typing import Any, Dict, List, Optional

from .retriever import Retriever
from ..storage.vector_store import VectorStore

logger = logging.getLogger(__name__)


class VectorRetriever(Retriever):
    """Vector similarity-based retriever."""

    def __init__(self, vector_store: VectorStore):
        """Initialize vector retriever with vector store."""
        self.vector_store = vector_store
        logger.info("VectorRetriever initialized")

    async def retrieve(
        self,
        query: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks using vector similarity."""
        try:
            results = await self.vector_store.search_by_text(
                query_text=query,
                collection=collection,
                limit=limit,
                score_threshold=score_threshold,
                metadata_filter=metadata_filter,
            )
            logger.debug(f"Retrieved {len(results)} chunks from {collection}")
            return results
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return []

    async def retrieve_multiple_collections(
        self,
        query: str,
        collections: List[str],
        limit_per_collection: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve from multiple collections."""
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

