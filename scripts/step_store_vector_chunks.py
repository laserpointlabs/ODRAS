#!/usr/bin/env python3
"""
BPMN Step 5: Store Vector Chunks

Focused script for storing chunk embeddings in Qdrant vector database.
This script takes embeddings and makes them searchable via RAG.

Usage: python3 step_store_vector_chunks.py <file_id> <knowledge_asset_id>
"""

import sys
import os
import asyncio
import json
import uuid
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.qdrant_service import get_qdrant_service
from backend.services.config import Settings


async def store_vector_chunks_in_qdrant(file_id: str, knowledge_asset_id: str):
    """Store chunk embeddings in Qdrant vector database."""
    try:
        settings = Settings()

        # Get Qdrant service
        qdrant_service = get_qdrant_service(settings)

        print(f"🗂️ Step 5: Storing vector chunks for asset {knowledge_asset_id}")

        # Read embeddings from previous step
        embeddings_file = f"/tmp/odras_embeddings_{file_id}.json"
        if not os.path.exists(embeddings_file):
            raise FileNotFoundError(f"Embeddings file not found: {embeddings_file}")

        with open(embeddings_file, "r", encoding="utf-8") as f:
            embeddings_data = json.load(f)

        if not embeddings_data:
            raise ValueError("No embeddings available for storage")

        # Read asset info
        asset_info_file = f"/tmp/odras_asset_{file_id}.json"
        asset_info = {}
        if os.path.exists(asset_info_file):
            with open(asset_info_file, "r", encoding="utf-8") as f:
                asset_info = json.load(f)

        project_id = asset_info.get("project_id", "unknown")
        document_type = asset_info.get("document_type", "text")

        print(f"📚 Storing {len(embeddings_data)} chunks in Qdrant")

        # Store all chunks in Qdrant as batch
        collection_name = "knowledge_chunks"

        # Prepare vectors in Qdrant format
        vectors_to_store = []
        for chunk_data in embeddings_data:
            # Generate proper UUID for Qdrant point ID
            point_id = str(uuid.uuid4())

            vector_data = {
                "id": point_id,
                "vector": chunk_data["embedding"],
                "payload": {
                    "content": chunk_data["content"],
                    "asset_id": knowledge_asset_id,  # FIELD RAG SERVICE EXPECTS!
                    "source_asset": knowledge_asset_id,  # Keep for compatibility
                    "source_file": file_id,
                    "project_id": project_id,
                    "chunk_sequence": chunk_data["sequence_number"],
                    "document_type": document_type,
                    "embedding_model": chunk_data.get("embedding_model", "unknown"),
                    "metadata": chunk_data.get("metadata", {}),
                },
            }
            vectors_to_store.append(vector_data)

        # Store all vectors in Qdrant
        point_ids = qdrant_service.store_vectors(
            collection_name=collection_name, vectors=vectors_to_store
        )

        stored_count = len(point_ids)
        print(f"📊 Qdrant storage completed: {stored_count} chunks stored")

        # ALSO store chunks in PostgreSQL for UI content display
        print(f"📋 Storing chunks in PostgreSQL for content display...")

        from backend.services.knowledge_transformation import (
            get_knowledge_transformation_service,
        )

        knowledge_service = get_knowledge_transformation_service()
        conn = knowledge_service.db_service._conn()

        try:
            with conn.cursor() as cur:
                for i, chunk_data in enumerate(embeddings_data):
                    qdrant_point_id = point_ids[i] if i < len(point_ids) else str(uuid.uuid4())

                    # Insert chunk into PostgreSQL knowledge_chunks table
                    cur.execute(
                        """
                        INSERT INTO knowledge_chunks
                        (id, asset_id, sequence_number, chunk_type, content,
                         token_count, metadata, embedding_model, qdrant_point_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                        (
                            str(uuid.uuid4()),  # PostgreSQL chunk ID
                            knowledge_asset_id,  # Link to knowledge asset
                            chunk_data["sequence_number"],
                            "text",  # Default chunk type
                            chunk_data["content"],
                            chunk_data.get("metadata", {}).get(
                                "token_count", len(chunk_data["content"].split())
                            ),  # Use proper token count from chunking
                            json.dumps(chunk_data.get("metadata", {})),
                            chunk_data.get("embedding_model", "all-MiniLM-L6-v2"),
                            qdrant_point_id,  # Link to Qdrant point
                        ),
                    )

                conn.commit()
                print(
                    f"✅ PostgreSQL storage completed: {len(embeddings_data)} chunks stored for UI display"
                )

        except Exception as e:
            print(f"❌ PostgreSQL chunk storage failed: {str(e)}")
            # Don't fail the whole step if PostgreSQL fails
        finally:
            knowledge_service.db_service._return(conn)

        print(
            f"✅ Complete storage: Qdrant ({stored_count}) + PostgreSQL ({len(embeddings_data)}) chunks"
        )

        # Clean up temporary files
        temp_files = [
            f"/tmp/odras_text_{file_id}.txt",
            f"/tmp/odras_chunks_{file_id}.json",
            f"/tmp/odras_embeddings_{file_id}.json",
            f"/tmp/odras_asset_{file_id}.json",
        ]

        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        # Prepare output
        result = {
            "success": True,
            "file_id": file_id,
            "knowledge_asset_id": knowledge_asset_id,
            "stored_chunks": stored_count,
            "collection_name": collection_name,
            "project_id": project_id,
            "step": "vector_storage",
            "step_status": "completed",
            "cleanup_completed": True,
            "asset_status_updated": "active",  # Indicate final status update
        }

        print(f"✅ Vector storage completed: {stored_count} chunks stored")
        print(f"🗂️ Collection: {collection_name}")
        print(f"🧹 Temporary files cleaned up")
        print("📋 BPMN_RESULT:", json.dumps(result))

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "file_id": file_id,
            "knowledge_asset_id": knowledge_asset_id,
            "error": str(e),
            "step": "vector_storage",
            "step_status": "failed",
        }

        print(f"❌ Vector storage failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))

        sys.exit(1)


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 3:
        print("Usage: python3 step_store_vector_chunks.py <file_id> <knowledge_asset_id>")
        sys.exit(1)

    file_id = sys.argv[1]
    knowledge_asset_id = sys.argv[2] if len(sys.argv) > 2 else "auto-generated"

    # Run async vector storage
    asyncio.run(store_vector_chunks_in_qdrant(file_id, knowledge_asset_id))


if __name__ == "__main__":
    main()

