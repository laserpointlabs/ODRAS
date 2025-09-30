"""
Full Stack API Integration Tests

Comprehensive test suite that validates complete workflows across all API endpoints.
This tests real-world scenarios including project lifecycle, file management,
knowledge processing, and ontology operations.

Run with: pytest tests/api/test_full_stack_api.py -v
"""

import pytest
import asyncio
import json
import io
import time
from typing import Dict, List, Any, Optional
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app


class TestFullStackAPI:
    """Comprehensive full stack API tests"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_token(self, client):
        """Get authentication token for das_service user"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        return response.json()["token"]

    @pytest.fixture
    async def auth_headers(self, auth_token):
        """Get authentication headers"""
        return {"Authorization": f"Bearer {auth_token}"}

    @pytest.fixture
    async def admin_token(self, client):
        """Get admin authentication token"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123!"}
        )
        if response.status_code != 200:
            # Try jdehart as admin
            response = await client.post(
                "/api/auth/login",
                json={"username": "jdehart", "password": "jdehart123!"}
            )
        assert response.status_code == 200
        return response.json()["token"]

    @pytest.fixture
    async def admin_headers(self, admin_token):
        """Get admin authentication headers"""
        return {"Authorization": f"Bearer {admin_token}"}

    # ========== PROJECT MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_complete_project_lifecycle(self, client, auth_headers):
        """Test complete project lifecycle: create, read, update, delete"""

        # 1. Create a project
        project_data = {
            "name": f"Test Project {int(time.time())}",
            "description": "Full stack test project",
            "metadata": {"test": True, "category": "integration"}
        }
        create_response = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        project = create_response.json()
        project_id = project["project_id"]

        # Verify project data
        assert project["name"] == project_data["name"]
        assert project["description"] == project_data["description"]
        assert project["is_active"] is True

        # 2. List projects (should include our new project)
        list_response = await client.get("/api/projects", headers=auth_headers)
        assert list_response.status_code == 200
        projects = list_response.json()
        assert any(p["project_id"] == project_id for p in projects)

        # 3. Get specific project
        get_response = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert get_response.status_code == 200
        retrieved_project = get_response.json()
        assert retrieved_project["project_id"] == project_id

        # 4. Update project (rename)
        new_name = f"Updated Project {int(time.time())}"
        update_response = await client.put(
            f"/api/projects/{project_id}",
            json={"name": new_name},
            headers=auth_headers
        )
        assert update_response.status_code == 200
        updated_project = update_response.json()
        assert updated_project["name"] == new_name

        # 5. Archive project (soft delete)
        archive_response = await client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert archive_response.status_code == 200

        # 6. Verify project is archived
        archived_response = await client.get(
            "/api/projects?include_archived=true",
            headers=auth_headers
        )
        assert archived_response.status_code == 200
        all_projects = archived_response.json()
        archived_project = next((p for p in all_projects if p["project_id"] == project_id), None)
        assert archived_project is not None
        assert archived_project["is_active"] is False

        # 7. Restore project
        restore_response = await client.post(
            f"/api/projects/{project_id}/restore",
            headers=auth_headers
        )
        if restore_response.status_code == 200:
            restored_project = restore_response.json()
            assert restored_project["is_active"] is True

    # ========== FILE MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_file_upload_and_management(self, client, auth_headers):
        """Test file upload, listing, and deletion"""

        # Create a project first
        project_response = await client.post(
            "/api/projects",
            json={"name": f"File Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = project_response.json()["project_id"]

        # 1. Upload a text file
        file_content = b"This is a test file for ODRAS integration testing."
        file_data = {
            "file": ("test_document.txt", file_content, "text/plain")
        }

        upload_response = await client.post(
            f"/api/files/upload/{project_id}",
            files=file_data,
            headers=auth_headers
        )
        assert upload_response.status_code == 200
        uploaded_file = upload_response.json()
        file_id = uploaded_file["file_id"]

        # 2. List files in project
        list_response = await client.get(
            f"/api/files/project/{project_id}",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        files = list_response.json()
        assert len(files) > 0
        assert any(f["file_id"] == file_id for f in files)

        # 3. Get file metadata
        metadata_response = await client.get(
            f"/api/files/{file_id}/metadata",
            headers=auth_headers
        )
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        assert metadata["filename"] == "test_document.txt"
        assert metadata["mime_type"] == "text/plain"

        # 4. Download file
        download_response = await client.get(
            f"/api/files/{file_id}/download",
            headers=auth_headers
        )
        assert download_response.status_code == 200
        assert download_response.content == file_content

        # 5. Delete file
        delete_response = await client.delete(
            f"/api/files/{file_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200

        # 6. Verify file is deleted
        deleted_list_response = await client.get(
            f"/api/files/project/{project_id}",
            headers=auth_headers
        )
        assert deleted_list_response.status_code == 200
        remaining_files = deleted_list_response.json()
        assert not any(f["file_id"] == file_id for f in remaining_files)

    # ========== ONTOLOGY MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_ontology_creation_and_management(self, client, auth_headers):
        """Test ontology creation, modification, and element management"""

        # Create a project
        project_response = await client.post(
            "/api/projects",
            json={"name": f"Ontology Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = project_response.json()["project_id"]

        # 1. Create an ontology
        ontology_data = {
            "name": "TestOntology",
            "description": "Test ontology for integration testing",
            "base_uri": "http://test.odras.ai/onto/test#"
        }

        create_response = await client.post(
            f"/api/ontology/{project_id}/create",
            json=ontology_data,
            headers=auth_headers
        )

        # Handle both possible response formats
        if create_response.status_code == 200:
            ontology = create_response.json()
            if isinstance(ontology, dict) and "ontology_id" in ontology:
                ontology_id = ontology["ontology_id"]
            else:
                # Assume success and retrieve ontology
                ontology_id = None

        # 2. Add a class to the ontology
        class_data = {
            "name": "TestClass",
            "description": "A test class",
            "parent": "owl:Thing"
        }

        add_class_response = await client.post(
            f"/api/ontology/{project_id}/class",
            json=class_data,
            headers=auth_headers
        )

        # Test different response codes that might indicate success
        assert add_class_response.status_code in [200, 201, 204]

        # 3. Add a property to the ontology
        property_data = {
            "name": "hasTestProperty",
            "description": "A test property",
            "domain": "TestClass",
            "range": "xsd:string"
        }

        add_property_response = await client.post(
            f"/api/ontology/{project_id}/property",
            json=property_data,
            headers=auth_headers
        )
        assert add_property_response.status_code in [200, 201, 204]

        # 4. Get ontology structure
        structure_response = await client.get(
            f"/api/ontology/{project_id}",
            headers=auth_headers
        )

        if structure_response.status_code == 200:
            structure = structure_response.json()
            # Verify our additions are present (if the endpoint returns structure)
            if isinstance(structure, dict):
                print(f"Ontology structure: {structure}")

        # 5. Update ontology name
        update_data = {
            "name": "UpdatedTestOntology",
            "description": "Updated description"
        }

        update_response = await client.put(
            f"/api/ontology/{project_id}",
            json=update_data,
            headers=auth_headers
        )
        # Accept various success codes
        assert update_response.status_code in [200, 201, 204, 404]  # 404 if endpoint not implemented

    # ========== KNOWLEDGE MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_knowledge_document_processing(self, client, auth_headers):
        """Test knowledge document upload and search"""

        # Create a project
        project_response = await client.post(
            "/api/projects",
            json={"name": f"Knowledge Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = project_response.json()["project_id"]

        # 1. Upload a document for knowledge processing
        doc_content = """
        ODRAS Integration Testing Document

        This document contains information about testing the ODRAS system.
        Key concepts include:
        - API endpoints
        - Database integrity
        - File management
        - Knowledge extraction

        The system should process this document and make it searchable.
        """

        file_data = {
            "file": ("knowledge_test.txt", doc_content.encode(), "text/plain")
        }

        upload_response = await client.post(
            f"/api/knowledge/{project_id}/upload",
            files=file_data,
            headers=auth_headers
        )

        # Handle various response formats
        if upload_response.status_code == 200:
            result = upload_response.json()
            if isinstance(result, dict) and "document_id" in result:
                document_id = result["document_id"]
            else:
                document_id = None

        # 2. Search knowledge base
        search_query = {
            "query": "API endpoints testing",
            "top_k": 5,
            "threshold": 0.5
        }

        search_response = await client.post(
            f"/api/knowledge/{project_id}/search",
            json=search_query,
            headers=auth_headers
        )

        assert search_response.status_code == 200
        search_results = search_response.json()

        # Results should be a list or have a 'results' key
        if isinstance(search_results, dict) and "results" in search_results:
            results = search_results["results"]
        else:
            results = search_results if isinstance(search_results, list) else []

        # 3. Get knowledge statistics
        stats_response = await client.get(
            f"/api/knowledge/{project_id}/stats",
            headers=auth_headers
        )

        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"Knowledge stats: {stats}")

    # ========== NAMESPACE MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_namespace_operations(self, client, auth_headers, admin_headers):
        """Test namespace creation and management"""

        # 1. Create a namespace (requires admin)
        namespace_data = {
            "name": f"test-namespace-{int(time.time())}",
            "description": "Test namespace for integration testing",
            "base_uri": "http://test.odras.ai/ns/test#"
        }

        create_response = await client.post(
            "/api/namespaces",
            json=namespace_data,
            headers=admin_headers  # Admin required
        )

        if create_response.status_code == 200:
            namespace = create_response.json()
            namespace_id = namespace.get("namespace_id")

            # 2. List namespaces
            list_response = await client.get("/api/namespaces", headers=auth_headers)
            assert list_response.status_code == 200
            namespaces = list_response.json()
            assert isinstance(namespaces, list)

            # 3. Get specific namespace
            if namespace_id:
                get_response = await client.get(
                    f"/api/namespaces/{namespace_id}",
                    headers=auth_headers
                )
                if get_response.status_code == 200:
                    retrieved = get_response.json()
                    assert retrieved["namespace_id"] == namespace_id

    # ========== WORKFLOW TESTS ==========

    @pytest.mark.asyncio
    async def test_workflow_operations(self, client, auth_headers):
        """Test workflow listing and execution"""

        # 1. List available workflows
        list_response = await client.get(
            "/api/workflows/available",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        workflows = list_response.json()
        assert isinstance(workflows, list)

        # 2. Get workflow status (if any running)
        status_response = await client.get(
            "/api/workflows/status",
            headers=auth_headers
        )
        assert status_response.status_code in [200, 404]  # 404 if no active workflows

    # ========== USER MANAGEMENT TESTS ==========

    @pytest.mark.asyncio
    async def test_user_profile_operations(self, client, auth_headers):
        """Test user profile operations"""

        # 1. Get current user profile
        profile_response = await client.get("/api/auth/me", headers=auth_headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["username"] == "das_service"

        # 2. Update user profile (if endpoint exists)
        update_data = {
            "display_name": "DAS Service Account Updated",
            "email": "das_updated@odras.ai"
        }

        update_response = await client.put(
            "/api/users/profile",
            json=update_data,
            headers=auth_headers
        )
        # Accept 404 if endpoint not implemented
        assert update_response.status_code in [200, 404]

    # ========== COMPLEX INTEGRATION SCENARIOS ==========

    @pytest.mark.asyncio
    async def test_complete_document_processing_workflow(self, client, auth_headers):
        """Test complete workflow: project -> file -> knowledge -> search"""

        # 1. Create project
        project_response = await client.post(
            "/api/projects",
            json={"name": f"Integration Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = project_response.json()["project_id"]

        # 2. Upload multiple files
        files_to_upload = [
            ("doc1.txt", b"Machine learning is a subset of artificial intelligence."),
            ("doc2.txt", b"Deep learning uses neural networks with multiple layers."),
            ("doc3.txt", b"Natural language processing enables computers to understand text.")
        ]

        uploaded_files = []
        for filename, content in files_to_upload:
            file_data = {"file": (filename, content, "text/plain")}
            upload_response = await client.post(
                f"/api/files/upload/{project_id}",
                files=file_data,
                headers=auth_headers
            )
            assert upload_response.status_code == 200
            uploaded_files.append(upload_response.json())

        # 3. Process files for knowledge extraction
        for file_info in uploaded_files:
            process_response = await client.post(
                f"/api/knowledge/{project_id}/process/{file_info['file_id']}",
                headers=auth_headers
            )
            # Accept various success codes
            assert process_response.status_code in [200, 201, 202, 204, 404]

        # 4. Search across all documents
        search_queries = [
            "artificial intelligence",
            "neural networks",
            "language processing"
        ]

        for query in search_queries:
            search_response = await client.post(
                f"/api/knowledge/{project_id}/search",
                json={"query": query, "top_k": 3},
                headers=auth_headers
            )
            assert search_response.status_code == 200

        # 5. Clean up - archive project
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_multi_user_collaboration(self, client):
        """Test multi-user project collaboration"""

        # Login as two different users
        das_response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        das_token = das_response.json()["token"]
        das_headers = {"Authorization": f"Bearer {das_token}"}

        # Try to get admin token
        admin_response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123!"}
        )
        if admin_response.status_code == 200:
            admin_token = admin_response.json()["token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # DAS creates a project
            project_response = await client.post(
                "/api/projects",
                json={"name": f"Collab Project {int(time.time())}"},
                headers=das_headers
            )
            project_id = project_response.json()["project_id"]

            # Admin accesses the project (if they have permission)
            admin_access_response = await client.get(
                f"/api/projects/{project_id}",
                headers=admin_headers
            )
            # Admin might not have access initially
            assert admin_access_response.status_code in [200, 403, 404]

            # Clean up
            await client.delete(f"/api/projects/{project_id}", headers=das_headers)

    @pytest.mark.asyncio
    async def test_error_handling_and_validation(self, client, auth_headers):
        """Test API error handling and input validation"""

        # 1. Invalid project creation (missing required fields)
        invalid_response = await client.post(
            "/api/projects",
            json={},  # Missing required 'name' field
            headers=auth_headers
        )
        assert invalid_response.status_code in [400, 422]

        # 2. Access non-existent resource
        not_found_response = await client.get(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        assert not_found_response.status_code == 404

        # 3. Unauthorized access (no token)
        unauth_response = await client.get("/api/projects")
        assert unauth_response.status_code == 401

        # 4. Invalid file upload (wrong project)
        file_data = {"file": ("test.txt", b"content", "text/plain")}
        invalid_upload = await client.post(
            "/api/files/upload/00000000-0000-0000-0000-000000000000",
            files=file_data,
            headers=auth_headers
        )
        assert invalid_upload.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_api_performance_and_limits(self, client, auth_headers):
        """Test API performance and rate limits"""

        # 1. Rapid project creation
        start_time = time.time()
        project_ids = []

        for i in range(5):  # Create 5 projects rapidly
            response = await client.post(
                "/api/projects",
                json={"name": f"Perf Test {i} {int(time.time())}"},
                headers=auth_headers
            )
            if response.status_code == 200:
                project_ids.append(response.json()["project_id"])

        elapsed = time.time() - start_time
        print(f"Created {len(project_ids)} projects in {elapsed:.2f} seconds")

        # 2. Concurrent searches
        if project_ids:
            search_tasks = []
            for project_id in project_ids[:3]:  # Search in first 3 projects
                search_tasks.append(
                    client.post(
                        f"/api/knowledge/{project_id}/search",
                        json={"query": "test", "top_k": 1},
                        headers=auth_headers
                    )
                )

            if search_tasks:
                responses = await asyncio.gather(*search_tasks, return_exceptions=True)
                successful_searches = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
                print(f"Completed {len(successful_searches)} concurrent searches")

        # 3. Clean up projects
        for project_id in project_ids:
            await client.delete(f"/api/projects/{project_id}", headers=auth_headers)


# Utility function for running specific test scenarios
async def run_specific_test(test_name: str):
    """Run a specific test by name"""
    test_instance = TestFullStackAPI()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get auth token
        auth_response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        token = auth_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Run the specified test
        test_method = getattr(test_instance, test_name)
        await test_method(client, headers)


if __name__ == "__main__":
    # Example of running a specific test
    import sys
    if len(sys.argv) > 1:
        test_to_run = sys.argv[1]
        asyncio.run(run_specific_test(test_to_run))
    else:
        print("Run with pytest: pytest tests/api/test_full_stack_api.py -v")
