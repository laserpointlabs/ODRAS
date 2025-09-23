#!/usr/bin/env python3
"""
Add simple RDF classes directly to ontologies using SPARQL INSERT.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
PROJECT_ID = "6b705b95-3499-46a5-bb0e-d8559618732b"


def get_auth_token():
    """Get authentication token."""
    login_data = {"username": "admin", "password": "admin"}

    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None


def add_classes_to_ontology(ontology_name, token):
    """Add simple RDF classes to an ontology using SPARQL INSERT."""
    graph_iri = f"http://odras.local/onto/{PROJECT_ID}/{ontology_name}"

    # Create SPARQL INSERT query to add classes
    if ontology_name == "my-ontology":
        sparql_query = f"""INSERT DATA {{
            GRAPH <{graph_iri}> {{
                <{graph_iri}#Constraint> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Constraint> <http://www.w3.org/2000/01/rdf-schema#label> "Constraint" .

                <{graph_iri}#Requirement> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Requirement> <http://www.w3.org/2000/01/rdf-schema#label> "Requirement" .

                <{graph_iri}#Component> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Component> <http://www.w3.org/2000/01/rdf-schema#label> "Component" .
            }}
        }}"""
    else:  # my-onto2
        sparql_query = f"""INSERT DATA {{
            GRAPH <{graph_iri}> {{
                <{graph_iri}#Constraint> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Constraint> <http://www.w3.org/2000/01/rdf-schema#label> "Constraint" .

                <{graph_iri}#Process> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Process> <http://www.w3.org/2000/01/rdf-schema#label> "Process" .

                <{graph_iri}#Function> a <http://www.w3.org/2002/07/owl#Class> .
                <{graph_iri}#Function> <http://www.w3.org/2000/01/rdf-schema#label> "Function" .
            }}
        }}"""

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Execute the SPARQL INSERT
    response = requests.post(
        f"{BASE_URL}/api/ontology/sparql", json={"query": sparql_query}, headers=headers
    )

    if response.status_code == 200:
        print(f"✅ Successfully added classes to {ontology_name}")
        return True
    else:
        print(
            f"❌ Failed to add classes to {ontology_name}: {response.status_code} - {response.text}"
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
    print("🚀 Adding simple RDF classes to ontologies...")

    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        sys.exit(1)

    print("✅ Authentication successful")

    # Add classes to each ontology
    ontologies = ["my-ontology", "my-onto2"]
    success_count = 0

    for ontology_name in ontologies:
        print(f"\n📝 Adding classes to {ontology_name}...")
        if add_classes_to_ontology(ontology_name, token):
            success_count += 1

            # Verify the classes were loaded
            print(f"🔍 Verifying classes in {ontology_name}...")
            verify_classes_loaded(ontology_name, token)

    print(f"\n🎉 Successfully added classes to {success_count}/{len(ontologies)} ontologies")

    if success_count == len(ontologies):
        print("\n✅ All ontologies now have classes! You can now test the import functionality.")
        print("   - Both ontologies have a 'Constraint' class that should match")
        print("   - Try importing one ontology into the other to see class matching")
    else:
        print("\n❌ Some ontologies failed to load classes. Check the errors above.")


if __name__ == "__main__":
    main()

