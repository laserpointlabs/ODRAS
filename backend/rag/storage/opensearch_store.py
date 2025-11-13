"""
OpenSearch/Elasticsearch Text Search Implementation

Provides full-text search capabilities to complement Qdrant vector search.
OpenSearch is used for keyword matching, BM25 ranking, and exact term searches.
"""

import logging
from typing import Any, Dict, List, Optional
import asyncio
from asyncio import iscoroutine

from .text_search_store import TextSearchStore
from ...services.config import Settings

logger = logging.getLogger(__name__)

# Try to import OpenSearch client
try:
    from opensearchpy import AsyncOpenSearch
    OPENSEARCH_AVAILABLE = True
    OPENSEARCH_LIBRARY = "opensearch"
except ImportError:
    try:
        # Fallback to Elasticsearch if OpenSearch not available
        from elasticsearch import AsyncElasticsearch
        OPENSEARCH_AVAILABLE = True
        OPENSEARCH_LIBRARY = "elasticsearch"
        AsyncOpenSearch = AsyncElasticsearch
    except ImportError:
        OPENSEARCH_AVAILABLE = False
        OPENSEARCH_LIBRARY = None
        AsyncOpenSearch = None


class OpenSearchTextStore(TextSearchStore):
    """OpenSearch/Elasticsearch implementation for full-text search."""

    def __init__(self, settings: Settings):
        """Initialize OpenSearch text search store."""
        if not OPENSEARCH_AVAILABLE:
            raise RuntimeError(
                "OpenSearch/Elasticsearch client not available. "
                "Install with: pip install opensearch-py or pip install elasticsearch"
            )

        self.settings = settings
        self.client = None

        # Get OpenSearch/Elasticsearch URL from settings
        self.opensearch_url = getattr(settings, "opensearch_url", "http://localhost:9200")
        self.opensearch_user = getattr(settings, "opensearch_user", None)
        self.opensearch_password = getattr(settings, "opensearch_password", None)

        self._init_client()

    def _init_client(self):
        """Initialize OpenSearch/Elasticsearch async client connection."""
        try:
            http_auth = None
            if self.opensearch_user and self.opensearch_password:
                http_auth = (self.opensearch_user, self.opensearch_password)

            # AsyncOpenSearch uses aiohttp by default - no need for RequestsHttpConnection
            # RequestsHttpConnection is for synchronous clients only
            self.client = AsyncOpenSearch(
                hosts=[self.opensearch_url],
                http_auth=http_auth,
                use_ssl=False,
                verify_certs=False,
                timeout=30,
            )

            logger.info(f"OpenSearch/Elasticsearch async client initialized: {self.opensearch_url}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {str(e)}")
            raise RuntimeError(f"OpenSearch connection failed: {str(e)}")

    async def search(
        self,
        query_text: str,
        index: str,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform full-text search using BM25."""
        try:
            # Build query - optimize for both exact IDs and semantic queries
            # For exact IDs/codes (containing hyphens, alphanumeric), use term/wildcard
            # For general queries, use phrase match and multi-match
            query_clauses = []
            
            # Detect if query looks like an exact ID (contains hyphens, alphanumeric pattern)
            is_exact_id = bool(query_text and (
                '-' in query_text or 
                (query_text.replace('-', '').replace('.', '').replace(' ', '').isalnum() and len(query_text.split()) == 1)
            ))
            
            if is_exact_id:
                # For exact IDs, use match query with high boost (not term - too strict)
                # Match query will find the phrase even if tokenized
                query_clauses.append({
                    "match": {
                        "content": {
                            "query": query_text,
                            "boost": 10.0,
                            "operator": "and",  # All terms must match
                        }
                    }
                })
                query_clauses.append({
                    "match": {
                        "text": {
                            "query": query_text,
                            "boost": 10.0,
                            "operator": "and",
                        }
                    }
                })
                # Also try on keyword field for exact match
                query_clauses.append({
                    "match": {
                        "content.keyword": {
                            "query": query_text,
                            "boost": 15.0,
                        }
                    }
                })
                query_clauses.append({
                    "match": {
                        "text.keyword": {
                            "query": query_text,
                            "boost": 15.0,
                        }
                    }
                })
            
            # Exact phrase match (high boost for exact phrases)
            query_clauses.append({
                "match_phrase": {
                "content": {
                    "query": query_text,
                    "boost": 3.0
                }
            }})
            query_clauses.append({
                "match_phrase": {
                    "title": {
                        "query": query_text,
                        "boost": 2.0
                    }
                }
            })
            
            # Multi-match for general terms (fuzzy matching)
            query_clauses.append({
                "multi_match": {
                    "query": query_text,
                    "fields": fields or ["content^2", "text", "title^1.5"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "or",
                }
            })
            
            query = {
                "query": {
                    "bool": {
                        "should": query_clauses,
                        "minimum_should_match": 1
                    }
                },
                "size": limit,
            }

            # Add filters
            if metadata_filter:
                filter_clauses = []
                for key, value in metadata_filter.items():
                    if isinstance(value, list):
                        filter_clauses.append({"terms": {key: value}})
                    else:
                        filter_clauses.append({"term": {key: value}})

                if filter_clauses:
                    query["query"]["bool"]["filter"] = filter_clauses

            # Execute search (opensearch-py async client)
            # AsyncOpenSearch.search() returns a coroutine that resolves to a dict
            logger.debug(f"OpenSearch query: {query}")
            response = await self.client.search(index=index, body=query)
            logger.debug(f"OpenSearch response total: {response.get('hits', {}).get('total', {}).get('value', 0)} hits")

            # Format results - response is a dict
            results = []
            hits = response.get("hits", {}).get("hits", [])
            
            for hit in hits:
                # Extract chunk_id from _source or _id
                source = hit.get("_source", {})
                chunk_id = source.get("chunk_id") or source.get("original_chunk_id") or hit.get("_id")
                
                results.append({
                    "id": chunk_id,  # Use chunk_id for matching with vector results
                    "score": hit.get("_score", 0.0),
                    "payload": source,
                    "search_type": "keyword",  # Flag to distinguish from vector search
                })

            logger.debug(f"OpenSearch found {len(results)} results for query: '{query_text[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"OpenSearch search failed: {e}")
            return []

    async def index_document(
        self,
        index: str,
        document_id: str,
        document: Dict[str, Any],
    ) -> bool:
        """Index a document for full-text search."""
        try:
            # AsyncOpenSearch.index() uses body parameter
            await self.client.index(
                index=index,
                id=document_id,
                body=document,
            )
            logger.debug(f"Indexed document {document_id} in {index}")
            # Refresh index to make document immediately searchable
            try:
                await self.client.indices.refresh(index=index)
            except Exception as e:
                logger.debug(f"Index refresh failed (non-critical): {e}")
            return True
        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            return False

    async def delete_document(
        self,
        index: str,
        document_id: str,
    ) -> bool:
        """Delete a document from the index."""
        try:
            await self.client.delete(index=index, id=document_id)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete document {document_id}: {e}")
            return False

    async def ensure_index(
        self,
        index: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Ensure index exists with specified settings."""
        try:
            exists = await self.client.indices.exists(index=index)
            if exists:
                logger.debug(f"Index '{index}' already exists")
                return True

            # Create index with default mapping optimized for text search
            index_body = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "standard": {
                                "type": "standard"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "content": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}  # For exact matching
                            }
                        },
                        "text": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}  # For exact matching
                            }
                        },
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}  # For exact matching
                            }
                        },
                        "chunk_id": {"type": "keyword"},
                        "original_chunk_id": {"type": "keyword"},  # For matching with Qdrant
                        "asset_id": {"type": "keyword"},
                        "project_id": {"type": "keyword"},
                        "document_type": {"type": "keyword"},
                    }
                }
            }

            if settings:
                index_body["settings"].update(settings)

            await self.client.indices.create(index=index, body=index_body)
            logger.info(f"Created OpenSearch index '{index}'")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure index '{index}': {e}")
            return False

    async def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]],
    ) -> bool:
        """Bulk index multiple documents."""
        try:
            actions = []
            for doc in documents:
                doc_id = doc.get("id") or doc.get("chunk_id")
                if not doc_id:
                    continue

                action = {
                    "_index": index,
                    "_id": doc_id,
                    "_source": doc,
                }
                actions.append(action)

            if not actions:
                return True

            # Use bulk API
            try:
                from opensearchpy.helpers import async_bulk
            except ImportError:
                from elasticsearch.helpers import async_bulk
            await async_bulk(self.client, actions)
            logger.info(f"Bulk indexed {len(actions)} documents to {index}")
            # Refresh index to make documents immediately searchable
            try:
                await self.client.indices.refresh(index=index)
            except Exception as e:
                logger.debug(f"Index refresh failed (non-critical): {e}")
            return True

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return False
