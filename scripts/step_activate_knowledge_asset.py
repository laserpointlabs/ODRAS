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

async def activate_knowledge_asset(knowledge_asset_id: str):
    """Activate knowledge asset by updating status to 'active'."""
    try:
        settings = Settings()
        
        print(f"🔄 Step 6: Activating knowledge asset {knowledge_asset_id}")
        
        # Get database connection using knowledge service approach
        from backend.services.knowledge_transformation import get_knowledge_transformation_service
        
        knowledge_service = get_knowledge_transformation_service()
        conn = knowledge_service.db_service._conn()
        
        try:
            with conn.cursor() as cur:
                # Update status to active and set updated timestamp
                cur.execute("""
                    UPDATE knowledge_assets 
                    SET status = 'active', updated_at = NOW()
                    WHERE id = %s AND status = 'processing'
                """, (knowledge_asset_id,))
                
                rows_updated = cur.rowcount
                conn.commit()
                
                if rows_updated > 0:
                    print(f"✅ Knowledge asset {knowledge_asset_id} activated successfully")
                    
                    # Get asset details for reporting
                    cur.execute("""
                        SELECT title, document_type, 
                               (metadata->>'chunk_count')::int as chunk_count,
                               (metadata->>'source_filename') as filename
                        FROM knowledge_assets 
                        WHERE id = %s
                    """, (knowledge_asset_id,))
                    
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
                        "step_status": "completed"
                    }
                    
                    if asset_row:
                        result.update({
                            "title": title,
                            "document_type": doc_type,
                            "chunk_count": chunk_count or 0,
                            "source_filename": source_filename
                        })
                    
                else:
                    # Asset not found or already active
                    cur.execute("SELECT status FROM knowledge_assets WHERE id = %s", (knowledge_asset_id,))
                    existing_status = cur.fetchone()
                    
                    if existing_status:
                        current_status = existing_status[0]
                        if current_status == 'active':
                            print(f"ℹ️ Knowledge asset {knowledge_asset_id} already active")
                            result = {
                                "success": True,
                                "knowledge_asset_id": knowledge_asset_id,
                                "status": "already_active",
                                "step": "asset_activation",
                                "step_status": "completed"
                            }
                        else:
                            print(f"⚠️ Knowledge asset {knowledge_asset_id} has status: {current_status}")
                            result = {
                                "success": True,
                                "knowledge_asset_id": knowledge_asset_id,
                                "status": f"already_{current_status}",
                                "step": "asset_activation",
                                "step_status": "completed"
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
            "step_status": "failed"
        }
        
        print(f"❌ Knowledge asset activation failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))
        
        sys.exit(1)

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python3 step_activate_knowledge_asset.py <knowledge_asset_id>")
        sys.exit(1)
    
    knowledge_asset_id = sys.argv[1]
    
    # Run async activation
    asyncio.run(activate_knowledge_asset(knowledge_asset_id))

if __name__ == "__main__":
    main()
