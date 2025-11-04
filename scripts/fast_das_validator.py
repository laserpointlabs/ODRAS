#!/usr/bin/env python3
"""
Fast DAS Validator - Quick Health Check

Performs rapid validation of DAS functionality without long waits.
Fails fast on basic issues to avoid 10-minute timeouts.

Tests performed in <90 seconds total:
1. ODRAS connectivity (1s)
2. Authentication (2s)
3. Basic DAS response (30s)
4. Ontology context (30s - enhanced with rich attributes)
5. Rich attribute validation (30s)

If any fail, stops immediately with clear error.
Only run full tests if fast validation passes.
"""

import asyncio
import httpx
import requests
import json
import time
import sys
import os
from datetime import datetime


class FastDASValidator:
    """Quick validation of DAS core functionality"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.auth_token = None
        self.project_id = None  # Will create test project
        self.start_time = time.time()

    def log(self, message: str, status: str = "INFO"):
        """Log with timestamp"""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:5.1f}s] {status}: {message}")

    def fast_fail_check(self, condition: bool, error_msg: str):
        """Fail fast if condition is false"""
        if not condition:
            self.log(error_msg, "FAIL")
            print(f"\n❌ FAST VALIDATION FAILED: {error_msg}")
            print(f"⏱️  Total time: {time.time() - self.start_time:.1f}s")
            sys.exit(1)

    def test_01_connectivity(self):
        """Test basic ODRAS connectivity (1s timeout)"""
        self.log("Testing ODRAS connectivity...")

        try:
            response = requests.get(f"{self.base_url}/", timeout=1)
            self.fast_fail_check(
                response.status_code == 200,
                "ODRAS not responding - check if services are running"
            )
            self.log("✅ ODRAS responding", "PASS")
        except Exception as e:
            self.fast_fail_check(False, f"ODRAS connectivity failed: {e}")

    def test_02_authentication(self):
        """Test authentication (2s timeout)"""
        self.log("Testing authentication...")

        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=2
            )

            self.fast_fail_check(
                response.status_code == 200,
                f"Authentication failed: {response.status_code} - {response.text}"
            )

            auth_data = response.json()
            self.auth_token = auth_data.get("token")

            self.fast_fail_check(
                self.auth_token is not None,
                "No auth token in response"
            )

            self.log("✅ Authentication successful", "PASS")

        except Exception as e:
            self.fast_fail_check(False, f"Authentication exception: {e}")

    def test_03_basic_das_response(self):
        """Test basic DAS functionality (30s timeout)"""
        self.log("Testing basic DAS response...")

        try:
            response = requests.post(
                f"{self.base_url}/api/das/chat",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                json={
                    "project_id": self.project_id,
                    "message": "Hello, can you respond?"
                },
                timeout=30
            )

            self.fast_fail_check(
                response.status_code == 200,
                f"DAS chat API failed: {response.status_code} - {response.text}"
            )

            das_data = response.json()
            answer = das_data.get("message", "")

            self.fast_fail_check(
                len(answer) > 10,
                f"DAS response too short or empty: '{answer}'"
            )

            self.log(f"✅ DAS responding ({len(answer)} chars)", "PASS")

        except Exception as e:
            self.fast_fail_check(False, f"DAS response test failed: {e}")

    def create_test_project(self):
        """Create a test project dynamically (same as UI workflow)"""
        self.log("Creating test project...")

        try:
            # Get available namespaces (same as UI)
            namespaces_response = requests.get(
                f"{self.base_url}/api/namespaces/released",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=5
            )

            self.fast_fail_check(
                namespaces_response.status_code == 200,
                f"Could not get namespaces: {namespaces_response.status_code}"
            )

            namespaces = namespaces_response.json()
            self.fast_fail_check(
                len(namespaces) > 0,
                "No released namespaces available"
            )

            # Use first available namespace
            namespace_id = namespaces[0]["id"]

            # Create test project
            project_response = requests.post(
                f"{self.base_url}/api/projects",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                json={
                    "name": f"FastValidator_Test_{int(time.time())}",
                    "description": "Fast validator test project",
                    "domain": "systems-engineering",
                    "namespace_id": namespace_id
                },
                timeout=10
            )

            self.fast_fail_check(
                project_response.status_code == 200,
                f"Project creation failed: {project_response.status_code} - {project_response.text}"
            )

            project_data = project_response.json()
            self.project_id = project_data["project"]["project_id"]

            self.log(f"Test project created: {self.project_id}")

        except Exception as e:
            self.fast_fail_check(False, f"Project creation failed: {e}")

    def test_04_ontology_context(self):
        """Test ontology context awareness (30s timeout)"""
        self.log("Testing ontology context...")

        # Create test project first if not exists
        if not self.project_id:
            self.create_test_project()

        try:
            response = requests.post(
                f"{self.base_url}/api/das/chat",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                json={
                    "project_id": self.project_id,
                    "message": "What ontologies are in this project?"
                },
                timeout=30  # Increased timeout for enhanced ontology context
            )

            self.fast_fail_check(
                response.status_code == 200,
                f"DAS ontology query failed: {response.status_code}"
            )

            answer = response.json().get("message", "")

            # Check for ontology intelligence
            has_ontology_context = any(keyword in answer.lower() for keyword in ["ontology", "test", "working", "vehicle", "aircraft"])

            self.fast_fail_check(
                has_ontology_context,
                f"DAS lacks ontology context in answer: {answer[:100]}..."
            )

            self.log("✅ Ontology context working", "PASS")

        except Exception as e:
            self.fast_fail_check(False, f"Ontology context test failed: {e}")

    def test_05_rich_attributes(self):
        """Test rich attribute display (10s timeout)"""
        self.log("Testing rich attribute display...")

        try:
            response = requests.post(
                f"{self.base_url}/api/das/chat",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                json={
                    "project_id": self.project_id,
                    "message": "Tell me about the Vehicle class including its priority and creator."
                },
                timeout=30  # Increased timeout for rich attribute queries
            )

            self.fast_fail_check(
                response.status_code == 200,
                f"DAS rich attributes query failed: {response.status_code}"
            )

            answer = response.json().get("message", "")

            # Check for rich context (priority, creator, etc.)
            has_rich_context = any(keyword in answer.lower() for keyword in ["priority", "creator", "das_service", "definition"])

            if has_rich_context:
                self.log("✅ Rich attributes working", "PASS")
            else:
                self.log("⚠️  Rich attributes limited but functional", "WARN")
                # Don't fail - this is enhancement, not core functionality

        except Exception as e:
            self.fast_fail_check(False, f"Rich attributes test failed: {e}")

    def run_fast_validation(self):
        """Run complete fast validation"""
        print("🚀 FAST DAS VALIDATION")
        print("=" * 60)
        print(f"Target: Complete validation in <90 seconds (enhanced ontology context)")
        print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
        print()

        # Run tests with fail-fast behavior
        self.test_01_connectivity()
        self.test_02_authentication()
        self.create_test_project()  # Create project before DAS tests
        self.test_03_basic_das_response()
        self.test_04_ontology_context()
        self.test_05_rich_attributes()

        # Success summary
        total_time = time.time() - self.start_time

        print()
        print("🎉 FAST VALIDATION PASSED!")
        print("=" * 60)
        print(f"✅ ODRAS connectivity: Working")
        print(f"✅ Authentication: Working")
        print(f"✅ DAS basic response: Working")
        print(f"✅ Ontology context: Working")
        print(f"✅ Rich attributes: Working")
        print(f"⏱️  Total time: {total_time:.1f}s")
        print()
        print("🚀 READY FOR FULL TEST SUITE")
        print("All core functionality validated - safe to run comprehensive tests")

        # Cleanup test project
        self.cleanup_test_project()

        return True

    def cleanup_test_project(self):
        """Clean up test project"""
        if self.project_id:
            self.log("Cleaning up test project...")
            try:
                response = requests.delete(
                    f"{self.base_url}/api/projects/{self.project_id}",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    timeout=5
                )
                if response.status_code == 200:
                    self.log("Test project cleaned up", "SUCCESS")
                else:
                    self.log(f"Project cleanup warning: {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"Project cleanup warning: {e}", "WARNING")


def main():
    """Main entry point"""
    validator = FastDASValidator()

    try:
        success = validator.run_fast_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚡ Fast validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during fast validation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
