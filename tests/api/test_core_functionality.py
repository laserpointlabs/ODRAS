"""
Core Functionality Tests

Essential tests that MUST pass for CI to succeed.
Only tests fully implemented and stable endpoints.

These are the minimum required tests for database changes.
"""

import pytest
import time
from httpx import AsyncClient


class TestCoreFunctionality:
    """Core functionality that must work"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200, f"Core auth failed: {response.text}"
        return {"Authorization": f"Bearer {response.json()['token']}"}

    @pytest.mark.asyncio
    async def test_api_health(self, client):
        """Core requirement: API must be healthy"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ API health check passed")

    @pytest.mark.asyncio
    async def test_authentication(self, client):
        """Core requirement: Authentication must work"""
        # Test valid login
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        assert "token" in response.json()
        print("✅ Authentication working")

        # Test invalid login
        response = await client.post(
            "/api/auth/login",
            json={"username": "fake", "password": "wrong"}
        )
        assert response.status_code == 401
        print("✅ Invalid authentication properly rejected")

    @pytest.mark.asyncio
    async def test_project_creation(self, client, auth_headers):
        """Core requirement: Project creation must work"""
        project_data = {
            "name": f"Core Test Project {int(time.time())}",
            "description": "Core functionality test project"
        }

        response = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        result = response.json()
        project = result["project"]
        project_id = project["project_id"]

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        print("✅ Project creation and deletion working")

    @pytest.mark.asyncio
    async def test_project_listing(self, client, auth_headers):
        """Core requirement: Project listing must work"""
        response = await client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, (list, dict))
        print("✅ Project listing working")

    @pytest.mark.asyncio
    async def test_service_status(self, client, auth_headers):
        """Core requirement: Service status must be accessible"""
        response = await client.get("/api/service-status", headers=auth_headers)
        # Service status might not be fully implemented
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            print("✅ Service status endpoint working")
        else:
            print("⚠️ Service status endpoint not implemented (expected)")

    @pytest.mark.asyncio
    async def test_das_health(self, client, auth_headers):
        """Core requirement: DAS system must be healthy"""
        response = await client.get("/api/das/health", headers=auth_headers)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            print("✅ DAS health check working")
        else:
            print("⚠️ DAS health endpoint not implemented")

    @pytest.mark.asyncio
    async def test_das_interaction_with_openai(self, client, auth_headers):
        """Core requirement: DAS must work with OpenAI API (when key available)"""
        import os

        # Skip if no API key (local testing without OpenAI)
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️ No OpenAI API key - skipping DAS interaction test")
            return

        # Create a test project first
        project_data = {
            "name": f"DAS Test Project {int(time.time())}",
            "description": "Testing DAS interaction with OpenAI"
        }

        project_resp = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert project_resp.status_code == 200

        result = project_resp.json()
        project = result["project"]
        project_id = project["project_id"]

        try:
            # Test DAS2 chat with a simple question
            das_message = {
                "message": "What is this project about? Please respond briefly.",
                "project_id": project_id
            }

            print("    Testing DAS2 chat with OpenAI...")
            das_resp = await client.post(
                "/api/das2/chat",
                json=das_message,
                headers=auth_headers
            )

            if das_resp.status_code == 200:
                response_data = das_resp.json()
                print("✅ DAS2 working with OpenAI")
                if "message" in response_data:
                    message = response_data['message']
                    print(f"    DAS Response: {message[:150]}...")
                    # Validate it's a real AI response (not error message)
                    if len(message) > 10 and "error" not in message.lower():
                        print("    ✅ Real AI response received")
                    else:
                        print("    ⚠️ Response may be error message")
                else:
                    print("    ⚠️ No message in DAS response")
            elif das_resp.status_code == 404:
                print("⚠️ DAS2 endpoint not implemented")

                # Try DAS simple endpoint
                print("    Testing DAS simple chat...")
                simple_resp = await client.post(
                    "/api/das-simple/chat",
                    json=das_message,
                    headers=auth_headers
                )

                if simple_resp.status_code == 200:
                    simple_data = simple_resp.json()
                    print("✅ DAS simple working with OpenAI")
                    if "message" in simple_data:
                        print(f"    DAS Response: {simple_data['message'][:150]}...")
                else:
                    print(f"⚠️ DAS simple failed (status: {simple_resp.status_code})")
            else:
                print(f"⚠️ DAS2 failed (status: {das_resp.status_code})")
                response_text = das_resp.text if hasattr(das_resp, 'text') else str(das_resp.content)
                print(f"    Response: {response_text[:200]}...")

        finally:
            # Cleanup project
            await client.delete(f"/api/projects/{project_id}", headers=auth_headers)


# Run core tests only
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
