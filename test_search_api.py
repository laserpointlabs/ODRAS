#!/usr/bin/env python3
"""
Test the new search API endpoint
"""
import requests
import json
import time

def test_search_api():
    print("🔍 Testing Knowledge Search API")
    print("=" * 50)
    
    try:
        # Step 1: Login
        print("🔐 Step 1: Authentication...")
        login_data = {"username": "jdehart", "password": "jdehart"}
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # Step 2: Test search with various queries
        test_queries = [
            "GPS navigation requirements",
            "system requirements", 
            "navigation accuracy",
            "requirements document"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing search: '{query}'")
            
            search_data = {
                "query": query,
                "limit": 5,
                "min_score": 0.0,
                "include_metadata": True
            }
            
            response = requests.post(
                "http://localhost:8000/api/knowledge/search", 
                json=search_data,
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Search successful:")
                print(f"  📊 Results: {results['total_found']}")
                print(f"  ⏱️  Time: {results['search_time_ms']}ms")
                
                if results['results']:
                    print(f"  🎯 Top result:")
                    top_result = results['results'][0]
                    print(f"    • Score: {top_result['score']:.3f}")
                    print(f"    • Asset: {top_result['asset_metadata']['title']}")
                    print(f"    • Type: {top_result['asset_metadata']['document_type']}")
                    print(f"    • Content: {top_result['content'][:100]}...")
                else:
                    print(f"  📭 No results found")
                    
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(f"Error: {response.text}")
        
        # Step 3: Test search with project filter
        print(f"\n🏗️  Testing project-filtered search...")
        
        # Get a project ID
        response = requests.get("http://localhost:8000/api/projects", headers=headers, timeout=10)
        projects_data = response.json()
        projects = projects_data.get("projects", [])
        
        if projects:
            project_id = projects[0]["project_id"]
            print(f"📁 Using project: {project_id}")
            
            search_data = {
                "query": "requirements",
                "project_id": project_id,
                "limit": 3,
                "min_score": 0.0
            }
            
            response = requests.post(
                "http://localhost:8000/api/knowledge/search", 
                json=search_data,
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Project search successful: {results['total_found']} results")
            else:
                print(f"❌ Project search failed: {response.status_code}")
        
        print(f"\n🎉 Search API Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    test_search_api()

