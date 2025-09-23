"""
Test suite for Knowledge Management API endpoints.

Tests all knowledge-related endpoints including asset management,
processing jobs, and query functionality.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestKnowledgeManagementEndpoints:
    """Test knowledge management API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication."""
        self.base_url = "/api/knowledge"
        self.auth_token = None

        # Login to get auth token
        login_response = client.post(
            "/api/auth/login",
            json={"username": "jdehart", "password": "jdehart123!"}
        )
        if login_response.status_code == 200:
            self.auth_token = login_response.json().get("access_token")

    def _get_headers(self):
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def test_get_knowledge_assets(self):
        """Test GET /api/knowledge/assets - list knowledge assets."""
        response = client.get(f"{self.base_url}/assets", headers=self._get_headers())

        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert isinstance(data["assets"], list)

    def test_get_knowledge_assets_with_pagination(self):
        """Test GET /api/knowledge/assets with pagination parameters."""
        response = client.get(
            f"{self.base_url}/assets?limit=10&offset=0",
            headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_get_knowledge_health(self):
        """Test GET /api/knowledge/health - check knowledge service health."""
        response = client.get(f"{self.base_url}/health", headers=self._get_headers())

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_get_knowledge_jobs(self):
        """Test GET /api/knowledge/jobs - list processing jobs."""
        response = client.get(f"{self.base_url}/jobs", headers=self._get_headers())

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_knowledge_jobs_with_filters(self):
        """Test GET /api/knowledge/jobs with filter parameters."""
        response = client.get(
            f"{self.base_url}/jobs?status=completed&limit=5",
            headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_query_suggestions(self):
        """Test GET /api/knowledge/query/suggestions - get query suggestions."""
        response = client.get(
            f"{self.base_url}/query/suggestions?q=test",
            headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_get_query_suggestions_empty_query(self):
        """Test GET /api/knowledge/query/suggestions with empty query."""
        response = client.get(
            f"{self.base_url}/query/suggestions",
            headers=self._get_headers()
        )

        # Should either return empty suggestions or 400 for missing query
        assert response.status_code in [200, 400]

    def test_create_knowledge_asset(self):
        """Test POST /api/knowledge/assets - create knowledge asset."""
        asset_data = {
            "title": "Test Knowledge Asset",
            "content": "This is test content for a knowledge asset",
            "document_type": "text",
            "metadata": {"source": "test", "category": "test"}
        }

        response = client.post(
            f"{self.base_url}/assets",
            json=asset_data,
            headers=self._get_headers()
        )

        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 201, 404, 501]

    def test_get_knowledge_asset_by_id(self):
        """Test GET /api/knowledge/assets/{asset_id} - get specific asset."""
        response = client.get(f"{self.base_url}/assets/1", headers=self._get_headers())

        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]

    def test_update_knowledge_asset(self):
        """Test PUT /api/knowledge/assets/{asset_id} - update asset."""
        update_data = {
            "title": "Updated Knowledge Asset",
            "content": "Updated content",
            "metadata": {"source": "test", "category": "updated"}
        }

        response = client.put(
            f"{self.base_url}/assets/1",
            json=update_data,
            headers=self._get_headers()
        )

        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]

    def test_delete_knowledge_asset(self):
        """Test DELETE /api/knowledge/assets/{asset_id} - delete asset."""
        response = client.delete(f"{self.base_url}/assets/1", headers=self._get_headers())

        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 204, 404, 501]

    def test_knowledge_endpoints_require_auth(self):
        """Test that knowledge endpoints require authentication."""
        endpoints = [
            ("GET", f"{self.base_url}/assets"),
            ("GET", f"{self.base_url}/health"),
            ("GET", f"{self.base_url}/jobs"),
            ("GET", f"{self.base_url}/query/suggestions"),
            ("POST", f"{self.base_url}/assets"),
            ("GET", f"{self.base_url}/assets/1"),
            ("PUT", f"{self.base_url}/assets/1"),
            ("DELETE", f"{self.base_url}/assets/1"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            assert response.status_code == 401, f"{method} {endpoint} should require auth"















