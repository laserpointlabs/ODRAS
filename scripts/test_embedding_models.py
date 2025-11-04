#!/usr/bin/env python3
"""
Test script to verify both embedding models work correctly with ODRAS.
Tests both all-MiniLM-L6-v2 (384 dims) and all-mpnet-base-v2 (768 dims).
"""

import asyncio
import json
import requests
import time
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER = "das_service"
TEST_PASSWORD = "das_service_2024!"

def login():
    """Login and get session token."""
    print("🔐 Logging in...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USER,
        "password": TEST_PASSWORD
    })

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Logged in as {TEST_USER}")
        # Try different possible token field names
        token = data.get("access_token") or data.get("token") or data.get("auth_token")
        if token:
            return token
        else:
            print(f"❌ No token found in response: {data}")
            return None
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def get_default_project(token):
    """Get the default project ID."""
    print("🔍 Getting default project...")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)

    if response.status_code == 200:
        data = response.json()
        projects = data.get('projects', [])
        print(f"🔍 Projects response: {projects}")
        if projects and len(projects) > 0:
            project_id = projects[0].get('project_id') or projects[0].get('id')
            print(f"✅ Found project: {project_id}")
            return project_id
        else:
            print("❌ No projects found - creating default project")
            return create_default_project(token)
    else:
        print(f"❌ Failed to get projects: {response.status_code}")
        return None

def create_default_project(token):
    """Create a default project for testing."""
    print("🔧 Creating default project...")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/projects", json={
        "name": "Test Project",
        "description": "Default project for embedding model testing"
    }, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"🔍 Project creation response: {result}")
        # Handle nested project structure
        project_data = result.get('project', result)
        project_id = project_data.get('project_id') or project_data.get('id')
        print(f"✅ Created project: {project_id}")
        return project_id
    else:
        print(f"❌ Failed to create project: {response.status_code} - {response.text}")
        return None

def upload_document(token, file_path, doc_type="requirements", project_id=None, embedding_model="all-MiniLM-L6-v2"):
    """Upload a document for processing."""
    print(f"📤 Uploading {file_path} as {doc_type} with {embedding_model}...")

    headers = {"Authorization": f"Bearer {token}"}

    with open(file_path, 'rb') as f:
        filename = Path(file_path).name
        files = {'file': (filename, f, 'text/markdown')}
        data = {
            'docType': doc_type,
            'embedding_model': embedding_model
        }
        if project_id:
            data['project_id'] = project_id

        response = requests.post(
            f"{BASE_URL}/api/files/upload",
            headers=headers,
            files=files,
            data=data
        )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful: {result}")
        # Try different possible file ID field names
        file_id = result.get('file_id') or result.get('id') or result.get('upload_id')
        return file_id
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None

