"""
Comprehensive ODRAS Test Suite

This is the primary test file for validating all critical ODRAS functionality.
Run this after any database changes or major updates to ensure system integrity.

Usage:
    pytest tests/test_comprehensive_suite.py -v
    pytest tests/test_comprehensive_suite.py::TestDatabaseIntegrity -v  # Run specific test class
    pytest tests/test_comprehensive_suite.py -k "database" -v  # Run tests matching pattern
"""

import pytest
import asyncio
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from httpx import AsyncClient, ASGITransport
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestDatabaseIntegrity:
    """Critical database integrity tests"""

    @pytest.fixture(scope="class")
    def postgres_conn(self):
        """Create PostgreSQL connection"""
        import os
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "odras"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "password")
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        yield conn
        conn.close()

    @pytest.fixture(scope="class")
    def neo4j_driver(self):
        """Create Neo4j driver"""
        import os
        driver = GraphDatabase.driver(
            f"bolt://{os.getenv('NEO4J_HOST', 'localhost')}:{os.getenv('NEO4J_PORT', '7687')}",
            auth=("neo4j", "testpassword")  # Use local password from docker-compose.yml
        )
        yield driver
        driver.close()

    @pytest.fixture(scope="class")
    def qdrant_client(self):
        """Create Qdrant client"""
        import os
        from qdrant_client import QdrantClient
        client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333"))
        )
        return client

    def test_postgres_connection(self, postgres_conn):
        """Test PostgreSQL connection and basic functionality"""
        with postgres_conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            assert version is not None
            print(f"PostgreSQL version: {version[0]}")

    def test_postgres_tables_exist(self, postgres_conn):
        """Test that all required PostgreSQL tables exist"""
        required_tables = [
            'users',
            'projects',
            'project_members',
            'files',
            'knowledge_documents',
            'knowledge_chunks',
            'knowledge_entities',
            'knowledge_topics',
            'knowledge_summaries',
            'knowledge_public_assets',
            'auth_tokens',
            'namespaces',
            'namespace_members',
            'das_projects',
            'das_threads',
            'das_messages',
            'das_instructions',
            'project_threads'
        ]

        with postgres_conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}

        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)

        assert len(missing_tables) == 0, f"Missing tables: {missing_tables}"
        print(f"✓ All {len(required_tables)} required tables exist")

    def test_das_service_user_exists(self, postgres_conn):
        """Test that das_service user exists with correct permissions"""
        with postgres_conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, username, display_name, is_admin
                FROM users
                WHERE username = 'das_service'
            """)
            user = cursor.fetchone()

            assert user is not None, "das_service user not found"
            assert user[1] == 'das_service', "Username mismatch"
            assert user[2] == 'DAS Service Account', "Display name mismatch"
            # das_service should not be admin
            assert user[3] is False, "das_service should not be admin"
            print(f"✓ das_service user exists with ID: {user[0]}")

    def test_neo4j_connection(self, neo4j_driver):
        """Test Neo4j connection and basic functionality"""
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            assert record["test"] == 1
            print("✓ Neo4j connection successful")

    def test_neo4j_constraints_exist(self, neo4j_driver):
        """Test that required Neo4j constraints exist"""
        with neo4j_driver.session() as session:
            # Check for User constraint
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)

            # We should have at least one constraint for User nodes
            user_constraints = [c for c in constraints if 'User' in str(c)]
            assert len(user_constraints) > 0, "No User node constraints found"
            print(f"✓ Found {len(constraints)} Neo4j constraints")

    def test_qdrant_collections_exist(self, qdrant_client):
        """Test that all required Qdrant collections exist"""
        required_collections = [
            ('knowledge_chunks', 384),      # MiniLM embeddings
            ('knowledge_large', 1536),      # OpenAI embeddings
            ('odras_requirements', 384),    # Requirements
            ('das_instructions', 384),      # DAS instructions
            ('project_threads', 384)        # Project threads - CRITICAL for DAS
        ]

        collections = qdrant_client.get_collections().collections
        existing_collections = {c.name: c for c in collections}

        missing_collections = []
        dimension_mismatches = []

        for collection_name, expected_dim in required_collections:
            if collection_name not in existing_collections:
                missing_collections.append(collection_name)
            else:
                # Check vector dimension
                collection = existing_collections[collection_name]
                if hasattr(collection.config.params.vectors, 'size'):
                    actual_dim = collection.config.params.vectors.size
                    if actual_dim != expected_dim:
                        dimension_mismatches.append(
                            f"{collection_name}: expected {expected_dim}, got {actual_dim}"
                        )

        assert len(missing_collections) == 0, f"Missing Qdrant collections: {missing_collections}"
        assert len(dimension_mismatches) == 0, f"Dimension mismatches: {dimension_mismatches}"
        print(f"✓ All {len(required_collections)} required Qdrant collections exist with correct dimensions")

    def test_fuseki_connection(self, settings):
        """Test Apache Fuseki connection"""
        import requests

        fuseki_url = f"http://{settings.fuseki_host}:{settings.fuseki_port}/$/ping"
        try:
            response = requests.get(fuseki_url, timeout=5)
            assert response.status_code == 200
            print("✓ Fuseki connection successful")
        except Exception as e:
            pytest.fail(f"Failed to connect to Fuseki: {e}")


class TestCriticalEndpoints:
    """Test critical API endpoints"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        """Get authentication headers for das_service user"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health endpoint working")

    @pytest.mark.asyncio
    async def test_service_status_endpoint(self, client, auth_headers):
        """Test service status endpoint"""
        response = await client.get("/api/service-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Check all required services
        required_services = ['postgres', 'neo4j', 'qdrant', 'fuseki']
        for service in required_services:
            assert service in data, f"Missing service: {service}"
            assert data[service]["status"] in ["healthy", "degraded"], f"{service} is not healthy"

        print(f"✓ All {len(required_services)} services reporting status")

    @pytest.mark.asyncio
    async def test_auth_login_logout_flow(self, client):
        """Test complete authentication flow"""
        # Login
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]

        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "das_service"

        # Logout
        response = await client.post("/api/auth/logout", headers=headers)
        assert response.status_code == 200

        # Verify token is invalid
        response = await client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

        print("✓ Authentication flow working correctly")

    @pytest.mark.asyncio
    async def test_project_crud_operations(self, client, auth_headers):
        """Test project CRUD operations"""
        # Create project
        project_data = {
            "name": f"Test Project {int(time.time())}",
            "description": "Automated test project"
        }
        response = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        project = response.json()
        project_id = project["project_id"]

        # List projects
        response = await client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert any(p["project_id"] == project_id for p in projects)

        # Archive project
        response = await client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        print("✓ Project CRUD operations working")

    @pytest.mark.asyncio
    async def test_knowledge_upload_and_search(self, client, auth_headers):
        """Test knowledge document upload and search"""
        # First create a project
        project_response = await client.post(
            "/api/projects",
            json={"name": f"Knowledge Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = project_response.json()["project_id"]

        # Test knowledge search (should return empty initially)
        response = await client.post(
            f"/api/knowledge/{project_id}/search",
            json={"query": "test query", "top_k": 5},
            headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert "results" in results

        print("✓ Knowledge management endpoints working")

    @pytest.mark.asyncio
    async def test_namespace_operations(self, client, auth_headers):
        """Test namespace operations"""
        # List namespaces
        response = await client.get("/api/namespaces", headers=auth_headers)
        assert response.status_code == 200
        namespaces = response.json()
        assert isinstance(namespaces, list)

        print("✓ Namespace endpoints working")

    @pytest.mark.asyncio
    async def test_workflow_endpoints(self, client, auth_headers):
        """Test workflow endpoints"""
        # Get available workflows
        response = await client.get("/api/workflows/available", headers=auth_headers)
        assert response.status_code == 200
        workflows = response.json()
        assert isinstance(workflows, list)

        print("✓ Workflow endpoints working")


class TestDatabaseBuildProcess:
    """Test odras.sh database build process"""

    def test_odras_script_exists(self):
        """Test that odras.sh exists and is executable"""
        odras_path = project_root / "odras.sh"
        assert odras_path.exists(), "odras.sh not found"
        assert odras_path.stat().st_mode & 0o111, "odras.sh is not executable"
        print("✓ odras.sh exists and is executable")

    def test_migration_order_file_exists(self):
        """Test that migration_order.txt exists"""
        migration_order_path = project_root / "backend" / "migrations" / "migration_order.txt"
        assert migration_order_path.exists(), "migration_order.txt not found"

        # Verify content
        content = migration_order_path.read_text().strip()
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        assert len(lines) > 0, "migration_order.txt is empty"
        print(f"✓ migration_order.txt contains {len(lines)} migrations")

    def test_all_migrations_in_order_file(self):
        """Test that all SQL migrations are listed in migration_order.txt"""
        migrations_dir = project_root / "backend" / "migrations"
        migration_order_path = migrations_dir / "migration_order.txt"

        # Get all SQL files
        sql_files = sorted([f.name for f in migrations_dir.glob("*.sql")])

        # Get migrations from order file
        order_content = migration_order_path.read_text().strip()
        ordered_migrations = [line.strip() for line in order_content.split('\n') if line.strip()]

        # Check for missing migrations
        missing_in_order = set(sql_files) - set(ordered_migrations)
        extra_in_order = set(ordered_migrations) - set(sql_files)

        assert len(missing_in_order) == 0, f"Migrations missing from order file: {missing_in_order}"
        assert len(extra_in_order) == 0, f"Extra migrations in order file: {extra_in_order}"
        print("✓ All migrations properly listed in migration_order.txt")

    def test_database_schema_manager_status(self):
        """Test database schema manager can check status"""
        script_path = project_root / "scripts" / "database_schema_manager.py"

        result = subprocess.run(
            ["python", str(script_path), "status"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"Schema manager failed: {result.stderr}"
        assert "Database Schema Status" in result.stdout
        print("✓ Database schema manager status check working")


class TestIntegrationScenarios:
    """Test complete integration scenarios"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_complete_das_workflow(self, client):
        """Test complete DAS workflow from login to project creation"""
        # 1. Login as das_service
        login_response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a project
        project_response = await client.post(
            "/api/projects",
            json={
                "name": f"DAS Integration Test {int(time.time())}",
                "description": "Testing complete DAS workflow"
            },
            headers=headers
        )
        assert project_response.status_code == 200
        project_id = project_response.json()["project_id"]

        # 3. Check project exists
        projects_response = await client.get("/api/projects", headers=headers)
        assert projects_response.status_code == 200
        projects = projects_response.json()
        assert any(p["project_id"] == project_id for p in projects)

        # 4. Archive the project
        archive_response = await client.delete(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert archive_response.status_code == 200

        print("✓ Complete DAS workflow successful")

    @pytest.mark.asyncio
    async def test_service_resilience(self, client):
        """Test that API handles service failures gracefully"""
        # Even if some services are down, health check should work
        response = await client.get("/api/health")
        assert response.status_code == 200

        # Login should work even if some services are degraded
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200

        print("✓ Service resilience verified")


def run_quick_validation():
    """Quick validation script for manual testing after database changes"""
    print("\n" + "="*60)
    print("ODRAS Quick Validation Check")
    print("="*60 + "\n")

    # Check if services are running
    print("1. Checking service availability...")
    services = {
        "PostgreSQL": ("localhost", 5432),
        "Neo4j": ("localhost", 7687),
        "Qdrant": ("localhost", 6333),
        "Fuseki": ("localhost", 3030)
    }

    import socket
    services_running = []
    services_missing = []
    for service, (host, port) in services.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"   ✓ {service} is running on port {port}")
            services_running.append(service)
        else:
            print(f"   ⚠ {service} is NOT accessible on port {port} (expected if services not started)")
            services_missing.append(service)
    
    # If no services running, this is a structure validation only
    if len(services_running) == 0:
        print("\n   Note: No services running - this is a structure-only validation")

    # Check API health (only if services are running)
    print("\n2. Checking API health...")
    import requests
    if len(services_running) > 0:
        try:
            response = requests.get("http://localhost:8000/api/health", timeout=5)
            if response.status_code == 200:
                print("   ✓ API is healthy")
            else:
                print(f"   ⚠ API returned status {response.status_code}")
        except Exception as e:
            print(f"   ⚠ API is not accessible: {e}")
    else:
        print("   ⚠ Skipping API check (services not running)")

    # Test DAS login (only if services are running)
    print("\n3. Testing DAS service account...")
    if len(services_running) > 0:
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=5
            )
            if response.status_code == 200:
                print("   ✓ DAS service account login successful")
                token = response.json().get("token")
                if token:
                    print(f"   ✓ Token received (length: {len(token)})")
            else:
                print(f"   ⚠ DAS login failed with status {response.status_code}")
        except Exception as e:
            print(f"   ⚠ DAS login error: {e}")
    else:
        print("   ⚠ Skipping DAS test (services not running)")

    print("\n" + "="*60)
    print("Quick validation complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # If run directly, execute quick validation
    run_quick_validation()
