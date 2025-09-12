"""
Test suite for Service Status API endpoints.

Tests all service status endpoints including Camunda, Ollama, OpenAI,
and other service health checks.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestServiceStatusEndpoints:
    """Test service status API endpoints."""
    
    def test_get_camunda_status(self):
        """Test GET /api/camunda/status - check Camunda status."""
        response = client.get("/api/camunda/status")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["running", "offline", "unreachable"]
    
    def test_get_camunda_deployments(self):
        """Test GET /api/camunda/deployments - get Camunda deployments."""
        response = client.get("/api/camunda/deployments")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "deployments" in data
        assert isinstance(data["deployments"], list)
    
    def test_get_ollama_status(self):
        """Test GET /api/ollama/status - check Ollama status."""
        response = client.get("/api/ollama/status")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["running", "offline", "unreachable"]
    
    def test_get_openai_status(self):
        """Test GET /api/openai/status - check OpenAI status."""
        response = client.get("/api/openai/status")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["running", "offline", "unreachable"]
    
    def test_get_embedding_models(self):
        """Test GET /api/embedding-models - get available embedding models."""
        response = client.get("/api/embedding-models")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
    
    def test_get_ollama_models(self):
        """Test GET /api/models/ollama - get Ollama models."""
        response = client.get("/api/models/ollama")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
    
    def test_get_openai_models(self):
        """Test GET /api/models/openai - get OpenAI models."""
        response = client.get("/api/models/openai")
        
        # This is a public endpoint, should not require auth
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
    
    def test_service_status_endpoints_no_auth_required(self):
        """Test that service status endpoints don't require authentication."""
        public_endpoints = [
            ("GET", "/api/camunda/status"),
            ("GET", "/api/camunda/deployments"),
            ("GET", "/api/ollama/status"),
            ("GET", "/api/openai/status"),
            ("GET", "/api/embedding-models"),
            ("GET", "/api/models/ollama"),
            ("GET", "/api/models/openai"),
        ]
        
        for method, endpoint in public_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            
            assert response.status_code != 401, f"{method} {endpoint} should not require auth"
    
    def test_service_status_response_format(self):
        """Test that service status endpoints return expected response format."""
        status_endpoints = [
            "/api/camunda/status",
            "/api/ollama/status", 
            "/api/openai/status"
        ]
        
        for endpoint in status_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert isinstance(data["status"], str)
            
            # Check for optional fields that might be present
            if "message" in data:
                assert isinstance(data["message"], str)
            if "model_count" in data:
                assert isinstance(data["model_count"], int)
            if "error" in data:
                assert isinstance(data["error"], str)
    
    def test_model_endpoints_response_format(self):
        """Test that model endpoints return expected response format."""
        model_endpoints = [
            "/api/embedding-models",
            "/api/models/ollama",
            "/api/models/openai"
        ]
        
        for endpoint in model_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            assert "models" in data
            assert isinstance(data["models"], list)
            
            # If models are returned, they should have expected structure
            if data["models"]:
                model = data["models"][0]
                # Models should have at least a name or id field
                assert "name" in model or "id" in model or isinstance(model, str)














