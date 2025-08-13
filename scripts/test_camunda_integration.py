#!/usr/bin/env python3
"""
Test script for ODRAS Camunda integration.
"""

import asyncio
import httpx
import json

# Test configuration
API_BASE = "http://127.0.0.1:8000"
CAMUNDA_BASE = "http://localhost:8080"

async def test_camunda_status():
    """Test Camunda status endpoint."""
    print("🔍 Testing Camunda status...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/api/camunda/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Camunda status: {data['status']}")
                return data['status'] == 'running'
            else:
                print(f"❌ Camunda status failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Camunda status error: {e}")
            return False

async def test_model_listing():
    """Test model listing endpoints."""
    print("\n🔍 Testing model listing...")
    
    async with httpx.AsyncClient() as client:
        # Test Ollama models
        try:
            response = await client.get(f"{API_BASE}/api/models/ollama")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Ollama models: {len(data.get('models', []))} found")
            else:
                print(f"❌ Ollama models failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Ollama models error: {e}")
        
        # Test OpenAI models
        try:
            response = await client.get(f"{API_BASE}/api/models/openai")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ OpenAI models: {len(data.get('models', []))} found")
            else:
                print(f"❌ OpenAI models failed: {response.status_code}")
        except Exception as e:
            print(f"❌ OpenAI models error: {e}")

async def test_document_upload():
    """Test document upload and BPMN process start."""
    print("\n🔍 Testing document upload...")
    
    # Create a simple test document
    test_content = """
    The system shall provide user authentication.
    The system must respond within 100ms.
    The component shall interface with external APIs.
    The function will process data efficiently.
    The subsystem should be capable of handling 1000 concurrent users.
    """
    
    # Simulate file upload
    files = {
        'file': ('test_requirements.txt', test_content.encode(), 'text/plain')
    }
    
    data = {
        'iterations': '3',
        'llm_provider': 'openai',
        'llm_model': 'gpt-4o-mini'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE}/api/upload", files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Document upload successful!")
                print(f"   Run ID: {result['run_id']}")
                print(f"   Process ID: {result['process_id']}")
                return result['run_id']
            else:
                print(f"❌ Document upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Document upload error: {e}")
            return None

async def test_run_status(run_id: str):
    """Test run status endpoint."""
    print(f"\n🔍 Testing run status for {run_id}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/api/runs/{run_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Run status: {data['status']}")
                print(f"   Filename: {data['filename']}")
                print(f"   Camunda URL: {data.get('camunda_url', 'N/A')}")
                return data
            else:
                print(f"❌ Run status failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Run status error: {e}")
            return None

async def test_camunda_deployments():
    """Test Camunda deployments endpoint."""
    print("\n🔍 Testing Camunda deployments...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/api/camunda/deployments")
            if response.status_code == 200:
                data = response.json()
                deployments = data.get('deployments', [])
                print(f"✅ Camunda deployments: {len(deployments)} found")
                for deployment in deployments:
                    print(f"   - {deployment.get('name', 'Unknown')} ({deployment.get('id', 'No ID')})")
            else:
                print(f"❌ Camunda deployments failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Camunda deployments error: {e}")

async def main():
    """Run all tests."""
    print("🚀 Starting ODRAS Camunda integration tests...\n")
    
    # Test 1: Camunda status
    camunda_running = await test_camunda_status()
    
    if not camunda_running:
        print("\n⚠️  Camunda is not running. Please start it first:")
        print("   docker compose up -d camunda7")
        print("   Then wait for it to be ready and run this test again.")
        return
    
    # Test 2: Model listing
    await test_model_listing()
    
    # Test 3: Camunda deployments
    await test_camunda_deployments()
    
    # Test 4: Document upload
    run_id = await test_document_upload()
    
    if run_id:
        # Test 5: Run status
        await test_run_status(run_id)
        
        print(f"\n🎯 Test completed successfully!")
        print(f"   View the process in Camunda: {CAMUNDA_BASE}/cockpit/default/")
        print(f"   Run ID: {run_id}")
    else:
        print("\n❌ Document upload test failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
