#!/usr/bin/env python3
"""
Test script to upload a file and check knowledge processing
"""

import requests
import json
import sys

def get_auth_token():
    """Get an authentication token by logging in"""
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {"username": "admin", "password": "admin"}
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            result = response.json()
            token = result.get("token")
            if token:
                print(f"🔐 Authentication successful, token: {token[:20]}...")
                return token
            else:
                print("❌ No token in login response")
                return None
        else:
            print(f"❌ Login failed: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error}")
            except:
                print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login request failed: {e}")
        return None

def test_file_upload():
    # Get authentication token first
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    # Test data
    url = "http://localhost:8000/api/files/upload"
    
    # Create a test file content
    test_content = """
System Requirements Document

1. Introduction
This document describes the requirements for the GPS navigation system.

2. Functional Requirements
REQ-001: The system shall provide GPS accuracy within 3 meters.
REQ-002: The system shall update position every 1 second.
REQ-003: The system shall display current location on a map.

3. Non-functional Requirements
REQ-004: The system shall start within 30 seconds of power-on.
REQ-005: The system shall operate in temperatures from -20C to +60C.
"""
    
    # Prepare form data
    files = {
        'file': ('test_requirements.txt', test_content, 'text/plain')
    }
    
    # Get the default project ID from database
    import psycopg2
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="odras", 
            user="postgres",
            password="password",
            port=5432
        )
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM projects LIMIT 1")
        project_result = cur.fetchone()
        if not project_result:
            print("❌ No project found in database")
            return False
        project_id = str(project_result[0])
        cur.close()
        conn.close()
        print(f"📁 Using project ID: {project_id}")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    data = {
        'project_id': project_id,
        'tags': json.dumps({
            'docType': 'requirements',
            'status': 'new',
            'testFile': True
        }),
        'process_for_knowledge': 'true',
        'embedding_model': 'all-MiniLM-L6-v2',
        'chunking_strategy': 'hybrid'
    }
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    print("🚀 Uploading test file with knowledge processing...")
    print(f"   URL: {url}")
    print(f"   File: test_requirements.txt ({len(test_content)} chars)")
    print(f"   Tags: {data['tags']}")
    print(f"   Knowledge Processing: {data['process_for_knowledge']}")
    print()
    
    try:
        response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   File ID: {result.get('file_id')}")
            print(f"   Message: {result.get('message')}")
            
            # Check if knowledge asset was created
            if 'knowledge asset' in result.get('message', '').lower():
                print("🧠 Knowledge processing completed!")
                return True
            else:
                print("⚠️ Knowledge processing may not have completed")
                return False
        else:
            print(f"❌ Upload failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def check_database_state():
    """Check the current state of files and knowledge assets"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="odras", 
            user="postgres",
            password="password",
            port=5432
        )
        cur = conn.cursor()
        
        # Check files table
        cur.execute("SELECT COUNT(*) FROM files")
        file_count = cur.fetchone()[0]
        print(f"📁 Files in database: {file_count}")
        
        # Check latest files
        cur.execute("SELECT id, filename, status, created_at FROM files ORDER BY created_at DESC LIMIT 3")
        files = cur.fetchall()
        if files:
            print("   Latest files:")
            for f in files:
                print(f"   - {f[1]} (status: {f[2]}, id: {f[0]})")
        
        # Check knowledge assets
        cur.execute("SELECT COUNT(*) FROM knowledge_assets")
        asset_count = cur.fetchone()[0]
        print(f"🧠 Knowledge assets: {asset_count}")
        
        # Check latest assets
        cur.execute("SELECT id, title, document_type, status, created_at FROM knowledge_assets ORDER BY created_at DESC LIMIT 3")
        assets = cur.fetchall()
        if assets:
            print("   Latest assets:")
            for a in assets:
                print(f"   - {a[1]} (type: {a[2]}, status: {a[3]}, id: {a[0]})")
                
        # Check processing jobs
        cur.execute("SELECT COUNT(*) FROM knowledge_processing_jobs")
        job_count = cur.fetchone()[0]
        print(f"⚙️ Processing jobs: {job_count}")
        
        # Check latest jobs
        cur.execute("SELECT job_type, status, created_at FROM knowledge_processing_jobs ORDER BY created_at DESC LIMIT 3")
        jobs = cur.fetchall()
        if jobs:
            print("   Latest jobs:")
            for j in jobs:
                print(f"   - {j[0]} (status: {j[1]}, created: {j[2]})")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ODRAS Knowledge Processing Test")
    print("=" * 40)
    
    # Check initial database state
    print("📊 Current database state:")
    check_database_state()
    print()
    
    # Test file upload
    success = test_file_upload()
    print()
    
    # Check final database state
    print("📊 Database state after upload:")
    check_database_state()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)
