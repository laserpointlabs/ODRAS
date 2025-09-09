#!/usr/bin/env python3
"""
Script to check for floating/orphaned data in ODRAS system after deleting all ontologies and projects.
This script will identify any data that should be cleaned up.
"""

import os
import sys
import psycopg2
import requests
import json
from typing import Dict, List, Any


def get_db_connection():
    """Get database connection using environment variables or defaults."""
    try:
        # Try environment variables first
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        database = os.environ.get("POSTGRES_DATABASE", "odras")
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "password")

        return psycopg2.connect(
            host=host, port=port, database=database, user=user, password=password
        )
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None


def check_postgres_data(conn):
    """Check PostgreSQL for floating data."""
    print("=== PostgreSQL Data Check ===")

    floating_data = {
        "users": [],
        "projects": [],
        "project_members": [],
        "ontologies_registry": [],
        "file_metadata": [],
        "extraction_jobs": [],
        "requirements": [],
        "ontology_changes": [],
    }

    try:
        with conn.cursor() as cur:
            # Check users
            cur.execute("SELECT user_id, username, display_name, is_admin FROM public.users")
            users = cur.fetchall()
            floating_data["users"] = [
                {
                    "user_id": u[0],
                    "username": u[1],
                    "display_name": u[2],
                    "is_admin": u[3],
                }
                for u in users
            ]

            # Check projects
            cur.execute(
                "SELECT project_id, name, description, created_by, is_active FROM public.projects"
            )
            projects = cur.fetchall()
            floating_data["projects"] = [
                {
                    "project_id": p[0],
                    "name": p[1],
                    "description": p[2],
                    "created_by": p[3],
                    "is_active": p[4],
                }
                for p in projects
            ]

            # Check project members
            cur.execute("SELECT project_id, user_id, role FROM public.project_members")
            members = cur.fetchall()
            floating_data["project_members"] = [
                {"project_id": m[0], "user_id": m[1], "role": m[2]} for m in members
            ]

            # Check ontologies registry
            cur.execute(
                "SELECT id, project_id, graph_iri, label, role, is_reference FROM public.ontologies_registry"
            )
            ontologies = cur.fetchall()
            floating_data["ontologies_registry"] = [
                {
                    "id": o[0],
                    "project_id": o[1],
                    "graph_iri": o[2],
                    "label": o[3],
                    "role": o[4],
                    "is_reference": o[5],
                }
                for o in ontologies
            ]

            # Check file metadata
            cur.execute(
                "SELECT file_id, filename, project_id, created_by, is_deleted FROM file_storage.file_metadata"
            )
            files = cur.fetchall()
            floating_data["file_metadata"] = [
                {
                    "file_id": f[0],
                    "filename": f[1],
                    "project_id": f[2],
                    "created_by": f[3],
                    "is_deleted": f[4],
                }
                for f in files
            ]

            # Check extraction jobs
            cur.execute("SELECT job_id, project_id, file_id, status FROM public.extraction_jobs")
            jobs = cur.fetchall()
            floating_data["extraction_jobs"] = [
                {"job_id": j[0], "project_id": j[1], "file_id": j[2], "status": j[3]} for j in jobs
            ]

            # Check requirements
            cur.execute(
                "SELECT requirement_id, project_id, file_id, text FROM public.requirements LIMIT 10"
            )
            requirements = cur.fetchall()
            floating_data["requirements"] = [
                {
                    "requirement_id": r[0],
                    "project_id": r[1],
                    "file_id": r[2],
                    "text": r[3][:100] + "..." if len(r[3]) > 100 else r[3],
                }
                for r in requirements
            ]

            # Check ontology changes
            cur.execute(
                "SELECT change_id, user_id, change_type, change_description FROM public.ontology_changes LIMIT 10"
            )
            changes = cur.fetchall()
            floating_data["ontology_changes"] = [
                {
                    "change_id": c[0],
                    "user_id": c[1],
                    "change_type": c[2],
                    "change_description": c[3],
                }
                for c in changes
            ]

    except Exception as e:
        print(f"Error checking PostgreSQL data: {e}")
        return None

    return floating_data


def check_fuseki_data():
    """Check Fuseki for floating ontology data."""
    print("\n=== Fuseki Data Check ===")

    try:
        # Get Fuseki URL from environment or use default
        fuseki_url = os.environ.get("FUSEKI_URL", "http://localhost:3030")
        fuseki_user = os.environ.get("FUSEKI_USER", "")
        fuseki_password = os.environ.get("FUSEKI_PASSWORD", "")

        # List datasets
        datasets_url = f"{fuseki_url}/$/datasets"
        auth = (fuseki_user, fuseki_password) if fuseki_user and fuseki_password else None

        response = requests.get(datasets_url, auth=auth, timeout=10)
        if response.status_code == 200:
            datasets_data = response.json()
            datasets = (
                datasets_data.get("datasets", [])
                if isinstance(datasets_data, dict)
                else datasets_data
            )
            print(f"Found {len(datasets)} datasets in Fuseki")

            floating_graphs = []
            for dataset in datasets:
                dataset_name = dataset.get("ds.name", "unknown")
                # Query for named graphs in each dataset
                query_url = f"{fuseki_url}/{dataset_name}/sparql"
                query = """
                SELECT DISTINCT ?g WHERE {
                    GRAPH ?g { ?s ?p ?o }
                }
                """

                try:
                    graph_response = requests.post(
                        query_url,
                        data={"query": query},
                        headers={"Accept": "application/sparql-results+json"},
                        auth=auth,
                        timeout=10,
                    )

                    if graph_response.status_code == 200:
                        results = graph_response.json()
                        graphs = [
                            binding["g"]["value"]
                            for binding in results.get("results", {}).get("bindings", [])
                        ]
                        floating_graphs.extend(
                            [{"dataset": dataset_name, "graph": graph} for graph in graphs]
                        )

                except Exception as e:
                    print(f"Error querying dataset {dataset_name}: {e}")

            return floating_graphs
        else:
            print(f"Failed to get datasets from Fuseki: {response.status_code}")
            return []

    except Exception as e:
        print(f"Error checking Fuseki data: {e}")
        return []


