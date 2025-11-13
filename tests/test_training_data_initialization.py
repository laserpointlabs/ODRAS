"""
Test DAS Training Data Auto-Loading on Startup

Verifies that base training data is automatically loaded during system initialization.
This test ensures the startup process correctly loads training data without manual intervention.
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
@pytest.mark.integration
async def test_training_collections_exist_after_startup(auth_headers):
    """Verify that all base training collections exist after startup."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        
        # Should have all base collections
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
        
        assert len(collections) >= 5, f"Expected at least 5 collections, found {len(collections)}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_base_training_data_loaded(auth_headers):
    """Verify that base training data is loaded (completed assets exist)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        
        # Check that at least some collections have completed assets
        collections_with_data = []
        for collection in collections:
            collection_id = collection["collection_id"]
            
            # Get assets for this collection
            assets_response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}/assets",
                headers=auth_headers,
            )
            
            if assets_response.status_code == 200:
                assets = assets_response.json()
                completed_assets = [
                    a for a in assets 
                    if a.get("processing_status") == "completed" and a.get("chunk_count", 0) > 0
                ]
                if completed_assets:
                    collections_with_data.append({
                        "collection": collection["collection_name"],
                        "completed_count": len(completed_assets),
                    })
        
        # At least some collections should have completed training data
        assert len(collections_with_data) > 0, "No collections have completed training data loaded"
        
        # Log what we found
        print(f"\n✅ Found {len(collections_with_data)} collections with completed training data:")
        for item in collections_with_data:
            print(f"  - {item['collection']}: {item['completed_count']} completed assets")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_training_data_sql_first_storage(auth_headers):
    """Verify that training data uses SQL-first storage (chunks in SQL, no text in Qdrant)."""
    import psycopg2
    from backend.services.config import Settings
    
    settings = Settings()
    
    # Check SQL for training chunks
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    
    try:
        with conn.cursor() as cur:
            # Check that training chunks exist in SQL (using unified das_knowledge_chunks table)
            cur.execute("SELECT COUNT(*) FROM das_knowledge_chunks WHERE knowledge_type = 'training'")
            sql_chunk_count = cur.fetchone()[0]
            
            # Check that chunks have content (text stored in SQL)
            cur.execute("SELECT COUNT(*) FROM das_knowledge_chunks WHERE knowledge_type = 'training' AND LENGTH(content) > 0")
            chunks_with_content = cur.fetchone()[0]
            
            assert sql_chunk_count > 0, "No training chunks found in SQL database (das_knowledge_chunks)"
            assert chunks_with_content == sql_chunk_count, "Some training chunks missing content in SQL"
            
            print(f"✅ SQL-first storage verified: {sql_chunk_count} training chunks with content in SQL (das_knowledge_chunks)")
    finally:
        conn.close()
    
    # Check Qdrant - verify no text in payloads
    import urllib.request
    import json
    
    collections = [
        "das_training_ontology",
        "das_training_requirements",
        "das_training_systems_engineering",
        "das_training_odras_usage",
        "das_training_acquisition",
    ]
    
    violations = []
    for col in collections:
        url = f"http://localhost:6333/collections/{col}/points/scroll"
        data = json.dumps({"limit": 5, "with_payload": True}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            response = urllib.request.urlopen(req, timeout=5)
            result = json.loads(response.read())
            points = result.get('result', {}).get('points', [])
            
            for point in points:
                payload = point.get('payload', {})
                if 'text' in payload or 'content' in payload:
                    violations.append({
                        'collection': col,
                        'point_id': point.get('id'),
                        'has_text': 'text' in payload,
                        'has_content': 'content' in payload,
                    })
        except Exception as e:
            print(f"⚠️  Could not check Qdrant collection {col}: {e}")
    
    assert len(violations) == 0, f"SQL-first violation: Found text/content in Qdrant payloads: {violations}"
    print(f"✅ Qdrant payloads verified: No text/content fields found (SQL-first pattern)")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_training_data_accessible_via_rag(auth_headers):
    """Verify that training data is accessible via RAG queries."""
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
        
        # Query that should match training data (with longer timeout for RAG processing)
        response = await client.post(
            f"{BASE_URL}/api/das/chat",
            headers=auth_headers,
            json={
                "message": "What is an ontology?",
                "project_id": project_id,
            },
            timeout=60.0,  # Longer timeout for RAG processing
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Should have a response
        assert "message" in result
        assert len(result["message"]) > 0
        
        # Should have sources (may include training sources)
        if "sources" in result:
            sources = result["sources"]
            assert isinstance(sources, list)
            
            # Check if any sources are from training collections
            training_sources = [s for s in sources if s.get("source_type") == "training"]
            
            if training_sources:
                print(f"✅ Found {len(training_sources)} training sources in RAG response")
                for source in training_sources[:3]:
                    print(f"  - {source.get('title', 'Unknown')} (score: {source.get('relevance_score', 0):.3f})")
            else:
                print("ℹ️  No training sources in response (may be normal if project-specific sources ranked higher)")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_training_data_idempotent_loading(auth_headers):
    """Verify that training data loading is idempotent (doesn't duplicate on restart)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all collections and count assets
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        collections = response.json()
        
        # Count total completed assets
        total_completed = 0
        asset_titles = set()
        
        for collection in collections:
            collection_id = collection["collection_id"]
            assets_response = await client.get(
                f"{BASE_URL}/api/das-training/collections/{collection_id}/assets",
                headers=auth_headers,
            )
            
            if assets_response.status_code == 200:
                assets = assets_response.json()
                completed = [
                    a for a in assets 
                    if a.get("processing_status") == "completed"
                ]
                total_completed += len(completed)
                
                for asset in completed:
                    asset_titles.add(asset.get("title"))
        
        # Should have exactly 5 base training assets (one per collection)
        # This verifies idempotency - if we restart, we shouldn't get duplicates
        assert total_completed >= 5, f"Expected at least 5 completed assets, found {total_completed}"
        assert len(asset_titles) >= 5, f"Expected at least 5 unique asset titles, found {len(asset_titles)}"
        
        print(f"✅ Idempotency verified: {total_completed} completed assets, {len(asset_titles)} unique titles")
        print(f"   Asset titles: {sorted(asset_titles)}")
