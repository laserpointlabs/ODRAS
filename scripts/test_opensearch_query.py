#!/usr/bin/env python3
"""Quick test to debug OpenSearch queries."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.config import Settings
from backend.rag.storage.text_search_factory import create_text_search_store

async def test_query():
    settings = Settings()
    settings.opensearch_enabled = 'true'
    
    store = create_text_search_store(settings)
    if not store:
        print("❌ OpenSearch not available")
        return
    
    # Ensure index exists
    await store.ensure_index("knowledge_chunks")
    
    # Index a test document
    test_doc = {
        "chunk_id": "test_req_1",
        "content": "REQ-SYS-042 requires altitude monitoring with ±5 meter accuracy.",
        "title": "Test Requirement",
        "project_id": "test_project",
    }
    
    print("📝 Indexing test document...")
    success = await store.index_document(
        index="knowledge_chunks",
        document_id="test_req_1",
        document=test_doc
    )
    print(f"   Index result: {success}")
    
    # Wait a moment for indexing
    await asyncio.sleep(1)
    
    # Test queries
    queries = ["REQ-SYS-042", "REQ", "altitude", "monitoring"]
    
    for query in queries:
        print(f"\n🔍 Testing query: '{query}'")
        results = await store.search(
            query_text=query,
            index="knowledge_chunks",
            limit=10
        )
        print(f"   Found {len(results)} results")
        for r in results:
            print(f"      - {r.get('id')}: score={r.get('score', 0):.2f}")
            print(f"        content: {r.get('payload', {}).get('content', '')[:60]}...")

if __name__ == "__main__":
    asyncio.run(test_query())


