#!/usr/bin/env python3
"""
BPMN Step 6: Activate Knowledge Asset

Final step that updates knowledge asset status from 'processing' to 'active'.
This makes the asset visible in the UI and available for RAG queries.

Usage: python3 step_activate_knowledge_asset.py <knowledge_asset_id>
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

from backend.services.config import Settings


async def activate_knowledge_asset(knowledge_asset_id: str, processing_data: dict = None):
    """Activate knowledge asset by updating status to 'active'."""
    try:
        settings = Settings()

        print(f"🔄 Step 6: Activating knowledge asset {knowledge_asset_id}")
        if processing_data:
            print(f"📊 Processing stats: {processing_data}")

        # Get database connection using knowledge service approach
        from backend.services.knowledge_transformation import (
            get_knowledge_transformation_service,
        )

        knowledge_service = get_knowledge_transformation_service()
        conn = knowledge_service.db_service._conn()

        try:
            with conn.cursor() as cur:
                # Get current asset data to extract correct processing stats
                cur.execute(
                    """
                    SELECT metadata, title, document_type
                    FROM knowledge_assets 
                    WHERE id = %s
                """,
                    (knowledge_asset_id,),
                )

                asset_data = cur.fetchone()
                if not asset_data:
                    raise ValueError(f"Knowledge asset {knowledge_asset_id} not found")

                current_metadata, title, doc_type = asset_data

                # Calculate total tokens from chunks (what the UI needs!)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(token_count), 0) as total_tokens,
                           COUNT(*) as actual_chunks
                    FROM knowledge_chunks 
                    WHERE asset_id = %s
                """,
                    (knowledge_asset_id,),
                )

                token_data = cur.fetchone()
                total_tokens = token_data[0] if token_data else 0
                actual_chunks = token_data[1] if token_data else 0

                print(
                    f"📊 Calculated from chunks: {actual_chunks} chunks, {total_tokens} total tokens"
                )

                # Extract correct stats from metadata (where they're properly stored)
                processing_stats = {
                    "chunk_count": current_metadata.get("chunk_count", actual_chunks),
                    "token_count": total_tokens,  # CORRECT FIELD NAME FOR UI!
                    "text_length": current_metadata.get("total_content_length", 0),
                    "embedding_model": "all-MiniLM-L6-v2",  # From workflow
                    "chunking_strategy": "hybrid",  # From workflow
                    "embedding_dimensions": 384,  # Standard for all-MiniLM-L6-v2
                    "processing_method": "bpmn_workflow",
                    "workflow_completed": True,
                    "source_filename": current_metadata.get("source_filename", "unknown"),
                    "created_via": current_metadata.get("created_via", "bpmn_workflow"),
                }

                print(
                    f"📊 Processing stats from metadata: chunk_count={processing_stats['chunk_count']}"
                )

                # Update status and copy correct stats to processing_stats field
                cur.execute(
                    """
                    UPDATE knowledge_assets 
                    SET status = 'active', 
                        updated_at = NOW(),
                        processing_stats = %s
                    WHERE id = %s
                """,
                    (json.dumps(processing_stats), knowledge_asset_id),
                )

                rows_updated = cur.rowcount
                conn.commit()

                if rows_updated > 0:
                    print(f"✅ Knowledge asset {knowledge_asset_id} activated successfully")

                    # Get asset details for reporting
                    cur.execute(
                        """
                        SELECT title, document_type, 
                               (metadata->>'chunk_count')::int as chunk_count,
                               (metadata->>'source_filename') as filename
                        FROM knowledge_assets 
                        WHERE id = %s
                    """,
                        (knowledge_asset_id,),
                    )

                    asset_row = cur.fetchone()
                    if asset_row:
                        title, doc_type, chunk_count, source_filename = asset_row
                        print(f"📋 Asset details: {title} ({doc_type}) - {chunk_count} chunks")

                    result = {
                        "success": True,
                        "knowledge_asset_id": knowledge_asset_id,
                        "status": "active",
                        "rows_updated": rows_updated,
                        "step": "asset_activation",
                        "step_status": "completed",
                    }

                    if asset_row:
                        result.update(
                            {
                                "title": title,
                                "document_type": doc_type,
                                "chunk_count": chunk_count or 0,
                                "source_filename": source_filename,
                            }
                        )

                else:
                    # Asset not found or already active
                    cur.execute(
                        "SELECT status FROM knowledge_assets WHERE id = %s",
                        (knowledge_asset_id,),
                    )
                    existing_status = cur.fetchone()

                    if existing_status:
                        current_status = existing_status[0]
                        if current_status == "active":
                            print(f"ℹ️ Knowledge asset {knowledge_asset_id} already active")
                            result = {
                                "success": True,
                                "knowledge_asset_id": knowledge_asset_id,
                                "status": "already_active",
                                "step": "asset_activation",
                                "step_status": "completed",
                            }
                        else:
                            print(
                                f"⚠️ Knowledge asset {knowledge_asset_id} has status: {current_status}"
                            )
                            result = {
                                "success": True,
                                "knowledge_asset_id": knowledge_asset_id,
                                "status": f"already_{current_status}",
                                "step": "asset_activation",
                                "step_status": "completed",
                            }
                    else:
                        raise ValueError(f"Knowledge asset {knowledge_asset_id} not found")

        finally:
            knowledge_service.db_service._return(conn)

        print("✅ Knowledge asset activation completed")
        print("📋 BPMN_RESULT:", json.dumps(result))

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "knowledge_asset_id": knowledge_asset_id,
            "error": str(e),
            "step": "asset_activation",
            "step_status": "failed",
        }

        print(f"❌ Knowledge asset activation failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))

        sys.exit(1)


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print(
            "Usage: python3 step_activate_knowledge_asset.py <knowledge_asset_id> [processing_data_json]"
        )
        sys.exit(1)

    knowledge_asset_id = sys.argv[1]
    processing_data = None

    # Parse processing data if provided
    if len(sys.argv) > 2:
        try:
            processing_data = json.loads(sys.argv[2])
            print(f"📊 Received processing data: {len(processing_data)} fields")
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse processing data: {e}")
            processing_data = None

    # Run async activation
    asyncio.run(activate_knowledge_asset(knowledge_asset_id, processing_data))


if __name__ == "__main__":
    main()
