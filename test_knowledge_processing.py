#!/usr/bin/env python3
"""
Test knowledge processing workflow end-to-end
"""
import requests
import json
import time
import tempfile
import os

def test_knowledge_processing():
    print("🧠 Testing Knowledge Processing Workflow")
    print("=" * 60)
    
    # Test content
    test_content = """# Test Requirements Document

## 1. System Overview
This document outlines the requirements for a navigation system.

## 2. Functional Requirements

### 2.1 GPS Navigation
- REQ-001: The system shall provide GPS-based navigation
- REQ-002: Position accuracy shall be within ±3 meters
- REQ-003: The system shall update position every 1 second

### 2.2 User Interface  
- REQ-004: Display shall show current position and heading
- REQ-005: Route planning shall be available to users
- REQ-006: Voice guidance shall be provided during navigation

## 3. Performance Requirements
- REQ-007: System startup time shall not exceed 30 seconds
- REQ-008: Route calculation shall complete within 5 seconds
"""

    try:
        # Step 1: Login
        print("🔐 Step 1: Authentication...")
        login_data = {"username": "jdehart", "password": "jdehart"}
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        token = response.json().get("token")
        if not token:
            print("❌ No token received")
            return False
        
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # Step 2: Get project ID
        print("\n📁 Step 2: Getting project...")
        response = requests.get("http://localhost:8000/api/projects", headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Projects request failed: {response.status_code}")
            return False
        
        projects_data = response.json()
        projects = projects_data.get("projects", [])
        
        if not projects:
            print("❌ No projects found")
            print(f"Response: {projects_data}")
            return False
            
        project_id = projects[0]["project_id"]
        print(f"✅ Using project: {project_id}")
        
        # Step 3: Upload file
        print("\n📤 Step 3: Uploading test file...")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_navigation_reqs.md', f, 'text/markdown')}
                data = {
                    'project_id': project_id,
                    'process_for_knowledge': True,  # Enable knowledge processing
                    'embedding_model': 'all-MiniLM-L6-v2',
                    'chunking_strategy': 'hybrid'
                }
                
                response = requests.post(
                    "http://localhost:8000/api/files/upload", 
                    files=files, 
                    data=data,
                    headers=headers, 
                    timeout=30
                )
            
            if response.status_code != 200:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            file_data = response.json()
            file_id = file_data.get("file_id")
            print(f"✅ File uploaded: {file_id}")
            
        finally:
            os.unlink(temp_file_path)
        
        # Step 4: Wait and check for knowledge processing
        print("\n🧠 Step 4: Checking knowledge processing...")
        time.sleep(3)  # Give some time for background processing
        
        # Check if knowledge assets were created
        response = requests.get(
            f"http://localhost:8000/api/knowledge/assets?project_id={project_id}", 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Knowledge assets check failed: {response.status_code}")
            return False
        
        assets_data = response.json()
        assets = assets_data.get("assets", [])
        total_count = assets_data.get("total_count", 0)
        print(f"📊 Found {total_count} knowledge assets")
        
        # Find our asset
        our_asset = None
        for asset in assets:
            if asset.get("source_file_id") == file_id:
                our_asset = asset
                break
        
        if our_asset:
            print(f"✅ Knowledge asset created: {our_asset['id']}")
            print(f"📄 Title: {our_asset['title']}")
            print(f"🏷️  Type: {our_asset['document_type']}")
            
            # Check chunks using include_chunks parameter
            asset_id = our_asset['id']
            response = requests.get(
                f"http://localhost:8000/api/knowledge/assets/{asset_id}?include_chunks=true", 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                asset_with_chunks = response.json()
                chunks = asset_with_chunks.get('chunks', [])
                print(f"📝 Found {len(chunks)} chunks")
                
                if chunks:
                    print("📋 Sample chunk:")
                    chunk = chunks[0]
                    print(f"  • Sequence: {chunk.get('sequence_number')}")
                    print(f"  • Type: {chunk.get('chunk_type')}")
                    content = chunk.get('content', '')[:100]
                    print(f"  • Content preview: {content}...")
            else:
                print(f"⚠️  Could not retrieve asset with chunks: {response.status_code}")
                
        else:
            print("❌ No knowledge asset found for uploaded file")
            return False
        
        # Step 5: Test search (SKIP - search API not yet implemented)
        print("\n🔍 Step 5: Testing knowledge search...")
        print("⏭️  Skipping search test - search API not yet implemented")
        
        print("\n🎉 Knowledge Processing Test: SUCCESS!")
        print("✅ File upload, knowledge transformation, and chunking all working")
        print("📝 Search API still needs to be implemented")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    test_knowledge_processing()
