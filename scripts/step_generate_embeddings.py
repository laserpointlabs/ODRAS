#!/usr/bin/env python3
"""
BPMN Step 3: Generate Vector Embeddings

Focused script for generating embeddings from document chunks.
This script reads chunks and creates vector representations.

Usage: python3 step_generate_embeddings.py <file_id> <embedding_model>
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.embedding_service import get_embedding_service
from backend.services.config import Settings


async def generate_chunk_embeddings(file_id: str, embedding_model: str = "all-MiniLM-L6-v2"):
    """Generate vector embeddings for document chunks."""
    try:
        settings = Settings()

        # Get embedding service
        embedding_service = get_embedding_service(settings)

        print(f"🧮 Step 3: Generating embeddings for file {file_id} using {embedding_model}")

        # Read chunks from previous step
        chunks_file = f"/tmp/odras_chunks_{file_id}.json"
        if not os.path.exists(chunks_file):
            raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        if not chunks_data:
            raise ValueError("No chunks available for embedding generation")

        print(f"📚 Processing {len(chunks_data)} chunks")

        # Generate embeddings for each chunk
        chunks_with_embeddings = []
        for i, chunk_data in enumerate(chunks_data):
            print(f"🔍 Processing chunk {i+1}/{len(chunks_data)}")

            # Generate embedding
            embedding = embedding_service.generate_single_embedding(
                text=chunk_data["content"], model_id=embedding_model
            )

            # Convert numpy array to list for JSON serialization
            if hasattr(embedding, "tolist"):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)

            # Add embedding to chunk data
            chunk_with_embedding = chunk_data.copy()
            chunk_with_embedding["embedding"] = embedding_list
            chunk_with_embedding["embedding_model"] = embedding_model
            chunk_with_embedding["embedding_dimensions"] = len(embedding_list)

            chunks_with_embeddings.append(chunk_with_embedding)

        # Store embeddings for next step
        embeddings_file = f"/tmp/odras_embeddings_{file_id}.json"
        with open(embeddings_file, "w", encoding="utf-8") as f:
            json.dump(chunks_with_embeddings, f, indent=2)

        # Prepare output
        result = {
            "success": True,
            "file_id": file_id,
            "embedding_model": embedding_model,
            "chunks_processed": len(chunks_with_embeddings),
            "embedding_dimensions": (
                len(chunks_with_embeddings[0]["embedding"]) if chunks_with_embeddings else 0
            ),
            "embeddings_file": embeddings_file,
            "step": "embedding_generation",
            "step_status": "completed",
        }

        print(f"✅ Embedding generation completed")
        print(f"📊 Model: {embedding_model}, Chunks: {len(chunks_with_embeddings)}")
        print(f"📏 Dimensions: {result['embedding_dimensions']}")
        print("📋 BPMN_RESULT:", json.dumps(result))

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "file_id": file_id,
            "error": str(e),
            "step": "embedding_generation",
            "step_status": "failed",
        }

        print(f"❌ Embedding generation failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))

        sys.exit(1)


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python3 step_generate_embeddings.py <file_id> [embedding_model]")
        sys.exit(1)

    file_id = sys.argv[1]
    embedding_model = sys.argv[2] if len(sys.argv) > 2 else "all-MiniLM-L6-v2"

    # Run async embedding generation
    asyncio.run(generate_chunk_embeddings(file_id, embedding_model))


if __name__ == "__main__":
    main()

