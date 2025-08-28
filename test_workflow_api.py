#!/usr/bin/env python3
"""
Test workflow API to verify the 500 error is fixed
"""
import requests
import json

def test_workflow_api():
    """Test the workflow start API endpoint"""
    print("🔧 Testing Workflow Start API")
    print("=" * 40)
    
    # Login first to get auth token
    login_data = {"username": "admin", "password": "admin"}
    try:
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data, timeout=10)
        print(f"📊 Login status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        response_data = response.json()
        print(f"📊 Login response: {response_data}")
        token = response_data.get("token")
        if not token:
            print("❌ No access token received")
            return False
            
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test workflow start
    headers = {"Authorization": f"Bearer {token}"}
    workflow_data = {
        "processKey": "ingestion_pipeline",
        "projectId": "test-project-id",
        "fileIds": ["test-file-id"],
        "params": {"test": True}
    }
    
    try:
        print(f"📤 Starting workflow: {workflow_data['processKey']}")
        response = requests.post(
            "http://localhost:8000/api/workflows/start", 
            json=workflow_data, 
            headers=headers,
            timeout=30
        )
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Workflow started successfully!")
            print(f"  • Process ID: {result.get('runId')}")
            print(f"  • Process Key: {result.get('processKey')}")
            return True
        else:
            print(f"❌ Workflow start failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  • Error: {error_detail}")
            except:
                print(f"  • Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow API error: {e}")
        return False

if __name__ == "__main__":
    success = test_workflow_api()
    if success:
        print("\n🎉 Workflow API test PASSED!")
    else:
        print("\n❌ Workflow API test FAILED!")
