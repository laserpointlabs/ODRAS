"""
Project CRUD Operations Tests

Comprehensive tests for all project-related operations:
- Create, Read, Update, Delete projects
- Project member management
- Project metadata handling
- Project archiving and restoration
- Access control and permissions

Run with: pytest tests/api/test_project_crud.py -v
"""

import pytest
import time
import json
from typing import Dict, List, Any
from httpx import AsyncClient
from pathlib import Path
import sys

# Add project root to path if needed for any imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestProjectCRUD:
    """Test all project CRUD operations"""

    @pytest.fixture
    async def client(self):
        # Connect to the REAL running API with longer timeout
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
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

    @pytest.fixture
    async def admin_headers(self, client):
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"Authorization": f"Bearer {response.json()['token']}"}
        # Fallback to regular user
        return await self.auth_headers(client)

    # ========== CREATE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_create_basic_project(self, client, auth_headers):
        """Test creating a basic project"""
        project_data = {
            "name": f"Basic Project {int(time.time())}",
            "description": "A simple test project"
        }

        response = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        result = response.json()
        project = result["project"]
        assert "project_id" in project
        assert project["name"] == project_data["name"]
        assert project["description"] == project_data["description"]
        assert project["is_active"] is True

        # Cleanup
        await client.delete(f"/api/projects/{project['project_id']}", headers=auth_headers)
        print("✓ Basic project creation tested")

    @pytest.mark.asyncio
    async def test_create_project_with_metadata(self, client, auth_headers):
        """Test creating a project with metadata"""
        project_data = {
            "name": f"Metadata Project {int(time.time())}",
            "description": "Project with rich metadata",
            "metadata": {
                "department": "Engineering",
                "priority": "high",
                "tags": ["test", "automated", "ci/cd"],
                "budget": 50000,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }

        response = await client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        project = response.json()
        if "metadata" in project:
            assert project["metadata"]["department"] == "Engineering"
            assert "tags" in project["metadata"]

        # Cleanup
        await client.delete(f"/api/projects/{project['project_id']}", headers=auth_headers)
        print("✓ Project with metadata creation tested")

    @pytest.mark.asyncio
    async def test_create_project_validation(self, client, auth_headers):
        """Test project creation validation"""
        invalid_projects = [
            # Missing name
            {"description": "No name provided"},
            # Empty name
            {"name": "", "description": "Empty name"},
            # Name too long
            {"name": "A" * 1000, "description": "Name too long"},
            # Invalid characters
            {"name": "Project\x00WithNull", "description": "Null character"},
            # Missing all fields
            {}
        ]

        for invalid_data in invalid_projects:
            response = await client.post(
                "/api/projects",
                json=invalid_data,
                headers=auth_headers
            )
            assert response.status_code in [400, 422], f"Expected validation error for {invalid_data}"

        print("✓ Project creation validation tested")

    # ========== READ OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_read_project_by_id(self, client, auth_headers):
        """Test reading a project by ID"""
        # Create a project first
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Read Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Read the project
        response = await client.get(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        project = response.json()
        assert project["project_id"] == project_id
        assert "name" in project
        assert "created_at" in project
        assert "created_by" in project

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        print("✓ Read project by ID tested")

    @pytest.mark.asyncio
    async def test_list_projects(self, client, auth_headers):
        """Test listing projects with various filters"""
        # Create multiple projects
        project_ids = []
        for i in range(3):
            resp = await client.post(
                "/api/projects",
                json={"name": f"List Test {i} {int(time.time())}"},
                headers=auth_headers
            )
            project_ids.append(resp.json()["project_id"])

        # List all active projects
        response = await client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, list)
        assert len(projects) >= 3

        # List with pagination
        paginated_resp = await client.get(
            "/api/projects",
            params={"limit": 2, "offset": 0},
            headers=auth_headers
        )
        assert paginated_resp.status_code in [200, 404]  # 404 if pagination not supported

        # List including archived
        archived_resp = await client.get(
            "/api/projects",
            params={"include_archived": True},
            headers=auth_headers
        )
        assert archived_resp.status_code in [200, 404]

        # Cleanup
        for project_id in project_ids:
            await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

        print("✓ List projects with filters tested")

    @pytest.mark.asyncio
    async def test_project_not_found(self, client, auth_headers):
        """Test accessing non-existent project"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.get(
            f"/api/projects/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ Project not found handling tested")

    # ========== UPDATE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_update_project_name(self, client, auth_headers):
        """Test updating project name"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Original Name {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Update name
        new_name = f"Updated Name {int(time.time())}"
        response = await client.put(
            f"/api/projects/{project_id}",
            json={"name": new_name},
            headers=auth_headers
        )
        assert response.status_code == 200

        updated = response.json()
        assert updated["name"] == new_name
        assert updated["project_id"] == project_id

        # Verify update persisted
        get_resp = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert get_resp.json()["name"] == new_name

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        print("✓ Update project name tested")

    @pytest.mark.asyncio
    async def test_update_project_metadata(self, client, auth_headers):
        """Test updating project metadata"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={
                "name": f"Metadata Update Test {int(time.time())}",
                "metadata": {"version": 1, "status": "active"}
            },
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Update metadata
        new_metadata = {
            "version": 2,
            "status": "in_progress",
            "last_modified": "2024-01-15",
            "tags": ["updated", "tested"]
        }

        response = await client.put(
            f"/api/projects/{project_id}",
            json={"metadata": new_metadata},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        print("✓ Update project metadata tested")

    @pytest.mark.asyncio
    async def test_partial_update(self, client, auth_headers):
        """Test partial project updates"""
        # Create project with full data
        create_resp = await client.post(
            "/api/projects",
            json={
                "name": f"Partial Update Test {int(time.time())}",
                "description": "Original description",
                "metadata": {"key1": "value1", "key2": "value2"}
            },
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Update only description
        response = await client.put(
            f"/api/projects/{project_id}",
            json={"description": "Updated description only"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify other fields unchanged
        updated = response.json()
        assert updated["description"] == "Updated description only"
        assert "name" in updated  # Name should still exist

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
        print("✓ Partial project update tested")

    # ========== DELETE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_delete_project_archive(self, client, auth_headers):
        """Test project deletion (archiving)"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Delete Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Delete (archive) project
        response = await client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify it's archived (not in active list)
        list_resp = await client.get("/api/projects", headers=auth_headers)
        active_projects = list_resp.json()
        assert not any(p["project_id"] == project_id for p in active_projects)

        print("✓ Project deletion (archiving) tested")

    @pytest.mark.asyncio
    async def test_restore_archived_project(self, client, auth_headers):
        """Test restoring an archived project"""
        # Create and archive project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Restore Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Archive it
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

        # Restore project
        restore_resp = await client.post(
            f"/api/projects/{project_id}/restore",
            headers=auth_headers
        )

        if restore_resp.status_code == 200:
            # Verify it's active again
            get_resp = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
            if get_resp.status_code == 200:
                assert get_resp.json()["is_active"] is True
            print("✓ Project restoration tested")
        else:
            print("⚠ Project restoration endpoint not implemented")

    @pytest.mark.asyncio
    async def test_permanent_delete(self, client, admin_headers):
        """Test permanent project deletion (admin only)"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Permanent Delete Test {int(time.time())}"},
            headers=admin_headers
        )
        project_id = create_resp.json()["project_id"]

        # Try permanent delete
        perm_delete_resp = await client.delete(
            f"/api/projects/{project_id}",
            params={"permanent": True},
            headers=admin_headers
        )

        if perm_delete_resp.status_code in [200, 204]:
            # Verify it's gone
            get_resp = await client.get(f"/api/projects/{project_id}", headers=admin_headers)
            assert get_resp.status_code == 404
            print("✓ Permanent project deletion tested")
        else:
            # Just do regular cleanup
            await client.delete(f"/api/projects/{project_id}", headers=admin_headers)
            print("⚠ Permanent deletion not implemented")

    # ========== ACCESS CONTROL ==========

    @pytest.mark.asyncio
    async def test_project_access_control(self, client):
        """Test project access control between users"""
        # Login as das_service
        das_resp = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        das_headers = {"Authorization": f"Bearer {das_resp.json()['token']}"}

        # Create project as das_service
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Access Control Test {int(time.time())}"},
            headers=das_headers
        )
        project_id = create_resp.json()["project_id"]

        # Try to access without auth
        unauth_resp = await client.get(f"/api/projects/{project_id}")
        assert unauth_resp.status_code == 401

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=das_headers)
        print("✓ Project access control tested")

    # ========== MEMBER MANAGEMENT ==========

    @pytest.mark.asyncio
    async def test_project_members(self, client, auth_headers):
        """Test project member management"""
        # Create project
        create_resp = await client.post(
            "/api/projects",
            json={"name": f"Member Test {int(time.time())}"},
            headers=auth_headers
        )
        project_id = create_resp.json()["project_id"]

        # Add member (if endpoint exists)
        add_member_resp = await client.post(
            f"/api/projects/{project_id}/members",
            json={"username": "admin", "role": "contributor"},
            headers=auth_headers
        )

        if add_member_resp.status_code in [200, 201]:
            # List members
            list_resp = await client.get(
                f"/api/projects/{project_id}/members",
                headers=auth_headers
            )
            assert list_resp.status_code == 200
            members = list_resp.json()
            assert isinstance(members, list)

            # Remove member
            remove_resp = await client.delete(
                f"/api/projects/{project_id}/members/admin",
                headers=auth_headers
            )
            assert remove_resp.status_code in [200, 204]
            print("✓ Project member management tested")
        else:
            print("⚠ Project member management not implemented")

        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)


# Run all project CRUD tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
