"""
Session Capture Middleware - Proper FastAPI middleware implementation

Captures API calls with semantic meaning for session thread intelligence.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Global Redis client for middleware
_global_redis_client = None


class SessionCaptureMiddleware(BaseHTTPMiddleware):
    """Middleware to capture API calls for session intelligence"""

    def __init__(self, app: ASGIApp, redis_client=None):
        super().__init__(app)
        self.redis = redis_client

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and capture semantic events"""
        start_time = time.time()

        # Debug: Log that middleware is being called
        print(f"🔥 MIDDLEWARE: {request.method} {request.url.path}")

        # Process the request
        response = await call_next(request)

        # Debug: Check if we should capture
        should_capture = self._should_capture(request, response)
        print(f"🔥 MIDDLEWARE: Should capture {request.method} {request.url.path}: {should_capture}")
        print(f"🔥 MIDDLEWARE: Redis available: {bool(self.redis)}")
        print(f"🔥 MIDDLEWARE: Global Redis available: {bool(_global_redis_client)}")

        # Use global Redis client
        redis_client = self.redis or _global_redis_client

        # Capture semantic events if Redis is available
        if redis_client and should_capture:
            try:
                print(f"🔥 MIDDLEWARE: Attempting to capture semantic event for {request.method} {request.url.path}")
                await self._capture_semantic_event(request, response, start_time, redis_client)
                print(f"🔥 MIDDLEWARE: Semantic event captured successfully")
            except Exception as e:
                print(f"🔥 MIDDLEWARE: Session capture error: {e}")
                import traceback
                print(f"🔥 MIDDLEWARE: Full traceback: {traceback.format_exc()}")
                logger.warning(f"Session capture error: {e}")
        elif not redis_client:
            print(f"🔥 MIDDLEWARE: No Redis client available for {request.method} {request.url.path}")
        elif not should_capture:
            print(f"🔥 MIDDLEWARE: Not capturing {request.method} {request.url.path} (filtered out)")

        return response

    def _should_capture(self, request: Request, response: Response) -> bool:
        """Determine if this request should be captured"""
        # Only capture successful state-changing operations
        if response.status_code not in [200, 201]:
            return False

        # Skip health checks and static content
        path = str(request.url.path)
        if any(skip in path for skip in ["/health", "/static", "/favicon"]):
            return False

        # Capture meaningful API operations
        meaningful_operations = request.method in ["POST", "PUT", "DELETE"]

        # Also capture project creation even if it fails (for debugging)
        if "projects" in path and request.method == "POST":
            return True

        return meaningful_operations

    async def _capture_semantic_event(self, request: Request, response: Response, start_time: float, redis_client):
        """Extract semantic meaning and queue event"""
        try:
            # Extract user info from auth header
            username = await self._get_username_from_request(request)
            if not username:
                return

            # Extract semantic meaning with request/response body analysis
            semantic_data = await self._extract_semantics(request, response)

            # Skip event if semantic extraction returned None (filtered out)
            if semantic_data is None:
                print(f"🔥 MIDDLEWARE: Event filtered out - not capturing")
                return

            # Create clean event
            event = {
                "event_id": f"api_{int(time.time() * 1000)}",
                "username": username,
                "timestamp": datetime.now().isoformat(),
                "semantic_action": semantic_data["action"],
                "context": semantic_data["context"],
                "metadata": semantic_data["metadata"],
                "response_time": time.time() - start_time,
                "success": True
            }

            # Route directly to DAS bridge if available, otherwise queue
            das_bridge = getattr(sys.modules[__name__], 'das_bridge', None)
            if das_bridge:
                print(f"🔥 CAPTURE: Routing event directly to DAS: {event['semantic_action']}")
                try:
                    success = await das_bridge._route_event_to_das(event)
                    print(f"🔥 CAPTURE: DAS routing {'SUCCESS' if success else 'FAILED'}")
                except Exception as das_error:
                    print(f"🔥 CAPTURE: DAS routing FAILED: {das_error}")
                    # Fallback to queue
                    result = await redis_client.lpush("api_events", json.dumps(event))
                    print(f"🔥 CAPTURE: Fallback queued, result: {result}")
            else:
                print(f"🔥 CAPTURE: No DAS bridge, queuing event: {event['semantic_action']}")
                try:
                    result = await redis_client.lpush("api_events", json.dumps(event))
                    print(f"🔥 CAPTURE: Event queued successfully, result: {result}")
                except Exception as redis_error:
                    print(f"🔥 CAPTURE: Redis write FAILED: {redis_error}")
                    raise redis_error
            logger.debug(f"Captured: {semantic_data['action']} for {username}")

        except Exception as e:
            logger.error(f"Error capturing semantic event: {e}")

    async def _get_username_from_request(self, request: Request) -> Optional[str]:
        """Extract username from request using proper auth system"""
        try:
            auth_header = request.headers.get("authorization", "")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Use the same authentication logic as the auth service
            from backend.services.auth import get_user
            try:
                user = get_user(auth_header)
                return user.get("username")
            except Exception:
                # If auth fails, don't capture event (user not authenticated)
                return None
        except Exception:
            pass
            return None

    def _extract_project_id_from_graph(self, graph_url: str) -> Optional[str]:
        """Extract project ID from ontology graph URL"""
        try:
            # Pattern: https://xma-adt.usnc.mil/odras/core/{project_id}/ontologies/{ontology_id}
            if "/core/" in graph_url and "/ontologies/" in graph_url:
                parts = graph_url.split("/core/")[1].split("/ontologies/")[0]
                return parts if parts else None
        except Exception:
            pass
        return None

    async def _extract_layout_changes(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract detailed information about ontology layout changes and classify them"""
        try:
            # Read request body to understand what changed
            # Note: request.body() can only be called once, and may have been consumed
            try:
                body = await request.body()
            except:
                # Body may have been consumed already
                body = getattr(request, '_body', b'')

            if body:
                body_str = body.decode('utf-8')

                # Parse common layout operations
                changes = []
                is_semantic = False  # Track if this is a meaningful semantic change

                # Check for pure positioning changes (not semantic)
                if '"x":' in body_str and '"y":' in body_str:
                    changes.append("repositioned elements")

                # Check for semantic changes (meaningful for DAS)
                if '"label":' in body_str or '"name":' in body_str:
                    # Try to extract class names from body
                    import re
                    names = re.findall(r'"(?:label|name)"\s*:\s*"([^"]+)"', body_str)
                    if names:
                        changes.append(f"modified {', '.join(names[:3])}")
                        is_semantic = True  # Renaming is semantic

                if '"source":' in body_str and '"target":' in body_str:
                    changes.append("modified relationships")
                    is_semantic = True  # Relationship changes are semantic

                if '"type":' in body_str:
                    types = re.findall(r'"type"\s*:\s*"([^"]+)"', body_str)
                    if types:
                        changes.append(f"worked with {', '.join(set(types[:3]))}")
                        # Type changes might be semantic depending on the type
                        if any(t for t in types if t not in ['position', 'layout', 'view']):
                            is_semantic = True

                # Check for class creation/deletion indicators
                if any(keyword in body_str.lower() for keyword in ['create', 'delete', 'add', 'remove']):
                    is_semantic = True

                return {
                    "description": ", ".join(changes) if changes else None,
                    "is_semantic": is_semantic,
                    "is_layout_only": len(changes) == 1 and "repositioned elements" in changes
                }

        except Exception as e:
            logger.debug(f"Could not extract layout details: {e}")
        return None

    async def _extract_class_creation_details(self, request: Request, response: Response) -> Optional[str]:
        """Extract details about class creation"""
        try:
            # Check request body for class details
            try:
                body = await request.body()
            except:
                body = getattr(request, '_body', b'')

            if body:
                body_str = body.decode('utf-8')

                # Try to extract class name and type
                import re
                class_names = re.findall(r'"(?:label|name|className)"\s*:\s*"([^"]+)"', body_str)
                class_types = re.findall(r'"(?:type|classType)"\s*:\s*"([^"]+)"', body_str)

                details = []
                if class_names:
                    details.append(f"class '{class_names[0]}'")
                if class_types and class_types[0] != "owl:Class":
                    details.append(f"type {class_types[0]}")

                return " ".join(details) if details else None

            # Check response for created class info
            if hasattr(response, '_content') and response._content:
                response_str = response._content.decode('utf-8')
                class_names = re.findall(r'"(?:label|name|className)"\s*:\s*"([^"]+)"', response_str)
                if class_names:
                    return f"class '{class_names[0]}'"

        except Exception as e:
            logger.debug(f"Could not extract class creation details: {e}")
        return None

    async def _extract_semantics(self, request: Request, response: Response) -> Dict[str, Any]:
        """Extract semantic meaning from API call"""
        method = request.method
        path = str(request.url.path)
        query_params = dict(request.query_params)

        print(f"🔥 MIDDLEWARE: Extracting semantics for {method} {path}")

        # Ontology operations
        if "ontology/layout" in path and method == "PUT":
            graph = query_params.get("graph", "")
            ontology_id = graph.split("/")[-1] if graph else "unknown"
            project_id = self._extract_project_id_from_graph(graph)

            # Try to extract detailed layout changes from request body
            layout_analysis = await self._extract_layout_changes(request)

            # Skip layout-only changes to prevent CUDA memory overload
            if layout_analysis and layout_analysis.get("is_layout_only", False):
                print(f"🔥 MIDDLEWARE: Skipping layout-only change for {ontology_id} (prevents CUDA overload)")
                return None  # Signal to skip this event

            # Only process semantic changes, but use the same routing path that worked before
            layout_details = layout_analysis.get("description") if layout_analysis else None

            # Determine if this is semantic or just layout
            is_semantic = layout_analysis and layout_analysis.get("is_semantic", False)

            if is_semantic:
                action = f"Modified {ontology_id} ontology: {layout_details}"
                print(f"🔥 MIDDLEWARE: Capturing semantic ontology change: {layout_details}")
            else:
                # This is a pure layout change, skip it
                print(f"🔥 MIDDLEWARE: Skipping pure layout change for {ontology_id}")
                return None

            return {
                "action": action,
                "context": {
                    "ontology_id": ontology_id,
                    "workbench": "ontology",
                    "project_id": project_id,
                    "operation_details": layout_details
                },
                "metadata": {
                    "type": "ontology_layout",  # Keep same type that worked before
                    "graph": graph,
                    "project_id": project_id,
                    "detailed_operation": layout_details,
                    "is_semantic": is_semantic
                }
            }

        elif path == "/api/ontology/" and method == "POST":
            # Handle ontology creation
            project_id = query_params.get("project_id")
            print(f"🔥 MIDDLEWARE: Capturing ontology CREATION for project {project_id}")

            ontology_name = "default"

            # Extract ontology name from request body
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8')
                    body_json = json.loads(body_str)
                    if body_json.get("metadata", {}).get("name"):
                        ontology_name = body_json["metadata"]["name"]
            except:
                pass

            action = f"Created new ontology: {ontology_name}"

            return {
                "action": action,
                "context": {
                    "ontology_name": ontology_name,
                    "workbench": "ontology",
                    "operation_type": "ontology_creation",
                    "project_id": project_id
                },
                "metadata": {
                    "type": "ontology_layout",  # Use same type as working layout events
                    "is_semantic": True,
                    "is_creation": True,
                    "endpoint": "/api/ontology/",
                    "ontology_name": ontology_name,
                    "project_id": project_id
                }
            }

        elif path == "/api/ontology/" and method == "PUT":
            # Handle general ontology updates (semantic changes like adding classes, properties)
            project_id = query_params.get("project_id")
            print(f"🔥 MIDDLEWARE: Capturing general ontology update for project {project_id}")

            action = "Updated ontology with semantic changes"
            ontology_name = "default"

            # Try to extract what was changed from the request body
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8')
                    body_json = json.loads(body_str)

                    # Extract ontology name if available
                    if body_json.get("metadata", {}).get("name"):
                        ontology_name = body_json["metadata"]["name"]

                    changes = []
                    if body_json.get("classes"):
                        changes.append(f"{len(body_json['classes'])} classes")
                    if body_json.get("object_properties"):
                        changes.append(f"{len(body_json['object_properties'])} object properties")
                    if body_json.get("datatype_properties"):
                        changes.append(f"{len(body_json['datatype_properties'])} datatype properties")

                    if changes:
                        action = f"Updated {ontology_name} ontology: {', '.join(changes)}"
            except:
                pass

            return {
                "action": action,
                "context": {
                    "ontology_name": ontology_name,
                    "workbench": "ontology",
                    "operation_type": "semantic_update",
                    "project_id": project_id
                },
                "metadata": {
                    "type": "ontology_layout",  # Use same type as working layout events
                    "is_semantic": True,
                    "endpoint": "/api/ontology/",
                    "ontology_name": ontology_name,
                    "project_id": project_id
                }
            }

        elif "ontology/save" in path and method == "POST":
            graph = query_params.get("graph", "")
            ontology_id = graph.split("/")[-1] if graph else "unknown"
            project_id = self._extract_project_id_from_graph(graph)
            return {
                "action": f"Saved ontology {ontology_id}",
                "context": {"ontology_id": ontology_id, "workbench": "ontology", "project_id": project_id},
                "metadata": {"type": "ontology_save", "graph": graph, "project_id": project_id}
            }

        elif "ontology/classes" in path and method == "POST":
            graph = query_params.get("graph", "")
            ontology_id = graph.split("/")[-1] if graph else "unknown"
            project_id = self._extract_project_id_from_graph(graph)

            # Extract class creation details
            class_details = await self._extract_class_creation_details(request, response)

            action = f"Created ontology class in {ontology_id}"
            if class_details:
                action = f"Created {class_details} in {ontology_id} ontology"

            return {
                "action": action,
                "context": {
                    "ontology_id": ontology_id,
                    "workbench": "ontology",
                    "project_id": project_id,
                    "operation_details": class_details
                },
                "metadata": {
                    "type": "ontology_class_creation",
                    "graph": graph,
                    "project_id": project_id,
                    "class_details": class_details
                }
            }

        # Project operations
        elif path == "/api/projects" and method == "POST":
            # Try to extract project details from request body
            project_name = "Unknown"
            project_description = None
            try:
                if hasattr(request, '_body'):
                    body = json.loads(request._body)
                    project_name = body.get("name", "Unknown")
                    project_description = body.get("description")
            except:
                pass

            return {
                "action": f"Created project '{project_name}'",
                "context": {
                    "workbench": "project",
                    "project_name": project_name,
                    "project_description": project_description
                },
                "metadata": {
                    "type": "project_create",
                    "project_name": project_name,
                    "has_description": bool(project_description)
                }
            }

        elif path.startswith("/api/projects/") and method == "PUT":
            project_id = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"
            return {
                "action": f"Updated project {project_id}",
                "context": {"project_id": project_id, "workbench": "project"},
                "metadata": {"type": "project_update"}
            }

        # File operations
        elif "/api/files/upload" in path and method == "POST":
            project_id = query_params.get("project_id", "unknown")
            return {
                "action": "Uploaded file to project",
                "context": {"project_id": project_id, "workbench": "files"},
                "metadata": {"type": "file_upload"}
            }

        elif path.startswith("/api/files/") and method == "DELETE":
            file_id = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"
            return {
                "action": f"Deleted file {file_id}",
                "context": {"file_id": file_id, "workbench": "files"},
                "metadata": {"type": "file_delete"}
            }

        # Knowledge operations
        elif "/api/knowledge/query" in path and method == "POST":
            return {
                "action": "Searched knowledge base",
                "context": {"workbench": "knowledge"},
                "metadata": {"type": "knowledge_search"}
            }

        elif "/api/knowledge/assets" in path and method == "POST":
            return {
                "action": "Created knowledge asset",
                "context": {"workbench": "knowledge"},
                "metadata": {"type": "knowledge_create"}
            }

        # Workflow operations
        elif "/api/workflows/start" in path and method == "POST":
            return {
                "action": "Started workflow process",
                "context": {"workbench": "workflows"},
                "metadata": {"type": "workflow_start"}
            }

        # DAS interactions
        elif "/api/das/chat" in path and method == "POST":
            return {
                "action": "Interacted with DAS assistant",
                "context": {"workbench": "das"},
                "metadata": {"type": "das_chat"}
            }

        elif "/api/das/session" in path and method == "POST":
            return {
                "action": "Started DAS session",
                "context": {"workbench": "das"},
                "metadata": {"type": "das_session_start"}
            }

        # Default - still capture for analysis
        else:
            return {
                "action": f"{method} {path}",
                "context": {},
                "metadata": {"type": "api_call", "method": method, "path": path}
            }


def set_global_redis_client(redis_client):
    """Set global Redis client for middleware"""
    global _global_redis_client
    _global_redis_client = redis_client
    print(f"🔥 GLOBAL: Set global Redis client: {bool(redis_client)}")


def create_session_capture_middleware(redis_client):
    """Factory to create middleware with Redis client"""
    def middleware_factory(app: ASGIApp) -> SessionCaptureMiddleware:
        return SessionCaptureMiddleware(app, redis_client)
    return middleware_factory