def test_rag_query(token, question, project_id, max_wait=30):
    """Test RAG query using DAS2 endpoint."""
    print(f"🔍 Testing RAG query via DAS2: '{question}'")

    headers = {"Authorization": f"Bearer {token}"}

    # Send DAS2 chat message
    response = requests.post(f"{BASE_URL}/api/das/chat", json={
        "message": question,
        "project_id": project_id
    }, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ RAG query successful")
        # print(f"🔍 DAS2 response: {result}")  # Too verbose

        # Try different possible response field names
        response_text = result.get('response') or result.get('message') or result.get('answer') or ""
        chunks_found = result.get('metadata', {}).get('chunks_found', 0)
        rag_chunks = result.get('metadata', {}).get('debug', {}).get('rag_debug', {}).get('chunks_found', 0)
        sources = result.get('sources', [])

        print(f"   Response preview: {response_text[:300]}...")
        print(f"   Sources: {len(sources)}")
        print(f"   Chunks found: {chunks_found} (RAG reported: {rag_chunks})")

        # Check if response is actually useful
        useless_phrases = [
            "I don't have that information",
            "I couldn't find any relevant information",
            "Unfortunately, I don't have",
            "may find relevant details",
            "available in the document titled",
            "can be found in the document"
        ]
        is_useless = any(phrase in response_text for phrase in useless_phrases)

        if is_useless:
            print(f"   ❌ USELESS RESPONSE DETECTED!")
            rag_debug = result.get('metadata', {}).get('debug', {}).get('rag_debug', {})
            print(f"   RAG content preview: {rag_debug.get('rag_content_preview', 'N/A')[:200]}...")
            print(f"   RAG success: {rag_debug.get('rag_success')}")
            result['_test_useless'] = True
        else:
            print(f"   ✅ Response contains actual information")
            result['_test_useless'] = False

        return result
    else:
        print(f"❌ RAG query failed: {response.status_code} - {response.text}")
        return None

def check_collections():
    """Check Qdrant collections."""
    print("🔍 Checking Qdrant collections...")

    try:
        response = requests.get("http://localhost:6333/collections")
        if response.status_code == 200:
            collections = response.json()
            collection_names = [col['name'] for col in collections.get('result', {}).get('collections', [])]

            required_collections = [
                "knowledge_chunks",      # 384 dims
                "knowledge_chunks_768",   # 768 dims
                "project_threads"
            ]

            print(f"📊 Found collections: {collection_names}")

            for req_col in required_collections:
                if req_col in collection_names:
                    print(f"✅ {req_col} exists")
                else:
                    print(f"❌ {req_col} missing")

            return all(req_col in collection_names for req_col in required_collections)
        else:
            print(f"❌ Failed to get collections: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking collections: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing ODRAS Embedding Models")
    print("=" * 50)

    # Check collections first
    if not check_collections():
        print("❌ Required collections missing. Run './odras.sh init-db' first.")
        return False

    # Login
    token = login()
    if not token:
        return False

    # Get default project
    project_id = get_default_project(token)
    if not project_id:
        print("❌ No project available for testing")
        return False

    # Test documents with different embedding models
    test_docs = [
        ("data/disaster_response_requirements.md", "requirements", "all-MiniLM-L6-v2"),
        ("data/uas_specifications.md", "specification", "all-mpnet-base-v2"),
        ("data/decision_matrix_template.md", "analysis_template", "all-MiniLM-L6-v2")
    ]

    uploaded_files = []

    # Upload test documents
    for doc_path, doc_type, embedding_model in test_docs:
        if Path(doc_path).exists():
            file_id = upload_document(token, doc_path, doc_type, project_id, embedding_model)
            if file_id:
                uploaded_files.append(file_id)
        else:
            print(f"⚠️ Document not found: {doc_path}")

    if not uploaded_files:
        print("❌ No documents uploaded successfully")
        return False

    print(f"📤 Uploaded {len(uploaded_files)} documents")
    print("⏳ Waiting for processing...")
    time.sleep(10)  # Wait for processing

    # Test multiple RAG queries
    test_queries = [
        "What are the UAS requirements for disaster response?",
        "What are the different types of UAS platforms available?",
        "How should I evaluate UAS platforms using the decision matrix?",
        "What are the environmental tolerance requirements?",
        "What is the deployment speed requirement?"
    ]

    successful_queries = 0
    useful_responses = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Testing query {i}/{len(test_queries)}: '{query}'")
        result = test_rag_query(token, query, project_id)
        if result and result.get('message'):
            successful_queries += 1
            if not result.get('_test_useless', True):
                useful_responses += 1
                print(f"✅ Query {i} successful with USEFUL response")
            else:
                print(f"⚠️ Query {i} returned but with USELESS response")
        else:
            print(f"❌ Query {i} failed")
        time.sleep(2)  # Brief pause between queries

    print("\n" + "=" * 50)
    print(f"📊 Test Results:")
    print(f"   Documents uploaded: {len(uploaded_files)}")
    print(f"   Successful RAG queries: {successful_queries}/{len(test_queries)}")
    print(f"   USEFUL responses: {useful_responses}/{len(test_queries)}")

    if useful_responses == len(test_queries):
        print("🎉 All tests passed! Both embedding models are working correctly.")
        return True
    elif useful_responses > 0:
        print(f"⚠️ Only {useful_responses}/{len(test_queries)} queries returned useful information.")
        print("RAG is partially working but not returning good results for all queries.")
        return False
    else:
        print("❌ RAG is completely broken - no useful responses returned!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
