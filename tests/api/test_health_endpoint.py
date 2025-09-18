"""Test the health check endpoint - a simple test that doesn't require authentication."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that the health endpoint returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_root_redirect():
    """Test that the root path redirects to the app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get("/")
        # Should redirect to the app
        assert response.status_code in [302, 307]  # Redirect status codes


@pytest.mark.asyncio
async def test_api_docs_available():
    """Test that the API documentation is available."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        # FastAPI automatically generates docs at /docs
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

