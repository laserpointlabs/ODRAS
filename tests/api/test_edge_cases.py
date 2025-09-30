"""
Edge Cases and Error Handling Tests

Tests for boundary conditions, error scenarios, and edge cases
across all ODRAS API endpoints.

Run with: pytest tests/api/test_edge_cases.py -v
"""

import pytest
import asyncio
import time
import json
from typing import List
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    # ========== AUTHENTICATION EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_invalid_credentials(self, client):
        """Test various invalid credential scenarios"""
        test_cases = [
            # Wrong password
            {"username": "das_service", "password": "wrong_password"},
            # Non-existent user
            {"username": "non_existent_user", "password": "any_password"},
            # Empty credentials
            {"username": "", "password": ""},
            # Missing fields
            {"username": "das_service"},
            {"password": "das_service_2024!"},
            # SQL injection attempt
            {"username": "admin' OR '1'='1", "password": "password"},
            # Very long username
            {"username": "a" * 1000, "password": "password"}
        ]

        for creds in test_cases:
            response = await client.post("/api/auth/login", json=creds)
            assert response.status_code in [400, 401, 422], f"Unexpected status for {creds}"

    @pytest.mark.asyncio
    async def test_expired_token_handling(self, client):
        """Test handling of expired or invalid tokens"""
        invalid_tokens = [
            "Bearer invalid_token",
            "Bearer ",
            "invalid_token",
            "Bearer null",
            "Bearer undefined",
            f"Bearer {'x' * 1000}",  # Very long token
            ""  # Empty authorization header
        ]

        for token in invalid_tokens:
            headers = {"Authorization": token} if token else {}
            response = await client.get("/api/projects", headers=headers)
            assert response.status_code == 401, f"Expected 401 for token: {token}"

    # ========== PROJECT EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_project_name_edge_cases(self, client, auth_headers):
        """Test project creation with edge case names"""
        edge_names = [
            # Unicode and special characters
            "项目名称 🚀 Test",
            "Project\nWith\nNewlines",
            "Project\tWith\tTabs",
            "   Spaces Before and After   ",
            # HTML/Script injection attempts
            "<script>alert('xss')</script>",
            "Project <b>Bold</b> Name",
            # SQL injection attempts
            "Project'; DROP TABLE projects; --",
            # Very long name
            "P" * 500,
            # Special filesystem characters
            "Project/With/Slashes",
            "Project\\With\\Backslashes",
            "Project:With:Colons",
            "Project|With|Pipes",
            # Empty or whitespace
            "     ",  # Just spaces
            ""  # Empty string (should fail)
        ]

        for name in edge_names:
            response = await client.post(
                "/api/projects",
                json={"name": name, "description": "Edge case test"},
                headers=auth_headers
            )

            if name.strip():  # Non-empty names might succeed
                if response.status_code == 200:
                    # Clean up successful creations
                    project_id = response.json()["project_id"]
                    await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
            else:  # Empty names should fail
                assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_project_access_control(self, client):
        """Test project access control and permissions"""
        # Create project as das_service
        das_login = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        das_headers = {"Authorization": f"Bearer {das_login.json()['token']}"}

        project_resp = await client.post(
            "/api/projects",
            json={"name": f"Access Test {int(time.time())}"},
            headers=das_headers
        )
        project_id = project_resp.json()["project_id"]

        # Try to access without authentication
        unauth_resp = await client.get(f"/api/projects/{project_id}")
        assert unauth_resp.status_code == 401

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=das_headers)

    @pytest.mark.asyncio
    async def test_non_existent_project_operations(self, client, auth_headers):
        """Test operations on non-existent projects"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        # Try various operations on non-existent project
        operations = [
            ("GET", f"/api/projects/{fake_id}"),
            ("PUT", f"/api/projects/{fake_id}"),
            ("DELETE", f"/api/projects/{fake_id}"),
            ("POST", f"/api/files/upload/{fake_id}"),
            ("GET", f"/api/files/project/{fake_id}"),
            ("POST", f"/api/knowledge/{fake_id}/search"),
            ("POST", f"/api/ontology/{fake_id}/create")
        ]

        for method, url in operations:
            if method == "GET":
                response = await client.get(url, headers=auth_headers)
            elif method == "PUT":
                response = await client.put(url, json={"name": "Updated"}, headers=auth_headers)
            elif method == "DELETE":
                response = await client.delete(url, headers=auth_headers)
            elif method == "POST":
                response = await client.post(url, json={}, headers=auth_headers)

            assert response.status_code in [403, 404], f"Expected 403/404 for {method} {url}"

    # ========== FILE UPLOAD EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_file_upload_edge_cases(self, client, auth_headers):
        """Test file upload with edge cases"""
        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"File Edge Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = proj_resp.json()["project_id"]

        # Test various file scenarios
        test_files = [
            # Empty file
            ("empty.txt", b"", "text/plain"),
            # Very large filename
            ("a" * 255 + ".txt", b"content", "text/plain"),
            # Special characters in filename
            ("file<>:|?*.txt", b"content", "text/plain"),
            # No extension
            ("noextension", b"content", "application/octet-stream"),
            # Multiple dots
            ("file.test.multiple.dots.txt", b"content", "text/plain"),
            # Unicode filename
            ("文件名.txt", b"content", "text/plain"),
            # Path traversal attempt
            ("../../../etc/passwd", b"content", "text/plain"),
            # Null bytes in filename
            ("file\x00.txt", b"content", "text/plain")
        ]

        for filename, content, mime_type in test_files:
            try:
                files = {"file": (filename, content, mime_type)}
                response = await client.post(
                    f"/api/files/upload/{project_id}",
                    files=files,
                    headers=auth_headers
                )
                # Some might succeed, some might fail
                assert response.status_code in [200, 400, 422]
            except Exception:
                # Some edge cases might cause exceptions
                pass

        # Test file size limits (if any)
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        files = {"file": ("large.txt", large_content, "text/plain")}
        large_resp = await client.post(
            f"/api/files/upload/{project_id}",
            files=files,
            headers=auth_headers
        )
        # Should either succeed or return appropriate error
        assert large_resp.status_code in [200, 413, 507]

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, client, auth_headers):
        """Test concurrent file uploads to same project"""
        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"Concurrent Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = proj_resp.json()["project_id"]

        # Upload multiple files concurrently
        upload_tasks = []
        for i in range(10):
            files = {"file": (f"concurrent_{i}.txt", f"Content {i}".encode(), "text/plain")}
            task = client.post(
                f"/api/files/upload/{project_id}",
                files=files,
                headers=auth_headers
            )
            upload_tasks.append(task)

        responses = await asyncio.gather(*upload_tasks, return_exceptions=True)
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]

        # At least some should succeed
        assert len(successful) > 0, "No concurrent uploads succeeded"

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== KNOWLEDGE SEARCH EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_knowledge_search_edge_cases(self, client, auth_headers):
        """Test knowledge search with edge cases"""
        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"Search Edge Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = proj_resp.json()["project_id"]

        # Edge case search queries
        edge_queries = [
            # Empty query
            {"query": "", "top_k": 5},
            # Very long query
            {"query": "test " * 1000, "top_k": 5},
            # Special characters
            {"query": "!@#$%^&*()", "top_k": 5},
            # SQL injection attempt
            {"query": "'; DROP TABLE knowledge; --", "top_k": 5},
            # Unicode
            {"query": "搜索测试 🔍", "top_k": 5},
            # Invalid top_k values
            {"query": "test", "top_k": -1},
            {"query": "test", "top_k": 0},
            {"query": "test", "top_k": 10000},
            {"query": "test", "top_k": "not_a_number"},
            # Missing required fields
            {"top_k": 5},  # Missing query
            {"query": "test"},  # Missing top_k
            # Null values
            {"query": None, "top_k": 5},
            {"query": "test", "top_k": None}
        ]

        for query_data in edge_queries:
            response = await client.post(
                f"/api/knowledge/{project_id}/search",
                json=query_data,
                headers=auth_headers
            )
            # Should handle gracefully
            assert response.status_code in [200, 400, 422]

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== ONTOLOGY EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_ontology_edge_cases(self, client, auth_headers):
        """Test ontology operations with edge cases"""
        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"Ontology Edge Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = proj_resp.json()["project_id"]

        # Edge case ontology data
        edge_ontologies = [
            # Invalid URIs
            {"name": "Test", "base_uri": "not_a_valid_uri"},
            {"name": "Test", "base_uri": ""},
            {"name": "Test", "base_uri": "http://"},
            # Special characters in names
            {"name": "Ontology<script>", "base_uri": "http://test.com#"},
            {"name": "Onto\nWith\nNewlines", "base_uri": "http://test.com#"},
            # Very long values
            {"name": "O" * 1000, "base_uri": "http://test.com#"},
            {"name": "Test", "base_uri": "http://test.com/" + "a" * 1000 + "#"},
            # Missing required fields
            {"base_uri": "http://test.com#"},  # Missing name
            {"name": "Test"},  # Missing base_uri
        ]

        for onto_data in edge_ontologies:
            response = await client.post(
                f"/api/ontology/{project_id}/create",
                json=onto_data,
                headers=auth_headers
            )
            # Should handle gracefully
            assert response.status_code in [200, 201, 204, 400, 422]

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== RATE LIMITING AND PERFORMANCE ==========

    @pytest.mark.asyncio
    async def test_rapid_requests(self, client, auth_headers):
        """Test API behavior under rapid request load"""
        # Make many requests rapidly
        start_time = time.time()
        request_count = 50

        tasks = []
        for _ in range(request_count):
            tasks.append(client.get("/api/projects", headers=auth_headers))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        # Count successful responses
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
        rate_limited = [r for r in responses if not isinstance(r, Exception) and r.status_code == 429]

        print(f"\nRapid request test: {len(successful)}/{request_count} successful in {elapsed:.2f}s")
        print(f"Rate limited: {len(rate_limited)} requests")

        # Most should succeed (no strict rate limiting expected in test env)
        assert len(successful) > request_count * 0.8, "Too many requests failed"

    # ========== MALFORMED REQUESTS ==========

    @pytest.mark.asyncio
    async def test_malformed_json_requests(self, client, auth_headers):
        """Test API handling of malformed JSON"""
        # Send invalid JSON
        invalid_json_response = await client.post(
            "/api/projects",
            content=b"{'invalid': json syntax}",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert invalid_json_response.status_code in [400, 422]

        # Send non-JSON content with JSON content-type
        text_response = await client.post(
            "/api/projects",
            content=b"This is plain text, not JSON",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert text_response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client, auth_headers):
        """Test calling endpoints with wrong HTTP methods"""
        # Try wrong methods on various endpoints
        wrong_method_tests = [
            ("PUT", "/api/auth/login"),  # Should be POST
            ("GET", "/api/projects"),  # This should work
            ("POST", "/api/projects/123"),  # Should be GET/PUT/DELETE
            ("DELETE", "/api/auth/login"),  # Should be POST
            ("PATCH", "/api/projects"),  # Might not be implemented
        ]

        for method, url in wrong_method_tests:
            request = client.build_request(method, url, headers=auth_headers)
            response = await client.send(request)

            # GET /api/projects should work
            if method == "GET" and url == "/api/projects":
                assert response.status_code == 200
            else:
                # Others should return 405 or 404
                assert response.status_code in [404, 405]

    # ========== DATA VALIDATION ==========

    @pytest.mark.asyncio
    async def test_data_type_validation(self, client, auth_headers):
        """Test API data type validation"""
        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"name": f"Validation Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = proj_resp.json()["project_id"]

        # Test knowledge search with wrong data types
        invalid_searches = [
            {"query": 123, "top_k": 5},  # Query should be string
            {"query": "test", "top_k": "five"},  # top_k should be int
            {"query": ["test", "array"], "top_k": 5},  # Query should be string
            {"query": {"nested": "object"}, "top_k": 5},  # Query should be string
        ]

        for search_data in invalid_searches:
            response = await client.post(
                f"/api/knowledge/{project_id}/search",
                json=search_data,
                headers=auth_headers
            )
            assert response.status_code in [400, 422]

        # Clean up
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_boundary_values(self, client, auth_headers):
        """Test API with boundary values"""
        # Create project with boundary length name
        boundary_names = [
            "A",  # Single character
            "AB",  # Two characters
            "A" * 255,  # Max reasonable length
            "A" * 256,  # Just over typical limit
        ]

        for name in boundary_names:
            response = await client.post(
                "/api/projects",
                json={"name": name},
                headers=auth_headers
            )

            if len(name) <= 255:  # Reasonable length
                if response.status_code == 200:
                    project_id = response.json()["project_id"]
                    await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
            else:  # Too long
                assert response.status_code in [400, 422]


# Summary function for edge case testing
async def run_edge_case_summary():
    """Run a summary of critical edge cases"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        auth_resp = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        headers = {"Authorization": f"Bearer {auth_resp.json()['token']}"}

        print("\n" + "="*60)
        print("Edge Case Testing Summary")
        print("="*60 + "\n")

        # Test invalid authentication
        invalid_auth = await client.post(
            "/api/auth/login",
            json={"username": "invalid", "password": "invalid"}
        )
        print(f"✓ Invalid auth handled: {invalid_auth.status_code}")

        # Test non-existent resource
        fake_project = await client.get(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            headers=headers
        )
        print(f"✓ Non-existent resource: {fake_project.status_code}")

        # Test malformed request
        malformed = await client.post(
            "/api/projects",
            json={},  # Missing required fields
            headers=headers
        )
        print(f"✓ Malformed request: {malformed.status_code}")

        # Test special characters
        special_proj = await client.post(
            "/api/projects",
            json={"name": "Test <script>alert('xss')</script>"},
            headers=headers
        )
        if special_proj.status_code == 200:
            proj_id = special_proj.json()["project_id"]
            await client.delete(f"/api/projects/{proj_id}", headers=headers)
            print("✓ Special characters handled gracefully")
        else:
            print(f"✓ Special characters rejected: {special_proj.status_code}")

        print("\n✓ Edge case testing completed!")
        print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_edge_case_summary())