def check_neo4j_data():
    """Check Neo4j for floating data."""
    print("\n=== Neo4j Data Check ===")

    try:
        # Neo4j connection details
        neo4j_url = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "testpassword")

        # For now, just report if Neo4j is accessible
        # In a full implementation, you'd use the neo4j driver to query for nodes/relationships
        print("Neo4j check would require neo4j driver - skipping detailed check")
        return []

    except Exception as e:
        print(f"Error checking Neo4j data: {e}")
        return []


def check_qdrant_data():
    """Check Qdrant for floating vector data."""
    print("\n=== Qdrant Data Check ===")

    try:
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")

        # List collections
        collections_url = f"{qdrant_url}/collections"
        response = requests.get(collections_url, timeout=10)

        if response.status_code == 200:
            collections_data = response.json()
            collections = collections_data.get("result", {}).get("collections", [])

            floating_collections = []
            for collection in collections:
                collection_name = collection.get("name", "unknown")
                # Get collection info
                info_url = f"{qdrant_url}/collections/{collection_name}"
                info_response = requests.get(info_url, timeout=10)

                if info_response.status_code == 200:
                    info_data = info_response.json()
                    points_count = info_data.get("result", {}).get("points_count", 0)
                    floating_collections.append(
                        {"name": collection_name, "points_count": points_count}
                    )

            return floating_collections
        else:
            print(f"Failed to get collections from Qdrant: {response.status_code}")
            return []

    except Exception as e:
        print(f"Error checking Qdrant data: {e}")
        return []


def generate_cleanup_report(floating_data, fuseki_graphs, neo4j_data, qdrant_collections):
    """Generate a comprehensive cleanup report."""
    print("\n" + "=" * 60)
    print("FLOATING DATA CLEANUP REPORT")
    print("=" * 60)

    total_items = 0

    # PostgreSQL data
    print("\n📊 PostgreSQL Data:")
    for table, items in floating_data.items():
        if items:
            print(f"  {table}: {len(items)} items")
            total_items += len(items)
            # Show first few items as examples
            for i, item in enumerate(items[:3]):
                print(f"    - {item}")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more")
        else:
            print(f"  {table}: 0 items ✓")

    # Fuseki data
    print(f"\n🔗 Fuseki Data:")
    if fuseki_graphs:
        print(f"  Found {len(fuseki_graphs)} named graphs")
        total_items += len(fuseki_graphs)
        for graph in fuseki_graphs[:5]:
            print(f"    - Dataset: {graph['dataset']}, Graph: {graph['graph']}")
        if len(fuseki_graphs) > 5:
            print(f"    ... and {len(fuseki_graphs) - 5} more")
    else:
        print("  No named graphs found ✓")

    # Qdrant data
    print(f"\n🔍 Qdrant Data:")
    if qdrant_collections:
        print(f"  Found {len(qdrant_collections)} collections")
        total_items += len(qdrant_collections)
        for collection in qdrant_collections:
            print(f"    - {collection['name']}: {collection['points_count']} points")
    else:
        print("  No collections found ✓")

    print(f"\n📈 SUMMARY:")
    print(f"  Total floating items found: {total_items}")

    if total_items > 0:
        print(f"\n🧹 RECOMMENDED CLEANUP ACTIONS:")
        print("  1. Run cleanup script to remove orphaned data")
        print("  2. Verify all references are properly cleaned")
        print("  3. Check for any remaining foreign key constraints")
    else:
        print(f"\n✅ SYSTEM IS CLEAN - No floating data detected!")


def main():
    """Main function to check for floating data."""
    print("ODRAS Floating Data Checker")
    print("=" * 40)

    # Check PostgreSQL
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to PostgreSQL. Exiting.")
        return 1

    try:
        floating_data = check_postgres_data(conn)
        if floating_data is None:
            print("Failed to check PostgreSQL data. Exiting.")
            return 1

        # Check other services
        fuseki_graphs = check_fuseki_data()
        neo4j_data = check_neo4j_data()
        qdrant_collections = check_qdrant_data()

        # Generate report
        generate_cleanup_report(floating_data, fuseki_graphs, neo4j_data, qdrant_collections)

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
