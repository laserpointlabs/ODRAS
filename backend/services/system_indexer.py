"""
System Indexer Service

Indexes all system entities (files, events, ontologies, requirements, conversations)
into a unified index for comprehensive search and context retrieval.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import Settings
from .db import DatabaseService
from .qdrant_service import get_qdrant_service
from .embedding_service import get_embedding_service
from .chunking_service import get_chunking_service
from .indexing_service_interface import IndexingServiceInterface

logger = logging.getLogger(__name__)


class SystemIndexer(IndexingServiceInterface):
    """
    Service for indexing system entities into unified index.
    
    Follows SQL-first pattern:
    - Stores full content in SQL (system_index_vectors table)
    - Stores only IDs and metadata in Qdrant vectors
    """
    
    def __init__(self, settings: Settings = None):
        """Initialize system indexer with dependencies."""
        self.settings = settings or Settings()
        self.db_service = DatabaseService(self.settings)
        self.qdrant_service = get_qdrant_service(self.settings)
        self.embedding_service = get_embedding_service(self.settings)
        self.chunking_service = get_chunking_service(self.settings)
        
        # Qdrant collection name for system index
        self.collection_name = "system_index"
        self.embedding_model = "all-MiniLM-L6-v2"  # Default model
        
        logger.info("System Indexer initialized")
    
    async def index_entity(
        self,
        entity_type: str,
        entity_id: str,
        content_summary: str,
        project_id: Optional[str] = None,
        entity_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> str:
        """
        Index a system entity.
        
        Args:
            entity_type: Type of entity (file, event, ontology, requirement, etc.)
            entity_id: Unique identifier for the entity
            content_summary: Summary/content to index
            project_id: Optional project ID
            entity_uri: Optional URI/IRI of the entity
            metadata: Optional additional metadata
            tags: Optional list of tags
            domain: Optional domain category
        
        Returns:
            Index ID (UUID string) of the created index entry
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Check if index entry already exists
                    cur.execute("""
                        SELECT index_id FROM system_index
                        WHERE entity_type = %s AND entity_id = %s
                    """, (entity_type, entity_id))
                    existing = cur.fetchone()
                    
                    if existing:
                        index_id = str(existing[0])
                        logger.info(f"Index entry already exists for {entity_type}:{entity_id}, updating")
                        # Update existing entry
                        await self.update_index(
                            index_id,
                            content_summary=content_summary,
                            metadata=metadata,
                            tags=tags
                        )
                        return index_id
                    
                    # Create new index entry
                    index_id = uuid4()
                    cur.execute("""
                        INSERT INTO system_index
                        (index_id, entity_type, entity_id, entity_uri, content_summary,
                         project_id, metadata, tags, domain, indexed_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        str(index_id),
                        entity_type,
                        entity_id,
                        entity_uri,
                        content_summary,
                        project_id,
                        json.dumps(metadata or {}),
                        tags or [],
                        domain,
                    ))
                    conn.commit()
                    
                    index_id_str = str(index_id)
                    logger.info(f"Created index entry {index_id_str} for {entity_type}:{entity_id}")
                    
                    # Index the content (chunk, embed, store vectors)
                    await self._index_content(index_id_str, content_summary, metadata or {})
                    
                    return str(index_id)
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to index entity {entity_type}:{entity_id}: {e}")
            raise
    
    async def _index_content(
        self,
        index_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Index content by chunking, embedding, and storing vectors."""
        try:
            # Chunk the content using fixed-size chunking (simpler, more reliable)
            chunks = self.chunking_service.chunk_fixed_size(
                text=content,
                chunk_size=512,
                overlap=50
            )
            
            if not chunks:
                logger.warning(f"No chunks created for index_id {index_id}")
                return
            
            # Ensure Qdrant collection exists
            model_info = self.embedding_service.get_model_info(self.embedding_model)
            if not model_info:
                raise ValueError(f"Unknown embedding model: {self.embedding_model}")
            
            vector_size = model_info["dimensions"]
            self.qdrant_service.ensure_collection(self.collection_name, vector_size)
            
            # Store chunks in SQL first (SQL-first pattern)
            conn = self.db_service._conn()
            try:
                vector_ids = []
                chunk_texts = []
                
                with conn.cursor() as cur:
                    for idx, chunk in enumerate(chunks):
                        # Extract text from DocumentChunk object
                        if hasattr(chunk, 'content'):
                            chunk_text = chunk.content
                            # Convert ChunkMetadata to dict if needed
                            chunk_metadata_obj = getattr(chunk, 'metadata', None)
                            if chunk_metadata_obj:
                                if hasattr(chunk_metadata_obj, '__dict__'):
                                    chunk_metadata = chunk_metadata_obj.__dict__
                                elif isinstance(chunk_metadata_obj, dict):
                                    chunk_metadata = chunk_metadata_obj
                                else:
                                    chunk_metadata = {}
                            else:
                                chunk_metadata = {}
                        elif hasattr(chunk, 'text'):
                            chunk_text = chunk.text
                            chunk_metadata = getattr(chunk, 'metadata', {})
                        elif isinstance(chunk, tuple):
                            chunk_text = chunk[0]
                            chunk_metadata = chunk[1] if len(chunk) > 1 else {}
                        else:
                            chunk_text = str(chunk)
                            chunk_metadata = {}
                        
                        # Generate vector ID
                        vector_id = uuid4()
                        
                        # Store chunk in SQL (source of truth)
                        cur.execute("""
                            INSERT INTO system_index_vectors
                            (vector_id, index_id, sequence_number, content, token_count,
                             metadata, embedding_model, qdrant_collection, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            str(vector_id),
                            index_id,
                            idx,
                            chunk_text,
                            len(chunk_text.split()),  # Approximate token count
                            json.dumps({**metadata, **chunk_metadata}),
                            self.embedding_model,
                            self.collection_name,
                        ))
                        
                        vector_ids.append(str(vector_id))
                        chunk_texts.append(chunk_text)
                    
                    conn.commit()
                    
            finally:
                self.db_service._return(conn)
            
            logger.info(f"Stored {len(vector_ids)} chunks in SQL for index_id {index_id}")
            
            # Generate embeddings
            embeddings = self.embedding_service.generate_embeddings(
                texts=chunk_texts,
                model_id=self.embedding_model,
                batch_size=16
            )
            
            # Store vectors in Qdrant with IDs-only payload (NO text content)
            vectors_data = []
            for idx, (vector_id, embedding) in enumerate(zip(vector_ids, embeddings)):
                # Get metadata from SQL
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT metadata FROM system_index_vectors WHERE vector_id = %s
                        """, (vector_id,))
                        row = cur.fetchone()
                        vector_metadata = row[0] if row and row[0] else {}
                finally:
                    self.db_service._return(conn)
                
                # Create payload WITHOUT text content - SQL is source of truth
                payload = {
                    "vector_id": vector_id,
                    "index_id": index_id,
                    "sequence_number": idx,
                    "embedding_model": self.embedding_model,
                    "sql_first": True,  # Flag to indicate SQL-first storage
                }
                
                # Add metadata fields if present
                if vector_metadata and isinstance(vector_metadata, dict):
                    payload.update({k: v for k, v in vector_metadata.items() if k not in payload})
                
                # CRITICAL: NO "text" or "content" field - SQL is source of truth
                
                vectors_data.append({
                    "id": vector_id,  # Use vector_id as Qdrant point ID
                    "vector": embedding,
                    "payload": payload,
                })
                
                # Update vector with Qdrant point ID reference
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE system_index_vectors
                            SET qdrant_point_id = %s
                            WHERE vector_id = %s
                        """, (str(vector_id), str(vector_id)))  # Same ID used for both
                        conn.commit()
                finally:
                    self.db_service._return(conn)
            
            # Store vectors in Qdrant
            self.qdrant_service.store_vectors(self.collection_name, vectors_data)
            logger.info(f"Stored {len(vectors_data)} vectors in Qdrant for index_id {index_id}")
            
        except Exception as e:
            logger.error(f"Failed to index content for index_id {index_id}: {e}")
            raise
    
    async def update_index(
        self,
        index_id: str,
        content_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Update an existing index entry."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Build update query dynamically
                    updates = []
                    params = []
                    
                    if content_summary is not None:
                        updates.append("content_summary = %s")
                        params.append(content_summary)
                    
                    if metadata is not None:
                        # Merge with existing metadata
                        cur.execute("SELECT metadata FROM system_index WHERE index_id = %s", (str(index_id),))
                        existing_row = cur.fetchone()
                        existing_metadata = existing_row[0] if existing_row and existing_row[0] else {}
                        merged_metadata = {**existing_metadata, **metadata}
                        updates.append("metadata = %s")
                        params.append(json.dumps(merged_metadata))
                    
                    if tags is not None:
                        updates.append("tags = %s")
                        params.append(tags)
                    
                    if updates:
                        updates.append("updated_at = NOW()")
                        params.append(str(index_id))
                        
                        cur.execute(f"""
                            UPDATE system_index
                            SET {', '.join(updates)}
                            WHERE index_id = %s
                        """, params)
                        conn.commit()
                        
                        logger.info(f"Updated index entry {index_id}")
                        
                        # Re-index content if summary changed
                        if content_summary is not None:
                            # Delete old vectors
                            await self._delete_vectors(index_id)
                            # Re-index
                            await self._index_content(index_id, content_summary, metadata or {})
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to update index {index_id}: {e}")
            raise
    
    async def _delete_vectors(self, index_id: str) -> None:
        """Delete all vectors for an index entry."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Get vector IDs and Qdrant point IDs
                    cur.execute("""
                        SELECT vector_id, qdrant_point_id FROM system_index_vectors
                        WHERE index_id = %s
                    """, (str(index_id),))
                    vectors = cur.fetchall()
                    
                    # Delete from Qdrant
                    if vectors:
                        point_ids = [str(row[1]) for row in vectors if row[1]]
                        if point_ids:
                            self.qdrant_service.delete_vectors(self.collection_name, point_ids)
                    
                    # Delete from SQL
                    cur.execute("DELETE FROM system_index_vectors WHERE index_id = %s", (str(index_id),))
                    conn.commit()
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to delete vectors for index_id {index_id}: {e}")
            raise
    
    async def delete_index(
        self,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """Delete an index entry by entity type and ID."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Get index_id
                    cur.execute("""
                        SELECT index_id FROM system_index
                        WHERE entity_type = %s AND entity_id = %s
                    """, (entity_type, entity_id))
                    row = cur.fetchone()
                    
                    if not row:
                        logger.warning(f"Index entry not found: {entity_type}:{entity_id}")
                        return
                    
                    index_id = str(row[0])
                    
                    # Delete vectors first
                    await self._delete_vectors(index_id)
                    
                    # Delete index entry
                    cur.execute("DELETE FROM system_index WHERE index_id = %s", (str(index_id),))
                    conn.commit()
                    
                    logger.info(f"Deleted index entry {index_id} for {entity_type}:{entity_id}")
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to delete index {entity_type}:{entity_id}: {e}")
            raise
    
    async def get_indexed_entities(
        self,
        entity_type: Optional[str] = None,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get indexed entities matching criteria."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Build query with filters
                    query = "SELECT * FROM system_index WHERE 1=1"
                    params = []
                    
                    if entity_type:
                        query += " AND entity_type = %s"
                        params.append(entity_type)
                    
                    if project_id:
                        query += " AND project_id = %s"
                        params.append(str(project_id))
                    
                    if domain:
                        query += " AND domain = %s"
                        params.append(domain)
                    
                    if tags:
                        # Entities must have all specified tags
                        for tag in tags:
                            query += " AND %s = ANY(tags)"
                            params.append(tag)
                    
                    query += " ORDER BY indexed_at DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    # Convert to dicts
                    columns = [desc[0] for desc in cur.description]
                    entities = []
                    for row in rows:
                        entity = dict(zip(columns, row))
                        # Parse JSONB fields
                        if entity.get("metadata") and isinstance(entity["metadata"], str):
                            try:
                                entity["metadata"] = json.loads(entity["metadata"])
                            except:
                                pass
                        entities.append(entity)
                    
                    return entities
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to get indexed entities: {e}")
            return []
