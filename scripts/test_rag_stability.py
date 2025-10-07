#!/usr/bin/env python3
"""
RAG Stability Test - Comprehensive testing for ODRAS RAG system
Tests chunk limits, source attribution, and response consistency
"""

import requests
import time
import json
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

def login() -> str:
    """Login and return token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "das_service",
        "password": "das_service_2024!"
    })

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token") or data.get("auth_token")
        print(f"✅ Logged in as das_service")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def get_project(token: str) -> str:
    """Get or create a test project."""
    headers = {"Authorization": f"Bearer {token}"}

    # Get existing projects
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if response.ok:
        projects = response.json()
        if projects and isinstance(projects, list) and len(projects) > 0:
            project_id = projects[0]['project_id']
            print(f"✅ Using existing project: {project_id}")
            return project_id

    print("❌ No projects found")
    return None

def test_rag_query(token: str, question: str, project_id: str) -> Dict[str, Any]:
    """Test a RAG query and return detailed results."""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(f"{BASE_URL}/api/das2/chat", json={
        "message": question,
        "project_id": project_id
    }, headers=headers)

    if response.status_code == 200:
        result = response.json()
        return {
            "success": True,
            "response": result.get('message', ''),
            "sources": result.get('sources', []),
            "chunks_found": result.get('metadata', {}).get('chunks_found', 0),
            "rag_chunks": result.get('metadata', {}).get('debug', {}).get('rag_debug', {}).get('chunks_found', 0),
            "rag_success": result.get('metadata', {}).get('debug', {}).get('rag_debug', {}).get('rag_success', False)
        }
    else:
        return {
            "success": False,
            "error": f"{response.status_code}: {response.text}"
        }

def analyze_response_quality(response: str) -> Dict[str, Any]:
    """Analyze the quality of a RAG response."""
    useless_phrases = [
        "I don't have that information",
        "I couldn't find any relevant information",
        "Unfortunately, I don't have",
        "may find relevant details",
        "available in the document titled",
        "can be found in the document"
    ]

    is_useless = any(phrase in response for phrase in useless_phrases)
    word_count = len(response.split())

    # Look for specific technical details
    has_numbers = any(char.isdigit() for char in response)
    has_technical_terms = any(term in response.lower() for term in [
        'specification', 'requirement', 'meter', 'kilometer', 'hour', 'kg', 'knot',
        'temperature', 'operational', 'deployment', 'endurance', 'payload'
    ])

    quality_score = 0
    if not is_useless:
        quality_score += 40
    if word_count > 50:
        quality_score += 20
    if has_numbers:
        quality_score += 20
    if has_technical_terms:
        quality_score += 20

    return {
        "is_useless": is_useless,
        "word_count": word_count,
        "has_numbers": has_numbers,
        "has_technical_terms": has_technical_terms,
        "quality_score": quality_score,
        "quality_level": "High" if quality_score >= 80 else "Medium" if quality_score >= 50 else "Low"
    }

def main():
    print("🚀 RAG Stability Test - Comprehensive Testing")
    print("=" * 60)

    # Login
    token = login()
    if not token:
        return False

    # Get project
    project_id = get_project(token)
    if not project_id:
        return False

    # Test queries designed to test different aspects
    test_cases = [
        {
            "query": "What are the operational requirements for UAS in disaster response?",
            "expected_chunks": 5,  # Should find multiple chunks
            "expected_sources": 2,  # Should have sources
            "description": "Basic operational requirements query"
        },
        {
            "query": "List all UAS platforms with their specifications including weight, range, and endurance",
            "expected_chunks": 10,  # Should find many chunks for comprehensive query
            "expected_sources": 3,   # Should have multiple sources
            "description": "Comprehensive specifications query"
        },
        {
            "query": "What is the deployment speed requirement?",
            "expected_chunks": 3,   # Specific query
            "expected_sources": 1,  # Should have at least one source
            "description": "Specific requirement query"
        },
        {
            "query": "How do I evaluate UAS platforms using the decision matrix framework?",
            "expected_chunks": 5,   # Should find decision matrix content
            "expected_sources": 2,  # Should reference decision matrix document
            "description": "Framework/process query"
        },
        {
            "query": "What are the environmental tolerance requirements including temperature and wind?",
            "expected_chunks": 5,   # Should find environmental specs
            "expected_sources": 2,  # Should have sources
            "description": "Environmental specifications query"
        }
    ]

    results = []
    total_passed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}/5: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")

        # Run the test
        result = test_rag_query(token, test_case['query'], project_id)

        if not result['success']:
            print(f"❌ Query failed: {result['error']}")
            results.append({**test_case, "passed": False, "result": result})
            continue

        # Analyze results
        quality = analyze_response_quality(result['response'])

        print(f"✅ Query successful")
        print(f"   Response length: {len(result['response'])} chars ({quality['word_count']} words)")
        print(f"   Quality: {quality['quality_level']} (score: {quality['quality_score']}/100)")
        print(f"   Sources: {len(result['sources'])} (expected: ≥{test_case['expected_sources']})")
        print(f"   RAG chunks: {result['rag_chunks']} (expected: ≥{test_case['expected_chunks']})")
        print(f"   Has technical details: {'✅' if quality['has_technical_terms'] else '❌'}")
        print(f"   Has numbers: {'✅' if quality['has_numbers'] else '❌'}")

        # Check if test passed
        test_passed = (
            not quality['is_useless'] and
            len(result['sources']) >= test_case['expected_sources'] and
            result['rag_chunks'] >= test_case['expected_chunks'] and
            quality['quality_score'] >= 60
        )

        if test_passed:
            print(f"✅ Test {i} PASSED")
            total_passed += 1
        else:
            print(f"❌ Test {i} FAILED")
            if quality['is_useless']:
                print(f"   - Response is useless")
            if len(result['sources']) < test_case['expected_sources']:
                print(f"   - Insufficient sources: {len(result['sources'])} < {test_case['expected_sources']}")
            if result['rag_chunks'] < test_case['expected_chunks']:
                print(f"   - Insufficient chunks: {result['rag_chunks']} < {test_case['expected_chunks']}")
            if quality['quality_score'] < 60:
                print(f"   - Low quality score: {quality['quality_score']}")

        results.append({
            **test_case,
            "passed": test_passed,
            "result": result,
            "quality": quality
        })

        time.sleep(2)  # Brief pause between tests

    # Final results
    print("\n" + "=" * 60)
    print(f"📊 RAG Stability Test Results:")
    print(f"   Tests passed: {total_passed}/{len(test_cases)}")
    print(f"   Success rate: {(total_passed/len(test_cases)*100):.1f}%")

    if total_passed == len(test_cases):
        print("🎉 All tests passed! RAG system is stable.")
        return True
    elif total_passed >= len(test_cases) * 0.8:  # 80% pass rate
        print("⚠️ Most tests passed but some issues remain.")
        return False
    else:
        print("❌ RAG system is unstable - major issues detected.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
