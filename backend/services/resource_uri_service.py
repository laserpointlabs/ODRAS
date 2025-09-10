"""
Resource URI Service for ODRAS
Provides consistent, namespace-aware URI generation for all resource types.
Follows the organizational URI design document specifications.
"""

import logging
import uuid
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class ResourceURIService:
    """
    Centralized URI generation service that follows namespace organization best practices.

    All ODRAS resource URIs follow this pattern:
    {installation_base_uri}/{namespace_path}/{project_uuid}/{resource_type}/{resource_name}

    Supports multi-tenant deployment and consistent namespace management.
    """

    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)

        # Installation base should be organizational domain only
        self.installation_base_uri = settings.installation_base_uri.rstrip("/")

        # Validate installation base URI doesn't include project paths
        if "/usn/" in self.installation_base_uri or "/adt/" in self.installation_base_uri:
            logger.warning(
                f"Installation base URI appears to include namespace paths: {self.installation_base_uri}. "
                "This should be just the organizational domain (e.g., https://ontology.navy.mil)"
            )

    def _get_project_namespace_info(self, project_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get project namespace information from database.

        Returns:
            Tuple of (namespace_path, project_name) or (None, None) if not found
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT p.name as project_name, n.path as namespace_path
                        FROM public.projects p
                        LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                        WHERE p.project_id = %s
                        """,
                        (project_id,),
                    )
                    result = cur.fetchone()
                    if result:
                        project_name, namespace_path = result
                        return namespace_path, project_name
                    return None, None
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.warning(f"Failed to get project namespace info for {project_id}: {e}")
            return None, None

    def generate_project_uri(self, project_id: str) -> str:
        """
        Generate project base URI.
        Format: {base_uri}/{namespace_path}/{project_uuid}/
        """
        namespace_path, project_name = self._get_project_namespace_info(project_id)

        if namespace_path:
            return f"{self.installation_base_uri}/{namespace_path}/{project_id}/"
        else:
            # Fallback for projects without namespace
            return f"{self.installation_base_uri}/projects/{project_id}/"

    def generate_ontology_uri(self, project_id: str, ontology_name: str) -> str:
        """
        Generate ontology URI.
        Format: {base_uri}/{namespace_path}/{project_uuid}/ontologies/{name}
        """
        namespace_path, project_name = self._get_project_namespace_info(project_id)

        # Sanitize ontology name for URI
        safe_name = self._sanitize_name(ontology_name)

        if namespace_path:
            return (
                f"{self.installation_base_uri}/{namespace_path}/{project_id}/ontologies/{safe_name}"
            )
        else:
            # Fallback for projects without namespace
            return f"{self.installation_base_uri}/projects/{project_id}/ontologies/{safe_name}"

    def generate_ontology_entity_uri(
        self, project_id: str, ontology_name: str, entity_name: str
    ) -> str:
        """
        Generate ontology entity URI (class, property, individual).
        Format: {base_uri}/{namespace_path}/{project_uuid}/ontologies/{name}#{entity}
        """
        ontology_uri = self.generate_ontology_uri(project_id, ontology_name)
        safe_entity = self._sanitize_name(entity_name)
        return f"{ontology_uri}#{safe_entity}"

    def generate_file_uri(
        self, project_id: str, file_name: str, file_id: Optional[str] = None
    ) -> str:
        """
        Generate file URI.
        Format: {base_uri}/{namespace_path}/{project_uuid}/files/{name}
        """
        namespace_path, project_name = self._get_project_namespace_info(project_id)

        # Use file_id if provided, otherwise sanitized filename
        resource_name = file_id if file_id else self._sanitize_name(file_name)

        if namespace_path:
            return (
                f"{self.installation_base_uri}/{namespace_path}/{project_id}/files/{resource_name}"
            )
        else:
            return f"{self.installation_base_uri}/projects/{project_id}/files/{resource_name}"

    def generate_knowledge_uri(
        self, project_id: str, asset_name: str, asset_id: Optional[str] = None
    ) -> str:
        """
        Generate knowledge asset URI.
        Format: {base_uri}/{namespace_path}/{project_uuid}/knowledge/{name}
        """
        namespace_path, project_name = self._get_project_namespace_info(project_id)

        # Use asset_id if provided, otherwise sanitized asset name
        resource_name = asset_id if asset_id else self._sanitize_name(asset_name)

        if namespace_path:
            return f"{self.installation_base_uri}/{namespace_path}/{project_id}/knowledge/{resource_name}"
        else:
            return f"{self.installation_base_uri}/projects/{project_id}/knowledge/{resource_name}"

    def generate_admin_uri(self, resource_type: str, resource_name: str) -> str:
        """
        Generate admin resource URI.
        Format: {base_uri}/admin/{resource_type}/{resource_name}
        """
        safe_type = self._sanitize_name(resource_type)
        safe_name = self._sanitize_name(resource_name)
        return f"{self.installation_base_uri}/admin/{safe_type}/{safe_name}"

    def generate_shared_uri(self, resource_type: str, resource_name: str) -> str:
        """
        Generate shared resource URI.
        Format: {base_uri}/shared/{resource_type}/{resource_name}
        """
        safe_type = self._sanitize_name(resource_type)
        safe_name = self._sanitize_name(resource_name)
        return f"{self.installation_base_uri}/shared/{safe_type}/{safe_name}"

    def parse_project_from_uri(self, uri: str) -> Optional[str]:
        """
        Extract project UUID from a resource URI.
        Handles both namespaced and non-namespaced URIs.
        """
        try:
            # Remove base URI
            if not uri.startswith(self.installation_base_uri):
                return None

            path = uri[len(self.installation_base_uri) :].strip("/")
            parts = path.split("/")

            # Look for UUID pattern in path segments
            for part in parts:
                if self._is_uuid(part):
                    return part

            return None
        except Exception as e:
            logger.warning(f"Failed to parse project from URI {uri}: {e}")
            return None

    def get_namespace_info(self, project_id: str) -> Dict[str, Optional[str]]:
        """
        Get complete namespace information for a project.

        Returns:
            Dict containing namespace_path, project_name, domain, etc.
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT p.project_id, p.name as project_name, p.domain,
                               n.path as namespace_path, n.name as namespace_name,
                               n.status as namespace_status
                        FROM public.projects p
                        LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                        WHERE p.project_id = %s
                        """,
                        (project_id,),
                    )
                    result = cur.fetchone()
                    if result:
                        (
                            project_id,
                            project_name,
                            domain,
                            namespace_path,
                            namespace_name,
                            namespace_status,
                        ) = result
                        return {
                            "project_id": project_id,
                            "project_name": project_name,
                            "domain": domain,
                            "namespace_path": namespace_path,
                            "namespace_name": namespace_name,
                            "namespace_status": namespace_status,
                            "project_base_uri": self.generate_project_uri(project_id),
                        }
                    return {"project_id": project_id}
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get namespace info for project {project_id}: {e}")
            return {"project_id": project_id, "error": str(e)}

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in URIs.
        Follows URI-safe naming conventions.
        """
        if not name:
            return "unnamed"

        # Convert to lowercase and replace spaces/special chars with hyphens
        sanitized = name.lower().strip()
        sanitized = sanitized.replace(" ", "-")
        sanitized = sanitized.replace("_", "-")

        # Remove any characters that aren't alphanumeric or hyphens
        import re

        sanitized = re.sub(r"[^a-z0-9\-]", "", sanitized)

        # Remove multiple consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    def _is_uuid(self, value: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False

    def validate_installation_config(self) -> List[str]:
        """
        Validate the installation configuration for best practices.

        Returns:
            List of warnings/issues found
        """
        issues = []

        # Check base URI format
        base_uri = self.installation_base_uri

        if not base_uri.startswith("http"):
            issues.append("Installation base URI should start with http:// or https://")

        # Check for common misconfigurations
        problematic_paths = ["/usn/", "/adt/", "/core/", "/projects/"]
        for path in problematic_paths:
            if path in base_uri:
                issues.append(
                    f"Installation base URI contains namespace path '{path}'. "
                    "It should be just the organizational domain (e.g., https://ontology.navy.mil)"
                )

        # Check if it ends with domain-like pattern
        if not any(tld in base_uri for tld in [".mil", ".gov", ".com", ".org", ".edu"]):
            issues.append("Installation base URI should be an organizational domain")

        return issues


# Convenience function for getting URI service instance
def get_resource_uri_service(
    settings: Settings = None, db_service: DatabaseService = None
) -> ResourceURIService:
    """Get a ResourceURIService instance with proper dependencies."""
    if not settings:
        settings = Settings()
    if not db_service:
        db_service = DatabaseService(settings)
    return ResourceURIService(settings, db_service)
