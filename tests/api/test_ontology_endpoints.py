"""
Ontology Management API Endpoint Tests

Tests for all ontology-related endpoints including CRUD operations, validation, and import/export.
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport
from backend.main import app


class TestOntologyEndpoints:
    """Test suite for ontology management endpoints"""

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

    @pytest.mark.asyncio
    async def test_get_ontology(self, client, auth_token):
        """Test getting current ontology"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "classes" in data
        assert "properties" in data
        assert isinstance(data["classes"], dict)
        assert isinstance(data["properties"], dict)

    @pytest.mark.asyncio
    async def test_get_ontology_without_auth(self, client):
        """Test getting ontology without authentication"""
        response = await client.get("/api/ontology")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_ontology_statistics(self, client, auth_token):
        """Test getting ontology statistics"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_classes" in data
        assert "total_properties" in data
        assert isinstance(data["total_classes"], int)
        assert isinstance(data["total_properties"], int)

    @pytest.mark.asyncio
    async def test_get_ontology_layout(self, client, auth_token):
        """Test getting ontology layout information"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology/layout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "layout" in data

    @pytest.mark.asyncio
    async def test_validate_ontology_integrity(self, client, auth_token):
        """Test ontology integrity validation"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology/validate-integrity", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "issues" in data
        assert isinstance(data["valid"], bool)
        assert isinstance(data["issues"], list)

    @pytest.mark.asyncio
    async def test_create_ontology_class(self, client, auth_token):
        """Test creating a new ontology class"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        class_data = {
            "name": "TestClass",
            "label": "Test Class",
            "description": "A test class for validation",
            "parent_classes": ["Thing"],
        }

        response = await client.post(
            "/api/ontology/classes", headers=headers, json=class_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    @pytest.mark.asyncio
    async def test_create_ontology_class_invalid_data(self, client, auth_token):
        """Test creating ontology class with invalid data"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Missing required fields
        class_data = {
            "label": "Test Class"
            # Missing 'name' field
        }

        response = await client.post(
            "/api/ontology/classes", headers=headers, json=class_data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_ontology_property(self, client, auth_token):
        """Test creating a new ontology property"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        property_data = {
            "name": "testProperty",
            "label": "Test Property",
            "description": "A test property for validation",
            "domain": "TestClass",
            "range": "string",
            "property_type": "data_property",
        }

        response = await client.post(
            "/api/ontology/properties", headers=headers, json=property_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_ontology_class(self, client, auth_token):
        """Test deleting an ontology class"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # First create a class
        class_data = {
            "name": "DeleteTestClass",
            "label": "Delete Test Class",
            "description": "A class to be deleted",
        }

        create_response = await client.post(
            "/api/ontology/classes", headers=headers, json=class_data
        )
        assert create_response.status_code == 200

        # Now delete it
        response = await client.delete(
            "/api/ontology/classes/DeleteTestClass", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_ontology_property(self, client, auth_token):
        """Test deleting an ontology property"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # First create a property
        property_data = {
            "name": "deleteTestProperty",
            "label": "Delete Test Property",
            "description": "A property to be deleted",
            "property_type": "data_property",
        }

        create_response = await client.post(
            "/api/ontology/properties", headers=headers, json=property_data
        )
        assert create_response.status_code == 200

        # Now delete it
        response = await client.delete(
            "/api/ontology/properties/deleteTestProperty", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_validate_ontology_json(self, client, auth_token):
        """Test ontology JSON validation"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Valid ontology data
        ontology_data = {
            "classes": {
                "TestClass": {"label": "Test Class", "description": "A test class"}
            },
            "properties": {
                "testProperty": {
                    "label": "Test Property",
                    "description": "A test property",
                    "property_type": "data_property",
                }
            },
        }

        response = await client.post(
            "/api/ontology/validate", headers=headers, json=ontology_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data

    @pytest.mark.asyncio
    async def test_export_ontology_turtle(self, client, auth_token):
        """Test exporting ontology in Turtle format"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology/export/turtle", headers=headers)

        assert response.status_code == 200
        # Should return Turtle format content
        content = response.text
        assert "@prefix" in content or "PREFIX" in content

    @pytest.mark.asyncio
    async def test_export_ontology_json(self, client, auth_token):
        """Test exporting ontology in JSON format"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = await client.get("/api/ontology/export/json", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "classes" in data
        assert "properties" in data

    @pytest.mark.asyncio
    async def test_mint_iri(self, client, auth_token):
        """Test IRI minting functionality"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        iri_data = {"local_name": "TestResource", "namespace": "http://example.org/"}

        response = await client.post(
            "/api/ontology/mint-iri", headers=headers, json=iri_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "iri" in data
        assert data["iri"].startswith("http://example.org/")
        assert "TestResource" in data["iri"]
