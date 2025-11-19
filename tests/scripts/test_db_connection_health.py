#!/usr/bin/env python3
"""
Database Connection Health Test

Tests connection pool behavior, detects leaks, and validates proper cleanup.
Designed to catch connection pool issues that cause CI failures.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to Python path
# tests/scripts/test_db_connection_health.py -> tests/scripts/ -> tests/ -> project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.config import Settings
from backend.services.db import DatabaseService


class ConnectionHealthTester:
    """Test database connection health and pool behavior."""
    
    def __init__(self):
        self.settings = Settings()
        
    def test_basic_connection(self):
        """Test basic connection acquisition and return."""
        print("🔍 Testing basic connection...")
        
        db_service = DatabaseService(self.settings)
        conn = db_service._conn()
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result[0] == 1
        finally:
            db_service._return(conn)
            
        print("✓ Basic connection test passed")
        return True  # Explicitly return True for consistency
        
    def test_connection_pool_stress(self):
        """Test connection pool under stress to detect leaks."""
        print("🔍 Testing connection pool stress...")
        
        db_service = DatabaseService(self.settings)
        
        # Get initial pool status
        initial_status = db_service.get_pool_status()
        print(f"📊 Initial pool status: {initial_status}")
        
        # Test multiple rapid connections
        connections = []
        try:
            for i in range(15):  # Less than pool max but enough to test
                conn = db_service._conn()
                connections.append(conn)
                
                with conn.cursor() as cur:
                    cur.execute("SELECT %s", (i,))
                    cur.fetchone()
                    
        finally:
            # Return all connections
            for conn in connections:
                try:
                    db_service._return(conn)
                except Exception as e:
                    print(f"⚠️ Error returning connection: {e}")
                    
        # Check final pool status
        final_status = db_service.get_pool_status()
        print(f"📊 Final pool status: {final_status}")
        
        # Verify no connections leaked
        if "available" in final_status and "in_use" in final_status:
            if final_status["in_use"] > 2:  # Allow some for background tasks
                print(f"❌ Possible connection leak: {final_status['in_use']} connections still in use")
                return False
                
        print("✓ Connection pool stress test passed")
        return True
        
    def test_concurrent_access(self):
        """Test concurrent connection access patterns."""
        print("🔍 Testing concurrent connection access...")
        
        db_service = DatabaseService(self.settings)
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(5):
                    conn = db_service._conn()
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SELECT %s, %s", (thread_id, i))
                            cur.fetchone()
                        time.sleep(0.1)  # Simulate work
                    finally:
                        db_service._return(conn)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
                
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
            
        # Wait for all threads
        for thread in threads:
            thread.join()
            
        if errors:
            print(f"❌ Concurrent access errors: {errors}")
            return False
            
        print("✓ Concurrent access test passed")
        return True
        
    def test_project_lattice_services(self):
        """Test the new project lattice services for connection leaks."""
        print("🔍 Testing project lattice services...")
        
        try:
            from backend.services.project_knowledge_service import ProjectKnowledgeService
            from backend.services.project_relationship_service import ProjectRelationshipService
            from backend.services.event_subscription_service import EventSubscriptionService
            
            # Test each service multiple times
            knowledge_service = ProjectKnowledgeService()
            relationship_service = ProjectRelationshipService()
            event_service = EventSubscriptionService()
            
            # Test operations that use connections
            dummy_uuid = "00000000-0000-0000-0000-000000000000"
            for i in range(10):
                # These should not leak connections
                knowledge_service.get_domain_knowledge("systems-engineering")
                relationship_service.get_cousin_projects(dummy_uuid)
                event_service.get_subscriptions(dummy_uuid)
                
            print("✓ Project lattice services connection test passed")
            return True
            
        except Exception as e:
            print(f"❌ Project lattice service error: {e}")
            return False
            
    def run_all_tests(self):
        """Run all connection health tests."""
        print("\n🧪 Database Connection Health Test Suite")
        print("=" * 50)
        
        tests_passed = 0
        tests_total = 4
        
        # Test 1: Basic Connection
        try:
            self.test_basic_connection()
            tests_passed += 1
        except Exception as e:
            print(f"❌ Basic connection test failed: {e}")
            
        # Test 2: Connection Pool Stress  
        try:
            if self.test_connection_pool_stress():
                tests_passed += 1
            else:
                print("❌ Connection pool stress test returned False")
        except Exception as e:
            print(f"❌ Connection pool stress test failed: {e}")
            
        # Test 3: Concurrent Access
        try:
            if self.test_concurrent_access():
                tests_passed += 1
            else:
                print("❌ Concurrent access test returned False")
        except Exception as e:
            print(f"❌ Concurrent access test failed: {e}")
            
        # Test 4: Project Lattice Services
        try:
            if self.test_project_lattice_services():
                tests_passed += 1
            else:
                print("❌ Project lattice services test returned False")
        except Exception as e:
            print(f"❌ Project lattice services test failed: {e}")
        
        print(f"\n📊 Test Results: {tests_passed}/{tests_total} passed")
        
        if tests_passed == tests_total:
            print("✅ All database connection health tests passed!")
            return True
        else:
            print("❌ Some database connection tests failed!")
            return False


if __name__ == "__main__":
    tester = ConnectionHealthTester()
    success = tester.run_all_tests()
    
    if not success:
        print("\n❌ Connection health issues detected!")
        sys.exit(1)
    else:
        print("\n✅ Database connection health verified!")
        sys.exit(0)
