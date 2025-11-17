"""
Multi-Tenant Architecture CI Test
Validates multi-tenant functionality for CI/CD pipeline.
"""

import os
import sys
import pytest
import logging
import requests
from typing import Dict

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.db import DatabaseService
from services.tenant_service import TenantService, get_tenant_service
from services.unified_iri_service import UnifiedIRIService, create_tenant_context

logger = logging.getLogger(__name__)

@pytest.fixture
def db_service():
    """Database service fixture"""
    settings = Settings()
    return DatabaseService(settings)

@pytest.fixture
def tenant_service(db_service):
    """Tenant service fixture"""
    settings = Settings()
    return get_tenant_service(db_service, settings)

class TestMultiTenantArchitecture:
    """Multi-tenant architecture test suite for CI"""
    
    def test_database_schema_exists(self, db_service):
        """Test that multi-tenant database schema exists"""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check tenants table exists
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'tenants'
                """)
                assert cur.fetchone()[0] == 1, "tenants table not found"
                
                # Check tenant_members table exists
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'tenant_members'
                """)
                assert cur.fetchone()[0] == 1, "tenant_members table not found"
                
                # Check system tenant exists
                cur.execute("""
                    SELECT tenant_code FROM public.tenants 
                    WHERE tenant_id = '00000000-0000-0000-0000-000000000000'::UUID
                """)
                result = cur.fetchone()
                assert result and result[0] == 'system', "system tenant not found"
                
        finally:
            db_service._return(conn)
    
    def test_tenant_id_columns(self, db_service):
        """Test that key tables have tenant_id columns"""
        key_tables = ['users', 'projects', 'files', 'knowledge_assets', 'ontologies_registry']
        
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                for table in key_tables:
                    cur.execute("""
                        SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s AND column_name = 'tenant_id'
                    """, (table,))
                    assert cur.fetchone()[0] == 1, f"tenant_id column not found in {table}"
                    
        finally:
            db_service._return(conn)
    
    def test_unified_iri_service(self):
        """Test unified IRI service functionality"""
        # Create test tenant context
        tenant_context = create_tenant_context(
            tenant_id="test-tenant-id",
            tenant_code="test-org",
            tenant_name="Test Organization",
            base_iri="https://test.odras.local/test-org"
        )
        
        # Create IRI service
        iri_service = UnifiedIRIService(tenant_context)
        
        # Test project IRI generation
        project_iri = iri_service.generate_project_iri("abc-123-def")
        assert project_iri == "https://test.odras.local/test-org/projects/abc-123-def/"
        
        # Test ontology IRI generation
        ontology_iri = iri_service.generate_ontology_iri("abc-123-def", "Requirements")
        assert ontology_iri == "https://test.odras.local/test-org/projects/abc-123-def/ontologies/requirements"
        
        # Test user IRI generation
        user_iri = iri_service.generate_user_iri("jdehart")
        assert user_iri == "https://test.odras.local/test-org/users/jdehart"
        
        # Test IRI parsing
        components = iri_service.parse_iri_components(project_iri)
        assert components.get("tenant_code") == "test-org"
        
        # Test validation
        issues = iri_service.validate_tenant_iri_compliance()
        # Should pass validation for properly formatted IRIs
        
    def test_tenant_management(self, tenant_service):
        """Test tenant management operations"""
        # Test creating a tenant
        tenant = tenant_service.create_tenant(
            tenant_code="ci-test",
            tenant_name="CI Test Tenant",
            tenant_type="testing"
        )
        
        assert tenant.tenant_code == "ci-test"
        assert tenant.tenant_name == "CI Test Tenant"
        assert tenant.status == "active"
        
        # Test tenant retrieval
        retrieved = tenant_service.get_tenant(tenant.tenant_id)
        assert retrieved is not None
        assert retrieved.tenant_code == "ci-test"
        
        # Test tenant lookup by code
        by_code = tenant_service.get_tenant_by_code("ci-test")
        assert by_code is not None
        assert by_code.tenant_id == tenant.tenant_id
        
        # Test tenant listing
        all_tenants = tenant_service.list_tenants()
        tenant_codes = [t.tenant_code for t in all_tenants]
        assert "system" in tenant_codes
        assert "ci-test" in tenant_codes
        
        # Cleanup
        try:
            conn = tenant_service.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM public.tenants WHERE tenant_code = 'ci-test'")
                    conn.commit()
            finally:
                tenant_service.db_service._return(conn)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def test_tenant_isolation_constraints(self, db_service):
        """Test tenant isolation database constraints"""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Test that we can query with tenant filtering
                cur.execute("""
                    SELECT COUNT(*) FROM public.projects 
                    WHERE tenant_id = '00000000-0000-0000-0000-000000000000'::UUID
                """)
                system_project_count = cur.fetchone()[0]
                # Should not raise error (count can be 0, that's fine)
                
                # Test that invalid tenant_id fails
                with pytest.raises(Exception):
                    cur.execute("""
                        INSERT INTO public.projects (name, tenant_id) 
                        VALUES ('Test Project', 'invalid-uuid')
                    """)
                    conn.commit()  # This should fail
                
                conn.rollback()  # Reset transaction
                
        finally:
            db_service._return(conn)


