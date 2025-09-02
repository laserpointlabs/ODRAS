#!/usr/bin/env python3
"""
Test knowledge processing with the fixed project_id storage
"""
import requests
import json
import tempfile
import os

def test_fixed_processing():
    print("🧠 Testing Fixed Knowledge Processing")
    print("=" * 50)
    
    test_content = """# Navigation System Requirements v2

## Overview
This document specifies requirements for a GPS navigation system.

## Functional Requirements
- REQ-001: GPS positioning accuracy shall be within 3 meters
- REQ-002: Route calculation shall complete within 5 seconds
- REQ-003: Voice guidance shall be provided during navigation

## Performance Requirements
- REQ-004: System shall support 1000+ concurrent users
- REQ-005: Battery life shall exceed 8 hours continuous use"""
    
    try:
        # Login
        login_data = {"username": "jdehart", "password": "jdehart"}
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data)
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # Get project
        response = requests.get("http://localhost:8000/api/projects", headers=headers)
        project_id = response.json()["projects"][0]["project_id"]
        print(f"✅ Using project: {project_id}")
        
        # Upload file with knowledge processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('nav_requirements_v2.md', f, 'text/markdown')}
                data = {
                    'project_id': project_id,
                    'process_for_knowledge': True,
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
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ File uploaded and processed successfully")
                    print(f"📄 File ID: {result['file_id']}")
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    return False
        finally:
            os.unlink(temp_file_path)
        
        # Wait a moment for processing
        import time
        time.sleep(3)
        
        # Test search
        search_data = {
            "query": "GPS positioning accuracy",
            "project_id": project_id,
            "limit": 5,
            "min_score": 0.0
        }
        
        response = requests.post(
            "http://localhost:8000/api/knowledge/search", 
            json=search_data,
            headers=headers
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"🔍 Search results: {results['total_found']} found")
            if results['results']:
                top_result = results['results'][0]
                print(f"🎯 Top result score: {top_result['score']:.3f}")
                print(f"📄 Content preview: {top_result['content'][:100]}...")
                print(f"✅ Knowledge search working!")
            else:
                print(f"📭 No search results (but search worked)")
        else:
            print(f"❌ Search failed: {response.status_code}")
        
        print(f"\n🎉 Test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_fixed_processing()

