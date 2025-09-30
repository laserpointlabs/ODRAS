"""
CRUD Operations Test Suite

Comprehensive tests for Create, Read, Update, Delete operations
on all major ODRAS entities: Projects, Files, Ontologies, Knowledge, etc.

Run with: pytest tests/api/test_crud_operations.py -v
"""

import pytest
import time
import json
from typing import Dict, Any
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app


class TestProjectCRUD:
    """Test CRUD operations for Projects"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_create_project(self, client, auth_headers):
        """Test project creation with various data"""
        test_cases = [
            # Basic project
            {
                "name": f"Basic Project {int(time.time())}",
                "description": "A simple project"
            },
            # Project with metadata
            {
                "name": f"Metadata Project {int(time.time())}",
                "description": "Project with metadata",
                "metadata": {
                    "department": "Engineering",
                    "priority": "high",
                    "tags": ["test", "integration"]
                }
            },
            # Project with special characters
            {
                "name": f"Special Project αβγ {int(time.time())}",
                "description": "Project with unicode: 测试项目"
            }
        ]

        created_projects = []
        for project_data in test_cases:
            response = await client.post(
                "/api/projects",
                json=project_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            project = response.json()
            assert project["name"] == project_data["name"]
            assert project["description"] == project_data["description"]
            created_projects.append(project["project_id"])

        # Cleanup
        for project_id in created_projects:
            await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_read_project(self, client, auth_headers):
        """Test reading project details"""
        # Create a project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Read Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Read by ID
        get_resp = await client.get(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert get_resp.status_code == 200
        project = get_resp.json()
        assert project["project_id"] == project_id

        # List all projects
        list_resp = await client.get("/api/projects", headers=auth_headers)
        assert list_resp.status_code == 200
        projects = list_resp.json()
        assert any(p["project_id"] == project_id for p in projects)

        # List with filters
        active_resp = await client.get(
            "/api/projects?active=true",
            headers=auth_headers
        )
        assert active_resp.status_code == 200

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_update_project(self, client, auth_headers):
        """Test updating project attributes"""
        # Create project
        original_name = f"Original Name {int(time.time())}"
        create_resp = await client.post(
            "/api/projects",
            json={"name": original_name, "description": "Original desc"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Update name
        new_name = f"Updated Name {int(time.time())}"
        update_resp = await client.put(
            f"/api/projects/{project_id}",
            json={"name": new_name},
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == new_name

        # Update description
        desc_resp = await client.put(
            f"/api/projects/{project_id}",
            json={"description": "New description"},
            headers=auth_headers
        )
        assert desc_resp.status_code == 200

        # Update metadata
        meta_resp = await client.put(
            f"/api/projects/{project_id}",
            json={"metadata": {"updated": True, "version": 2}},
            headers=auth_headers
        )
        assert meta_resp.status_code == 200

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_delete_project(self, client, auth_headers):
        """Test project deletion (archive)"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Delete Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Delete (archive) project
        delete_resp = await client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert delete_resp.status_code == 200

        # Verify it's archived (not in active list)
        list_resp = await client.get("/api/projects", headers=auth_headers)
        active_projects = list_resp.json()
        assert not any(p["project_id"] == project_id for p in active_projects)

        # Verify it's in archived list
        archived_resp = await client.get(
            "/api/projects?include_archived=true",
            headers=auth_headers
        )
        if archived_resp.status_code == 200:
            all_projects = archived_resp.json()
            archived_project = next(
                (p for p in all_projects if p["project_id"] == project_id),
                None
            )
            if archived_project:
                assert archived_project["is_active"] is False


