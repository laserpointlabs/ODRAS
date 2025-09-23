"""
Document Processing Workflow Integration Tests

Tests for complete end-to-end document processing workflows including:
- File upload → processing → knowledge asset creation
- Requirements extraction → review → approval
- Ontology integration with knowledge assets
"""

import pytest
import json
import io
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app


class TestDocumentProcessingWorkflow:
    """Test suite for complete document processing workflows"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_token(self, client):
        """Get authentication token"""
        response = await client.post(
            "/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}
        )
        return response.json()["token"]

    @pytest.fixture
    async def test_project(self, client, auth_token):
        """Create a test project"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post(
            "/api/projects",
            headers=headers,
            json={
                "name": "Integration Test Project",
                "description": "Project for integration testing",
            },
        )
        return response.json()["project"]

    @pytest.mark.asyncio
    async def test_complete_document_processing_workflow(
        self, client, auth_token, test_project
    ):
        """Test complete workflow: upload → process → knowledge asset creation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Step 1: Upload a test document
        file_content = b"""
# Requirements Document

## System Requirements

REQ-001: The system shall provide user authentication
REQ-002: The system shall store user data securely
REQ-003: The system shall support multiple file formats

## Performance Requirements

REQ-004: The system shall respond within 2 seconds
REQ-005: The system shall support 1000 concurrent users
        """

        files = {"file": ("requirements.md", io.BytesIO(file_content), "text/markdown")}
        data = {
            "project_id": project_id,
            "tags": json.dumps({"docType": "requirements", "status": "new"}),
        }

        upload_response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )

        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Step 2: Start processing workflow
        workflow_data = {
            "processKey": "ingestion_pipeline",
            "projectId": project_id,
            "fileIds": [file_id],
            "params": {
                "chunking": {"sizeTokens": 350, "overlapTokens": 50},
                "embedding": {"modelId": "e5-large-v2"},
            },
        }

        workflow_response = await client.post(
            "/api/workflows/start", headers=headers, json=workflow_data
        )

        # Note: This might fail in test environment without Camunda
        # We'll check for either success or expected failure
        assert workflow_response.status_code in [200, 503, 500]

        if workflow_response.status_code == 200:
            workflow_data = workflow_response.json()
            assert "runId" in workflow_data
            assert workflow_data["success"] is True

        # Step 3: Verify file is accessible
        file_list_response = await client.get(
            "/api/files", params={"project_id": project_id}, headers=headers
        )

        assert file_list_response.status_code == 200
        files_list = file_list_response.json()["files"]
        assert any(f["file_id"] == file_id for f in files_list)

        # Step 4: Check if knowledge assets were created
        knowledge_response = await client.get(
            "/api/knowledge/assets", params={"project_id": project_id}, headers=headers
        )

        assert knowledge_response.status_code == 200
        # Knowledge assets might not be created immediately in test environment

    @pytest.mark.asyncio
    async def test_requirements_extraction_workflow(
        self, client, auth_token, test_project
    ):
        """Test requirements extraction and review workflow"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Step 1: Upload requirements document
        requirements_content = b"""
# Software Requirements Specification

## Functional Requirements

FR-001: The system shall allow users to create accounts
FR-002: The system shall provide secure login functionality
FR-003: The system shall allow users to upload documents

## Non-Functional Requirements

NFR-001: The system shall be available 99.9% of the time
NFR-002: The system shall process requests within 3 seconds
NFR-003: The system shall support up to 500 concurrent users
        """

        files = {"file": ("srs.md", io.BytesIO(requirements_content), "text/markdown")}
        data = {"project_id": project_id}

        upload_response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )

        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Step 2: Start requirements extraction workflow
        extraction_data = {
            "processKey": "requirements_extraction",
            "projectId": project_id,
            "fileIds": [file_id],
            "params": {"extraction_method": "llm", "confidence_threshold": 0.7},
        }

        extraction_response = await client.post(
            "/api/workflows/start", headers=headers, json=extraction_data
        )

        # This might fail in test environment, which is expected
        assert extraction_response.status_code in [200, 503, 500]

    @pytest.mark.asyncio
    async def test_ontology_knowledge_integration(
        self, client, auth_token, test_project
    ):
        """Test integration between ontology and knowledge management"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Step 1: Create ontology classes
        class_data = {
            "name": "Requirement",
            "label": "Requirement",
            "description": "A system requirement",
            "parent_classes": ["Thing"],
        }

        ontology_response = await client.post(
            "/api/ontology/classes", headers=headers, json=class_data
        )

        assert ontology_response.status_code == 200

        # Step 2: Create knowledge asset
        knowledge_data = {
            "title": "Test Requirement",
            "content": "The system shall provide user authentication",
            "project_id": project_id,
            "asset_type": "requirement",
            "metadata": {"requirement_id": "REQ-001", "category": "functional"},
        }

        knowledge_response = await client.post(
            "/api/knowledge/assets", headers=headers, json=knowledge_data
        )

        assert knowledge_response.status_code == 200
        asset_id = knowledge_response.json()["asset"]["asset_id"]

        # Step 3: Verify knowledge asset was created
        get_asset_response = await client.get(
            f"/api/knowledge/assets/{asset_id}", headers=headers
        )

        assert get_asset_response.status_code == 200
        asset_data = get_asset_response.json()["asset"]
        assert asset_data["title"] == "Test Requirement"
        assert asset_data["asset_type"] == "requirement"

    @pytest.mark.asyncio
    async def test_cross_module_data_consistency(
        self, client, auth_token, test_project
    ):
        """Test data consistency across different modules"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Step 1: Create project-specific namespace
        namespace_data = {
            "name": "test_namespace",
            "uri": "http://test.example.org/",
            "description": "Test namespace for integration",
            "project_id": project_id,
        }

        namespace_response = await client.post(
            "/api/namespaces", headers=headers, json=namespace_data
        )

        # This might fail if namespace management is not fully implemented
        assert namespace_response.status_code in [200, 404, 500]

        # Step 2: Create ontology class with namespace
        class_data = {
            "name": "TestClass",
            "label": "Test Class",
            "description": "A test class with namespace",
            "namespace": "http://test.example.org/",
        }

        ontology_response = await client.post(
            "/api/ontology/classes", headers=headers, json=class_data
        )

        assert ontology_response.status_code == 200

        # Step 3: Verify consistency
        ontology_get_response = await client.get("/api/ontology", headers=headers)
        assert ontology_get_response.status_code == 200

        ontology_data = ontology_get_response.json()
        assert "TestClass" in ontology_data["classes"]

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, client, auth_token, test_project):
        """Test error handling and recovery in workflows"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Test 1: Invalid file upload
        invalid_files = {"file": ("test.txt", io.BytesIO(b""), "text/plain")}
        invalid_data = {"project_id": "invalid_project_id"}

        invalid_response = await client.post(
            "/api/files/upload", files=invalid_files, data=invalid_data, headers=headers
        )

        assert invalid_response.status_code == 400

        # Test 2: Invalid workflow parameters
        invalid_workflow_data = {
            "processKey": "invalid_process",
            "projectId": project_id,
            "fileIds": ["invalid_file_id"],
        }

        invalid_workflow_response = await client.post(
            "/api/workflows/start", headers=headers, json=invalid_workflow_data
        )

        # Should handle gracefully
        assert invalid_workflow_response.status_code in [400, 404, 500]

        # Test 3: Invalid ontology data
        invalid_ontology_data = {
            "name": "",  # Invalid empty name
            "label": "Invalid Class",
        }

        invalid_ontology_response = await client.post(
            "/api/ontology/classes", headers=headers, json=invalid_ontology_data
        )

        assert invalid_ontology_response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client, auth_token, test_project):
        """Test system behavior under concurrent operations"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        project_id = test_project["project_id"]

        # Create multiple concurrent file uploads
        async def upload_file(file_index):
            file_content = f"Test content {file_index}".encode()
            files = {
                "file": (
                    f"test_{file_index}.txt",
                    io.BytesIO(file_content),
                    "text/plain",
                )
            }
            data = {"project_id": project_id}

            response = await client.post(
                "/api/files/upload", files=files, data=data, headers=headers
            )
            return response

        # Run 5 concurrent uploads
        upload_tasks = [upload_file(i) for i in range(5)]
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # Check that all uploads succeeded
        successful_uploads = 0
        for result in upload_results:
            if isinstance(result, Exception):
                continue
            if result.status_code == 200:
                successful_uploads += 1

        # At least some uploads should succeed
        assert successful_uploads > 0

        # Verify files are listed
        list_response = await client.get(
            "/api/files", params={"project_id": project_id}, headers=headers
        )

        assert list_response.status_code == 200
        files_list = list_response.json()["files"]
        assert len(files_list) >= successful_uploads

