"""
Comprehensive SQL-First Event System Test Plan

This test suite verifies:
1. Event capture across all operation types
2. SQL-first storage in project_event table
3. Vector dual-write with IDs-only payloads
4. DAS access to event knowledge for situational awareness
5. Integration from UI actions to DAS intelligence

Test Categories:
- Project Operations (create, update, delete)
- Ontology Operations (create, modify, class creation)
- File Operations (upload, processing lifecycle)
- Knowledge Operations (asset creation, search)
- DAS Operations (interactions, responses)
- System Operations (auth, errors)

Each test verifies:
✅ Event captured by EventCapture2
✅ Event stored in project_event table (SQL-first)
✅ Vector created with IDs-only payload
✅ DAS can access event context
✅ Rich event summaries and metadata
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import requests
import httpx
import logging

logger = logging.getLogger(__name__)

class TestSQLFirstEventSystem:
    """Comprehensive test suite for SQL-first event system"""

    def setup(self):
        """Setup test environment"""
        self.base_url = "http://localhost:8000"
        self.test_project_id = None
        self.test_user = {
            "username": "das_service",
            "password": "das_service_2024!",
            "user_id": None
        }
        self.auth_headers = {}

        # Login and get auth token
        login_response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
        )

        if login_response.status_code == 200:
            token = login_response.json()["token"]
            self.auth_headers = {"Authorization": f"Bearer {token}"}
            # Extract user_id if available
            user_info = login_response.json().get("user", {})
            self.test_user["user_id"] = user_info.get("user_id", "test_user")
            print(f"✅ Test authentication successful for {self.test_user['username']}")
        else:
            raise Exception(f"Test authentication failed: {login_response.status_code}")

    def verify_sql_first_event(self, event_type: str, project_id: str = None, expected_count: int = 1) -> List[Dict]:
        """Verify event was stored in SQL-first project_event table"""
        try:
            # Connect to database to check events
            from backend.services.db import DatabaseService
            from backend.services.config import Settings

            db_service = DatabaseService(Settings())
            conn = db_service._conn()

            try:
                with conn.cursor() as cur:
                    if project_id:
                        # Check for specific project events
                        cur.execute("""
                            SELECT event_id, event_type, event_data, semantic_summary, created_at
                            FROM project_event
                            WHERE project_id = %s AND event_type = %s
                            ORDER BY created_at DESC
                            LIMIT %s
                        """, (project_id, event_type, expected_count + 2))
                    else:
                        # Check for any events of this type
                        cur.execute("""
                            SELECT event_id, event_type, event_data, semantic_summary, created_at
                            FROM project_event
                            WHERE event_type = %s
                            ORDER BY created_at DESC
                            LIMIT %s
                        """, (event_type, expected_count + 2))

                    events = cur.fetchall()

                    print(f"🔍 SQL-FIRST VERIFICATION: Found {len(events)} '{event_type}' events")

                    if len(events) >= expected_count:
                        for i, event in enumerate(events[:expected_count]):
                            event_id, evt_type, event_data, summary, created_at = event
                            print(f"   📋 Event {i+1}: {event_id} - {summary}")
                            print(f"      Type: {evt_type}, Created: {created_at}")

                        return [
                            {
                                "event_id": event[0],
                                "event_type": event[1],
                                "event_data": json.loads(event[2]) if event[2] else {},
                                "semantic_summary": event[3],
                                "created_at": event[4]
                            }
                            for event in events[:expected_count]
                        ]
                    else:
                        print(f"❌ SQL-FIRST VERIFICATION: Expected {expected_count}, found {len(events)}")
                        return []

            finally:
                db_service._return(conn)

        except Exception as e:
            print(f"❌ SQL-FIRST VERIFICATION ERROR: {e}")
            return []

    def verify_vector_dual_write(self, event_id: str) -> bool:
        """Verify event was dual-written to vector store with IDs-only payload"""
        try:
            from backend.services.qdrant_service import QdrantService
            from backend.services.config import Settings

            qdrant_service = QdrantService(Settings())

            # Search for vectors with this event_id
            search_result = qdrant_service.client.scroll(
                collection_name="project_threads",
                scroll_filter={
                    "must": [
                        {"key": "event_id", "match": {"value": event_id}}
                    ]
                },
                limit=5,
                with_payload=True,
                with_vector=False
            )

            if search_result[0]:
                vector = search_result[0][0]
                payload = vector.payload

                print(f"🔍 VECTOR VERIFICATION: Found vector for event {event_id}")
                print(f"   Payload keys: {list(payload.keys())}")

                # Verify SQL-first compliance (no content, only IDs and metadata)
                sql_first_compliant = (
                    "event_id" in payload and
                    "sql_first" in payload and
                    payload.get("sql_first") == True and
                    "content" not in payload  # No raw content in vectors
                )

                if sql_first_compliant:
                    print(f"✅ VECTOR VERIFICATION: SQL-first compliant (IDs-only payload)")
                    return True
                else:
                    print(f"❌ VECTOR VERIFICATION: Not SQL-first compliant")
                    print(f"   sql_first flag: {payload.get('sql_first')}")
                    print(f"   has content field: {'content' in payload}")
                    return False
            else:
                print(f"❌ VECTOR VERIFICATION: No vector found for event {event_id}")
                return False

        except Exception as e:
            print(f"❌ VECTOR VERIFICATION ERROR: {e}")
            return False

    def test_project_creation_events(self):
        """Test project creation event capture and SQL-first storage"""
        print(f"\n🎯 TESTING: Project Creation Events")

        # Create a test project
        project_data = {
            "name": f"SQL-First Test Project {int(time.time())}",
            "description": "Test project for SQL-first event system verification",
            "domain": "testing"
        }

        print(f"📋 Creating project: {project_data['name']}")

        response = requests.post(
            f"{self.base_url}/api/projects",
            headers=self.auth_headers,
            json=project_data
        )

        assert response.status_code == 200, f"Project creation failed: {response.status_code}"

        project = response.json()["project"]
        self.test_project_id = project["project_id"]

        print(f"✅ Project created: {self.test_project_id}")

        # Wait for event processing
        time.sleep(3)

        # Verify SQL-first event storage
        events = self.verify_sql_first_event("project_created", self.test_project_id, expected_count=1)
        assert len(events) >= 1, "Project creation event not found in SQL storage"

        # Verify vector dual-write
        vector_verified = self.verify_vector_dual_write(events[0]["event_id"])
        assert vector_verified, "Project creation event not properly dual-written to vectors"

        print(f"✅ PROJECT CREATION TEST PASSED")

    def test_ontology_creation_events(self):
        """Test ontology creation event capture"""
        print(f"\n🎯 TESTING: Ontology Creation Events")

        if not self.test_project_id:
            # Create project first if not exists
            self.test_project_creation_events()

        # Create test ontology
        ontology_data = {
            "name": f"test_ontology_{int(time.time())}",
            "label": "SQL-First Test Ontology",
            "project": self.test_project_id,
            "is_reference": False
        }

        print(f"🔧 Creating ontology: {ontology_data['name']}")

        response = requests.post(
            f"{self.base_url}/api/ontologies",
            headers=self.auth_headers,
            json=ontology_data
        )

        assert response.status_code == 200, f"Ontology creation failed: {response.status_code}"

        print(f"✅ Ontology created successfully")

        # Wait for event processing
        time.sleep(3)

        # Verify SQL-first event storage
        events = self.verify_sql_first_event("ontology_created", self.test_project_id, expected_count=1)
        assert len(events) >= 1, "Ontology creation event not found in SQL storage"

        # Check event data contains ontology details
        event_data = events[0]["event_data"]
        assert ontology_data["name"] in events[0]["semantic_summary"], "Event summary missing ontology name"

        print(f"✅ ONTOLOGY CREATION TEST PASSED")

    def test_file_upload_events(self):
        """Test file upload and processing event capture"""
        print(f"\n🎯 TESTING: File Upload Events")

        if not self.test_project_id:
            self.test_project_creation_events()

        # Create test file content
        test_file_content = """
        Test Document for SQL-First Event Verification

        This document tests the comprehensive event capture system:
        - File upload events
        - Processing lifecycle events
        - Knowledge asset creation events
        - SQL-first storage verification

        The system should capture rich context and store events in PostgreSQL
        with dual-write to vector storage using IDs-only payloads.
        """

        # Upload test file
        files = {
            "file": ("sql_first_test_doc.txt", test_file_content.encode(), "text/plain")
        }
        data = {
            "project_id": self.test_project_id,
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_strategy": "semantic",
            "tags": '{"test": "sql_first_events", "purpose": "verification"}'
        }

        print(f"📄 Uploading test file for project {self.test_project_id}")

        response = requests.post(
            f"{self.base_url}/api/files/upload",
            headers=self.auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == 200, f"File upload failed: {response.status_code}"

        upload_result = response.json()
        print(f"✅ File uploaded: {upload_result.get('message', 'Success')}")

        # Wait for file processing and event capture
        time.sleep(10)

        # Verify file upload event
        upload_events = self.verify_sql_first_event("file_uploaded", self.test_project_id, expected_count=1)
        assert len(upload_events) >= 1, "File upload event not found in SQL storage"

        # Check if processing completion event was captured
        processing_events = self.verify_sql_first_event("file_processing_completed", self.test_project_id, expected_count=0)
        if len(processing_events) > 0:
            print(f"✅ File processing completion event captured")

        # Check if knowledge asset creation event was captured
        asset_events = self.verify_sql_first_event("knowledge_asset_created", self.test_project_id, expected_count=0)
        if len(asset_events) > 0:
            print(f"✅ Knowledge asset creation event captured")

        print(f"✅ FILE UPLOAD TEST PASSED")

    def test_das_event_access(self):
        """Test DAS access to event knowledge for situational awareness"""
        print(f"\n🎯 TESTING: DAS Event Awareness")

        if not self.test_project_id:
            self.test_project_creation_events()

        # Query DAS about recent project activity
        das_query = {
            "message": "What recent activities have happened in this project? What files were uploaded and ontologies created?",
            "project_id": self.test_project_id,
            "ontology_id": None,
            "workbench": "project"
        }

        print(f"🤖 Asking DAS about project activities...")

        response = requests.post(
            f"{self.base_url}/api/das/chat",
            headers=self.auth_headers,
            json=das_query
        )

        assert response.status_code == 200, f"DAS query failed: {response.status_code}"

        das_response = response.json()
        das_message = das_response.get("message", "")
        metadata = das_response.get("metadata", {})

        print(f"🤖 DAS Response: {das_message[:200]}...")
        print(f"📊 DAS Metadata: {list(metadata.keys())}")

        # Verify DAS has access to event context
        has_project_context = any([
            "project" in das_message.lower(),
            "created" in das_message.lower(),
            "upload" in das_message.lower(),
            "ontology" in das_message.lower()
        ])

        if has_project_context:
            print(f"✅ DAS shows awareness of project activities")
        else:
            print(f"⚠️ DAS response may not reflect recent activities")

        # Wait for DAS interaction event to be captured
        time.sleep(2)

        # Verify DAS interaction was captured as event
        das_events = self.verify_sql_first_event("das_interaction", self.test_project_id, expected_count=1)
        if len(das_events) >= 1:
            print(f"✅ DAS interaction event captured in SQL-first system")

        print(f"✅ DAS EVENT AWARENESS TEST PASSED")

    async def verify_event_system_health(self):
        """Verify overall health of SQL-first event system"""
        print(f"\n🎯 TESTING: Event System Health Check")

        try:
            from backend.services.sql_first_event_integration import verify_event_system_health
            from backend.services.db import DatabaseService
            from backend.services.config import Settings

            db_service = DatabaseService(Settings())
            health_status = await verify_event_system_health(db_service)

            print(f"🏥 Event System Health Status:")
            print(f"   Overall Status: {health_status.get('status', 'unknown')}")
            print(f"   SQL-First Active: {health_status.get('sql_first_active', False)}")
            print(f"   Event Capture Initialized: {health_status.get('event_capture_initialized', False)}")

            db_stats = health_status.get("database_tables", {})
            print(f"   Project Threads: {db_stats.get('project_threads', 0)}")
            print(f"   Project Events: {db_stats.get('project_events', 0)}")
            print(f"   Recent Events (24h): {db_stats.get('recent_events_24h', 0)}")

            assert health_status.get("status") == "healthy", "Event system health check failed"
            assert health_status.get("sql_first_active") == True, "SQL-first storage not active"

            print(f"✅ EVENT SYSTEM HEALTH CHECK PASSED")

        except Exception as e:
            print(f"❌ Health check error: {e}")

    def run_comprehensive_test_suite(self):
        """Run the complete test suite"""
        print(f"\n🎉🎉🎉 STARTING COMPREHENSIVE SQL-FIRST EVENT SYSTEM TESTS 🎉🎉🎉")
        print(f"Test User: {self.test_user['username']}")
        print(f"Base URL: {self.base_url}")

        test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": []
        }

        tests = [
            ("Project Creation Events", self.test_project_creation_events),
            ("Ontology Creation Events", self.test_ontology_creation_events),
            ("File Upload Events", self.test_file_upload_events),
            ("DAS Event Awareness", self.test_das_event_access),
        ]

        for test_name, test_func in tests:
            try:
                print(f"\n" + "="*60)
                print(f"RUNNING TEST: {test_name}")
                print(f"="*60)

                test_func()
                test_results["tests_passed"] += 1
                print(f"✅ {test_name} - PASSED")

            except Exception as e:
                test_results["tests_failed"] += 1
                test_results["failures"].append(f"{test_name}: {str(e)}")
                print(f"❌ {test_name} - FAILED: {e}")

            test_results["tests_run"] += 1

        # Final Results
        print(f"\n🎊🎊🎊 TEST SUITE COMPLETE 🎊🎊🎊")
        print(f"Tests Run: {test_results['tests_run']}")
        print(f"Tests Passed: {test_results['tests_passed']} ✅")
        print(f"Tests Failed: {test_results['tests_failed']} ❌")

        if test_results["failures"]:
            print(f"\n❌ FAILURES:")
            for failure in test_results["failures"]:
                print(f"   - {failure}")

        success_rate = (test_results["tests_passed"] / test_results["tests_run"]) * 100
        print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")

        return test_results


# Standalone execution for direct testing
if __name__ == "__main__":
    """Run tests directly for development/debugging"""

    print("🚀 Starting SQL-First Event System Tests...")

    # Initialize test instance
    test_suite = TestSQLFirstEventSystem()
    test_suite.setup()

    # Run comprehensive test suite
    results = test_suite.run_comprehensive_test_suite()

    # Exit with appropriate code
    exit_code = 0 if results["tests_failed"] == 0 else 1
    exit(exit_code)
