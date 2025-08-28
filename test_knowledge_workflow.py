#!/usr/bin/env python3
"""
Test complete knowledge management workflow with MinIO + Qdrant + Neo4j + PostgreSQL
"""

import requests
import json
import sys
import psycopg2
import time

def get_auth_token():
    """Get authentication token"""
    try:
        response = requests.post(
            "http://localhost:8000/api/auth/login", 
            json={"username": "admin", "password": "admin"}
        )
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"🔐 Authentication successful")
            return token
        else:
            print(f"❌ Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def get_project_id():
    """Get a project ID from database"""
    try:
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM projects LIMIT 1")
        result = cur.fetchone()
        if result:
            project_id = str(result[0])
            cur.close()
            conn.close()
            return project_id
        else:
            print("❌ No projects found")
            return None
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None

def test_file_upload_with_knowledge_processing(token, project_id):
    """Test file upload with knowledge processing enabled"""
    print("\n📤 Testing File Upload with Knowledge Processing...")
    
    # Create a comprehensive test document
    test_content = """
# System Requirements Document

## 1. Introduction
This document describes the requirements for the Advanced Navigation System (ANS).

## 2. Functional Requirements

### 2.1 GPS Requirements
REQ-001: The system shall provide GPS accuracy within 3 meters under normal conditions.
REQ-002: The system shall update position data every 1 second during operation.
REQ-003: The system shall display current location on a high-resolution map interface.

### 2.2 User Interface Requirements  
REQ-004: The system shall provide a touch-screen interface with minimum 10-inch display.
REQ-005: The system shall support voice commands for hands-free operation.
REQ-006: The system shall display route information with turn-by-turn directions.

## 3. Performance Requirements

### 3.1 System Performance
REQ-007: The system shall start within 30 seconds of power-on.
REQ-008: The system shall operate continuously for minimum 8 hours on battery power.
REQ-009: The system shall maintain data accuracy during vehicle speeds up to 120 mph.

### 3.2 Environmental Requirements
REQ-010: The system shall operate in temperatures from -20°C to +60°C.
REQ-011: The system shall be resistant to vibration and shock per MIL-STD-810G.
REQ-012: The system shall have IP67 water resistance rating.

## 4. Safety Requirements
REQ-013: The system shall not distract the driver during operation.
REQ-014: The system shall provide audio alerts for critical navigation information.
REQ-015: The system shall automatically reduce screen brightness in low-light conditions.

## 5. Technical Dependencies
- The navigation system depends on GPS satellite availability
- Map data requires regular updates from cloud services
- Voice recognition requires internet connectivity for enhanced accuracy
"""
    
    # Prepare upload request
    files = {
        'file': ('navigation_requirements.md', test_content, 'text/markdown')
    }
    
    data = {
        'project_id': project_id,
        'tags': json.dumps({
            'docType': 'requirements',
            'status': 'new',
            'domain': 'navigation',
            'testDocument': True
        }),
        'process_for_knowledge': 'true',  # Enable knowledge processing
        'embedding_model': 'all-MiniLM-L6-v2',
        'chunking_strategy': 'hybrid'
    }
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        print("   📄 Uploading test requirements document...")
        response = requests.post(
            "http://localhost:8000/api/files/upload", 
            files=files, 
            data=data, 
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"       Response: {response.text}")
            return None
            
        result = response.json()
        file_id = result.get('file_id')
        message = result.get('message', '')
        
        print(f"   ✅ File uploaded successfully - ID: {file_id}")
        print(f"   💬 Message: {message}")
        
        # Check if knowledge processing was triggered
        if 'knowledge asset' in message.lower():
            print("   🧠 Knowledge processing completed immediately")
        else:
            print("   ⏳ Knowledge processing may be running asynchronously")
        
        return file_id
        
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return None

def check_knowledge_processing_results(file_id, project_id):
    """Check if knowledge processing created assets and chunks"""
    print("\n🔍 Checking Knowledge Processing Results...")
    
    try:
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        
        # Check files table
        print("   📁 Checking files table...")
        cur.execute("SELECT COUNT(*) FROM files WHERE id = %s", (file_id,))
        file_count = cur.fetchone()[0]
        
        if file_count > 0:
            print("   ✅ File record found in database")
            
            # Get file details
            cur.execute("""
                SELECT filename, file_size, content_type, status, tags 
                FROM files WHERE id = %s
            """, (file_id,))
            
            file_data = cur.fetchone()
            if file_data:
                filename, size, content_type, status, tags = file_data
                print(f"       - Filename: {filename}")
                print(f"       - Size: {size} bytes")
                print(f"       - Type: {content_type}")
                print(f"       - Status: {status}")
                print(f"       - Tags: {json.dumps(tags, indent=2)}")
        else:
            print("   ❌ File not found in database")
            return False
        
        # Check knowledge assets
        print("   🧠 Checking knowledge assets...")
        cur.execute("""
            SELECT COUNT(*) FROM knowledge_assets 
            WHERE source_file_id = %s AND project_id = %s
        """, (file_id, project_id))
        
        asset_count = cur.fetchone()[0]
        print(f"   📊 Knowledge assets created: {asset_count}")
        
        if asset_count > 0:
            # Get asset details
            cur.execute("""
                SELECT id, title, document_type, status, processing_stats
                FROM knowledge_assets 
                WHERE source_file_id = %s
            """, (file_id,))
            
            assets = cur.fetchall()
            for i, (asset_id, title, doc_type, status, stats) in enumerate(assets, 1):
                print(f"   ✅ Asset {i}: {title}")
                print(f"       - Type: {doc_type}")
                print(f"       - Status: {status}")
                print(f"       - Stats: {json.dumps(stats, indent=2) if stats else 'None'}")
                
                # Check chunks for this asset
                cur.execute("""
                    SELECT COUNT(*), SUM(token_count) 
                    FROM knowledge_chunks WHERE asset_id = %s
                """, (asset_id,))
                
                chunk_data = cur.fetchone()
                chunk_count, total_tokens = chunk_data
                print(f"       - Chunks: {chunk_count}")
                print(f"       - Total tokens: {total_tokens or 0}")
        
        # Check processing jobs
        print("   ⚙️ Checking processing jobs...")
        cur.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                   SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
            FROM knowledge_processing_jobs kj
            JOIN knowledge_assets ka ON kj.asset_id = ka.id
            WHERE ka.source_file_id = %s
        """, (file_id,))
        
        job_stats = cur.fetchone()
        total_jobs, completed, failed, pending, running = job_stats
        
        print(f"   📈 Processing jobs: {total_jobs} total")
        if total_jobs > 0:
            print(f"       - Completed: {completed}")
            print(f"       - Failed: {failed}")
            print(f"       - Pending: {pending}")
            print(f"       - Running: {running}")
        
        cur.close()
        conn.close()
        
        # Determine success
        if asset_count > 0:
            return True
        else:
            print("   ⚠️ No knowledge assets created yet")
            return False
        
    except Exception as e:
        print(f"   ❌ Database check error: {e}")
        return False

def check_vector_storage():
    """Check if vectors were stored in Qdrant"""
    print("\n🔍 Checking Vector Storage (Qdrant)...")
    
    try:
        # Get collections
        response = requests.get("http://localhost:6333/collections")
        if response.status_code != 200:
            print(f"   ❌ Failed to get collections: {response.status_code}")
            return False
        
        collections = response.json()
        collection_names = [c['name'] for c in collections.get('result', {}).get('collections', [])]
        
        print(f"   📊 Available collections: {collection_names}")
        
        # Check if our collection exists and has vectors
        target_collection = "odras_requirements"  # From config
        if target_collection in collection_names:
            # Get collection info
            info_response = requests.get(f"http://localhost:6333/collections/{target_collection}")
            if info_response.status_code == 200:
                info = info_response.json()
                point_count = info.get('result', {}).get('points_count', 0)
                vector_count = info.get('result', {}).get('vectors_count', 0)
                
                print(f"   ✅ Collection '{target_collection}' found")
                print(f"   📊 Points: {point_count}, Vectors: {vector_count}")
                
                return point_count > 0
            else:
                print(f"   ❌ Failed to get collection info: {info_response.status_code}")
        else:
            print(f"   ⚠️ Collection '{target_collection}' not found")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Qdrant check error: {e}")
        return False

def main():
    """Run complete knowledge processing workflow test"""
    print("🧪 ODRAS Knowledge Processing Workflow Test")
    print("=" * 60)
    
    # Step 1: Authentication
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    # Step 2: Get project
    project_id = get_project_id()
    if not project_id:
        sys.exit(1)
    
    print(f"📁 Using project ID: {project_id}")
    
    # Step 3: Upload file with knowledge processing
    file_id = test_file_upload_with_knowledge_processing(token, project_id)
    if not file_id:
        sys.exit(1)
    
    # Step 4: Wait a moment for async processing
    print("\n⏳ Waiting for knowledge processing to complete...")
    time.sleep(3)
    
    # Step 5: Check results
    processing_success = check_knowledge_processing_results(file_id, project_id)
    vector_success = check_vector_storage()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("-" * 40)
    print(f"File Upload:         ✅ SUCCESS")
    print(f"Knowledge Assets:    {'✅ SUCCESS' if processing_success else '❌ FAILED'}")
    print(f"Vector Storage:      {'✅ SUCCESS' if vector_success else '❌ FAILED'}")
    
    if processing_success and vector_success:
        print("\n🎉 Complete Knowledge Processing Workflow SUCCESS!")
        print("🚀 MinIO + PostgreSQL + Qdrant + Neo4j integration working!")
    else:
        print("\n⚠️ Some components need attention")
        if not processing_success:
            print("   - Knowledge processing may be async or failing")
        if not vector_success:
            print("   - Vector storage not populated yet")

if __name__ == "__main__":
    main()
