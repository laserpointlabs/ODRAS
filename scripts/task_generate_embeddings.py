#!/usr/bin/env python3
"""
External Task Script: Generate Embeddings for RAG Pipeline
Create vector embeddings for document chunks using configured embedding model.
"""

import json
import sys
import os
from typing import Dict, List, Any
import time

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.embedding_service import EmbeddingService


def generate_embeddings(
    chunks_data: List[Dict], embedding_model: str = None, batch_size: int = 10
) -> Dict[str, Any]:
    """
    Generate vector embeddings for document chunks.

    Args:
        chunks_data: List of document chunks with content
        embedding_model: Model to use for embeddings
        batch_size: Number of chunks to process in each batch

    Returns:
        Dict containing embeddings and generation statistics
    """
    embedding_result = {
        "embeddings_generated": [],
        "embedding_stats": {},
        "processing_status": "success",
        "errors": [],
    }

    start_time = time.time()

    try:
        if not chunks_data:
            embedding_result["processing_status"] = "failure"
            embedding_result["errors"].append("No chunks provided for embedding generation")
            return embedding_result

        settings = Settings()
        embedding_service = EmbeddingService(settings)

        # Extract text content from chunks
        texts = []
        chunk_metadata = []

        for i, chunk in enumerate(chunks_data):
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
                chunk_id = chunk.get("chunk_id", f"chunk_{i}")
                chunk_index = chunk.get("chunk_index", i)
            else:
                # Handle case where chunk is just text
                content = str(chunk)
                chunk_id = f"chunk_{i}"
                chunk_index = i

            texts.append(content)
            chunk_metadata.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "content_length": len(content),
                    "word_count": len(content.split()) if content else 0,
                }
            )

        # Generate embeddings in batches
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(texts), batch_size):
            batch_texts = texts[batch_idx : batch_idx + batch_size]
            batch_metadata = chunk_metadata[batch_idx : batch_idx + batch_size]

            try:
                # Generate embeddings for this batch
                batch_embeddings = embedding_service.create_embeddings(batch_texts)

                # Combine embeddings with metadata
                for i, embedding in enumerate(batch_embeddings):
                    metadata_idx = batch_idx + i
                    if metadata_idx < len(chunk_metadata):
                        embedding_record = {
                            "chunk_id": chunk_metadata[metadata_idx]["chunk_id"],
                            "chunk_index": chunk_metadata[metadata_idx]["chunk_index"],
                            "embedding": (
                                embedding.tolist() if hasattr(embedding, "tolist") else embedding
                            ),
                            "embedding_dimension": len(embedding),
                            "content_preview": (
                                texts[metadata_idx][:200] + "..."
                                if len(texts[metadata_idx]) > 200
                                else texts[metadata_idx]
                            ),
                            "content_length": chunk_metadata[metadata_idx]["content_length"],
                            "word_count": chunk_metadata[metadata_idx]["word_count"],
                            "batch_index": batch_idx // batch_size,
                        }
                        all_embeddings.append(embedding_record)

                print(
                    f"Generated embeddings for batch {(batch_idx // batch_size) + 1}/{total_batches}"
                )

            except Exception as e:
                embedding_result["errors"].append(
                    f"Failed to generate embeddings for batch {batch_idx // batch_size}: {str(e)}"
                )
                continue

        if not all_embeddings:
            embedding_result["processing_status"] = "failure"
            embedding_result["errors"].append("No embeddings were successfully generated")
            return embedding_result

        embedding_result["embeddings_generated"] = all_embeddings

        # Calculate statistics
        processing_time = time.time() - start_time
        total_embeddings = len(all_embeddings)
        embedding_dimensions = all_embeddings[0]["embedding_dimension"] if all_embeddings else 0
        total_text_length = sum(chunk["content_length"] for chunk in chunk_metadata)
        total_words = sum(chunk["word_count"] for chunk in chunk_metadata)

        embedding_result["embedding_stats"] = {
            "total_embeddings": total_embeddings,
            "embedding_dimension": embedding_dimensions,
            "processing_time_seconds": processing_time,
            "embeddings_per_second": (
                total_embeddings / processing_time if processing_time > 0 else 0
            ),
            "total_text_length": total_text_length,
            "total_words": total_words,
            "average_embedding_time": (
                processing_time / total_embeddings if total_embeddings > 0 else 0
            ),
            "batch_size_used": batch_size,
            "total_batches": total_batches,
            "failed_batches": len([e for e in embedding_result["errors"] if "batch" in e]),
            "model_used": embedding_model or settings.embedding_model or "default",
            "success_rate": ((total_embeddings / len(chunks_data)) * 100 if chunks_data else 0),
        }

        print(f"Successfully generated {total_embeddings} embeddings")
        print(f"Embedding dimension: {embedding_dimensions}")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Average time per embedding: {processing_time / total_embeddings:.3f} seconds")

    except Exception as e:
        embedding_result["processing_status"] = "failure"
        embedding_result["errors"].append(f"Embedding generation error: {str(e)}")
        print(f"Embedding generation failed: {str(e)}")

    return embedding_result


