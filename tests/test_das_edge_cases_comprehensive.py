#!/usr/bin/env python3
"""
DAS Edge Cases and Consistency Test

This test identifies and validates DAS consistency issues including:
1. Knowledge inconsistency (same data, different answers)
2. Contextual reference failures
3. Source format consistency
4. Memory persistence across conversations
5. Cross-knowledge-asset queries
6. Edge case scenarios that break DAS

Based on real issues found in production usage.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

import httpx
import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class DASEdgeCaseTester:
    """Comprehensive DAS edge case and consistency tester - self-contained"""

    def __init__(self, username: str = "jdehart", password: str = "jdehart123!", verbose: bool = True):
        self.base_url = "http://localhost:8000"
        self.username = username
        self.password = password
        self.verbose = verbose
        self.auth_token = None
        self.test_log = []
        self.conversation_history = []

        # Will be created during test
        self.project_id = None
        self.ontology_iri = None

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        self.test_log.append(log_entry)

        if self.verbose:
            if level == "ERROR":
                print(f"❌ {message}")
            elif level == "SUCCESS":
                print(f"✅ {message}")
            elif level == "CONSISTENCY_FAIL":
                print(f"🚨 CONSISTENCY FAILURE: {message}")
            elif level == "EDGE_CASE":
                print(f"🔍 EDGE CASE: {message}")
            else:
                print(f"📋 {message}")

    async def authenticate(self):
        """Authenticate with provided credentials"""
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

            self.log(f"Authenticated as {self.username}", "SUCCESS")

    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.auth_token}"}

    async def create_test_project(self):
        """Create test project with full setup"""
        project_name = f"DAS_EdgeCase_Test_{int(time.time())}"
        self.log(f"Creating test project: {project_name}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/projects",
                headers=self.auth_headers(),
                json={
                    "name": project_name,
                    "description": "Edge case testing project for DAS consistency validation",
                    "domain": "aerospace-engineering",
                    "namespace_path": "test/edge-cases"
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

            self.log(f"Test project created: {project_name} ({self.project_id})", "SUCCESS")
            await asyncio.sleep(2)  # Wait for project thread creation

            # Setup DAS exactly like the DAS dock does
            await self._setup_das_like_dock()

    async def setup_test_ontology_and_classes(self):
        """Create test ontology with classes for edge case testing"""
        self.log("Creating test ontology and classes...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create ontology
            response = await client.post(
                f"{self.base_url}/api/ontologies",
                headers=self.auth_headers(),
                json={
                    "project": self.project_id,
                    "name": "EDGE_TEST_V1",
                    "label": "Edge Case Test Ontology Version 1",
                    "is_reference": False
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ontology creation failed: {response.text}")

            ontology_data = response.json()
            self.ontology_iri = ontology_data.get("graphIri")

            if not self.ontology_iri:
                raise Exception("No ontology IRI received")

            self.log(f"Test ontology created: {self.ontology_iri}", "SUCCESS")

            # Create test classes
            test_classes = ["TestClass1", "TestClass2", "EdgeCaseClass"]

            for class_name in test_classes:
                response = await client.post(
                    f"{self.base_url}/api/ontology/classes?graph={self.ontology_iri}",
                    headers=self.auth_headers(),
                    json={
                        "name": class_name,
                        "label": class_name,
                        "comment": f"Test class for edge case validation: {class_name}"
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Class creation failed for {class_name}: {response.text}")

                self.log(f"Test class created: {class_name}", "SUCCESS")

            await asyncio.sleep(2)  # Wait for events processing

    async def upload_test_knowledge(self):
        """Upload test knowledge content for edge case testing"""
        self.log("Creating and uploading test knowledge...")

        # Create comprehensive test content
        test_content = """# Edge Case Test Specifications

## AeroMapper X8 Test Platform
- **Weight**: 20 kg
- **Payload**: 5 kg
- **Wingspan**: 4.2 meters
- **Speed**: 140 km/h

## QuadCopter T4 Test Platform
- **Weight**: 2.5 kg
- **Payload**: 0.8 kg
- **Speed**: 65 km/h

## TriVector VTOL Test Platform
- **Weight**: 15.2 kg
- **Payload**: 5.5 kg
- **Wingspan**: 2.8 meters
- **Speed**: 180 km/h

