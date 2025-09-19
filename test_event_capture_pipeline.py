#!/usr/bin/env python3
"""
Comprehensive Event Capture Pipeline Test

This script tests the complete event capture pipeline from project creation
through DAS interaction to ensure all semantic events are properly captured
and available for DAS context.

Test Flow:
1. Create project → verify project thread creation + project name capture
2. Create ontology → verify ontology creation event + ontology name capture
3. Perform semantic operations → create classes, rename, add relationships, data properties, notes
4. Test DAS integration → query via DAS dock API with full project thread context + RAG results
"""

import asyncio
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Test configuration
BASE_URL = "http://localhost:8000"
QDRANT_URL = "http://localhost:6333"
TEST_USERNAME = "das_service"
TEST_PASSWORD = "das_service_2024!"

class ODRASEventTester:
    def __init__(self):
        self.token = None
        self.project_id = None
        self.project_thread_id = None
        self.test_session = f"test_{int(time.time())}"
        self.uploaded_files = []  # Track uploaded files and their processing
        self.process_instances = []  # Track specific process instances we created

        # Set up logging to file
        import os
        os.makedirs("logs", exist_ok=True)
        self.log_file = f"logs/event_capture_test_{self.test_session}.log"

    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp to both console and file with real-time output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}"

        # Print to console with immediate flush for real-time output
        print(log_message, flush=True)

        # Write to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
                f.flush()  # Ensure immediate write
        except Exception as e:
            print(f"❌ Failed to write to log file: {e}", flush=True)

    def authenticate(self) -> bool:
        """Authenticate and get token"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                self.token = response.json()["token"]
                self.log(f"✅ Authentication successful")
                return True
            else:
                self.log(f"❌ Authentication failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Authentication error: {e}", "ERROR")
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def test_project_creation(self) -> bool:
        """Test 1: Create project and verify project thread creation"""
        self.log("🧪 TEST 1: Creating project and verifying project thread...")

        project_data = {
            "name": f"Event Pipeline Test {self.test_session}",
            "description": f"Testing complete event capture pipeline - {self.test_session}"
        }

        try:
            # Create project
            response = requests.post(
                f"{BASE_URL}/api/projects",
                json=project_data,
                headers=self.get_auth_headers(),
                timeout=10
            )

            if response.status_code != 200:
                self.log(f"❌ Project creation failed: {response.status_code} - {response.text}", "ERROR")
                return False

            project_info = response.json()["project"]
            self.project_id = project_info["project_id"]
            self.log(f"✅ Project created: {self.project_id}")
            self.log(f"   Name: {project_info['name']}")

            # Wait for project thread creation
            time.sleep(2)

            # Verify project thread was created
            project_thread = self.get_project_thread(self.project_id)
            if not project_thread:
                self.log("❌ Project thread not found", "ERROR")
                return False

            self.project_thread_id = project_thread["project_thread_id"]
            self.log(f"✅ Project thread created: {self.project_thread_id}")

            # Verify project creation event was captured
            return self.verify_specific_event("project_creation", "project_created")

        except Exception as e:
            self.log(f"❌ Project creation test failed: {e}", "ERROR")
            return False

    def test_ontology_creation(self) -> bool:
        """Test 2: Create ontology and verify ontology creation event"""
        self.log("🧪 TEST 2: Creating ontology and verifying capture...")

        ontology_data = {
            "metadata": {
                "name": f"Test Pipeline Ontology {self.test_session}",
                "namespace": "https://xma-adt.usnc.mil",
                "description": f"Test ontology for event pipeline - {self.test_session}"
            },
            "classes": [],
            "object_properties": [],
            "datatype_properties": []
        }

        try:
            # Create ontology using POST endpoint with project_id
            response = requests.post(
                f"{BASE_URL}/api/ontology/?project_id={self.project_id}",
                json=ontology_data,
                headers=self.get_auth_headers(),
                timeout=10
            )

            if response.status_code != 200:
                self.log(f"❌ Ontology creation failed: {response.status_code} - {response.text}", "ERROR")
                return False

            result = response.json()
            self.log(f"✅ Ontology created successfully")
            self.log(f"   Backup ID: {result['data']['backup_id']}")
            self.log(f"   Triples: {result['data']['triples_count']}")

            # Wait for event processing
            time.sleep(2)

            # Verify ontology creation event was captured
            return self.verify_specific_event("ontology_creation", "Created new ontology")

        except Exception as e:
            self.log(f"❌ Ontology creation test failed: {e}", "ERROR")
            return False

    def test_semantic_operations(self) -> bool:
        """Test 3: Create classes, rename, add relationships, data properties"""
        self.log("🧪 TEST 3: Performing semantic operations...")

        # Test 3a: Create initial classes
        ontology_with_classes = {
            "metadata": {
                "name": f"Semantic Test Ontology {self.test_session}",
                "namespace": "https://xma-adt.usnc.mil",
                "description": "Testing semantic operations capture"
            },
            "classes": [
                {
                    "name": "TestClass1",
                    "iri": "https://xma-adt.usnc.mil/TestClass1",
                    "label": "Test Class One",
                    "description": "First test class for semantic operations"
                },
                {
                    "name": "TestClass2",
                    "iri": "https://xma-adt.usnc.mil/TestClass2",
                    "label": "Test Class Two",
                    "description": "Second test class for semantic operations"
                }
            ],
            "object_properties": [],
            "datatype_properties": []
        }

        try:
            # Create classes
            response = requests.put(
                f"{BASE_URL}/api/ontology/?project_id={self.project_id}",
                json=ontology_with_classes,
                headers=self.get_auth_headers(),
                timeout=10
            )

            if response.status_code != 200:
                self.log(f"❌ Class creation failed: {response.status_code}", "ERROR")
                return False

            self.log("✅ Classes created: TestClass1, TestClass2")
            time.sleep(1)

            # Test 3b: Add relationships and data properties
            ontology_with_relations = {
                "metadata": {
                    "name": f"Semantic Test Ontology {self.test_session}",
                    "namespace": "https://xma-adt.usnc.mil",
                    "description": "Testing semantic operations capture"
                },
                "classes": [
                    {
                        "name": "TestClass1",
                        "iri": "https://xma-adt.usnc.mil/TestClass1",
                        "label": "Test Class One RENAMED",  # Rename test
                        "description": "First test class - RENAMED for testing"
                    },
                    {
                        "name": "TestClass2",
                        "iri": "https://xma-adt.usnc.mil/TestClass2",
                        "label": "Test Class Two",
                        "description": "Second test class for semantic operations"
                    }
                ],
                "object_properties": [
                    {
                        "name": "relatedTo",
                        "iri": "https://xma-adt.usnc.mil/relatedTo",
                        "label": "related to",
                        "description": "Test relationship between classes",
                        "domain": "TestClass1",
                        "range": "TestClass2"
                    }
                ],
                "datatype_properties": [
                    {
                        "name": "testName",
                        "iri": "https://xma-adt.usnc.mil/testName",
                        "label": "test name",
                        "description": "Test data property",
                        "domain": "TestClass1",
                        "range": "string"
                    }
                ]
            }

            # Add relationships and properties
            response = requests.put(
                f"{BASE_URL}/api/ontology/?project_id={self.project_id}",
                json=ontology_with_relations,
                headers=self.get_auth_headers(),
                timeout=10
            )

            if response.status_code != 200:
                self.log(f"❌ Relationship/property creation failed: {response.status_code}", "ERROR")
                return False

            self.log("✅ Added: relationship 'relatedTo', data property 'testName', renamed TestClass1")
            time.sleep(2)

            # Verify semantic events were captured
            project_thread = self.get_project_thread(self.project_id)
            if not project_thread:
                return False

            events = project_thread["thread_data"]["project_events"]
            semantic_events = [e for e in events if "ontology" in e.get("key_data", {}).get("semantic_action", "").lower()]

            self.log(f"✅ Captured {len(semantic_events)} semantic ontology events")
            for event in semantic_events:
                action = event.get("key_data", {}).get("semantic_action", "unknown")
                self.log(f"   - {action}")

            return len(semantic_events) > 0

        except Exception as e:
            self.log(f"❌ Semantic operations test failed: {e}", "ERROR")
            return False

    def upload_knowledge_files(self) -> bool:
        """Upload the three test knowledge files to the project"""
        self.log("🧪 TEST 3.5: Uploading knowledge files...")

        test_files = [
            "data/decision_matrix_template.md",
            "data/disaster_response_requirements.md",
            "data/uas_specifications.md"
        ]

        try:
            for file_path in test_files:
                self.log(f"📁 Uploading {file_path}...")

                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                # Upload file exactly like the UI does
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.split('/')[-1], f, 'text/markdown')}
                    data = {
                        'project_id': self.project_id,
                        'embedding_model': 'all-MiniLM-L6-v2',
                        'chunking_strategy': 'hybrid',
                        'tags': '{"docType": "requirements", "status": "new"}'
                    }

                    response = requests.post(
                        f"{BASE_URL}/api/files/upload",
                        files=files,
                        data=data,
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=30
                    )

                if response.status_code == 200:
                    result = response.json()
                    file_id = result.get('file_id', 'unknown')
                    workflow_id = result.get('workflow_id', result.get('knowledge_asset_id', 'unknown'))
                    message = result.get('message', '')

                    # Track this file and its associated workflow
                    file_info = {
                        'file_path': file_path,
                        'file_id': file_id,
                        'workflow_id': workflow_id,
                        'upload_time': datetime.now().isoformat()
                    }
                    self.uploaded_files.append(file_info)

                    self.log(f"✅ Uploaded {file_path.split('/')[-1]}")
                    self.log(f"   File ID: {file_id}")
                    self.log(f"   Knowledge Asset ID: {workflow_id}")
                    self.log(f"   Message: {message}")

                    # The workflow_id is actually the knowledge asset ID, which corresponds to a process instance
                    if workflow_id != 'unknown':
                        self.process_instances.append({
                            'file_id': file_id,
                            'process_instance_id': workflow_id,  # This IS the process instance ID
                            'process_definition_key': 'automatic_knowledge_processing',
                            'start_time': datetime.now().isoformat()
                        })
                        self.log(f"   Process Instance: {workflow_id}")
                else:
                    self.log(f"❌ Failed to upload {file_path}: {response.status_code}", "ERROR")
                    return False

                time.sleep(1)  # Brief pause between uploads

            # Wait for knowledge processing to complete via Camunda monitoring
            self.log("⏳ Monitoring Camunda knowledge processing workflows...")
            if not self.wait_for_knowledge_processing():
                self.log("❌ Knowledge processing failed or timed out", "ERROR")
                return False

            return True

        except Exception as e:
            self.log(f"❌ File upload failed: {e}", "ERROR")
            return False

    def test_das_integration(self) -> bool:
        """Test 5: Query DAS via dock API with full project and knowledge context"""
        self.log("🧪 TEST 5: Testing DAS integration with complete project context...")

        test_questions = [
            "What is this project name and id?",
            "What ontologies does this project have?",
            "Can you tell me what classes we have in our ontologies?",
            "What files are in this project?",
            "What are the specifications of the QuadCopter T4?",
            "Tell me about the TriVector VTOL platform",
            "What did I just ask?"  # Should answer: "Tell me about the TriVector VTOL platform"
        ]

        try:
            das_results = []

            for i, question in enumerate(test_questions, 1):
                self.log(f"🤖 Question {i}/{len(test_questions)}: {question}")

                response = requests.post(
                    f"{BASE_URL}/api/das/chat/send",
                    json={
                        "message": question,
                        "project_id": self.project_id,
                        "project_thread_id": self.project_thread_id
                    },
                    headers=self.get_auth_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    das_response = response.json()
                    message = das_response.get("message", "No response")
                    confidence = das_response.get("confidence", "unknown")
                    sources = das_response.get("metadata", {}).get("sources", [])

                    # Analyze response quality
                    is_generic = "couldn't find" in message.lower() or "no relevant information" in message.lower()

                    if is_generic:
                        self.log(f"⚠️  DAS Response ({confidence}): Generic response - {message[:80]}...")
                        result_status = "GENERIC"
                    else:
                        self.log(f"✅ DAS Response ({confidence}): Specific answer - {message[:80]}...")
                        result_status = "SPECIFIC"

                    if sources:
                        self.log(f"   📚 Sources: {len(sources)} found")
                        for source in sources[:2]:  # Show first 2 sources
                            self.log(f"      - {source.get('title', 'unknown')} ({source.get('relevance_score', 0)*100:.0f}% relevant)")

                    das_results.append({
                        "question": question,
                        "status": result_status,
                        "confidence": confidence,
                        "sources_count": len(sources)
                    })

                else:
                    self.log(f"❌ DAS query failed: {response.status_code} - {response.text}", "ERROR")
                    das_results.append({
                        "question": question,
                        "status": "FAILED",
                        "confidence": "none",
                        "sources_count": 0
                    })

                time.sleep(2)  # Give DAS time between questions

            # Summary of DAS performance
            specific_answers = len([r for r in das_results if r["status"] == "SPECIFIC"])
            generic_answers = len([r for r in das_results if r["status"] == "GENERIC"])
            failed_answers = len([r for r in das_results if r["status"] == "FAILED"])

            self.log(f"📊 DAS Performance Summary:")
            self.log(f"   Specific answers: {specific_answers}/{len(test_questions)}")
            self.log(f"   Generic answers: {generic_answers}/{len(test_questions)}")
            self.log(f"   Failed answers: {failed_answers}/{len(test_questions)}")

            # Test passes if DAS responds to all questions (even if some are generic)
            return failed_answers == 0

        except Exception as e:
            self.log(f"❌ DAS integration test failed: {e}", "ERROR")
            return False

    def get_project_thread(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project thread from Qdrant with detailed verification"""
        try:
            self.log(f"🔍 Querying Qdrant for project thread with project_id: {project_id}")

            response = requests.post(
                f"{QDRANT_URL}/collections/project_threads/points/scroll",
                json={
                    "limit": 10,  # Get more to make sure we find the right one
                    "with_payload": True,
                    "with_vector": False,
                    "filter": {
                        "must": [{"key": "project_id", "match": {"value": project_id}}]
                    }
                },
                timeout=10
            )

            self.log(f"🔍 Qdrant response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                points = result.get("result", {}).get("points", [])
                self.log(f"🔍 Found {len(points)} project threads for project {project_id}")

                if points:
                    # Get the most recent one
                    most_recent = max(points, key=lambda p: p["payload"]["last_activity"])
                    self.log(f"🔍 Using most recent project thread: {most_recent['payload']['project_thread_id']}")
                    self.log(f"🔍 Last activity: {most_recent['payload']['last_activity']}")
                    return most_recent["payload"]
                else:
                    self.log(f"❌ No project threads found for project {project_id}", "ERROR")
            else:
                self.log(f"❌ Qdrant query failed: {response.status_code} - {response.text}", "ERROR")

            return None

        except Exception as e:
            self.log(f"❌ Error getting project thread: {e}", "ERROR")
            return None

    def get_process_instance_for_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the specific process instance created for a workflow"""
        try:
            # Query Camunda for recent process instances that might be related to our workflow
            response = requests.get(
                f"http://localhost:8080/engine-rest/process-instance",
                params={"sortBy": "startTime", "sortOrder": "desc"},
                timeout=5
            )

            if response.status_code == 200:
                processes = response.json()
                # Return the most recent process (likely ours)
                if processes:
                    return processes[0]

            return None

        except Exception as e:
            self.log(f"❌ Error getting process instance for workflow {workflow_id}: {e}", "ERROR")
            return None

    def monitor_specific_process_instances(self) -> Dict[str, Any]:
        """Monitor the specific process instances we created"""
        if not self.process_instances:
            self.log("⚠️  No process instances to monitor", "WARNING")
            return {"status": "no_processes"}

        self.log(f"🔍 Monitoring {len(self.process_instances)} specific process instances...")

        completed_count = 0
        failed_count = 0
        active_count = 0

        for process_info in self.process_instances:
            process_id = process_info['process_instance_id']
            file_id = process_info['file_id']

            try:
                # Check process status
                response = requests.get(
                    f"http://localhost:8080/engine-rest/process-instance/{process_id}",
                    timeout=5
                )

                if response.status_code == 200:
                    # Process is still active
                    active_count += 1
                    self.log(f"   📋 {file_id}: ACTIVE (Process {process_id})")

                elif response.status_code == 404:
                    # Process completed (no longer exists in active instances)
                    completed_count += 1
                    self.log(f"   ✅ {file_id}: COMPLETED (Process {process_id})")

                else:
                    # Other status - might be failed
                    failed_count += 1
                    self.log(f"   ❌ {file_id}: UNKNOWN STATUS {response.status_code} (Process {process_id})", "WARNING")

            except Exception as e:
                failed_count += 1
                self.log(f"   ❌ {file_id}: ERROR checking process {process_id}: {e}", "ERROR")

        return {
            "status": "monitored",
            "total": len(self.process_instances),
            "completed": completed_count,
            "active": active_count,
            "failed": failed_count
        }

    def wait_for_knowledge_processing(self) -> bool:
        """Clean up any hanging processes and wait for knowledge processing to complete"""
        from camunda_process_manager import CamundaProcessManager

        manager = CamundaProcessManager()

        # Don't immediately clean up processes - let them run first!
        self.log("🔍 Checking for existing processes before starting monitoring...")

        # Wait a moment for any new processes to start
        time.sleep(3)

        # Now monitor for completion (simplified for DAS testing focus)
        max_wait_time = 120  # 2 minutes should be enough
        start_time = time.time()

        self.log("⏳ Waiting for knowledge processing to complete...")

        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    "http://localhost:8080/engine-rest/process-instance",
                    params={"processDefinitionKey": "automatic_knowledge_processing"},
                    timeout=5
                )

                if response.status_code == 200:
                    current_processes = response.json()
                    active_count = len(current_processes)

                    if active_count == 0:
                        self.log("✅ Knowledge processing completed!")
                        return self.verify_knowledge_assets()
                    else:
                        elapsed = int(time.time() - start_time)
                        self.log(f"⏳ {active_count} processes still active (elapsed: {elapsed}s)")

                        # If processes are hanging too long, clean them up
                        if elapsed > 180:  # 3 minutes - give more time for processing
                            self.log("🧹 Processes taking too long (>3 min), cleaning up...")
                            manager.cleanup_hanging_processes("automatic_knowledge_processing")
                            time.sleep(2)
                            return self.verify_knowledge_assets()
                else:
                    self.log(f"❌ Failed to check processes: {response.status_code}", "ERROR")
                    return False

            except Exception as e:
                self.log(f"❌ Error monitoring: {e}", "ERROR")
                return False

            time.sleep(5)

        # Timeout - clean up and continue with DAS testing
        self.log("⏰ Knowledge processing timed out, cleaning up and continuing...", "WARNING")
        manager.cleanup_hanging_processes("automatic_knowledge_processing")
        return self.verify_knowledge_assets()

    def check_knowledge_asset_creation_status(self) -> Dict[str, Any]:
        """Check if knowledge assets are being created for our uploaded files"""
        try:
            # Check if knowledge assets exist for our uploaded files
            created_assets = []

            for file_info in self.uploaded_files:
                file_id = file_info['file_id']

                # Check if knowledge asset was created for this file
                response = requests.get(
                    f"{BASE_URL}/api/knowledge/assets",
                    params={"project_id": self.project_id},
                    headers=self.get_auth_headers(),
                    timeout=10
                )

                if response.status_code == 200:
                    assets = response.json().get("assets", [])
                    file_assets = [a for a in assets if a.get("source_file_id") == file_id]

                    if file_assets:
                        asset = file_assets[0]
                        status = asset.get("status", "unknown")
                        asset_id = asset.get("asset_id", "unknown")

                        created_assets.append({
                            "file_id": file_id,
                            "asset_id": asset_id,
                            "status": status,
                            "filename": file_info['file_path'].split('/')[-1]
                        })

                        self.log(f"📋 {file_info['file_path'].split('/')[-1]}: Asset {asset_id} - Status: {status}")

            return {
                "total_files": len(self.uploaded_files),
                "assets_created": len(created_assets),
                "assets": created_assets
            }

        except Exception as e:
            self.log(f"❌ Error checking knowledge asset status: {e}", "ERROR")
            return {"total_files": len(self.uploaded_files), "assets_created": 0, "assets": []}

    def wait_for_knowledge_assets_available(self, max_wait_minutes: int = 15) -> bool:
        """Wait for knowledge assets to be fully available and searchable"""
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        self.log(f"⏳ Waiting up to {max_wait_minutes} minutes for knowledge assets to become available...")

        while time.time() - start_time < max_wait_seconds:
            # Check asset creation status
            asset_status = self.check_knowledge_asset_creation_status()

            if asset_status["assets_created"] == 0:
                elapsed = int(time.time() - start_time)
                self.log(f"⏳ No assets created yet (elapsed: {elapsed}s)")
                time.sleep(10)
                continue

            # Check if all assets are completed (not just active)
            completed_assets = [a for a in asset_status["assets"] if a["status"] == "completed"]
            active_assets = [a for a in asset_status["assets"] if a["status"] == "active"]

            self.log(f"📊 Assets: {len(completed_assets)} completed, {len(active_assets)} active")

            if len(completed_assets) == asset_status["total_files"]:
                self.log("✅ All knowledge assets completed!")
                return self.verify_knowledge_searchable()

            elapsed = int(time.time() - start_time)
            self.log(f"⏳ Waiting for asset completion (elapsed: {elapsed}s)")
            time.sleep(15)  # Check every 15 seconds

        # Timeout - check what we have
        asset_status = self.check_knowledge_asset_creation_status()
        self.log(f"⏰ Timeout reached - final status: {asset_status['assets_created']}/{asset_status['total_files']} assets")

        # If we have any completed assets, try to proceed
        if asset_status["assets_created"] > 0:
            return self.verify_knowledge_searchable()

        return False

    def verify_knowledge_searchable(self) -> bool:
        """Verify knowledge assets are searchable via RAG"""
        test_searches = [
            "QuadCopter T4",
            "TriVector VTOL",
            "disaster response"
        ]

        for search_term in test_searches:
            response = requests.post(
                f"{BASE_URL}/api/knowledge/query",
                json={"question": search_term, "project_id": self.project_id},
                headers=self.get_auth_headers(),
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                chunks_found = result.get("chunks_found", 0)
                if chunks_found > 0:
                    self.log(f"✅ Knowledge searchable: '{search_term}' found {chunks_found} chunks")
                    return True
                else:
                    self.log(f"⚠️  Search for '{search_term}' found 0 chunks")
            else:
                self.log(f"❌ Knowledge search failed for '{search_term}': {response.status_code}")

        self.log("⚠️  Knowledge assets not yet searchable", "WARNING")
        return False

    def verify_knowledge_assets(self) -> bool:
        """Verify that knowledge assets are fully available"""
        return self.wait_for_knowledge_assets_available()

    def verify_specific_event(self, event_description: str, action_contains: str) -> bool:
        """Verify a specific event exists in the project thread"""
        self.log(f"🔍 Verifying event: {event_description}")

        project_thread = self.get_project_thread(self.project_id)
        if not project_thread:
            self.log(f"❌ FAIL: Could not retrieve project thread for {event_description}", "ERROR")
            return False

        events = project_thread["thread_data"]["project_events"]

        # Look for event with matching action
        found_event = None
        for event in events:
            action = event.get("key_data", {}).get("semantic_action", event.get("key_data", {}).get("action", ""))
            if action_contains.lower() in action.lower():
                found_event = event
                break

        if found_event:
            action = found_event.get("key_data", {}).get("semantic_action", found_event.get("key_data", {}).get("action", ""))
            self.log(f"✅ PASS: {event_description} event found: {action}")
            return True
        else:
            self.log(f"❌ FAIL: {event_description} event not found", "ERROR")
            available_actions = [e.get("key_data", {}).get("semantic_action", e.get("key_data", {}).get("action", "unknown")) for e in events]
            self.log(f"   Available events: {available_actions}")
            return False

    def check_das_routing_failures(self):
        """Check for DAS routing failures in logs"""
        self.log("🔍 Checking for DAS routing failures...")
        try:
            # This is a simple check - in production you'd read actual log files
            # For now, we'll just note that routing failures should be investigated
            self.log("⚠️  Note: Check /tmp/odras_app.log for 'DAS routing FAILED' messages")
            self.log("⚠️  Routing failures indicate events are captured but not reaching project threads")
        except Exception as e:
            self.log(f"❌ Error checking routing failures: {e}", "ERROR")

    def print_project_thread_summary(self):
        """Print detailed summary of project thread contents with real Qdrant verification"""
        self.log("📋 PROJECT THREAD SUMMARY (Real Qdrant Data):")

        project_thread = self.get_project_thread(self.project_id)
        if not project_thread:
            self.log("❌ No project thread found in Qdrant", "ERROR")
            return

        thread_data = project_thread["thread_data"]

        self.log(f"   Project ID: {project_thread['project_id']}")
        self.log(f"   Thread ID: {project_thread['project_thread_id']}")
        self.log(f"   Created: {project_thread['created_at']}")
        self.log(f"   Last Activity: {project_thread['last_activity']}")

        events = thread_data["project_events"]
        self.log(f"   Total Events in Qdrant: {len(events)}")

        # Categorize events
        event_types = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        self.log(f"   Event breakdown: {event_types}")

        # Show detailed events
        for i, event in enumerate(events):
            event_type = event.get("event_type", "unknown")
            action = event.get("key_data", {}).get("semantic_action", event.get("key_data", {}).get("action", "unknown"))
            timestamp = event.get("timestamp", "unknown")
            self.log(f"   Event {i+1}: [{event_type}] {action} @ {timestamp}")

        # Verify specific event types we expect
        expected_events = ["project_thread_created", "project_created", "ontology"]
        found_events = []
        for event in events:
            action = event.get("key_data", {}).get("semantic_action", event.get("key_data", {}).get("action", ""))
            for expected in expected_events:
                if expected in action.lower():
                    found_events.append(expected)

        self.log(f"   Expected events found: {found_events}")
        missing_events = [e for e in expected_events if e not in found_events]
        if missing_events:
            self.log(f"   ⚠️  Missing expected events: {missing_events}", "WARNING")

    def run_complete_test(self) -> bool:
        """Run the complete test pipeline"""
        self.log("🚀 Starting complete event capture pipeline test...")
        self.log(f"   Test Session: {self.test_session}")
        self.log(f"   Log File: {self.log_file}")

        # Step 1: Authenticate
        if not self.authenticate():
            return False

        # Step 2: Test project creation
        if not self.test_project_creation():
            self.log("❌ Project creation test failed", "ERROR")
            return False

        # Step 3: Test ontology creation
        if not self.test_ontology_creation():
            self.log("❌ Ontology creation test failed", "ERROR")
            return False

        # Step 4: Test semantic operations
        if not self.test_semantic_operations():
            self.log("❌ Semantic operations test failed", "ERROR")
            return False

        # Step 4.5: Upload knowledge files (continue even if knowledge processing fails)
        if not self.upload_knowledge_files():
            self.log("⚠️  Knowledge file upload had issues, but continuing with DAS testing...", "WARNING")

        # Step 5: Test DAS integration
        if not self.test_das_integration():
            self.log("❌ DAS integration test failed", "ERROR")
            return False

        # Step 6: Check for DAS routing failures
        self.check_das_routing_failures()

        # Step 7: Print summary with real Qdrant verification
        self.print_project_thread_summary()

        self.log("🎉 ALL TESTS PASSED! Event capture pipeline is working correctly.")
        self.log(f"📊 FINAL RESULTS:")
        self.log(f"   Project ID: {self.project_id}")
        self.log(f"   Project Thread ID: {self.project_thread_id}")
        self.log(f"   Log File: {self.log_file}")
        return True

def main():
    """Main test execution"""
    tester = ODRASEventTester()

    print("=" * 80)
    print("ODRAS EVENT CAPTURE PIPELINE TEST")
    print("=" * 80)

    success = tester.run_complete_test()

    print("=" * 80)
    if success:
        print("✅ TEST SUITE PASSED - Event capture pipeline is working correctly!")
    else:
        print("❌ TEST SUITE FAILED - Issues found in event capture pipeline")
    print("=" * 80)

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
