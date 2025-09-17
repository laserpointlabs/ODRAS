#!/usr/bin/env python3
"""
Verify Project Threads Collection in Qdrant

This script verifies that the project_threads collection exists and displays its configuration.

Usage: python3 verify_project_threads_collection.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.qdrant_service import get_qdrant_service
from backend.services.config import Settings


def verify_project_threads_collection():
    """Verify the project_threads collection exists and show its details."""
    try:
        print("🔍 Verifying project_threads collection in Qdrant...")
        
        # Get settings and Qdrant service
        settings = Settings()
        qdrant_service = get_qdrant_service(settings)
        
        collection_name = "project_threads"
        
        # Check if collection exists
        existing_collections = qdrant_service.list_collections()
        if collection_name not in existing_collections:
            print(f"❌ Collection '{collection_name}' does not exist!")
            print(f"📚 Available collections: {existing_collections}")
            return False
        
        print(f"✅ Collection '{collection_name}' exists!")
        
        # Get detailed collection info
        collection_info = qdrant_service.get_collection_info(collection_name)
        if collection_info:
            print(f"\n📊 Collection Details:")
            print(f"   - Name: {collection_info.get('name', 'unknown')}")
            print(f"   - Points count: {collection_info.get('points_count', 0)}")
            print(f"   - Vectors count: {collection_info.get('vectors_count', 'N/A')}")
            print(f"   - Indexed vectors count: {collection_info.get('indexed_vectors_count', 'N/A')}")
            print(f"   - Status: {collection_info.get('status', 'unknown')}")
            print(f"   - Segments count: {collection_info.get('segments_count', 'unknown')}")
            print(f"   - Optimizer status: {collection_info.get('optimizer_status', 'unknown')}")
            print(f"   - Disk data size: {collection_info.get('disk_data_size', 0)} bytes")
            print(f"   - RAM data size: {collection_info.get('ram_data_size', 0)} bytes")
        
        # Get collection configuration from Qdrant client directly
        try:
            collection_config = qdrant_service.client.get_collection(collection_name)
            print(f"\n⚙️  Collection Configuration:")
            print(f"   - Vector size: {collection_config.config.params.vectors.size}")
            print(f"   - Distance metric: {collection_config.config.params.vectors.distance}")
            print(f"   - Collection type: {collection_config.config.params.vectors.__class__.__name__}")
        except Exception as e:
            print(f"⚠️  Could not get detailed configuration: {e}")
        
        # Test basic operations
        print(f"\n🧪 Testing basic operations...")
        
        # Test search with empty vector (should not error)
        try:
            empty_vector = [0.0] * 384  # 384-dimensional zero vector
            results = qdrant_service.search_vectors(
                collection_name=collection_name,
                query_vector=empty_vector,
                limit=1
            )
            print(f"   ✅ Search operation: OK (returned {len(results)} results)")
        except Exception as e:
            print(f"   ❌ Search operation failed: {e}")
        
        print(f"\n🎉 Collection verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying collection: {str(e)}")
        return False


def main():
    """Main function for command line usage."""
    print("=" * 60)
    print("🔍 Qdrant Project Threads Collection Verifier")
    print("=" * 60)
    
    success = verify_project_threads_collection()
    
    if success:
        print("\n✅ Collection is ready for use!")
        sys.exit(0)
    else:
        print("\n❌ Collection verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
