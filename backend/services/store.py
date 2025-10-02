# backend/services/store.py
"""
Dual-write wrapper functions for RAG SQL-first storage

These functions implement the dual-write pattern:
1. Store data in SQL (source of truth)
2. Mirror to vectors with IDs-only payloads

Vector payloads contain only metadata/IDs, never full text content.
Full text is retrieved from SQL using the chunk/message IDs.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.db.queries import insert_chunk, insert_chat, now_utc
from backend.services.embedding_service import EmbeddingService
from backend.services.qdrant_service import QdrantService
from backend.services.config import Settings

logger = logging.getLogger(__name__)


class RAGStoreService:
    """
    Service for dual-write RAG operations (SQL + vectors)

    Manages the SQL-first storage pattern where:
    - SQL contains the authoritative text content
    - Vectors contain only embeddings and ID references
    - Read-through pattern retrieves text from SQL using vector-found IDs
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.embedding_service = EmbeddingService(settings)
        self.qdrant_service = QdrantService(settings)

        # Default embedding model (matches ODRAS standard)
        self.default_embedding_model = "all-MiniLM-L6-v2"

        # Collection names (matches existing ODRAS collections)
        self.docs_collection = "knowledge_chunks"  # For document chunks
        self.threads_collection = "project_threads"  # For chat/project threads

        logger.info("RAG Store Service initialized with SQL-first storage")

    def store_chunk_and_vector(
        self,
        conn,
        project_id: str,
        doc_id: str,
        idx: int,
        text: str,
        version: int = 1,
        page: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        embedding_model: Optional[str] = None
    ) -> str:
        """
        Store document chunk in SQL and mirror to vectors with IDs-only payload.

        Args:
            conn: Database connection
            project_id: Project identifier
            doc_id: Document identifier
            idx: Chunk index within document
            text: Full text content (stored in SQL only)
            version: Document version
            page: Optional page number
            start: Optional start character position
            end: Optional end character position
            embedding_model: Override default embedding model

        Returns:
            str: Generated chunk_id
        """
        try:
            # Step 1: Store in SQL (source of truth)
            chunk_id = insert_chunk(conn, doc_id, idx, text, page, start, end)
            logger.debug(f"Stored chunk {chunk_id} in SQL")

            # Check if dual-write is enabled
            dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
            if not dual_write:
                logger.debug("Dual-write disabled, skipping vector storage")
                return chunk_id

            # Step 2: Generate embedding
            model = embedding_model or self.default_embedding_model
            embedding = self.embedding_service.generate_single_embedding(text, model)
            logger.debug(f"Generated embedding for chunk {chunk_id}")

            # Step 3: Store in vectors with IDs-only payload (NO text content)
            vector_data = [{
                "id": chunk_id,  # Use chunk_id as vector point ID
                "vector": embedding,
                "payload": {
                    "project_id": project_id,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "version": version,
                    "page": page,
                    "start_char": start,
                    "end_char": end,
                    "created_at": now_utc().isoformat(),
                    "embedding_model": model,
                    # CRITICAL: NO "text" field in payload - SQL is source of truth
                }
            }]

            stored_ids = self.qdrant_service.store_vectors(self.docs_collection, vector_data)
            logger.debug(f"Stored vector for chunk {chunk_id} in collection {self.docs_collection}")

            return chunk_id

        except Exception as e:
            logger.error(f"Failed to store chunk and vector: {e}")
            # Re-raise to let caller handle (SQL transaction should rollback)
            raise

    def store_message_and_vector(
        self,
        conn,
        project_id: str,
        session_id: str,
        role: str,
        content: str,
        embedding_model: Optional[str] = None
    ) -> str:
        """
        Store chat message in SQL and mirror to vectors with IDs-only payload.
        """
        try:
            print(f"🔍 DUAL_WRITE_DEBUG: Starting message storage")
            print(f"   Role: {role}")
            print(f"   Content length: {len(content)}")
            print(f"   Project ID: {project_id}")
            print(f"   Session ID: {session_id}")

            # Step 1: Store in SQL (source of truth)
            message_id = insert_chat(conn, session_id, project_id, role, content)
            print(f"✅ DUAL_WRITE_DEBUG: SQL storage complete - Message ID: {message_id[:8]}...")

            # Check if dual-write is enabled
            dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
            print(f"🔍 DUAL_WRITE_DEBUG: Dual-write enabled: {dual_write}")

            if not dual_write:
                print("⚠️ DUAL_WRITE_DEBUG: Dual-write disabled, skipping vector storage")
                return message_id

            # Step 2: Generate embedding
            model = embedding_model or self.default_embedding_model
            print(f"🔍 DUAL_WRITE_DEBUG: Generating embedding with model: {model}")

            embedding = self.embedding_service.generate_single_embedding(content, model)
            print(f"✅ DUAL_WRITE_DEBUG: Embedding generated - {len(embedding)} dimensions")

            # Step 3: Store in vectors with IDs-only payload (NO content)
            vector_data = [{
                "id": message_id,  # Use message_id as vector point ID
                "vector": embedding,
                "payload": {
                    "project_id": project_id,
                    "item_id": message_id,  # matches existing project_threads schema
                    "message_id": message_id,
                    "session_id": session_id,
                    "kind": "message",
                    "role": role,
                    "created_at": now_utc().isoformat(),
                    "embedding_model": model,
                    # CRITICAL: NO "content" field in payload - SQL is source of truth
                }
            }]

            print(f"🔍 DUAL_WRITE_DEBUG: Storing vector in collection: {self.threads_collection}")
            print(f"   Vector payload keys: {list(vector_data[0]['payload'].keys())}")

            stored_ids = self.qdrant_service.store_vectors(self.threads_collection, vector_data)
            print(f"✅ DUAL_WRITE_DEBUG: Vector storage complete - Stored IDs: {stored_ids}")

            return message_id

        except Exception as e:
            print(f"❌ DUAL_WRITE_DEBUG: Storage failed: {e}")
            logger.error(f"Failed to store message and vector: {e}")
            import traceback
            traceback.print_exc()
            # Re-raise to let caller handle (SQL transaction should rollback)
            raise

    def bulk_store_chunks_and_vectors(
        self,
        conn,
        project_id: str,
        doc_id: str,
        chunks_data: List[Dict[str, Any]],
        version: int = 1,
        embedding_model: Optional[str] = None
    ) -> List[str]:
        """
        Bulk store multiple chunks with their vectors.

        Args:
            conn: Database connection
            project_id: Project identifier
            doc_id: Document identifier
            chunks_data: List of chunk dictionaries with keys:
                - 'text': chunk text content
                - 'index': chunk sequence number
                - 'page': optional page number
                - 'start': optional start position
                - 'end': optional end position
            version: Document version
            embedding_model: Override default embedding model

        Returns:
            List[str]: Generated chunk_ids
        """
        try:
            chunk_ids = []

            # Step 1: Store all chunks in SQL first
            for chunk_data in chunks_data:
                chunk_id = insert_chunk(
                    conn,
                    doc_id,
                    chunk_data['index'],
                    chunk_data['text'],
                    chunk_data.get('page'),
                    chunk_data.get('start'),
                    chunk_data.get('end')
                )
                chunk_ids.append(chunk_id)

            logger.info(f"Stored {len(chunk_ids)} chunks in SQL for document {doc_id}")

            # Check if dual-write is enabled
            dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
            if not dual_write:
                logger.debug("Dual-write disabled, skipping vector storage")
                return chunk_ids

            # Step 2: Generate embeddings in batch
            texts = [chunk['text'] for chunk in chunks_data]
            model = embedding_model or self.default_embedding_model
            embeddings = self.embedding_service.generate_embeddings(texts, model)
            logger.info(f"Generated {len(embeddings)} embeddings for document {doc_id}")

            # Step 3: Prepare vector data with IDs-only payloads
            vectors_data = []
            for i, (chunk_data, chunk_id, embedding) in enumerate(zip(chunks_data, chunk_ids, embeddings)):
                vector_data = {
                    "id": chunk_id,
                    "vector": embedding,
                    "payload": {
                        "project_id": project_id,
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_data['index'],
                        "version": version,
                        "page": chunk_data.get('page'),
                        "start_char": chunk_data.get('start'),
                        "end_char": chunk_data.get('end'),
                        "created_at": now_utc().isoformat(),
                        "embedding_model": model,
                        "sql_first": True,  # Flag to indicate SQL-first storage
                        # CRITICAL: NO "text" field - SQL is source of truth
                    }
                }
                vectors_data.append(vector_data)

            # Step 4: Store vectors in batch
            stored_ids = self.qdrant_service.store_vectors(self.docs_collection, vectors_data)
            logger.info(f"Stored {len(stored_ids)} vectors for document {doc_id}")

            return chunk_ids

        except Exception as e:
            logger.error(f"Failed to bulk store chunks and vectors: {e}")
            raise

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the RAG store service configuration."""
        dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
        sql_read_through = getattr(self.settings, 'rag_sql_read_through', 'true').lower() == 'true'

        return {
            "service": "RAGStoreService",
            "sql_first_storage": True,
            "dual_write_enabled": dual_write,
            "sql_read_through_enabled": sql_read_through,
            "embedding_model": self.default_embedding_model,
            "collections": {
                "docs": self.docs_collection,
                "threads": self.threads_collection
            },
            "vector_payload_contains_content": False,  # This is the key difference!
            "text_source_of_truth": "PostgreSQL"
        }


# Factory function for easy instantiation
def create_rag_store_service(settings: Settings = None) -> RAGStoreService:
    """Create a configured RAG store service instance."""
    return RAGStoreService(settings)
