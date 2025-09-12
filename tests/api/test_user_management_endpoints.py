"""
Test suite for User Management API endpoints.

Tests all user-related endpoints including CRUD operations,
authentication, and user management functionality.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestUserManagementEndpoints:
    """Test user management API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication."""
        self.base_url = "/api/users"
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
    
    def test_get_users_list(self):
        """Test GET /api/users - list all users."""
        response = client.get(self.base_url, headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        
        # Check that we have at least the default users
        usernames = [user["username"] for user in data["users"]]
        assert "admin" in usernames
        assert "jdehart" in usernames
    
    def test_get_current_user(self):
        """Test GET /api/users/me - get current user info."""
        response = client.get(f"{self.base_url}/me", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "jdehart"
    
    def test_get_current_user_without_auth(self):
        """Test GET /api/users/me without authentication."""
        response = client.get(f"{self.base_url}/me")
        
        assert response.status_code == 401
    
    def test_change_password(self):
        """Test PUT /api/users/me/password - change password."""
        response = client.put(
            f"{self.base_url}/me/password",
            json={
                "old_password": "jdehart123!",
                "new_password": "new_password123!"
            },
            headers=self._get_headers()
        )
        
        assert response.status_code == 204
        
        # Change it back
        response = client.put(
            f"{self.base_url}/me/password",
            json={
                "old_password": "new_password123!",
                "new_password": "jdehart123!"
            },
            headers=self._get_headers()
        )
        assert response.status_code == 204
    
    def test_change_password_wrong_old_password(self):
        """Test PUT /api/users/me/password with wrong old password."""
        response = client.put(
            f"{self.base_url}/me/password",
            json={
                "old_password": "wrong_password",
                "new_password": "new_password123!"
            },
            headers=self._get_headers()
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_create_user(self):
        """Test POST /api/users - create new user."""
        user_data = {
            "username": "test_user",
            "display_name": "Test User",
            "password": "test_password123!",
            "is_admin": False,
            "is_active": True
        }
        
        response = client.post(
            self.base_url,
            json=user_data,
            headers=self._get_headers()
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "test_user"
        assert data["display_name"] == "Test User"
        assert data["is_admin"] is False
        assert data["is_active"] is True
        assert "user_id" in data
    
    def test_create_user_duplicate_username(self):
        """Test POST /api/users with duplicate username."""
        user_data = {
            "username": "jdehart",  # Already exists
            "display_name": "Duplicate User",
            "password": "test_password123!",
            "is_admin": False,
            "is_active": True
        }
        
        response = client.post(
            self.base_url,
            json=user_data,
            headers=self._get_headers()
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_get_user_by_id(self):
        """Test GET /api/users/{user_id} - get specific user."""
        # First get the current user to get their ID
        me_response = client.get(f"{self.base_url}/me", headers=self._get_headers())
        assert me_response.status_code == 200
        user_id = me_response.json()["user_id"]
        
        response = client.get(f"{self.base_url}/{user_id}", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["username"] == "jdehart"
    
    def test_get_nonexistent_user(self):
        """Test GET /api/users/{user_id} with nonexistent user ID."""
        response = client.get(f"{self.base_url}/999999", headers=self._get_headers())
        
        assert response.status_code == 404
    
    def test_update_user(self):
        """Test PUT /api/users/{user_id} - update user."""
        # First get the current user to get their ID
        me_response = client.get(f"{self.base_url}/me", headers=self._get_headers())
        assert me_response.status_code == 200
        user_id = me_response.json()["user_id"]
        
        update_data = {
            "display_name": "Updated Display Name",
            "is_active": True
        }
        
        response = client.put(
            f"{self.base_url}/{user_id}",
            json=update_data,
            headers=self._get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Display Name"
    
    def test_activate_user(self):
        """Test POST /api/users/{user_id}/activate - activate user."""
        # First create a user
        user_data = {
            "username": "inactive_user",
            "display_name": "Inactive User",
            "password": "test_password123!",
            "is_admin": False,
            "is_active": False
        }
        
        create_response = client.post(
            self.base_url,
            json=user_data,
            headers=self._get_headers()
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        # Activate the user
        response = client.post(
            f"{self.base_url}/{user_id}/activate",
            headers=self._get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
    
    def test_activate_nonexistent_user(self):
        """Test POST /api/users/{user_id}/activate with nonexistent user."""
        response = client.post(
            f"{self.base_url}/999999/activate",
            headers=self._get_headers()
        )
        
        assert response.status_code == 404
    
    def test_user_endpoints_require_auth(self):
        """Test that user endpoints require authentication."""
        endpoints = [
            ("GET", self.base_url),
            ("GET", f"{self.base_url}/me"),
            ("POST", self.base_url),
            ("PUT", f"{self.base_url}/me/password"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"














