"""
Text Search Store Interface for Full-Text/Keyword Search

Provides abstraction for text-based search engines (OpenSearch, Elasticsearch, etc.)
to complement vector similarity search from Qdrant.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class TextSearchStore(ABC):
    """Abstract interface for full-text/keyword search backends."""

    @abstractmethod
    async def search(
        self,
        query_text: str,
        index: str,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text/keyword search.

        Args:
            query_text: Text query (keywords, phrases)
            index: Index name to search
            limit: Maximum number of results
            metadata_filter: Optional metadata filters
            fields: Optional list of fields to search

        Returns:
            List of search results with scores and metadata
        """
        pass

    @abstractmethod
    async def index_document(
        self,
        index: str,
        document_id: str,
        document: Dict[str, Any],
    ) -> bool:
        """
        Index a document for full-text search.

        Args:
            index: Index name
            document_id: Unique document identifier
            document: Document data with text fields

        Returns:
            True if indexing succeeded
        """
        pass

    @abstractmethod
    async def delete_document(
        self,
        index: str,
        document_id: str,
    ) -> bool:
        """Delete a document from the index."""
        pass

    @abstractmethod
    async def ensure_index(
        self,
        index: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Ensure index exists with specified settings."""
        pass

    @abstractmethod
    async def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]],
    ) -> bool:
        """Bulk index multiple documents."""
        pass


