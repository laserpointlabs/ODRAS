"""
Text Search Store Factory

Creates appropriate TextSearchStore implementation based on configuration.
"""

import logging
from typing import Optional

from .text_search_store import TextSearchStore
from .opensearch_store import OpenSearchTextStore
from ...services.config import Settings

logger = logging.getLogger(__name__)


def create_text_search_store(settings: Optional[Settings] = None) -> Optional[TextSearchStore]:
    """
    Factory function to create text search store based on configuration.

    Args:
        settings: Optional settings instance (creates default if not provided)

    Returns:
        TextSearchStore implementation instance, or None if not enabled/available
    """
    if settings is None:
        from ...services.config import Settings
        settings = Settings()

    # Check if text search is enabled
    opensearch_enabled = getattr(settings, "opensearch_enabled", "false").lower() == "true"
    if not opensearch_enabled:
        logger.debug("Text search not enabled in settings")
        return None

    # Get backend type (currently only OpenSearch supported)
    backend = getattr(settings, "text_search_backend", "opensearch").lower()

    if backend == "opensearch":
        try:
            logger.info("Creating OpenSearchTextStore")
            return OpenSearchTextStore(settings)
        except Exception as e:
            logger.warning(f"Failed to create OpenSearchTextStore: {e}")
            return None
    elif backend == "elasticsearch":
        # Elasticsearch uses same implementation as OpenSearch
        try:
            logger.info("Creating OpenSearchTextStore (Elasticsearch mode)")
            return OpenSearchTextStore(settings)
        except Exception as e:
            logger.warning(f"Failed to create Elasticsearch store: {e}")
            return None
    else:
        logger.warning(f"Unknown text search backend: {backend}")
        return None


