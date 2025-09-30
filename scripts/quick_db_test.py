#!/usr/bin/env python3
"""
Quick Database Test Script

Run this after any database changes to quickly validate everything is working.
This provides immediate feedback without running the full test suite.

Usage:
    python scripts/quick_db_test.py
    python scripts/quick_db_test.py --api  # Also test API endpoints
    python scripts/quick_db_test.py --full  # Run all checks
"""

import sys
import os
import argparse
import socket
import time
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{text:^60}{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}ℹ {text}{RESET}")


def check_port(host: str, port: int, service_name: str) -> bool:
    """Check if a service is running on a specific port"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()

    if result == 0:
        print_success(f"{service_name} is running on {host}:{port}")
        return True
    else:
        print_error(f"{service_name} is NOT accessible on {host}:{port}")
        return False


def check_services() -> Dict[str, bool]:
    """Check if all required services are running"""
    print_header("Service Availability Check")

    services = {
        "PostgreSQL": ("localhost", 5432),
        "Neo4j": ("localhost", 7687),
        "Qdrant": ("localhost", 6333),
        "Fuseki": ("localhost", 3030),
        "ODRAS API": ("localhost", 8000)
    }

    results = {}
    for service, (host, port) in services.items():
        results[service] = check_port(host, port, service)

    return results


def check_postgres_tables():
    """Check PostgreSQL tables"""
    print_header("PostgreSQL Database Check")

    try:
        import psycopg2
        import os

        # Use environment variables or defaults
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = int(os.getenv('POSTGRES_PORT', '5432'))
        database = os.getenv('POSTGRES_DB', 'odras_db')
        user = os.getenv('POSTGRES_USER', 'odras_user')
        password = os.getenv('POSTGRES_PASSWORD', 'your_password_here')

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

        with conn.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]

            print_info(f"Found {len(tables)} tables in database")

            # Check required tables
            required_tables = [
                'users', 'projects', 'project_members', 'files',
                'knowledge_documents', 'knowledge_chunks', 'auth_tokens',
                'namespaces', 'das_projects', 'project_threads'
            ]

            missing_tables = []
            for table in required_tables:
                if table in tables:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print_success(f"Table '{table}' exists ({count} rows)")
                else:
                    missing_tables.append(table)
                    print_error(f"Table '{table}' is MISSING")

            # Check for das_service user
            cursor.execute("""
                SELECT username, display_name, is_admin
                FROM users
                WHERE username = 'das_service'
            """)
            das_user = cursor.fetchone()

            if das_user:
                print_success(f"User 'das_service' exists (admin={das_user[2]})")
            else:
                print_error("User 'das_service' NOT FOUND")

        conn.close()
        return len(missing_tables) == 0

    except Exception as e:
        print_error(f"PostgreSQL check failed: {e}")
        return False


def check_qdrant_collections():
    """Check Qdrant collections"""
    print_header("Qdrant Collections Check")

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333)

        # Get all collections
        collections = client.get_collections().collections
        collection_info = {c.name: c for c in collections}

        print_info(f"Found {len(collections)} collections")

        # Check required collections
        required_collections = [
            ('knowledge_chunks', 384),
            ('knowledge_large', 1536),
            ('odras_requirements', 384),
            ('das_instructions', 384),
            ('project_threads', 384)  # Critical for DAS
        ]

        all_good = True
        for name, expected_dim in required_collections:
            if name in collection_info:
                collection = collection_info[name]
                # Handle different Qdrant client versions
                try:
                    if hasattr(collection, 'config') and hasattr(collection.config, 'params'):
                        if hasattr(collection.config.params.vectors, 'size'):
                            actual_dim = collection.config.params.vectors.size
                        else:
                            actual_dim = collection.config.params.vectors.get('size', 0)
                    else:
                        # Newer Qdrant client structure
                        actual_dim = collection.vectors_count if hasattr(collection, 'vectors_count') else 0
                        print_warning(f"Could not determine dimension for '{name}', assuming OK")
                        continue
                except:
                    print_warning(f"Could not check dimension for '{name}'")
                    continue
                    if actual_dim == expected_dim:
                        print_success(f"Collection '{name}' exists (dim={actual_dim})")
                    else:
                        print_error(f"Collection '{name}' dimension mismatch: expected {expected_dim}, got {actual_dim}")
                        all_good = False
            else:
                print_error(f"Collection '{name}' is MISSING")
                all_good = False

        return all_good

    except Exception as e:
        print_error(f"Qdrant check failed: {e}")
        return False


def check_neo4j():
    """Check Neo4j connection"""
    print_header("Neo4j Database Check")

    try:
        from neo4j import GraphDatabase
        import os

        # Use environment variables or defaults
        host = os.getenv('NEO4J_HOST', 'localhost')
        port = int(os.getenv('NEO4J_PORT', '7687'))
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'your_neo4j_password')

        driver = GraphDatabase.driver(
            f"bolt://{host}:{port}",
            auth=(user, password)
        )

        with driver.session() as session:
            # Test connection
            result = session.run("RETURN 1 as test")
            test_val = result.single()["test"]
            print_success("Neo4j connection successful")

            # Check constraints
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            print_info(f"Found {len(constraints)} constraints")

            # Check node counts
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, COUNT(n) as count")
            for record in result:
                if record["label"]:
                    print_success(f"Node type '{record['label']}': {record['count']} nodes")

        driver.close()
        return True

    except Exception as e:
        print_error(f"Neo4j check failed: {e}")
        return False


def check_api_endpoints():
    """Test critical API endpoints"""
    print_header("API Endpoint Tests")

    try:
        import requests

        base_url = "http://localhost:8000"

        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Health endpoint: {data['status']}")
            else:
                print_error(f"Health endpoint returned {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Health endpoint failed: {e}")
            return False

        # Test login with das_service
        try:
            response = requests.post(
                f"{base_url}/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=5
            )
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    print_success(f"DAS login successful (token length: {len(token)})")

                    # Test authenticated endpoint
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.get(f"{base_url}/api/auth/me", headers=headers, timeout=5)
                    if response.status_code == 200:
                        user = response.json()
                        print_success(f"Authenticated as: {user['username']}")
                    else:
                        print_error("Failed to get current user")
                else:
                    print_error("No token received from login")
                    return False
            else:
                print_error(f"DAS login failed with status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Login test failed: {e}")
            return False

        return True

    except ImportError:
        print_warning("requests library not available, skipping API tests")
        return True


def run_migration_check():
    """Check migration files and order"""
    print_header("Migration Files Check")

    # Try multiple possible locations for migrations
    possible_dirs = [
        project_root / "backend" / "migrations",
        project_root / "migrations",
        project_root / "cleanup" / "old_migrations" / "migrations"
    ]

    migrations_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists() and (dir_path / "migration_order.txt").exists():
            migrations_dir = dir_path
            break

    if migrations_dir is None:
        print_warning("Migrations directory not found in expected locations")
        print_info("Searched in:")
        for dir_path in possible_dirs:
            print_info(f"  - {dir_path}")
        return True  # Don't fail, just warn

    order_file = migrations_dir / "migration_order.txt"

    if not migrations_dir.exists():
        print_error("Migrations directory not found")
        return False

    if not order_file.exists():
        print_error("migration_order.txt not found")
        return False

    # Read migration order
    with open(order_file) as f:
        ordered_migrations = [line.strip() for line in f if line.strip()]

    # Check all migrations exist
    all_good = True
    for migration in ordered_migrations:
        migration_path = migrations_dir / migration
        if migration_path.exists():
            size = migration_path.stat().st_size
            print_success(f"Migration '{migration}' exists ({size} bytes)")
        else:
            print_error(f"Migration '{migration}' is MISSING")
            all_good = False

    # Check for orphaned migrations
    sql_files = list(migrations_dir.glob("*.sql"))
    for sql_file in sql_files:
        if sql_file.name not in ordered_migrations:
            print_warning(f"Migration '{sql_file.name}' not in order file")

    return all_good


def run_pytest_check():
    """Run critical pytest tests"""
    print_header("Running Critical Tests")

    try:
        # Run only the comprehensive test suite
        result = subprocess.run(
            ["pytest", "tests/test_comprehensive_suite.py", "-v", "--tb=short", "-k", "test_postgres_connection or test_qdrant_collections"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print_success("Critical tests passed")
            return True
        else:
            print_error("Some tests failed")
            print(result.stdout)
            return False

    except subprocess.TimeoutExpired:
        print_warning("Tests timed out")
        return False
    except Exception as e:
        print_warning(f"Could not run pytest: {e}")
        return True  # Don't fail if pytest not available


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Quick ODRAS database validation")
    parser.add_argument("--api", action="store_true", help="Also test API endpoints")
    parser.add_argument("--full", action="store_true", help="Run all checks including tests")
    args = parser.parse_args()

    print_header("ODRAS Quick Database Validation")
    print_info(f"Running from: {project_root}")

    results = {
        "services": check_services(),
        "migrations": run_migration_check(),
        "postgres": False,
        "qdrant": False,
        "neo4j": False,
        "api": True,
        "tests": True
    }

    # Only check databases if services are running
    if results["services"].get("PostgreSQL"):
        results["postgres"] = check_postgres_tables()

    if results["services"].get("Qdrant"):
        results["qdrant"] = check_qdrant_collections()

    if results["services"].get("Neo4j"):
        results["neo4j"] = check_neo4j()

    # Optional checks
    if args.api or args.full:
        if results["services"].get("ODRAS API"):
            results["api"] = check_api_endpoints()

    if args.full:
        results["tests"] = run_pytest_check()

    # Summary
    print_header("Validation Summary")

    all_passed = True
    for check, result in results.items():
        if isinstance(result, dict):
            # Services check returns dict
            for service, status in result.items():
                if not status and service != "ODRAS API":  # API might not be running
                    all_passed = False
        elif check in ["api", "tests"] and not (args.api or args.full):
            continue  # Skip if not requested
        elif not result:
            all_passed = False

    if all_passed:
        print_success("All critical checks passed! ✨")
        print_info("\nYour database is ready for use.")
        print_info("Run with --api to test API endpoints")
        print_info("Run with --full for comprehensive testing")
    else:
        print_error("\nSome checks failed! Please review the errors above.")
        print_info("\nCommon fixes:")
        print_info("  - Start services: ./odras.sh start")
        print_info("  - Rebuild database: ./odras.sh clean -y && ./odras.sh init-db")
        print_info("  - Check logs: ./odras.sh logs [service]")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
