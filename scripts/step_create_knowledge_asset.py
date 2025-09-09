#!/usr/bin/env python3
"""
BPMN Step 4: Create Knowledge Asset

Focused script for creating knowledge asset records in PostgreSQL.
This script creates the database record and metadata.

Usage: python3 step_create_knowledge_asset.py <file_id> <project_id> <document_type>
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.knowledge_transformation import (
    get_knowledge_transformation_service,
)
from backend.services.file_storage import get_file_storage_service
from backend.services.config import Settings


async def create_knowledge_asset_record(
    file_id: str,
    project_id: str,
    document_type: str = "text",
    filename: str = "unknown_file",
):
    """Create knowledge asset record in database."""
    try:
        settings = Settings()

        # Get services
        knowledge_service = get_knowledge_transformation_service()
        file_storage = get_file_storage_service()

        print(f"📋 Step 4: Creating knowledge asset for file {file_id}")

        # Use filename parameter passed from BPMN workflow
        title = filename.rsplit(".", 1)[0] if "." in filename else filename  # Remove extension
        print(f"📄 Using filename from BPMN: {filename} → title: {title}")

        # Read chunks info from previous step
        embeddings_file = f"/tmp/odras_embeddings_{file_id}.json"
        chunk_count = 0
        total_content_length = 0

        if os.path.exists(embeddings_file):
            with open(embeddings_file, "r", encoding="utf-8") as f:
                embeddings_data = json.load(f)
            chunk_count = len(embeddings_data)
            total_content_length = sum(len(chunk.get("content", "")) for chunk in embeddings_data)

        # Create knowledge asset using service
        print(f"📊 Creating asset with: chunks={chunk_count}, length={total_content_length}")

        asset_id = await knowledge_service.create_knowledge_asset(
            source_file_id=file_id,
            project_id=project_id,
            title=title,
            document_type=document_type,
            processing_options={
                "source_filename": filename,
                "chunk_count": chunk_count,
                "total_content_length": total_content_length,
                "created_via": "bpmn_workflow",
                "processing_timestamp": datetime.utcnow().isoformat(),
            },
        )

        if not asset_id:
            raise ValueError("Knowledge asset creation returned no ID")

        # Store asset ID for next step
        asset_info_file = f"/tmp/odras_asset_{file_id}.json"
        asset_info = {
            "knowledge_asset_id": asset_id,
            "file_id": file_id,
            "project_id": project_id,
            "title": title,
            "document_type": document_type,
            "chunk_count": chunk_count,
        }

        with open(asset_info_file, "w", encoding="utf-8") as f:
            json.dump(asset_info, f, indent=2)

        # Prepare output
        result = {
            "success": True,
            "file_id": file_id,
            "project_id": project_id,
            "knowledge_asset_id": asset_id,
            "title": title,
            "document_type": document_type,
            "chunk_count": chunk_count,
            "asset_info_file": asset_info_file,
            "step": "knowledge_asset_creation",
            "step_status": "completed",
        }

        print(f"✅ Knowledge asset created: {asset_id}")
        print(f"📄 Title: {title}")
        print(f"📊 Chunks: {chunk_count}, Type: {document_type}")
        print("📋 BPMN_RESULT:", json.dumps(result))

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "file_id": file_id,
            "project_id": project_id,
            "error": str(e),
            "step": "knowledge_asset_creation",
            "step_status": "failed",
        }

        print(f"❌ Knowledge asset creation failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))

        sys.exit(1)


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 3:
        print(
            "Usage: python3 step_create_knowledge_asset.py <file_id> <project_id> [document_type] [filename]"
        )
        sys.exit(1)

    file_id = sys.argv[1]
    project_id = sys.argv[2]
    document_type = sys.argv[3] if len(sys.argv) > 3 else "text"
    filename = sys.argv[4] if len(sys.argv) > 4 else "unknown_file"

    # Run async asset creation
    asyncio.run(create_knowledge_asset_record(file_id, project_id, document_type, filename))


if __name__ == "__main__":
    main()
