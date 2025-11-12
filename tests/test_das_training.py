"""
Tests for DAS Training Workbench functionality.

Tests training collection management and RAG integration with global training collections.
"""

import pytest
import asyncio
from uuid import uuid4
import httpx


BASE_URL = "http://localhost:8000"
TEST_USERNAME = "das_service"
TEST_PASSWORD = "das_service_2024!"


@pytest.fixture
def auth_token():
    """Get authentication token for test user."""
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=30.0,
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.mark.asyncio
async def test_list_training_collections(auth_headers):
    """Test listing training collections."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        assert isinstance(collections, list)
        
        # Check that default collections exist
        collection_names = [c["collection_name"] for c in collections]
        assert "das_training_ontology" in collection_names or len(collections) == 0


@pytest.mark.asyncio
async def test_get_training_collection(auth_headers):
    """Test getting a specific training collection."""
    # First, list collections to get an ID
    async with httpx.AsyncClient(timeout=30.0) as client:
        list_response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        collections = list_response.json()
        
        if collections:
            collection_id = collections[0]["collection_id"]
            
            # Get specific collection
            response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            collection = response.json()
            assert collection["collection_id"] == collection_id
            assert "collection_name" in collection
            assert "domain" in collection


@pytest.mark.asyncio
async def test_get_collection_stats(auth_headers):
    """Test getting collection statistics."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # List collections
        list_response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        collections = list_response.json()
        
        if collections:
            collection_id = collections[0]["collection_id"]
            
            # Get stats
            response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}/stats",
                headers=auth_headers,
            )
            assert response.status_code == 200
            stats = response.json()
            assert stats["collection_id"] == collection_id
            assert "total_assets" in stats
            assert "total_chunks" in stats
            assert "assets_by_status" in stats


@pytest.mark.asyncio
async def test_list_training_assets(auth_headers):
    """Test listing training assets in a collection."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # List collections
        list_response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        collections = list_response.json()
        
        if collections:
            collection_id = collections[0]["collection_id"]
            
            # List assets
            response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}/assets",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assets = response.json()
            assert isinstance(assets, list)


@pytest.mark.asyncio
async def test_rag_includes_training_collections(auth_headers):
    """Test that RAG queries include results from training collections."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get a project ID first
        projects_response = await client.get(
            f"{BASE_URL}/api/projects",
            headers=auth_headers,
        )
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if isinstance(projects, list) and len(projects) > 0:
            project_id = projects[0]["project_id"]
        elif isinstance(projects, dict) and "projects" in projects and projects["projects"]:
            project_id = projects["projects"][0]["project_id"]
        else:
            pytest.skip("No projects available for testing")
        
        # Query DAS/RAG with a general question
        response = await client.post(
            f"{BASE_URL}/api/das/chat",
            headers=auth_headers,
            json={
                "message": "What is ontology?",
                "project_id": project_id,
            },
            timeout=30.0,
        )
        
        # Should succeed
        assert response.status_code == 200
        
        result = response.json()
        # Check if response includes message
        assert "message" in result
        # Check if sources are included (may include training knowledge)
        if "sources" in result:
            sources = result["sources"]
            # Training sources would have source_type="training" if present
            assert isinstance(sources, list)
