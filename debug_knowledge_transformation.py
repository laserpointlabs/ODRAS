#!/usr/bin/env python3
"""
Debug the knowledge transformation pipeline to identify where it's failing
"""
import asyncio
import sys
import os
sys.path.append('/home/jdehart/working/ODRAS/backend')

from services.knowledge_transformation import get_knowledge_transformation_service
from services.config import Settings

async def debug_transformation():
    print("🔧 Debug Knowledge Transformation Pipeline")
    print("=" * 60)
    
    try:
        # Initialize the service
        print("📊 Step 1: Initialize transformation service...")
        service = get_knowledge_transformation_service(Settings())
        print("✅ Service initialized successfully")
        
        # Test with a known file ID from our earlier test
        print("\n📊 Step 2: Test file extraction...")
        # Let's get a file ID from the database first
        import psycopg2
        
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432, connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT id, filename FROM files ORDER BY created_at DESC LIMIT 1")
        result = cur.fetchone()
        
        if not result:
            print("❌ No files found in database")
            return
        
        file_id, filename = result
        print(f"✅ Using file: {filename} ({file_id})")
        cur.close()
        conn.close()
        
        # Test each step of the pipeline
        print(f"\n📊 Step 3: Test text extraction...")
        try:
            extracted_text, extraction_metadata = await service.extract_text_content(file_id)
            print(f"✅ Text extracted: {len(extracted_text)} characters")
            print(f"📄 Preview: {extracted_text[:100]}...")
        except Exception as e:
            print(f"❌ Text extraction failed: {e}")
            return
        
        print(f"\n📊 Step 4: Test chunking...")
        try:
            processing_config = {
                'chunking_strategy': 'hybrid',
                'chunk_size': 512,
                'chunk_overlap': 50,
                'document_type': 'unknown'
            }
            
            chunks = service.chunking_service.chunk_document(
                extracted_text,
                document_metadata=extraction_metadata,
                chunking_config=processing_config
            )
            print(f"✅ Chunking successful: {len(chunks)} chunks created")
            
            if chunks:
                print(f"📋 Sample chunk:")
                chunk = chunks[0]
                print(f"  • Sequence: {chunk.metadata.sequence_number}")
                print(f"  • Type: {chunk.metadata.chunk_type}")
                print(f"  • Content length: {len(chunk.content)}")
                print(f"  • Content preview: {chunk.content[:100]}...")
                
        except Exception as e:
            print(f"❌ Chunking failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print(f"\n📊 Step 5: Test database connection...")
        try:
            # Test if database services work
            conn = service.db_service._conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_assets")
            count = cur.fetchone()[0]
            print(f"✅ Database connection OK: {count} existing assets")
            cur.close()
            service.db_service._return(conn)
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return
        
        print(f"\n📊 Step 6: Test Qdrant connection...")
        try:
            collections = service.qdrant_service.list_collections()
            print(f"✅ Qdrant connection OK: {len(collections)} collections")
        except Exception as e:
            print(f"❌ Qdrant test failed: {e}")
            return
        
        print(f"\n🎉 All individual components working!")
        print(f"🔍 Now testing full transformation pipeline...")
        
        # Test full pipeline
        try:
            # Get a project ID 
            conn = psycopg2.connect(
                host="localhost", database="odras", user="postgres", 
                password="password", port=5432, connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT project_id FROM projects LIMIT 1")
            project_id = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            print(f"📁 Using project: {project_id}")
            
            asset_id = await service.transform_file_to_knowledge(
                file_id=file_id,
                project_id=project_id,
                processing_options=processing_config
            )
            print(f"🎉 FULL TRANSFORMATION SUCCESS!")
            print(f"✅ Knowledge asset created: {asset_id}")
            
        except Exception as e:
            print(f"❌ Full transformation failed: {e}")
            import traceback
            traceback.print_exc()
            return
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_transformation())
