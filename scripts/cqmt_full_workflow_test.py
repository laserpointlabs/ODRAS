#!/usr/bin/env python3
"""
Full CQ/MT Workflow Test Script - Self-Contained
Tests the complete workflow: Create MT → Add Data → Create CQ → Execute CQ
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def main():
    print("=== CQ/MT Full Workflow Test ===\n")
    
    # Step 1: Login
    print("1. Logging in as das_service...")
    login_resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "das_service", "password": "das_service_2024!"}
    )
    token = login_resp.json()['token']
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in\n")
    
    # Step 2: Get project
    print("2. Getting project...")
    projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    projects = projects_resp.json()['projects']
    if not projects:
        print("❌ No projects found. Please create a project first.")
        sys.exit(1)
    project_id = projects[0]['project_id']
    print(f"✅ Using project: {project_id}\n")
    
    # Step 3: Create microtheory
    print("3. Creating microtheory...")
    mt_data = {
        "label": "Test Aircraft Microtheory",
        "description": "Microtheory containing test aircraft data",
        "setDefault": True
    }
    create_mt_resp = requests.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
        headers=headers,
        json=mt_data
    )
    if create_mt_resp.status_code not in [200, 201]:
        print(f"❌ Failed to create MT: {create_mt_resp.text}")
        sys.exit(1)
    
    mt_result = create_mt_resp.json()
    mt_iri = mt_result.get('data', {}).get('iri') if isinstance(mt_result, dict) else mt_result.get('iri')
    mt_id = mt_result.get('data', {}).get('id') if isinstance(mt_result, dict) else mt_result.get('id')
    print(f"✅ Created microtheory: {mt_iri}")
    
    # Step 3b: Add triples to microtheory
    print("3b. Adding test data to microtheory...")
    update_data = {
        "label": "Test Aircraft Microtheory",
        "description": "Microtheory containing test aircraft data",
        "triples": [
            {"subject": "http://example.org/test#Aircraft1", "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "object": "http://example.org/test#Aircraft"},
            {"subject": "http://example.org/test#Aircraft1", "predicate": "http://www.w3.org/2000/01/rdf-schema#label", "object": "F-22 Raptor"},
            {"subject": "http://example.org/test#Aircraft2", "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "object": "http://example.org/test#Aircraft"},
            {"subject": "http://example.org/test#Aircraft2", "predicate": "http://www.w3.org/2000/01/rdf-schema#label", "object": "F-35 Lightning II"},
            {"subject": "http://example.org/test#Aircraft3", "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "object": "http://example.org/test#Aircraft"},
            {"subject": "http://example.org/test#Aircraft3", "predicate": "http://www.w3.org/2000/01/rdf-schema#label", "object": "C-130 Hercules"}
        ]
    }
    update_mt_resp = requests.put(
        f"{BASE_URL}/api/cqmt/microtheories/{mt_id}",
        headers=headers,
        json=update_data
    )
    if update_mt_resp.status_code not in [200, 201, 204]:
        print(f"❌ Failed to add triples: {update_mt_resp.text}")
        sys.exit(1)
    print("✅ Added test data\n")
    
    # Step 4: Create competency question
    print("4. Creating competency question...")
    cq_data = {
        "cq_name": "List All Aircraft",
        "problem_text": "List all aircraft in the ontology",
        "sparql_text": """PREFIX ex: <http://example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    OPTIONAL { ?aircraft rdfs:label ?label }
}
ORDER BY ?label""",
        "contract_json": {
            "require_columns": ["aircraft", "label"],
            "min_rows": 2,
            "max_execution_time_ms": 5000
        },
        "mt_iri_default": mt_iri,
        "status": "active"
    }
    create_cq_resp = requests.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
        headers=headers,
        json=cq_data
    )
    if create_cq_resp.status_code not in [200, 201]:
        print(f"❌ Failed to create CQ: {create_cq_resp.text}")
        sys.exit(1)
    
    cq_result = create_cq_resp.json()
    cq_id = cq_result.get('data', {}).get('id') if isinstance(cq_result, dict) else cq_result.get('id')
    print(f"✅ Created CQ: {cq_id}\n")
    
    # Step 5: Execute CQ
    print("5. Executing CQ against microtheory...")
    exec_data = {
        "mt_iri": mt_iri,
        "params": {}
    }
    exec_resp = requests.post(
        f"{BASE_URL}/api/cqmt/cqs/{cq_id}/run",
        headers=headers,
        json=exec_data
    )
    if exec_resp.status_code != 200:
        print(f"❌ Failed to execute CQ: {exec_resp.text}")
        sys.exit(1)
    
    exec_result = exec_resp.json()
    print("Execution response:")
    print(json.dumps(exec_result, indent=2))
    print()
    
    # Step 6: Test "Test Query" endpoint
    print("6. Testing 'Test Query' endpoint...")
    test_query_data = {
        "sparql": """PREFIX ex: <http://example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    OPTIONAL { ?aircraft rdfs:label ?label }
}
ORDER BY ?label""",
        "mt_iri": mt_iri,
        "project_id": project_id
    }
    test_resp = requests.post(
        f"{BASE_URL}/api/cqmt/test-query",
        headers=headers,
        json=test_query_data
    )
    if test_resp.status_code != 200:
        print(f"❌ Failed to test query: {test_resp.text}")
        sys.exit(1)
    
    test_result = test_resp.json()
    print("Test Query response:")
    print(json.dumps(test_result, indent=2))
    print()
    
    # Step 7: Summary
    print("=== Summary ===")
    print(f"Project ID: {project_id}")
    print(f"Microtheory IRI: {mt_iri}")
    print(f"CQ ID: {cq_id}")
    print(f"CQ Execution Pass: {exec_result.get('pass', False)}")
    print(f"Test Query Success: {test_result.get('success', False)}")
    print(f"Rows Returned: {test_result.get('row_count', 0)}")
    print("✅ Workflow completed successfully")

if __name__ == "__main__":
    main()
