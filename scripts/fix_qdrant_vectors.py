#!/usr/bin/env python3
"""
Fix Qdrant vectors by repopulating from PostgreSQL chunks with correct embedding model

This script reads chunks from PostgreSQL and recreates vectors in Qdrant
using the all-mpnet-base-v2 model (768 dimensions) to match the collection.
"""

import asyncio
import sys
import os
import logging
from typing import List, Dict, Any

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from db import DatabaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_qdrant_vectors():
    """Repopulate Qdrant vectors from PostgreSQL chunks with correct embedding model"""

    # Initialize services
    settings = Settings()
    db_service = DatabaseService(settings)
    embedding_service = EmbeddingService(settings)
    qdrant_service = QdrantService(settings)

    collection_name = "knowledge_chunks"

    try:
        # Get all chunks from PostgreSQL
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT dc.chunk_id, dc.doc_id, dc.chunk_index, dc.text,
                           dc.page, dc.start_char, dc.end_char, d.project_id
                    FROM doc_chunk dc
                    JOIN doc d ON dc.doc_id = d.doc_id
                    ORDER BY dc.doc_id, dc.chunk_index
                """)

                chunks = cur.fetchall()
                logger.info(f"Found {len(chunks)} chunks in PostgreSQL")

                if not chunks:
                    logger.warning("No chunks found in PostgreSQL")
                    return

                # Generate embeddings using all-mpnet-base-v2 (768 dimensions)
                texts = [chunk[3] for chunk in chunks]  # chunk[3] is text
                logger.info(f"Generating embeddings for {len(texts)} chunks using all-mpnet-base-v2...")

                embeddings = embedding_service.generate_bulk_embeddings(
                    texts,
                    model="all-mpnet-base-v2"  # Use the correct model
                )

                logger.info(f"Generated {len(embeddings)} embeddings with {len(embeddings[0])} dimensions")

                # Prepare vector data
                vectors_data = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_id, doc_id, chunk_index, text, page, start_char, end_char, project_id = chunk

                    vector_data = {
                        "id": chunk_id,
                        "vector": embedding,
                        "payload": {
                            "project_id": project_id,
                            "doc_id": doc_id,
                            "chunk_id": chunk_id,
                            "chunk_index": chunk_index,
                            "version": 1,
                            "page": page,
                            "start_char": start_char,
                            "end_char": end_char,
                            "created_at": "2024-01-01T00:00:00Z",  # Placeholder
                            "embedding_model": "all-mpnet-base-v2",
                            "sql_first": True,
                            # CRITICAL: NO "text" field - SQL is source of truth
                        }
                    }
                    vectors_data.append(vector_data)

                # Store vectors in Qdrant
                logger.info(f"Storing {len(vectors_data)} vectors in Qdrant collection '{collection_name}'...")

                stored_ids = qdrant_service.store_vectors(collection_name, vectors_data)

                logger.info(f"Successfully stored {len(stored_ids)} vectors in Qdrant")

                # Verify storage
                collection_info = qdrant_service.get_collection_info(collection_name)
                logger.info(f"Qdrant collection '{collection_name}' now has {collection_info.get('points_count', 0)} points")

        finally:
            db_service._return(conn)

    except Exception as e:
        logger.error(f"Error fixing Qdrant vectors: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(fix_qdrant_vectors())

