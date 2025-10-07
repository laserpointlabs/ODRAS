#!/usr/bin/env python3
"""
CI RAG Test - Automated validation for continuous integration
Validates RAG system functionality with specific success criteria
"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:8000"

def login():
    """Login and return authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "das_service",
        "password": "das_service_2024!"
    })
    if response.ok:
        data = response.json()
        return data.get("access_token") or data.get("token")
    return None

def get_or_create_project(token):
    """Get existing project or create new one"""
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get existing project
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if response.ok:
        projects = response.json()
        if projects and isinstance(projects, list) and len(projects) > 0:
            return projects[0]['project_id']

    # Create new project
    response = requests.post(f"{BASE_URL}/api/projects", json={
        "name": "CI RAG Test Project",
        "description": "Project for CI RAG testing"
    }, headers=headers)

    if response.ok:
        result = response.json()
        return result.get('project', {}).get('project_id')

    return None

def upload_document(token, project_id, file_path, doc_type="requirements"):
    """Upload document and return success status"""
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

    return response.ok

def test_query(token, project_id, question):
    """Test RAG query and return results"""
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

def validate_uas_names_query(result):
    """Validate UAS names query meets success criteria"""
    if not result:
        return False, "Query failed"

    message = result['message'].lower()
    sources = result['sources']
    chunks_found = result['chunks_found']

    # Check for minimum UAS platforms
    uas_platforms = [
        'hexacopter h6 heavy', 'octocopter sentinel', 'skyeagle x500',
        'wingone pro', 'aeromapper x8', 'falcon vtol-x',
        'hovercruise 700', 'trivector vtol', 'quadcopter t4'
    ]

    found_platforms = [platform for platform in uas_platforms if platform in message]

    # Success criteria
    criteria = {
        'min_platforms': len(found_platforms) >= 6,  # At least 6 of 9 platforms
        'min_chunks': chunks_found >= 6,  # At least 6 chunks retrieved
        'has_sources': len(sources) > 0,  # Sources present
        'correct_titles': all('unknown' not in source.get('title', '').lower() for source in sources),  # No "Unknown Document"
        'comprehensive_response': len(message) > 100  # Substantial response
    }

    # Check each criterion
    failed_criteria = []
    for criterion, passed in criteria.items():
        if not passed:
            failed_criteria.append(criterion)

    if failed_criteria:
        return False, f"Failed criteria: {', '.join(failed_criteria)}"

    return True, f"✅ Found {len(found_platforms)} UAS platforms: {', '.join(found_platforms)}"

def validate_general_query(result, query_type):
    """Validate general query meets success criteria"""
    if not result:
        return False, "Query failed"

    message = result['message']
    sources = result['sources']
    chunks_found = result['chunks_found']

    # Success criteria for general queries
    criteria = {
        'min_chunks': chunks_found >= 3,  # At least 3 chunks
        'has_sources': len(sources) > 0,  # Sources present
        'correct_titles': all('unknown' not in source.get('title', '').lower() for source in sources),
        'substantial_response': len(message) > 50,  # Not just "I don't know"
        'no_generic_response': 'i don\'t have that information' not in message.lower()
    }

    # Check each criterion
    failed_criteria = []
    for criterion, passed in criteria.items():
        if not passed:
            failed_criteria.append(criterion)

    if failed_criteria:
        return False, f"Failed criteria: {', '.join(failed_criteria)}"

    return True, f"✅ {query_type} query successful"

def main():
    """Main CI test function"""
    print("=== CI RAG SYSTEM TEST ===")
    print("Validating RAG functionality with automated criteria")
    print()

    # Login
    token = login()
    if not token:
        print("❌ Login failed")
        sys.exit(1)

    # Get or create project
    project_id = get_or_create_project(token)
    if not project_id:
        print("❌ No project available")
        sys.exit(1)

    print(f"✅ Using project: {project_id}")

    # Upload test documents
    print("📤 Uploading test documents...")
    uploads = [
        ("data/disaster_response_requirements.md", "requirements"),
        ("data/uas_specifications.md", "specification"),
        ("data/decision_matrix_template.md", "analysis_template")
    ]

    for file_path, doc_type in uploads:
        if upload_document(token, project_id, file_path, doc_type):
            print(f"✅ Uploaded {os.path.basename(file_path)}")
        else:
            print(f"❌ Failed to upload {os.path.basename(file_path)}")
            sys.exit(1)

    print("\n⏳ Waiting for processing...")
    time.sleep(15)  # Wait for processing

    # Test queries with validation
    test_cases = [
        {
            "query": "Please list the names only of the UAS we can select from in the specification",
            "validator": validate_uas_names_query,
            "name": "UAS Names Query"
        },
        {
            "query": "What are the UAS requirements for disaster response?",
            "validator": lambda r: validate_general_query(r, "UAS Requirements"),
            "name": "UAS Requirements Query"
        },
        {
            "query": "What are the different types of UAS platforms available?",
            "validator": lambda r: validate_general_query(r, "UAS Types"),
            "name": "UAS Types Query"
        }
    ]

    print("\n🧪 Running RAG validation tests...")
    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"Query: {test_case['query']}")

        result = test_query(token, project_id, test_case['query'])
        passed, message = test_case['validator'](result)

        if passed:
            print(f"✅ PASS: {message}")
        else:
            print(f"❌ FAIL: {message}")
            all_passed = False

        # Show debug info
        if result:
            print(f"   Chunks found: {result['chunks_found']}")
            print(f"   Sources: {len(result['sources'])}")
            if result['sources']:
                for j, source in enumerate(result['sources'], 1):
                    print(f"     {j}. {source.get('title', 'Unknown')} (score: {source.get('relevance_score', 0):.3f})")

    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL RAG TESTS PASSED")
        print("✅ RAG system is stable and working correctly")
        sys.exit(0)
    else:
        print("❌ SOME RAG TESTS FAILED")
        print("🚨 RAG system needs attention")
        sys.exit(1)

if __name__ == "__main__":
    main()
