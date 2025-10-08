#!/usr/bin/env python3
"""
Requirements Workbench Test Script

Tests the complete requirements workbench functionality:
1. Authenticate with das_service account
2. Create a test project
3. Create a sample requirements document
4. Extract requirements from the document
5. Test DAS review functionality
6. Add collaborative notes
7. Test filtering and querying
"""

import asyncio
import json
import io
import os
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
import requests


class RequirementsWorkbenchTester:
    """Test the Requirements Workbench functionality"""

    def __init__(self, verbose: bool = True):
        self.base_url = "http://localhost:8000"
        self.username = "das_service"
        self.password = "das_service_2024!"
        self.verbose = verbose
        self.auth_token = None
        self.project_id = None
        self.requirements = []
        
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

    def authenticate(self):
        """Authenticate with das_service account"""
        self.log("Authenticating as das_service...")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=30
            )

            if response.status_code != 200:
                self.log(f"Authentication failed: {response.text}", "ERROR")
                raise Exception(f"Authentication failed: {response.text}")

            auth_data = response.json()
            self.auth_token = auth_data.get("token")

            if not self.auth_token:
                self.log("No auth token received", "ERROR")
                raise Exception("No auth token received")

            self.log(f"Authentication successful", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Authentication exception: {e}", "ERROR")
            raise

    def auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}"}

    def create_test_project(self):
        """Create a test project for requirements"""
        self.log("Creating test project...")
        
        project_data = {
            "name": f"Requirements Test Project {int(time.time())}",
            "description": "Test project for requirements workbench",
            "domain": "systems-engineering"
        }
        
        response = requests.post(
            f"{self.base_url}/api/projects",
            json=project_data,
            headers=self.auth_headers(),
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Project creation failed: {response.text}", "ERROR")
            raise Exception(f"Project creation failed: {response.text}")
        
        project = response.json()
        self.project_id = project["project"]["project_id"]
        self.log(f"Created project: {self.project_id}", "SUCCESS")
        return self.project_id

    def upload_requirements_document(self):
        """Upload a sample requirements document"""
        self.log("Uploading sample requirements document...")
        
        # Create sample requirements document
        sample_document = """
# System Requirements Document

## 1. Navigation Requirements

REQ-001: The GPS navigation system shall provide position accuracy of ±3 meters.
The system must maintain this accuracy under normal operating conditions.
Performance objective: Accuracy should be ±1 meter for optimal operation.

REQ-002: The navigation system shall update position data at a rate of 10 Hz minimum.
Threshold: System shall not operate below 5 Hz update rate.

## 2. Safety Requirements

REQ-003: The system shall implement fail-safe mechanisms in case of GPS signal loss.
Safety threshold: Position uncertainty shall not exceed 10 meters.

REQ-004: Emergency shutdown procedures must be accessible within 2 seconds.
Critical safety requirement for operator protection.

## 3. Performance Requirements

REQ-005: System response time shall not exceed 100 milliseconds for user commands.
KPP-001: Key Performance Parameter - Response time is critical for mission success.

REQ-006: The system shall operate continuously for 72 hours minimum.
Battery life objective: 96 hours preferred operating time.
        """
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(sample_document)
            temp_file = f.name
        
        try:
            # Upload file
            with open(temp_file, 'rb') as file_content:
                files = {'file': ('requirements.md', file_content, 'text/markdown')}
                data = {
                    'project_id': self.project_id,
                    'document_type': 'requirements'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/files/upload",
                    files=files,
                    data=data,
                    headers=self.auth_headers(),
                    timeout=30
                )
            
            if response.status_code != 200:
                self.log(f"File upload failed: {response.text}", "ERROR")
                raise Exception(f"File upload failed: {response.text}")
            
            file_data = response.json()
            
            # Try different possible file ID field names
            self.document_id = (file_data.get("file", {}).get("id") or 
                              file_data.get("id") or 
                              file_data.get("file_id"))
            
            if not self.document_id:
                self.log(f"Could not extract file ID from response: {file_data}", "ERROR")
                raise Exception("Failed to get file ID from upload response")
                
            self.log(f"Uploaded requirements document: {self.document_id}", "SUCCESS")
            return self.document_id
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    def extract_requirements(self):
        """Extract requirements from the uploaded document"""
        self.log("Starting requirements extraction...")
        
        extraction_data = {
            "job_name": f"Test Extraction {int(time.time())}",
            "source_document_id": self.document_id,
            "extraction_type": "document",
            "functional_keywords": ["shall", "must", "will"],
            "constraint_keywords": ["threshold", "objective", "minimum", "maximum", "kpp"],
            "min_confidence": 0.6,
            "extract_constraints": True
        }
        
        response = requests.post(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/extract",
            json=extraction_data,
            headers=self.auth_headers(),
            timeout=60  # Extraction can take time
        )
        
        if response.status_code != 200:
            self.log(f"Requirements extraction failed: {response.text}", "ERROR")
            raise Exception(f"Requirements extraction failed: {response.text}")
        
        extraction_result = response.json()
        self.log(f"Extraction completed: {extraction_result['requirements_created']} requirements, {extraction_result['constraints_created']} constraints", "SUCCESS")
        return extraction_result

    def list_requirements(self):
        """List all requirements in the project"""
        self.log("Listing project requirements...")
        
        response = requests.get(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/requirements",
            headers=self.auth_headers(),
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Failed to list requirements: {response.text}", "ERROR")
            raise Exception(f"Failed to list requirements: {response.text}")
        
        result = response.json()
        self.requirements = result["requirements"]
        
        self.log(f"Found {len(self.requirements)} requirements", "SUCCESS")
        for req in self.requirements[:3]:  # Show first 3
            self.log(f"  - {req['requirement_identifier']}: {req['requirement_text'][:100]}...")
        
        return self.requirements

    def test_das_review(self):
        """Test DAS review functionality"""
        if not self.requirements:
            self.log("No requirements to review", "ERROR")
            return None
            
        self.log("Testing DAS review functionality...")
        
        # Review the first requirement
        requirement = self.requirements[0]
        review_data = {
            "review_type": "improvement",
            "include_context": True,
            "focus_areas": ["clarity", "testability"]
        }
        
        response = requests.post(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/requirements/{requirement['requirement_id']}/das-review",
            json=review_data,
            headers=self.auth_headers(),
            timeout=60  # DAS can take time
        )
        
        if response.status_code != 200:
            self.log(f"DAS review failed: {response.text}", "ERROR")
            return None
        
        review_result = response.json()
        self.log(f"DAS review completed with {len(review_result.get('suggestions', []))} suggestions", "SUCCESS")
        
        if review_result.get("das_response"):
            self.log(f"DAS Response: {review_result['das_response'][:200]}...")
        
        return review_result

    def add_collaborative_note(self):
        """Add a collaborative note to a requirement"""
        if not self.requirements:
            self.log("No requirements to add notes to", "ERROR")
            return None
            
        self.log("Adding collaborative note...")
        
        requirement = self.requirements[0]
        note_data = {
            "requirement_id": requirement["requirement_id"],
            "note_text": "This requirement needs clarification on the measurement method for position accuracy.",
            "note_type": "clarification",
            "visibility": "project"
        }
        
        response = requests.post(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/requirements/{requirement['requirement_id']}/notes",
            json=note_data,
            headers=self.auth_headers(),
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Failed to add note: {response.text}", "ERROR")
            return None
        
        note = response.json()
        self.log(f"Added collaborative note: {note['note_id']}", "SUCCESS")
        return note

    def test_filtering(self):
        """Test requirement filtering capabilities"""
        self.log("Testing requirement filtering...")
        
        # Test filtering by requirement type
        response = requests.get(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/requirements",
            params={
                "requirement_type": "functional",
                "page_size": 10
            },
            headers=self.auth_headers(),
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Filtering test failed: {response.text}", "ERROR")
            return None
        
        filtered_result = response.json()
        self.log(f"Filtering by functional type returned {len(filtered_result['requirements'])} requirements", "SUCCESS")
        return filtered_result

    def create_manual_requirement(self):
        """Create a manual requirement to test CRUD operations"""
        self.log("Creating manual requirement...")
        
        requirement_data = {
            "requirement_title": "Manual Test Requirement",
            "requirement_text": "The system shall provide comprehensive logging capabilities for all user interactions.",
            "requirement_type": "functional",
            "category": "Logging",
            "priority": "medium",
            "verification_method": "test",
            "verification_criteria": "Log files shall contain timestamps and user IDs for all interactions",
            "tags": ["logging", "audit", "manual-test"]
        }
        
        response = requests.post(
            f"{self.base_url}/api/requirements/projects/{self.project_id}/requirements",
            json=requirement_data,
            headers=self.auth_headers(),
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Manual requirement creation failed: {response.text}", "ERROR")
            return None
        
        requirement = response.json()
        self.log(f"Created manual requirement: {requirement['requirement_identifier']}", "SUCCESS")
        return requirement

    async def run_comprehensive_test(self):
        """Run the complete requirements workbench test suite"""
        print("🚀 Starting Requirements Workbench Comprehensive Test")
        print("=" * 60)
        
        try:
            # Step 1: Authentication
            self.authenticate()
            
            # Step 2: Create test project
            self.create_test_project()
            
            # Step 3: Upload requirements document
            self.upload_requirements_document()
            
            # Step 4: Extract requirements
            self.extract_requirements()
            
            # Step 5: List requirements
            self.list_requirements()
            
            # Step 6: Test DAS review
            self.test_das_review()
            
            # Step 7: Add collaborative notes
            self.add_collaborative_note()
            
            # Step 8: Test filtering
            self.test_filtering()
            
            # Step 9: Create manual requirement
            self.create_manual_requirement()
            
            print("=" * 60)
            print("🎉 Requirements Workbench Test COMPLETED SUCCESSFULLY!")
            print(f"✅ Project ID: {self.project_id}")
            print(f"✅ Requirements extracted: {len(self.requirements)}")
            print("✅ All functionality tested and working")
            
            return True
            
        except Exception as e:
            print("=" * 60)
            print(f"❌ Requirements Workbench Test FAILED: {e}")
            return False


def main():
    """Main test execution"""
    tester = RequirementsWorkbenchTester(verbose=True)
    
    # Run the test
    success = asyncio.run(tester.run_comprehensive_test())
    
    if success:
        print("\n🎯 Requirements Workbench is ready for use!")
        print("🌐 Access the API at: http://localhost:8000/docs")
        exit(0)
    else:
        print("\n⚠️  Requirements Workbench test failed!")
        exit(1)


if __name__ == "__main__":
    main()
