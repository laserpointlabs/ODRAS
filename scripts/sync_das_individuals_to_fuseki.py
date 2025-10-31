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

def sync_individual_to_fuseki(graph_iri: str, class_name: str, individual: Dict[str, Any]):
    """Insert an individual into Fuseki."""
    fuseki_url = "http://localhost:3030/odras/update"
    
    instance_uri = individual.get("instance_uri")
    instance_name = individual.get("instance_name")
    properties = individual.get("properties", {})
    
    if not instance_uri:
        # Create a simple URI
        instance_uri = f"{graph_iri}#{instance_name}"
    
    # Build triples (use lowercase for Fuseki IRI)
    class_name_for_iri = class_name.lower()
    class_iri = f"<{graph_iri}#{class_name_for_iri}>"
    triples = [
        f"<{instance_uri}> rdf:type {class_iri} .",
        f"<{instance_uri}> rdfs:label \"{instance_name}\" ."
    ]
    
    # Add property triples
    for prop_name, prop_value in properties.items():
        prop_name_clean = prop_name.replace(" ", "")
        prop_iri = f"<{graph_iri}#{prop_name_clean}>"
        if isinstance(prop_value, str):
            # Escape quotes in strings
            prop_value_escaped = prop_value.replace('"', '\\"')
            triples.append(f"<{instance_uri}> {prop_iri} \"{prop_value_escaped}\" .")
        else:
            triples.append(f"<{instance_uri}> {prop_iri} {prop_value} .")
    
    # Build INSERT query
    query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{graph_iri}> {{
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

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/sync_das_individuals_to_fuseki.py <project_id> <graph_iri>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    graph_iri = sys.argv[2]
    
    print("=" * 70)
    print("Sync DAS Individuals to Fuseki")
    print("=" * 70)
    print(f"Project: {project_id}")
    print(f"Graph: {graph_iri}")
    print()
    
    # Login
    with httpx.Client() as client:
        token = login(client)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(headers=headers, timeout=TIMEOUT) as client:
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
                if sync_individual_to_fuseki(graph_iri, class_name, ind):
                    synced += 1
            
            print(f"   ✅ Synced {synced}/{len(individuals)} to Fuseki")
            total_synced += synced
        
        print("\n" + "=" * 70)
        print(f"✅ Complete! Synced {total_synced} individuals to Fuseki")
        print("=" * 70)

if __name__ == "__main__":
    main()

