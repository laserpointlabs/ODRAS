#!/usr/bin/env python3
"""
Debug MinIO metadata storage issue
"""
import asyncio
import sys
import os
sys.path.append('/home/jdehart/working/ODRAS/backend')

from services.file_storage import FileStorageService
from services.config import Settings

async def test_minio_metadata():
    """Test MinIO storage and metadata storage separately"""
    print("🔍 Debugging MinIO + PostgreSQL Metadata Storage")
    print("=" * 60)
    
    # Initialize with MinIO backend
    settings = Settings()
    print(f"📊 Storage Backend: {settings.storage_backend}")
    print(f"📊 MinIO Endpoint: {settings.minio_endpoint}")
    print(f"📊 MinIO Bucket: {settings.minio_bucket_name}")
    
    try:
        service = FileStorageService(settings)
        print(f"📊 Backend Type: {type(service.backend).__name__}")
        print(f"📊 Metadata Backend: {type(service.metadata_backend).__name__ if service.metadata_backend else 'None'}")
        
        # Test with a small file
        test_content = b"Test content for debugging MinIO metadata storage"
        test_filename = "debug_test.txt"
        
        print(f"\n📤 Testing file storage:")
        print(f"  • Content size: {len(test_content)} bytes")
        print(f"  • Filename: {test_filename}")
        
        # Get a valid project ID from database  
        import psycopg2
        try:
            conn = psycopg2.connect(
                host="localhost", database="odras", user="postgres", 
                password="password", port=5432, connect_timeout=3
            )
            cur = conn.cursor()
            cur.execute("SELECT project_id FROM projects LIMIT 1")
            project_result = cur.fetchone()
            project_id = project_result[0] if project_result else None
            cur.close()
            conn.close()
            print(f"📊 Using project ID: {project_id}")
        except Exception as e:
            print(f"⚠️  Could not get project ID: {e}")
            project_id = None
        
        # Try storing the file
        result = await service.store_file(
            content=test_content,
            filename=test_filename,
            content_type="text/plain",
            project_id=project_id,
            tags={"test": True}
        )
        
        print(f"\n📊 Storage Result:")
        print(f"  • Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"  • File ID: {result.get('file_id')}")
            print(f"  • Message: {result.get('message')}")
            
            # Try to retrieve metadata
            file_id = result.get('file_id')
            if file_id:
                metadata = await service.get_file_metadata(file_id)
                print(f"  • Metadata retrieval: {'✅ Success' if metadata else '❌ Failed'}")
                if metadata:
                    print(f"    - Filename: {metadata.get('filename')}")
                    print(f"    - Size: {metadata.get('file_size')}")
                    print(f"    - Backend: {metadata.get('storage_backend')}")
        else:
            print(f"  • Error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_minio_metadata())
