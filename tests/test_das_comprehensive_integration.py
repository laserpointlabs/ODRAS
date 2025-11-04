#!/usr/bin/env python3
"""
DAS Comprehensive Integration Test

This test creates a complete project workflow and validates DAS knowledge and context awareness:
1. Creates a new project
2. Creates an ontology (BSEO_V1) with classes
3. Uploads and processes knowledge files
4. Tests DAS understanding of:
   - Project information and context
   - Ontology and class structure
   - Knowledge asset content
   - Conversation thread memory
   - Event history awareness

This test simulates real user interactions, not mocks, to ensure end-to-end functionality.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any

import httpx
import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings


class DASIntegrationTester:
    """Comprehensive DAS integration tester that simulates real user workflows"""

    def __init__(self):
        self.settings = Settings()
        self.base_url = "http://localhost:8000"
        self.auth_token = None
        self.project_id = None
        self.ontology_iri = None
        self.test_data = {}

    async def authenticate(self):
        """Authenticate as das_service user"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=10.0
            )
            assert response.status_code == 200, f"Authentication failed: {response.text}"

            auth_data = response.json()
            self.auth_token = auth_data.get("token")
            assert self.auth_token, "No auth token received"

            print("✅ Authenticated successfully")

    def auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}"}

    async def create_test_project(self):
        """Create a new test project"""
        project_name = f"DAS_Test_Project_{int(time.time())}"

        async with httpx.AsyncClient() as client:
            # Create project
            response = await client.post(
                f"{self.base_url}/api/projects",
                headers=self.auth_headers(),
                json={
                    "name": project_name,
                    "description": "Test project for DAS integration testing with UAV specifications and systems engineering knowledge",
                    "domain": "aerospace-engineering",
                    "namespace_path": "test/das-integration"
                },
                timeout=30.0
            )
            assert response.status_code in [200, 201], f"Project creation failed: {response.text}"

            project_data = response.json()
            # Handle nested project structure
            if "project" in project_data:
                project_info = project_data["project"]
                self.project_id = project_info.get("project_id")
            else:
                self.project_id = project_data.get("project_id")
            assert self.project_id, "No project ID received"

            self.test_data["project"] = {
                "project_id": self.project_id,
                "name": project_name,
                "description": "Test project for DAS integration testing with UAV specifications and systems engineering knowledge",
                "domain": "aerospace-engineering"
            }

            print(f"✅ Created test project: {project_name} ({self.project_id})")

            # Wait for project thread to be created
            await asyncio.sleep(2)

    async def create_ontology_and_classes(self):
        """Create BSEO_V1 ontology with test classes"""
        async with httpx.AsyncClient() as client:
            # Create ontology using the same endpoint as the UI modal
            response = await client.post(
                f"{self.base_url}/api/ontologies",
                headers=self.auth_headers(),
                json={
                    "project": self.project_id,
                    "name": "BSEO_V1",
                    "label": "Basic Systems Engineering Ontology Version 1",
                    "is_reference": False  # Project-specific ontology
                },
                timeout=30.0
            )
            print(f"Ontology creation response: {response.status_code}")
            print(f"Response content: {response.text}")
            assert response.status_code == 200, f"Ontology creation failed: Status {response.status_code}, Response: {response.text}"

            ontology_data = response.json()
            self.ontology_iri = ontology_data.get("graphIri")
            assert self.ontology_iri, "No ontology IRI received"

            print(f"✅ Created BSEO_V1 ontology: {self.ontology_iri}")

            # Add test classes
            test_classes = [
                {
                    "name": "UAVPlatform",
                    "description": "Unmanned Aerial Vehicle Platform class representing different types of UAVs"
                },
                {
                    "name": "QuadCopter",
                    "description": "Quadcopter UAV with four rotors for vertical takeoff and landing"
                },
                {
                    "name": "FixedWingUAV",
                    "description": "Fixed-wing UAV for long-range missions and efficient flight"
                },
                {
                    "name": "VTOLPlatform",
                    "description": "Vertical Takeoff and Landing platform combining helicopter and airplane capabilities"
                }
            ]

            created_classes = []
            for class_info in test_classes:
                # Use the same endpoint as the UI
                response = await client.post(
                    f"{self.base_url}/api/ontology/classes?graph={self.ontology_iri}",
                    headers=self.auth_headers(),
                    json={
                        "name": f"Class_{class_info['name']}",  # Generate unique class name
                        "label": class_info['name'],
                        "comment": class_info['description']
                    },
                    timeout=30.0
                )
                assert response.status_code == 200, f"Class creation failed for {class_info['name']}: {response.text}"

                class_data = response.json()
                created_classes.append({
                    "name": class_info['name'],
                    "description": class_info['description'],
                    "response": class_data
                })
                print(f"✅ Created class: {class_info['name']}")

            self.test_data["ontology"] = {
                "ontology_iri": self.ontology_iri,
                "name": "BSEO_V1",
                "classes": created_classes
            }

            # Wait for ontology events to be processed
            await asyncio.sleep(2)

    async def upload_knowledge_content(self):
        """Upload and process knowledge content"""
        # Create test UAV specification content
        uav_content = """# UAV Specifications Document

## QuadCopter T4 Specifications

### Physical Characteristics
- **Weight**: 2.5 kg (5.5 lbs)
- **Payload Capacity**: 800g (1.76 lbs)
- **Dimensions**: 450mm x 450mm x 200mm
- **Rotor Diameter**: 15 inches
- **Battery**: 6000mAh LiPo

### Performance Specifications
- **Max Speed**: 65 km/h (40 mph)
- **Flight Time**: 28 minutes
- **Max Altitude**: 4000m AGL
- **Operating Temperature**: -10°C to +40°C
- **Wind Resistance**: Up to 12 m/s

## TriVector VTOL Platform

### Overview
The TriVector VTOL (Vertical Takeoff and Landing) platform represents next-generation UAV technology combining:
- **Vertical Capability**: Helicopter-style takeoff and landing
- **Forward Flight**: Fixed-wing efficiency for long-range missions
- **Hybrid Design**: Three-vector thrust system for optimal performance

### Technical Specifications
- **Weight**: 15.2 kg (33.5 lbs)
- **Payload Capacity**: 5.5 kg (12.1 lbs)
- **Wingspan**: 2.8m (9.2 ft)
- **Max Speed**: 180 km/h (112 mph)
- **Endurance**: 4.5 hours
- **Range**: 750 km

### Operational Capabilities
- **Surveillance**: High-resolution imaging and video
- **Cargo Delivery**: Precision payload deployment
- **Search and Rescue**: Extended range operations
- **Environmental Monitoring**: Long-duration data collection

## Systems Engineering Context

These UAV platforms demonstrate key systems engineering principles:
- **Requirements Traceability**: Each specification maps to operational requirements
- **Performance Optimization**: Balance between payload, endurance, and capability
- **Modular Design**: Interchangeable components for different mission profiles
- **Safety Systems**: Redundant flight controls and emergency procedures
"""

        async with httpx.AsyncClient() as client:
            # Upload knowledge file
            files = {
                'file': ('uav_specifications.md', uav_content, 'text/markdown')
            }
            data = {
                'project_id': self.project_id,
                'document_type': 'specification',
                'title': 'UAV Specifications',
                'description': 'Comprehensive UAV platform specifications for QuadCopter T4 and TriVector VTOL'
            }

            response = await client.post(
                f"{self.base_url}/api/files/upload",
                headers=self.auth_headers(),
                files=files,
                data=data,
                timeout=60.0
            )
            assert response.status_code == 200, f"Knowledge upload failed: {response.text}"

            upload_result = response.json()
            print(f"✅ Uploaded knowledge file: {upload_result.get('filename')}")

            self.test_data["knowledge"] = {
                "filename": "uav_specifications.md",
                "content_preview": uav_content[:200] + "...",
                "document_type": "specification"
            }

            # Wait for knowledge processing
            await asyncio.sleep(5)

    async def test_das_knowledge_questions(self):
        """Test DAS with comprehensive knowledge and context questions"""

        test_questions = [
            # Project awareness
            {
                "question": "Can you tell me about this project?",
                "expected_keywords": ["DAS_Test_Project", "aerospace-engineering", "UAV", "systems engineering"],
                "category": "project_awareness"
            },

            # Ontology awareness
            {
                "question": "What ontologies does this project have?",
                "expected_keywords": ["BSEO_V1", "Basic Systems Engineering Ontology"],
                "category": "ontology_awareness"
            },

            # Class structure awareness
            {
                "question": "Can you tell me what classes we have in our BSEO_V1 ontology?",
                "expected_keywords": ["UAVPlatform", "QuadCopter", "FixedWingUAV", "VTOLPlatform"],
                "category": "class_awareness"
            },

            # File awareness
            {
                "question": "What files are in this project?",
                "expected_keywords": ["uav_specifications.md", "specification", "UAV"],
                "category": "file_awareness"
            },

            # Specific knowledge content
            {
                "question": "What is the weight of the QuadCopter T4?",
                "expected_keywords": ["2.5 kg", "5.5 lbs", "QuadCopter T4"],
                "category": "knowledge_content"
            },

            # Related knowledge content
            {
                "question": "What is its payload capacity?",
                "expected_keywords": ["800g", "1.76 lbs", "payload"],
                "category": "contextual_knowledge"
            },

            # Complex knowledge query
            {
                "question": "Tell me about the TriVector VTOL platform",
                "expected_keywords": ["TriVector", "VTOL", "15.2 kg", "2.8m wingspan", "hybrid design"],
                "category": "detailed_knowledge"
            },

            # Conversation memory
            {
                "question": "What was the previous question I asked you?",
                "expected_keywords": ["TriVector", "VTOL", "platform", "previous"],
                "category": "conversation_memory"
            }
        ]

        results = []

        for i, test_case in enumerate(test_questions, 1):
            print(f"\n🔍 Testing Question {i}/{len(test_questions)}: {test_case['category']}")
            print(f"   Question: {test_case['question']}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/das/chat",
                    headers=self.auth_headers(),
                    json={
                        "message": test_case["question"],
                        "project_id": self.project_id
                    },
                    timeout=60.0
                )

                assert response.status_code == 200, f"DAS query failed: {response.text}"

                das_response = response.json()
                answer = das_response.get("message", "")

                # Check if expected keywords are present
                keywords_found = []
                keywords_missing = []

                for keyword in test_case["expected_keywords"]:
                    if keyword.lower() in answer.lower():
                        keywords_found.append(keyword)
                    else:
                        keywords_missing.append(keyword)

                success = len(keywords_missing) == 0
                score = len(keywords_found) / len(test_case["expected_keywords"]) * 100

                result = {
                    "question_num": i,
                    "category": test_case["category"],
                    "question": test_case["question"],
                    "answer": answer,
                    "expected_keywords": test_case["expected_keywords"],
                    "keywords_found": keywords_found,
                    "keywords_missing": keywords_missing,
                    "success": success,
                    "score": score,
                    "sources": das_response.get("sources", []),
                    "chunks_found": das_response.get("metadata", {}).get("chunks_found", 0)
                }

                results.append(result)

                print(f"   Score: {score:.1f}% ({len(keywords_found)}/{len(test_case['expected_keywords'])} keywords)")
                if keywords_missing:
                    print(f"   Missing: {keywords_missing}")
                if das_response.get("sources"):
                    print(f"   Sources: {len(das_response.get('sources', []))} knowledge sources used")

                # Brief pause between questions to simulate real interaction
                await asyncio.sleep(1)

        return results

    async def cleanup_test_project(self):
        """Clean up test project and resources"""
        if self.project_id:
            async with httpx.AsyncClient() as client:
                try:
                    # Delete project (this should cascade to ontologies and knowledge)
                    response = await client.delete(
                        f"{self.base_url}/api/projects/{self.project_id}",
                        headers=self.auth_headers(),
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        print(f"✅ Cleaned up test project: {self.project_id}")
                    else:
                        print(f"⚠️ Could not delete test project: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Cleanup error: {e}")

    def generate_test_report(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        average_score = sum(r["score"] for r in results) / total_tests if total_tests > 0 else 0

        # Group results by category
        by_category = {}
        for result in results:
            category = result["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)

        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_score": average_score,
                "timestamp": datetime.now().isoformat()
            },
            "project_info": self.test_data,
            "results_by_category": by_category,
            "detailed_results": results
        }

        return report


@pytest.mark.asyncio
async def test_das_comprehensive_integration():
    """
    Comprehensive DAS integration test that validates:
    - Project creation and awareness
    - Ontology and class management
    - Knowledge upload and processing
    - DAS context and memory capabilities
    """

    tester = DASIntegrationTester()

    try:
        print("\n" + "="*80)
        print("🚀 STARTING DAS COMPREHENSIVE INTEGRATION TEST")
        print("="*80)

        # Step 1: Authentication
        print("\n📋 Step 1: Authentication")
        await tester.authenticate()

        # Step 2: Create test project
        print("\n📋 Step 2: Project Creation")
        await tester.create_test_project()

        # Step 3: Create ontology and classes
        print("\n📋 Step 3: Ontology and Class Creation")
        await tester.create_ontology_and_classes()

        # Step 4: Upload knowledge content
        print("\n📋 Step 4: Knowledge Upload and Processing")
        await tester.upload_knowledge_content()

        # Step 5: Test DAS knowledge and awareness
        print("\n📋 Step 5: DAS Knowledge and Context Testing")
        results = await tester.test_das_knowledge_questions()

        # Step 6: Generate report
        print("\n📋 Step 6: Test Report Generation")
        report = tester.generate_test_report(results)

        # Print summary
        print("\n" + "="*80)
        print("📊 DAS INTEGRATION TEST RESULTS")
        print("="*80)

        summary = report["test_summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Average Score: {summary['average_score']:.1f}%")

        print(f"\n📁 Test Project: {tester.test_data['project']['name']}")
        print(f"🔗 Ontology: {tester.test_data['ontology']['name']} ({len(tester.test_data['ontology']['classes'])} classes)")
        print(f"📄 Knowledge: {tester.test_data['knowledge']['filename']}")

        # Print category results
        print("\n📋 Results by Category:")
        for category, cat_results in report["results_by_category"].items():
            cat_success = sum(1 for r in cat_results if r["success"])
            cat_total = len(cat_results)
            cat_score = sum(r["score"] for r in cat_results) / cat_total if cat_total > 0 else 0
            print(f"  {category}: {cat_success}/{cat_total} ({cat_score:.1f}%)")

        # Print failed tests
        failed_tests = [r for r in results if not r["success"]]
        if failed_tests:
            print("\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  Q{test['question_num']}: {test['question']}")
                print(f"    Missing keywords: {test['keywords_missing']}")

        # Assert overall success
        assert summary["success_rate"] >= 75.0, f"DAS integration test failed: {summary['success_rate']:.1f}% success rate (minimum 75% required)"

        print("\n🎉 DAS COMPREHENSIVE INTEGRATION TEST PASSED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ DAS Integration Test Failed: {e}")
        raise

    finally:
        # Cleanup
        print("\n🧹 Cleaning up test resources...")
        await tester.cleanup_test_project()


if __name__ == "__main__":
    """Run the test directly for development"""
    asyncio.run(test_das_comprehensive_integration())
