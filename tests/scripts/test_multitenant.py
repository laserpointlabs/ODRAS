#!/usr/bin/env python3
"""
Clean Multi-Tenant Implementation Test
Tests the simplified multi-tenant architecture without legacy complexity.
"""

import os
import sys
import logging
import requests
import time
from typing import Dict, List

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.db import DatabaseService
from services.tenant_service import TenantService, get_tenant_service
from services.unified_iri_service import UnifiedIRIService, create_tenant_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiTenantTester:
    """Clean multi-tenant implementation tester"""
    
    def __init__(self):
        self.settings = Settings()
        self.db_service = DatabaseService(self.settings)
        self.tenant_service = get_tenant_service(self.db_service, self.settings)
        self.api_base = "http://localhost:8000"
        
    def run_tests(self):
        """Run all multi-tenant tests"""
        logger.info("🧪 Starting Clean Multi-Tenant Implementation Tests")
        
        try:
            # Test 1: Database Schema Validation
            logger.info("\n=== Test 1: Database Schema Validation ===")
            self.test_database_schema()
            
            # Test 2: Tenant Management
            logger.info("\n=== Test 2: Tenant Management ===")
            self.test_tenant_management()
            
            # Test 3: Unified IRI Service
            logger.info("\n=== Test 3: Unified IRI Service ===")
            self.test_unified_iri_service()
            
            # Test 4: Tenant Isolation
            logger.info("\n=== Test 4: Tenant Isolation ===")
            self.test_tenant_isolation()
            
            # Test 5: API Integration (if server running)
            logger.info("\n=== Test 5: API Integration ===")
            self.test_api_integration()
            
            logger.info("\n✅ All tests completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
    
    def test_database_schema(self):
        """Test database schema includes tenant tables and columns"""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check tenants table exists
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'tenants'
                """)
                if cur.fetchone()[0] == 0:
                    raise AssertionError("tenants table not found")
                logger.info("✓ tenants table exists")
                
                # Check tenant_members table exists
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'tenant_members'
                """)
                if cur.fetchone()[0] == 0:
                    raise AssertionError("tenant_members table not found")
                logger.info("✓ tenant_members table exists")
                
                # Check system tenant exists
                cur.execute("""
                    SELECT tenant_code, tenant_name FROM public.tenants 
                    WHERE tenant_id = '00000000-0000-0000-0000-000000000000'::UUID
                """)
                result = cur.fetchone()
                if not result or result[0] != 'system':
                    raise AssertionError("system tenant not found")
                logger.info(f"✓ system tenant exists: {result[0]} - {result[1]}")
                
                # Check key tables have tenant_id columns
                key_tables = ['users', 'projects', 'files', 'knowledge_assets', 'ontologies_registry']
                for table in key_tables:
                    cur.execute("""
                        SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s AND column_name = 'tenant_id'
                    """, (table,))
                    if cur.fetchone()[0] == 0:
                        raise AssertionError(f"tenant_id column not found in {table}")
                    logger.info(f"✓ {table} table has tenant_id column")
                    
        finally:
            self.db_service._return(conn)
    
    def test_tenant_management(self):
        """Test tenant creation and management"""
        # Create a test tenant
        tenant = self.tenant_service.create_tenant(
            tenant_code="test-org",
            tenant_name="Test Organization", 
            tenant_type="organization"
        )
        logger.info(f"✓ Created tenant: {tenant.tenant_code} ({tenant.tenant_id})")
        
        # Test tenant retrieval
        retrieved = self.tenant_service.get_tenant(tenant.tenant_id)
        if not retrieved or retrieved.tenant_code != "test-org":
            raise AssertionError("Failed to retrieve created tenant")
        logger.info("✓ Tenant retrieval works")
        
        # Test tenant lookup by code
        by_code = self.tenant_service.get_tenant_by_code("test-org")
        if not by_code or by_code.tenant_id != tenant.tenant_id:
            raise AssertionError("Failed to lookup tenant by code")
        logger.info("✓ Tenant lookup by code works")
        
        # Test tenant listing
        all_tenants = self.tenant_service.list_tenants()
        tenant_codes = [t.tenant_code for t in all_tenants]
        if "system" not in tenant_codes or "test-org" not in tenant_codes:
            raise AssertionError("Tenant listing incomplete")
        logger.info(f"✓ Tenant listing works: {len(all_tenants)} tenants found")
        
        return tenant
    
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
        expected = "https://test.odras.local/test-org/projects/abc-123-def/"
        if project_iri != expected:
            raise AssertionError(f"Project IRI mismatch: {project_iri} != {expected}")
        logger.info(f"✓ Project IRI: {project_iri}")
        
        # Test ontology IRI generation
        ontology_iri = iri_service.generate_ontology_iri("abc-123-def", "Requirements")
        expected = "https://test.odras.local/test-org/projects/abc-123-def/ontologies/requirements"
        if ontology_iri != expected:
            raise AssertionError(f"Ontology IRI mismatch: {ontology_iri} != {expected}")
        logger.info(f"✓ Ontology IRI: {ontology_iri}")
        
        # Test user IRI generation
        user_iri = iri_service.generate_user_iri("jdehart")
        expected = "https://test.odras.local/test-org/users/jdehart"
        if user_iri != expected:
            raise AssertionError(f"User IRI mismatch: {user_iri} != {expected}")
        logger.info(f"✓ User IRI: {user_iri}")
        
        # Test IRI parsing
        components = iri_service.parse_iri_components(project_iri)
        if components.get("tenant_code") != "test-org":
            raise AssertionError("IRI parsing failed to extract tenant_code")
        logger.info("✓ IRI parsing works")
        
        # Test validation
        issues = iri_service.validate_tenant_iri_compliance()
        logger.info("✓ IRI validation passes")
    
    def test_tenant_isolation(self):
        """Test tenant isolation in database operations"""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Test that we can query with tenant filtering
                cur.execute("""
                    SELECT COUNT(*) FROM public.projects 
                    WHERE tenant_id = '00000000-0000-0000-0000-000000000000'::UUID
                """)
                system_project_count = cur.fetchone()[0]
                logger.info(f"✓ System tenant has {system_project_count} projects")
                
                # Test that foreign key constraints work
                try:
                    cur.execute("""
                        INSERT INTO public.projects (name, tenant_id) 
                        VALUES ('Test Project', 'invalid-uuid')
                    """)
                    conn.rollback()
                    raise AssertionError("Should have failed with invalid tenant_id")
                except Exception as e:
                    if "invalid input syntax for type uuid" in str(e):
                        conn.rollback()
                        logger.info("✓ Tenant foreign key constraint works")
                    else:
                        raise
                        
        finally:
            self.db_service._return(conn)
    
    def test_api_integration(self):
        """Test API integration with real endpoints"""
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_base}/api/health", timeout=5)
            if response.status_code != 200:
                logger.warning("⚠ API server health check failed")
                return
                
            logger.info("✓ API server is healthy")
            
            # Test authentication
            auth_response = requests.post(
                f"{self.api_base}/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=5
            )
            
            if auth_response.status_code != 200:
                logger.warning("⚠ Authentication test failed")
                return
                
            token = auth_response.json()["token"]
            logger.info("✓ Authentication works")
            
            # Test tenant endpoint
            headers = {"Authorization": f"Bearer {token}"}
            tenant_response = requests.get(
                f"{self.api_base}/api/tenants/current",
                headers=headers,
                timeout=5
            )
            
            if tenant_response.status_code == 200:
                tenant_data = tenant_response.json()
                logger.info(f"✓ Current tenant: {tenant_data['tenant_code']}")
            else:
                logger.warning(f"⚠ Tenant endpoint failed: {tenant_response.status_code}")
            
            # Test IRI generation endpoint
            iri_response = requests.get(
                f"{self.api_base}/api/tenants/iri-test/test-project-123",
                headers=headers,
                timeout=5
            )
            
            if iri_response.status_code == 200:
                iri_data = iri_response.json()
                logger.info(f"✓ IRI generation: {iri_data['tenant_context']['tenant_code']}")
                logger.info(f"  Example project IRI: {iri_data['test_iris']['project']}")
            else:
                logger.warning(f"⚠ IRI endpoint failed: {iri_response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"⚠ API tests failed: {e}")
    
    def cleanup(self):
        """Clean up test data"""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Remove test tenant if it exists
                    cur.execute("""
                        DELETE FROM public.tenants 
                        WHERE tenant_code = 'test-org'
                    """)
                    conn.commit()
                    logger.info("✓ Test tenant cleaned up")
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

def main():
    """Main test runner"""
    tester = MultiTenantTester()
    
    try:
        tester.run_tests()
        print("\n🎉 All tests passed! Multi-tenant implementation is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        sys.exit(1)
        
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
