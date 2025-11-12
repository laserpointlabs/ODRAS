"""
DAS Training Processor Service.

Processes training documents and stores them in global training collections.
Unlike project knowledge, training assets are global and not project-scoped.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

from .config import Settings
from .db import DatabaseService
from .file_storage import get_file_storage_service
from .qdrant_service import get_qdrant_service, QdrantService
from .embedding_service import get_embedding_service
from .chunking_service import get_chunking_service

logger = logging.getLogger(__name__)


class DASTrainingProcessor:
    """
    Service for processing training documents into global knowledge collections.
    
    Processes documents and stores chunks in Qdrant training collections
    without project_id metadata (global collections).
    """

    def __init__(self, settings: Settings = None):
        """Initialize training processor with all dependencies."""
        self.settings = settings or Settings()
        self.db_service = DatabaseService(self.settings)
        self.file_storage = get_file_storage_service()
        self.qdrant_service = get_qdrant_service(self.settings)
        self.embedding_service = get_embedding_service(self.settings)
        self.chunking_service = get_chunking_service(self.settings)

        logger.info("DAS Training Processor initialized")

    async def process_training_file(
        self,
        file_id: str,
        collection_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        source_type: str = "pdf",
        source_url: Optional[str] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a file and add it to a training collection.
        
        Args:
            file_id: Source file ID
            collection_id: Training collection ID
            title: Optional title (defaults to filename)
            description: Optional description
            source_type: Type of source (youtube_transcript, pdf, doc, etc.)
            source_url: Optional source URL
            processing_options: Optional processing configuration
            user_id: User ID who uploaded the file
            
        Returns:
            Dict with asset_id and processing status
        """
        try:
            # Get collection info
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT collection_name, embedding_model, vector_size
                        FROM das_training_collections
                        WHERE collection_id = %s AND is_active = TRUE
                        """,
                        (collection_id,)  # collection_id is already a string UUID
                    )
                    collection_row = cur.fetchone()
                    if not collection_row:
                        raise ValueError(f"Collection {collection_id} not found or inactive")
                    
                    collection_name, embedding_model, vector_size = collection_row
            finally:
                self.db_service._return(conn)

            # Get file info (file should already be in database from upload)
            # Use provided title or construct from file_id
            asset_title = title or f"Training Document {file_id[:8]}"

            # Create training asset record
            # Note: source_file_id can be NULL if file doesn't exist in files table yet
            asset_id = uuid4()
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Check if file exists in files table
                    cur.execute("SELECT id FROM files WHERE id = %s", (file_id,))
                    file_exists = cur.fetchone() is not None
                    
                    cur.execute(
                        """
                        INSERT INTO das_training_assets
                        (asset_id, collection_id, source_file_id, title, description,
                         source_type, source_url, created_by, processing_status, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING asset_id, created_at
                        """,
                        (
                            str(asset_id),  # Convert UUID to string for psycopg2
                            collection_id,  # Already a string UUID
                            file_id if file_exists else None,  # Only set if file exists
                            asset_title,
                            description,
                            source_type,
                            source_url,
                            str(user_id) if user_id else None,  # Convert to string if UUID
                            "processing",
                            json.dumps(processing_options or {}),
                        ),
                    )
                    conn.commit()
            finally:
                self.db_service._return(conn)

            # Process the file
            try:
                # Step 1: Extract text content
                logger.info(f"Extracting text from file {file_id}")
                extracted_text = await self._extract_text_content(file_id)
                
                if not extracted_text.strip():
                    raise ValueError("No text content could be extracted from file")

                # Step 2: Chunk the content
                logger.info(f"Chunking content for asset {asset_id}")
                chunking_config = {
                    "strategy": processing_options.get("chunking_strategy", "hybrid") if processing_options else "hybrid",
                    "chunk_size": processing_options.get("chunk_size", 512) if processing_options else 512,
                    "overlap": processing_options.get("chunk_overlap", 50) if processing_options else 50,
                }
                
                chunks = self.chunking_service.chunk_document(
                    extracted_text,
                    document_metadata={"source_file_id": file_id, "asset_id": str(asset_id)},
                    chunking_config=chunking_config,
                )

                if not chunks:
                    raise ValueError("No chunks could be generated from content")

                # Step 3: Store chunks in SQL first (SQL-first pattern)
                logger.info(f"Storing {len(chunks)} chunks in SQL database")
                chunk_ids = []
                chunk_texts = []
                
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        for idx, chunk in enumerate(chunks):
                            # Extract text from chunk
                            if hasattr(chunk, 'text'):
                                chunk_text = chunk.text
                                chunk_metadata_obj = getattr(chunk, 'metadata', {})
                            elif isinstance(chunk, tuple):
                                chunk_text = chunk[0]
                                chunk_metadata_obj = chunk[1] if len(chunk) > 1 else {}
                            else:
                                chunk_text = str(chunk)
                                chunk_metadata_obj = {}
                            
                            # Convert metadata to dict if it's an object
                            if hasattr(chunk_metadata_obj, '__dict__'):
                                chunk_metadata = chunk_metadata_obj.__dict__
                            elif isinstance(chunk_metadata_obj, dict):
                                chunk_metadata = chunk_metadata_obj
                            else:
                                chunk_metadata = {}
                            
                            # Store chunk in SQL (source of truth)
                            chunk_id = uuid4()
                            cur.execute(
                                """
                                INSERT INTO das_training_chunks
                                (chunk_id, asset_id, collection_id, sequence_number, content, 
                                 token_count, metadata, embedding_model, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                """,
                                (
                                    str(chunk_id),
                                    str(asset_id),
                                    collection_id,
                                    idx,
                                    chunk_text,
                                    len(chunk_text.split()),  # Approximate token count
                                    json.dumps(chunk_metadata),
                                    embedding_model,
                                ),
                            )
                            chunk_ids.append(str(chunk_id))
                            chunk_texts.append(chunk_text)
                        
                        conn.commit()
                finally:
                    self.db_service._return(conn)
                
                logger.info(f"Stored {len(chunk_ids)} chunks in SQL database")

                # Step 4: Generate embeddings
                logger.info(f"Generating embeddings for {len(chunks)} chunks using {embedding_model}")
                batch_size = processing_options.get("batch_size", 16) if processing_options else 16
                embeddings = self.embedding_service.generate_embeddings(
                    texts=chunk_texts,
                    model_id=embedding_model,
                    batch_size=batch_size
                )

                # Step 5: Store vectors in Qdrant with IDs-only payload (NO text content)
                logger.info(f"Storing {len(chunks)} vectors in Qdrant collection {collection_name}")
                vectors_data = []
                for idx, (chunk_id, embedding) in enumerate(zip(chunk_ids, embeddings)):
                    # Get metadata from SQL (already stored as JSONB)
                    chunk_metadata_dict = {}
                    try:
                        conn = self.db_service._conn()
                        try:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "SELECT metadata FROM das_training_chunks WHERE chunk_id = %s",
                                    (chunk_id,)
                                )
                                row = cur.fetchone()
                                if row and row[0]:
                                    # Metadata is already JSONB dict in database
                                    chunk_metadata_dict = row[0] if isinstance(row[0], dict) else {}
                        finally:
                            self.db_service._return(conn)
                    except Exception as e:
                        logger.warning(f"Could not retrieve metadata for chunk {chunk_id}: {e}")
                    
                    # Create payload WITHOUT text content - SQL is source of truth
                    # Payload contains only IDs and metadata
                    payload = {
                        "chunk_id": chunk_id,  # Reference to SQL chunk
                        "asset_id": str(asset_id),
                        "file_id": file_id,
                        "collection_id": collection_id,
                        "chunk_index": idx,
                        "source_type": "training",  # Mark as training knowledge (global)
                        "document_type": source_type,  # Original source type (pdf, text, etc.)
                        "title": asset_title,
                        "embedding_model": embedding_model,
                        "sql_first": True,  # Flag to indicate SQL-first storage
                    }
                    # Add metadata fields if present (but not as spread - add specific fields)
                    if chunk_metadata_dict:
                        # Only add safe metadata fields, not the whole dict
                        if isinstance(chunk_metadata_dict, dict):
                            payload.update({k: v for k, v in chunk_metadata_dict.items() if k not in payload})
                    # CRITICAL: NO "text" or "content" field - SQL is source of truth
                    
                    # Use chunk_id as Qdrant point ID (UUID format)
                    vectors_data.append({
                        "id": chunk_id,  # Use SQL chunk_id as vector point ID
                        "vector": embedding,
                        "payload": payload,
                    })
                    
                    # Update chunk with Qdrant point ID reference
                    conn = self.db_service._conn()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE das_training_chunks
                                SET qdrant_point_id = %s
                                WHERE chunk_id = %s
                                """,
                                (chunk_id, chunk_id),  # Same ID used for both
                            )
                            conn.commit()
                    finally:
                        self.db_service._return(conn)

                # Store vectors in Qdrant
                self.qdrant_service.store_vectors(collection_name, vectors_data)
                logger.info(f"Stored {len(vectors_data)} vectors in Qdrant")

                # Update asset with chunk count and completed status
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE das_training_assets
                            SET chunk_count = %s, processing_status = 'completed'
                            WHERE asset_id = %s
                            """,
                            (len(chunks), str(asset_id)),  # Convert UUID to string
                        )
                        conn.commit()
                finally:
                    self.db_service._return(conn)

                logger.info(f"Successfully processed training asset {asset_id} with {len(chunks)} chunks")
                
                return {
                    "success": True,
                    "asset_id": str(asset_id),
                    "chunk_count": len(chunks),
                    "collection_name": collection_name,
                }

            except Exception as e:
                # Update asset status to failed
                logger.error(f"Failed to process training asset {asset_id}: {e}")
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE das_training_assets
                            SET processing_status = 'failed', metadata = jsonb_set(metadata, '{error}', %s::jsonb)
                            WHERE asset_id = %s
                            """,
                            (json.dumps(str(e)), str(asset_id)),  # Convert UUID to string
                        )
                        conn.commit()
                finally:
                    self.db_service._return(conn)
                
                raise

        except Exception as e:
            logger.error(f"Failed to process training file {file_id}: {e}")
            raise

    async def _extract_text_content(self, file_id: str) -> str:
        """
        Extract text content from a file.
        
        Args:
            file_id: File ID
            
        Returns:
            Extracted text content
        """
        try:
            # Get file content using retrieve_file method
            file_result = await self.file_storage.retrieve_file(file_id)
            if not file_result:
                raise ValueError(f"Could not retrieve content for file {file_id}")
            
            # Extract content from result dict
            file_content = file_result.get("content") if isinstance(file_result, dict) else file_result
            if not file_content:
                raise ValueError(f"File {file_id} has no content")

            # Try to decode as text
            if isinstance(file_content, bytes):
                try:
                    text = file_content.decode("utf-8", errors="ignore")
                except Exception:
                    text = file_content.decode("latin-1", errors="ignore")
            else:
                text = str(file_content)

            # For now, return raw text
            # TODO: Add proper document parsing (PDF, DOCX, etc.) using existing extraction service
            return text

        except Exception as e:
            logger.error(f"Failed to extract text from file {file_id}: {e}")
            raise ValueError(f"Text extraction failed: {str(e)}")
