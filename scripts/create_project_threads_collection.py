#!/usr/bin/env python3
"""
Create Project Threads Collection in Qdrant

This script creates a dedicated collection for storing project thread conversations
and related vector embeddings in Qdrant.

Usage: python3 create_project_threads_collection.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.qdrant_service import get_qdrant_service
from backend.services.config import Settings


def create_project_threads_collection():
    """Create the project_threads collection in Qdrant."""
    try:
        print("🚀 Creating project_threads collection in Qdrant...")
        
        # Get settings and Qdrant service
        settings = Settings()
        qdrant_service = get_qdrant_service(settings)
        
        # Collection configuration
        collection_name = "project_threads"
        vector_size = 384  # Standard size for sentence-transformers
        distance_metric = "Cosine"  # Best for semantic similarity
        
        print(f"📋 Collection: {collection_name}")
        print(f"📏 Vector size: {vector_size}")
        print(f"📐 Distance metric: {distance_metric}")
        
        # Check if collection already exists
        existing_collections = qdrant_service.list_collections()
        if collection_name in existing_collections:
            print(f"⚠️  Collection '{collection_name}' already exists")
            
            # Get collection info
            collection_info = qdrant_service.get_collection_info(collection_name)
            if collection_info:
                print(f"📊 Collection info:")
                print(f"   - Points count: {collection_info.get('points_count', 'unknown')}")
                print(f"   - Vectors count: {collection_info.get('vectors_count', 'unknown')}")
                print(f"   - Status: {collection_info.get('status', 'unknown')}")
            
            # Ask user if they want to recreate
            response = input("Do you want to recreate the collection? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                print(f"🗑️  Deleting existing collection '{collection_name}'...")
                # Note: QdrantService doesn't have a delete_collection method, 
                # so we'll use the client directly
                qdrant_service.client.delete_collection(collection_name)
                print(f"✅ Collection '{collection_name}' deleted")
            else:
                print(f"✅ Using existing collection '{collection_name}'")
                return True
        
        # Create the collection
        print(f"🔨 Creating collection '{collection_name}'...")
        success = qdrant_service.ensure_collection(
            collection_name=collection_name,
            vector_size=vector_size,
            distance=distance_metric
        )
        
        if success:
            print(f"✅ Collection '{collection_name}' created successfully!")
            
            # Get and display collection info
            collection_info = qdrant_service.get_collection_info(collection_name)
            if collection_info:
                print(f"📊 Collection details:")
                print(f"   - Name: {collection_info.get('name', 'unknown')}")
                print(f"   - Points count: {collection_info.get('points_count', 0)}")
                print(f"   - Vectors count: {collection_info.get('vectors_count', 0)}")
                print(f"   - Status: {collection_info.get('status', 'unknown')}")
                print(f"   - Segments count: {collection_info.get('segments_count', 'unknown')}")
            
            # Display all collections
            print(f"\n📚 All available collections:")
            all_collections = qdrant_service.list_collections()
            for i, col_name in enumerate(all_collections, 1):
                print(f"   {i}. {col_name}")
            
            return True
        else:
            print(f"❌ Failed to create collection '{collection_name}'")
            return False
            
    except Exception as e:
        print(f"❌ Error creating collection: {str(e)}")
        return False


def main():
    """Main function for command line usage."""
    print("=" * 60)
    print("🔧 Qdrant Project Threads Collection Creator")
    print("=" * 60)
    
    success = create_project_threads_collection()
    
    if success:
        print("\n🎉 Collection creation completed successfully!")
        print("\n💡 The 'project_threads' collection is now ready for:")
        print("   - Storing conversation embeddings")
        print("   - Semantic search across project discussions")
        print("   - Thread-based knowledge retrieval")
        sys.exit(0)
    else:
        print("\n💥 Collection creation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
