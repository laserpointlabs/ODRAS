"""
Session Capture Middleware - Enhanced with EventCapture2

Captures API calls with rich, semantic meaning using EventCapture2 system.
Features rich event summaries instead of generic ones.
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

        # CRITICAL: Capture request body BEFORE processing request (body gets consumed)
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                # Store in request for later use
                request._body = request_body
                print(f"🔥 MIDDLEWARE: Captured request body ({len(request_body)} bytes)")
            except Exception as e:
                print(f"🔥 MIDDLEWARE: Could not capture request body: {e}")

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
        """Capture events using EventCapture2 with rich context"""
        try:
            # Extract user info from auth header
            user_info = await self._get_user_info_from_request(request)
            if not user_info:
                return

            username = user_info["username"]
            user_id = user_info["user_id"]

            # Get EventCapture2 instance
            from backend.services.eventcapture2 import get_event_capture
            event_capture = get_event_capture()

            if not event_capture:
                print(f"🔥 MIDDLEWARE: EventCapture2 not initialized")
                return

            # Extract event details and route to appropriate EventCapture2 method
            response_time = time.time() - start_time
            captured = await self._route_to_eventcapture2(
                request, response, user_id, username, response_time, event_capture
            )

            if captured:
                print(f"🔥 EVENTCAPTURE2: Successfully captured rich event for {username}")
            else:
                print(f"🔥 EVENTCAPTURE2: Event not captured (filtered or no project context)")

        except Exception as e:
            logger.error(f"EventCapture2 middleware error: {e}")
            print(f"🔥 EVENTCAPTURE2: Error - {e}")
            import traceback
            print(f"🔥 EVENTCAPTURE2: Traceback - {traceback.format_exc()}")

    async def _get_username_from_request(self, request: Request) -> Optional[str]:
        """Extract username from request using proper auth system"""
        user_info = await self._get_user_info_from_request(request)
        return user_info["username"] if user_info else None

    async def _get_user_info_from_request(self, request: Request) -> Optional[Dict[str, str]]:
        """Extract user info (username and user_id) from request"""
        try:
            auth_header = request.headers.get("authorization", "")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Use the same authentication logic as the auth service
            from backend.services.auth import get_user
            try:
                user = get_user(auth_header)
                return {
                    "username": user.get("username"),
                    "user_id": user.get("user_id")
                }
            except Exception:
                # If auth fails, don't capture event (user not authenticated)
                return None
        except Exception:
            pass
            return None

    async def _route_to_eventcapture2(
        self,
        request: Request,
        response: Response,
        user_id: str,
        username: str,
        response_time: float,
        event_capture
    ) -> bool:
        """Route API calls to appropriate EventCapture2 methods for rich event summaries"""
        method = request.method
        path = str(request.url.path)
        query_params = dict(request.query_params)

        try:
            # Project operations
            if path == "/api/projects" and method == "POST":
                return await self._capture_project_created(request, user_id, username, response_time, event_capture)

            elif path.startswith("/api/projects/") and method == "PUT":
                return await self._capture_project_updated(request, path, user_id, username, response_time, event_capture)

            # Ontology operations - DISABLED (using direct endpoint capture instead)
            # elif path == "/api/ontologies" and method == "POST":
            #     return await self._capture_ontology_created_gui(request, user_id, username, response_time, event_capture)

            elif path == "/api/ontology/" and method == "PUT":
                return await self._capture_ontology_modified(request, query_params, user_id, username, response_time, event_capture)

            elif "ontology/save" in path and method == "POST":
                return await self._capture_ontology_saved(request, query_params, user_id, username, response_time, event_capture)

            elif "ontology/layout" in path and method == "PUT":
                return await self._capture_ontology_layout_modified(request, query_params, user_id, username, response_time, event_capture)

            # File operations
            elif "/api/files/upload" in path and method == "POST":
                return await self._capture_file_uploaded(request, query_params, user_id, username, response_time, event_capture)

            elif path.startswith("/api/files/") and method == "DELETE":
                return await self._capture_file_deleted(request, path, user_id, username, response_time, event_capture)

            # Workflow operations
            elif "/api/workflows/start" in path and method == "POST":
                return await self._capture_workflow_started(request, user_id, username, response_time, event_capture)

            # DAS interactions
            elif "/api/das2/chat" in path and method == "POST":
                return await self._capture_das_interaction(request, user_id, username, response_time, event_capture)

            # Knowledge operations
            elif "/api/knowledge/assets" in path and method == "POST" and not path.endswith(('public', 'content')):
                return await self._capture_knowledge_asset_created(request, user_id, username, response_time, event_capture)

            elif "/api/knowledge/assets/" in path and method == "PUT" and path.endswith("/public"):
                return await self._capture_knowledge_asset_published(request, path, user_id, username, response_time, event_capture)

            elif "/api/knowledge/assets/" in path and method == "PUT" and not path.endswith("/public"):
                return await self._capture_knowledge_asset_updated(request, path, user_id, username, response_time, event_capture)

            elif "/api/knowledge/search" in path and method == "POST":
                return await self._capture_knowledge_search(request, user_id, username, response_time, event_capture)

            elif "/api/knowledge/query" in path and method == "POST":
                return await self._capture_knowledge_rag_query(request, user_id, username, response_time, event_capture)

            else:
                # Not a tracked event type
                return False

        except Exception as e:
            logger.error(f"Error routing to EventCapture2: {e}")
            return False

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

    # EventCapture2 specific capture methods for rich context extraction

    async def _capture_project_created(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture project creation with rich context"""
        try:
            # Extract project details from request body
            body = await self._get_request_body(request)
            if not body:
                return False

            project_name = body.get("name", "Unknown Project")
            project_details = {
                "description": body.get("description"),
                "domain": body.get("domain"),
                "namespace_id": body.get("namespace_id")
            }

            # We don't have project_id yet (it's created by the endpoint), so we'll use a placeholder
            # The actual project_id will be available when the event is processed
            return await event_capture.capture_project_created(
                project_id="pending",  # Will be resolved later
                project_name=project_name,
                user_id=user_id,
                username=username,
                project_details=project_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing project creation: {e}")
            return False

    async def _capture_project_updated(self, request: Request, path: str, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture project updates with rich context"""
        try:
            # Extract project ID from path
            project_id = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"

            # Extract updated fields
            body = await self._get_request_body(request)
            if not body:
                return False

            # For now, just capture as a generic project event
            # This could be enhanced to show what fields were updated
            return await event_capture.capture_project_created(
                project_id=project_id,
                project_name=body.get("name", "Updated Project"),
                user_id=user_id,
                username=username,
                project_details={
                    "operation": "update",
                    "updated_fields": list(body.keys())
                },
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing project update: {e}")
            return False

    async def _capture_ontology_created(self, request: Request, query_params: dict, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture ontology creation with rich context"""
        try:
            project_id = query_params.get("project_id")
            if not project_id:
                return False

            # Extract ontology details
            body = await self._get_request_body(request)
            ontology_name = "default"

            if body and body.get("metadata", {}).get("name"):
                ontology_name = body["metadata"]["name"]

            operation_details = {
                "is_reference": body.get("is_reference", False) if body else False,
                "classes_count": len(body.get("classes", [])) if body else 0,
                "properties_count": len(body.get("object_properties", [])) + len(body.get("datatype_properties", [])) if body else 0
            }

            return await event_capture.capture_ontology_operation(
                operation_type="created",
                ontology_name=ontology_name,
                project_id=project_id,
                user_id=user_id,
                username=username,
                operation_details=operation_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing ontology creation: {e}")
            return False

    async def _capture_ontology_created_gui(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture ontology creation from GUI (/api/ontologies endpoint)"""
        try:
            print(f"🔥 DEBUG: Starting GUI ontology capture")
            body = await self._get_request_body(request)
            print(f"🔥 DEBUG: Body extracted: {body}")
            if not body:
                print(f"🔥 DEBUG: No body found - returning False")
                return False

            project_id = body.get('project', '')  # Note: this endpoint uses 'project' not 'project_id'
            print(f"🔥 DEBUG: Project ID: {project_id}")
            if not project_id:
                print(f"🔥 DEBUG: No project ID found - returning False")
                return False

            ontology_name = body.get('name', 'Unknown Ontology')
            ontology_label = body.get('label', ontology_name)
            is_reference = body.get('is_reference', False)

            print(f"🔥 DEBUG: Ontology details - name: {ontology_name}, label: {ontology_label}")

            operation_details = {
                'name': ontology_name,
                'label': ontology_label,
                'is_reference': is_reference,
                'classes_count': 0,  # New ontology starts empty
                'properties_count': 0,
                'created_via': 'gui'
            }

            print(f"🔥 DEBUG: Calling event_capture.capture_ontology_operation")
            result = await event_capture.capture_ontology_operation(
                operation_type="created",
                ontology_name=ontology_name,
                project_id=project_id,
                user_id=user_id,
                username=username,
                operation_details=operation_details,
                response_time=response_time
            )
            print(f"🔥 DEBUG: EventCapture2 result: {result}")
            return result

        except Exception as e:
            print(f"🔥 DEBUG: Exception in GUI ontology capture: {e}")
            logger.error(f"Error capturing GUI ontology creation: {e}")
            return False

    async def _capture_ontology_modified(self, request: Request, query_params: dict, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture ontology modifications with rich context"""
        try:
            project_id = query_params.get("project_id")
            if not project_id:
                return False

            # Extract ontology details
            body = await self._get_request_body(request)
            ontology_name = "default"

            if body and body.get("metadata", {}).get("name"):
                ontology_name = body["metadata"]["name"]

            operation_details = {
                "classes_count": len(body.get("classes", [])) if body else 0,
                "properties_count": len(body.get("object_properties", [])) + len(body.get("datatype_properties", [])) if body else 0,
                "relationships_modified": bool(body.get("object_properties")) if body else False
            }

            return await event_capture.capture_ontology_operation(
                operation_type="modified",
                ontology_name=ontology_name,
                project_id=project_id,
                user_id=user_id,
                username=username,
                operation_details=operation_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing ontology modification: {e}")
            return False

    async def _capture_ontology_saved(self, request: Request, query_params: dict, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture ontology saves with rich context"""
        try:
            graph = query_params.get("graph", "")
            project_id = self._extract_project_id_from_graph(graph)

            if not project_id:
                return False

            ontology_name = graph.split("/")[-1] if graph else "unknown"

            return await event_capture.capture_ontology_operation(
                operation_type="saved",
                ontology_name=ontology_name,
                project_id=project_id,
                user_id=user_id,
                username=username,
                operation_details={"graph_uri": graph},
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing ontology save: {e}")
            return False

    async def _capture_ontology_layout_modified(self, request: Request, query_params: dict, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture ontology layout modifications (only semantic ones)"""
        try:
            graph = query_params.get("graph", "")
            project_id = self._extract_project_id_from_graph(graph)

            if not project_id:
                return False

            # Analyze layout changes to determine if they're semantic
            layout_analysis = await self._extract_layout_changes(request)

            # Skip pure layout changes (positioning only)
            if layout_analysis and layout_analysis.get("is_layout_only", False):
                return False

            # Only capture semantic changes
            if not (layout_analysis and layout_analysis.get("is_semantic", False)):
                return False

            ontology_name = graph.split("/")[-1] if graph else "unknown"

            operation_details = {
                "layout_changes": layout_analysis.get("description"),
                "is_semantic": True,
                "graph_uri": graph
            }

            return await event_capture.capture_ontology_operation(
                operation_type="modified",
                ontology_name=ontology_name,
                project_id=project_id,
                user_id=user_id,
                username=username,
                operation_details=operation_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing ontology layout modification: {e}")
            return False

    async def _capture_file_uploaded(self, request: Request, query_params: dict, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture file uploads with rich context"""
        try:
            project_id = query_params.get("project_id")
            if not project_id:
                return False

            # Try to extract filename and file details from form data or headers
            filename = "uploaded_file"
            file_details = {}

            # This is approximate - actual file details would need to be extracted differently
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                # File upload via form data
                filename = "document"  # Would need actual form parsing
                file_details = {"content_type": content_type}

            return await event_capture.capture_file_operation(
                operation_type="uploaded",
                filename=filename,
                project_id=project_id,
                user_id=user_id,
                username=username,
                file_details=file_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing file upload: {e}")
            return False

    async def _capture_file_deleted(self, request: Request, path: str, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture file deletions with rich context"""
        try:
            file_id = path.split("/")[3] if len(path.split("/")) > 3 else "unknown"

            return await event_capture.capture_file_operation(
                operation_type="deleted",
                filename=f"file_{file_id}",
                project_id="unknown",  # Would need to be resolved
                user_id=user_id,
                username=username,
                file_details={"file_id": file_id},
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing file deletion: {e}")
            return False

    async def _capture_workflow_started(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture workflow starts with rich context"""
        try:
            body = await self._get_request_body(request)
            if not body:
                return False

            process_key = body.get("processKey", "unknown")
            project_id = body.get("projectId")

            workflow_details = {
                "fileIds": body.get("fileIds", []),
                "params": body.get("params", {}),
                "businessKey": body.get("businessKey")
            }

            return await event_capture.capture_workflow_started(
                process_key=process_key,
                project_id=project_id,
                user_id=user_id,
                username=username,
                workflow_details=workflow_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing workflow start: {e}")
            return False

    async def _capture_das_interaction(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture DAS interactions with rich context"""
        try:
            body = await self._get_request_body(request)
            if not body:
                return False

            project_id = body.get("project_id")
            if not project_id:
                return False

            message = body.get("message", "")

            interaction_details = {
                "message": message,
                "project_thread_id": body.get("project_thread_id"),
                "interaction_type": "question"
            }

            return await event_capture.capture_das_interaction(
                interaction_type="question",
                project_id=project_id,
                user_id=user_id,
                username=username,
                interaction_details=interaction_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing DAS interaction: {e}")
            return False

    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Safely extract request body as JSON"""
        try:
            # Try to get body from request (may have been consumed already)
            if hasattr(request, '_body'):
                body_bytes = request._body
            else:
                try:
                    body_bytes = await request.body()
                except:
                    return None

            if body_bytes:
                body_str = body_bytes.decode('utf-8')
                return json.loads(body_str)

            return None

        except Exception as e:
            logger.debug(f"Could not extract request body: {e}")
            return None

    # Knowledge event capture methods

    async def _capture_knowledge_asset_created(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture knowledge asset creation with rich context"""
        try:
            body = await self._get_request_body(request)
            if not body:
                return False

            title = body.get('title', 'Unknown Asset')

            # Extract project_id from request or body
            project_id = body.get('project_id')
            if not project_id:
                # Try to get from query params if not in body
                return False

            asset_details = {
                'document_type': body.get('document_type', 'unknown'),
                'source_file_id': body.get('source_file_id'),
                'content_summary': body.get('content_summary'),
                'metadata': body.get('metadata', {})
            }

            return await event_capture.capture_knowledge_asset_created(
                asset_id="pending",  # Will be assigned by the endpoint
                title=title,
                project_id=project_id,
                user_id=user_id,
                username=username,
                asset_details=asset_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing knowledge asset creation: {e}")
            return False

    async def _capture_knowledge_asset_updated(self, request: Request, path: str, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture knowledge asset updates with rich context"""
        try:
            asset_id = path.split("/")[-1] if "/" in path else "unknown"

            body = await self._get_request_body(request)
            if not body:
                return False

            # For knowledge asset updates, we don't always have project_id in the request
            # We'll use "unknown" and let the system try to resolve it later
            project_id = body.get('project_id', 'unknown')

            update_details = {
                'title': body.get('title'),
                'document_type': body.get('document_type'),
                'content_summary': body.get('content_summary'),
                'status': body.get('status'),
                'metadata': body.get('metadata')
            }

            return await event_capture.capture_knowledge_asset_updated(
                asset_id=asset_id,
                project_id=project_id,
                user_id=user_id,
                username=username,
                update_details=update_details,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing knowledge asset update: {e}")
            return False

    async def _capture_knowledge_asset_published(self, request: Request, path: str, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture knowledge asset publishing with rich context"""
        try:
            # Extract asset_id from path like /api/knowledge/assets/{asset_id}/public
            path_parts = path.split("/")
            asset_id = path_parts[-2] if len(path_parts) > 2 else "unknown"

            # We don't have project_id or asset_title from the request, so we'll use placeholders
            project_id = "unknown"  # Would need to be resolved from asset_id
            asset_title = f"Asset {asset_id}"  # Would need to be resolved from database

            return await event_capture.capture_knowledge_asset_published(
                asset_id=asset_id,
                asset_title=asset_title,
                project_id=project_id,
                user_id=user_id,
                username=username,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing knowledge asset publishing: {e}")
            return False

    async def _capture_knowledge_search(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture knowledge search with rich context"""
        try:
            body = await self._get_request_body(request)
            if not body:
                return False

            search_query = body.get('query', '') or body.get('search_term', '')
            if not search_query:
                return False

            project_id = body.get('project_id')  # May be None for global searches

            # We don't have search results from the middleware, so we'll use placeholders
            search_results = {
                'results_count': 0,  # Would need to be extracted from response
                'search_filters': body.get('filters', {}),
                'search_scope': body.get('scope', 'all')
            }

            return await event_capture.capture_knowledge_search(
                search_query=search_query,
                project_id=project_id,
                user_id=user_id,
                username=username,
                search_results=search_results,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing knowledge search: {e}")
            return False

    async def _capture_knowledge_rag_query(self, request: Request, user_id: str, username: str, response_time: float, event_capture) -> bool:
        """Capture RAG knowledge queries with rich context"""
        try:
            body = await self._get_request_body(request)
            if not body:
                return False

            query = body.get('question', '') or body.get('query', '')
            if not query:
                return False

            project_id = body.get('project_id')

            # We don't have query results from the middleware, so we'll use placeholders
            query_results = {
                'chunks_found': 0,  # Would need to be extracted from response
                'max_chunks': body.get('max_chunks', 5),
                'similarity_threshold': body.get('similarity_threshold', 0.7),
                'sources': []  # Would need to be extracted from response
            }

            return await event_capture.capture_knowledge_rag_query(
                query=query,
                project_id=project_id,
                user_id=user_id,
                username=username,
                query_results=query_results,
                response_time=response_time
            )

        except Exception as e:
            logger.error(f"Error capturing RAG query: {e}")
            return False


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
