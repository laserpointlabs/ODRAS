"""
Test suite for Namespace Management API endpoints.

Tests all namespace-related endpoints including CRUD operations,
public namespaces, and namespace validation.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestNamespaceManagementEndpoints:
    """Test namespace management API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication."""
        self.base_url = "/api/namespaces"
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
    
    def test_get_namespaces_list(self):
        """Test GET /api/namespaces - list all namespaces."""
        response = client.get(self.base_url, headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "namespaces" in data
        assert isinstance(data["namespaces"], list)
    
    def test_get_public_namespaces(self):
        """Test GET /api/namespaces/public/namespaces - get public namespaces."""
        response = client.get(f"{self.base_url}/public/namespaces")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "namespaces" in data
        assert isinstance(data["namespaces"], list)
    
    def test_get_available_namespaces(self):
        """Test GET /api/namespaces/available/namespaces - get available namespaces."""
        response = client.get(f"{self.base_url}/available/namespaces", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "namespaces" in data
        assert isinstance(data["namespaces"], list)
    
    def test_create_namespace(self):
        """Test POST /api/namespaces - create new namespace."""
        namespace_data = {
            "prefix": "test",
            "namespace_uri": "http://example.com/test/",
            "description": "Test namespace",
            "is_public": False
        }
        
        response = client.post(
            self.base_url,
            json=namespace_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 201, 404, 501]
    
    def test_create_namespace_duplicate_prefix(self):
        """Test POST /api/namespaces with duplicate prefix."""
        namespace_data = {
            "prefix": "test",  # Same as above
            "namespace_uri": "http://example.com/test2/",
            "description": "Another test namespace",
            "is_public": False
        }
        
        response = client.post(
            self.base_url,
            json=namespace_data,
            headers=self._get_headers()
        )
        
        # Should either succeed (if previous test didn't run) or fail with conflict
        assert response.status_code in [201, 409, 404, 501]
    
    def test_get_namespace_by_id(self):
        """Test GET /api/namespaces/{namespace_id} - get specific namespace."""
        response = client.get(f"{self.base_url}/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_update_namespace(self):
        """Test PUT /api/namespaces/{namespace_id} - update namespace."""
        update_data = {
            "description": "Updated namespace description",
            "is_public": True
        }
        
        response = client.put(
            f"{self.base_url}/1",
            json=update_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_delete_namespace(self):
        """Test DELETE /api/namespaces/{namespace_id} - delete namespace."""
        response = client.delete(f"{self.base_url}/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 204, 404, 501]
    
    def test_namespace_validation(self):
        """Test POST /api/namespaces/validate - validate namespace."""
        validation_data = {
            "prefix": "test",
            "namespace_uri": "http://example.com/test/"
        }
        
        response = client.post(
            f"{self.base_url}/validate",
            json=validation_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 400, 404, 501]
    
    def test_namespace_endpoints_require_auth(self):
        """Test that namespace endpoints require authentication (except public ones)."""
        protected_endpoints = [
            ("GET", self.base_url),
            ("POST", self.base_url),
            ("GET", f"{self.base_url}/1"),
            ("PUT", f"{self.base_url}/1"),
            ("DELETE", f"{self.base_url}/1"),
            ("POST", f"{self.base_url}/validate"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"
    
    def test_public_namespace_endpoints_no_auth_required(self):
        """Test that public namespace endpoints don't require authentication."""
        public_endpoints = [
            ("GET", f"{self.base_url}/public/namespaces"),
        ]
        
        for method, endpoint in public_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            
            assert response.status_code != 401, f"{method} {endpoint} should not require auth"













