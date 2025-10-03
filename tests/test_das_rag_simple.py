#!/usr/bin/env python3
"""
Simple DAS RAG Test - UI Workflow Mimicking

This test creates a minimal environment to verify DAS RAG functionality
by following the exact UI workflow:
1. Authenticate with das_service account
2. Create a test project
3. Create an ontology and add classes
4. Upload a test knowledge file
5. Wait for embeddings to be generated
6. Ask a single question and verify RAG sources are returned

Based on the working UI flow to identify why automated tests don't get sources.
"""

import asyncio
import json
import os
import sys
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Any

import httpx
import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class SimpleDASTester:
    """Minimal DAS RAG tester that follows exact UI workflow"""

    def __init__(self, verbose: bool = True):
        self.base_url = "http://localhost:8000"
        # Use das_service account as per testing rules
        self.username = "das_service"
        self.password = "das_service_2024!"
        self.verbose = verbose
        self.auth_token = None
        self.project_id = None
        self.project_thread_id = None
        self.ontology_iri = None

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if level == "ERROR":
                print(f"❌ [{timestamp}] {message}")
            elif level == "SUCCESS":
                print(f"✅ [{timestamp}] {message}")
            else:
                print(f"📋 [{timestamp}] {message}")

    async def authenticate(self):
        """Authenticate with das_service account"""
        self.log(f"Authenticating as {self.username}...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password}
            )

            if response.status_code != 200:
                raise Exception(f"Authentication failed: {response.text}")

            auth_data = response.json()
            self.auth_token = auth_data.get("token")

            if not self.auth_token:
                raise Exception("No auth token received")

            self.log(f"Authenticated successfully", "SUCCESS")

    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.auth_token}"}

    async def create_test_project(self):
        """Create a simple test project"""
        project_name = f"DAS_RAG_Test_{int(time.time())}"
        self.log(f"Creating test project: {project_name}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/projects",
                headers=self.auth_headers(),
                json={
                    "name": project_name,
                    "description": "Simple DAS RAG test project",
                    "domain": "testing",
                    "namespace_path": "test/rag-simple"
                }
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Project creation failed: {response.text}")

            project_data = response.json()
            if "project" in project_data:
                self.project_id = project_data["project"]["project_id"]
            else:
                self.project_id = project_data.get("project_id")

            if not self.project_id:
                raise Exception("No project ID received")

            self.log(f"Project created: {project_name} (ID: {self.project_id})", "SUCCESS")

            # Wait for project thread creation
            await asyncio.sleep(3)
            await self.setup_project_thread()

    async def setup_project_thread(self):
        """Setup project thread exactly like UI does"""
        self.log("Setting up project thread...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get existing thread first
            response = await client.get(
                f"{self.base_url}/api/das2/project/{self.project_id}/thread",
                headers=self.auth_headers()
            )

            if response.status_code == 200:
                data = response.json()
                self.project_thread_id = data.get("project_thread_id")
                self.log(f"Found existing project thread: {self.project_thread_id}", "SUCCESS")
            else:
                # Create new thread
                response = await client.post(
                    f"{self.base_url}/api/das2/project/{self.project_id}/thread",
                    headers=self.auth_headers(),
                    json={"create_if_not_exists": True}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.project_thread_id = data.get("project_thread_id")
                    self.log(f"Created project thread: {self.project_thread_id}", "SUCCESS")
                else:
                    raise Exception(f"Could not create project thread: {response.status_code} - {response.text}")

    async def create_test_ontology(self):
        """Create a simple test ontology and add a class"""
        self.log("Creating test ontology...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create ontology
            response = await client.post(
                f"{self.base_url}/api/ontologies",
                headers=self.auth_headers(),
                json={
                    "project": self.project_id,
                    "name": "RAG_TEST_V1",
                    "label": "Simple RAG Test Ontology",
                    "is_reference": False
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ontology creation failed: {response.text}")

            ontology_data = response.json()
            self.ontology_iri = ontology_data.get("graphIri")

            if not self.ontology_iri:
                raise Exception("No ontology IRI received")

            self.log(f"Ontology created: {self.ontology_iri}", "SUCCESS")

            # Add a test class
            response = await client.post(
                f"{self.base_url}/api/ontology/classes?graph={self.ontology_iri}",
                headers=self.auth_headers(),
                json={
                    "name": "TestDrone",
                    "label": "Test Drone",
                    "comment": "Test drone class for RAG validation"
                }
            )

            if response.status_code != 200:
                raise Exception(f"Class creation failed: {response.text}")

            self.log("Test class 'TestDrone' created", "SUCCESS")
            await asyncio.sleep(2)  # Wait for events processing

    async def upload_test_knowledge(self):
        """Upload a simple test knowledge file"""
        self.log("Creating and uploading test knowledge...")

        # Create very specific test content that should be easy to find
        test_content = """# UAV Test Specifications

## SkyHawk Drone Specifications
- **Weight**: 12.5 kg
- **Payload Capacity**: 3.2 kg
- **Maximum Speed**: 85 km/h
- **Flight Time**: 45 minutes
- **Range**: 15 kilometers

## Mission Profile
The SkyHawk drone is designed for surveillance missions requiring extended flight time and moderate payload capacity. It excels in reconnaissance operations where stability and reliability are paramount.

## Technical Details
The aircraft utilizes a proven quadcopter design with carbon fiber construction for optimal strength-to-weight ratio.
"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(temp_file, 'rb') as file_content:
                    files = {'file': ('skyhawk_specs.md', file_content, 'text/markdown')}
                    data = {
                        'project_id': self.project_id,
                        'document_type': 'specification',
                        'title': 'SkyHawk Drone Specifications',
                        'description': 'Test specifications for SkyHawk drone'
                    }

                    response = await client.post(
                        f"{self.base_url}/api/files/upload",
                        headers=self.auth_headers(),
                        files=files,
                        data=data
                    )

                    if response.status_code != 200:
                        raise Exception(f"Knowledge upload failed: {response.text}")

                    upload_result = response.json()
                    self.log(f"Knowledge uploaded: {upload_result.get('filename')}", "SUCCESS")

                    # Wait for embedding generation - be generous with time
                    self.log("Waiting for embedding generation (15 seconds)...")
                    await asyncio.sleep(15)

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    async def test_das_rag_query(self) -> Dict[str, Any]:
        """Ask DAS a specific question that should return RAG sources"""
        question = "What is the weight of the SkyHawk drone?"
        self.log(f"Asking DAS: {question}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/das2/chat/stream",
                headers=self.auth_headers(),
                json={
                    "message": question,
                    "project_id": self.project_id,
                    "project_thread_id": self.project_thread_id,
                    "ontology_id": self.ontology_iri.split('/')[-1] if self.ontology_iri else None,
                    "workbench": "ontology"
                }
            )

            self.log(f"DAS response status: {response.status_code}")

            if response.status_code != 200:
                response_text = await response.aread()
                raise Exception(f"DAS query failed: {response.status_code} - {response_text}")

            # Parse streaming response carefully
            full_response = ""
            sources = []
            metadata = {}

            self.log("Parsing streaming response...")

            try:
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    self.log(f"  Line {line_count}: {line[:100]}...")  # Show first 100 chars

                    if line.startswith("data: "):
                        try:
                            chunk_data = line[6:]  # Remove "data: " prefix
                            if chunk_data.strip() == "":
                                continue

                            chunk = json.loads(chunk_data)
                            chunk_type = chunk.get("type")

                            self.log(f"    Chunk type: {chunk_type}")

                            if chunk_type == "content":
                                content = chunk.get("content", "")
                                full_response += content
                            elif chunk_type == "done":
                                metadata = chunk.get("metadata", {})
                                sources = metadata.get("sources", [])
                                self.log(f"    Found {len(sources)} sources in metadata")
                            elif chunk_type == "error":
                                raise Exception(f"DAS streaming error: {chunk.get('message', 'Unknown error')}")

                        except json.JSONDecodeError as e:
                            self.log(f"    JSON decode error: {e}")
                            continue

            except Exception as e:
                self.log(f"Error parsing streaming response: {e}", "ERROR")
                response_text = await response.aread()
                self.log(f"Raw response text: {response_text}")
                raise

            das_response = {
                "message": full_response,
                "sources": sources,
                "metadata": metadata
            }

            # Log detailed results
            self.log(f"DAS Response Message: {full_response}")
            self.log(f"Number of sources found: {len(sources)}")

            if sources:
                self.log("Sources found:", "SUCCESS")
                for i, source in enumerate(sources):
                    self.log(f"  Source {i+1}: {source.get('title', 'No title')} - {source.get('type', 'No type')}")
            else:
                self.log("No sources found - RAG may not be working", "ERROR")

            return das_response

    async def cleanup_existing_test_projects(self):
        """Clean up any existing test projects before starting"""
        self.log("Checking for existing test projects to clean up...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get list of projects
            response = await client.get(
                f"{self.base_url}/api/projects",
                headers=self.auth_headers()
            )

            if response.status_code != 200:
                self.log(f"Could not list projects for cleanup: {response.status_code}", "ERROR")
                return

            response_data = response.json()

            # Handle both list and dict with 'projects' key
            if isinstance(response_data, dict) and 'projects' in response_data:
                projects = response_data['projects']
            elif isinstance(response_data, list):
                projects = response_data
            else:
                projects = []

            test_projects = [p for p in projects if isinstance(p, dict) and p.get('name', '').startswith('DAS_RAG_Test_')]

            if test_projects:
                self.log(f"Found {len(test_projects)} existing test projects, cleaning up...")

                for project in test_projects:
                    project_id = project.get('project_id')
                    response = await client.delete(
                        f"{self.base_url}/api/projects/{project_id}",
                        headers=self.auth_headers()
                    )
                    if response.status_code == 200:
                        self.log(f"Deleted existing test project: {project.get('name')}", "SUCCESS")
                    else:
                        self.log(f"Warning: Could not delete project {project.get('name')}: {response.status_code}", "ERROR")
            else:
                self.log("No existing test projects found")

    async def cleanup_project_knowledge_assets(self):
        """Clean up knowledge assets specifically before deleting project"""
        if not self.project_id:
            return

        self.log("Cleaning up knowledge assets...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get and delete project files
            try:
                response = await client.get(
                    f"{self.base_url}/api/files",
                    headers=self.auth_headers(),
                    params={"project_id": self.project_id}
                )

                if response.status_code == 200:
                    files_data = response.json()
                    files = files_data if isinstance(files_data, list) else files_data.get('files', [])

                    for file_info in files:
                        file_id = file_info.get('id') or file_info.get('file_id')
                        if file_id:
                            delete_response = await client.delete(
                                f"{self.base_url}/api/files/{file_id}",
                                headers=self.auth_headers()
                            )
                            if delete_response.status_code == 200:
                                self.log(f"Deleted file: {file_info.get('filename', file_id)}")

            except Exception as e:
                self.log(f"Error cleaning up files: {e}", "ERROR")

    async def cleanup_test_project(self):
        """Thoroughly clean up the test project and all associated assets"""
        if self.project_id:
            self.log("Starting comprehensive test cleanup...")

            # First clean up knowledge assets explicitly
            await self.cleanup_project_knowledge_assets()

            # Then delete the project (should cascade delete remaining items)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/api/projects/{self.project_id}",
                    headers=self.auth_headers()
                )

                if response.status_code == 200:
                    self.log("Test project and all assets cleaned up", "SUCCESS")
                else:
                    self.log(f"Warning: Could not delete test project: {response.status_code}", "ERROR")

                    # If project deletion fails, log the error but don't fail the test
                    try:
                        error_text = await response.aread() if hasattr(response, 'aread') else response.text
                        self.log(f"Project deletion error details: {error_text}", "ERROR")
                    except:
                        pass


@pytest.mark.asyncio
async def test_das_rag_simple():
    """
    Simple DAS RAG test that follows exact UI workflow

    This test:
    1. Uses das_service account (as per testing rules)
    2. Creates a minimal project setup
    3. Uploads specific test content
    4. Asks one targeted question
    5. Verifies RAG sources are returned
    """

    tester = SimpleDASTester(verbose=True)
    test_exception = None

    try:
        print("\n" + "="*60)
        print("🧪 SIMPLE DAS RAG TEST - UI WORKFLOW")
        print("="*60)

        # Step 1: Authenticate
        await tester.authenticate()

        # Step 1.5: Clean up any existing test projects
        await tester.cleanup_existing_test_projects()

        # Step 2: Create test project
        await tester.create_test_project()

        # Step 3: Create ontology and class
        await tester.create_test_ontology()

        # Step 4: Upload knowledge
        await tester.upload_test_knowledge()

        print("\n📋 Test environment ready, asking DAS question...")

        # Step 5: Test RAG query
        das_response = await tester.test_das_rag_query()

        # Step 6: Verify results
        sources_count = len(das_response.get("sources", []))
        message = das_response.get("message", "")

        print(f"\n📊 RESULTS:")
        print(f"   Sources found: {sources_count}")
        print(f"   Response length: {len(message)} chars")
        print(f"   Contains 'SkyHawk': {'SkyHawk' in message}")
        print(f"   Contains weight info: {'12.5' in message}")

        # Success criteria
        if sources_count > 0:
            print(f"\n✅ SUCCESS: DAS returned {sources_count} sources!")
            print("   RAG functionality is working correctly")
        else:
            test_exception = Exception(f"FAILURE: DAS returned no sources - RAG not working")

        if "12.5" not in message and "SkyHawk" not in message:
            if not test_exception:
                test_exception = Exception("FAILURE: DAS response doesn't contain expected knowledge")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        test_exception = e

    finally:
        # Always cleanup
        try:
            await tester.cleanup_test_project()
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup error: {cleanup_error}")

        # Raise any test failures after cleanup
        if test_exception:
            raise test_exception

    print(f"\n🎉 DAS RAG test completed successfully!")
    return das_response


if __name__ == "__main__":
    """Run simple DAS RAG test directly"""
    print("🔍 Running Simple DAS RAG Test...")
    result = asyncio.run(test_das_rag_simple())
    print(f"Final result: {len(result.get('sources', []))} sources found")
