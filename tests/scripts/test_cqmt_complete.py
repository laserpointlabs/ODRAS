#!/usr/bin/env python3
"""
Complete CQMT test script that creates fresh test data and validates it.
"""

import httpx
import json
import sys
import time

BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = "CQMT Test Project"
TIMEOUT = 60.0

def login() -> str:
    """Login and return auth token."""
    print("🔐 Logging in as jdehart...")
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "jdehart", "password": "jdehart123!"},
            timeout=TIMEOUT
        )
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            print(response.text)
            sys.exit(1)
        token = response.json().get("access_token") or response.json().get("token")
        print(f"✅ Logged in as jdehart")
        return token

def cleanup_all_test_data(client: httpx.Client):
    """Delete ALL test projects and their data."""
    print("\n🧹 STEP 1: Cleaning up ALL existing test data...")
    
    # Clean up for current user (das_service)
    deleted_count = _cleanup_projects_for_user(client)
    
    # Also try to clean up for jdehart user (already done above, but keeping for das_service cleanup)
    print("\n   Checking for remaining test projects...")
    try:
        jdehart_response = httpx.post(f"{BASE_URL}/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}, timeout=10)
        if jdehart_response.status_code == 200:
            jdehart_token = jdehart_response.json().get("access_token") or jdehart_response.json().get("token")
            jdehart_client = httpx.Client(headers={"Authorization": f"Bearer {jdehart_token}"}, timeout=60)
            deleted_count += _cleanup_projects_for_user(jdehart_client)
    except Exception as e:
        print(f"   ⚠️  Could not clean up jdehart projects: {e}")
    
    print(f"\n✅ Total cleanup: {deleted_count} project(s)")
    time.sleep(2)  # Wait for cleanup to propagate

def _cleanup_projects_for_user(client: httpx.Client) -> int:
    """Helper to clean up projects for a specific user."""
    response = client.get(f"{BASE_URL}/api/projects")
    if response.status_code != 200:
        return 0
    
    projects = response.json().get("projects", [])
    deleted_count = 0
    
    for project in projects:
        # Delete ANY project matching our test name pattern OR specifically named
        project_name = project.get("name", "")
        if TEST_PROJECT_NAME in project_name or "CQMT" in project_name or "CQ/MT" in project_name:
            project_id = project.get("project_id")
            print(f"   🗑️  Deleting project: {project_id}")
            
            # Delete CQs
            try:
                cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
                if cqs_response.status_code == 200:
                    cqs = cqs_response.json()
                    for cq in cqs:
                        cq_id = cq.get("id")
                        client.delete(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
                        print(f"      Deleted CQ: {cq_id}")
            except Exception as e:
                print(f"      Error deleting CQs: {e}")
            
            # Delete MTs
            try:
                mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
                if mts_response.status_code == 200:
                    mts = mts_response.json()
                    for mt in mts:
                        mt_id = mt.get("id")
                        client.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
                        print(f"      Deleted MT: {mt_id}")
            except Exception as e:
                print(f"      Error deleting MTs: {e}")
            
            # Delete ontologies FIRST before deleting project
            try:
                ontos_response = client.get(f"{BASE_URL}/api/ontologies?project={project_id}")
                if ontos_response.status_code == 200:
                    ontos = ontos_response.json().get("ontologies", [])
                    for onto in ontos:
                        graph_iri = onto.get("graphIri")
                        if graph_iri:
                            print(f"      Deleting ontology: {graph_iri}")
                            client.delete(f"{BASE_URL}/api/ontologies?graph={graph_iri}")
            except Exception as e:
                print(f"      Error deleting ontologies: {e}")
            
            # Delete project
            try:
                delete_response = client.delete(f"{BASE_URL}/api/projects/{project_id}")
                if delete_response.status_code in [200, 204]:
                    print(f"   ✅ Deleted project: {project_id}")
                    deleted_count += 1
            except Exception as e:
                print(f"   ⚠️  Error deleting project: {e}")
    
    return deleted_count

def create_fresh_project(client: httpx.Client) -> str:
    """Create a FRESH test project and return its UUID."""
    print("\n📁 STEP 2: Creating FRESH test project...")
    
    response = client.post(
        f"{BASE_URL}/api/projects",
        json={
            "name": TEST_PROJECT_NAME,
            "description": "Fresh test project for CQMT validation"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create project: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    project_data = response.json()
    # Handle nested response
    if "project" in project_data:
        project_id = project_data["project"].get("project_id")
    else:
        project_id = project_data.get("project_id") or project_data.get("id")
    
    if not project_id:
        print(f"❌ No project ID in response: {project_data}")
        sys.exit(1)
    
    print(f"✅ Created project with UUID: {project_id}")
    return project_id

def create_ontology(client: httpx.Client, project_id: str) -> str:
    """Create ontology in the project."""
    print("\n📚 STEP 3: Creating ontology...")
    
    response = client.post(
        f"{BASE_URL}/api/ontologies",
        json={
            "project": project_id,
            "name": "test-ontology",
            "label": "Test Ontology",
            "is_reference": False
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create ontology: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    ontology_data = response.json()
    graph_iri = ontology_data.get("graphIri")
    
    if not graph_iri:
        print(f"❌ No graph IRI returned")
        sys.exit(1)
    
    print(f"✅ Created ontology: {graph_iri}")
    
    # Add content
    base_uri = graph_iri.rstrip('#').rstrip('/')
    ontology_content = f"""
@prefix : <{base_uri}#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

:Aircraft a owl:Class ;
    rdfs:label "Aircraft" .

:FighterJet a owl:Class ;
    rdfs:subClassOf :Aircraft ;
    rdfs:label "Fighter Jet" .

:TransportPlane a owl:Class ;
    rdfs:subClassOf :Aircraft ;
    rdfs:label "Transport Plane" .

:hasSpeed a owl:DatatypeProperty ;
    rdfs:label "has speed" .

:hasCapacity a owl:DatatypeProperty ;
    rdfs:label "has capacity" .

:F22 a :FighterJet ;
    rdfs:label "F-22 Raptor" ;
    :hasSpeed "Mach 2.25" .

:F35 a :FighterJet ;
    rdfs:label "F-35 Lightning II" ;
    :hasSpeed "Mach 1.6" .

:C130 a :TransportPlane ;
    rdfs:label "C-130 Hercules" ;
    :hasCapacity "92 passengers" .

:C17 a :TransportPlane ;
    rdfs:label "C-17 Globemaster III" ;
    :hasCapacity "102 passengers" .
"""
    
    save_response = client.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": graph_iri},
        content=ontology_content,
        headers={"Content-Type": "text/turtle"}
    )
    
    if save_response.status_code in [200, 201]:
        print(f"✅ Saved ontology content")
    else:
        print(f"⚠️  Failed to save content: {save_response.status_code}")
    
    return graph_iri

def create_microtheory(client: httpx.Client, project_id: str, label: str, set_default: bool = False) -> str:
    """Create a microtheory."""
    print(f"   🧪 Creating microtheory: {label}...")
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
        json={
            "label": label,
            "setDefault": set_default
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"   ❌ Failed: {response.status_code}")
        print(response.text)
        return None
    
    mt_data = response.json()
    mt_iri = mt_data.get("iri") or (mt_data.get("data") or {}).get("iri")
    
    if mt_iri:
        print(f"   ✅ Created: {mt_iri}")
    return mt_iri

def inject_mt_data(client: httpx.Client, mt_iri: str, graph_iri: str):
    """Inject test data into microtheory."""
    base_uri = graph_iri.rstrip('#').rstrip('/')
    
    update_query = f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{mt_iri}> {{
        :F22 a :FighterJet ;
            rdfs:label "F-22 Raptor" ;
            :hasSpeed "Mach 2.25" .
        
        :F35 a :FighterJet ;
            rdfs:label "F-35 Lightning II" ;
            :hasSpeed "Mach 1.6" .
        
        :C130 a :TransportPlane ;
            rdfs:label "C-130 Hercules" ;
            :hasCapacity "92 passengers" .
        
        :C17 a :TransportPlane ;
            rdfs:label "C-17 Globemaster III" ;
            :hasCapacity "102 passengers" .
    }}
}}
"""
    
    fuseki_url = "http://localhost:3030/odras/update"
    try:
        response = httpx.post(
            fuseki_url,
            data=update_query,
            headers={"Content-Type": "application/sparql-update"},
            timeout=30.0
        )
        if response.status_code in [200, 204]:
            print(f"   ✅ Injected test data")
    except Exception as e:
        print(f"   ⚠️  Failed to inject data: {e}")

def create_cq(client: httpx.Client, project_id: str, mt_iri: str, name: str, sparql: str, problem: str) -> str:
    """Create a competency question."""
    print(f"   ❓ Creating CQ: {name}...")
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
        json={
            "cq_name": name,
            "problem_text": problem,
            "sparql_text": sparql,
            "params_json": {},  # Empty params dict - matches backend API
            "contract_json": {
                "require_columns": ["aircraft", "label"],
                "min_rows": 1
            },
            "mt_iri_default": mt_iri,
            "status": "active"
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"   ❌ Failed: {response.status_code}")
        print(response.text)
        return None
    
    cq_data = response.json()
    cq_id = cq_data.get("id") or (cq_data.get("data") or {}).get("id")
    
    if cq_id:
        print(f"   ✅ Created: {cq_id}")
    return cq_id

def validate_project(client: httpx.Client, project_id: str):
    """Validate all objects exist via API."""
    print("\n🔍 STEP 6: Validating project data via API...")
    
    # Check ontologies
    ontos_response = client.get(f"{BASE_URL}/api/ontologies?project={project_id}")
    ontos = ontos_response.json().get("ontologies", [])
    print(f"   Ontologies: {len(ontos)}")
    for onto in ontos:
        print(f"      - {onto.get('label')}: {onto.get('graphIri')}")
    
    # Check CQs
    cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
    cqs = cqs_response.json() if isinstance(cqs_response.json(), list) else []
    print(f"   CQs: {len(cqs)}")
    for cq in cqs:
        print(f"      - {cq.get('cq_name')}: {cq.get('id')}")
    
    # Check MTs
    mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
    mts = mts_response.json() if isinstance(mts_response.json(), list) else []
    print(f"   MTs: {len(mts)}")
    for mt in mts:
        print(f"      - {mt.get('label')}: {mt.get('iri')}")
    
    if len(ontos) == 0:
        print("   ❌ NO ONTOLOGIES FOUND!")
    if len(cqs) == 0:
        print("   ❌ NO CQs FOUND!")
    if len(mts) == 0:
        print("   ❌ NO MTs FOUND!")
    
    return len(ontos) > 0 and len(cqs) > 0 and len(mts) > 0

def main():
    print("=" * 60)
    print("🚀 CQMT Complete Test Suite")
    print("=" * 60)
    
    # Login
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(headers=headers, timeout=TIMEOUT) as client:
        # 1. Cleanup
        cleanup_all_test_data(client)
        
        # 2. Create project
        project_id = create_fresh_project(client)
        
        # 3. Create ontology
        graph_iri = create_ontology(client, project_id)
        
        # 4. Create microtheories
        print("\n🧪 STEP 4: Creating microtheories...")
        baseline_mt_iri = create_microtheory(client, project_id, "Baseline", set_default=True)
        test_mt_iri = create_microtheory(client, project_id, "Test Data", set_default=False)
        
        if not baseline_mt_iri or not test_mt_iri:
            print("❌ Failed to create microtheories")
            sys.exit(1)
        
        # Inject data
        print("\n💉 Injecting test data into microtheories...")
        inject_mt_data(client, baseline_mt_iri, graph_iri)
        inject_mt_data(client, test_mt_iri, graph_iri)
        
        # 5. Create CQs
        print("\n❓ STEP 5: Creating competency questions...")
        base_uri = graph_iri.rstrip('#').rstrip('/')
        
        cq1_sparql = f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?aircraft ?label WHERE {{
    ?aircraft rdf:type/rdfs:subClassOf* :Aircraft .
    ?aircraft rdfs:label ?label .
}}
"""
        
        cq1_id = create_cq(
            client, project_id, baseline_mt_iri,
            "List all aircraft",
            cq1_sparql,
            "What aircraft are available in the system?"
        )
        
        cq2_sparql = f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?aircraft ?label WHERE {{
    ?aircraft rdf:type :FighterJet .
    ?aircraft rdfs:label ?label .
}}
"""
        
        cq2_id = create_cq(
            client, project_id, baseline_mt_iri,
            "List fighter jets",
            cq2_sparql,
            "What fighter jets are available?"
        )
        
        if not cq1_id or not cq2_id:
            print("❌ Failed to create CQs")
            sys.exit(1)
        
        # 6. Validate
        is_valid = validate_project(client, project_id)
        
        # 7. Print URLs
        print("\n" + "=" * 60)
        print("🌐 BROWSER VERIFICATION URLs")
        print("=" * 60)
        print(f"\nProject UUID: {project_id}")
        print(f"\nOntology URL:")
        print(f"http://localhost:8000/app?project={project_id}&wb=ontology&graph={graph_iri}")
        print(f"\nCQ/MT URL:")
        print(f"http://localhost:8000/app?project={project_id}&wb=cqmt")
        print(f"\n💡 INSTRUCTIONS:")
        print(f"1. Copy one of the URLs above")
        print(f"2. Open in browser")
        print(f"3. Select '{TEST_PROJECT_NAME}' from the project dropdown")
        print(f"4. Click 'Ontologies' tab to see ontology")
        print(f"5. Click 'CQ/MT' tab to see CQs and MTs")
        
        if is_valid:
            print("\n✅ Test data created successfully!")
            print("✅ All objects exist via API")
            print("✅ Ready for browser verification")
        else:
            print("\n❌ Validation failed - objects missing")
            sys.exit(1)

if __name__ == "__main__":
    main()
