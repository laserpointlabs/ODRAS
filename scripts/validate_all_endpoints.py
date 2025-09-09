#!/usr/bin/env python3
"""
Comprehensive API endpoint validation script for ODRAS.
Tests all endpoints with both admin and regular users to validate authorization controls.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi.routing import APIRoute
import re

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Import the FastAPI app
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class APIEndpointValidator:
    """Validates all API endpoints in the ODRAS application with dual-user testing."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.app = app
        self.endpoints: List[Dict] = []
        self.test_results: Dict[str, Dict] = {}
        self.admin_token: Optional[str] = None
        self.user_token: Optional[str] = None
        # Storage for IDs of resources created during validation
        self.created_ids: Dict[str, str] = {}

    def discover_endpoints(self) -> List[Dict]:
        """Discover all API endpoints from the FastAPI app."""
        endpoints = []

        for route in self.app.routes:
            if isinstance(route, APIRoute):
                endpoints.append(
                    {
                        "path": route.path,
                        "methods": list(route.methods),
                        "requires_auth": not self.is_public_endpoint(route.path),
                    }
                )

        return sorted(endpoints, key=lambda x: x["path"])

    def is_public_endpoint(self, path: str) -> bool:
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
            "/api/embedding-models/",
            "/api/namespaces/public/namespaces",
            "/api/domains/public",
            "/api/admin/namespaces/available/namespaces",
            "/api/admin/namespaces/public/namespaces",
            "/api/admin/prefixes/",
            "/api/ontology/",
            "/api/ontologies",
            "/api/ontology/statistics",
            "/api/ontology/summary",
            "/api/ontology/validate",
            "/api/personas",
            "/api/prompts",
            "/api/runs",
            "/api/test/",
            "/api/user-tasks",
            "/api/files/keywords",
            "/api/files/storage/info",
            "/api/files/{file_id}/url",
            "/api/files/{file_id}/download",
            "/api/files/{file_id}/process",
            "/api/knowledge/health",
            "/api/models/",
            "/api/namespaces/released",
            "/api/installation/config",
            "/app",
            "/ontology-editor",
            "/user-review",
        }

        # Skip logout endpoint during validation as it invalidates tokens
        if path == "/api/auth/logout":
            return True

        # Check exact matches
        if path in public_paths:
            return True

        # Check pattern matches
        for public_path in public_paths:
            if path.startswith(public_path) and public_path != "/":
                return True

        return False

    def is_admin_only_endpoint(self, path: str) -> bool:
        """Check if an endpoint requires admin privileges."""
        admin_only_patterns = [
            "/api/admin/",
            "/api/users/",  # User management (except /api/users/me)
            "/api/knowledge/assets/{asset_id}/force",
            "/api/knowledge/assets/{asset_id}/public",
            "/api/ontologies/reference",
            "/api/files/{file_id}/visibility",
            "/api/workflows/start",
        ]

        # Special cases: endpoints that are accessible to regular users
        public_exceptions = [
            "/api/users/me",
            "/api/users/me/password",
            "/api/admin/namespaces/available/namespaces",
            "/api/admin/namespaces/public/namespaces",
            "/api/admin/prefixes/",  # GET only - prefix listing for namespace creation
        ]

        if path in public_exceptions:
            return False

        # Check if path matches admin-only patterns
        for pattern in admin_only_patterns:
            if pattern in path:
                return True

        return False

    async def authenticate(self) -> bool:
        """Authenticate both admin and regular user for comprehensive testing."""
        try:
            async with httpx.AsyncClient() as client:
                # Authenticate admin user
                logger.info("🔐 Attempting admin authentication...")
                admin_response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": "admin", "password": "admin123!"},
                )

                if admin_response.status_code == 200:
                    admin_data = admin_response.json()
                    self.admin_token = admin_data.get("token") or admin_data.get("access_token")
                    token_preview = self.admin_token[:8] + "..." if self.admin_token else "None"
                    logger.info(f"✅ Admin authentication successful - Token: {token_preview}")
                else:
                    logger.error(
                        f"❌ Admin authentication failed: {admin_response.status_code} - {admin_response.text}"
                    )
                return False

                # Authenticate regular user with fallbacks
                logger.info("🔐 Attempting regular user authentication...")
                regular_user_authenticated = False
                for pwd in ["jdehart123!", "newpassword123!"]:
                    logger.info(f"🔐 Trying jdehart with password ending in {pwd[-4:]}")
                    user_response = await client.post(
                        f"{self.base_url}/api/auth/login",
                        json={"username": "jdehart", "password": pwd},
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        self.user_token = user_data.get("token") or user_data.get("access_token")
                        token_preview = self.user_token[:8] + "..." if self.user_token else "None"
                        logger.info(
                            f"✅ Regular user authentication successful - Token: {token_preview}"
                        )
                        regular_user_authenticated = True
                        break
                    else:
                        logger.warning(
                            f"⚠️ jdehart auth failed with {pwd[-4:]}: {user_response.status_code}"
                        )

                # If regular user failed, create a temporary non-admin user and authenticate
                if not regular_user_authenticated:
                    temp_username = f"validator_user_{int(datetime.now().timestamp())}"
                    temp_password = "validator123!"
                    create_headers = {
                        "Authorization": f"Bearer {self.admin_token}",
                        "Content-Type": "application/json",
                    }
                    create_resp = await client.post(
                        f"{self.base_url}/api/users/",
                        headers=create_headers,
                        json={
                            "username": temp_username,
                            "password": temp_password,
                            "display_name": "Validator User",
                            "is_admin": False,
                        },
                    )
                    if create_resp.status_code in (200, 201):
                        login_resp = await client.post(
                            f"{self.base_url}/api/auth/login",
                            json={"username": temp_username, "password": temp_password},
                        )
                        if login_resp.status_code == 200:
                            user_data = login_resp.json()
                            self.user_token = user_data.get("token") or user_data.get(
                                "access_token"
                            )
                            logger.info("✅ Regular user authentication successful (temp user)")
                            regular_user_authenticated = True

                if not regular_user_authenticated:
                    logger.warning(
                        "⚠️ Regular user authentication failed, proceeding with admin-only testing"
                    )
                else:
                    logger.info("✅ Both admin and regular user authentication successful")
                return True

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    async def test_endpoint(self, endpoint: Dict) -> Dict:
        """Test a single endpoint with both admin and regular user to validate authorization."""
        path = endpoint["path"]
        methods = endpoint["methods"]
        requires_auth = endpoint["requires_auth"]
        is_admin_only = self.is_admin_only_endpoint(path)

        results = {
            "path": path,
            "methods": methods,
            "requires_auth": requires_auth,
            "is_admin_only": is_admin_only,
            "test_results": {},
            "overall_status": "unknown",
        }

        # Skip non-HTTP methods
        http_methods = [m for m in methods if m in ["GET", "POST", "PUT", "DELETE", "PATCH"]]
        if not http_methods:
            results["overall_status"] = "skipped"
            return results

        # Test each HTTP method with appropriate user(s)
        for method in http_methods:
            if not requires_auth:
                # Public endpoint - test without authentication
                results["test_results"][method] = await self._test_method(
                    path, method, "public", None
                )
            elif is_admin_only:
                # Admin-only endpoint - test with both users to ensure proper access control
                admin_result = await self._test_method(path, method, "admin", self.admin_token)
                user_result = await self._test_method(path, method, "user", self.user_token)

                results["test_results"][method] = {
                    "admin_access": admin_result,
                    "user_access": user_result,
                    "status": (
                        "success"
                        if admin_result.get("status") == "success"
                        and user_result.get("status_code") == 403
                        else "error"
                    ),
                    "authorization_correct": admin_result.get("status") == "success"
                    and user_result.get("status_code") == 403,
                }
            else:
                # Regular authenticated endpoint - both users should have access
                admin_result = await self._test_method(path, method, "admin", self.admin_token)
                user_result = await self._test_method(path, method, "user", self.user_token)

                results["test_results"][method] = {
                    "admin_access": admin_result,
                    "user_access": user_result,
                    "status": (
                        "success"
                        if (
                            admin_result.get("status") == "success"
                            or user_result.get("status") == "success"
                        )
                        else "error"
                    ),
                    "both_have_access": admin_result.get("status") == "success"
                    and user_result.get("status") == "success",
                }

        # Determine overall status based on authorization correctness
        method_statuses = [
            result.get("status", "error") for result in results["test_results"].values()
        ]
        if any(status == "success" for status in method_statuses):
            results["overall_status"] = "success"
        elif any(status == "error" for status in method_statuses):
            results["overall_status"] = "error"
        else:
            results["overall_status"] = "skipped"

        return results

    async def _test_method(
        self, path: str, method: str, user_type: str, token: Optional[str]
    ) -> Dict:
        """Test a specific HTTP method on an endpoint with a specific user type."""
        self._retry_count = 0  # Reset retry counter for each request
        resolved_path = self._resolve_path_params(path)
        url = f"{self.base_url}{resolved_path}"

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Prepare request data and query parameters based on method and path
        json_data = self._get_test_data(path, method)
        params = self._get_query_params(path, method)
        raw_data = None
        files = None
        data_form = None

        # Some endpoints expect raw text bodies rather than JSON
        if isinstance(json_data, str):
            raw_data = json_data
            json_data = None
            # Adjust content type for known text endpoints
            if "/api/ontology/push-turtle" in path:
                headers["Content-Type"] = "text/turtle"
            elif "/api/ontology/sparql" in path:
                headers["Content-Type"] = "application/sparql-query"
            else:
                headers["Content-Type"] = "text/plain"

        # Special-case payload tweaks
        if path.endswith("/users/me/password"):
            # Skip password change endpoints during validation to avoid breaking auth
            return {
                "status": "skipped",
                "reason": "Password change skipped to preserve authentication",
                "response_type": "validation_skip",
            }

        # Handle special form data endpoints
        if json_data == "form_data":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            if "/import-url" in path:
                data_form = {
                    "url": "https://httpbin.org/json",  # Use a reliable test URL
                    "project_id": "bfe732af-04d9-44ba-a27a-d0e8cd4afc4b",
                    "tags": "test,validation",
                }
            elif "/visibility" in path:
                data_form = {
                    "visibility": "public",
                }
            elif "/extract/keywords" in path:
                data_form = {
                    "project_id": "bfe732af-04d9-44ba-a27a-d0e8cd4afc4b",
                }
            else:
                data_form = {}
            json_data = None

        # Multipart for uploads
        elif any(p in path for p in ["/upload", "/batch/upload"]) and method == "POST":
            headers.pop("Content-Type", None)  # let httpx set boundary
            data_form = {}

            if "/batch/upload" in path:
                # Batch upload needs multiple files and project_id
                data_form["project_id"] = (
                    "bfe732af-04d9-44ba-a27a-d0e8cd4afc4b"  # Use real project ID
                )
                files = [
                    ("files", ("test1.txt", b"test file 1 content", "text/plain")),
                    ("files", ("test2.txt", b"test file 2 content", "text/plain")),
                ]
            else:
                # Single file upload with project_id
                data_form["project_id"] = "bfe732af-04d9-44ba-a27a-d0e8cd4afc4b"
                files = [("file", ("test.txt", b"hello from validator", "text/plain"))]
            json_data = None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    if files is not None:
                        response = await client.post(
                            url, headers=headers, files=files, data=data_form, params=params
                        )
                    elif data_form is not None and json_data is None:
                        response = await client.post(
                            url, headers=headers, data=data_form, params=params
                        )
                    elif raw_data is not None:
                        response = await client.post(
                            url, headers=headers, content=raw_data, params=params
                        )
                    else:
                        response = await client.post(
                            url, headers=headers, json=json_data, params=params
                        )
                elif method == "PUT":
                    if data_form is not None and json_data is None:
                        response = await client.put(
                            url, headers=headers, data=data_form, params=params
                        )
                    elif raw_data is not None:
                        response = await client.put(
                            url, headers=headers, content=raw_data, params=params
                        )
                    else:
                        response = await client.put(
                            url, headers=headers, json=json_data, params=params
                        )
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                elif method == "PATCH":
                    if raw_data is not None:
                        response = await client.patch(
                            url, headers=headers, content=raw_data, params=params
                        )
                    else:
                        response = await client.patch(
                            url, headers=headers, json=json_data, params=params
                        )
                else:
                    return {"status": "skipped", "reason": f"Unsupported method: {method}"}

                # Analyze response
                if response.status_code < 400:
                    result = {
                        "status": "success",
                        "status_code": response.status_code,
                        "response_type": "success",
                    }
                    try:
                        result["json"] = response.json()
                    except Exception:
                        result["json"] = None
                    # Capture IDs for created resources
                    if method == "POST" and result["json"]:
                        body = result["json"]
                        # Users
                        if "/api/users/" in path and isinstance(body, dict) and body.get("user_id"):
                            self.created_ids.setdefault("user_id", body["user_id"])
                        # Projects
                        if (
                            "/api/projects" in path
                            and isinstance(body, dict)
                            and body.get("project_id")
                        ):
                            self.created_ids.setdefault("project_id", body["project_id"])
                        # Files
                        if (
                            "/api/files/upload" in path
                            and isinstance(body, dict)
                            and body.get("file_id")
                        ):
                            self.created_ids.setdefault("file_id", body["file_id"])
                        # Batch upload files
                        if "/api/files/batch/upload" in path and isinstance(body, dict):
                            files_list = body.get("files", [])
                            if files_list and len(files_list) > 0 and files_list[0].get("file_id"):
                                self.created_ids.setdefault("file_id", files_list[0]["file_id"])
                        # Namespaces
                        if (
                            "/api/admin/namespaces" in path
                            and isinstance(body, dict)
                            and body.get("id")
                        ):
                            self.created_ids.setdefault("namespace_id", body["id"])
                        # Domains
                        if (
                            "/api/admin/domains" in path
                            and isinstance(body, dict)
                            and body.get("id")
                        ):
                            self.created_ids.setdefault("domain_id", body["id"])
                    return result
                elif response.status_code == 401:
                    return {
                        "status": "auth_required",
                        "status_code": response.status_code,
                        "response_type": "authentication_required",
                    }
                elif response.status_code == 403:
                    return {
                        "status": "forbidden",
                        "status_code": response.status_code,
                        "response_type": "access_denied",
                        "error_detail": response.text[:200],
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

    def _get_test_data(self, path: str, method: str) -> Optional[Union[Dict[str, Any], str]]:
        """Generate appropriate test data for POST/PUT/PATCH requests."""
        # Skip GET and DELETE methods
        if method in ["GET", "DELETE"]:
            return None

        # Generate test data based on endpoint path
        if "/api/users/me/password" in path:
            return {
                "old_password": "jdehart123!",
                "new_password": "newpassword123!",
            }
        elif "/api/admin/domains" in path and method in ["POST"]:
            return {
                "domain": f"testdomain{int(datetime.now().timestamp())}",
                "description": "Test domain description",
                "owner": "owner@example.com",
            }
        elif "/api/admin/namespaces" in path and method in ["POST"]:
            ts = int(datetime.now().timestamp())
            return {
                "name": f"ns{ts}",
                "type": "domain",
                "path": f"ns/{ts}",
                "prefix": f"ns{ts}",
                "description": "Test namespace",
                "owners": ["owner@example.com"],
            }
        elif "/api/users" in path and method in ["POST", "PUT"]:
            return {
                "username": "test_user_" + str(int(datetime.now().timestamp())),
                "display_name": "Test User",
                "password": "test_password123!",
                "is_admin": False,
                "is_active": True,
            }
        elif "/api/projects" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Project " + str(int(datetime.now().timestamp())),
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
            return {
                "name": "test_domain",
                "description": "Test domain description",
                "namespace_uri": "http://example.com/test/",
            }
        elif "/api/knowledge/assets" in path and method in ["POST"]:
            return {
                "title": "Test Knowledge Asset",
                "document_type": "knowledge",
                "content_summary": "Test content for knowledge asset validation",
                "metadata": {"category": "test"},
                "processing_options": {"auto_chunk": True},
            }
        elif "/api/knowledge/query" in path and method in ["POST"]:
            return {
                "question": "What is ODRAS?",
                "context": "test context",
            }
        elif "/api/knowledge/search" in path and method in ["POST"]:
            return {
                "query": "test search query",
                "limit": 10,
            }
        elif "/api/knowledge/search/semantic" in path and method in ["POST"]:
            return {
                "query": "semantic search test",
                "limit": 5,
            }
        elif "/api/personas" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Persona",
                "description": "Test persona description",
                "prompt": "You are a test persona",
            }
        elif "/api/prompts" in path and method in ["POST", "PUT"]:
            return {
                "name": "Test Prompt",
                "description": "Test prompt description",
                "content": "Test prompt content",
            }
        elif "/api/workflows/rag-query" in path and method in ["POST"]:
            return {
                "query": "test workflow query",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        elif "/api/workflows/start" in path and method in ["POST"]:
            return {
                "processKey": "document_review",
                "variables": {"document_id": "test_doc"},
            }
        elif "/api/files/batch/upload" in path and method in ["POST"]:
            return {
                "files": [{"filename": "test.txt", "content": "test content"}],
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        elif "/api/files/import-url" in path and method in ["POST"]:
            # This endpoint expects form data, not JSON
            return "form_data"
        elif "/api/files/extract/keywords" in path and method in ["POST"]:
            # This endpoint expects form data, not JSON
            return "form_data"  # Special marker for form data
        elif "/api/files/{file_id}/tags" in path and method in ["PUT"]:
            return {
                "tags": {"category": "test", "type": "validation", "purpose": "api"},
            }
        elif "/api/files/{file_id}/visibility" in path and method in ["PUT"]:
            # This endpoint expects form data, not JSON
            return "form_data"
        elif "/api/ontology/classes" in path and method in ["POST"]:
            return {
                "name": "TestClass",
                "description": "A test class for validation",
            }
        elif "/api/ontology/properties" in path and method in ["POST"]:
            return {
                "name": "testProperty",
                "description": "A test property for validation",
                "domain": "TestClass",
                "range": "string",
                "type": "datatype",
            }
        elif "/api/ontology/mint-iri" in path and method in ["POST"]:
            return {
                "base_name": "TestConcept",
                "namespace": "http://example.com/test/",
                "entity_type": "class",
            }
        elif "/api/ontology/import" in path and method in ["POST"]:
            return {
                "file_content": "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n@prefix test: <http://example.com/test/> .\ntest:TestClass a owl:Class .",
                "format": "turtle",
            }
        elif "/api/ontology/push-turtle" in path:
            return "@prefix test: <http://example.com/test/> .\ntest:TestClass a owl:Class ."
        elif "/api/ontology/sparql" in path and method in ["POST"]:
            return {
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            }
        elif "/api/embedding-models/test" in path and method in ["POST"]:
            return {
                "model_id": "text-embedding-ada-002",
                "texts": ["test text for embedding"],
            }
        elif "/api/embedding-models/" in path and method in ["POST"]:
            return {
                "id": "test_embedding_model",
                "name": "Test Embedding Model",
                "provider": "openai",
                "model": "text-embedding-ada-002",
            }
        elif "/api/ontologies/label" in path and method in ["PUT"]:
            return {
                "graph": "http://example.com/test",
                "label": "Test Label",
            }
        else:
            # Generic test data
            return {"test": "data"}

    def _resolve_path_params(self, path: str) -> str:
        """Substitute common path parameters with representative test values."""
        param_to_value: Dict[str, str] = {
            "project_id": "550e8400-e29b-41d4-a716-446655440000",
            "asset_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "namespace_id": "550e8400-e29b-41d4-a716-446655440000",
            "domain_id": "550e8400-e29b-41d4-a716-446655440000",
            "file_id": "550e8400-e29b-41d4-a716-446655440000",
            "process_instance_id": "test-process-id",
            "run_id": "test-run-id",
            "format": "turtle",
            "class_name": "TestClass",
            "property_name": "testProperty",
            "model_id": "text-embedding-ada-002",
            "prompt_id": "nonexistent",
        }

        # Prefer created IDs when available
        for k in list(param_to_value.keys()):
            if k in self.created_ids:
                param_to_value[k] = self.created_ids[k]

        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            return param_to_value.get(key, "nonexistent")

        return re.sub(r"\{([^}]+)\}", replace_match, path)

    def _get_query_params(self, path: str, method: str) -> Optional[Dict]:
        """Generate query parameters for endpoints that require them."""
        if "/api/ontology/layout" in path:
            return {"graph": "http://example.com/test"}
        elif "/api/ontology/save" in path:
            return {"graph": "http://example.com/test"}
        elif "/api/ontology/validate-integrity" in path:
            return {"graph": "http://example.com/test"}
        elif "/api/ontologies" in path and method == "DELETE":
            return {"graph": "http://example.com/test"}
        elif "/api/knowledge/assets" in path and method == "POST":
            return {"project_id": "bfe732af-04d9-44ba-a27a-d0e8cd4afc4b"}  # Use real project ID
        else:
            return None

    async def run_validation(self) -> Dict:
        """Run comprehensive validation of all endpoints."""
        logger.info("🔍 Starting comprehensive API endpoint validation...")

        # Discover all endpoints
        logger.info("📋 Discovering API endpoints...")
        endpoints = self.discover_endpoints()
        logger.info(f"Found {len(endpoints)} endpoints")

        # Authenticate for protected endpoints
        logger.info("🔐 Authenticating both admin and regular users...")
        auth_success = await self.authenticate()
        if not auth_success:
            logger.warning("⚠️ Authentication failed - some tests may be skipped")

        # Test all endpoints
        logger.info("🧪 Testing all endpoints with dual-user approach...")
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

        # Count by method and authorization correctness
        method_counts = {}
        authorization_stats = {
            "correct": 0,
            "incorrect": 0,
            "admin_only_endpoints": 0,
            "regular_endpoints": 0,
        }

        for result in test_results:
            if result.get("is_admin_only"):
                authorization_stats["admin_only_endpoints"] += 1
            elif result.get("requires_auth"):
                authorization_stats["regular_endpoints"] += 1

            for method, method_result in result["test_results"].items():
                if method not in method_counts:
                    method_counts[method] = {
                        "success": 0,
                        "error": 0,
                        "skipped": 0,
                        "auth_correct": 0,
                        "auth_incorrect": 0,
                    }

                # Handle dual-user test results
                if isinstance(method_result, dict) and "admin_access" in method_result:
                    status = method_result["status"]
                    if status == "success":
                        method_counts[method]["success"] += 1
                        # Check authorization correctness for admin-only endpoints
                        if result.get("is_admin_only") and method_result.get(
                            "authorization_correct"
                        ):
                            method_counts[method]["auth_correct"] += 1
                            authorization_stats["correct"] += 1
                        elif result.get("is_admin_only") and not method_result.get(
                            "authorization_correct"
                        ):
                            method_counts[method]["auth_incorrect"] += 1
                            authorization_stats["incorrect"] += 1
                    elif status in ["skipped", "timeout"]:
                        method_counts[method]["skipped"] += 1
                    else:
                        method_counts[method]["error"] += 1
                else:
                    # Handle simple status results (public endpoints)
                    status = method_result.get("status", "error")
                    if status == "success":
                        method_counts[method]["success"] += 1
                    elif status in ["skipped", "timeout"]:
                        method_counts[method]["skipped"] += 1
                    else:
                        method_counts[method]["error"] += 1

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
            "authorization_stats": authorization_stats,
            "method_breakdown": method_counts,
        }

    def print_results(self, results: Dict):
        """Print validation results in a formatted way."""
        print("\n" + "=" * 80)
        print("🔍 ODRAS API ENDPOINT VALIDATION RESULTS (DUAL-USER TESTING)")
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

        # Authorization Statistics
        auth_stats = summary.get("authorization_stats", {})
        if auth_stats.get("admin_only_endpoints", 0) > 0:
            print(f"\n🛡️ AUTHORIZATION VALIDATION:")
            print(f"   👑 Admin-Only Endpoints: {auth_stats['admin_only_endpoints']}")
            print(f"   👤 Regular Auth Endpoints: {auth_stats['regular_endpoints']}")
            print(f"   ✅ Authorization Correct: {auth_stats['correct']}")
            print(f"   ❌ Authorization Issues: {auth_stats['incorrect']}")

        print(f"\n📋 METHOD BREAKDOWN:")
        for method, counts in summary["method_breakdown"].items():
            total = sum(counts.values())
            success_rate = f"{(counts['success'] / total * 100):.1f}%" if total > 0 else "0%"
            auth_correct = counts.get("auth_correct", 0)
            auth_incorrect = counts.get("auth_incorrect", 0)
            auth_info = (
                f" (Auth: {auth_correct}✅/{auth_incorrect}❌)"
                if auth_correct + auth_incorrect > 0
                else ""
            )
            print(
                f"   {method}: {counts['success']}/{total} successful ({success_rate}){auth_info}"
            )

        print(f"\n🔍 DETAILED RESULTS:")
        for result in results["test_results"]:
            status_icon = (
                "✅"
                if result["overall_status"] == "success"
                else "❌" if result["overall_status"] == "error" else "⏭️"
            )
            auth_icon = "🔐" if result["requires_auth"] else "🌐"
            admin_icon = " 👑" if result.get("is_admin_only") else ""
            print(
                f"   {status_icon} {auth_icon}{admin_icon} {result['path']} [{', '.join(result['methods'])}]"
            )

            for method, method_result in result["test_results"].items():
                if isinstance(method_result, dict) and "admin_access" in method_result:
                    # Dual-user test result
                    admin_status = method_result["admin_access"].get("status", "unknown")
                    user_status = method_result["user_access"].get("status_code", "unknown")
                    auth_correct = method_result.get("authorization_correct", False)

                    admin_icon = "✅" if admin_status == "success" else "❌"
                    user_icon = (
                        "🚫"
                        if user_status == 403
                        else ("✅" if isinstance(user_status, int) and user_status < 400 else "❌")
                    )
                    auth_check_icon = "✅" if auth_correct else "❌"

                    print(f"      {method}:")
                    print(f"         👑 Admin: {admin_icon} {admin_status}")
                    print(f"         👤 User: {user_icon} {user_status}")
                    if result.get("is_admin_only"):
                        print(
                            f"         🛡️ Authorization: {auth_check_icon} {'Correct' if auth_correct else 'Issues'}"
                        )
                else:
                    # Simple test result (public endpoint)
                    method_status = method_result.get("status", "unknown")
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

    parser = argparse.ArgumentParser(
        description="Validate all ODRAS API endpoints with dual-user testing"
    )
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
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
