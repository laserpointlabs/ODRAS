"""
Qdrant Vector Store Implementation

Wraps QdrantService to provide VectorStore interface.
"""

import logging
from typing import Any, Dict, List, Optional

from .vector_store import VectorStore
from ...services.config import Settings
from ...services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of VectorStore interface."""

    def __init__(self, settings: Settings):
        """Initialize Qdrant vector store."""
        self.settings = settings
        self.qdrant_service = QdrantService(settings)
        logger.info("QdrantVectorStore initialized")

    async def search(
        self,
        query_vector: List[float],
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        try:
            # QdrantService.search_vectors is synchronous, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.qdrant_service.search_vectors(
                    query_vector=query_vector,
                    collection_name=collection,
                    limit=limit,
                    score_threshold=score_threshold,
                    metadata_filter=metadata_filter,
                ),
            )
            return results
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            raise

    async def search_by_text(
        self,
        query_text: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search by text query using QdrantService's search_similar_chunks."""
        try:
            # QdrantService.search_similar_chunks is already async
            results = await self.qdrant_service.search_similar_chunks(
                query_text=query_text,
                collection_name=collection,
                limit=limit,
                score_threshold=score_threshold,
                metadata_filter=metadata_filter,
            )
            return results
        except Exception as e:
            logger.error(f"Qdrant text search failed: {e}")
            raise

    async def store(
        self,
        collection: str,
        vectors: List[Dict[str, Any]],
    ) -> List[str]:
        """Store vectors in Qdrant."""
        try:
            # QdrantService.store_vectors is synchronous, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            stored_ids = await loop.run_in_executor(
                None,
                lambda: self.qdrant_service.store_vectors(
                    collection_name=collection,
                    vectors=vectors,
                ),
            )
            return stored_ids
        except Exception as e:
            logger.error(f"Qdrant store failed: {e}")
            raise

    async def ensure_collection(
        self,
        collection: str,
        vector_size: int = 384,
        distance: str = "Cosine",
    ) -> bool:
        """Ensure Qdrant collection exists."""
        try:
            # QdrantService.ensure_collection is synchronous, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.qdrant_service.ensure_collection(
                    collection_name=collection,
                    vector_size=vector_size,
                    distance=distance,
                ),
            )
            return result
        except Exception as e:
            logger.error(f"Qdrant collection creation failed: {e}")
            raise

    async def delete_vectors(
        self,
        collection: str,
        vector_ids: List[str],
    ) -> bool:
        """Delete vectors from Qdrant."""
        try:
            # QdrantService.delete_vectors is synchronous, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.qdrant_service.delete_vectors(
                    collection_name=collection,
                    point_ids=vector_ids,
                ),
            )
            return result
        except Exception as e:
            logger.error(f"Qdrant vector deletion failed: {e}")
            raise

    async def get_collection_info(
        self,
        collection: str,
    ) -> Dict[str, Any]:
        """Get Qdrant collection information."""
        try:
            # QdrantService.get_collection_info is synchronous, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self.qdrant_service.get_collection_info(collection_name=collection),
            )
            return info or {}
        except Exception as e:
            logger.error(f"Failed to get Qdrant collection info: {e}")
            raise

