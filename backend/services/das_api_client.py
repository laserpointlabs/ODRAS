"""
DAS API Client - Autonomous API execution for DAS commands

This module provides a secure HTTP client that can execute API calls on behalf of DAS,
with proper authentication, error handling, and session management.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from urllib.parse import urljoin
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class APICallResult:
    """Result of an API call execution"""
    success: bool
    status_code: int
    data: Dict[str, Any] = None
    error: Optional[str] = None
    response_time: Optional[float] = None
    headers: Dict[str, str] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.headers is None:
            self.headers = {}


class DASAPIClient:
    """
    Secure HTTP client for autonomous API execution by DAS
    """

    def __init__(self, settings: Settings, base_url: str = None):
        self.settings = settings
        self.base_url = base_url or "http://localhost:8000"
        self.session: Optional[ClientSession] = None
        self.auth_token: Optional[str] = None
        self.timeout = ClientTimeout(total=30, connect=10)

        # API endpoints that DAS is allowed to call autonomously
        self.allowed_endpoints = {
            # Ontology management
            "GET:/api/ontologies": "read_ontologies",
            "GET:/api/ontologies/{ontology_id}": "read_ontology",
            "POST:/api/ontologies/{ontology_id}/classes": "create_class",
            "POST:/api/ontologies/{ontology_id}/relationships": "create_relationship",
            "PUT:/api/ontologies/{ontology_id}/classes/{class_id}": "update_class",

            # Knowledge management
            "GET:/api/knowledge/assets": "read_knowledge_assets",
            "POST:/api/knowledge/search": "search_knowledge",
            "GET:/api/knowledge/assets/{asset_id}": "read_knowledge_asset",

            # File operations (limited)
            "GET:/api/files": "list_files",
            "GET:/api/files/{file_id}": "read_file_info",
            "POST:/api/files/upload": "upload_file",

            # Analysis workflows
            "POST:/api/workflows/requirements_analysis": "run_requirements_analysis",
            "GET:/api/workflows/status/{workflow_id}": "check_workflow_status",

            # Project management (read-only)
            "GET:/api/projects": "list_projects",
            "GET:/api/projects/{project_id}": "read_project",
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def initialize(self):
        """Initialize the HTTP client session"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30
            )
            self.session = ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    "User-Agent": "DAS-Autonomous-Agent/1.0",
                    "Content-Type": "application/json"
                }
            )
            logger.info("DAS API client initialized")

    async def close(self):
        """Close the HTTP client session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("DAS API client closed")

    async def authenticate(self, username: str = "das_service", password: str = "das_service_2024!") -> bool:
        """
        Authenticate DAS with the ODRAS API using the dedicated service account
        """
        try:
            if not self.session:
                await self.initialize()

            auth_data = {
                "username": username,
                "password": password
            }

            async with self.session.post(
                f"{self.base_url}/api/auth/login",
                json=auth_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get("token")

                    # Update session headers with auth token
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}"
                    })

                    logger.info("DAS authenticated successfully")
                    return True
                else:
                    logger.error(f"DAS authentication failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"DAS authentication error: {e}")
            return False

    def _is_endpoint_allowed(self, method: str, endpoint: str) -> bool:
        """
        Check if the endpoint is in the allowed list for autonomous execution
        Enhanced with DAS service account permission checking
        """
        # Create a key for the allowed endpoints
        endpoint_key = f"{method.upper()}:{endpoint}"

        # First check against hardcoded whitelist
        if endpoint_key in self.allowed_endpoints:
            return True

        # Check pattern match (for endpoints with path parameters)
        for allowed_pattern in self.allowed_endpoints.keys():
            if self._endpoint_matches_pattern(endpoint_key, allowed_pattern):
                return True

        # Additional security: Block dangerous operations for DAS service account
        dangerous_patterns = [
            "DELETE:",  # No delete operations
            ":*/api/auth/",  # No auth management
            ":*/api/admin/",  # No admin operations
            "POST:*/api/users",  # No user creation
            "PUT:*/api/users",  # No user modification
            "DELETE:*/api/users",  # No user deletion
            ":*/api/system/",  # No system operations
        ]

        for dangerous in dangerous_patterns:
            if dangerous in endpoint_key:
                logger.warning(f"DAS service account blocked from dangerous operation: {endpoint_key}")
                return False

        return False

    def _endpoint_matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """
        Check if an endpoint matches a pattern with path parameters
        """
        # Split method and path
        endpoint_parts = endpoint.split(":", 1)
        pattern_parts = pattern.split(":", 1)

        if len(endpoint_parts) != 2 or len(pattern_parts) != 2:
            return False

        endpoint_method, endpoint_path = endpoint_parts
        pattern_method, pattern_path = pattern_parts

        # Method must match exactly
        if endpoint_method != pattern_method:
            return False

        # Split paths into segments
        endpoint_segments = endpoint_path.strip("/").split("/")
        pattern_segments = pattern_path.strip("/").split("/")

        # Must have same number of segments
        if len(endpoint_segments) != len(pattern_segments):
            return False

        # Check each segment
        for ep_seg, pat_seg in zip(endpoint_segments, pattern_segments):
            # Pattern segment with {} matches any value
            if pat_seg.startswith("{") and pat_seg.endswith("}"):
                continue
            # Otherwise must match exactly
            elif ep_seg != pat_seg:
                return False

        return True

    async def execute_api_call(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        files: Dict[str, Any] = None
    ) -> APICallResult:
        """
        Execute an API call with security checks
        """
        import time
        start_time = time.time()

        try:
            # Security check - only allow pre-approved endpoints
            if not self._is_endpoint_allowed(method, endpoint):
                return APICallResult(
                    success=False,
                    status_code=403,
                    error=f"Endpoint {method} {endpoint} not allowed for autonomous execution"
                )

            # Ensure we're authenticated
            if not self.auth_token:
                auth_success = await self.authenticate()
                if not auth_success:
                    return APICallResult(
                        success=False,
                        status_code=401,
                        error="Authentication failed"
                    )

            if not self.session:
                await self.initialize()

            # Build full URL
            url = urljoin(self.base_url, endpoint.lstrip("/"))

            # Prepare request kwargs
            request_kwargs = {}
            if data:
                if files:
                    # For file uploads, don't set json data
                    request_kwargs["data"] = data
                else:
                    request_kwargs["json"] = data
            if params:
                request_kwargs["params"] = params
            if files:
                request_kwargs["data"] = aiohttp.FormData()
                for key, value in (data or {}).items():
                    request_kwargs["data"].add_field(key, str(value))
                for file_key, file_data in files.items():
                    request_kwargs["data"].add_field(file_key, file_data)

            # Execute the request
            async with self.session.request(method, url, **request_kwargs) as response:
                response_time = time.time() - start_time

                # Get response data
                try:
                    if response.content_type == 'application/json':
                        response_data = await response.json()
                    else:
                        response_text = await response.text()
                        response_data = {"text": response_text}
                except Exception:
                    response_data = {"raw": await response.text()}

                # Create result
                result = APICallResult(
                    success=200 <= response.status < 300,
                    status_code=response.status,
                    data=response_data,
                    response_time=response_time,
                    headers=dict(response.headers)
                )

                if not result.success:
                    result.error = f"HTTP {response.status}: {response_data.get('detail', 'Unknown error')}"

                logger.info(f"DAS API call: {method} {endpoint} -> {response.status} ({response_time:.2f}s)")
                return result

        except asyncio.TimeoutError:
            return APICallResult(
                success=False,
                status_code=408,
                error="Request timeout",
                response_time=time.time() - start_time
            )
        except ClientError as e:
            return APICallResult(
                success=False,
                status_code=0,
                error=f"Client error: {str(e)}",
                response_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            return APICallResult(
                success=False,
                status_code=500,
                error=f"Unexpected error: {str(e)}",
                response_time=time.time() - start_time
            )

    async def create_ontology_class(
        self,
        ontology_id: str,
        class_name: str,
        parent_class: str = None,
        description: str = None,
        properties: Dict[str, Any] = None
    ) -> APICallResult:
        """
        Create a new class in an ontology
        """
        data = {
            "name": class_name,
            "description": description or f"Class {class_name} created by DAS"
        }

        if parent_class:
            data["parent_class"] = parent_class
        if properties:
            data["properties"] = properties

        return await self.execute_api_call(
            "POST",
            f"/api/ontologies/{ontology_id}/classes",
            data=data
        )

    async def retrieve_ontology(self, ontology_id: str) -> APICallResult:
        """
        Retrieve an ontology by ID
        """
        return await self.execute_api_call(
            "GET",
            f"/api/ontologies/{ontology_id}"
        )

    async def search_knowledge(
        self,
        query: str,
        project_id: str = None,
        max_results: int = 10
    ) -> APICallResult:
        """
        Search the knowledge base
        """
        data = {
            "query": query,
            "max_results": max_results
        }

        if project_id:
            data["project_id"] = project_id

        return await self.execute_api_call(
            "POST",
            "/api/knowledge/search",
            data=data
        )

    async def run_requirements_analysis(
        self,
        document_id: str,
        analysis_type: str = "full",
        ontology_id: str = None
    ) -> APICallResult:
        """
        Start a requirements analysis workflow
        """
        data = {
            "document_id": document_id,
            "analysis_type": analysis_type
        }

        if ontology_id:
            data["ontology_id"] = ontology_id

        return await self.execute_api_call(
            "POST",
            "/api/workflows/requirements_analysis",
            data=data
        )

    async def list_ontologies(self, project_id: str = None) -> APICallResult:
        """
        List available ontologies
        """
        params = {}
        if project_id:
            params["project_id"] = project_id

        return await self.execute_api_call(
            "GET",
            "/api/ontologies",
            params=params
        )

    async def add_relationship(
        self,
        ontology_id: str,
        source_class: str,
        target_class: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> APICallResult:
        """
        Add a relationship between two classes
        """
        data = {
            "source_class": source_class,
            "target_class": target_class,
            "relationship_type": relationship_type
        }

        if properties:
            data["properties"] = properties

        return await self.execute_api_call(
            "POST",
            f"/api/ontologies/{ontology_id}/relationships",
            data=data
        )

    async def get_workflow_status(self, workflow_id: str) -> APICallResult:
        """
        Check the status of a running workflow
        """
        return await self.execute_api_call(
            "GET",
            f"/api/workflows/status/{workflow_id}"
        )

    async def health_check(self) -> bool:
        """
        Check if the API is accessible
        """
        try:
            result = await self.execute_api_call("GET", "/health")
            return result.success
        except Exception:
            return False

