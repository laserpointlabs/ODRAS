"""
Authentication API Endpoint Tests

Tests for all authentication-related endpoints including login, logout, and user management.
"""

import pytest
import json
from httpx import AsyncClient


class TestAuthenticationEndpoints:
    """Test suite for authentication endpoints"""

    @pytest.fixture
    async def client(self):
        """Create test client connecting to real API"""
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful user login"""
        response = await client.post(
            "/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"] is not None
        assert len(data["token"]) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "invalid_user", "password": "wrong_password"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = await client.post("/api/auth/login", json={})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_current_user_with_token(self, client):
        """Test getting current user with valid token"""
        # First login to get token
        login_response = await client.post(
            "/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}
        )
        token = login_response.json()["token"]

        # Use token to get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == "jdehart"

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self, client):
        """Test getting current user without token"""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, client):
        """Test successful logout"""
        # First login to get token
        login_response = await client.post(
            "/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}
        )
        token = login_response.json()["token"]

        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/api/auth/logout", headers=headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client):
        """Test logout without token"""
        response = await client.post("/api/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_expiration(self, client):
        """Test that tokens expire after logout"""
        # Login and get token
        login_response = await client.post(
            "/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"}
        )
        token = login_response.json()["token"]

        # Verify token works
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200

        # Logout
        await client.post("/api/auth/logout", headers=headers)

        # Verify token no longer works
        response = await client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
