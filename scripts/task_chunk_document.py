#!/usr/bin/env python3
"""
External Task Script: Chunk Document for RAG Pipeline
This script is called by Camunda BPMN process to chunk parsed documents.

Input Variables (from Camunda):
- parsed_content: Extracted text content from document
- document_metadata: Document metadata from parsing step
- chunking_config: Configuration for chunking (chunk_size, overlap, etc.)

Output Variables (set in Camunda):
- chunks_created: List of document chunks with metadata
- chunking_stats: Statistics about the chunking process
"""

import json
import sys
import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings

# Try to import ChunkingService, create a fallback if not available
try:
    from services.chunking_service import ChunkingService

    HAS_CHUNKING_SERVICE = True
except ImportError:
    HAS_CHUNKING_SERVICE = False


def simple_chunk_text(text: str, chunk_size: int, overlap_size: int) -> List[str]:
    """
    Simple fallback text chunking function.

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk
        overlap_size: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the target boundary
            for i in range(max(0, end - 100), min(len(text), end + 100)):
                if text[i] in ".!?":
                    end = i + 1
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = max(start + 1, end - overlap_size)

        # Prevent infinite loop
        if start >= len(text):
            break

    return chunks


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""

    chunk_size: int = 1000  # Target chunk size in characters
    overlap_size: int = 200  # Overlap between chunks in characters
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 2000  # Maximum chunk size
    preserve_sentences: bool = True  # Try to preserve sentence boundaries
    preserve_paragraphs: bool = True  # Try to preserve paragraph boundaries


def chunk_document(
    content: str,
    metadata: Optional[Dict] = None,
    config: Optional[ChunkingConfig] = None,
) -> Dict[str, Any]:
    """
    Chunk document content for RAG pipeline processing.

    Args:
        content: Raw text content to chunk
        metadata: Document metadata
        config: Chunking configuration

    Returns:
        Dict containing chunks and statistics
    """
    if config is None:
        config = ChunkingConfig()

    if metadata is None:
        metadata = {}

    chunking_result = {
        "chunks_created": [],
        "chunking_stats": {},
        "processing_status": "success",
        "errors": [],
    }

    try:
        # Clean and prepare content
        cleaned_content = content.strip()
        if not cleaned_content:
            chunking_result["processing_status"] = "failure"
            chunking_result["errors"].append("No content to chunk")
            return chunking_result

        # Basic content preprocessing
        # Remove excessive whitespace while preserving structure
        cleaned_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned_content)  # Max 2 newlines
        cleaned_content = re.sub(r"[ \t]+", " ", cleaned_content)  # Normalize spaces

        # Split into chunks
        if HAS_CHUNKING_SERVICE:
            # Use the chunking service if available
            settings = Settings()
            chunking_service = ChunkingService(settings)
            chunks = chunking_service.chunk_text(
                text=cleaned_content,
                chunk_size=config.chunk_size,
                overlap_size=config.overlap_size,
            )
        else:
            # Simple fallback chunking
            chunks = simple_chunk_text(cleaned_content, config.chunk_size, config.overlap_size)

        # Process chunks and add metadata
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "chunk_id": f"chunk_{i:04d}",
                "chunk_index": i,
                "content": chunk,
                "char_count": len(chunk),
                "word_count": len(chunk.split()),
                "start_position": None,  # Would be calculated by chunking service
                "end_position": None,
                "chunk_metadata": {
                    "document_id": metadata.get("document_id"),
                    "source_filename": metadata.get("source_filename"),
                    "chunk_method": "sliding_window",
                    "chunk_size_config": config.chunk_size,
                    "overlap_config": config.overlap_size,
                    "preserve_sentences": config.preserve_sentences,
                    "preserve_paragraphs": config.preserve_paragraphs,
                },
            }

            # Calculate approximate positions
            if i == 0:
                chunk_data["start_position"] = 0
            else:
                # Estimate based on previous chunks with overlap
                prev_end = processed_chunks[i - 1]["end_position"]
                chunk_data["start_position"] = max(0, prev_end - config.overlap_size)

            chunk_data["end_position"] = chunk_data["start_position"] + len(chunk)

            # Quality checks for chunk
            quality_indicators = {
                "size_appropriate": config.min_chunk_size <= len(chunk) <= config.max_chunk_size,
                "has_complete_sentences": chunk.rstrip().endswith((".", "!", "?", ";")),
                "not_just_whitespace": chunk.strip() != "",
                "has_meaningful_content": len(re.sub(r"[\s\W]", "", chunk)) > 10,
            }

            chunk_data["quality_indicators"] = quality_indicators
            processed_chunks.append(chunk_data)

        # Calculate chunking statistics
        total_chars = sum(len(chunk["content"]) for chunk in processed_chunks)
        total_words = sum(chunk["word_count"] for chunk in processed_chunks)
        avg_chunk_size = total_chars / len(processed_chunks) if processed_chunks else 0

        chunking_stats = {
            "total_chunks": len(processed_chunks),
            "total_characters": total_chars,
            "total_words": total_words,
            "original_length": len(cleaned_content),
            "average_chunk_size": avg_chunk_size,
            "min_chunk_size": (
                min(len(chunk["content"]) for chunk in processed_chunks) if processed_chunks else 0
            ),
            "max_chunk_size": (
                max(len(chunk["content"]) for chunk in processed_chunks) if processed_chunks else 0
            ),
            "compression_ratio": (total_chars / len(cleaned_content) if cleaned_content else 0),
            "config_used": {
                "chunk_size": config.chunk_size,
                "overlap_size": config.overlap_size,
                "min_chunk_size": config.min_chunk_size,
                "max_chunk_size": config.max_chunk_size,
                "preserve_sentences": config.preserve_sentences,
                "preserve_paragraphs": config.preserve_paragraphs,
            },
        }

        chunking_result["chunks_created"] = processed_chunks
        chunking_result["chunking_stats"] = chunking_stats

        print(f"Document chunking successful")
        print(f"Created {len(processed_chunks)} chunks")
        print(f"Average chunk size: {avg_chunk_size:.0f} characters")
        print(f"Total content: {total_chars} characters")

    except Exception as e:
        chunking_result["processing_status"] = "failure"
        chunking_result["errors"].append(f"Chunking error: {str(e)}")
        print(f"Document chunking failed: {str(e)}")

    return chunking_result


def main():
    """
    Main function for Camunda external task execution.
    Reads process variables and returns chunking results.
    """
    # For testing, use command line arguments
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            # If argument is a file path, read the content
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                content = f.read()
        else:
            # If argument is direct content
            content = sys.argv[1]

        # Parse chunking configuration from command line
        config = ChunkingConfig()
        if len(sys.argv) > 2:
            config.chunk_size = int(sys.argv[2])
        if len(sys.argv) > 3:
            config.overlap_size = int(sys.argv[3])

        metadata = {"document_id": "test_doc", "source_filename": "test_document.txt"}

        result = chunk_document(content, metadata, config)
        print(json.dumps(result, indent=2, default=str))
        return result

    # In production, this would be called by Camunda with process variables
    return {
        "chunks_created": [{"chunk_id": "sample", "content": "Sample chunk"}],
        "chunking_stats": {"total_chunks": 1},
        "processing_status": "success",
        "errors": [],
    }


if __name__ == "__main__":
    main()
