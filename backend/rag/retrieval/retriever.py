"""
Abstract Retriever Interface for RAG Modularization

Provides abstraction for knowledge retrieval strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Retriever(ABC):
    """Abstract interface for knowledge retrieval."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge chunks.

        Args:
            query: Query text
            collection: Collection to search
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters

        Returns:
            List of relevant chunks with scores and metadata
        """
        pass

    @abstractmethod
    async def retrieve_multiple_collections(
        self,
        query: str,
        collections: List[str],
        limit_per_collection: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve from multiple collections.

        Args:
            query: Query text
            collections: List of collection names
            limit_per_collection: Results per collection
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters

        Returns:
            Dictionary mapping collection names to results
        """
        pass

