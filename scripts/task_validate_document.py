#!/usr/bin/env python3
"""
External Task Script: Validate Document for RAG Pipeline
This script is called by Camunda BPMN process to validate uploaded documents.

Input Variables (from Camunda):
- document_content: Raw document bytes or file path
- document_filename: Original filename
- document_mime_type: MIME type of the document

Output Variables (set in Camunda):
- validation_result: 'success' or 'failure'
- validation_errors: List of validation error messages
- document_metadata: Extracted document metadata
"""

import json
import sys
import os
import hashlib
from typing import Dict, List, Any
from pathlib import Path

# Optional import for python-magic
try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings


def validate_document(document_path: str, filename: str, mime_type: str = None) -> Dict[str, Any]:
    """
    Validate document for RAG pipeline processing.

    Args:
        document_path: Path to the document file
        filename: Original filename
        mime_type: MIME type (optional, will be detected)

    Returns:
        Dict containing validation results and metadata
    """
    validation_result = {
        "validation_result": "success",
        "validation_errors": [],
        "document_metadata": {},
        "file_info": {},
    }

    try:
        # Check if file exists
        if not os.path.exists(document_path):
            validation_result["validation_result"] = "failure"
            validation_result["validation_errors"].append(f"File not found: {document_path}")
            return validation_result

        # Get file stats
        file_stats = os.stat(document_path)
        file_size = file_stats.st_size

        # Check file size (max 50MB for now)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            validation_result["validation_result"] = "failure"
            validation_result["validation_errors"].append(
                f"File too large: {file_size} bytes (max {max_size})"
            )
            return validation_result

        # Detect MIME type if not provided
        if not mime_type:
            if HAS_MAGIC:
                try:
                    mime_type = magic.from_file(document_path, mime=True)
                except Exception as e:
                    mime_type = None

            if not mime_type:
                # Fallback to extension-based detection
                ext = Path(filename).suffix.lower()
                mime_map = {
                    ".pdf": "application/pdf",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".doc": "application/msword",
                    ".txt": "text/plain",
                    ".md": "text/markdown",
                    ".rtf": "application/rtf",
                }
                mime_type = mime_map.get(ext, "application/octet-stream")

        # Check supported MIME types
        supported_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/plain",
            "text/markdown",
            "application/rtf",
        ]

        if mime_type not in supported_types:
            validation_result["validation_result"] = "failure"
            validation_result["validation_errors"].append(f"Unsupported file type: {mime_type}")
            return validation_result

        # Calculate file hash for deduplication
        with open(document_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Check for empty files
        if file_size == 0:
            validation_result["validation_result"] = "failure"
            validation_result["validation_errors"].append("File is empty")
            return validation_result

        # Basic content validation for text files
        if mime_type.startswith("text/"):
            try:
                with open(document_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if not content.strip():
                        validation_result["validation_result"] = "failure"
                        validation_result["validation_errors"].append(
                            "Text file contains no content"
                        )
                        return validation_result
            except UnicodeDecodeError:
                # Try with different encoding
                try:
                    with open(document_path, "r", encoding="latin1") as f:
                        content = f.read()
                        if not content.strip():
                            validation_result["validation_result"] = "failure"
                            validation_result["validation_errors"].append(
                                "Text file contains no readable content"
                            )
                            return validation_result
                except Exception as e:
                    validation_result["validation_result"] = "failure"
                    validation_result["validation_errors"].append(
                        f"Cannot read text file: {str(e)}"
                    )
                    return validation_result

        # Store file metadata
        validation_result["file_info"] = {
            "filename": filename,
            "file_path": document_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "file_hash": file_hash,
            "created_time": file_stats.st_ctime,
            "modified_time": file_stats.st_mtime,
        }

        # Store document metadata
        validation_result["document_metadata"] = {
            "source_filename": filename,
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "content_type": mime_type,
            "validation_timestamp": file_stats.st_mtime,
            "processing_status": "validated",
        }

        print(f"Document validation successful: {filename}")
        print(f"File size: {file_size} bytes")
        print(f"MIME type: {mime_type}")
        print(f"Hash: {file_hash}")

    except Exception as e:
        validation_result["validation_result"] = "failure"
        validation_result["validation_errors"].append(f"Validation error: {str(e)}")
        print(f"Document validation failed: {str(e)}")

    return validation_result


def main():
    """
    Main function for Camunda external task execution.
    Reads process variables and returns validation results.
    """
    # For testing, use command line arguments
    if len(sys.argv) > 1:
        document_path = sys.argv[1]
        filename = os.path.basename(document_path)
        mime_type = sys.argv[2] if len(sys.argv) > 2 else None

        result = validate_document(document_path, filename, mime_type)
        print(json.dumps(result, indent=2))
        return result

    # In production, this would be called by Camunda with process variables
    # For now, return a sample result
    return {
        "validation_result": "success",
        "validation_errors": [],
        "document_metadata": {"status": "validated"},
        "file_info": {"status": "processed"},
    }


if __name__ == "__main__":
    main()
