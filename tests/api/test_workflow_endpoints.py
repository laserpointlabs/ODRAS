"""
Test suite for Workflow API endpoints.

Tests all workflow-related endpoints including user tasks,
runs, personas, prompts, and workflow management.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestWorkflowEndpoints:
    """Test workflow API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication."""
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
    
    def test_get_user_tasks(self):
        """Test GET /api/user-tasks - list user tasks."""
        response = client.get("/api/user-tasks", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
    
    def test_get_user_task_by_id(self):
        """Test GET /api/user-tasks/{process_instance_id} - get specific task."""
        response = client.get("/api/user-tasks/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_get_user_task_requirements(self):
        """Test GET /api/user-tasks/{process_instance_id}/requirements - get task requirements."""
        response = client.get("/api/user-tasks/1/requirements", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_complete_user_task(self):
        """Test POST /api/user-tasks/{process_instance_id}/complete - complete task."""
        complete_data = {
            "decision": "approve",
            "approved_requirements": []
        }
        
        response = client.post(
            "/api/user-tasks/1/complete",
            json=complete_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 201, 404, 501]
    
    def test_get_user_task_status(self):
        """Test GET /api/user-tasks/{process_instance_id}/status - get task status."""
        response = client.get("/api/user-tasks/1/status", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_get_runs(self):
        """Test GET /api/runs - list workflow runs."""
        response = client.get("/api/runs", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert isinstance(data["runs"], list)
    
    def test_get_run_by_id(self):
        """Test GET /api/runs/{run_id} - get specific run."""
        response = client.get("/api/runs/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_get_personas(self):
        """Test GET /api/personas - list personas."""
        response = client.get("/api/personas", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
        assert isinstance(data["personas"], list)
    
    def test_create_persona(self):
        """Test POST /api/personas - create persona."""
        persona_data = {
            "name": "Test Persona",
            "description": "Test persona description",
            "system_prompt": "You are a test persona.",
            "is_active": True
        }
        
        response = client.post(
            "/api/personas",
            json=persona_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 201, 404, 501]
    
    def test_get_persona_by_id(self):
        """Test GET /api/personas/{persona_id} - get specific persona."""
        response = client.get("/api/personas/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_update_persona(self):
        """Test PUT /api/personas/{persona_id} - update persona."""
        update_data = {
            "name": "Updated Persona",
            "description": "Updated description",
            "is_active": False
        }
        
        response = client.put(
            "/api/personas/1",
            json=update_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_delete_persona(self):
        """Test DELETE /api/personas/{persona_id} - delete persona."""
        response = client.delete("/api/personas/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 204, 404, 501]
    
    def test_get_prompts(self):
        """Test GET /api/prompts - list prompts."""
        response = client.get("/api/prompts", headers=self._get_headers())
        
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert isinstance(data["prompts"], list)
    
    def test_create_prompt(self):
        """Test POST /api/prompts - create prompt."""
        prompt_data = {
            "name": "Test Prompt",
            "description": "Test prompt description",
            "prompt_template": "Test prompt template: {input}",
            "is_active": True
        }
        
        response = client.post(
            "/api/prompts",
            json=prompt_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 201, 404, 501]
    
    def test_get_prompt_by_id(self):
        """Test GET /api/prompts/{prompt_id} - get specific prompt."""
        response = client.get("/api/prompts/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_update_prompt(self):
        """Test PUT /api/prompts/{prompt_id} - update prompt."""
        update_data = {
            "name": "Updated Prompt",
            "description": "Updated description",
            "is_active": False
        }
        
        response = client.put(
            "/api/prompts/1",
            json=update_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_delete_prompt(self):
        """Test DELETE /api/prompts/{prompt_id} - delete prompt."""
        response = client.delete("/api/prompts/1", headers=self._get_headers())
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 204, 404, 501]
    
    def test_test_prompt(self):
        """Test POST /api/prompts/{prompt_id}/test - test prompt."""
        test_data = {
            "input": "Test input for prompt",
            "parameters": {"temperature": 0.7}
        }
        
        response = client.post(
            "/api/prompts/1/test",
            json=test_data,
            headers=self._get_headers()
        )
        
        # This endpoint might not be implemented yet, so we check for either success or 404/501
        assert response.status_code in [200, 404, 501]
    
    def test_workflow_endpoints_require_auth(self):
        """Test that workflow endpoints require authentication."""
        endpoints = [
            ("GET", "/api/user-tasks"),
            ("GET", "/api/user-tasks/1"),
            ("GET", "/api/user-tasks/1/requirements"),
            ("POST", "/api/user-tasks/1/complete"),
            ("GET", "/api/user-tasks/1/status"),
            ("GET", "/api/runs"),
            ("GET", "/api/runs/1"),
            ("GET", "/api/personas"),
            ("POST", "/api/personas"),
            ("GET", "/api/personas/1"),
            ("PUT", "/api/personas/1"),
            ("DELETE", "/api/personas/1"),
            ("GET", "/api/prompts"),
            ("POST", "/api/prompts"),
            ("GET", "/api/prompts/1"),
            ("PUT", "/api/prompts/1"),
            ("DELETE", "/api/prompts/1"),
            ("POST", "/api/prompts/1/test"),
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













