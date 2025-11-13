"""
Abstract Vector Store Interface for RAG Modularization

Provides a clean abstraction over vector storage backends (Qdrant, OpenSearch, etc.)
to enable easy swapping and testing of different vector stores.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Abstract interface for vector storage backends."""

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the collection.

        Args:
            query_vector: Query embedding vector
            collection: Collection name to search
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters

        Returns:
            List of search results with scores and payloads
        """
        pass

    @abstractmethod
    async def search_by_text(
        self,
        query_text: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search by text query (handles embedding generation internally).

        Args:
            query_text: Text query to search for
            collection: Collection name to search
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters

        Returns:
            List of search results with scores and payloads
        """
        pass

    @abstractmethod
    async def store(
        self,
        collection: str,
        vectors: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Store vectors in the collection.

        Args:
            collection: Collection name
            vectors: List of vector data dicts with 'id', 'vector', 'payload'

        Returns:
            List of stored vector IDs
        """
        pass

    @abstractmethod
    async def ensure_collection(
        self,
        collection: str,
        vector_size: int = 384,
        distance: str = "Cosine",
    ) -> bool:
        """
        Ensure collection exists with specified configuration.

        Args:
            collection: Collection name
            vector_size: Vector dimension
            distance: Distance metric (Cosine, Euclidean, Dot)

        Returns:
            True if collection exists or was created
        """
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        collection: str,
        vector_ids: List[str],
    ) -> bool:
        """
        Delete vectors by IDs.

        Args:
            collection: Collection name
            vector_ids: List of vector IDs to delete

        Returns:
            True if deletion succeeded
        """
        pass

    @abstractmethod
    async def get_collection_info(
        self,
        collection: str,
    ) -> Dict[str, Any]:
        """
        Get collection information.

        Args:
            collection: Collection name

        Returns:
            Dictionary with collection metadata
        """
        pass

