#!/usr/bin/env python3
"""
Complete CQ/MT Generation Script with Cleanup:
1. Clears existing CQs and MTs for fresh start
2. Generates basic entity identification CQs
3. Generates Gruninger's enterprise engineering CQs
4. Requires data in CQs (min_rows > 0)
5. No hardcoded UUIDs

Usage:
    python scripts/generate_cqmt_from_ontology_complete.py <project_id> [--graph-iri <iri>] [--ontology-name <name>]
"""

import httpx
import json
import sys
import argparse
from typing import Dict, List, Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0

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

def get_project_ontologies(client: httpx.Client, project_id: str) -> List[Dict[str, Any]]:
    """Get all ontologies for a project."""
    print(f"📚 Fetching ontologies for project {project_id}...")
    
    response = client.get(f"{BASE_URL}/api/ontologies", params={"project": project_id})
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch ontologies: {response.status_code}")
        return []
    
    data = response.json()
    ontologies = data.get("ontologies", [])
    print(f"✅ Found {len(ontologies)} ontologies")
    return ontologies

def get_ontology_details(client: httpx.Client, graph_iri: str) -> Dict[str, Any]:
    """Get detailed ontology structure."""
    print(f"🔍 Fetching ontology details...")
    
    response = client.get(f"{BASE_URL}/api/ontology", params={"graph": graph_iri}, follow_redirects=True)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch ontology details: {response.status_code}")
        return {}
    
    data = response.json()
    return data.get("data", {})

def wrap_query_in_graph(sparql: str, graph_iri: str) -> str:
    """Wrap a SPARQL query in a GRAPH clause."""
    # Find the WHERE clause
    if "WHERE {" in sparql:
        parts = sparql.split("WHERE {", 1)
        # Remove trailing closing brace from parts[1] if present
        query_body = parts[1].rstrip()
        if query_body.endswith("}"):
            query_body = query_body[:-1].rstrip()
        return f"{parts[0]}WHERE {{\n    GRAPH <{graph_iri}> {{\n{query_body}\n    }}\n}}" 
    return sparql

