#!/usr/bin/env python3
"""
Script to clean up floating/orphaned data in ODRAS system.
This script will remove any data that should be cleaned up after deleting all ontologies and projects.
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


def cleanup_postgres_data(conn, dry_run=True):
    """Clean up PostgreSQL floating data."""
    print("=== PostgreSQL Data Cleanup ===")

    cleanup_queries = [
        # Remove ontology changes (these are just logs)
        ("DELETE FROM public.ontology_changes", "ontology_changes"),
        # Remove requirements (orphaned from deleted projects)
        ("DELETE FROM public.requirements", "requirements"),
        # Remove extraction jobs (orphaned from deleted projects)
        ("DELETE FROM public.extraction_jobs", "extraction_jobs"),
        # Remove file metadata (orphaned from deleted projects)
        ("DELETE FROM file_storage.file_metadata", "file_metadata"),
        # Remove ontologies registry entries (orphaned from deleted projects)
        ("DELETE FROM public.ontologies_registry", "ontologies_registry"),
        # Remove project members (orphaned from deleted projects)
        ("DELETE FROM public.project_members", "project_members"),
        # Remove projects (should be empty but just in case)
        ("DELETE FROM public.projects", "projects"),
        # Remove users (should be empty but just in case)
        ("DELETE FROM public.users", "users"),
    ]

    try:
        with conn.cursor() as cur:
            for query, table_name in cleanup_queries:
                if dry_run:
                    # Count records that would be deleted
                    count_query = f"SELECT COUNT(*) FROM ({query.replace('DELETE FROM', 'SELECT * FROM')}) AS count_query"
                    cur.execute(count_query)
                    count = cur.fetchone()[0]
                    print(f"  {table_name}: Would delete {count} records")
                else:
                    # Actually delete
                    cur.execute(query)
                    deleted_count = cur.rowcount
                    print(f"  {table_name}: Deleted {deleted_count} records")

            if not dry_run:
                conn.commit()
                print("  ✓ All PostgreSQL cleanup completed")
            else:
                print("  ✓ Dry run completed - no changes made")

    except Exception as e:
        print(f"Error during PostgreSQL cleanup: {e}")
        if not dry_run:
            conn.rollback()
        return False

    return True


def cleanup_fuseki_data(dry_run=True):
    """Clean up Fuseki floating data."""
    print("\n=== Fuseki Data Cleanup ===")

    try:
        # Get Fuseki URL from environment or use default
        fuseki_url = os.environ.get("FUSEKI_URL", "http://localhost:3030")
        fuseki_user = os.environ.get("FUSEKI_USER", "")
        fuseki_password = os.environ.get("FUSEKI_PASSWORD", "")
        auth = (fuseki_user, fuseki_password) if fuseki_user and fuseki_password else None

        # List datasets
        datasets_url = f"{fuseki_url}/$/datasets"
        response = requests.get(datasets_url, auth=auth, timeout=10)

        if response.status_code == 200:
            datasets_data = response.json()
            datasets = (
                datasets_data.get("datasets", [])
                if isinstance(datasets_data, dict)
                else datasets_data
            )
            print(f"Found {len(datasets)} datasets in Fuseki")

            for dataset in datasets:
                dataset_name = dataset.get("ds.name", "unknown")
                print(f"  Processing dataset: {dataset_name}")

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

                        print(f"    Found {len(graphs)} named graphs")

                        for graph_iri in graphs:
                            if dry_run:
                                print(f"      Would delete graph: {graph_iri}")
                            else:
                                # Delete the named graph
                                delete_url = f"{fuseki_url}/{dataset_name}/data"
                                delete_response = requests.delete(
                                    delete_url,
                                    params={"graph": graph_iri},
                                    auth=auth,
                                    timeout=10,
                                )

                                if delete_response.status_code in [200, 204]:
                                    print(f"      ✓ Deleted graph: {graph_iri}")
                                else:
                                    print(
                                        f"      ✗ Failed to delete graph: {graph_iri} (status: {delete_response.status_code})"
                                    )

                except Exception as e:
                    print(f"    Error processing dataset {dataset_name}: {e}")
        else:
            print(f"Failed to get datasets from Fuseki: {response.status_code}")

    except Exception as e:
        print(f"Error during Fuseki cleanup: {e}")
        return False

    return True


def cleanup_qdrant_data(dry_run=True):
    """Clean up Qdrant floating data."""
    print("\n=== Qdrant Data Cleanup ===")

    try:
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")

        # List collections
        collections_url = f"{qdrant_url}/collections"
        response = requests.get(collections_url, timeout=10)

        if response.status_code == 200:
            collections_data = response.json()
            collections = collections_data.get("result", {}).get("collections", [])

            print(f"Found {len(collections)} collections in Qdrant")

            for collection in collections:
                collection_name = collection.get("name", "unknown")

                if dry_run:
                    # Get collection info
                    info_url = f"{qdrant_url}/collections/{collection_name}"
                    info_response = requests.get(info_url, timeout=10)

                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        points_count = info_data.get("result", {}).get("points_count", 0)
                        print(
                            f"  Would delete collection '{collection_name}' with {points_count} points"
                        )
                else:
                    # Delete collection
                    delete_url = f"{qdrant_url}/collections/{collection_name}"
                    delete_response = requests.delete(delete_url, timeout=10)

                    if delete_response.status_code in [200, 202]:
                        print(f"  ✓ Deleted collection: {collection_name}")
                    else:
                        print(
                            f"  ✗ Failed to delete collection: {collection_name} (status: {delete_response.status_code})"
                        )
        else:
            print(f"Failed to get collections from Qdrant: {response.status_code}")

    except Exception as e:
        print(f"Error during Qdrant cleanup: {e}")
        return False

    return True


def main():
    """Main function to clean up floating data."""
    import argparse

    parser = argparse.ArgumentParser(description="Clean up floating data in ODRAS system")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Perform a dry run without making changes (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the cleanup (overrides --dry-run)",
    )
    parser.add_argument(
        "--postgres-only", action="store_true", help="Only clean up PostgreSQL data"
    )
    parser.add_argument("--fuseki-only", action="store_true", help="Only clean up Fuseki data")
    parser.add_argument("--qdrant-only", action="store_true", help="Only clean up Qdrant data")

    args = parser.parse_args()

    # Determine if this is a dry run
    dry_run = not args.execute

    print("ODRAS Floating Data Cleanup")
    print("=" * 40)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  EXECUTION MODE - Changes will be made!")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cleanup cancelled.")
            return 0

    success = True

    # Clean up PostgreSQL
    if not args.fuseki_only and not args.qdrant_only:
        conn = get_db_connection()
        if not conn:
            print("Failed to connect to PostgreSQL. Skipping PostgreSQL cleanup.")
            success = False
        else:
            try:
                if not cleanup_postgres_data(conn, dry_run):
                    success = False
            finally:
                conn.close()

    # Clean up Fuseki
    if not args.postgres_only and not args.qdrant_only:
        if not cleanup_fuseki_data(dry_run):
            success = False

    # Clean up Qdrant
    if not args.postgres_only and not args.fuseki_only:
        if not cleanup_qdrant_data(dry_run):
            success = False

    print("\n" + "=" * 40)
    if success:
        if dry_run:
            print("✅ Dry run completed successfully")
            print("Run with --execute to perform actual cleanup")
        else:
            print("✅ Cleanup completed successfully")
    else:
        print("❌ Some cleanup operations failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
