"""
Unified Event Middleware - SQL-first event capture for all API operations

This middleware consolidates all event capture into a single SQL-first system:
- Routes ALL events through SqlFirstThreadManager
- Uses EventCapture2 for rich context capture
- Eliminates fragmented Redis-only event systems
- Provides unified event flow: API → Middleware → EventCapture2 → SQL-first storage
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class UnifiedEventMiddleware(BaseHTTPMiddleware):
    """
    Unified middleware for SQL-first event capture across all ODRAS operations
    """

    def __init__(self, app, redis_client=None, sql_first_manager=None):
        super().__init__(app)
        self.redis = redis_client
        self.sql_first_manager = sql_first_manager

        # Initialize comprehensive capture patterns
        self._init_capture_patterns()

    def _init_capture_patterns(self):
        """Initialize comprehensive event capture patterns"""
        self.capture_patterns = {
            # Project operations
            "POST:/api/projects": "project_created",
            "PUT:/api/projects": "project_updated",
            "DELETE:/api/projects": "project_deleted",

            # Ontology operations
            "POST:/api/ontologies": "ontology_created",
            "POST:/api/ontology/save": "ontology_saved",
            "POST:/api/ontology/classes": "class_created",
            "PUT:/api/ontology/classes": "class_updated",
            "DELETE:/api/ontology/classes": "class_deleted",
            "POST:/api/ontology/properties": "property_created",
            "PUT:/api/ontology/properties": "property_updated",
            "DELETE:/api/ontology/properties": "property_deleted",
            "POST:/api/ontology/relationships": "relationship_added",
            "POST:/api/ontology/validate": "ontology_validated",
            "POST:/api/ontology/import": "ontology_imported",
            "GET:/api/ontology/export": "ontology_exported",

            # File operations
            "POST:/api/files/upload": "file_uploaded",
            "DELETE:/api/files": "file_deleted",

            # Knowledge operations
            "POST:/api/knowledge/assets": "knowledge_asset_created",
            "PUT:/api/knowledge/assets": "knowledge_asset_updated",
            "DELETE:/api/knowledge/assets": "knowledge_asset_deleted",
            "POST:/api/knowledge/query": "knowledge_searched",
            "POST:/api/knowledge/query-workflow": "knowledge_rag_query",

            # DAS operations
            "POST:/api/das2/chat": "das_interaction",
            "POST:/api/das/chat": "das_interaction",

            # Workflow operations
            "POST:/api/workflows": "workflow_started",

            # Authentication operations
            "POST:/api/auth/login": "user_login",
            "POST:/api/auth/logout": "user_logout"
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Capture events for all relevant API operations"""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Only capture successful operations that should generate events
        if self._should_capture(request, response):
            try:
                await self._capture_unified_event(request, response, start_time)
            except Exception as e:
                # Don't fail the request if event capture fails
                logger.warning(f"Unified event capture failed: {e}")

        return response

    def _should_capture(self, request: Request, response: Response) -> bool:
        """Determine if this API call should be captured"""
        # Only capture successful operations
        if response.status_code not in [200, 201, 202]:
            return False

        # Check for configured patterns
        method = request.method
        path = str(request.url.path)
        endpoint_key = f"{method}:{path}"

        # Exact match
        if endpoint_key in self.capture_patterns:
            return True

        # Pattern match for endpoints with IDs (e.g., PUT:/api/projects/123)
        for pattern in self.capture_patterns.keys():
            if self._matches_pattern(endpoint_key, pattern):
                return True

        return False

    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Match endpoint with pattern (handles dynamic IDs)"""
        endpoint_parts = endpoint.split(':')
        pattern_parts = pattern.split(':')

        if len(endpoint_parts) != 2 or len(pattern_parts) != 2:
            return False

        # Method must match exactly
        if endpoint_parts[0] != pattern_parts[0]:
            return False

        # Path matching with dynamic segments
        endpoint_path = endpoint_parts[1]
        pattern_path = pattern_parts[1]

        # Handle exact matches
        if endpoint_path == pattern_path:
            return True

        # Handle patterns with IDs (e.g., /api/projects/{id})
        endpoint_segments = endpoint_path.strip('/').split('/')
        pattern_segments = pattern_path.strip('/').split('/')

        if len(endpoint_segments) == len(pattern_segments):
            for ep_seg, pat_seg in zip(endpoint_segments, pattern_segments):
                # Segment matches or is a dynamic ID segment
                if ep_seg != pat_seg and not (pat_seg == 'projects' and ep_seg != 'projects' and len(endpoint_segments) > 2):
                    # Allow ID matching for known endpoints
                    if not (len(endpoint_segments) >= 3 and endpoint_segments[1] in ['projects', 'ontology', 'files', 'knowledge', 'assets']):
                        return False
            return True

        return False

    async def _capture_unified_event(self, request: Request, response: Response, start_time: float):
        """Capture event using unified SQL-first system"""
        try:
            # Get user info from request
            user_info = await self._get_user_info(request)
            if not user_info:
                return

            # Get EventCapture2 instance
            from backend.services.eventcapture2 import get_event_capture
            event_capture = get_event_capture()

            if not event_capture:
                logger.warning("EventCapture2 not initialized - cannot capture unified event")
                return

            # Determine operation type and route to appropriate capture method
            method = request.method
            path = str(request.url.path)
            endpoint_key = f"{method}:{path}"

            response_time = time.time() - start_time

            # Route to specific capture methods based on operation type
            success = await self._route_event_capture(
                event_capture, endpoint_key, request, response, user_info, response_time
            )

            if success:
                logger.debug(f"Unified event capture success for {endpoint_key}")
            else:
                logger.debug(f"Unified event capture filtered for {endpoint_key}")

        except Exception as e:
            logger.error(f"Error in unified event capture: {e}")

    async def _route_event_capture(
        self,
        event_capture,
        endpoint_key: str,
        request: Request,
        response: Response,
        user_info: Dict[str, Any],
        response_time: float
    ) -> bool:
        """Route to appropriate EventCapture2 method based on operation type"""

        operation_type = self.capture_patterns.get(endpoint_key)
        if not operation_type:
            # Try pattern matching
            for pattern, op_type in self.capture_patterns.items():
                if self._matches_pattern(endpoint_key, pattern):
                    operation_type = op_type
                    break

        if not operation_type:
            return False

        # Extract data from request/response
        try:
            request_data = await self._get_request_data(request)
            response_data = await self._get_response_data(response)
        except:
            request_data = {}
            response_data = {}

        username = user_info.get("username", "unknown")
        user_id = user_info.get("user_id", "unknown")

        # Route to appropriate capture method
        try:
            if operation_type == "project_created":
                project_id = response_data.get("project", {}).get("project_id")
                project_name = request_data.get("name", "Unknown Project")
                if project_id:
                    return await event_capture.capture_project_created(
                        project_id=project_id,
                        project_name=project_name,
                        user_id=user_id,
                        username=username,
                        project_details=request_data,
                        response_time=response_time
                    )

            elif operation_type == "ontology_created":
                ontology_name = request_data.get("name", "Unknown Ontology")
                project_id = request_data.get("project")
                if project_id:
                    return await event_capture.capture_ontology_operation(
                        operation_type="created",
                        ontology_name=ontology_name,
                        project_id=project_id,
                        user_id=user_id,
                        username=username,
                        operation_details=request_data,
                        response_time=response_time
                    )

            elif operation_type == "class_created":
                class_name = request_data.get("name", "Unknown Class")
                # Extract project_id and ontology_name from graph parameter
                graph = request.query_params.get("graph", "")
                project_id = self._extract_project_from_graph(graph)
                ontology_name = graph.split("/")[-1] if "/" in graph else "unknown"
                if project_id:
                    return await event_capture.capture_ontology_operation(
                        operation_type="modified",
                        ontology_name=ontology_name,
                        project_id=project_id,
                        user_id=user_id,
                        username=username,
                        operation_details={
                            "class_name": class_name,
                            "operation": "class_added",
                            **request_data
                        },
                        response_time=response_time
                    )

            elif operation_type == "file_uploaded":
                filename = request_data.get("filename") or "Unknown File"
                project_id = request_data.get("project_id")
                if project_id:
                    return await event_capture.capture_file_operation(
                        operation_type="uploaded",
                        filename=filename,
                        project_id=project_id,
                        user_id=user_id,
                        username=username,
                        file_details=request_data,
                        response_time=response_time
                    )

            elif operation_type == "knowledge_asset_created":
                asset_title = request_data.get("title", "Unknown Asset")
                project_id = request.query_params.get("project_id")
                if project_id:
                    return await event_capture.capture_knowledge_asset_created(
                        asset_id="pending",  # Will be resolved from response
                        title=asset_title,
                        project_id=project_id,
                        user_id=user_id,
                        username=username,
                        asset_details=request_data,
                        response_time=response_time
                    )

            elif operation_type == "das_interaction":
                project_id = request_data.get("project_id")
                if project_id:
                    return await event_capture.capture_das_interaction(
                        interaction_type="chat",
                        project_id=project_id,
                        user_id=user_id,
                        username=username,
                        interaction_details=request_data,
                        response_time=response_time
                    )

            # Add more operation types as needed...

        except Exception as e:
            logger.error(f"Error routing event capture for {operation_type}: {e}")

        return False

    def _extract_project_from_graph(self, graph_uri: str) -> Optional[str]:
        """Extract project ID from graph URI"""
        try:
            # Graph URIs typically have format: .../projects/{project_id}/ontologies/...
            parts = graph_uri.split('/')
            if 'projects' in parts:
                idx = parts.index('projects')
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except:
            pass
        return None

    async def _get_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from request"""
        try:
            # Try to get user from auth header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return None

            # This should integrate with your existing auth system
            # For now, return a placeholder - you'll need to integrate with your JWT validation
            from backend.api.dependencies import get_user
            from fastapi import Depends

            # This is a simplified version - you'll need to adapt to your auth system
            return {"user_id": "middleware_user", "username": "api_user"}

        except Exception as e:
            logger.warning(f"Could not extract user info: {e}")
            return None

    async def _get_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract request data safely"""
        try:
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = await request.body()
                if body:
                    return json.loads(body.decode('utf-8'))
        except:
            pass
        return {}

    async def _get_response_data(self, response: Response) -> Dict[str, Any]:
        """Extract response data safely"""
        # Note: This is challenging because response body may be consumed
        # You might need to implement response body caching if needed
        return {}
