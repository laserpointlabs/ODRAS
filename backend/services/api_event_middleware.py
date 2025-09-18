"""
API Event Middleware - Capture all API calls for session thread intelligence

Leverages existing Uvicorn logging but adds Redis event capture for DAS session intelligence.
Works alongside existing logging system without duplication.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APIEventCaptureMiddleware(BaseHTTPMiddleware):
    """
    Middleware to capture API calls for session thread intelligence

    Integrates with existing logging system and adds Redis event capture
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client
        self.app = app

        # Class-level Redis client that can be set after initialization
        APIEventCaptureMiddleware._redis_client = redis_client

        # Initialize capture patterns
        self._init_capture_patterns()

    @classmethod
    def set_redis_client(cls, redis_client):
        """Set Redis client for all middleware instances"""
        cls._redis_client = redis_client

    def _init_capture_patterns(self):
        """Initialize capture patterns"""
        # Define which endpoints to capture for session intelligence
        self.capture_patterns = {
            # Project operations
            "POST:/api/projects": "project_created",
            "PUT:/api/projects/": "project_updated",
            "DELETE:/api/projects/": "project_deleted",

            # Ontology operations
            "POST:/api/ontologies": "ontology_created",
            "POST:/api/ontology/classes": "ontology_class_created",
            "POST:/api/ontology/save": "ontology_saved",
            "GET:/api/ontology/layout": "ontology_viewed",

            # File operations
            "POST:/api/files/upload": "file_uploaded",
            "DELETE:/api/files/": "file_deleted",

            # Knowledge operations
            "POST:/api/knowledge/query": "knowledge_searched",
            "POST:/api/knowledge/query-workflow": "knowledge_searched_workflow",
            "POST:/api/knowledge/assets": "knowledge_asset_created",

            # Analysis operations
            "POST:/api/workflows/": "workflow_started",

            # DAS operations
            "POST:/api/das/chat": "das_interaction"
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Capture API call and process response"""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Use class-level Redis client if instance client not set
        redis_client = self.redis or getattr(self.__class__, '_redis_client', None)

        # Capture relevant API calls (don't interfere with existing logging)
        if redis_client and self._should_capture(request, response):
            # Set instance Redis client for this request
            self.redis = redis_client
            try:
                await self._capture_api_event(request, response, start_time)
            except Exception as e:
                # Don't fail the request if event capture fails
                logger.warning(f"Failed to capture API event: {e}")

        return response

    def _should_capture(self, request: Request, response: Response) -> bool:
        """Determine if this API call should be captured for session intelligence"""
        # Only capture successful operations that change state
        if response.status_code not in [200, 201]:
            return False

        # Only capture relevant endpoints
        method = request.method
        path = str(request.url.path)

        # Check for exact matches or pattern matches
        endpoint_key = f"{method}:{path}"

        # Exact match
        if endpoint_key in self.capture_patterns:
            return True

        # Pattern match for endpoints with IDs
        for pattern in self.capture_patterns.keys():
            if self._matches_pattern(endpoint_key, pattern):
                return True

        return False

    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches a pattern (e.g., DELETE:/api/files/ matches DELETE:/api/files/123)"""
        if pattern.endswith("/") and endpoint.startswith(pattern):
            return True
        return False

    async def _capture_api_event(self, request: Request, response: Response, start_time: float):
        """Capture API event with enhanced semantics and clean data for Redis"""
        try:
            # Extract user information from request state or auth header
            username = getattr(request.state, 'username', None)
            user_id = getattr(request.state, 'user_id', None)
            session_thread_id = getattr(request.state, 'session_thread_id', None)

            # If no user context, try to extract from auth header
            if not username:
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    # Get user info from token (simplified for now)
                    try:
                        # Use existing auth token validation
                        from ..services.auth import get_user_by_token
                        user_info = get_user_by_token(token)
                        if user_info:
                            username = user_info.get("username")
                            user_id = user_info.get("user_id")
                    except Exception:
                        # For now, use a simple default for testing
                        username = "unknown_user"
                        user_id = "unknown"

            if not username:
                return  # Skip anonymous calls

            # Extract semantic meaning from the API call
            semantic_event = await self._extract_semantic_meaning(request, response)

            if not semantic_event:
                return  # Skip if we can't extract meaningful semantics

            # Create clean, semantic event for Redis
            clean_event = {
                "event_id": f"api_{int(time.time() * 1000)}",
                "session_thread_id": session_thread_id,
                "username": username,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "event_type": semantic_event["event_type"],
                "semantic_action": semantic_event["semantic_action"],
                "context": semantic_event.get("context", {}),
                "metadata": semantic_event.get("metadata", {}),
                "response_time": time.time() - start_time,
                "success": 200 <= response.status_code < 300
            }

            # Queue for background processing
            await self.redis.lpush("api_events", json.dumps(clean_event))

            logger.debug(f"Captured semantic event: {semantic_event['semantic_action']} for user {username}")

        except Exception as e:
            logger.error(f"Error capturing API event: {e}")

    async def _extract_semantic_meaning(self, request: Request, response: Response) -> Optional[Dict[str, Any]]:
        """Extract semantic meaning from API calls for session intelligence"""
        method = request.method
        path = str(request.url.path)
        query_params = dict(request.query_params)

        # Extract semantic meaning based on endpoint patterns

        # Ontology Operations
        if "ontology/layout" in path and method == "PUT":
            graph_param = query_params.get("graph", "")
            ontology_id = graph_param.split("/")[-1] if graph_param else "unknown"
            return {
                "event_type": "ontology_layout_modified",
                "semantic_action": f"Modified layout for ontology {ontology_id}",
                "context": {
                    "ontology_id": ontology_id,
                    "ontology_iri": graph_param,
                    "project_id": self._extract_project_from_iri(graph_param)
                },
                "metadata": {
                    "workbench": "ontology",
                    "action_type": "layout_modification"
                }
            }

        elif "ontology/save" in path and method == "POST":
            graph_param = query_params.get("graph", "")
            ontology_id = graph_param.split("/")[-1] if graph_param else "unknown"
            return {
                "event_type": "ontology_saved",
                "semantic_action": f"Saved ontology {ontology_id}",
                "context": {
                    "ontology_id": ontology_id,
                    "ontology_iri": graph_param,
                    "project_id": self._extract_project_from_iri(graph_param)
                },
                "metadata": {
                    "workbench": "ontology",
                    "action_type": "ontology_save"
                }
            }

        # Project Operations
        elif path == "/api/projects" and method == "POST":
            return {
                "event_type": "project_created",
                "semantic_action": "Created new project",
                "context": {},
                "metadata": {
                    "workbench": "project",
                    "action_type": "project_creation"
                }
            }

        # File Operations
        elif "/api/files/upload" in path and method == "POST":
            project_id = query_params.get("project_id", "unknown")
            return {
                "event_type": "file_uploaded",
                "semantic_action": f"Uploaded file to project {project_id}",
                "context": {
                    "project_id": project_id
                },
                "metadata": {
                    "workbench": "files",
                    "action_type": "file_upload"
                }
            }

        # Knowledge Operations
        elif "/api/knowledge/query" in path and method == "POST":
            return {
                "event_type": "knowledge_searched",
                "semantic_action": "Searched knowledge base",
                "context": {},
                "metadata": {
                    "workbench": "knowledge",
                    "action_type": "knowledge_search"
                }
            }

        # DAS Operations
        elif "/api/das/chat" in path and method == "POST":
            return {
                "event_type": "das_interaction",
                "semantic_action": "Interacted with DAS assistant",
                "context": {},
                "metadata": {
                    "workbench": "das",
                    "action_type": "das_chat"
                }
            }

        # Skip non-semantic operations (health checks, static files, etc.)
        elif any(skip in path for skip in ["/health", "/static", "/favicon", "/api/auth/me"]):
            return None

        # Default for unrecognized but potentially important operations
        else:
            return {
                "event_type": "api_call",
                "semantic_action": f"{method} request to {path}",
                "context": {},
                "metadata": {
                    "method": method,
                    "endpoint": path,
                    "action_type": "generic_api_call"
                }
            }

    def _extract_project_from_iri(self, iri: str) -> Optional[str]:
        """Extract project ID from ontology IRI"""
        try:
            # Pattern: https://ontology.navy.mil/odras/core/{project_id}/ontologies/{ontology_id}
            parts = iri.split("/")
            if "core" in parts:
                core_index = parts.index("core")
                if len(parts) > core_index + 1:
                    return parts[core_index + 1]
        except Exception:
            pass
        return None


def create_api_event_middleware(redis_client):
    """Factory function to create middleware with Redis client"""
    return lambda app: APIEventCaptureMiddleware(app, redis_client)

