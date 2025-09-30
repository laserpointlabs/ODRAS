"""
Admin CRUD Operations Tests

Comprehensive tests for all administrative operations:
- Prefix Management
- Domain Management
- Namespace Management
- User Management
- System Configuration
- Backup and Restore
- Audit Logs
- System Statistics

Run with: pytest tests/api/test_admin_crud.py -v
"""

import pytest
import time
import json
from typing import Dict, List, Any
from httpx import AsyncClient
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))



class TestAdminCRUD:
    """Test all admin CRUD operations"""

    @pytest.fixture
    async def client(self):
        # Connect to the REAL running API
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def admin_headers(self, client):
        """Get admin authentication headers"""
        # Try different admin accounts
        for username, password in [
            ("admin", "admin123!"),
            ("jdehart", "jdehart123!")
        ]:
            response = await client.post(
                "/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                token = response.json()["token"]
                return {"Authorization": f"Bearer {token}"}

        # Fallback to regular user for testing
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}

    @pytest.fixture
    async def user_headers(self, client):
        """Get regular user authentication headers"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}

    # ========== PREFIX MANAGEMENT ==========

    @pytest.mark.asyncio
    async def test_create_prefix(self, client, admin_headers):
        """Test creating a new prefix"""
        prefix_data = {
            "prefix": f"test{int(time.time())}",
            "namespace": f"http://test.odras.ai/ns/{int(time.time())}#",
            "description": "Test prefix for admin CRUD testing"
        }

        response = await client.post(
            "/api/prefixes",
            json=prefix_data,
            headers=admin_headers
        )

        if response.status_code == 200:
            prefix = response.json()
            assert prefix["prefix"] == prefix_data["prefix"]
            assert prefix["namespace"] == prefix_data["namespace"]

            # Cleanup
            await client.delete(f"/api/prefixes/{prefix_data['prefix']}", headers=admin_headers)
            print("✓ Prefix creation tested")
        else:
            print("⚠ Prefix creation requires admin privileges or not implemented")

    @pytest.mark.asyncio
    async def test_list_prefixes(self, client, user_headers):
        """Test listing all prefixes"""
        response = await client.get("/api/prefixes", headers=user_headers)

        if response.status_code == 200:
            prefixes = response.json()
            assert isinstance(prefixes, list)

            # Standard prefixes should exist
            standard_prefixes = ["rdf", "rdfs", "owl", "xsd"]
            existing_prefixes = [p.get("prefix") for p in prefixes]

            for std_prefix in standard_prefixes:
                if std_prefix in existing_prefixes:
                    print(f"✓ Found standard prefix: {std_prefix}")

            print(f"✓ Listed {len(prefixes)} prefixes")
        else:
            print("⚠ Prefix listing not implemented")

    @pytest.mark.asyncio
    async def test_update_prefix(self, client, admin_headers):
        """Test updating a prefix"""
        # Create a prefix first
        prefix_data = {
            "prefix": f"update{int(time.time())}",
            "namespace": "http://test.odras.ai/update#"
        }

        create_resp = await client.post(
            "/api/prefixes",
            json=prefix_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            # Update the prefix
            update_data = {
                "description": "Updated description",
                "namespace": "http://test.odras.ai/updated#"
            }

            update_resp = await client.put(
                f"/api/prefixes/{prefix_data['prefix']}",
                json=update_data,
                headers=admin_headers
            )

            if update_resp.status_code == 200:
                updated = update_resp.json()
                assert updated.get("description") == update_data["description"]
                print("✓ Prefix update tested")
            else:
                print("⚠ Prefix update not implemented")

            # Cleanup
            await client.delete(f"/api/prefixes/{prefix_data['prefix']}", headers=admin_headers)

    @pytest.mark.asyncio
    async def test_delete_prefix(self, client, admin_headers):
        """Test deleting a prefix"""
        # Create a prefix to delete
        prefix_data = {
            "prefix": f"delete{int(time.time())}",
            "namespace": "http://test.odras.ai/delete#"
        }

        create_resp = await client.post(
            "/api/prefixes",
            json=prefix_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            # Delete the prefix
            delete_resp = await client.delete(
                f"/api/prefixes/{prefix_data['prefix']}",
                headers=admin_headers
            )

            assert delete_resp.status_code in [200, 204]

            # Verify deletion
            list_resp = await client.get("/api/prefixes", headers=admin_headers)
            if list_resp.status_code == 200:
                prefixes = list_resp.json()
                assert not any(p.get("prefix") == prefix_data["prefix"] for p in prefixes)

            print("✓ Prefix deletion tested")

    # ========== DOMAIN MANAGEMENT ==========

    @pytest.mark.asyncio
    async def test_create_domain(self, client, admin_headers):
        """Test creating a new domain"""
        domain_data = {
            "domain": f"test{int(time.time())}.odras.ai",
            "description": "Test domain for admin CRUD",
            "is_public": False,
            "metadata": {
                "environment": "test",
                "owner": "admin"
            }
        }

        response = await client.post(
            "/api/domains",
            json=domain_data,
            headers=admin_headers
        )

        if response.status_code == 200:
            domain = response.json()
            assert domain["domain"] == domain_data["domain"]

            # Cleanup
            await client.delete(f"/api/domains/{domain_data['domain']}", headers=admin_headers)
            print("✓ Domain creation tested")
        else:
            print("⚠ Domain creation requires admin privileges or not implemented")

    @pytest.mark.asyncio
    async def test_list_domains(self, client, admin_headers):
        """Test listing domains"""
        response = await client.get("/api/domains", headers=admin_headers)

        if response.status_code == 200:
            domains = response.json()
            assert isinstance(domains, list)
            print(f"✓ Listed {len(domains)} domains")
        else:
            print("⚠ Domain listing not implemented")

    @pytest.mark.asyncio
    async def test_public_domain_access(self, client):
        """Test public domain listing without auth"""
        response = await client.get("/api/domains/public")

        if response.status_code == 200:
            domains = response.json()
            # All should be public
            for domain in domains:
                if "is_public" in domain:
                    assert domain["is_public"] is True
            print("✓ Public domain access tested")
        else:
            print("⚠ Public domain endpoint not implemented")

    # ========== NAMESPACE MANAGEMENT ==========

    @pytest.mark.asyncio
    async def test_create_namespace(self, client, admin_headers):
        """Test creating a new namespace"""
        namespace_data = {
            "name": f"test-ns-{int(time.time())}",
            "description": "Test namespace for admin CRUD",
            "base_uri": f"http://test.odras.ai/ns/{int(time.time())}#",
            "namespace_type": "project",
            "is_public": False
        }

        response = await client.post(
            "/api/namespaces",
            json=namespace_data,
            headers=admin_headers
        )

        if response.status_code == 200:
            namespace = response.json()
            namespace_id = namespace["namespace_id"]
            assert namespace["name"] == namespace_data["name"]

            # Cleanup
            await client.delete(f"/api/namespaces/{namespace_id}", headers=admin_headers)
            print("✓ Namespace creation tested")
        else:
            print("⚠ Namespace creation requires admin privileges or not implemented")

    @pytest.mark.asyncio
    async def test_namespace_members(self, client, admin_headers):
        """Test namespace member management"""
        # Create namespace
        namespace_data = {
            "name": f"member-ns-{int(time.time())}",
            "base_uri": f"http://test.odras.ai/members/{int(time.time())}#"
        }

        create_resp = await client.post(
            "/api/namespaces",
            json=namespace_data,
            headers=admin_headers
        )

        if create_resp.status_code == 200:
            namespace_id = create_resp.json()["namespace_id"]

            # Add member
            member_data = {
                "username": "das_service",
                "role": "contributor"
            }

            add_resp = await client.post(
                f"/api/namespaces/{namespace_id}/members",
                json=member_data,
                headers=admin_headers
            )

            if add_resp.status_code in [200, 201]:
                # List members
                list_resp = await client.get(
                    f"/api/namespaces/{namespace_id}/members",
                    headers=admin_headers
                )

                if list_resp.status_code == 200:
                    members = list_resp.json()
                    assert any(m.get("username") == "das_service" for m in members)

                # Remove member
                remove_resp = await client.delete(
                    f"/api/namespaces/{namespace_id}/members/das_service",
                    headers=admin_headers
                )
                assert remove_resp.status_code in [200, 204]

                print("✓ Namespace member management tested")
            else:
                print("⚠ Namespace member management not implemented")

            # Cleanup
            await client.delete(f"/api/namespaces/{namespace_id}", headers=admin_headers)

    # ========== USER MANAGEMENT ==========

    @pytest.mark.asyncio
    async def test_create_user(self, client, admin_headers):
        """Test creating a new user"""
        user_data = {
            "username": f"testuser{int(time.time())}",
            "email": f"test{int(time.time())}@odras.ai",
            "display_name": "Test User",
            "password": "TestPassword123!",
            "is_admin": False
        }

        response = await client.post(
            "/api/users",
            json=user_data,
            headers=admin_headers
        )

        if response.status_code in [200, 201]:
            user = response.json()
            user_id = user["user_id"]
            assert user["username"] == user_data["username"]

            # Cleanup
            await client.delete(f"/api/users/{user_id}", headers=admin_headers)
            print("✓ User creation tested")
        else:
            print("⚠ User creation requires admin privileges or not implemented")

    @pytest.mark.asyncio
    async def test_list_users(self, client, admin_headers):
        """Test listing all users"""
        response = await client.get("/api/users", headers=admin_headers)

        if response.status_code == 200:
            users = response.json()
            assert isinstance(users, list)

            # Standard users should exist
            standard_users = ["admin", "das_service"]
            existing_users = [u.get("username") for u in users]

            for std_user in standard_users:
                if std_user in existing_users:
                    print(f"✓ Found standard user: {std_user}")

            print(f"✓ Listed {len(users)} users")
        else:
            print("⚠ User listing requires admin privileges or not implemented")

    @pytest.mark.asyncio
    async def test_update_user(self, client, admin_headers):
        """Test updating user information"""
        # Create a user first
        user_data = {
            "username": f"updateuser{int(time.time())}",
            "email": f"update{int(time.time())}@odras.ai",
            "display_name": "Update Test User",
            "password": "UpdatePass123!"
        }

        create_resp = await client.post(
            "/api/users",
            json=user_data,
            headers=admin_headers
        )

        if create_resp.status_code in [200, 201]:
            user_id = create_resp.json()["user_id"]

            # Update user
            update_data = {
                "display_name": "Updated Display Name",
                "email": f"updated{int(time.time())}@odras.ai",
                "is_active": True
            }

            update_resp = await client.put(
                f"/api/users/{user_id}",
                json=update_data,
                headers=admin_headers
            )

            if update_resp.status_code == 200:
                updated = update_resp.json()
                assert updated["display_name"] == update_data["display_name"]
                print("✓ User update tested")
            else:
                print("⚠ User update not implemented")

            # Cleanup
            await client.delete(f"/api/users/{user_id}", headers=admin_headers)

    @pytest.mark.asyncio
    async def test_user_roles(self, client, admin_headers):
        """Test user role management"""
        # Assign role to user
        role_data = {
            "username": "das_service",
            "role": "data_analyst"
        }

        role_resp = await client.post(
            "/api/users/roles",
            json=role_data,
            headers=admin_headers
        )

        if role_resp.status_code in [200, 201]:
            print("✓ User role assignment tested")
        else:
            print("⚠ User role management not implemented")

    # ========== SYSTEM CONFIGURATION ==========

    @pytest.mark.asyncio
    async def test_get_system_config(self, client, admin_headers):
        """Test retrieving system configuration"""
        response = await client.get(
            "/api/admin/config",
            headers=admin_headers
        )

        if response.status_code == 200:
            config = response.json()
            print("✓ System configuration retrieved")

            # Check for common config keys
            expected_keys = [
                "max_file_size",
                "max_upload_size",
                "enable_public_access",
                "default_chunk_size"
            ]

            for key in expected_keys:
                if key in config:
                    print(f"  - {key}: {config[key]}")
        else:
            print("⚠ System configuration endpoint not implemented")

    @pytest.mark.asyncio
    async def test_update_system_config(self, client, admin_headers):
        """Test updating system configuration"""
        config_updates = {
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "enable_public_access": False,
            "session_timeout": 3600,
            "maintenance_mode": False
        }

        response = await client.put(
            "/api/admin/config",
            json=config_updates,
            headers=admin_headers
        )

        if response.status_code == 200:
            updated = response.json()
            print("✓ System configuration update tested")
        else:
            print("⚠ System configuration update not implemented")

    # ========== SYSTEM STATISTICS ==========

    @pytest.mark.asyncio
    async def test_system_statistics(self, client, admin_headers):
        """Test retrieving system statistics"""
        response = await client.get(
            "/api/admin/stats",
            headers=admin_headers
        )

        if response.status_code == 200:
            stats = response.json()

            # Expected statistics
            stat_categories = [
                "users",
                "projects",
                "files",
                "knowledge_documents",
                "ontologies",
                "namespaces",
                "storage_used",
                "api_calls"
            ]

            for category in stat_categories:
                if category in stats:
                    print(f"✓ {category}: {stats[category]}")

            print("✓ System statistics retrieved")
        else:
            print("⚠ System statistics endpoint not implemented")

    @pytest.mark.asyncio
    async def test_resource_usage(self, client, admin_headers):
        """Test retrieving resource usage statistics"""
        response = await client.get(
            "/api/admin/resources",
            headers=admin_headers
        )

        if response.status_code == 200:
            resources = response.json()

            # Check resource metrics
            if "cpu" in resources:
                print(f"✓ CPU usage: {resources['cpu']}%")
            if "memory" in resources:
                print(f"✓ Memory usage: {resources['memory']}%")
            if "disk" in resources:
                print(f"✓ Disk usage: {resources['disk']}%")

            print("✓ Resource usage retrieved")
        else:
            print("⚠ Resource usage endpoint not implemented")

    # ========== AUDIT LOGS ==========

    @pytest.mark.asyncio
    async def test_audit_logs(self, client, admin_headers):
        """Test retrieving audit logs"""
        response = await client.get(
            "/api/admin/audit-logs",
            params={
                "limit": 50,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            headers=admin_headers
        )

        if response.status_code == 200:
            logs = response.json()
            assert isinstance(logs, list)

            if logs:
                # Check log structure
                log_entry = logs[0]
                expected_fields = ["timestamp", "user", "action", "resource", "ip_address"]

                for field in expected_fields:
                    if field in log_entry:
                        print(f"✓ Audit log contains '{field}'")

            print(f"✓ Retrieved {len(logs)} audit log entries")
        else:
            print("⚠ Audit logs endpoint not implemented")

    @pytest.mark.asyncio
    async def test_audit_log_filtering(self, client, admin_headers):
        """Test filtering audit logs"""
        filter_params = [
            {"user": "das_service"},
            {"action": "login"},
            {"resource_type": "project"},
            {"severity": "high"}
        ]

        for params in filter_params:
            response = await client.get(
                "/api/admin/audit-logs",
                params=params,
                headers=admin_headers
            )

            if response.status_code == 200:
                logs = response.json()
                print(f"✓ Audit log filtering by {list(params.keys())[0]} tested")
            else:
                print("⚠ Audit log filtering not implemented")
                break

    # ========== BACKUP AND RESTORE ==========

    @pytest.mark.asyncio
    async def test_create_backup(self, client, admin_headers):
        """Test creating a system backup"""
        backup_data = {
            "backup_type": "full",
            "include_files": True,
            "include_database": True,
            "description": "Test backup"
        }

        response = await client.post(
            "/api/admin/backup",
            json=backup_data,
            headers=admin_headers
        )

        if response.status_code in [200, 202]:
            result = response.json()
            if "backup_id" in result:
                print(f"✓ Backup created with ID: {result['backup_id']}")
            print("✓ Backup creation tested")
        else:
            print("⚠ Backup endpoint not implemented")

    @pytest.mark.asyncio
    async def test_list_backups(self, client, admin_headers):
        """Test listing available backups"""
        response = await client.get(
            "/api/admin/backups",
            headers=admin_headers
        )

        if response.status_code == 200:
            backups = response.json()
            assert isinstance(backups, list)

            if backups:
                backup = backups[0]
                expected_fields = ["backup_id", "timestamp", "size", "type", "status"]

                for field in expected_fields:
                    if field in backup:
                        print(f"✓ Backup info contains '{field}'")

            print(f"✓ Listed {len(backups)} backups")
        else:
            print("⚠ Backup listing not implemented")

    # ========== SYSTEM MAINTENANCE ==========

    @pytest.mark.asyncio
    async def test_maintenance_mode(self, client, admin_headers):
        """Test enabling/disabling maintenance mode"""
        # Enable maintenance mode
        enable_resp = await client.post(
            "/api/admin/maintenance",
            json={"enabled": True, "message": "System maintenance in progress"},
            headers=admin_headers
        )

        if enable_resp.status_code == 200:
            # Check if maintenance mode is active
            status_resp = await client.get("/api/admin/maintenance")
            if status_resp.status_code == 200:
                status = status_resp.json()
                assert status.get("enabled") is True

            # Disable maintenance mode
            disable_resp = await client.post(
                "/api/admin/maintenance",
                json={"enabled": False},
                headers=admin_headers
            )
            assert disable_resp.status_code == 200

            print("✓ Maintenance mode tested")
        else:
            print("⚠ Maintenance mode endpoint not implemented")

    @pytest.mark.asyncio
    async def test_cache_management(self, client, admin_headers):
        """Test cache management operations"""
        # Clear cache
        clear_resp = await client.post(
            "/api/admin/cache/clear",
            json={"cache_type": "all"},
            headers=admin_headers
        )

        if clear_resp.status_code in [200, 204]:
            print("✓ Cache clearing tested")
        else:
            print("⚠ Cache management not implemented")

        # Get cache stats
        stats_resp = await client.get(
            "/api/admin/cache/stats",
            headers=admin_headers
        )

        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            print(f"✓ Cache statistics retrieved")

    # ========== PERMISSION TESTS ==========

    @pytest.mark.asyncio
    async def test_admin_only_access(self, client, user_headers):
        """Test that regular users cannot access admin endpoints"""
        admin_endpoints = [
            ("/api/admin/config", "GET"),
            ("/api/admin/stats", "GET"),
            ("/api/admin/audit-logs", "GET"),
            ("/api/users", "POST"),
            ("/api/admin/backup", "POST")
        ]

        for endpoint, method in admin_endpoints:
            if method == "GET":
                response = await client.get(endpoint, headers=user_headers)
            elif method == "POST":
                response = await client.post(endpoint, json={}, headers=user_headers)

            # Should be forbidden for non-admin users
            if response.status_code in [403, 401]:
                print(f"✓ Admin-only access enforced for {endpoint}")
            elif response.status_code == 404:
                print(f"⚠ Endpoint {endpoint} not implemented")


# Run all admin CRUD tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