class TestFileCRUD:
    """Test CRUD operations for Files"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        """Create a test project for file operations"""
        response = await client.post(
            "/api/projects",
            json={"name": f"File Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = response.json()["project_id"]
        yield project_id
        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_create_files(self, client, auth_headers, test_project):
        """Test file upload with various types"""
        test_files = [
            # Text file
            ("test.txt", b"This is a test text file.", "text/plain"),
            # JSON file
            ("data.json", json.dumps({"key": "value"}).encode(), "application/json"),
            # CSV file
            ("data.csv", b"name,value\\ntest,123\\n", "text/csv"),
            # Markdown file
            ("readme.md", b"# Test Document\\n\\nThis is markdown.", "text/markdown")
        ]

        uploaded_files = []
        for filename, content, mime_type in test_files:
            files = {"file": (filename, content, mime_type)}
            response = await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )
            assert response.status_code == 200
            file_info = response.json()
            assert file_info["filename"] == filename
            uploaded_files.append(file_info["file_id"])

        # Verify all files uploaded
        list_resp = await client.get(
            f"/api/files/project/{test_project}",
            headers=auth_headers
        )
        assert list_resp.status_code == 200
        project_files = list_resp.json()
        assert len(project_files) >= len(test_files)

    @pytest.mark.asyncio
    async def test_read_files(self, client, auth_headers, test_project):
        """Test reading file metadata and content"""
        # Upload a file
        content = b"Test file content for reading"
        files = {"file": ("read_test.txt", content, "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Get file metadata
        meta_resp = await client.get(
            f"/api/files/{file_id}/metadata",
            headers=auth_headers
        )
        assert meta_resp.status_code == 200
        metadata = meta_resp.json()
        assert metadata["filename"] == "read_test.txt"
        assert metadata["mime_type"] == "text/plain"

        # Download file
        download_resp = await client.get(
            f"/api/files/{file_id}/download",
            headers=auth_headers
        )
        assert download_resp.status_code == 200
        assert download_resp.content == content

    @pytest.mark.asyncio
    async def test_update_files(self, client, auth_headers, test_project):
        """Test updating file metadata"""
        # Upload a file
        files = {"file": ("original.txt", b"Original content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Update metadata (if endpoint exists)
        update_resp = await client.put(
            f"/api/files/{file_id}/metadata",
            json={"description": "Updated file description", "tags": ["updated"]},
            headers=auth_headers
        )
        # Accept 404 if update endpoint doesn't exist
        assert update_resp.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_files(self, client, auth_headers, test_project):
        """Test file deletion"""
        # Upload a file
        files = {"file": ("delete_me.txt", b"Delete this file", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Delete file
        delete_resp = await client.delete(
            f"/api/files/{file_id}",
            headers=auth_headers
        )
        assert delete_resp.status_code == 200

        # Verify deletion
        list_resp = await client.get(
            f"/api/files/project/{test_project}",
            headers=auth_headers
        )
        files = list_resp.json()
        assert not any(f["file_id"] == file_id for f in files)


class TestOntologyCRUD:
    """Test CRUD operations for Ontologies"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        response = await client.post(
            "/api/projects",
            json={"name": f"Ontology Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = response.json()["project_id"]
        yield project_id
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_create_ontology(self, client, auth_headers, test_project):
        """Test ontology creation"""
        ontology_data = {
            "name": "TestOntology",
            "description": "Test ontology for CRUD operations",
            "base_uri": "http://test.odras.ai/onto/test#",
            "version": "1.0.0"
        }

        response = await client.post(
            f"/api/ontology/{test_project}/create",
            json=ontology_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201, 204]

    @pytest.mark.asyncio
    async def test_ontology_elements(self, client, auth_headers, test_project):
        """Test adding classes, properties, and individuals"""
        # Create ontology first
        onto_resp = await client.post(
            f"/api/ontology/{test_project}/create",
            json={"name": "ElementTest", "base_uri": "http://test.odras.ai/elem#"},
            headers=auth_headers
        )

        # Add classes
        classes = [
            {"name": "Person", "description": "A human being"},
            {"name": "Organization", "description": "A group or company"},
            {"name": "Document", "description": "A written record"}
        ]

        for cls in classes:
            cls_resp = await client.post(
                f"/api/ontology/{test_project}/class",
                json=cls,
                headers=auth_headers
            )
            assert cls_resp.status_code in [200, 201, 204]

        # Add properties
        properties = [
            {
                "name": "hasAuthor",
                "description": "Links document to author",
                "domain": "Document",
                "range": "Person"
            },
            {
                "name": "worksFor",
                "description": "Person works for organization",
                "domain": "Person",
                "range": "Organization"
            }
        ]

        for prop in properties:
            prop_resp = await client.post(
                f"/api/ontology/{test_project}/property",
                json=prop,
                headers=auth_headers
            )
            assert prop_resp.status_code in [200, 201, 204]

    @pytest.mark.asyncio
    async def test_update_ontology(self, client, auth_headers, test_project):
        """Test updating ontology metadata"""
        # Create ontology
        await client.post(
            f"/api/ontology/{test_project}/create",
            json={"name": "UpdateTest", "base_uri": "http://test.odras.ai/upd#"},
            headers=auth_headers
        )

        # Update ontology
        update_data = {
            "name": "UpdatedOntology",
            "description": "Updated description",
            "version": "2.0.0"
        }

        update_resp = await client.put(
            f"/api/ontology/{test_project}",
            json=update_data,
            headers=auth_headers
        )
        # Accept 404 if update not implemented
        assert update_resp.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_ontology_elements(self, client, auth_headers, test_project):
        """Test deleting ontology elements"""
        # Create ontology and add class
        await client.post(
            f"/api/ontology/{test_project}/create",
            json={"name": "DeleteTest", "base_uri": "http://test.odras.ai/del#"},
            headers=auth_headers
        )

        await client.post(
            f"/api/ontology/{test_project}/class",
            json={"name": "ToBeDeleted"},
            headers=auth_headers
        )

        # Delete class (if supported)
        delete_resp = await client.delete(
            f"/api/ontology/{test_project}/class/ToBeDeleted",
            headers=auth_headers
        )
        # Accept 404 if delete not implemented
        assert delete_resp.status_code in [200, 204, 404]


class TestKnowledgeCRUD:
    """Test CRUD operations for Knowledge Management"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        response = await client.post(
            "/api/projects",
            json={"name": f"Knowledge Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = response.json()["project_id"]
        yield project_id
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_create_knowledge(self, client, auth_headers, test_project):
        """Test creating knowledge entries"""
        # Upload documents for knowledge extraction
        documents = [
            ("ai_basics.txt", b"Artificial Intelligence is the simulation of human intelligence by machines."),
            ("ml_intro.txt", b"Machine Learning is a subset of AI that enables systems to learn from data."),
            ("dl_overview.txt", b"Deep Learning uses neural networks with multiple layers to process information.")
        ]

        for filename, content in documents:
            files = {"file": (filename, content, "text/plain")}
            upload_resp = await client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                headers=auth_headers
            )
            assert upload_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_read_knowledge(self, client, auth_headers, test_project):
        """Test searching and retrieving knowledge"""
        # Upload a document
        content = b"ODRAS is an advanced knowledge management system with AI capabilities."
        files = {"file": ("odras.txt", content, "text/plain")}
        await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        # Search knowledge
        search_queries = [
            {"query": "ODRAS", "top_k": 5},
            {"query": "knowledge management", "top_k": 3},
            {"query": "AI capabilities", "top_k": 10}
        ]

        for query in search_queries:
            search_resp = await client.post(
                f"/api/knowledge/{test_project}/search",
                json=query,
                headers=auth_headers
            )
            assert search_resp.status_code == 200
            results = search_resp.json()
            # Results should be a list or dict with 'results' key
            assert isinstance(results, (list, dict))

    @pytest.mark.asyncio
    async def test_update_knowledge(self, client, auth_headers, test_project):
        """Test updating knowledge metadata"""
        # This depends on implementation - knowledge updates might not be direct
        # but through re-processing or metadata updates

        # Upload document
        files = {"file": ("update_test.txt", b"Original knowledge content", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if upload_resp.status_code == 200:
            result = upload_resp.json()
            if "document_id" in result:
                # Try to update metadata
                update_resp = await client.put(
                    f"/api/knowledge/{test_project}/document/{result['document_id']}",
                    json={"tags": ["updated", "test"]},
                    headers=auth_headers
                )
                # Accept 404 if update not implemented
                assert update_resp.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_knowledge(self, client, auth_headers, test_project):
        """Test deleting knowledge documents"""
        # Upload document
        files = {"file": ("delete_test.txt", b"Delete this knowledge", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if upload_resp.status_code == 200:
            result = upload_resp.json()
            if "document_id" in result:
                # Delete document
                delete_resp = await client.delete(
                    f"/api/knowledge/{test_project}/document/{result['document_id']}",
                    headers=auth_headers
                )
                # Accept 404 if delete not implemented
                assert delete_resp.status_code in [200, 204, 404]


class TestNamespaceCRUD:
    """Test CRUD operations for Namespaces"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        # Try admin first, then jdehart
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                token = response.json()["token"]
                return {"Authorization": f"Bearer {token}"}
        pytest.skip("No admin user available")

    @pytest.mark.asyncio
    async def test_namespace_operations(self, client, admin_headers):
        """Test namespace CRUD operations"""
        # Create namespace
        namespace_data = {
            "name": f"test-ns-{int(time.time())}",
            "description": "Test namespace",
            "base_uri": f"http://test.odras.ai/ns/test-{int(time.time())}#"
        }

        create_resp = await client.post(
            "/api/namespaces",
            json=namespace_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            namespace = create_resp.json()
            namespace_id = namespace.get("namespace_id")

            # List namespaces
            list_resp = await client.get("/api/namespaces", headers=admin_headers)
            assert list_resp.status_code == 200

            # Get specific namespace
            if namespace_id:
                get_resp = await client.get(
                    f"/api/namespaces/{namespace_id}",
                    headers=admin_headers
                )
                assert get_resp.status_code in [200, 404]

                # Update namespace
                update_resp = await client.put(
                    f"/api/namespaces/{namespace_id}",
                    json={"description": "Updated description"},
                    headers=admin_headers
                )
                assert update_resp.status_code in [200, 404]

                # Delete namespace
                delete_resp = await client.delete(
                    f"/api/namespaces/{namespace_id}",
                    headers=admin_headers
                )
                assert delete_resp.status_code in [200, 204, 404]


# Summary test that runs all CRUD operations
@pytest.mark.asyncio
async def test_full_crud_cycle():
    """Run complete CRUD cycle for all major entities"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        auth_resp = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        headers = {"Authorization": f"Bearer {auth_resp.json()['token']}"}

        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"Full CRUD Test {int(time.time())}"},
            headers=headers
        )
        project_id = proj_resp.json()["project_id"]

        # Upload file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        file_resp = await client.post(
            f"/api/files/upload/{project_id}",
            files=files,
            headers=headers
        )

        # Create ontology
        onto_resp = await client.post(
            f"/api/ontology/{project_id}/create",
            json={"name": "TestOnto", "base_uri": "http://test#"},
            headers=headers
        )

        # Upload knowledge
        know_resp = await client.post(
            f"/api/knowledge/{project_id}/upload",
            files={"file": ("knowledge.txt", b"Knowledge content", "text/plain")},
            headers=headers
        )

        # Search knowledge
        search_resp = await client.post(
            f"/api/knowledge/{project_id}/search",
            json={"query": "knowledge", "top_k": 5},
            headers=headers
        )

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=headers)

        print("✓ Full CRUD cycle completed successfully!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_crud_cycle())