@pytest.mark.integration
class TestMultiTenantAPIIntegration:
    """Integration tests for multi-tenant API endpoints"""
    
    def test_api_health_check(self):
        """Test API is responding"""
        try:
            response = requests.get("http://localhost:8000/api/health", timeout=5)
            assert response.status_code == 200
            health_data = response.json()
            assert "status" in health_data
            assert health_data["status"] == "healthy"
        except requests.RequestException:
            pytest.skip("API server not running - skipping integration tests")
    
    def test_tenant_authentication_flow(self):
        """Test authentication and tenant context"""
        try:
            # Test authentication
            auth_response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=5
            )
            assert auth_response.status_code == 200
            
            token = auth_response.json()["token"]
            assert token
            
            # Test current tenant endpoint
            headers = {"Authorization": f"Bearer {token}"}
            tenant_response = requests.get(
                "http://localhost:8000/api/tenants/current",
                headers=headers,
                timeout=5
            )
            assert tenant_response.status_code == 200
            
            tenant_data = tenant_response.json()
            assert tenant_data["tenant_code"] == "system"
            assert tenant_data["status"] == "active"
            
            # Test IRI generation endpoint
            iri_response = requests.get(
                "http://localhost:8000/api/tenants/iri-test/test-project-ci",
                headers=headers,
                timeout=5
            )
            assert iri_response.status_code == 200
            
            iri_data = iri_response.json()
            assert iri_data["tenant_context"]["tenant_code"] == "system"
            assert "test_iris" in iri_data
            assert "project" in iri_data["test_iris"]
            
        except requests.RequestException:
            pytest.skip("API server not running - skipping integration tests")
    
    def test_admin_tenant_operations(self):
        """Test admin-level tenant operations"""
        try:
            # Login as admin
            auth_response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": "admin", "password": "admin123!"},
                timeout=5
            )
            assert auth_response.status_code == 200
            
            admin_token = auth_response.json()["token"]
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Test tenant listing
            list_response = requests.get(
                "http://localhost:8000/api/tenants/",
                headers=headers,
                timeout=5
            )
            assert list_response.status_code == 200
            
            tenants = list_response.json()
            assert isinstance(tenants, list)
            assert len(tenants) >= 1  # At least system tenant
            
            # Find system tenant
            system_tenant = next((t for t in tenants if t["tenant_code"] == "system"), None)
            assert system_tenant is not None
            assert system_tenant["tenant_name"] == "System Resources"
            
        except requests.RequestException:
            pytest.skip("API server not running - skipping integration tests")
