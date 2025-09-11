#!/usr/bin/env python3
"""
Load sample classes into ontologies for testing import functionality.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
PROJECT_ID = "6b705b95-3499-46a5-bb0e-d8559618732b"

# Sample classes to load
SAMPLE_CLASSES = {
    "my-ontology": [
        {"id": "Class1", "label": "Constraint", "type": "class"},
        {"id": "Class2", "label": "Requirement", "type": "class"},
        {"id": "Class3", "label": "Component", "type": "class"},
    ],
    "my-onto2": [
        {
            "id": "Class1",
            "label": "Constraint",
            "type": "class",
        },  # Same name as in my-ontology
        {"id": "Class4", "label": "Process", "type": "class"},
        {"id": "Class5", "label": "Function", "type": "class"},
    ],
}


def get_auth_token():
    """Get authentication token."""
    login_data = {"username": "admin", "password": "admin"}

    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None


def load_classes_to_ontology(ontology_name, classes, token):
    """Load classes into a specific ontology."""
    graph_iri = f"http://odras.local/onto/{PROJECT_ID}/{ontology_name}"

    # Create a simple ontology structure with the classes
    ontology_data = {"nodes": classes, "edges": []}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Save the ontology data
    response = requests.put(
        f"{BASE_URL}/api/ontology/?graph={graph_iri}",
        json=ontology_data,
        headers=headers,
    )

    if response.status_code == 200:
        print(f"✅ Successfully loaded {len(classes)} classes into {ontology_name}")
        return True
    else:
        print(
            f"❌ Failed to load classes into {ontology_name}: {response.status_code} - {response.text}"
        )
        return False


def verify_classes_loaded(ontology_name, token):
    """Verify that classes were loaded by querying them."""
    graph_iri = f"http://odras.local/onto/{PROJECT_ID}/{ontology_name}"

    sparql_query = f"""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?c ?label WHERE {{
        GRAPH <{graph_iri}> {{
            ?c a owl:Class .
            OPTIONAL {{ ?c rdfs:label ?label }}
        }}
    }}
    """

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(
        f"{BASE_URL}/api/ontology/sparql", json={"query": sparql_query}, headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        classes = result.get("results", {}).get("bindings", [])
        print(f"🔍 Found {len(classes)} classes in {ontology_name}:")
        for cls in classes:
            class_uri = cls.get("c", {}).get("value", "Unknown")
            label = cls.get("label", {}).get("value", "No label")
            print(f"   - {label} ({class_uri})")
        return len(classes) > 0
    else:
        print(
            f"❌ Failed to query classes in {ontology_name}: {response.status_code} - {response.text}"
        )
        return False


def main():
    print("🚀 Loading sample classes into ontologies...")

    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        sys.exit(1)

    print("✅ Authentication successful")

    # Load classes into each ontology
    success_count = 0
    for ontology_name, classes in SAMPLE_CLASSES.items():
        print(f"\n📝 Loading classes into {ontology_name}...")
        if load_classes_to_ontology(ontology_name, classes, token):
            success_count += 1

            # Verify the classes were loaded
            print(f"🔍 Verifying classes in {ontology_name}...")
            verify_classes_loaded(ontology_name, token)

    print(f"\n🎉 Successfully loaded classes into {success_count}/{len(SAMPLE_CLASSES)} ontologies")

    if success_count == len(SAMPLE_CLASSES):
        print("\n✅ All ontologies now have classes! You can now test the import functionality.")
        print("   - Both ontologies have a 'Constraint' class that should match")
        print("   - Try importing one ontology into the other to see class matching")
    else:
        print("\n❌ Some ontologies failed to load classes. Check the errors above.")


if __name__ == "__main__":
    main()
