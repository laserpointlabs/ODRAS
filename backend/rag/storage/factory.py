"""
Vector Store Factory

Creates appropriate VectorStore implementation based on configuration.
"""

import logging
from typing import Optional

from .vector_store import VectorStore
from .qdrant_store import QdrantVectorStore
from .text_search_store import TextSearchStore
from .opensearch_store import OpenSearchTextStore
from ...services.config import Settings

logger = logging.getLogger(__name__)


def create_vector_store(settings: Optional[Settings] = None) -> VectorStore:
    """
    Factory function to create vector store based on configuration.

    Args:
        settings: Optional settings instance (creates default if not provided)

    Returns:
        VectorStore implementation instance

    Raises:
        ValueError: If backend type is unknown or unsupported
    """
    if settings is None:
        from ...services.config import Settings
        settings = Settings()

    # Get backend type from settings (default to qdrant)
    backend = getattr(settings, "vector_store_backend", "qdrant").lower()

    if backend == "qdrant":
        logger.info("Creating QdrantVectorStore")
        return QdrantVectorStore(settings)
    elif backend == "opensearch":
        # Stretch goal - OpenSearch implementation
        raise NotImplementedError("OpenSearch backend not yet implemented")
    else:
        raise ValueError(f"Unknown vector store backend: {backend}")
