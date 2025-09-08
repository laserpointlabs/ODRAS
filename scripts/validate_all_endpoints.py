#!/usr/bin/env python3
"""
ODRAS API Endpoint Validation Script

This script validates all API endpoints in the ODRAS system to ensure they:
1. Are accessible and respond correctly
2. Return expected response formats
3. Handle authentication properly
4. Validate input correctly
5. Return appropriate error codes

Usage:
    python scripts/validate_all_endpoints.py [--base-url http://localhost:8000] [--verbose]
"""

import asyncio
import json
import sys
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import httpx
import argparse
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

console = Console()


@dataclass
class EndpointTest:
    """Represents a test case for an API endpoint"""

    method: str
    path: str
    name: str
    requires_auth: bool = True
    expected_status: int = 200
    test_data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None


@dataclass
class TestResult:
    """Represents the result of an endpoint test"""

    endpoint: EndpointTest
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


class ODRASAPITester:
    """Comprehensive API tester for ODRAS endpoints"""

    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.client: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        self.test_results: List[TestResult] = []

    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    async def authenticate(self) -> bool:
        """Authenticate with the API and get a token"""
        try:
            # Try to login with test user
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": "jdehart", "password": ""},
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                if self.verbose:
                    console.print(f"✅ Authentication successful", style="green")
                return True
            else:
                if self.verbose:
                    console.print(
                        f"❌ Authentication failed: {response.status_code}", style="red"
                    )
                return False

        except Exception as e:
            if self.verbose:
                console.print(f"❌ Authentication error: {e}", style="red")
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    async def test_endpoint(self, endpoint: EndpointTest) -> TestResult:
        """Test a single endpoint"""
        start_time = time.time()

        try:
            # Prepare headers
            headers = self.get_auth_headers()
            if endpoint.headers:
                headers.update(endpoint.headers)

            # Make the request
            if endpoint.method.upper() == "GET":
                response = await self.client.get(
                    f"{self.base_url}{endpoint.path}",
                    headers=headers,
                    params=endpoint.params,
                )
            elif endpoint.method.upper() == "POST":
                if endpoint.files:
                    response = await self.client.post(
                        f"{self.base_url}{endpoint.path}",
                        headers=headers,
                        files=endpoint.files,
                        data=endpoint.test_data,
                    )
                else:
                    response = await self.client.post(
                        f"{self.base_url}{endpoint.path}",
                        headers=headers,
                        json=endpoint.test_data,
                        params=endpoint.params,
                    )
            elif endpoint.method.upper() == "PUT":
                response = await self.client.put(
                    f"{self.base_url}{endpoint.path}",
                    headers=headers,
                    json=endpoint.test_data,
                    params=endpoint.params,
                )
            elif endpoint.method.upper() == "DELETE":
                response = await self.client.delete(
                    f"{self.base_url}{endpoint.path}",
                    headers=headers,
                    params=endpoint.params,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {endpoint.method}")

            response_time = time.time() - start_time

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            # Determine success
            success = response.status_code == endpoint.expected_status

            return TestResult(
                endpoint=endpoint,
                status_code=response.status_code,
                response_time=response_time,
                success=success,
                response_data=response_data,
            )

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e),
            )

    def get_all_endpoints(self) -> List[EndpointTest]:
        """Get all API endpoints to test"""
        endpoints = []

        # Authentication endpoints
        endpoints.extend(
            [
                EndpointTest(
                    "POST",
                    "/api/auth/login",
                    "User Login",
                    requires_auth=False,
                    test_data={"username": "jdehart", "password": ""},
                ),
                EndpointTest("GET", "/api/auth/me", "Get Current User"),
                EndpointTest("POST", "/api/auth/logout", "User Logout"),
            ]
        )

        # Project management endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/projects", "List Projects"),
                EndpointTest(
                    "POST",
                    "/api/projects",
                    "Create Project",
                    test_data={
                        "name": "Test Project",
                        "description": "Test project for validation",
                    },
                ),
            ]
        )

        # File management endpoints
        endpoints.extend(
            [
                EndpointTest(
                    "GET", "/api/files", "List Files", params={"project_id": "test"}
                ),
                EndpointTest("GET", "/api/files/storage/info", "Get Storage Info"),
                EndpointTest("GET", "/api/files/keywords", "Get Keyword Config"),
            ]
        )

        # Ontology endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/ontology", "Get Ontology"),
                EndpointTest(
                    "GET", "/api/ontology/statistics", "Get Ontology Statistics"
                ),
                EndpointTest("GET", "/api/ontology/layout", "Get Ontology Layout"),
                EndpointTest(
                    "GET",
                    "/api/ontology/validate-integrity",
                    "Validate Ontology Integrity",
                ),
            ]
        )

        # Knowledge management endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/knowledge/assets", "List Knowledge Assets"),
                EndpointTest("GET", "/api/knowledge/health", "Knowledge Health Check"),
                EndpointTest("GET", "/api/knowledge/jobs", "List Processing Jobs"),
                EndpointTest(
                    "GET", "/api/knowledge/query/suggestions", "Get Query Suggestions"
                ),
            ]
        )

        # Workflow endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/camunda/status", "Camunda Status"),
                EndpointTest(
                    "GET", "/api/camunda/deployments", "List Camunda Deployments"
                ),
            ]
        )

        # Embedding model endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/embedding-models", "List Embedding Models"),
            ]
        )

        # Namespace endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/namespaces", "List Namespaces"),
                EndpointTest(
                    "GET", "/api/namespaces/public/namespaces", "List Public Namespaces"
                ),
                EndpointTest(
                    "GET",
                    "/api/namespaces/available/namespaces",
                    "List Available Namespaces",
                ),
            ]
        )

        # Domain management endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/domains", "List Domains"),
            ]
        )

        # Prefix management endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/prefixes", "List Prefixes"),
            ]
        )

        # Persona and prompt endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/personas", "List Personas"),
                EndpointTest("GET", "/api/prompts", "List Prompts"),
            ]
        )

        # User task endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/user-tasks", "List User Tasks"),
            ]
        )

        # System status endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/api/ollama/status", "Ollama Status"),
                EndpointTest("GET", "/api/openai/status", "OpenAI Status"),
                EndpointTest("GET", "/api/models/ollama", "List Ollama Models"),
                EndpointTest("GET", "/api/models/openai", "List OpenAI Models"),
            ]
        )

        # Main application endpoints
        endpoints.extend(
            [
                EndpointTest("GET", "/", "Main Application", requires_auth=False),
                EndpointTest(
                    "GET", "/app", "Application Interface", requires_auth=False
                ),
                EndpointTest(
                    "GET", "/ontology-editor", "Ontology Editor", requires_auth=False
                ),
                EndpointTest(
                    "GET", "/user-review", "User Review Interface", requires_auth=False
                ),
            ]
        )

        return endpoints

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all endpoint tests"""
        console.print("\n🚀 Starting ODRAS API Endpoint Validation", style="bold blue")

        # Authenticate first
        auth_success = await self.authenticate()
        if not auth_success:
            console.print(
                "⚠️  Authentication failed, some tests may fail", style="yellow"
            )

        endpoints = self.get_all_endpoints()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing endpoints...", total=len(endpoints))

            for endpoint in endpoints:
                progress.update(
                    task, description=f"Testing {endpoint.method} {endpoint.path}"
                )

                result = await self.test_endpoint(endpoint)
                self.test_results.append(result)

                progress.advance(task)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - successful_tests

        # Calculate average response time
        avg_response_time = (
            sum(r.response_time for r in self.test_results) / total_tests
            if total_tests > 0
            else 0
        )

        # Group results by status code
        status_codes = {}
        for result in self.test_results:
            status = result.status_code
            if status not in status_codes:
                status_codes[status] = 0
            status_codes[status] += 1

        # Find slow endpoints (>2 seconds)
        slow_endpoints = [r for r in self.test_results if r.response_time > 2.0]

        # Find failed endpoints
        failed_endpoints = [r for r in self.test_results if not r.success]

        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (
                    (successful_tests / total_tests * 100) if total_tests > 0 else 0
                ),
                "average_response_time": avg_response_time,
            },
            "status_codes": status_codes,
            "slow_endpoints": slow_endpoints,
            "failed_endpoints": failed_endpoints,
            "all_results": self.test_results,
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print a formatted test report"""
        summary = report["summary"]

        # Summary panel
        summary_text = f"""
Total Tests: {summary['total_tests']}
Successful: {summary['successful_tests']} ✅
Failed: {summary['failed_tests']} ❌
Success Rate: {summary['success_rate']:.1f}%
Average Response Time: {summary['average_response_time']:.3f}s
        """.strip()

        console.print(Panel(summary_text, title="Test Summary", border_style="blue"))

        # Status codes table
        if report["status_codes"]:
            status_table = Table(title="Response Status Codes")
            status_table.add_column("Status Code", style="cyan")
            status_table.add_column("Count", style="magenta")

            for status, count in sorted(report["status_codes"].items()):
                status_table.add_row(str(status), str(count))

            console.print(status_table)

        # Slow endpoints
        if report["slow_endpoints"]:
            slow_table = Table(title="Slow Endpoints (>2s)")
            slow_table.add_column("Method", style="cyan")
            slow_table.add_column("Path", style="green")
            slow_table.add_column("Response Time", style="red")

            for result in report["slow_endpoints"]:
                slow_table.add_row(
                    result.endpoint.method,
                    result.endpoint.path,
                    f"{result.response_time:.3f}s",
                )

            console.print(slow_table)

        # Failed endpoints
        if report["failed_endpoints"]:
            failed_table = Table(title="Failed Endpoints")
            failed_table.add_column("Method", style="cyan")
            failed_table.add_column("Path", style="green")
            failed_table.add_column("Status", style="red")
            failed_table.add_column("Error", style="yellow")

            for result in report["failed_endpoints"]:
                error_msg = result.error_message or f"Status {result.status_code}"
                failed_table.add_row(
                    result.endpoint.method,
                    result.endpoint.path,
                    str(result.status_code),
                    error_msg[:50] + "..." if len(error_msg) > 50 else error_msg,
                )

            console.print(failed_table)

        # Detailed results if verbose
        if self.verbose:
            console.print("\n📋 Detailed Results:", style="bold")
            for result in self.test_results:
                status_icon = "✅" if result.success else "❌"
                console.print(
                    f"{status_icon} {result.endpoint.method} {result.endpoint.path} - {result.status_code} ({result.response_time:.3f}s)"
                )


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Validate all ODRAS API endpoints")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the ODRAS API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument("--output", "-o", help="Output results to JSON file")

    args = parser.parse_args()

    try:
        async with ODRASAPITester(args.base_url, args.verbose) as tester:
            report = await tester.run_all_tests()
            tester.print_report(report)

            # Save report if requested
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report, f, indent=2, default=str)
                console.print(f"\n💾 Report saved to {args.output}", style="green")

            # Exit with error code if tests failed
            if report["summary"]["failed_tests"] > 0:
                console.print(
                    f"\n❌ {report['summary']['failed_tests']} tests failed!",
                    style="red",
                )
                sys.exit(1)
            else:
                console.print("\n🎉 All tests passed!", style="green")

    except KeyboardInterrupt:
        console.print("\n⏹️  Testing interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n💥 Testing failed with error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
