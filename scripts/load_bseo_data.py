#!/usr/bin/env python3
"""
Load BSEO ontology data from JSON files into Fuseki named graphs.
This script converts the JSON ontology data to RDF/Turtle format and loads it into the appropriate graphs.
"""

import json
import logging
import sys
from typing import Dict, Any, List
import requests
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
PROJECT_ID = "b28d76c0-2101-4ecc-be2a-c72dc215cbed"


def json_to_turtle(ontology_data: Dict[str, Any], graph_iri: str) -> str:
    """Convert JSON ontology data to Turtle format."""
    lines = []

    # Add prefixes
    lines.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    lines.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    lines.append("")

    # Add ontology declaration
    lines.append(f"<{graph_iri}> a owl:Ontology ;")
    lines.append(f'  rdfs:label "{graph_iri.split("/")[-1]}" .')
    lines.append("")

    # Process nodes (classes)
    nodes = ontology_data.get("nodes", [])
    for node in nodes:
        node_data = node.get("data", {})
        if node_data.get("type") == "class":
            class_id = node_data.get("id", "")
            class_label = node_data.get("label", class_id)

            # Create class IRI
            class_iri = f"{graph_iri}#{class_id}"

            lines.append(f"<{class_iri}> a owl:Class ;")
            lines.append(f'  rdfs:label "{class_label}" .')
            lines.append("")

    # Process edges (properties and relationships)
    edges = ontology_data.get("edges", [])
    for edge in edges:
        edge_data = edge.get("data", {})
        edge_type = edge_data.get("type", "")
        source = edge_data.get("source", "")
        target = edge_data.get("target", "")
        predicate = edge_data.get("predicate", "")

        if edge_type == "objectProperty" and predicate:
            # Create property IRI
            prop_iri = f"{graph_iri}#{predicate}"
            source_iri = f"{graph_iri}#{source}"
            target_iri = f"{graph_iri}#{target}"

            lines.append(f"<{prop_iri}> a owl:ObjectProperty ;")
            lines.append(f'  rdfs:label "{predicate}" ;')
            lines.append(f"  rdfs:domain <{source_iri}> ;")
            lines.append(f"  rdfs:range <{target_iri}> .")
            lines.append("")

    return "\n".join(lines)


async def load_ontology_data(graph_name: str, json_file: str, label: str):
    """Load ontology data from JSON file into a named graph."""
    logger.info(f"Loading {graph_name} from {json_file}...")

    # Load JSON data
    try:
        with open(json_file, "r") as f:
            ontology_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {json_file}: {e}")
        return False

    # Build graph IRI
    graph_iri = f"http://odras.local/onto/{PROJECT_ID}/{graph_name}"

    # Convert to Turtle
    turtle_content = json_to_turtle(ontology_data, graph_iri)

    # Save to Fuseki
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/ontology/save",
                params={"graph": graph_iri},
                content=turtle_content,
                headers={"Content-Type": "text/turtle"},
            )

            if response.status_code == 200:
                logger.info(f"✅ Successfully loaded {graph_name}")
                return True
            else:
                logger.error(
                    f"Failed to save {graph_name}: {response.status_code} - {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"Error saving {graph_name}: {e}")
        return False


async def main():
    """Main function to load all BSEO data."""
    logger.info("Loading BSEO ontology data...")

    # Define the ontologies to load
    ontologies = [
        {"name": "bseo-v1", "file": "data/base_se_v1.json", "label": "BSEO V1"},
        {
            "name": "bseo-rnm-v1",
            "file": "data/base_se_v1.json",  # Using same data for now
            "label": "BSEO RNM V1",
        },
    ]

    success_count = 0
    for ontology in ontologies:
        success = await load_ontology_data(ontology["name"], ontology["file"], ontology["label"])
        if success:
            success_count += 1

    logger.info(f"Successfully loaded {success_count}/{len(ontologies)} ontologies")
    return 0 if success_count == len(ontologies) else 1


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))