def analyze_ontology(ontology_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze ontology structure."""
    print("🔬 Analyzing ontology structure...")
    
    analysis = {
        "classes": [],
        "object_properties": [],
        "relationships": []
    }
    
    # Handle nodes/edges format (from /api/ontology)
    nodes = ontology_data.get("nodes", [])
    edges = ontology_data.get("edges", [])
    
    if nodes:
        # Process nodes to extract classes
        for node in nodes:
            node_data = node.get("data", {})
            node_type = node_data.get("type")
            
            if node_type == "class":
                # Extract ID from node.data.id or node.data.name
                class_id = node_data.get("id") or node_data.get("name")
                class_label = node_data.get("label")
                analysis["classes"].append({
                    "id": class_id,
                    "label": class_label
                })
            elif node_type == "objectProperty":
                prop_info = {
                    "id": node_data.get("id"),
                    "label": node_data.get("label"),
                    "domain": None,
                    "range": None
                }
                analysis["object_properties"].append(prop_info)
    
    # Process edges to find relationships
    for edge in edges:
        edge_data = edge.get("data", {})
        if edge_data.get("type") == "objectProperty":
            rel_info = {
                "source": edge_data.get("source"),
                "target": edge_data.get("target"),
                "predicate": edge_data.get("predicate"),
                "label": edge_data.get("label")
            }
            analysis["relationships"].append(rel_info)
    
    # Fallback: Handle classes/object_properties format (from other endpoints)
    if not nodes:
        classes = ontology_data.get("classes", [])
        object_properties = ontology_data.get("object_properties", [])
        
        for cls in classes:
            # API returns "name" field, use it as "id"
            analysis["classes"].append({
                "id": cls.get("id") or cls.get("name"),
                "label": cls.get("label")
            })
        
        for prop in object_properties:
            prop_info = {
                "id": prop.get("id") or prop.get("name"),
                "label": prop.get("label"),
                "domain": prop.get("domain"),
                "range": prop.get("range")
            }
            analysis["object_properties"].append(prop_info)
            
            if prop_info["domain"] and prop_info["range"]:
                analysis["relationships"].append(prop_info)
    
    print(f"✅ Found {len(analysis['classes'])} classes, {len(analysis['object_properties'])} properties")
    return analysis

def cleanup_existing_cqs_and_mts(client: httpx.Client, project_id: str):
    """Delete all existing CQs and MTs for a clean start."""
    print("\n🧹 Cleaning up existing CQs and MTs...")
    
    # Get all CQs
    cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
    if cqs_response.status_code == 200:
        cqs = cqs_response.json()
        print(f"   Found {len(cqs)} existing CQs")
        
        for cq in cqs:
            cq_id = cq.get("id")
            if cq_id:
                delete_response = client.delete(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
                if delete_response.status_code in [200, 204]:
                    print(f"   ✅ Deleted CQ: {cq.get('cq_name')}")
    
    # Get all MTs
    mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
    if mts_response.status_code == 200:
        mts = mts_response.json()
        print(f"   Found {len(mts)} existing MTs")
        
        for mt in mts:
            mt_id = mt.get("id")
            if mt_id:
                delete_response = client.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
                if delete_response.status_code in [200, 204]:
                    print(f"   ✅ Deleted MT: {mt.get('label')}")
    
    print("✅ Cleanup complete\n")

def create_microtheory(client: httpx.Client, project_id: str, label: str, description: str, set_default: bool = False) -> Optional[str]:
    """Create a microtheory."""
    print(f"🧪 Creating microtheory: {label}...")
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
        json={"label": label, "description": description, "setDefault": set_default}
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create microtheory: {response.status_code}")
        print(response.text)
        return None
    
    mt_data = response.json()
    mt_iri = mt_data.get("data", {}).get("iri") or mt_data.get("iri")
    print(f"✅ Created microtheory: {mt_iri}")
    return mt_iri

def create_competency_question(client: httpx.Client, project_id: str, mt_iri: str, 
                               cq_name: str, problem_text: str, sparql_text: str, 
                               required_columns: List[str], min_rows: int = 1) -> Optional[str]:
    """Create a competency question."""
    print(f"❓ Creating CQ: {cq_name}...")
    
    # DON'T wrap in GRAPH clause - the SPARQLRunner will wrap in the microtheory GRAPH clause
    # If individuals are in the ontology graph, they need to be synced to the microtheory
    # Otherwise, queries will look in empty microtheory graph
    
    response = client.post(
        f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
        json={
            "cq_name": cq_name,
            "problem_text": problem_text,
            "sparql_text": sparql_text,
            "contract_json": {
                "require_columns": required_columns,
                "min_rows": min_rows  # Require at least 1 row
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
    cq_id = cq_data.get("data", {}).get("id") or cq_data.get("id")
    print(f"✅ Created CQ: {cq_id}")
    return cq_id

def generate_basic_cqs(client: httpx.Client, project_id: str, mt_iri: str, base_uri: str, analysis: Dict[str, Any]) -> List[Dict]:
    """Generate basic entity identification CQs."""
    print("\n📋 Generating Entity Identification CQs...")
    
    cqs = []
    
    for cls in analysis["classes"]:
        class_label = cls["label"]
        class_id = cls["id"]
        
        cq_name = f"List all {class_label}s"
        problem_text = f"What {class_label.lower()}s exist in the system?"
        
        sparql = f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?instance ?instanceName WHERE {{
    ?instance rdf:type :{class_id} .
    ?instance :name ?instanceName .
}}
"""
        
        cq_id = create_competency_question(
            client, project_id, mt_iri, cq_name, problem_text, sparql,
            ["instance", "instanceName"], min_rows=1
        )
        
        if cq_id:
            cqs.append({"name": cq_name, "id": cq_id})
    
    return cqs

def generate_gruninger_cqs(client: httpx.Client, project_id: str, mt_iri: str, base_uri: str, analysis: Dict[str, Any]) -> List[Dict]:
    """Generate Gruninger's 6 enterprise engineering CQ patterns."""
    print("\n🎯 Generating Gruninger's Enterprise Engineering CQs...")
    
    cqs = []
    
    # Find class IDs dynamically (case-insensitive match)
    class_map = {}
    print(f"   Debug: analysis classes: {[(c.get('label'), c.get('id')) for c in analysis['classes']]}")
    
    for cls in analysis["classes"]:
        label = cls.get("label", "")
        label_lower = label.lower()
        # Remove trailing 's' for matching
        label_singular = label_lower.rstrip('s')
        class_map[label_lower] = cls["id"]
        class_map[label_singular] = cls["id"]
    
    # Get class IDs safely
    requirement_class = class_map.get("requirement", "Class1")
    component_class = class_map.get("component", "Class2")
    constraint_class = class_map.get("constraint", "Class3")
    process_class = class_map.get("process", "Class6")
    function_class = class_map.get("function", "Class5")
    
    print(f"   Debug: class_map keys: {list(class_map.keys())}")
    print(f"   Debug: requirement={requirement_class}, component={component_class}, process={process_class}")
    
    # 1. TEMPORAL PROJECTION
    if process_class:
        temporal_cq = create_competency_question(
            client, project_id, mt_iri,
            "Temporal Projection: What processes exist at different times?",
            "Given actions at different times, what are properties of processes at arbitrary points in time?",
            f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?process ?processName WHERE {{
    ?process rdf:type :{process_class} .
    ?process :name ?processName .
}}
""",
            ["process", "processName"], min_rows=1
        )
        if temporal_cq:
            cqs.append({"name": "Temporal Projection", "id": temporal_cq})
    
    # 2. PLANNING AND SCHEDULING
    planning_cq = create_competency_question(
        client, project_id, mt_iri,
        "Planning: What components satisfy requirements?",
        "What sequence of components achieves system requirements?",
        f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?requirement ?requirementName ?component ?componentName WHERE {{
    ?requirement rdf:type :{requirement_class} .
    ?requirement :name ?requirementName .
    ?requirement :deploys ?component .
    ?component rdf:type :{component_class} .
    ?component :name ?componentName .
}}
""",
        ["requirement", "requirementName", "component", "componentName"], min_rows=1
    )
    if planning_cq:
        cqs.append({"name": "Planning and Scheduling", "id": planning_cq})
    
    # 3. BENCHMARKING
    benchmarking_cq = create_competency_question(
            client, project_id, mt_iri,
            "Benchmarking: What requirements have constraints?",
            "Can requirements be satisfied while meeting all constraints?",
            f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?requirement ?requirementName ?constraint ?constraintName WHERE {{
    ?requirement rdf:type :{requirement_class} .
    ?requirement :name ?requirementName .
    ?requirement :has_constraint ?constraint .
    ?constraint rdf:type :{constraint_class} .
    ?constraint :name ?constraintName .
}}
""",
            ["requirement", "requirementName", "constraint", "constraintName"], min_rows=1
        )
    if benchmarking_cq:
        cqs.append({"name": "Benchmarking", "id": benchmarking_cq})
    
    # 4. HYPOTHETICAL REASONING
    hypothetical_cq = create_competency_question(
            client, project_id, mt_iri,
            "Hypothetical: What functions do components enable?",
            "What are the effects if system components change?",
            f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?component ?componentName ?function ?functionName WHERE {{
    ?component rdf:type :{component_class} .
    ?component :name ?componentName .
    ?component :performs ?process .
    ?process :realizes ?function .
    ?function rdf:type :{function_class} .
    ?function :name ?functionName .
}}
""",
            ["component", "componentName", "function", "functionName"], min_rows=1
        )
    if hypothetical_cq:
        cqs.append({"name": "Hypothetical Reasoning", "id": hypothetical_cq})
    
    # 5. EXECUTION MONITORING
    monitoring_cq = create_competency_question(
            client, project_id, mt_iri,
            "Monitoring: What processes are supported by what components?",
            "What components support which processes in execution?",
            f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?component ?componentName ?process ?processName WHERE {{
    ?component rdf:type :{component_class} .
    ?component :name ?componentName .
    ?component :performs ?process .
    ?process rdf:type :{process_class} .
    ?process :name ?processName .
}}
""",
            ["component", "componentName", "process", "processName"], min_rows=1
        )
    if monitoring_cq:
        cqs.append({"name": "Execution Monitoring", "id": monitoring_cq})
    
    # 6. CONSTRAINT VERIFICATION
    constraint_cq = create_competency_question(
            client, project_id, mt_iri,
            "Constraint Verification: What requirements have constraints?",
            "What constraints apply to which requirements?",
            f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?requirement ?requirementName ?constraint ?constraintName WHERE {{
    ?requirement rdf:type :{requirement_class} .
    ?requirement :name ?requirementName .
    ?requirement :has_constraint ?constraint .
    ?constraint :name ?constraintName .
}}
""",
            ["requirement", "requirementName", "constraint", "constraintName"], min_rows=1
        )
    if constraint_cq:
        cqs.append({"name": "Constraint Verification", "id": constraint_cq})
    
    return cqs

def populate_microtheory_with_sample_data(mt_iri: str, base_uri: str, analysis: Dict[str, Any]):
    """Populate microtheory with sample data via Fuseki."""
    print(f"💉 Populating microtheory with sample data...")
    
    # Build class name map
    class_map = {}
    for cls in analysis["classes"]:
        label = cls.get("label", "").lower()
        class_id = cls.get("id", "")
        class_map[label] = class_id
    
    # Get class IDs
    requirement_class = class_map.get("requirement", "")
    component_class = class_map.get("component", "")
    constraint_class = class_map.get("constraint", "")
    interface_class = class_map.get("interface", "")
    function_class = class_map.get("function", "")
    process_class = class_map.get("process", "")
    
    fuseki_url = "http://localhost:3030/odras"
    
    update_query = f"""
PREFIX : <{base_uri}#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{mt_iri}> {{
        # Sample Requirements
        :req1 rdf:type :{requirement_class} ;
            rdfs:label "Endurance Requirement" .
        
        :req2 rdf:type :{requirement_class} ;
            rdfs:label "Payload Requirement" .
        
        # Sample Components
        :comp1 rdf:type :{component_class} ;
            rdfs:label "Sensor Module" .
        
        :comp2 rdf:type :{component_class} ;
            rdfs:label "Control Unit" .
        
        # Sample Constraints
        :const1 rdf:type :{constraint_class} ;
            rdfs:label "Weight Limit" .
        
        # Sample Interfaces
        :intf1 rdf:type :{interface_class} ;
            rdfs:label "Data Interface" .
        
        # Sample Functions
        :func1 rdf:type :{function_class} ;
            rdfs:label "Data Processing" .
        
        # Sample Processes
        :proc1 rdf:type :{process_class} ;
            rdfs:label "Process Data" .
        
        # Sample Relationships
        :req1 :deploys :comp1 .
        :req1 :has_constraint :const1 .
        :comp1 :has_interface :intf1 .
        :comp1 :performs :proc1 .
        :proc1 :realizes :func1 .
    }}
}}
"""
    
    try:
        response = httpx.post(
            f"{fuseki_url}/update",
            data=update_query,
            headers={"Content-Type": "application/sparql-update"},
            timeout=30.0
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Populated microtheory with sample data")
        else:
            print(f"⚠️  Failed to populate: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"⚠️  Error populating: {e}")

def main():
    parser = argparse.ArgumentParser(description="Complete CQ/MT Generation with Cleanup")
    parser.add_argument("project_id", help="Project UUID")
    parser.add_argument("--graph-iri", help="Specific ontology graph IRI")
    parser.add_argument("--ontology-name", help="Ontology name filter")
    parser.add_argument("--username", default="jdehart", help="Username for login")
    
    args = parser.parse_args()
    
    print("🚀 Complete CQ/MT Generation")
    print("=" * 60)
    print(f"📋 Project ID: {args.project_id}")
    print(f"👤 Username: {args.username}")
    if args.graph_iri:
        print(f"📚 Graph IRI: {args.graph_iri}")
    if args.ontology_name:
        print(f"🔍 Ontology Name: {args.ontology_name}")
    print("=" * 60)
    
    # Login
    with httpx.Client() as client:
        token = login(client, args.username)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(headers=headers, timeout=TIMEOUT) as client:
        # Get ontologies
        ontologies = get_project_ontologies(client, args.project_id)
        
        if not ontologies:
            print("❌ No ontologies found")
            sys.exit(1)
        
        # Find target ontology
        target_ontology = None
        if args.ontology_name:
            for onto in ontologies:
                if args.ontology_name.lower() in onto.get("label", "").lower():
                    target_ontology = onto
                    break
        elif args.graph_iri:
            for onto in ontologies:
                if onto.get("graphIri") == args.graph_iri:
                    target_ontology = onto
                    break
        else:
            target_ontology = ontologies[0]
        
        if not target_ontology:
            print("❌ Target ontology not found")
            sys.exit(1)
        
        graph_iri = target_ontology.get("graphIri")
        ontology_name = target_ontology.get("label", "Ontology")
        
        print(f"\n✅ Selected: {ontology_name} ({graph_iri})")
        
        # Cleanup existing CQs and MTs
        cleanup_existing_cqs_and_mts(client, args.project_id)
        
        # Get ontology details
        ontology_data = get_ontology_details(client, graph_iri)
        
        if not ontology_data:
            print("❌ Failed to retrieve ontology")
            sys.exit(1)
        
        # Analyze
        analysis = analyze_ontology(ontology_data)
        
        if not analysis["classes"]:
            print("❌ No classes found")
            sys.exit(1)
        
        # Create microtheory
        base_uri = graph_iri.rstrip('#').rstrip('/')
        mt_iri = create_microtheory(
            client, args.project_id,
            f"{ontology_name} Baseline",
            f"Baseline microtheory for {ontology_name}",
            set_default=True
        )
        
        if not mt_iri:
            print("❌ Failed to create microtheory")
            sys.exit(1)
        
        # Don't populate fake sample data - CQs will query real individuals from the ontology
        # populate_microtheory_with_sample_data(mt_iri, base_uri, analysis)
        
        # Generate CQs
        basic_cqs = generate_basic_cqs(client, args.project_id, mt_iri, base_uri, analysis)
        gruninger_cqs = generate_gruninger_cqs(client, args.project_id, mt_iri, base_uri, analysis)
        
        # Sync DAS individuals to microtheory so CQs can find them
        print("\n📥 Syncing DAS individuals to microtheory...")
        try:
            import subprocess
            sync_result = subprocess.run(
                ["python", "scripts/sync_das_individuals_to_fuseki.py", args.project_id, graph_iri],
                capture_output=True,
                text=True
            )
            if sync_result.returncode == 0:
                print("✅ Synced individuals to microtheory")
            else:
                print(f"⚠️  Sync failed: {sync_result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not sync individuals: {e}")
            print("   Run manually: python scripts/sync_das_individuals_to_fuseki.py <project_id> <graph_iri>")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Complete CQ/MT Generation Complete!")
        print("=" * 60)
        print(f"\n📚 Ontology: {ontology_name}")
        print(f"🔗 Graph IRI: {graph_iri}")
        print(f"\n🧪 Microtheory: {mt_iri}")
        print(f"\n❓ Basic CQs created: {len(basic_cqs)}")
        for cq in basic_cqs:
            print(f"   - {cq['name']}: {cq['id']}")
        
        print(f"\n❓ Gruninger CQs created: {len(gruninger_cqs)}")
        for cq in gruninger_cqs:
            print(f"   - {cq['name']}: {cq['id']}")
        
        print(f"\n🌐 View at: http://localhost:8000/app?project={args.project_id}&wb=cqmt")
        
        print("\n📊 Next Steps:")
        print("   1. Populate individuals using the Ontology Workbench")
        print("   2. Add relationships between individuals")
        print("   3. Run CQs to see actual results")
        print("   4. Example query: 'What processes are supported by what components?'")
        print("   5. CQs require min_rows=1, so they will show failures until data is added")

if __name__ == "__main__":
    main()
