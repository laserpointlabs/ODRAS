#!/usr/bin/env python3
"""
Test script to create a project, ontology, CQs, and Microtheories for CQ/MT Workbench testing.
This script ensures a clean slate by deleting any existing CQ/MT test data before creating new data.
"""

import httpx
import json
import sys
import time

BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = "CQ/MT Test Project"
TIMEOUT = 60.0  # 60 second timeout

def get_existing_test_project(client: httpx.Client) -> Optional[str]:
    """Get existing test project if it exists."""
    print("🔍 Checking for existing test project...")
    
    # Get all projects
    response = client.get(f"{BASE_URL}/api/projects")
    if response.status_code != 200:
        print(f"⚠️  Could not fetch projects: {response.status_code}")
        return None
    
    projects_data = response.json()
    projects = projects_data.get("projects", [])
    
    # Find test project
    for project in projects:
        if project.get("name") == TEST_PROJECT_NAME:
            project_id = project.get("project_id")
            print(f"✅ Found existing test project: {project_id}")
            return project_id
    
    print("ℹ️  No existing test project found")
    return None

def create_test_project(client: httpx.Client) -> str:
    """Create a NEW test project and return its UUID."""
    print("📁 Creating NEW test project...")
    
    response = client.post(
        f"{BASE_URL}/api/projects",
        json={
            "name": TEST_PROJECT_NAME,
            "description": "Test project for Competency Questions and Microtheories"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create project: {response.status_code}")
        print(response.text)
        return None
    
    project_data = response.json()
    # Handle nested response
    if "project" in project_data:
        project_id = project_data["project"].get("project_id")
    else:
        project_id = project_data.get("project_id") or project_data.get("id")
    
    print(f"✅ Created project with UUID: {project_id}")
    return project_id

def create_test_ontology(client: httpx.Client, project_id: str) -> str:
    """Create a test ontology."""
    print("📚 Creating test ontology...")
    
    # First create the ontology structure
    create_response = client.post(
        f"{BASE_URL}/api/ontologies",
        json={
            "project": project_id,
            "name": "test-ontology",
            "label": "Test Ontology",
            "is_reference": False
        }
    )
    
    if create_response.status_code not in [200, 201]:
        print(f"❌ Failed to create ontology: {create_response.status_code}")
        print(create_response.text)
        return None
    
    ontology_data = create_response.json()
    graph_iri = ontology_data.get("graphIri")
    
    if not graph_iri:
        print(f"❌ No graph IRI returned from ontology creation")
        return None
    
    print(f"✅ Created ontology structure: {graph_iri}")
    
    # Extract the base URI from the graph IRI to use as the ontology namespace
    base_uri = graph_iri.rstrip('#').rstrip('/')
    
    # Now add the content using the save endpoint with proper namespacing
    ontology_content = f"""
@prefix : <{base_uri}#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

:Aircraft a owl:Class ;
    rdfs:label "Aircraft" ;
    rdfs:comment "A flying vehicle" .

:FighterJet a owl:Class ;
    rdfs:subClassOf :Aircraft ;
    rdfs:label "Fighter Jet" ;
    rdfs:comment "A military fighter aircraft" .

:TransportPlane a owl:Class ;
    rdfs:subClassOf :Aircraft ;
    rdfs:label "Transport Plane" ;
    rdfs:comment "A cargo transport aircraft" .

:hasSpeed a owl:DatatypeProperty ;
    rdfs:label "has speed" ;
    rdfs:comment "The speed capability of an aircraft" .

:hasCapacity a owl:DatatypeProperty ;
    rdfs:label "has capacity" ;
    rdfs:comment "The passenger capacity of an aircraft" .

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
    
    # Save the ontology content
    save_response = client.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": graph_iri},
        content=ontology_content,
        headers={"Content-Type": "text/turtle"}
    )
    
    if save_response.status_code not in [200, 201]:
        print(f"⚠️  Failed to save ontology content: {save_response.status_code}")
        print(save_response.text)
    else:
        print(f"✅ Saved ontology content to: {graph_iri}")
    
    return graph_iri

def create_microtheory(client: httpx.Client, project_id: str, label: str, set_default: bool = False) -> str:
    """Create a microtheory."""
    print(f"🧪 Creating microtheory: {label}...")
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
        headers={"Content-Type": "application/json"},
        json={
            "label": label,
            "description": f"Test microtheory: {label}",
            "setDefault": set_default
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create microtheory: {response.status_code}")
        print(response.text)
        return None
    
    mt_data = response.json()
    # Handle nested response
    if "data" in mt_data:
        mt_id = mt_data["data"].get("id")
        mt_iri = mt_data["data"].get("iri")
    else:
        mt_id = mt_data.get("id")
        mt_iri = mt_data.get("iri")
    print(f"✅ Created microtheory: {mt_id} ({mt_iri})")
    return mt_iri

def inject_test_data_into_microtheory(client: httpx.Client, mt_iri: str, graph_iri: str):
    """Inject test data from the ontology into the microtheory."""
    print(f"💉 Injecting test data into microtheory: {mt_iri}")
    
    # Use SPARQL UPDATE to copy data from the ontology graph to the microtheory
    base_uri = graph_iri.rstrip('#').rstrip('/')
    
    # Create test data directly in the microtheory using the same namespace
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
    
    # Execute the update via Fuseki
    fuseki_url = "http://localhost:3030/odras"
    update_url = f"{fuseki_url}/update"
    
    try:
        response = httpx.post(
            update_url,
            data=update_query,
            headers={"Content-Type": "application/sparql-update"},
            timeout=30.0
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Injected test data into microtheory")
        else:
            print(f"⚠️  Failed to inject data: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"⚠️  Error injecting data: {e}")

def create_competency_question(client: httpx.Client, project_id: str, mt_iri: str, name: str, sparql: str, problem: str, graph_iri: str) -> str:
    """Create a competency question."""
    print(f"❓ Creating CQ: {name}...")
    
    # Extract base URI for namespace
    base_uri = graph_iri.rstrip('#').rstrip('/')
    
    # Determine expected columns from the SPARQL query
    if "aircraft" in sparql and "label" in sparql:
        columns = ["aircraft", "label"]
    else:
        columns = ["aircraft", "type"]
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
        headers={"Content-Type": "application/json"},
        json={
            "cq_name": name,
            "problem_text": problem,
            "sparql_text": sparql,
            "contract_json": {
                "require_columns": columns,
                "min_rows": 1
            },
            "mt_iri_default": mt_iri,
            "status": "active"
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create CQ: {response.status_code}")
        print(response.text)
        return None
    
    cq_data = response.json()
    # Handle nested response
    if "data" in cq_data:
        cq_id = cq_data["data"].get("id")
    else:
        cq_id = cq_data.get("id")
    print(f"✅ Created CQ: {cq_id}")
    return cq_id

def main():
    """Main test execution."""
    print("🚀 Starting CQ/MT Test Setup")
    print("=" * 60)
    
    # Login
    print("🔐 Logging in...")
    with httpx.Client() as client:
        login_response = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"},
            timeout=TIMEOUT
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            sys.exit(1)
        
        login_data = login_response.json()
        token = login_data.get("access_token") or login_data.get("token")
        print(f"✅ Logged in successfully (token length: {len(token) if token else 0})")
    
    # Set auth header for subsequent requests
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(headers=headers, timeout=TIMEOUT) as client:
        # 1. Clean up ALL existing test data
        cleanup_existing_test_data(client)
        time.sleep(1)
        
        # 2. Create NEW project and capture its UUID
        project_id = create_test_project(client)
        if not project_id:
            print("❌ Failed to create project")
            sys.exit(1)
        print(f"📋 Project UUID captured: {project_id}")
        
        time.sleep(1)
        
        # 3. Create ontology using the project UUID
        graph_iri = create_test_ontology(client, project_id)
        if not graph_iri:
            print("❌ Failed to create ontology")
            sys.exit(1)
        
        time.sleep(1)
        
        # 4. Create microtheories using the project UUID
        baseline_mt_iri = create_microtheory(client, project_id, "Baseline", set_default=True)
        test_mt_iri = create_microtheory(client, project_id, "Test Data", set_default=False)
        
        if not baseline_mt_iri or not test_mt_iri:
            print("❌ Failed to create microtheories")
            sys.exit(1)
        
        time.sleep(1)
        
        # 3a. Inject test data into microtheories
        inject_test_data_into_microtheory(client, baseline_mt_iri, graph_iri)
        inject_test_data_into_microtheory(client, test_mt_iri, graph_iri)
        
        time.sleep(1)
        
        # 5. Create competency questions using the project UUID
        # Extract base URI for namespace in SPARQL queries
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
        
        cq1_id = create_competency_question(
            client, project_id, baseline_mt_iri,
            "List all aircraft",
            cq1_sparql,
            "What aircraft are available in the system?",
            graph_iri
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
        
        cq2_id = create_competency_question(
            client, project_id, baseline_mt_iri,
            "List fighter jets",
            cq2_sparql,
            "What fighter jets are available?",
            graph_iri
        )
        
        if not cq1_id or not cq2_id:
            print("❌ Failed to create competency questions")
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("✅ CQ/MT Test Setup Complete!")
        print("=" * 60)
        print(f"\n📋 Project ID: {project_id}")
        print(f"📚 Ontology Graph IRI: {graph_iri}")
        print(f"🧪 Microtheories:")
        print(f"   - Baseline: {baseline_mt_iri}")
        print(f"   - Test Data: {test_mt_iri}")
        print(f"❓ Competency Questions:")
        print(f"   - List all aircraft: {cq1_id}")
        print(f"   - List fighter jets: {cq2_id}")
        print(f"\n🌐 Test URLs:")
        print(f"   Ontology: http://localhost:8000/app?project={project_id}&wb=ontology&graph={graph_iri}")
        print(f"   CQ/MT: http://localhost:8000/app?project={project_id}&wb=cqmt")
        print(f"\n💡 Select project '{project_id}' from the dropdown")
        print(f"\n📊 What to review:")
        print(f"   Ontology Workbench (first URL):")
        print(f"   - Test Ontology with Aircraft classes and instances")
        print(f"   - Classes: Aircraft, FighterJet, TransportPlane")
        print(f"   - Properties: hasSpeed, hasCapacity")
        print(f"   - Instances: F-22, F-35, C-130, C-17")
        print(f"\n   CQ/MT Workbench (second URL):")
        print(f"   - Microtheories: Baseline (default), Test Data")
        print(f"   - Competency Questions: List all aircraft, List fighter jets")
        
        # Test CQ execution
        print("\n" + "=" * 60)
        print("🧪 Testing CQ Execution")
        print("=" * 60)
        
        if cq1_id and baseline_mt_iri:
            test_cq_execution(client, cq1_id, baseline_mt_iri)
        
        print("\n✅ CQ/MT Test Suite Complete!")

def test_cq_execution(client: httpx.Client, cq_id: str, mt_iri: str):
    """Test executing a competency question."""
    print(f"\n▶️  Running CQ: {cq_id} against MT: {mt_iri}")
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/cqs/{cq_id}/run",
        json={
            "mt_iri": mt_iri,
            "params": {}
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ CQ executed successfully")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Results: {result.get('row_count', 0)} rows")
    else:
        print(f"❌ CQ execution failed: {response.status_code}")
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    main()
