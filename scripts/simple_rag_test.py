#!/usr/bin/env python3
"""
Simple RAG Test - Shows actual outputs so you can judge quality
"""

import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"

def login():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "das_service",
        "password": "das_service_2024!"
    })
    if response.ok:
        data = response.json()
        return data.get("access_token") or data.get("token")
    return None

def get_or_create_project(token):
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get existing project
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if response.ok:
        projects = response.json()
        if projects and isinstance(projects, list) and len(projects) > 0:
            print(f"✅ Using existing project: {projects[0]['project_id']}")
            return projects[0]['project_id']

    # Create new project
    print("Creating new project...")
    response = requests.post(f"{BASE_URL}/api/projects", json={
        "name": "RAG Test Project",
        "description": "Project for testing RAG functionality"
    }, headers=headers)

    if response.ok:
        result = response.json()
        project_id = result.get('project', {}).get('project_id')
        print(f"✅ Created project: {project_id}")
        return project_id

    print("❌ Failed to create project")
    return None

def upload_document(token, project_id, file_path, doc_type="requirements"):
    headers = {"Authorization": f"Bearer {token}"}

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'project_id': project_id,
            'document_type': doc_type,
            'embedding_model': 'all-MiniLM-L6-v2'
        }
        response = requests.post(f"{BASE_URL}/api/files/upload", files=files, data=data, headers=headers)

    if response.ok:
        result = response.json()
        print(f"✅ Uploaded {os.path.basename(file_path)} as {doc_type}")
        return True
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return False

def test_query(token, project_id, question):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/das2/chat", json={
        "message": question,
        "project_id": project_id
    }, headers=headers)

    if response.ok:
        result = response.json()
        return {
            "message": result.get('message', ''),
            "sources": result.get('sources', []),
            "chunks_found": result.get('metadata', {}).get('chunks_found', 0),
            "rag_chunks": result.get('metadata', {}).get('debug', {}).get('rag_debug', {}).get('chunks_found', 0)
        }
    return None

def main():
    print("=== SIMPLE RAG TEST ===")
    print("This will show you actual outputs so you can judge quality")
    print()

    # Login
    token = login()
    if not token:
        print("❌ Login failed")
        return

    # Get or create project
    project_id = get_or_create_project(token)
    if not project_id:
        print("❌ No project available")
        return

    print()

    # Upload test documents
    print("Uploading test documents...")
    upload_document(token, project_id, "data/disaster_response_requirements.md", "requirements")
    upload_document(token, project_id, "data/uas_specifications.md", "specification")
    upload_document(token, project_id, "data/decision_matrix_template.md", "analysis_template")

    print("\n⏳ Waiting for processing...")
    time.sleep(15)  # Wait for processing
    print()

    # Test queries
    queries = [
        "What are the UAS requirements for disaster response?",
        "List all UAS platforms with their specifications",
        "What is the deployment speed requirement?",
        "What are the environmental tolerance requirements?"
    ]

    for i, query in enumerate(queries, 1):
        print(f"--- QUERY {i} ---")
        print(f"Question: {query}")
        print()

        result = test_query(token, project_id, query)
        if result:
            print(f"Chunks found: {result['chunks_found']} (RAG: {result['rag_chunks']})")
            print(f"Sources: {len(result['sources'])}")
            print()
            print("RESPONSE:")
            print("-" * 50)
            print(result['message'])
            print("-" * 50)
            print()

            if result['sources']:
                print("SOURCES:")
                for j, source in enumerate(result['sources'], 1):
                    print(f"{j}. {source.get('title', 'Unknown')} (score: {source.get('relevance_score', 0):.3f})")
                print()
        else:
            print("❌ Query failed")
        print()

if __name__ == "__main__":
    main()
