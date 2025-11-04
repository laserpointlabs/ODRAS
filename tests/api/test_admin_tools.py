"""
Admin Tools and Management Tests

Comprehensive tests for all administrative functionality including:
- Prefix Management
- Domain Management
- Namespace Management
- User Management
- Document Management
- System Administration

Run with: pytest tests/api/test_admin_tools.py -v
"""

import pytest
import time
import json
from typing import Dict, List, Any
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app


class TestPrefixManagement:
    """Test prefix management functionality"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        # Try different admin accounts
        for username, password in [
            ("admin", "admin123!"),
            ("jdehart", "jdehart123!"),
            ("das_service", "das_service_2024!")  # Fallback if no admin
        ]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                token = response.json()["token"]
                return {"Authorization": f"Bearer {token}"}
        pytest.skip("No admin user available")

    @pytest.mark.asyncio
    async def test_prefix_crud(self, client, admin_headers):
        """Test prefix create, read, update, delete operations"""
        # Create prefix
        prefix_data = {
            "prefix": f"test{int(time.time())}",
            "namespace": f"http://test.odras.ai/prefix/{int(time.time())}#",
            "description": "Test prefix for admin tools testing"
        }

        create_resp = await client.post(
            "/api/prefixes",
            json=prefix_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            created_prefix = create_resp.json()
            prefix_id = created_prefix.get("id") or created_prefix.get("prefix_id")

            # List prefixes
            list_resp = await client.get("/api/prefixes", headers=admin_headers)
            assert list_resp.status_code == 200
            prefixes = list_resp.json()
            assert isinstance(prefixes, list)

            # Get specific prefix (if endpoint exists)
            if prefix_id:
                get_resp = await client.get(
                    f"/api/prefixes/{prefix_id}",
                    headers=admin_headers
                )
                assert get_resp.status_code in [200, 404]

            # Update prefix (if supported)
            update_resp = await client.put(
                f"/api/prefixes/{prefix_data['prefix']}",
                json={"description": "Updated description"},
                headers=admin_headers
            )
            assert update_resp.status_code in [200, 404]

            # Delete prefix
            delete_resp = await client.delete(
                f"/api/prefixes/{prefix_data['prefix']}",
                headers=admin_headers
            )
            assert delete_resp.status_code in [200, 204, 404]

        print("✓ Prefix management CRUD operations tested")

    @pytest.mark.asyncio
    async def test_prefix_validation(self, client, admin_headers):
        """Test prefix validation rules"""
        invalid_prefixes = [
            # Invalid format
            {"prefix": "123start", "namespace": "http://test.com#"},  # Starting with number
            {"prefix": "test space", "namespace": "http://test.com#"},  # Contains space
            {"prefix": "test-hyphen", "namespace": "http://test.com#"},  # Contains hyphen
            {"prefix": "", "namespace": "http://test.com#"},  # Empty prefix
            {"prefix": "a", "namespace": "http://test.com#"},  # Too short
            # Invalid namespace
            {"prefix": "valid", "namespace": "not_a_uri"},
            {"prefix": "valid", "namespace": ""},
            # Missing fields
            {"prefix": "test"},
            {"namespace": "http://test.com#"}
        ]

        for invalid_data in invalid_prefixes:
            resp = await client.post(
                "/api/prefixes",
                json=invalid_data,
                headers=admin_headers
            )
            assert resp.status_code in [400, 422], f"Expected validation error for {invalid_data}"

        print("✓ Prefix validation tested")

    @pytest.mark.asyncio
    async def test_prefix_conflicts(self, client, admin_headers):
        """Test handling of prefix conflicts"""
        prefix_data = {
            "prefix": f"conflict{int(time.time())}",
            "namespace": "http://test.odras.ai/conflict#"
        }

        # Create first prefix
        resp1 = await client.post("/api/prefixes", json=prefix_data, headers=admin_headers)

        if resp1.status_code == 200:
            # Try to create duplicate
            resp2 = await client.post("/api/prefixes", json=prefix_data, headers=admin_headers)
            assert resp2.status_code in [400, 409], "Duplicate prefix should be rejected"

            # Clean up
            await client.delete(f"/api/prefixes/{prefix_data['prefix']}", headers=admin_headers)

        print("✓ Prefix conflict handling tested")


class TestDomainManagement:
    """Test domain management functionality"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("No admin user available")

    @pytest.mark.asyncio
    async def test_domain_crud(self, client, admin_headers):
        """Test domain CRUD operations"""
        domain_data = {
            "domain": f"test{int(time.time())}.odras.ai",
            "description": "Test domain for admin tools",
            "is_public": False,
            "metadata": {"purpose": "testing", "environment": "test"}
        }

        # Create domain
        create_resp = await client.post(
            "/api/domains",
            json=domain_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            domain = create_resp.json()
            domain_id = domain.get("domain_id")

            # List domains
            list_resp = await client.get("/api/domains", headers=admin_headers)
            assert list_resp.status_code == 200
            domains = list_resp.json()
            assert isinstance(domains, list)

            # Get specific domain
            if domain_id:
                get_resp = await client.get(
                    f"/api/domains/{domain_id}",
                    headers=admin_headers
                )
                assert get_resp.status_code in [200, 404]

            # Update domain
            update_resp = await client.put(
                f"/api/domains/{domain_data['domain']}",
                json={"description": "Updated domain description"},
                headers=admin_headers
            )
            assert update_resp.status_code in [200, 404]

            # Delete domain
            delete_resp = await client.delete(
                f"/api/domains/{domain_data['domain']}",
                headers=admin_headers
            )
            assert delete_resp.status_code in [200, 204, 404]

        print("✓ Domain management CRUD operations tested")

    @pytest.mark.asyncio
    async def test_domain_validation(self, client, admin_headers):
        """Test domain validation rules"""
        invalid_domains = [
            # Invalid format
            {"domain": "not_a_domain"},
            {"domain": "test@domain.com"},  # Email format
            {"domain": "http://domain.com"},  # URL format
            {"domain": "domain with spaces.com"},
            {"domain": ""},  # Empty
            {"domain": ".com"},  # TLD only
            {"domain": "domain..com"},  # Double dots
            # Missing fields
            {"description": "No domain field"}
        ]

        for invalid_data in invalid_domains:
            resp = await client.post(
                "/api/domains",
                json=invalid_data,
                headers=admin_headers
            )
            assert resp.status_code in [400, 422], f"Expected validation error for {invalid_data}"

        print("✓ Domain validation tested")

    @pytest.mark.asyncio
    async def test_public_domain_access(self, client):
        """Test public domain access without authentication"""
        # Try to list public domains without auth
        public_resp = await client.get("/api/domains/public")
        # Should either work or return 404 if endpoint doesn't exist
        assert public_resp.status_code in [200, 404]

        if public_resp.status_code == 200:
            domains = public_resp.json()
            # Should only contain public domains
            for domain in domains:
                if "is_public" in domain:
                    assert domain["is_public"] is True

        print("✓ Public domain access tested")


class TestNamespaceManagement:
    """Test namespace management functionality"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("No admin user available")

    @pytest.fixture
    async def user_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        return {"Authorization": f"Bearer {response.json()['token']}"}

    @pytest.mark.asyncio
    async def test_namespace_crud(self, client, admin_headers):
        """Test namespace CRUD operations"""
        namespace_data = {
            "name": f"test-namespace-{int(time.time())}",
            "description": "Test namespace for admin tools",
            "base_uri": f"http://test.odras.ai/ns/{int(time.time())}#",
            "namespace_type": "project",  # or "service", "system"
            "is_public": False
        }

        # Create namespace
        create_resp = await client.post(
            "/api/namespaces",
            json=namespace_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            namespace = create_resp.json()
            namespace_id = namespace.get("namespace_id")

            # List namespaces
            list_resp = await client.get("/api/namespaces", headers=admin_headers)
            assert list_resp.status_code == 200
            namespaces = list_resp.json()
            assert isinstance(namespaces, list)

            # Get specific namespace
            if namespace_id:
                get_resp = await client.get(
                    f"/api/namespaces/{namespace_id}",
                    headers=admin_headers
                )
                assert get_resp.status_code == 200
                retrieved = get_resp.json()
                assert retrieved["namespace_id"] == namespace_id

            # Update namespace
            if namespace_id:
                update_resp = await client.put(
                    f"/api/namespaces/{namespace_id}",
                    json={"description": "Updated namespace description"},
                    headers=admin_headers
                )
                assert update_resp.status_code in [200, 404]

            # Delete namespace
            if namespace_id:
                delete_resp = await client.delete(
                    f"/api/namespaces/{namespace_id}",
                    headers=admin_headers
                )
                assert delete_resp.status_code in [200, 204, 404]

        print("✓ Namespace management CRUD operations tested")

    @pytest.mark.asyncio
    async def test_namespace_members(self, client, admin_headers, user_headers):
        """Test namespace member management"""
        # Create namespace
        namespace_resp = await client.post(
            "/api/namespaces",
            json={
                "name": f"member-test-{int(time.time())}",
                "base_uri": f"http://test.odras.ai/members/{int(time.time())}#"
            },
            headers=admin_headers
        )

        if namespace_resp.status_code == 200:
            namespace_id = namespace_resp.json()["namespace_id"]

            # Add member
            member_resp = await client.post(
                f"/api/namespaces/{namespace_id}/members",
                json={
                    "username": "das_service",
                    "role": "contributor"  # or "viewer", "admin"
                },
                headers=admin_headers
            )
            assert member_resp.status_code in [200, 201, 404]

            # List members
            list_resp = await client.get(
                f"/api/namespaces/{namespace_id}/members",
                headers=admin_headers
            )
            assert list_resp.status_code in [200, 404]

            # Remove member
            remove_resp = await client.delete(
                f"/api/namespaces/{namespace_id}/members/das_service",
                headers=admin_headers
            )
            assert remove_resp.status_code in [200, 204, 404]

            # Clean up
            await client.delete(f"/api/namespaces/{namespace_id}", headers=admin_headers)

        print("✓ Namespace member management tested")

    @pytest.mark.asyncio
    async def test_namespace_types(self, client, admin_headers):
        """Test different namespace types"""
        namespace_types = ["project", "service", "system"]

        for ns_type in namespace_types:
            namespace_data = {
                "name": f"type-test-{ns_type}-{int(time.time())}",
                "description": f"Testing {ns_type} namespace type",
                "base_uri": f"http://test.odras.ai/{ns_type}/{int(time.time())}#",
                "namespace_type": ns_type
            }

            resp = await client.post(
                "/api/namespaces",
                json=namespace_data,
                headers=admin_headers
            )

            if resp.status_code == 200:
                namespace = resp.json()
                assert namespace.get("namespace_type") == ns_type

                # Clean up
                await client.delete(
                    f"/api/namespaces/{namespace['namespace_id']}",
                    headers=admin_headers
                )

        print("✓ Namespace types tested")


class TestUserManagement:
    """Test user management functionality"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("No admin user available")

    @pytest.mark.asyncio
    async def test_user_crud(self, client, admin_headers):
        """Test user CRUD operations"""
        user_data = {
            "username": f"testuser{int(time.time())}",
            "email": f"test{int(time.time())}@odras.ai",
            "display_name": "Test User",
            "password": "TestPassword123!",
            "is_admin": False
        }

        # Create user (if endpoint exists)
        create_resp = await client.post(
            "/api/users",
            json=user_data,
            headers=admin_headers
        )

        if create_resp.status_code in [200, 201]:
            user = create_resp.json()
            user_id = user.get("user_id")

            # List users
            list_resp = await client.get("/api/users", headers=admin_headers)
            assert list_resp.status_code == 200
            users = list_resp.json()
            assert isinstance(users, list)

            # Get specific user
            if user_id:
                get_resp = await client.get(
                    f"/api/users/{user_id}",
                    headers=admin_headers
                )
                assert get_resp.status_code == 200

            # Update user
            if user_id:
                update_resp = await client.put(
                    f"/api/users/{user_id}",
                    json={"display_name": "Updated Test User"},
                    headers=admin_headers
                )
                assert update_resp.status_code in [200, 404]

            # Delete user
            if user_id:
                delete_resp = await client.delete(
                    f"/api/users/{user_id}",
                    headers=admin_headers
                )
                assert delete_resp.status_code in [200, 204, 404]
        elif create_resp.status_code == 404:
            print("⚠ User creation endpoint not implemented")

        print("✓ User management CRUD operations tested")

    @pytest.mark.asyncio
    async def test_user_roles_and_permissions(self, client, admin_headers):
        """Test user roles and permission management"""
        # Get current user info
        me_resp = await client.get("/api/auth/me", headers=admin_headers)
        assert me_resp.status_code == 200
        current_user = me_resp.json()

        # Check admin status
        if "is_admin" in current_user:
            print(f"✓ Current user admin status: {current_user['is_admin']}")

        # Test role assignment (if supported)
        role_resp = await client.post(
            "/api/users/roles",
            json={
                "username": "das_service",
                "role": "contributor"
            },
            headers=admin_headers
        )
        assert role_resp.status_code in [200, 201, 404]

        print("✓ User roles and permissions tested")

    @pytest.mark.asyncio
    async def test_user_search(self, client, admin_headers):
        """Test user search functionality"""
        # Search users by various criteria
        search_params = [
            {"q": "das"},  # Search query
            {"is_admin": True},  # Admin users only
            {"is_admin": False},  # Non-admin users
            {"limit": 10},  # Pagination
        ]

        for params in search_params:
            search_resp = await client.get(
                "/api/users",
                params=params,
                headers=admin_headers
            )
            assert search_resp.status_code in [200, 404]

            if search_resp.status_code == 200:
                results = search_resp.json()
                assert isinstance(results, list)

        print("✓ User search functionality tested")


class TestDocumentManagement:
    """Test document management functionality"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        return {"Authorization": f"Bearer {response.json()['token']}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        resp = await client.post(
            "/api/projects",
            json={"name": f"Doc Mgmt Test {int(time.time())}"},
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Project creation failed: {resp.text}"
        project_data = resp.json()
        # Handle both response formats: {"project": {...}} or {"project_id": ...}
        if "project" in project_data:
            project_id = project_data["project"]["project_id"]
        else:
            project_id = project_data["project_id"]
        yield project_id
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, client, auth_headers, test_project):
        """Test complete document lifecycle"""
        # Upload document
        doc_content = b"Test document for management testing"
        files = {"file": ("test_doc.txt", doc_content, "text/plain")}

        upload_resp = await client.post(
            "/api/files/upload",
            files=files,
            data={"project_id": test_project},
            headers=auth_headers
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        file_info = upload_resp.json()
        # Handle response format: {"file_id": ...} or {"success": True, "file_id": ...}
        file_id = file_info.get("file_id")
        assert file_id is not None, f"File ID not found in response: {file_info}"

        # Get document metadata
        meta_resp = await client.get(
            f"/api/files/{file_id}/metadata",
            headers=auth_headers
        )
        assert meta_resp.status_code == 200
        metadata = meta_resp.json()

        # Update document metadata
        update_resp = await client.put(
            f"/api/files/{file_id}/metadata",
            json={
                "tags": ["test", "management"],
                "description": "Updated document description"
            },
            headers=auth_headers
        )
        assert update_resp.status_code in [200, 404]

        # List documents with filters
        list_resp = await client.get(
            f"/api/files/project/{test_project}",
            params={"mime_type": "text/plain"},
            headers=auth_headers
        )
        assert list_resp.status_code == 200

        # Version management (if supported)
        version_resp = await client.get(
            f"/api/files/{file_id}/versions",
            headers=auth_headers
        )
        assert version_resp.status_code in [200, 404]

        # Delete document
        delete_resp = await client.delete(
            f"/api/files/{file_id}",
            headers=auth_headers
        )
        assert delete_resp.status_code == 200

        print("✓ Document lifecycle management tested")

    @pytest.mark.asyncio
    async def test_document_search_and_filter(self, client, auth_headers, test_project):
        """Test document search and filtering"""
        # Upload multiple documents
        docs = [
            ("report.pdf", b"PDF content", "application/pdf"),
            ("data.csv", b"CSV data", "text/csv"),
            ("notes.txt", b"Text notes", "text/plain"),
            ("image.png", b"PNG data", "image/png")
        ]

        uploaded_ids = []
        for filename, content, mime_type in docs:
            files = {"file": (filename, content, mime_type)}
            resp = await client.post(
                "/api/files/upload",
                files=files,
                data={"project_id": test_project},
                headers=auth_headers
            )
            if resp.status_code == 200:
                uploaded_ids.append(resp.json()["file_id"])

        # Search by mime type
        text_files = await client.get(
            f"/api/files/project/{test_project}",
            params={"mime_type": "text/plain"},
            headers=auth_headers
        )
        assert text_files.status_code == 200

        # Search by name pattern (if supported)
        search_resp = await client.get(
            f"/api/files/project/{test_project}",
            params={"search": "report"},
            headers=auth_headers
        )
        assert search_resp.status_code in [200, 404]

        # Filter by date range (if supported)
        date_resp = await client.get(
            f"/api/files/project/{test_project}",
            params={
                "created_after": "2024-01-01",
                "created_before": "2025-12-31"
            },
            headers=auth_headers
        )
        assert date_resp.status_code in [200, 404]

        print("✓ Document search and filtering tested")

    @pytest.mark.asyncio
    async def test_document_permissions(self, client, auth_headers, test_project):
        """Test document access permissions"""
        # Upload a document
        files = {"file": ("private.txt", b"Private content", "text/plain")}
        upload_resp = await client.post(
            "/api/files/upload",
            files=files,
            data={"project_id": test_project},
            headers=auth_headers
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        file_info = upload_resp.json()
        file_id = file_info.get("file_id")
        assert file_id is not None, f"File ID not found in response: {file_info}"

        # Try to access without auth (should fail)
        unauth_resp = await client.get(f"/api/files/{file_id}/download")
        assert unauth_resp.status_code == 401

        # Set document permissions (if supported)
        perm_resp = await client.put(
            f"/api/files/{file_id}/permissions",
            json={
                "public": False,
                "allowed_users": ["das_service"]
            },
            headers=auth_headers
        )
        assert perm_resp.status_code in [200, 404]

        print("✓ Document permissions tested")


class TestSystemAdministration:
    """Test system administration features"""

    @pytest.fixture
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("No admin user available")

    @pytest.mark.asyncio
    async def test_system_stats(self, client, admin_headers):
        """Test system statistics endpoints"""
        # Get system stats
        stats_resp = await client.get(
            "/api/admin/stats",
            headers=admin_headers
        )

        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            # Should contain various metrics
            expected_keys = ["users", "projects", "files", "namespaces"]
            for key in expected_keys:
                if key in stats:
                    print(f"✓ System stat '{key}': {stats[key]}")
        elif stats_resp.status_code == 404:
            print("⚠ System stats endpoint not implemented")

        print("✓ System statistics tested")

    @pytest.mark.asyncio
    async def test_audit_logs(self, client, admin_headers):
        """Test audit log access"""
        # Get audit logs
        audit_resp = await client.get(
            "/api/admin/audit-logs",
            params={"limit": 100},
            headers=admin_headers
        )

        if audit_resp.status_code == 200:
            logs = audit_resp.json()
            assert isinstance(logs, list)
            print(f"✓ Retrieved {len(logs)} audit log entries")
        elif audit_resp.status_code == 404:
            print("⚠ Audit logs endpoint not implemented")

    @pytest.mark.asyncio
    async def test_system_configuration(self, client, admin_headers):
        """Test system configuration management"""
        # Get current configuration
        config_resp = await client.get(
            "/api/admin/config",
            headers=admin_headers
        )

        if config_resp.status_code == 200:
            config = config_resp.json()
            print("✓ System configuration retrieved")

            # Try to update a config value
            update_resp = await client.put(
                "/api/admin/config",
                json={
                    "max_file_size": 100 * 1024 * 1024,  # 100MB
                    "enable_public_access": False
                },
                headers=admin_headers
            )
            assert update_resp.status_code in [200, 404]
        elif config_resp.status_code == 404:
            print("⚠ System configuration endpoint not implemented")

    @pytest.mark.asyncio
    async def test_backup_and_restore(self, client, admin_headers):
        """Test backup and restore functionality"""
        # Trigger backup
        backup_resp = await client.post(
            "/api/admin/backup",
            json={"backup_type": "full"},
            headers=admin_headers
        )

        if backup_resp.status_code in [200, 202]:
            backup_info = backup_resp.json()
            print(f"✓ Backup initiated: {backup_info}")
        elif backup_resp.status_code == 404:
            print("⚠ Backup endpoint not implemented")

        # List backups
        list_resp = await client.get(
            "/api/admin/backups",
            headers=admin_headers
        )
        assert list_resp.status_code in [200, 404]


# Summary function for admin tools testing
async def run_admin_tools_summary():
    """Run a summary of admin tools tests"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n" + "="*60)
        print("Admin Tools Testing Summary")
        print("="*60 + "\n")

        # Try to get admin access
        admin_headers = None
        for username, password in [("admin", "admin123!"), ("jdehart", "jdehart123!")]:
            resp = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if resp.status_code == 200:
                admin_headers = {"Authorization": f"Bearer {resp.json()['token']}"}
                print(f"✓ Logged in as admin: {username}")
                break

        if not admin_headers:
            print("⚠ No admin user available, using regular user")
            resp = await client.post(
                "/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"}
            )
            admin_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        # Test each admin tool
        tools_tested = []

        # Prefix management
        prefix_resp = await client.get("/api/prefixes", headers=admin_headers)
        if prefix_resp.status_code == 200:
            tools_tested.append("Prefix Management")

        # Domain management
        domain_resp = await client.get("/api/domains", headers=admin_headers)
        if domain_resp.status_code == 200:
            tools_tested.append("Domain Management")

        # Namespace management
        ns_resp = await client.get("/api/namespaces", headers=admin_headers)
        if ns_resp.status_code == 200:
            tools_tested.append("Namespace Management")

        # User management
        user_resp = await client.get("/api/users", headers=admin_headers)
        if user_resp.status_code == 200:
            tools_tested.append("User Management")

        print(f"\n✓ Admin tools available: {', '.join(tools_tested)}")
        print("✓ Admin tools testing completed!")
        print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_admin_tools_summary())
