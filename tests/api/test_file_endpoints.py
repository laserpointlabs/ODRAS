"""
File Management API Endpoint Tests

Tests for all file management endpoints including upload, download, listing, and processing.
"""

import pytest
import json
import io
from httpx import AsyncClient, ASGITransport
from backend.main import app


class TestFileManagementEndpoints:
    """Test suite for file management endpoints"""

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
    async def test_project_id(self, client, auth_token):
        """Create a test project and return its ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Test Project", "description": "Test project for file tests"},
        )
        return response.json()["project"]["project_id"]

    @pytest.mark.asyncio
    async def test_file_upload_success(self, client, auth_token, test_project_id):
        """Test successful file upload"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create test file content
        file_content = b"# Test Document\nThis is a test document for upload testing."
        files = {
            "file": ("test_document.md", io.BytesIO(file_content), "text/markdown")
        }
        data = {
            "project_id": test_project_id,
            "tags": json.dumps({"docType": "test", "status": "new"}),
        }

        response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "file_id" in data
        assert data["file_id"] is not None

    @pytest.mark.asyncio
    async def test_file_upload_without_auth(self, client, test_project_id):
        """Test file upload without authentication"""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"project_id": test_project_id}

        response = await client.post("/api/files/upload", files=files, data=data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_file_upload_invalid_project(self, client, auth_token):
        """Test file upload with invalid project ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"project_id": "invalid_project_id"}

        response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_file_list(self, client, auth_token, test_project_id):
        """Test file listing"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get(
            "/api/files", params={"project_id": test_project_id}, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert isinstance(data["files"], list)

    @pytest.mark.asyncio
    async def test_file_list_without_auth(self, client, test_project_id):
        """Test file listing without authentication"""
        response = await client.get(
            "/api/files", params={"project_id": test_project_id}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_file_download_url(self, client, auth_token, test_project_id):
        """Test getting file download URL"""
        # First upload a file
        headers = {"Authorization": f"Bearer {auth_token}"}
        file_content = b"Test content for download"
        files = {"file": ("download_test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"project_id": test_project_id}

        upload_response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )
        file_id = upload_response.json()["file_id"]

        # Get download URL
        response = await client.get(f"/api/files/{file_id}/url", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"] is not None

    @pytest.mark.asyncio
    async def test_file_download_url_invalid_file(self, client, auth_token):
        """Test getting download URL for invalid file"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/files/invalid_file_id/url", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_file_deletion(self, client, auth_token, test_project_id):
        """Test file deletion"""
        # First upload a file
        headers = {"Authorization": f"Bearer {auth_token}"}
        file_content = b"Test content for deletion"
        files = {"file": ("delete_test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"project_id": test_project_id}

        upload_response = await client.post(
            "/api/files/upload", files=files, data=data, headers=headers
        )
        file_id = upload_response.json()["file_id"]

        # Delete the file
        response = await client.delete(f"/api/files/{file_id}", headers=headers)

        assert response.status_code == 200

        # Verify file is deleted
        response = await client.get(f"/api/files/{file_id}/url", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_file_deletion_unauthorized(self, client, test_project_id):
        """Test file deletion without authorization"""
        response = await client.delete("/api/files/some_file_id")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_batch_upload(self, client, auth_token, test_project_id):
        """Test batch file upload"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create multiple test files
        files = []
        for i in range(3):
            content = f"Test content {i}".encode()
            files.append(("file", (f"test_{i}.txt", io.BytesIO(content), "text/plain")))

        data = {"project_id": test_project_id}

        response = await client.post(
            "/api/files/batch/upload", files=files, data=data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "file_ids" in data
        assert len(data["file_ids"]) == 3

    @pytest.mark.asyncio
    async def test_storage_info(self, client, auth_token):
        """Test getting storage information"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/files/storage/info", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "storage_type" in data
        assert "total_files" in data

    @pytest.mark.asyncio
    async def test_keyword_config(self, client, auth_token):
        """Test getting keyword configuration"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/files/keywords", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
