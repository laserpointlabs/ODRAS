#!/usr/bin/env python3
"""
Comprehensive API Endpoint Validation Script

This script discovers and tests all API endpoints in the ODRAS application,
providing detailed coverage analysis and validation results.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class APIEndpointValidator:
    """Validates all API endpoints in the ODRAS application."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.app = app
        self.endpoints: List[Dict] = []
        self.test_results: Dict[str, Dict] = {}
        self.auth_token: Optional[str] = None

    def discover_endpoints(self) -> List[Dict]:
        """Discover all API endpoints from the FastAPI app."""
        endpoints = []

        for route in self.app.routes:
            if isinstance(route, APIRoute):
                # Extract endpoint information
                endpoint_info = {
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": route.name,
                    "endpoint": route.endpoint,
                    "tags": getattr(route, "tags", []),
                    "summary": getattr(route, "summary", ""),
                    "description": getattr(route, "description", ""),
                    "requires_auth": self._requires_auth(route),
                    "is_public": self._is_public_endpoint(route.path),
                }
                endpoints.append(endpoint_info)

        # Sort endpoints by path for better organization
        endpoints.sort(key=lambda x: x["path"])
        self.endpoints = endpoints
        return endpoints

    def _requires_auth(self, route) -> bool:
        """Check if an endpoint requires authentication."""
        # Check if the endpoint has Depends(get_user) or similar auth dependencies
        if hasattr(route, "dependant"):
            for dep in route.dependant.dependencies:
                if hasattr(dep, "call"):
                    if "get_user" in str(dep.call) or "get_admin_user" in str(dep.call):
                        return True
        return False

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if an endpoint is public (no auth required)."""
        public_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/login",
            "/api/camunda/status",
            "/api/ollama/status",
            "/api/openai/status",
            "/api/embedding-models",
            "/api/namespaces/public/namespaces",
            "/api/domains/public",
        }

        # Check exact matches
        if path in public_paths:
            return True

        # Check pattern matches
        for public_path in public_paths:
            if path.startswith(public_path) and public_path != "/":
                return True

        return False

    async def authenticate(self) -> bool:
        """Authenticate and get a token for protected endpoints."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": "jdehart", "password": "jdehart123!"},
                )

                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data.get("access_token")
                    logger.info("✅ Authentication successful")
                    return True
                else:
                    logger.error(
                        f"❌ Authentication failed: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    async def test_endpoint(self, endpoint: Dict) -> Dict:
        """Test a single endpoint."""
        path = endpoint["path"]
        methods = endpoint["methods"]
        requires_auth = endpoint["requires_auth"]

        results = {
            "path": path,
            "methods": methods,
            "requires_auth": requires_auth,
            "test_results": {},
            "overall_status": "unknown",
        }

        # Skip non-HTTP methods
        http_methods = [m for m in methods if m in ["GET", "POST", "PUT", "DELETE", "PATCH"]]
        if not http_methods:
            results["overall_status"] = "skipped"
            return results

        # Test each HTTP method
        for method in http_methods:
            method_result = await self._test_method(path, method, requires_auth)
            results["test_results"][method] = method_result

        # Determine overall status
        if any(result["status"] == "success" for result in results["test_results"].values()):
            results["overall_status"] = "success"
        elif any(result["status"] == "error" for result in results["test_results"].values()):
            results["overall_status"] = "error"
        else:
            results["overall_status"] = "skipped"

        return results

    async def _test_method(self, path: str, method: str, requires_auth: bool) -> Dict:
        """Test a specific HTTP method on an endpoint."""
        url = f"{self.base_url}{path}"

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if requires_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Prepare request data based on method and path
        json_data = self._get_test_data(path, method)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=json_data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=json_data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=json_data)
                else:
                    return {"status": "skipped", "reason": f"Unsupported method: {method}"}

                # Analyze response
                if response.status_code < 400:
                    return {
                        "status": "success",
                        "status_code": response.status_code,
                        "response_type": "success",
                    }
                elif response.status_code == 401:
                    return {
                        "status": "auth_required",
                        "status_code": response.status_code,
                        "response_type": "authentication_required",
                    }
                elif response.status_code == 404:
                    return {
                        "status": "not_found",
                        "status_code": response.status_code,
                        "response_type": "endpoint_not_found",
                    }
                else:
                    return {
                        "status": "error",
                        "status_code": response.status_code,
                        "response_type": "client_error",
                        "error_detail": response.text[:200],
                    }

        except httpx.TimeoutException:
            return {"status": "timeout", "response_type": "timeout_error"}
        except Exception as e:
            return {"status": "error", "response_type": "connection_error", "error_detail": str(e)}

    def _get_test_data(self, path: str, method: str) -> Optional[Dict]:
        """Generate appropriate test data for POST/PUT/PATCH requests."""
        # Skip GET and DELETE methods
        if method in ["GET", "DELETE"]:
            return None

        # Generate test data based on endpoint path
        if "/api/users" in path and method in ["POST", "PUT"]:
            return {
                "username": "test_user",
                "display_name": "Test User",
                "password": "test_password123!",
                "is_admin": False,
                "is_active": True,
            }
        elif "/api/projects" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Project",
                "description": "Test project description",
                "domain": "test_domain",
            }
        elif "/api/namespaces" in path and method in ["POST", "PUT"]:
            return {
                "prefix": "test",
                "namespace_uri": "http://example.com/test/",
                "description": "Test namespace",
            }
        elif "/api/domains" in path and method in ["POST", "PUT"]:
            return {"domain": "test_domain", "description": "Test domain description"}
        elif "/api/personas" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Persona",
                "description": "Test persona description",
                "system_prompt": "You are a test persona.",
                "is_active": True,
            }
        elif "/api/prompts" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Prompt",
                "description": "Test prompt description",
                "prompt_template": "Test prompt template: {input}",
                "is_active": True,
            }
        elif "/api/auth/login" in path:
            return {"username": "jdehart", "password": "jdehart123!"}
        elif "/api/users/me/password" in path:
            return {"old_password": "jdehart123!", "new_password": "new_password123!"}
        else:
            # Generic test data
            return {"test": "data"}

    async def run_validation(self) -> Dict:
        """Run comprehensive validation of all endpoints."""
        logger.info("🔍 Starting comprehensive API endpoint validation...")

        # Discover all endpoints
        logger.info("📋 Discovering API endpoints...")
        endpoints = self.discover_endpoints()
        logger.info(f"Found {len(endpoints)} endpoints")

        # Authenticate for protected endpoints
        logger.info("🔐 Authenticating for protected endpoints...")
        auth_success = await self.authenticate()
        if not auth_success:
            logger.warning("⚠️ Authentication failed - some tests may be skipped")

        # Test all endpoints
        logger.info("🧪 Testing all endpoints...")
        test_results = []

        for i, endpoint in enumerate(endpoints, 1):
            logger.info(
                f"Testing {i}/{len(endpoints)}: {endpoint['path']} [{', '.join(endpoint['methods'])}]"
            )
            result = await self.test_endpoint(endpoint)
            test_results.append(result)

        # Generate summary
        summary = self._generate_summary(test_results)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_endpoints": len(endpoints),
            "test_results": test_results,
            "summary": summary,
        }

    def _generate_summary(self, test_results: List[Dict]) -> Dict:
        """Generate a summary of test results."""
        total_endpoints = len(test_results)
        successful_endpoints = sum(1 for r in test_results if r["overall_status"] == "success")
        error_endpoints = sum(1 for r in test_results if r["overall_status"] == "error")
        skipped_endpoints = sum(1 for r in test_results if r["overall_status"] == "skipped")

        # Count by method
        method_counts = {}
        for result in test_results:
            for method, method_result in result["test_results"].items():
                if method not in method_counts:
                    method_counts[method] = {"success": 0, "error": 0, "skipped": 0}
                method_counts[method][method_result["status"]] += 1

        # Count by authentication requirement
        auth_required = sum(1 for r in test_results if r["requires_auth"])
        public_endpoints = sum(1 for r in test_results if not r["requires_auth"])

        return {
            "total_endpoints": total_endpoints,
            "successful_endpoints": successful_endpoints,
            "error_endpoints": error_endpoints,
            "skipped_endpoints": skipped_endpoints,
            "success_rate": (
                f"{(successful_endpoints / total_endpoints * 100):.1f}%"
                if total_endpoints > 0
                else "0%"
            ),
            "auth_required_endpoints": auth_required,
            "public_endpoints": public_endpoints,
            "method_breakdown": method_counts,
        }

    def print_results(self, results: Dict):
        """Print validation results in a formatted way."""
        print("\n" + "=" * 80)
        print("🔍 ODRAS API ENDPOINT VALIDATION RESULTS")
        print("=" * 80)

        summary = results["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Endpoints: {summary['total_endpoints']}")
        print(f"   ✅ Successful: {summary['successful_endpoints']}")
        print(f"   ❌ Errors: {summary['error_endpoints']}")
        print(f"   ⏭️ Skipped: {summary['skipped_endpoints']}")
        print(f"   📈 Success Rate: {summary['success_rate']}")
        print(f"   🔐 Auth Required: {summary['auth_required_endpoints']}")
        print(f"   🌐 Public: {summary['public_endpoints']}")

        print(f"\n📋 METHOD BREAKDOWN:")
        for method, counts in summary["method_breakdown"].items():
            total = sum(counts.values())
            success_rate = f"{(counts['success'] / total * 100):.1f}%" if total > 0 else "0%"
            print(f"   {method}: {counts['success']}/{total} successful ({success_rate})")

        print(f"\n🔍 DETAILED RESULTS:")
        for result in results["test_results"]:
            status_icon = (
                "✅"
                if result["overall_status"] == "success"
                else "❌" if result["overall_status"] == "error" else "⏭️"
            )
            auth_icon = "🔐" if result["requires_auth"] else "🌐"
            print(f"   {status_icon} {auth_icon} {result['path']} [{', '.join(result['methods'])}]")

            for method, method_result in result["test_results"].items():
                method_status = method_result["status"]
                method_icon = (
                    "✅"
                    if method_status == "success"
                    else "❌" if method_status == "error" else "⏭️"
                )
                print(f"      {method_icon} {method}: {method_status}")
                if method_status == "error" and "error_detail" in method_result:
                    print(f"         Error: {method_result['error_detail'][:100]}...")


async def main():
    """Main function to run the API endpoint validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate all ODRAS API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--output", help="Output file for detailed results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    validator = APIEndpointValidator(args.base_url)

    try:
        results = await validator.run_validation()
        validator.print_results(results)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Detailed results saved to: {args.output}")

        # Exit with error code if there are failures
        if results["summary"]["error_endpoints"] > 0:
            print(f"\n❌ Validation completed with {results['summary']['error_endpoints']} errors")
            sys.exit(1)
        else:
            print(f"\n✅ Validation completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
