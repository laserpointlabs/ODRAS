#!/usr/bin/env python3
"""
Test CQMT queries against ontology to verify they return results.
"""
import httpx
import json
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

def login(client: httpx.Client, username: str = "jdehart") -> str:
    """Login and return auth token."""
    print(f"🔐 Logging in as {username}...")
    
    password = "jdehart123!" if username == "jdehart" else "das_service_2024!"
    
    response = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        sys.exit(1)
    
    login_data = response.json()
    token = login_data.get("token") or login_data.get("access_token")
    print(f"✅ Logged in successfully")
    return token

def get_ontology_classes(client: httpx.Client, graph_iri: str) -> List[Dict[str, Any]]:
    """Get ontology classes."""
    print(f"\n📚 Fetching ontology classes from: {graph_iri}")
    
    response = client.get(
        f"{BASE_URL}/api/ontology",
        params={"graph": graph_iri},
        follow_redirects=True,
        timeout=TIMEOUT
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch ontology: {response.status_code}")
        return []
    
    data = response.json()
    ontology_data = data.get("data", {})
    
    classes = []
    # API returns classes directly under data["classes"]
    class_list = ontology_data.get("classes", [])
    
    print(f"   Found {len(class_list)} classes")
    
    for cls in class_list:
        class_info = {
            "name": cls.get("name"),  # lowercase name like "requirement"
            "label": cls.get("label"),  # Display name like "Requirement"
            "uri": cls.get("uri")
        }
        classes.append(class_info)
        print(f"   ✓ {class_info['label']} (name: {class_info['name']})")
    
    return classes

def get_cqs(client: httpx.Client, project_id: str) -> List[Dict[str, Any]]:
    """Get all CQs for project."""
    print(f"\n❓ Fetching CQs for project {project_id}...")
    
    response = client.get(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
        timeout=TIMEOUT
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch CQs: {response.status_code}")
        return []
    
    cqs = response.json()
    print(f"   Found {len(cqs)} CQs")
    return cqs

def test_cq(client: httpx.Client, cq: Dict[str, Any], graph_iri: str) -> Dict[str, Any]:
    """Test a CQ by running its SPARQL query."""
    cq_name = cq.get("cq_name", "Unknown")
    sparql = cq.get("sparql_text", "")
    mt_iri = cq.get("microtheory_iri", "")
    
    print(f"\n🧪 Testing CQ: {cq_name}")
    print(f"   MT: {mt_iri}")
    
    if not sparql:
        print("   ❌ No SPARQL query")
        return {"passed": False, "reason": "No SPARQL query"}
    
    # Show the query
    print(f"\n   Full Query:")
    print(sparql)
    
    # Extract class IDs from query for debugging
    if ":Class" in sparql:
        print(f"\n   Class IDs used in query:")
        for line in sparql.split("\n"):
            if ":Class" in line:
                print(f"      {line.strip()}")
    
    # Run the query
    try:
        # Query Fuseki directly
        fuseki_url = "http://localhost:3030/odras/query"
        sparql_client = httpx.Client(timeout=TIMEOUT)
        
        response = sparql_client.post(
            fuseki_url,
            content=sparql,
            headers={"Content-Type": "application/sparql-query"}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Query failed: {response.status_code}")
            return {"passed": False, "reason": f"Query failed: {response.status_code}"}
        
        results = response.json()
        bindings = results.get("results", {}).get("bindings", [])
        
        print(f"\n   📊 Results: {len(bindings)} rows")
        
        if bindings:
            print(f"   ✅ Query returned data!")
            for i, binding in enumerate(bindings[:3]):  # Show first 3 rows
                print(f"      Row {i+1}: {binding}")
        else:
            print(f"   ⚠️  Query returned no rows")
        
        return {"passed": len(bindings) > 0, "row_count": len(bindings)}
        
    except Exception as e:
        print(f"   ❌ Error running query: {e}")
        return {"passed": False, "reason": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_cqmt_ontology.py <project_id> [graph_iri]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    graph_iri = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not graph_iri:
        graph_iri = f"https://xma-adt.usnc.mil/odras/core/{project_id}/ontologies/bseo-v1"
    
    print("=" * 70)
    print("CQMT Ontology Testing Script")
    print("=" * 70)
    
    client = httpx.Client(timeout=TIMEOUT)
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)
    
    # Get ontology classes
    classes = get_ontology_classes(client, graph_iri)
    
    if not classes:
        print("\n❌ No classes found in ontology")
        sys.exit(1)
    
    # Get CQs
    cqs = get_cqs(client, project_id)
    
    if not cqs:
        print("\n❌ No CQs found")
        sys.exit(1)
    
    # Test each CQ
    print("\n" + "=" * 70)
    print("Testing CQs")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for cq in cqs:
        result = test_cq(client, cq, graph_iri)
        if result.get("passed"):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 70)

if __name__ == "__main__":
    main()
