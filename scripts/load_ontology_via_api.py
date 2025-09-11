#!/usr/bin/env python3
"""
Script to load ontology data via the backend API instead of direct Fuseki access.
"""

import json
import requests
import sys
from pathlib import Path

# Configuration
BACKEND_BASE_URL = "http://localhost:8000"
PROJECT_ID = "6b705b95-3499-46a5-bb0e-d8559618732b"


def create_ontology_iri(ontology_name):
    """Create the full IRI for an ontology."""
    return f"http://odras.local/onto/{PROJECT_ID}/{ontology_name}"


def convert_json_to_turtle(json_data, ontology_iri, ontology_label):
    """Convert Cytoscape JSON data to Turtle format."""

    # Start with ontology declaration
    turtle = f"""@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<{ontology_iri}> a owl:Ontology ;
    rdfs:label "{ontology_label}" .

"""

    # Process nodes (classes)
    for node in json_data.get("nodes", []):
        if node["data"].get("type") == "class":
            class_id = node["data"]["id"]
            class_label = node["data"]["label"]
            class_iri = f"{ontology_iri}#{class_id}"

            turtle += f"""<{class_iri}> a owl:Class ;
    rdfs:label "{class_label}" .

"""

    # Process edges (object properties)
    for edge in json_data.get("edges", []):
        if edge["data"].get("type") == "objectProperty":
            source_id = edge["data"]["source"]
            target_id = edge["data"]["target"]
            predicate = edge["data"]["predicate"]

            source_iri = f"{ontology_iri}#{source_id}"
            target_iri = f"{ontology_iri}#{target_id}"
            property_iri = f"{ontology_iri}#{predicate}"

            turtle += f"""<{property_iri}> a owl:ObjectProperty ;
    rdfs:label "{predicate}" ;
    rdfs:domain <{source_iri}> ;
    rdfs:range <{target_iri}> .

"""

    return turtle


def load_ontology_via_api(ontology_iri, turtle_data):
    """Load Turtle data via the backend API."""

    print(f"Loading data via API for: {ontology_iri}")

    # Use the /api/ontology/save endpoint
    response = requests.post(
        f"{BACKEND_BASE_URL}/api/ontology/save",
        params={"graph": ontology_iri},
        data=turtle_data,
        headers={"Content-Type": "text/turtle"},
    )

    if response.status_code in [200, 201, 204]:
        print(f"Successfully loaded data via API into {ontology_iri}")
        return True
    else:
        print(f"Failed to load data via API: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def main():
    """Main function to load ontology data."""

    # Define the ontologies to load
    ontologies = [
        {"name": "my-ontology", "label": "My Ontology", "file": "data/beso_v1.json"},
        {"name": "my-onto2", "label": "My Ontology 2", "file": "data/bseo_rs_v1.json"},
    ]

    for ontology in ontologies:
        print(f"\nProcessing {ontology['name']}...")

        # Read JSON data
        json_file = Path(ontology["file"])
        if not json_file.exists():
            print(f"Error: File {json_file} not found")
            continue

        with open(json_file, "r") as f:
            json_data = json.load(f)

        # Convert to Turtle
        ontology_iri = create_ontology_iri(ontology["name"])
        turtle_data = convert_json_to_turtle(json_data, ontology_iri, ontology["label"])

        print(f"Generated Turtle data for {ontology['name']}:")
        print(turtle_data[:500] + "..." if len(turtle_data) > 500 else turtle_data)

        # Load via API
        success = load_ontology_via_api(ontology_iri, turtle_data)

        if success:
            print(f"✅ Successfully loaded {ontology['name']}")
        else:
            print(f"❌ Failed to load {ontology['name']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