def validate_embeddings(embeddings: List[Dict]) -> Dict[str, Any]:
    """
    Validate generated embeddings for quality and consistency.

    Args:
        embeddings: List of embedding records

    Returns:
        Dict containing validation results
    """
    validation_result = {
        "validation_status": "success",
        "quality_metrics": {},
        "consistency_checks": {},
        "warnings": [],
    }

    try:
        if not embeddings:
            validation_result["validation_status"] = "failure"
            validation_result["warnings"].append("No embeddings to validate")
            return validation_result

        # Check dimension consistency
        dimensions = [len(emb["embedding"]) for emb in embeddings]
        unique_dimensions = set(dimensions)

        if len(unique_dimensions) > 1:
            validation_result["warnings"].append(
                f"Inconsistent embedding dimensions: {unique_dimensions}"
            )

        # Check for zero vectors
        zero_vectors = 0
        for emb in embeddings:
            if all(x == 0 for x in emb["embedding"]):
                zero_vectors += 1

        if zero_vectors > 0:
            validation_result["warnings"].append(
                f"Found {zero_vectors} zero vectors out of {len(embeddings)}"
            )

        # Quality metrics
        validation_result["quality_metrics"] = {
            "total_embeddings": len(embeddings),
            "consistent_dimensions": len(unique_dimensions) == 1,
            "common_dimension": max(dimensions) if dimensions else 0,
            "zero_vector_count": zero_vectors,
            "zero_vector_percentage": ((zero_vectors / len(embeddings)) * 100 if embeddings else 0),
        }

        # Consistency checks
        validation_result["consistency_checks"] = {
            "all_have_embeddings": all("embedding" in emb for emb in embeddings),
            "all_have_ids": all("chunk_id" in emb for emb in embeddings),
            "all_have_content_preview": all("content_preview" in emb for emb in embeddings),
            "dimension_consistency": len(unique_dimensions) == 1,
        }

    except Exception as e:
        validation_result["validation_status"] = "failure"
        validation_result["warnings"].append(f"Validation error: {str(e)}")

    return validation_result


def main():
    """Main function for testing."""
    if len(sys.argv) > 1:
        # Read chunks from file or use sample data
        if os.path.exists(sys.argv[1]):
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                chunks_data = json.load(f)
        else:
            # Create sample chunks from provided text
            text = sys.argv[1]
            chunks_data = [{"chunk_id": "chunk_0", "chunk_index": 0, "content": text}]

        embedding_model = sys.argv[2] if len(sys.argv) > 2 else None
        batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 10

        result = generate_embeddings(chunks_data, embedding_model, batch_size)

        # Validate the embeddings
        if result["processing_status"] == "success":
            validation = validate_embeddings(result["embeddings_generated"])
            result["validation_results"] = validation

        print(json.dumps(result, indent=2, default=str))
        return result

    return {
        "embeddings_generated": [{"chunk_id": "sample", "embedding": [0.1] * 384}],
        "embedding_stats": {"total_embeddings": 1, "embedding_dimension": 384},
        "processing_status": "success",
        "errors": [],
    }


if __name__ == "__main__":
    main()