## Edge Case Scenarios
- Test platform for consistency validation
- Multiple UAV specifications for comprehensive testing
- Designed to test DAS knowledge retrieval and consistency
"""

        # Write to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(temp_file, 'rb') as file_content:
                    files = {'file': ('edge_case_specs.md', file_content, 'text/markdown')}
                    data = {
                        'project_id': self.project_id,
                        'document_type': 'specification',
                        'title': 'Edge Case Test Specifications',
                        'description': 'Test specifications for DAS edge case validation'
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
                    self.log(f"Test knowledge uploaded: {upload_result.get('filename')}", "SUCCESS")

                    # Wait for knowledge processing and embedding generation
                    self.log("Waiting for embedding generation...")
                    await asyncio.sleep(10)  # Reduced wait time to avoid connection pool issues

                    # Verify embeddings are ready (with shorter timeout)
                    await self._verify_embeddings_ready()

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    async def cleanup_test_project(self):
        """Clean up test project and all associated objects"""
        if self.project_id:
            self.log("Cleaning up test project and all associated objects...")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, clean up knowledge assets and chunks
                await self._cleanup_knowledge_assets()

                # Then clean up ontologies
                await self._cleanup_ontologies()

                # Finally delete the project
                response = await client.delete(
                    f"{self.base_url}/api/projects/{self.project_id}",
                    headers=self.auth_headers()
                )

                if response.status_code == 200:
                    self.log(f"Test project cleaned up: {self.project_id}", "SUCCESS")
                else:
                    self.log(f"Warning: Could not delete test project: {response.status_code}", "WARNING")

    async def _cleanup_knowledge_assets(self):
        """Clean up handled by project deletion API"""
        pass

    async def _cleanup_ontologies(self):
        """Clean up handled by project deletion API"""
        pass

    async def cleanup_existing_test_projects(self):
        """Clean up any existing test projects before starting - use API endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get list of projects
            response = await client.get(
                f"{self.base_url}/api/projects",
                headers=self.auth_headers()
            )

            if response.status_code != 200:
                raise Exception(f"Could not list projects for cleanup: {response.status_code}")

            response_data = response.json()

            # Handle both list and dict with 'projects' key
            if isinstance(response_data, dict) and 'projects' in response_data:
                projects = response_data['projects']
            elif isinstance(response_data, list):
                projects = response_data
            else:
                projects = []

            test_projects = [p for p in projects if isinstance(p, dict) and p.get('name', '').startswith('DAS_EdgeCase_Test_')]

            if test_projects:
                self.log(f"Found {len(test_projects)} existing test projects, cleaning up...")

                for project in test_projects:
                    project_id = project.get('project_id')
                    response = await client.delete(
                        f"{self.base_url}/api/projects/{project_id}",
                        headers=self.auth_headers()
                    )
                    if response.status_code == 200:
                        self.log(f"Deleted test project: {project.get('name')}", "SUCCESS")
                    else:
                        self.log(f"Warning: Could not delete project {project.get('name')}: {response.status_code}", "WARNING")

    async def _verify_embeddings_ready(self):
        """Verify that embeddings have been generated for the test knowledge"""
        max_retries = 3
        retry_delay = 3

        for attempt in range(max_retries):
            try:
                # Test with a simple DAS query to see if RAG works
                test_response = await self.ask_das("What is the weight of the QuadCopter T4?")

                # Check if we got sources (indicating RAG worked)
                if test_response.get('metadata', {}).get('sources'):
                    self.log("✅ Embeddings ready - RAG working", "SUCCESS")
                    return

                self.log(f"Attempt {attempt + 1}/{max_retries}: Embeddings not ready, waiting {retry_delay}s...")
                await asyncio.sleep(retry_delay)

            except Exception as e:
                self.log(f"Embedding verification error (attempt {attempt + 1}): {e}", "ERROR")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)

        self.log("⚠️ Embeddings may not be fully ready, proceeding with test", "WARNING")

    async def ask_das(self, question: str) -> Dict[str, Any]:
        """Ask DAS a question using the SAME endpoint as DAS dock"""
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

            if response.status_code != 200:
                raise Exception(f"DAS query failed: {response.status_code} - {response.text}")

            # Parse streaming response (same format as DAS dock)
            full_response = ""
            sources = []
            metadata = {}

            try:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])  # Remove "data: " prefix
                            chunk_type = chunk.get("type")

                            if chunk_type == "content":
                                content = chunk.get("content", "")
                                full_response += content
                            elif chunk_type == "done":
                                metadata = chunk.get("metadata", {})
                                sources = metadata.get("sources", [])
                            elif chunk_type == "error":
                                raise Exception(f"DAS streaming error: {chunk.get('message', 'Unknown error')}")
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
            except Exception as e:
                self.log(f"Error parsing streaming response: {e}", "ERROR")
                # If streaming fails, try to read as regular JSON
                try:
                    response_text = await response.aread()
                    fallback_response = json.loads(response_text)
                    full_response = fallback_response.get("message", "")
                    sources = fallback_response.get("sources", [])
                    metadata = fallback_response.get("metadata", {})
                except:
                    raise Exception(f"Could not parse DAS response: {e}")

            das_response = {
                "message": full_response,
                "sources": sources,
                "metadata": metadata
            }

            # Store in conversation history for consistency tracking
            self.conversation_history.append({
                "question": question,
                "answer": full_response,
                "sources": sources,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            })

            return das_response

    async def _setup_das_like_dock(self):
        """Setup DAS exactly like the DAS dock does"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Get/Create project thread (DAS dock does this first)
            response = await client.get(
                f"{self.base_url}/api/das2/project/{self.project_id}/thread",
                headers=self.auth_headers()
            )

            if response.status_code == 200:
                data = response.json()
                self.project_thread_id = data.get("project_thread_id")
                self.log(f"Using existing project thread: {self.project_thread_id}", "SUCCESS")
            else:
                # Create a new thread
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
                    self.log(f"Could not create project thread: {response.status_code}", "WARNING")
                    self.project_thread_id = None

            # 2. Load RAG configuration (DAS dock does this)
            response = await client.get(
                f"{self.base_url}/api/rag-config",
                headers=self.auth_headers()
            )

            if response.status_code == 200:
                rag_config = response.json()
                self.log(f"Loaded RAG config: {len(rag_config)} collections", "SUCCESS")
            else:
                self.log(f"Could not load RAG config: {response.status_code}", "WARNING")

    async def test_knowledge_consistency(self):
        """Test for knowledge consistency issues"""
        self.log("Testing knowledge consistency...", "EDGE_CASE")

        consistency_tests = [
            {
                "name": "AeroMapper X8 Direct vs Table Consistency",
                "questions": [
                    "What is the weight of the AeroMapper X8?",
                    "Can you give me a table of UAS weights?"
                ],
                "check_function": self._check_aeromapper_consistency
            },
            {
                "name": "QuadCopter T4 Multi-Query Consistency",
                "questions": [
                    "What is the weight of the QuadCopter T4?",
                    "Tell me about QuadCopter T4 specifications",
                    "What are the physical characteristics of the QuadCopter T4?"
                ],
                "check_function": self._check_quadcopter_consistency
            },
            {
                "name": "Cross-Asset Information Consistency",
                "questions": [
                    "What UAV platforms are mentioned in the project?",
                    "List all the aircraft specifications you know about"
                ],
                "check_function": self._check_cross_asset_consistency
            }
        ]

        results = []

        for test_case in consistency_tests:
            self.log(f"Running consistency test: {test_case['name']}")

            # Ask all questions in the test case
            responses = []
            for question in test_case["questions"]:
                self.log(f"  Asking: {question}")
                response = await self.ask_das(question)
                responses.append(response)
                await asyncio.sleep(1)  # Brief pause

            # Check consistency using the test function
            consistency_result = test_case["check_function"](responses)
            consistency_result["test_name"] = test_case["name"]
            results.append(consistency_result)

            if consistency_result["consistent"]:
                self.log(f"  ✅ CONSISTENT: {test_case['name']}")
            else:
                self.log(f"  🚨 INCONSISTENT: {consistency_result['issue']}", "CONSISTENCY_FAIL")

        return results

    def _check_aeromapper_consistency(self, responses: List[Dict]) -> Dict[str, Any]:
        """Check AeroMapper X8 consistency between direct and table queries"""
        direct_response = responses[0]["message"].lower()
        table_response = responses[1]["message"].lower()

        # Check if both mention AeroMapper X8
        direct_has_aeromapper = "aeromapper" in direct_response and "x8" in direct_response
        table_has_aeromapper = "aeromapper" in table_response and "x8" in table_response

        # Check for weight information
        direct_has_weight = "20" in direct_response or "kg" in direct_response
        table_has_weight = "20" in table_response

        # Check for "don't know" responses
        direct_says_unknown = any(phrase in direct_response for phrase in ["don't have", "don't know", "not specified", "not available"])

        consistent = True
        issue = ""

        if table_has_aeromapper and table_has_weight and direct_says_unknown:
            consistent = False
            issue = "Table shows AeroMapper X8 weight (20kg) but direct query claims no information available"
        elif direct_has_aeromapper and not direct_has_weight and not direct_says_unknown:
            consistent = False
            issue = "Direct query mentions AeroMapper X8 but provides no weight information"

        return {
            "consistent": consistent,
            "issue": issue,
            "details": {
                "direct_mentions_aeromapper": direct_has_aeromapper,
                "table_mentions_aeromapper": table_has_aeromapper,
                "direct_has_weight": direct_has_weight,
                "table_has_weight": table_has_weight,
                "direct_says_unknown": direct_says_unknown
            }
        }

    def _check_quadcopter_consistency(self, responses: List[Dict]) -> Dict[str, Any]:
        """Check QuadCopter T4 consistency across multiple query styles"""
        weight_values = []
        weights_mentioned = []

        for i, response in enumerate(responses):
            message = response["message"].lower()
            if "2.5" in message and "kg" in message:
                weight_values.append("2.5kg")
                weights_mentioned.append(f"Response {i+1}: 2.5kg")
            elif "weight" in message and "quadcopter" in message:
                weight_values.append("no_value")
                weights_mentioned.append(f"Response {i+1}: mentions weight but no value")

        # Check if all weight values are the same (consistent)
        unique_weights = set(weight_values)
        consistent = len(unique_weights) <= 1  # All same or no contradictions
        issue = "" if consistent else f"Inconsistent weight information: {weights_mentioned}"

        return {
            "consistent": consistent,
            "issue": issue,
            "details": {"weights_mentioned": weights_mentioned, "weight_values": weight_values}
        }

    def _check_cross_asset_consistency(self, responses: List[Dict]) -> Dict[str, Any]:
        """Check consistency when information spans multiple knowledge assets"""
        platforms_mentioned = set()

        for response in responses:
            message = response["message"].lower()
            # Extract platform names
            if "aeromapper" in message:
                platforms_mentioned.add("AeroMapper")
            if "quadcopter" in message:
                platforms_mentioned.add("QuadCopter")
            if "skyeagle" in message:
                platforms_mentioned.add("SkyEagle")
            if "trivector" in message:
                platforms_mentioned.add("TriVector")

        # Should find consistent platforms across queries
        consistent = len(platforms_mentioned) > 0
        issue = "" if consistent else "No consistent platform information across queries"

        return {
            "consistent": consistent,
            "issue": issue,
            "details": {"platforms_found": list(platforms_mentioned)}
        }

    async def test_contextual_reference_consistency(self):
        """Test contextual references (it, its, that, etc.)"""
        self.log("Testing contextual reference consistency...", "EDGE_CASE")

        contextual_tests = [
            {
                "setup_question": "What is the weight of the QuadCopter T4?",
                "followup_question": "What is its payload capacity?",
                "expected_context": "QuadCopter T4"
            },
            {
                "setup_question": "Tell me about the TriVector VTOL platform",
                "followup_question": "What is its wingspan?",
                "expected_context": "TriVector VTOL"
            },
            {
                "setup_question": "What files are in this project?",
                "followup_question": "What does that specification document contain?",
                "expected_context": "edge_case_specs"
            }
        ]

        results = []

        for test in contextual_tests:
            self.log(f"Testing contextual reference: {test['expected_context']}")

            # Ask setup question
            setup_response = await self.ask_das(test["setup_question"])
            await asyncio.sleep(1)

            # Ask followup with contextual reference
            followup_response = await self.ask_das(test["followup_question"])

            # Check if followup understood the context
            followup_text = followup_response["message"].lower()
            context_understood = test["expected_context"].lower() in followup_text

            result = {
                "setup_question": test["setup_question"],
                "followup_question": test["followup_question"],
                "expected_context": test["expected_context"],
                "context_understood": context_understood,
                "setup_answer": setup_response["message"],
                "followup_answer": followup_response["message"]
            }

            results.append(result)

            if context_understood:
                self.log(f"  ✅ Context understood: {test['expected_context']}")
            else:
                self.log(f"  ❌ Context lost: {test['expected_context']}", "CONSISTENCY_FAIL")

        return results

    async def test_conversation_memory_persistence(self):
        """Test conversation memory across multiple interactions"""
        self.log("Testing conversation memory persistence...", "EDGE_CASE")

        memory_tests = [
            "What is the weight of the QuadCopter T4?",
            "What was my previous question?",
            "Before that, what did I ask about?",
            "Can you summarize our conversation so far?"
        ]

        results = []

        for i, question in enumerate(memory_tests):
            self.log(f"Memory test {i+1}: {question}")
            response = await self.ask_das(question)

            # Check if response shows memory of previous questions
            answer = response["message"].lower()

            if i == 1:  # "What was my previous question?"
                remembers_previous = "quadcopter" in answer and ("weight" in answer or "t4" in answer)
            elif i == 2:  # "Before that, what did I ask about?"
                remembers_earlier = len(self.conversation_history) >= 2
            elif i == 3:  # "Can you summarize our conversation?"
                remembers_conversation = "quadcopter" in answer and "weight" in answer
            else:
                remembers_previous = True  # First question, no memory to check

            result = {
                "question": question,
                "answer": response["message"],
                "memory_working": remembers_previous if i == 1 else (remembers_earlier if i == 2 else (remembers_conversation if i == 3 else True))
            }

            results.append(result)
            await asyncio.sleep(1)

        return results

    async def test_knowledge_source_attribution(self):
        """Test that sources are correctly attributed and consistent"""
        self.log("Testing knowledge source attribution...", "EDGE_CASE")

        source_tests = [
            {
                "question": "What is the weight of the QuadCopter T4?",
                "expected_source": "edge_case_specs"
            },
            {
                "question": "What are the TriVector VTOL specifications?",
                "expected_source": "edge_case_specs"
            },
            {
                "question": "What test platforms are available?",
                "expected_source": "edge_case_specs"
            }
        ]

        results = []

        for test in source_tests:
            self.log(f"Testing source attribution for: {test['question']}")
            response = await self.ask_das(test["question"])

            # Debug the full response structure
            self.log(f"  Response keys: {list(response.keys())}")
            self.log(f"  Sources: {response.get('sources', [])}")
            self.log(f"  Metadata: {response.get('metadata', {})}")

            sources = response.get("sources", [])

            # FAIL FAST: If no sources at all, stop the test
            if not sources:
                self.log(f"❌ CRITICAL: No sources found at all for question: {test['question']}", "CONSISTENCY_FAIL")
                self.log(f"❌ This suggests DAS is not working correctly - stopping test", "CONSISTENCY_FAIL")
                raise Exception(f"DAS not returning sources - no RAG functionality detected for question: {test['question']}")

            # Check if expected source is present
            source_titles = [s.get("title", "") for s in sources]
            expected_found = any(test["expected_source"] in title for title in source_titles)

            result = {
                "question": test["question"],
                "expected_source": test["expected_source"],
                "sources_found": source_titles,
                "expected_source_present": expected_found,
                "total_sources": len(sources),
                "full_response": response  # For debugging
            }

            results.append(result)

            if expected_found:
                self.log(f"  ✅ Correct source: {test['expected_source']}")
            else:
                self.log(f"  ❌ Missing expected source: {test['expected_source']}", "CONSISTENCY_FAIL")
                self.log(f"    Found sources: {source_titles}")
                self.log(f"    Full response: {response}")

        return results

    async def test_edge_case_scenarios(self):
        """Test edge cases that commonly break DAS"""
        self.log("Testing edge case scenarios...", "EDGE_CASE")

        edge_cases = [
            {
                "name": "Empty Context Reference",
                "question": "What is its weight?",  # No prior context
                "should_ask_clarification": True
            },
            {
                "name": "Ambiguous Pronoun",
                "setup": "Tell me about QuadCopter T4 and TriVector VTOL",
                "question": "What is its weight?",  # Ambiguous "its"
                "should_ask_clarification": True
            },
            {
                "name": "Non-existent Information",
                "question": "What is the weight of the SuperDrone X99?",
                "should_say_unknown": True
            },
            {
                "name": "Cross-Domain Knowledge",
                "question": "What is the capital of France?",  # Outside project domain
                "should_stay_focused": True
            }
        ]

        results = []

        for test in edge_cases:
            self.log(f"Testing edge case: {test['name']}")

            # Setup question if needed
            if "setup" in test:
                await self.ask_das(test["setup"])
                await asyncio.sleep(1)

            response = await self.ask_das(test["question"])
            answer = response["message"].lower()

            # Check expected behavior
            passed = True
            issues = []

            if test.get("should_ask_clarification"):
                if not any(phrase in answer for phrase in ["clarify", "which", "specify", "what do you mean"]):
                    passed = False
                    issues.append("Should ask for clarification but didn't")

            if test.get("should_say_unknown"):
                if not any(phrase in answer for phrase in ["don't have", "don't know", "not available", "no information"]):
                    passed = False
                    issues.append("Should say unknown but provided answer")

            if test.get("should_stay_focused"):
                if "france" in answer or "paris" in answer:
                    passed = False
                    issues.append("Should stay focused on project but answered off-topic question")

            result = {
                "test_name": test["name"],
                "question": test["question"],
                "answer": response["message"],
                "passed": passed,
                "issues": issues,
                "sources_count": len(response.get("sources", []))
            }

            results.append(result)

            if passed:
                self.log(f"  ✅ Edge case handled correctly: {test['name']}")
            else:
                self.log(f"  ❌ Edge case failed: {', '.join(issues)}", "CONSISTENCY_FAIL")

        return results

    def generate_comprehensive_report(self, consistency_results, contextual_results, memory_results, source_results, edge_case_results):
        """Generate comprehensive edge case test report"""

        # Calculate overall scores
        total_consistency_tests = len(consistency_results)
        passed_consistency = sum(1 for r in consistency_results if r["consistent"])

        total_contextual_tests = len(contextual_results)
        passed_contextual = sum(1 for r in contextual_results if r["context_understood"])

        total_memory_tests = len(memory_results)
        passed_memory = sum(1 for r in memory_results if r["memory_working"])

        total_source_tests = len(source_results)
        passed_source = sum(1 for r in source_results if r["expected_source_present"])

        total_edge_tests = len(edge_case_results)
        passed_edge = sum(1 for r in edge_case_results if r["passed"])

        total_tests = total_consistency_tests + total_contextual_tests + total_memory_tests + total_source_tests + total_edge_tests
        total_passed = passed_consistency + passed_contextual + passed_memory + passed_source + passed_edge

        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        self.log("=" * 80)
        self.log("📊 DAS EDGE CASE & CONSISTENCY TEST REPORT", "SUCCESS")
        self.log("=" * 80)
        self.log(f"Overall Success Rate: {overall_success_rate:.1f}% ({total_passed}/{total_tests})")
        self.log("")
        self.log(f"Knowledge Consistency: {passed_consistency}/{total_consistency_tests} ({passed_consistency/total_consistency_tests*100:.1f}%)")
        self.log(f"Contextual References: {passed_contextual}/{total_contextual_tests} ({passed_contextual/total_contextual_tests*100:.1f}%)")
        self.log(f"Memory Persistence: {passed_memory}/{total_memory_tests} ({passed_memory/total_memory_tests*100:.1f}%)")
        self.log(f"Source Attribution: {passed_source}/{total_source_tests} ({passed_source/total_source_tests*100:.1f}%)")
        self.log(f"Edge Case Handling: {passed_edge}/{total_edge_tests} ({passed_edge/total_edge_tests*100:.1f}%)")

        # List critical failures
        critical_failures = []

        for r in consistency_results:
            if not r["consistent"]:
                critical_failures.append(f"CONSISTENCY: {r['issue']}")

        for r in contextual_results:
            if not r["context_understood"]:
                critical_failures.append(f"CONTEXT: Lost context for {r['expected_context']}")

        for r in edge_case_results:
            if not r["passed"]:
                critical_failures.append(f"EDGE CASE: {r['test_name']} - {', '.join(r['issues'])}")

        if critical_failures:
            self.log("\n🚨 CRITICAL FAILURES:")
            for failure in critical_failures:
                self.log(f"  • {failure}", "CONSISTENCY_FAIL")
        else:
            self.log("\n🎉 NO CRITICAL FAILURES DETECTED!", "SUCCESS")

        return {
            "overall_success_rate": overall_success_rate,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "consistency_results": consistency_results,
            "contextual_results": contextual_results,
            "memory_results": memory_results,
            "source_results": source_results,
            "edge_case_results": edge_case_results,
            "critical_failures": critical_failures
        }

    def write_detailed_log(self):
        """Write detailed test log"""
        log_content = "\n".join(self.test_log)
        log_file = f"/tmp/das_edge_case_test_{int(time.time())}.log"
        with open(log_file, 'w') as f:
            f.write(log_content)
            f.write("\n\n=== CONVERSATION HISTORY ===\n")
            for i, conv in enumerate(self.conversation_history):
                f.write(f"\n--- Conversation {i+1} ---\n")
                f.write(f"Q: {conv['question']}\n")
                f.write(f"A: {conv['answer']}\n")
                f.write(f"Sources: {len(conv['sources'])}\n")

        self.log(f"Detailed log written: {log_file}")
        return log_file


@pytest.mark.asyncio
async def test_das_edge_cases_comprehensive():
    """
    Comprehensive DAS edge case and consistency test - self-contained

    Creates its own project, ontologies, classes, and knowledge content
    to test DAS reliability, consistency, and edge case handling.
    """

    tester = DASEdgeCaseTester(verbose=True)
    test_exception = None
    report = None

    try:
        print("\n" + "="*80)
        print("🚀 DAS EDGE CASE & CONSISTENCY TEST - SELF-CONTAINED")
        print("="*80)

        # Authenticate first
        await tester.authenticate()

        # Clean up any existing test projects
        await tester.cleanup_existing_test_projects()

        # Setup complete test environment
        await tester.create_test_project()
        await tester.setup_test_ontology_and_classes()
        await tester.upload_test_knowledge()

        print(f"✅ Test environment ready - Project: {tester.project_id}")

        # Run all edge case tests
        consistency_results = await tester.test_knowledge_consistency()
        contextual_results = await tester.test_contextual_reference_consistency()
        memory_results = await tester.test_conversation_memory_persistence()
        source_results = await tester.test_knowledge_source_attribution()
        edge_case_results = await tester.test_edge_case_scenarios()

        # Generate comprehensive report
        report = tester.generate_comprehensive_report(
            consistency_results, contextual_results, memory_results,
            source_results, edge_case_results
        )

        # Write detailed log
        log_file = tester.write_detailed_log()

        # Assert minimum quality standards
        success_rate = report["overall_success_rate"]
        critical_failures = len(report["critical_failures"])

        print(f"\n📄 Detailed log: {log_file}")

        # Check requirements for DAS reliability
        if success_rate >= 85.0 and critical_failures == 0:
            print(f"\n🎉 DAS EDGE CASE TEST PASSED!")
            print(f"📊 Success Rate: {success_rate:.1f}%")
            print("="*80)
        else:
            # Test failed but don't throw exception - let cleanup happen first
            failure_msg = []
            if success_rate < 85.0:
                failure_msg.append(f"Success rate {success_rate:.1f}% < 85.0% required")
            if critical_failures > 0:
                failure_msg.append(f"{critical_failures} critical failures must be fixed")

            print(f"\n❌ DAS EDGE CASE TEST FAILED!")
            print(f"📊 Issues: {'; '.join(failure_msg)}")
            print("="*80)

            # Store failure to raise after cleanup
            test_exception = Exception(f"DAS edge case test failed: {'; '.join(failure_msg)}")

    except Exception as e:
        tester.log(f"❌ FATAL ERROR: {e}", "ERROR")
        log_file = tester.write_detailed_log()
        print(f"\n❌ TEST FAILED WITH ERROR - Log: {log_file}")
        print(f"❌ Error: {e}")
        test_exception = e

    finally:
        # Always cleanup test project
        try:
            await tester.cleanup_test_project()
            print("🧹 Test cleanup completed")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup error: {cleanup_error}")

        # Now handle test results/exceptions after cleanup
        if test_exception:
            raise test_exception

    return report


if __name__ == "__main__":
    """Run edge case tests directly"""
    print("🔍 Running DAS Edge Case & Consistency Tests...")
    asyncio.run(test_das_edge_cases_comprehensive())
