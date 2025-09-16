"""
Semantic Event Capture Service - Enhanced logging for session intelligence

Simple service to capture semantic events from API calls without middleware complexity.
Can be called directly from API endpoints or integrated with existing logging.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class SemanticEventCapture:
    """
    Service to capture and enhance API events with semantic meaning
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def capture_api_event(
        self,
        method: str,
        endpoint: str,
        username: str,
        session_thread_id: Optional[str] = None,
        query_params: Dict[str, Any] = None,
        request_data: Dict[str, Any] = None,
        response_data: Dict[str, Any] = None,
        status_code: int = 200
    ):
        """Capture an API event with enhanced semantics"""
        try:
            # Extract semantic meaning
            semantic_event = self._extract_semantic_meaning(
                method, endpoint, query_params, request_data, response_data
            )
            
            if not semantic_event:
                return  # Skip non-semantic events
            
            # Create clean event for Redis
            clean_event = {
                "event_id": f"api_{int(datetime.now().timestamp() * 1000)}",
                "session_thread_id": session_thread_id,
                "username": username,
                "timestamp": datetime.now().isoformat(),
                "event_type": semantic_event["event_type"],
                "semantic_action": semantic_event["semantic_action"],
                "context": semantic_event.get("context", {}),
                "metadata": semantic_event.get("metadata", {}),
                "success": 200 <= status_code < 300
            }
            
            # Queue for background processing
            if self.redis:
                await self.redis.lpush("api_events", json.dumps(clean_event))
                logger.debug(f"Captured semantic event: {semantic_event['semantic_action']} for {username}")
            
        except Exception as e:
            logger.error(f"Error capturing semantic event: {e}")
    
    def _extract_semantic_meaning(
        self,
        method: str,
        endpoint: str,
        query_params: Dict[str, Any] = None,
        request_data: Dict[str, Any] = None,
        response_data: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract semantic meaning from API call details"""
        
        query_params = query_params or {}
        request_data = request_data or {}
        response_data = response_data or {}
        
        # Ontology Operations
        if "ontology/layout" in endpoint and method == "PUT":
            graph_param = query_params.get("graph", "")
            ontology_id = graph_param.split("/")[-1] if graph_param else "unknown"
            project_id = self._extract_project_from_iri(graph_param)
            
            return {
                "event_type": "ontology_layout_modified",
                "semantic_action": f"Modified layout for ontology {ontology_id}",
                "context": {
                    "ontology_id": ontology_id,
                    "ontology_iri": graph_param,
                    "project_id": project_id
                },
                "metadata": {
                    "workbench": "ontology",
                    "action_type": "layout_modification"
                }
            }
        
        elif "ontology/save" in endpoint and method == "POST":
            graph_param = query_params.get("graph", "")
            ontology_id = graph_param.split("/")[-1] if graph_param else "unknown"
            project_id = self._extract_project_from_iri(graph_param)
            
            return {
                "event_type": "ontology_saved",
                "semantic_action": f"Saved ontology {ontology_id}",
                "context": {
                    "ontology_id": ontology_id,
                    "ontology_iri": graph_param,
                    "project_id": project_id
                },
                "metadata": {
                    "workbench": "ontology",
                    "action_type": "ontology_save"
                }
            }
        
        # Project Operations
        elif endpoint == "/api/projects" and method == "POST":
            project_name = request_data.get("name", "unknown")
            project_id = response_data.get("project", {}).get("project_id", "unknown")
            
            return {
                "event_type": "project_created",
                "semantic_action": f"Created project '{project_name}'",
                "context": {
                    "project_id": project_id,
                    "project_name": project_name
                },
                "metadata": {
                    "workbench": "project",
                    "action_type": "project_creation"
                }
            }
        
        # File Operations
        elif "/api/files/upload" in endpoint and method == "POST":
            project_id = query_params.get("project_id", "unknown")
            filename = response_data.get("file", {}).get("filename", "unknown")
            
            return {
                "event_type": "file_uploaded",
                "semantic_action": f"Uploaded file '{filename}' to project",
                "context": {
                    "project_id": project_id,
                    "filename": filename,
                    "file_id": response_data.get("file", {}).get("file_id")
                },
                "metadata": {
                    "workbench": "files",
                    "action_type": "file_upload"
                }
            }
        
        # Knowledge Operations
        elif "/api/knowledge/query" in endpoint and method == "POST":
            query_text = request_data.get("question", "unknown")
            project_id = request_data.get("project_id", "unknown")
            
            return {
                "event_type": "knowledge_searched",
                "semantic_action": f"Searched knowledge base for '{query_text}'",
                "context": {
                    "query": query_text,
                    "project_id": project_id
                },
                "metadata": {
                    "workbench": "knowledge",
                    "action_type": "knowledge_search"
                }
            }
        
        # DAS Operations
        elif "/api/das/chat" in endpoint and method == "POST":
            message = request_data.get("message", "unknown")
            
            return {
                "event_type": "das_interaction",
                "semantic_action": f"Asked DAS: '{message}'",
                "context": {
                    "message": message,
                    "project_id": request_data.get("project_id")
                },
                "metadata": {
                    "workbench": "das",
                    "action_type": "das_chat"
                }
            }
        
        # Skip health checks and non-semantic operations
        elif any(skip in endpoint for skip in ["/health", "/static", "/favicon", "/api/auth/me"]):
            return None
        
        # Generic API call for other operations
        else:
            return {
                "event_type": "api_call",
                "semantic_action": f"{method} request to {endpoint}",
                "context": {},
                "metadata": {
                    "method": method,
                    "endpoint": endpoint,
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


# Global service instance
semantic_capture: Optional[SemanticEventCapture] = None


async def initialize_semantic_capture(redis_client):
    """Initialize the semantic event capture service"""
    global semantic_capture
    semantic_capture = SemanticEventCapture(redis_client)
    logger.info("Semantic event capture service initialized")


async def capture_semantic_event(
    method: str,
    endpoint: str,
    username: str,
    session_thread_id: Optional[str] = None,
    **kwargs
):
    """Global function to capture semantic events from anywhere in the codebase"""
    if semantic_capture:
        await semantic_capture.capture_api_event(
            method=method,
            endpoint=endpoint,
            username=username,
            session_thread_id=session_thread_id,
            **kwargs
        )




