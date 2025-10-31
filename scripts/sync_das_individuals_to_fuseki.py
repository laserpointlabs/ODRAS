#!/usr/bin/env python3
"""
Sync DAS-generated individuals from database to Fuseki so CQs can find them.
"""
import httpx
import sys
import json
from typing import Dict, List, Any

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

def get_db_individuals(client: httpx.Client, project_id: str, graph_iri: str, class_name: str) -> List[Dict[str, Any]]:
    """Get individuals from database for a class."""
    try:
        response = client.get(
            f"{BASE_URL}/api/individuals/{project_id}/individuals/{class_name}",
            params={"graph": graph_iri},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("individuals", [])
        else:
            print(f"⚠️  Failed to get {class_name} individuals: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️  Error getting {class_name} individuals: {e}")
        return []

def sync_individual_to_fuseki(mt_iri: str, ontology_graph_iri: str, class_name: str, individual: Dict[str, Any]):
    """Insert an individual into Fuseki microtheory."""
    fuseki_url = "http://localhost:3030/odras/update"
    
    instance_uri = individual.get("instance_uri")
    instance_name = individual.get("instance_name")
    properties = individual.get("properties", {})
    
    if not instance_uri:
        # Create a simple URI
        instance_uri = f"{ontology_graph_iri}#{instance_name}"
    
    # Build triples (use lowercase for Fuseki IRI)
    class_name_for_iri = class_name.lower()
    class_iri = f"<{ontology_graph_iri}#{class_name_for_iri}>"
    triples = [
        f"<{instance_uri}> rdf:type {class_iri} .",
        f"<{instance_uri}> rdfs:label \"{instance_name}\" ."
    ]
    
    # Add property triples
    for prop_name, prop_value in properties.items():
        prop_name_clean = prop_name.replace(" ", "")
        prop_iri = f"<{ontology_graph_iri}#{prop_name_clean}>"
        if isinstance(prop_value, str):
            # Escape quotes in strings
            prop_value_escaped = prop_value.replace('"', '\\"')
            triples.append(f"<{instance_uri}> {prop_iri} \"{prop_value_escaped}\" .")
        else:
            triples.append(f"<{instance_uri}> {prop_iri} {prop_value} .")
    
    # Build INSERT query - insert into MICROTHEORY graph, not ontology graph
    query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{mt_iri}> {{
        {' '.join(triples)}
    }}
}}
"""
    
    try:
        response = httpx.post(
            fuseki_url,
            content=query,
            headers={"Content-Type": "application/sparql-update"},
            timeout=30.0
        )
        
        if response.status_code in [200, 204]:
            return True
        else:
            print(f"⚠️  Failed to sync {instance_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Error syncing {instance_name}: {e}")
        return False

def extract_relationships_recursive(obj: Dict[str, Any], ontology_graph_iri: str, triples: List[str], relationship_count: List[int], instance_types: Dict[str, str], instance_names: Dict[str, str]):
    """Recursively extract relationships from configuration structure."""
    # Add this instance's type and name
    instance_id = obj.get("instanceId")
    instance_class = obj.get("class")
    properties = obj.get("properties", {})
    
    if instance_id and instance_class:
        instance_types[instance_id] = instance_class
    
    # Extract name from properties
    instance_name = properties.get("name") or properties.get("Name")
    if instance_id and instance_name:
        instance_names[instance_id] = instance_name
    
    relationships = obj.get("relationships", [])
    
    for rel in relationships:
        predicate = rel.get("property")  # Use "property" field
        targets = rel.get("targets", [])
        
        if not predicate or not targets:
            continue
        
        # Get source instance ID
        source_instance_id = obj.get("instanceId")
        if not source_instance_id:
            continue
        
        source_uri = f"{ontology_graph_iri}#{source_instance_id}"
        
        # Create relationship triples
        for target in targets:
            target_instance_id = target.get("instanceId")
            if not target_instance_id:
                continue
            
            target_uri = f"{ontology_graph_iri}#{target_instance_id}"
            
            # Build predicate IRI - use exact property name from ontology
            predicate_iri = f"<{ontology_graph_iri}#{predicate}>"
            
            triples.append(f"<{source_uri}> {predicate_iri} <{target_uri}> .")
            relationship_count[0] += 1
            
            # Recursively process nested relationships
            extract_relationships_recursive(target, ontology_graph_iri, triples, relationship_count, instance_types, instance_names)

def sync_relationships_from_configurations(client: httpx.Client, project_id: str, mt_iri: str, ontology_graph_iri: str):
    """Sync relationships from DAS configurations to Fuseki."""
    print("\n🔗 Syncing relationships from configurations...")
    
    try:
        # Get configurations
        resp = client.get(f"{BASE_URL}/api/configurations/{project_id}/configurations")
        if resp.status_code != 200:
            print("⚠️  Failed to get configurations")
            return 0
        
        configs_data = resp.json()
        configs = configs_data.get("configurations", [])
        
        if not configs:
            print("   No configurations found")
            return 0
        
        print(f"   Found {len(configs)} configurations")
        
        triples = []
        relationship_count = [0]  # Use list to modify in recursive function
        instance_types = {}  # Track instance types
        instance_names = {}  # Track instance names
        
        for config in configs:
            structure = config.get("structure", {})
            extract_relationships_recursive(structure, ontology_graph_iri, triples, relationship_count, instance_types, instance_names)
        
        # Add rdf:type and name triples for all instances found in relationships
        for instance_id, class_name in instance_types.items():
            instance_uri = f"{ontology_graph_iri}#{instance_id}"
            class_name_for_iri = class_name.lower()
            class_iri = f"<{ontology_graph_iri}#{class_name_for_iri}>"
            triples.append(f"<{instance_uri}> rdf:type {class_iri} .")
            
            # Add name if available
            if instance_id in instance_names:
                name_value = instance_names[instance_id]
                # Escape quotes in name
                name_escaped = name_value.replace('"', '\\"')
                triples.append(f"<{instance_uri}> <{ontology_graph_iri}#name> \"{name_escaped}\" .")
        
        if triples:
            # Insert all relationship triples
            fuseki_url = "http://localhost:3030/odras/update"
            query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{mt_iri}> {{
        {' '.join(triples)}
    }}
}}
"""
            
            response = httpx.post(
                fuseki_url,
                content=query,
                headers={"Content-Type": "application/sparql-update"},
                timeout=30.0
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Synced {relationship_count[0]} relationships to microtheory")
                return relationship_count[0]
            else:
                print(f"⚠️  Failed to sync relationships: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return 0
        else:
            print("   No relationships found in configurations")
            return 0
            
    except Exception as e:
        print(f"⚠️  Error syncing relationships: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/sync_das_individuals_to_fuseki.py <project_id> <graph_iri> [mt_iri]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    graph_iri = sys.argv[2]
    mt_iri = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("=" * 70)
    print("Sync DAS Individuals to Fuseki")
    print("=" * 70)
    print(f"Project: {project_id}")
    print(f"Ontology Graph: {graph_iri}")
    if mt_iri:
        print(f"Microtheory: {mt_iri}")
    print()
    
    # Login
    with httpx.Client() as client:
        token = login(client)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(headers=headers, timeout=TIMEOUT) as client:
        # Get default microtheory if not provided
        if not mt_iri:
            print("📋 Getting default microtheory...")
            mt_resp = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
            if mt_resp.status_code == 200:
                mts = mt_resp.json()
                default_mt = next((mt for mt in mts if mt.get("is_default")), None)
                if default_mt:
                    mt_iri = default_mt.get("iri")
                    print(f"✅ Using default microtheory: {mt_iri}")
                else:
                    print("❌ No default microtheory found")
                    sys.exit(1)
            else:
                print("❌ Failed to get microtheories")
                sys.exit(1)
        
        # Get all classes with individuals (use capitalized names)
        classes = ["Requirement", "Component", "Constraint", "Interface", "Function", "Process", "Paramter"]
        
        total_synced = 0
        
        for class_name in classes:
            print(f"\n📋 Processing {class_name}...")
            individuals = get_db_individuals(client, project_id, graph_iri, class_name)
            
            if not individuals:
                print(f"   No individuals found")
                continue
            
            print(f"   Found {len(individuals)} individuals")
            
            # Sync each individual
            synced = 0
            for ind in individuals:
                if sync_individual_to_fuseki(mt_iri, graph_iri, class_name, ind):
                    synced += 1
            
            print(f"   ✅ Synced {synced}/{len(individuals)} to microtheory")
            total_synced += synced
        
        # Sync relationships from configurations
        rel_count = sync_relationships_from_configurations(client, project_id, mt_iri, graph_iri)
        
        print("\n" + "=" * 70)
        print(f"✅ Complete! Synced {total_synced} individuals and {rel_count} relationships to microtheory")
        print("=" * 70)

if __name__ == "__main__":
    main()
