#!/usr/bin/env python3
"""
Script to load ontology data from JSON files into Fuseki graphs.
Converts Cytoscape layout format to proper RDF/OWL format.
"""

import json
import requests
import sys
from pathlib import Path

# Configuration
FUSEKI_BASE_URL = "http://localhost:3030/odras"
PROJECT_ID = "1f5d5fe5-4ef0-42c7-8361-2afd91bb3223"


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


def load_ontology_to_fuseki(ontology_iri, turtle_data):
    """Load Turtle data into a Fuseki graph."""

    # First, clear the existing graph
    clear_query = f"""
    DELETE WHERE {{
        GRAPH <{ontology_iri}> {{
            ?s ?p ?o .
        }}
    }}
    """

    print(f"Clearing graph: {ontology_iri}")
    response = requests.post(
        f"{FUSEKI_BASE_URL}/update",
        data=clear_query,
        headers={"Content-Type": "application/sparql-update"},
    )

    if response.status_code != 200:
        print(f"Warning: Failed to clear graph: {response.status_code}")
        print(f"Response: {response.text}")

    # Load the new data
    print(f"Loading data into graph: {ontology_iri}")
    response = requests.post(
        f"{FUSEKI_BASE_URL}/data",
        data=turtle_data,
        headers={"Content-Type": "text/turtle", "Graph": ontology_iri},
    )

    if response.status_code in [200, 201, 204]:
        print(f"Successfully loaded data into {ontology_iri}")
        return True
    else:
        print(f"Failed to load data: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def main():
    """Main function to load ontology data."""

    # Define the ontologies to load
    ontologies = [
        {"name": "bseo-v1", "label": "BSEO_V1", "file": "data/beso_v1.json"},
        {"name": "bseo-mrs-v1", "label": "BSEO_RS_V1", "file": "data/bseo_rs_v1.json"},
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

        # Load into Fuseki
        success = load_ontology_to_fuseki(ontology_iri, turtle_data)

        if success:
            print(f"✅ Successfully loaded {ontology['name']}")
        else:
            print(f"❌ Failed to load {ontology['name']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
