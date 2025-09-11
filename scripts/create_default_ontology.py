#!/usr/bin/env python3
"""
Create and populate the default ontology for the Default Project
This script is called during init-db to ensure the project has a working ontology
"""
import json
import logging
import os
import sys
import time
import uuid
from typing import Dict, Any, Optional

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FUSEKI_URL = os.getenv("FUSEKI_URL", "http://localhost:3030/odras")
FUSEKI_USER = os.getenv("FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.getenv("FUSEKI_PASSWORD", "admin")

# Default ontology JSON file
DEFAULT_ONTOLOGY_FILE = os.path.join(
    os.path.dirname(__file__), "../data/default_project_ontology.json"
)


class DefaultOntologyCreator:
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.fuseki_url = FUSEKI_URL
        self.admin_token = None
        self.default_project_id = None

    async def authenticate_admin(self):
        """Authenticate as admin user"""
        logger.info("Authenticating as admin...")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.api_base_url}/api/auth/login",
                json={"username": "admin", "password": "admin"},
            )

            if response.status_code != 200:
                raise Exception(f"Admin authentication failed: {response.status_code}")

            self.admin_token = response.json()["token"]
            logger.info("✅ Admin authenticated")

    def get_default_project_id(self):
        """Get the Default Project ID from PostgreSQL"""
        logger.info("Getting Default Project ID...")

        try:
            conn = psycopg2.connect(
                host="localhost",
                database="odras",
                user="postgres",
                password="password",
                port=5432,
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT project_id, name 
                    FROM projects 
                    WHERE name = 'Default Project'
                    LIMIT 1
                """
                )

                result = cur.fetchone()
                if not result:
                    raise Exception("Default Project not found in database")

                self.default_project_id = str(result["project_id"])
                logger.info(f"✅ Found Default Project: {self.default_project_id}")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to get Default Project: {e}")
            return False

    async def check_existing_ontology(self):
        """Check if the Default Project already has ontologies"""
        logger.info("Checking for existing ontologies...")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.api_base_url}/api/ontologies",
                params={"project": self.default_project_id},
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                ontologies = data.get("ontologies", [])

                if ontologies:
                    logger.info(f"Found {len(ontologies)} existing ontologies")
                    # Check if we already have our default ontology
                    for onto in ontologies:
                        if "default-project-ontology" in onto.get("graphIri", ""):
                            logger.info("✅ Default ontology already exists, skipping creation")
                            return True

                logger.info("No default ontology found, will create one")
                return False
            else:
                logger.warning(f"Failed to check ontologies: {response.status_code}")
                return False

    async def create_ontology(self):
        """Create the default ontology in the project"""
        logger.info("Creating default ontology...")

        ontology_name = "default-project-ontology"
        ontology_label = "Default Project Ontology"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.api_base_url}/api/ontologies",
                json={
                    "project": self.default_project_id,
                    "name": ontology_name,
                    "label": ontology_label,
                },
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )

            if response.status_code in [200, 201]:
                data = response.json()
                graph_iri = data.get("graphIri")
                logger.info(f"✅ Created ontology: {graph_iri}")
                return graph_iri
            else:
                logger.error(f"Failed to create ontology: {response.status_code} - {response.text}")
                return None

    def load_ontology_json(self) -> Dict[str, Any]:
        """Load the default ontology JSON structure"""
        logger.info(f"Loading ontology from {DEFAULT_ONTOLOGY_FILE}...")

        if not os.path.exists(DEFAULT_ONTOLOGY_FILE):
            logger.error(f"Ontology file not found: {DEFAULT_ONTOLOGY_FILE}")
            return None

        with open(DEFAULT_ONTOLOGY_FILE, "r") as f:
            return json.load(f)

    def json_to_turtle(self, ontology_data: Dict[str, Any], graph_iri: str) -> str:
        """Convert JSON ontology to Turtle RDF format"""
        # Extract namespace from graph IRI
        base_namespace = graph_iri.rsplit("/", 1)[0] + "/"

        lines = [
            f"@base <{base_namespace}> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix odras: <http://odras.system/ontology#> .",
            "",
            f"<{graph_iri}> a owl:Ontology ;",
            f'  rdfs:label "{ontology_data.get("metadata", {}).get("name", "Default Ontology")}" ;',
            f'  rdfs:comment "{ontology_data.get("metadata", {}).get("description", "")}" .',
            "",
        ]

        # Add classes
        for cls in ontology_data.get("classes", []):
            lines.append(f"odras:{cls['name']} a owl:Class ;")
            if cls.get("label"):
                lines.append(f'  rdfs:label "{cls["label"]}" ;')
            if cls.get("comment"):
                lines.append(f'  rdfs:comment "{cls["comment"]}" ;')
            if cls.get("subclass_of"):
                lines.append(f"  rdfs:subClassOf odras:{cls['subclass_of']} ;")
            lines[-1] = lines[-1].rstrip(" ;") + " ."  # Replace last semicolon with period
            lines.append("")

        # Add object properties
        for prop in ontology_data.get("object_properties", []):
            lines.append(f"odras:{prop['name']} a owl:ObjectProperty ;")
            if prop.get("label"):
                lines.append(f'  rdfs:label "{prop["label"]}" ;')
            if prop.get("comment"):
                lines.append(f'  rdfs:comment "{prop["comment"]}" ;')
            if prop.get("domain"):
                lines.append(f"  rdfs:domain odras:{prop['domain']} ;")
            if prop.get("range"):
                lines.append(f"  rdfs:range odras:{prop['range']} ;")
            lines[-1] = lines[-1].rstrip(" ;") + " ."
            lines.append("")

        # Add datatype properties
        for prop in ontology_data.get("datatype_properties", []):
            lines.append(f"odras:{prop['name']} a owl:DatatypeProperty ;")
            if prop.get("label"):
                lines.append(f'  rdfs:label "{prop["label"]}" ;')
            if prop.get("comment"):
                lines.append(f'  rdfs:comment "{prop["comment"]}" ;')
            if prop.get("domain"):
                lines.append(f"  rdfs:domain odras:{prop['domain']} ;")
            if prop.get("range"):
                # Map common datatypes
                range_type = prop["range"]
                if range_type.startswith("xsd:"):
                    lines.append(f"  rdfs:range {range_type} ;")
                else:
                    lines.append(f"  rdfs:range xsd:string ;")  # Default to string
            lines[-1] = lines[-1].rstrip(" ;") + " ."
            lines.append("")

        return "\n".join(lines)

    async def populate_ontology(self, graph_iri: str):
        """Populate the ontology with classes and properties from JSON"""
        logger.info(f"Populating ontology {graph_iri}...")

        # Load the ontology structure
        ontology_data = self.load_ontology_json()
        if not ontology_data:
            return False

        # Convert JSON to RDF/Turtle format
        turtle_content = self.json_to_turtle(ontology_data, graph_iri)

        # Save the ontology directly to Fuseki
        async with httpx.AsyncClient(timeout=60) as client:
            # Save the turtle content to the named graph
            save_response = await client.post(
                f"{self.api_base_url}/api/ontology/save",
                params={"graph": graph_iri},
                content=turtle_content,
                headers={
                    "Authorization": f"Bearer {self.admin_token}",
                    "Content-Type": "text/turtle",
                },
            )

            if save_response.status_code == 200:
                logger.info("✅ Ontology saved to Fuseki successfully")
                return True
            else:
                logger.error(
                    f"Failed to save to Fuseki: {save_response.status_code} - {save_response.text}"
                )
                return False

    def create_cytoscape_format(self, ontology_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ontology JSON to Cytoscape format for UI"""
        nodes = []
        edges = []

        # Create nodes for classes
        y_pos = 100
        x_start = 200
        x_spacing = 250

        for i, cls in enumerate(ontology_data.get("classes", [])):
            # Arrange in a grid pattern
            row = i // 3
            col = i % 3

            node = {
                "data": {
                    "id": f"Class_{cls['name']}",
                    "label": cls["label"],
                    "type": "class",
                },
                "position": {
                    "x": x_start + (col * x_spacing),
                    "y": y_pos + (row * 150),
                },
            }
            nodes.append(node)

        # Create edges for object properties
        edge_id = 1
        for prop in ontology_data.get("object_properties", []):
            if prop.get("domain") and prop.get("range"):
                edge = {
                    "data": {
                        "id": f"e{edge_id}",
                        "source": f"Class_{prop['domain']}",
                        "target": f"Class_{prop['range']}",
                        "predicate": prop["name"],
                        "type": "objectProperty",
                        "attrs": {},
                    }
                }
                edges.append(edge)
                edge_id += 1

        return {"nodes": nodes, "edges": edges}

    async def setup_local_storage_sync(self, graph_iri: str):
        """Setup data to help with local storage synchronization"""
        logger.info("Setting up for local storage sync...")

        # Load ontology data and create cytoscape format
        ontology_data = self.load_ontology_json()
        if not ontology_data:
            return

        cytoscape_data = self.create_cytoscape_format(ontology_data)

        # Register the ontology in the database
        try:
            conn = psycopg2.connect(
                host="localhost",
                database="odras",
                user="postgres",
                password="password",
                port=5432,
            )

            with conn.cursor() as cur:
                # Add to ontologies_registry if not already there
                cur.execute(
                    """
                    INSERT INTO ontologies_registry (project_id, graph_iri, label, role)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (graph_iri) DO UPDATE
                    SET label = EXCLUDED.label, updated_at = NOW()
                """,
                    (
                        self.default_project_id,
                        graph_iri,
                        "Default Project Ontology",
                        "base",
                    ),
                )

                conn.commit()
                logger.info("✅ Ontology registered in database")

            conn.close()

        except Exception as e:
            logger.warning(f"Could not register ontology in database: {e}")

        # Save sync data for potential UI use
        sync_file = f"/tmp/default_ontology_sync_{self.default_project_id}.json"
        with open(sync_file, "w") as f:
            json.dump(
                {
                    "project_id": self.default_project_id,
                    "graph_iri": graph_iri,
                    "label": "Default Project Ontology",
                    "cytoscape_data": cytoscape_data,
                },
                f,
                indent=2,
            )

        logger.info(f"✅ Sync data saved to {sync_file}")
        logger.info("   The ontology is now ready for use in the UI")


async def main():
    """Main function to create default ontology"""
    creator = DefaultOntologyCreator()

    try:
        # Step 1: Authenticate as admin
        await creator.authenticate_admin()

        # Step 2: Get Default Project ID
        if not creator.get_default_project_id():
            logger.error("Cannot proceed without Default Project")
            return False

        # Step 3: Check if ontology already exists
        if await creator.check_existing_ontology():
            logger.info("Default ontology already exists, no action needed")
            return True

        # Step 4: Create the ontology
        graph_iri = await creator.create_ontology()
        if not graph_iri:
            logger.error("Failed to create ontology")
            return False

        # Step 5: Populate with classes and properties
        if not await creator.populate_ontology(graph_iri):
            logger.error("Failed to populate ontology")
            return False

        # Step 6: Setup sync data for UI
        await creator.setup_local_storage_sync(graph_iri)

        logger.info("🎉 Default ontology created and populated successfully!")
        logger.info(f"   Graph IRI: {graph_iri}")
        logger.info("   Contains:")
        logger.info("   - 13 Classes (including CADFile, Specification, etc.)")
        logger.info("   - 11 Object Properties")
        logger.info("   - 12 Datatype Properties")

        return True

    except Exception as e:
        logger.error(f"Error creating default ontology: {e}")
        return False


if __name__ == "__main__":
    import asyncio

    # Wait a bit to ensure services are ready
    time.sleep(2)

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
