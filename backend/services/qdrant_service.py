"""
Qdrant Vector Database Integration Service.

Provides high-level interface for vector operations including:
- Collection management
- Vector storage and retrieval  
- Semantic search with metadata filtering
- Batch operations and optimization
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest
    from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

from .config import Settings

logger = logging.getLogger(__name__)

class QdrantService:
    """
    High-level Qdrant vector database service.
    
    Provides operations for knowledge management including vector storage,
    semantic search, and metadata filtering.
    """
    
    def __init__(self, settings: Settings = None):
        """Initialize Qdrant service with configuration."""
        if not QDRANT_AVAILABLE:
            raise RuntimeError("Qdrant client not available. Install with: pip install qdrant-client")
        
        self.settings = settings or Settings()
        self.client = None
        self.collections = {}  # Cache collection info
        
        # Initialize client
        self._init_client()
    
    def _init_client(self):
        """Initialize Qdrant client connection."""
        try:
            # Use Qdrant URL from settings (default to localhost)
            qdrant_url = getattr(self.settings, 'qdrant_url', 'http://localhost:6333')
            
            logger.info(f"Connecting to Qdrant at {qdrant_url}")
            self.client = QdrantClient(url=qdrant_url)
            
            # Test connection
            self.client.get_collections()
            logger.info("Qdrant connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise RuntimeError(f"Qdrant connection failed: {str(e)}")
    
    def ensure_collection(self, collection_name: str, vector_size: int = 384, distance: str = "Cosine") -> bool:
        """
        Ensure collection exists with specified configuration.
        
        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors (default 384 for sentence-transformers)
            distance: Distance metric (Cosine, Euclidean, Dot)
            
        Returns:
            True if collection was created/exists
        """
        try:
            # Check if collection already exists
            collections = self.client.get_collections()
            existing_collections = [col.name for col in collections.collections]
            
            if collection_name in existing_collections:
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            
            # Create collection
            distance_enum = getattr(Distance, distance.upper(), Distance.COSINE)
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance_enum)
            )
            
            logger.info(f"Created Qdrant collection '{collection_name}' with vector size {vector_size} and {distance} distance")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure collection '{collection_name}': {str(e)}")
            return False
    
    def store_vectors(
        self, 
        collection_name: str, 
        vectors: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store vectors with metadata in Qdrant.
        
        Args:
            collection_name: Target collection name
            vectors: List of vector data with format:
                {
                    'id': 'uuid-string',  # optional, will generate if not provided
                    'vector': [0.1, 0.2, ...],  # embedding vector
                    'payload': {  # metadata
                        'chunk_id': 'uuid',
                        'asset_id': 'uuid', 
                        'content': 'text content',
                        'chunk_type': 'text',
                        'project_id': 'uuid',
                        'document_type': 'requirements',
                        ...
                    }
                }
                
        Returns:
            List of point IDs that were stored
        """
        try:
            if not vectors:
                return []
            
            # Prepare points for Qdrant
            points = []
            point_ids = []
            
            for vector_data in vectors:
                # Generate ID if not provided
                point_id = vector_data.get('id', str(uuid4()))
                point_ids.append(point_id)
                
                # Create point structure
                point = PointStruct(
                    id=point_id,
                    vector=vector_data['vector'],
                    payload=vector_data.get('payload', {})
                )
                points.append(point)
            
            # Batch upsert
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Stored {len(points)} vectors in collection '{collection_name}'")
            return point_ids
            
        except Exception as e:
            logger.error(f"Failed to store vectors in '{collection_name}': {str(e)}")
            raise RuntimeError(f"Vector storage failed: {str(e)}")
    
    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic vector search with optional metadata filtering.
        
        Args:
            collection_name: Target collection name
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters, format:
                {
                    'project_id': 'uuid',  # exact match
                    'document_type': ['requirements', 'specification'],  # any of
                    'chunk_type': 'text'  # exact match
                }
                
        Returns:
            List of search results with format:
                {
                    'id': 'point-id',
                    'score': 0.95,
                    'payload': {...metadata...}
                }
        """
        try:
            # Build Qdrant filter if metadata filters provided
            qdrant_filter = None
            if metadata_filter:
                conditions = []
                
                for key, value in metadata_filter.items():
                    if isinstance(value, list):
                        # Any of the values
                        for val in value:
                            conditions.append(
                                FieldCondition(key=key, match=MatchValue(value=val))
                            )
                    else:
                        # Exact match
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )
                
                if conditions:
                    qdrant_filter = Filter(should=conditions) if len(conditions) > 1 else Filter(must=[conditions[0]])
            
            # Perform search
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter
            )
            
            # Format results
            results = []
            for point in search_result:
                results.append({
                    'id': str(point.id),
                    'score': point.score,
                    'payload': point.payload or {}
                })
            
            logger.info(f"Found {len(results)} results in collection '{collection_name}' with threshold {score_threshold}")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed in '{collection_name}': {str(e)}")
            raise RuntimeError(f"Vector search failed: {str(e)}")
    
    def delete_vectors(self, collection_name: str, point_ids: List[str]) -> bool:
        """
        Delete vectors by point IDs.
        
        Args:
            collection_name: Target collection name
            point_ids: List of point IDs to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            if not point_ids:
                return True
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=rest.PointIdsList(
                    points=point_ids
                )
            )
            
            logger.info(f"Deleted {len(point_ids)} vectors from collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors from '{collection_name}': {str(e)}")
            return False
    
    def delete_by_filter(self, collection_name: str, metadata_filter: Dict[str, Any]) -> bool:
        """
        Delete vectors by metadata filter.
        
        Args:
            collection_name: Target collection name
            metadata_filter: Filter criteria for deletion
            
        Returns:
            True if deletion was successful
        """
        try:
            # Build filter conditions
            conditions = []
            for key, value in metadata_filter.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            
            if not conditions:
                logger.warning("No filter conditions provided for deletion")
                return False
            
            filter_obj = Filter(must=conditions)
            
            # Delete by filter
            self.client.delete(
                collection_name=collection_name,
                points_selector=rest.FilterSelector(filter=filter_obj)
            )
            
            logger.info(f"Deleted vectors from collection '{collection_name}' matching filter: {metadata_filter}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete by filter in '{collection_name}': {str(e)}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection information and statistics.
        
        Args:
            collection_name: Target collection name
            
        Returns:
            Collection info including vector count, config, etc.
        """
        try:
            # Get collection info
            info = self.client.get_collection(collection_name)
            
            return {
                'name': collection_name,
                'vectors_count': info.vectors_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'points_count': info.points_count,
                'segments_count': info.segments_count,
                'status': info.status.name if info.status else 'unknown',
                'optimizer_status': info.optimizer_status.ok if info.optimizer_status else True,
                'disk_data_size': getattr(info, 'disk_data_size', 0),
                'ram_data_size': getattr(info, 'ram_data_size', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info for '{collection_name}': {str(e)}")
            return None
    
    def list_collections(self) -> List[str]:
        """
        List all available collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
            
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Qdrant service health.
        
        Returns:
            Health status information
        """
        try:
            # Try to get collections as a health check
            collections = self.client.get_collections()
            
            return {
                'status': 'healthy',
                'collections_count': len(collections.collections),
                'collections': [col.name for col in collections.collections],
                'qdrant_available': True
            }
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'qdrant_available': False
            }

    async def search_similar_chunks(
        self,
        query_text: str,
        collection_name: str = "knowledge_chunks",
        limit: int = 10,
        score_threshold: float = 0.7,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar knowledge chunks using text query.
        
        This method handles embedding generation and vector search in one call.
        
        Args:
            query_text: The text query to search for
            collection_name: Target collection name
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters
            
        Returns:
            List of similar chunks with scores and metadata
        """
        try:
            # Generate embedding for query text
            from .embedding_service import get_embedding_service
            
            embedding_service = get_embedding_service()
            query_embeddings = embedding_service.generate_embeddings([query_text])
            
            if not query_embeddings:
                logger.error("Failed to generate embedding for query text")
                return []
            
            query_vector = query_embeddings[0]
            
            # Perform vector search
            results = self.search_vectors(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                metadata_filter=metadata_filter
            )
            
            logger.info(f"Found {len(results)} similar chunks for query: '{query_text[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Similar chunks search failed: {str(e)}")
            return []

# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_qdrant_service(settings: Settings = None) -> QdrantService:
    """Get configured Qdrant service instance."""
    return QdrantService(settings)

def ensure_knowledge_collections(qdrant_service: QdrantService) -> bool:
    """
    Ensure standard knowledge management collections exist.
    
    Args:
        qdrant_service: Configured Qdrant service
        
    Returns:
        True if all collections were created/verified
    """
    try:
        # Standard collections for knowledge management
        collections = [
            ('knowledge_chunks', 384),  # For sentence-transformer embeddings
            ('knowledge_large', 1536),  # For OpenAI/large model embeddings
        ]
        
        success = True
        for collection_name, vector_size in collections:
            if not qdrant_service.ensure_collection(collection_name, vector_size):
                success = False
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to ensure knowledge collections: {str(e)}")
        return False
