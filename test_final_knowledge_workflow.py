#!/usr/bin/env python3
"""
Final test for complete knowledge processing workflow with embeddings
"""

import requests
import json
import sys
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
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM projects LIMIT 1")
        result = cur.fetchone()
        if result:
            project_id = str(result[0])
            print(f"📁 Using project ID: {project_id}")
            cur.close()
            conn.close()
            return project_id
        else:
            print("❌ No projects found")
            return None
    except Exception as e:
        print(f"❌ Project ID error: {e}")
        return None

def test_complete_workflow():
    """Test the complete knowledge processing workflow"""
    print("🧪 ODRAS Complete Knowledge Processing Test")
    print("=" * 60)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        return False
        
    # Get project ID  
    project_id = get_project_id()
    if not project_id:
        return False
    
    print(f"\n📤 Testing File Upload with Knowledge Processing...")
    
    # Create test content
    test_content = """
# Navigation System Requirements v3.0

## 1. GPS Navigation Requirements

### REQ-001: GPS Accuracy
The GPS navigation system SHALL provide location accuracy within ±3 meters under clear sky conditions.

**Rationale**: Required for safe navigation in urban environments.
**Test**: Measured accuracy in open field conditions.

### REQ-002: Position Update Rate  
The system SHALL update position data at minimum 1 Hz frequency.

**Rationale**: Ensures smooth navigation experience.
**Test**: Verify update frequency under normal operation.

### REQ-003: Map Display
The system SHALL display current position on digital map within 2 seconds of startup.

**Rationale**: Quick orientation for user safety.
**Test**: Measure map display time from power-on.

## 2. Performance Requirements

### REQ-004: System Response
Navigation commands SHALL execute within 500ms of user input.

### REQ-005: Memory Usage
System SHALL operate within 512MB RAM limit.

## 3. Safety Requirements

### REQ-006: Fail-Safe Operation
If GPS signal is lost, system SHALL alert user within 10 seconds.

### REQ-007: Data Integrity
Position data SHALL be validated before display to user.
"""
    
    # Upload file with knowledge processing enabled
    files = {'file': ('navigation_requirements_v3.md', test_content, 'text/markdown')}
    data = {
        'project_id': project_id,
        'tags': json.dumps({
            'docType': 'requirements',
            'status': 'new', 
            'domain': 'navigation',
            'testDocument': True
        }),
        'process_for_knowledge': 'true'  # Enable knowledge processing
    }
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        print("   📄 Uploading test requirements document with knowledge processing...")
        response = requests.post(
            "http://localhost:8000/api/files/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            file_id = result.get('file_id')
            print(f"   ✅ File uploaded successfully - ID: {file_id}")
            print(f"   💬 Message: {result.get('message', 'No message')}")
            
            # Check if knowledge processing was triggered
            if 'knowledge' in result.get('message', '').lower():
                print("   🧠 Knowledge processing triggered!")
            else:
                print("   ⚠️ Knowledge processing status unclear")
                
            return file_id
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error details: {error}")
            except:
                print(f"   Raw error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Upload exception: {e}")
        return None

def check_processing_results(file_id, project_id):
    """Check the results of knowledge processing"""
    print(f"\n🔍 Checking Knowledge Processing Results...")
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        
        # Check file record
        print("   📁 Checking files table...")
        cur.execute("SELECT filename, file_size, content_type, tags FROM files WHERE id = %s", (file_id,))
        file_record = cur.fetchone()
        if file_record:
            print("   ✅ File record found in database")
            print(f"       - Filename: {file_record[0]}")
            print(f"       - Size: {file_record[1]} bytes")
            print(f"       - Type: {file_record[2]}")
            print(f"       - Tags: {json.dumps(file_record[3], indent=2) if file_record[3] else 'None'}")
        else:
            print("   ❌ File record not found")
            return False
            
        # Check knowledge assets
        print("   🧠 Checking knowledge assets...")
        cur.execute("SELECT id, title, document_type, status, metadata FROM knowledge_assets WHERE source_file_id = %s", (file_id,))
        assets = cur.fetchall()
        print(f"   📊 Knowledge assets created: {len(assets)}")
        
        for i, asset in enumerate(assets, 1):
            asset_id, title, doc_type, status, metadata = asset
            print(f"   ✅ Asset {i}: {title}")
            print(f"       - Type: {doc_type}")
            print(f"       - Status: {status}")
            print(f"       - Metadata: {metadata}")
            
            # Check chunks for this asset
            cur.execute("SELECT COUNT(*), SUM(token_count) FROM knowledge_chunks WHERE asset_id = %s", (asset_id,))
            chunk_info = cur.fetchone()
            if chunk_info:
                chunk_count, total_tokens = chunk_info
                print(f"       - Chunks: {chunk_count}")
                print(f"       - Total tokens: {total_tokens}")
        
        # Check processing jobs
        print("   ⚙️ Checking processing jobs...")
        cur.execute("SELECT status, progress_percent, error_message FROM knowledge_processing_jobs WHERE asset_id IN (SELECT id FROM knowledge_assets WHERE source_file_id = %s)", (file_id,))
        jobs = cur.fetchall()
        if jobs:
            for job_status, progress, error in jobs:
                print(f"       - Status: {job_status}, Progress: {progress}%")
                if error:
                    print(f"       - Error: {error}")
        
        cur.close()
        conn.close()
        
        return len(assets) > 0
        
    except Exception as e:
        print(f"   ❌ Database check error: {e}")
        return False

def check_vector_storage():
    """Check if vectors were stored in Qdrant"""
    print(f"\n🔍 Checking Vector Storage (Qdrant)...")
    
    try:
        # Check Qdrant collections
        response = requests.get("http://localhost:6333/collections")
        if response.status_code == 200:
            collections = response.json()
            collection_names = [c['name'] for c in collections.get('result', {}).get('collections', [])]
            print(f"   📊 Available collections: {collection_names}")
            
            # Check knowledge_chunks collection specifically
            if 'knowledge_chunks' in collection_names:
                print("   ✅ Collection 'knowledge_chunks' found")
                
                # Get collection info
                info_response = requests.get("http://localhost:6333/collections/knowledge_chunks")
                if info_response.status_code == 200:
                    info = info_response.json()
                    points_count = info.get('result', {}).get('points_count', 0)
                    vectors_count = info.get('result', {}).get('vectors_count', 0)
                    print(f"   📊 Points: {points_count}, Vectors: {vectors_count}")
                    return points_count > 0
                else:
                    print("   ⚠️ Could not get collection info")
            else:
                print("   ❌ Collection 'knowledge_chunks' not found")
        else:
            print(f"   ❌ Qdrant connection failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Qdrant check error: {e}")
        
    return False

def main():
    """Main test function"""
    print("🚀 Starting comprehensive knowledge processing test...\n")
    
    # Test file upload and knowledge processing
    file_id = test_complete_workflow()
    if not file_id:
        print("\n❌ Test FAILED: File upload failed")
        return False
    
    # Wait for processing to complete
    print("\n⏳ Waiting for knowledge processing to complete...")
    time.sleep(8)  # Give processing time to complete
    
    # Check results
    project_id = get_project_id()
    assets_created = check_processing_results(file_id, project_id)
    vectors_created = check_vector_storage()
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("-" * 40)
    print(f"File Upload:         {'✅ SUCCESS' if file_id else '❌ FAILED'}")
    print(f"Knowledge Assets:    {'✅ SUCCESS' if assets_created else '❌ FAILED'}")
    print(f"Vector Storage:      {'✅ SUCCESS' if vectors_created else '❌ FAILED'}")
    
    if file_id and assets_created and vectors_created:
        print(f"\n🎉 ALL TESTS PASSED! Knowledge processing is working perfectly!")
        return True
    elif file_id and assets_created:
        print(f"\n⚠️ Partial success - assets created but vectors need attention")
        return True
    else:
        print(f"\n❌ Some components need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
