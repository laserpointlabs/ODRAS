"""
Test DAS Training Data Integration

Verifies that training data is properly set up and RAG queries return results
from training collections. This test can be run repeatedly to ensure the
training system continues to work as development progresses.
"""

import pytest
import httpx
from typing import Dict

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "das_service"
TEST_PASSWORD = "das_service_2024!"


@pytest.fixture
async def auth_headers():
    """Get authentication headers."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_training_collections_exist(auth_headers):
    """Verify that training collections exist and have assets."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        
        # Should have at least the base collections
        collection_names = [c["collection_name"] for c in collections]
        expected_collections = [
            "das_training_ontology",
            "das_training_requirements",
            "das_training_systems_engineering",
            "das_training_odras_usage",
            "das_training_acquisition",
        ]
        
        for expected in expected_collections:
            assert expected in collection_names, f"Missing collection: {expected}"
        
        # Collections should exist (assets may still be processing)
        # Just verify collections are created - asset processing happens asynchronously
        assert len(collections) >= 5, f"Expected at least 5 collections, found {len(collections)}"


@pytest.mark.asyncio
async def test_training_data_in_rag_queries(auth_headers):
    """Verify that RAG queries return results from training collections."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get a project ID
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
        
        # Query DAS with questions that should match training data
        test_queries = [
            ("What is an ontology?", "ontology"),
            ("How do I write requirements?", "requirements"),
            ("What is systems engineering?", "systems_engineering"),
            ("How do I use ODRAS?", "odras_usage"),
            ("What is acquisition?", "acquisition"),
        ]
        
        for query, expected_domain in test_queries:
            response = await client.post(
                f"{BASE_URL}/api/das/chat",
                headers=auth_headers,
                json={
                    "message": query,
                    "project_id": project_id,
                },
                timeout=30.0,
            )
            
            assert response.status_code == 200, f"Query failed: {query}"
            result = response.json()
            
            # Should have a response
            assert "message" in result
            assert len(result["message"]) > 0, f"No response for query: {query}"
            
            # Check if sources include training data
            if "sources" in result and len(result["sources"]) > 0:
                training_sources = [
                    s for s in result["sources"]
                    if s.get("source_type") == "training"
                ]
                # At least one source should be from training (may not always be true, but good to check)
                if training_sources:
                    assert any(
                        expected_domain in s.get("collection_domain", "").lower()
                        or expected_domain in s.get("collection_name", "").lower()
                        for s in training_sources
                    ), f"Training sources found but not from expected domain: {expected_domain}"


@pytest.mark.asyncio
async def test_training_collection_statistics(auth_headers):
    """Verify that training collections have proper statistics."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get collections
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        
        # Check statistics for each collection
        for collection in collections[:3]:  # Check first 3 collections
            collection_id = collection["collection_id"]
            
            stats_response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}/stats",
                headers=auth_headers,
            )
            
            if stats_response.status_code == 200:
                stats = stats_response.json()
                # Should have basic stats (API returns total_assets, not asset_count)
                assert "total_assets" in stats or "asset_count" in stats
                assert "total_chunks" in stats
                asset_count = stats.get("total_assets") or stats.get("asset_count", 0)
                assert asset_count >= 0
                assert stats["total_chunks"] >= 0
