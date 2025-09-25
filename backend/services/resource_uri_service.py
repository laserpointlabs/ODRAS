"""
Dynamic Resource URI Service for ODRAS
Provides completely flexible, namespace-driven URI generation for all resource types.

Key Features:
- No hardcoded resource types - all from namespace configuration
- Uses 8-digit stable IDs instead of UUIDs
- Configurable installation prefix (no hardcoded "odras")
- Dynamic namespace paths from admin-created namespaces

Standards Compliance:
- RFC 3987: Internationalized Resource Identifiers (IRIs)
- W3C Semantic Web Best Practices
- W3C Cool URIs: Stable identifiers that never change
"""

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from .config import Settings
from .db import DatabaseService
from .stable_id_generator import generate_8_digit_id, is_8_digit_id

logger = logging.getLogger(__name__)


class ResourceURIService:
    """
    Dynamic URI generation service using admin-configured namespace paths.

    All ODRAS resource IRIs follow this dynamic pattern:
    {base_uri}/{installation_prefix}/{namespace_path}/{resource_ids...}#{entity_id}

    Examples:
    - https://xma-adt.usn.mil/usn/gov/dod/usn/project/23RT-56TW/45GH-34TG#B459-34TY
    - https://company.com/industry/boeing/core/67GH-89TY/12AB-34CD#X459-89QW
    - https://base.mil/gov/dod/usaf/domain/89JK-12LM/34EF-56GH#Z789-12AB

    No hardcoded resource types - everything comes from namespace configuration.
    """

    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)

        # Installation base domain (customer-configurable)
        self.installation_base_uri = settings.installation_base_uri.rstrip("/")

        # Installation prefix (configurable, can be empty)
        self.installation_prefix = settings.installation_prefix or ""

        logger.info(f"Initialized ResourceURIService with base: {self.installation_base_uri}")
        if self.installation_prefix:
            logger.info(f"Using installation prefix: '{self.installation_prefix}'")
        else:
            logger.info("No installation prefix configured - using clean URLs")

    def generate_dynamic_iri(
        self,
        namespace_path: str,
        resource_ids: List[str],
        entity_id: Optional[str] = None
    ) -> str:
        """
        Generate IRI using dynamic namespace path and 8-digit resource IDs.

        Args:
            namespace_path: Admin-created namespace path (e.g., "gov/dod/usn/project")
            resource_ids: List of 8-digit resource IDs (e.g., ["23RT-56TW", "45GH-34TG"])
            entity_id: Optional 8-digit entity ID (e.g., "B459-34TY")

        Returns:
            Complete IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/45GH-34TG#B459-34TY
        """
        # Build prefix path (configurable)
        prefix_path = f"/{self.installation_prefix}" if self.installation_prefix else ""

        # Build complete path: prefix + namespace + resource IDs
        path_parts = [namespace_path] + resource_ids
        full_path = "/".join(path_parts)

        # Build base IRI
        base_iri = f"{self.installation_base_uri}{prefix_path}/{full_path}"

        # Add entity fragment if provided
        if entity_id:
            return f"{base_iri}#{entity_id}"
        else:
            return f"{base_iri}/"

    def get_namespace_path(self, namespace_id: str) -> Optional[str]:
        """
        Get namespace path from namespace registry.

        Args:
            namespace_id: UUID of namespace in registry

        Returns:
            Namespace path like "gov/dod/usn/project" or None if not found
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT path FROM public.namespace_registry WHERE id = %s",
                        (namespace_id,)
                    )
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    return None
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get namespace path for {namespace_id}: {e}")
            return None

    def get_project_namespace_path(self, project_id: str) -> Optional[str]:
        """
        Get namespace path for a project.

        Args:
            project_id: Project's 8-digit ID

        Returns:
            Namespace path like "gov/dod/usn/project" or None if not found
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT n.path
                        FROM public.projects p
                        JOIN public.namespace_registry n ON n.id = p.namespace_id
                        WHERE p.stable_id = %s OR p.project_id = %s
                        """,
                        (project_id, project_id)
                    )
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    return None
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get project namespace path for {project_id}: {e}")
            return None

    def generate_project_iri(self, project_id: str) -> str:
        """
        Generate project IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID

        Returns:
            Project IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            logger.warning(f"No namespace found for project {project_id}, using fallback")
            namespace_path = "projects"  # Minimal fallback

        return self.generate_dynamic_iri(
            namespace_path=namespace_path,
            resource_ids=[project_id]
        )

    def generate_ontology_iri(self, project_id: str, ontology_id: str) -> str:
        """
        Generate ontology IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID
            ontology_id: Ontology's 8-digit stable ID

        Returns:
            Ontology IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/45GH-34TG/
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            logger.warning(f"No namespace found for project {project_id}, using fallback")
            namespace_path = "ontologies"

        return self.generate_dynamic_iri(
            namespace_path=namespace_path,
            resource_ids=[project_id, ontology_id]
        )

    def generate_entity_iri(
        self,
        project_id: str,
        ontology_id: str,
        entity_id: str
    ) -> str:
        """
        Generate ontology entity IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID
            ontology_id: Ontology's 8-digit stable ID
            entity_id: Entity's 8-digit stable ID

        Returns:
            Entity IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/45GH-34TG#B459-34TY
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            logger.warning(f"No namespace found for project {project_id}, using fallback")
            namespace_path = "entities"

        return self.generate_dynamic_iri(
            namespace_path=namespace_path,
            resource_ids=[project_id, ontology_id],
            entity_id=entity_id
        )

    def generate_file_iri(self, project_id: str, file_id: str) -> str:
        """
        Generate file IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID
            file_id: File's 8-digit stable ID

        Returns:
            File IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/files/67GH-89TY
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "files"

        # For files, we might want to add a "files" segment to the path
        # This could be configurable based on namespace configuration
        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/files",
            resource_ids=[project_id, file_id]
        )

    def generate_knowledge_asset_iri(self, project_id: str, asset_id: str) -> str:
        """
        Generate knowledge asset IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID
            asset_id: Asset's 8-digit stable ID

        Returns:
            Knowledge asset IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/knowledge/89JK-12LM
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "knowledge"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/knowledge",
            resource_ids=[project_id, asset_id]
        )

    def generate_simulation_iri(self, project_id: str, simulation_id: str) -> str:
        """
        Generate simulation IRI using dynamic namespace.

        Args:
            project_id: Project's 8-digit stable ID
            simulation_id: Simulation's 8-digit stable ID

        Returns:
            Simulation IRI like: https://base.mil/gov/dod/usn/project/23RT-56TW/simulations/45QR-67ST
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "simulations"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/simulations",
            resource_ids=[project_id, simulation_id]
        )

    def generate_analysis_iri(self, project_id: str, analysis_id: str) -> str:
        """
        Generate analysis IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "analysis"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/analysis",
            resource_ids=[project_id, analysis_id]
        )

    def generate_decision_iri(self, project_id: str, decision_id: str) -> str:
        """
        Generate decision record IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "decisions"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/decisions",
            resource_ids=[project_id, decision_id]
        )

    def generate_event_iri(self, project_id: str, event_id: str) -> str:
        """
        Generate event IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "events"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/events",
            resource_ids=[project_id, event_id]
        )

    def generate_requirement_iri(self, project_id: str, requirement_id: str) -> str:
        """
        Generate requirement IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "requirements"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/requirements",
            resource_ids=[project_id, requirement_id]
        )

    def generate_data_iri(self, project_id: str, data_id: str) -> str:
        """
        Generate data asset IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "data"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/data",
            resource_ids=[project_id, data_id]
        )

    def generate_model_iri(self, project_id: str, model_id: str) -> str:
        """
        Generate model IRI using dynamic namespace.
        """
        namespace_path = self.get_project_namespace_path(project_id)
        if not namespace_path:
            namespace_path = "models"

        return self.generate_dynamic_iri(
            namespace_path=f"{namespace_path}/models",
            resource_ids=[project_id, model_id]
        )

    def parse_iri_components(self, iri: str) -> Dict[str, Optional[str]]:
        """
        Parse an IRI into its components.

        Args:
            iri: Complete IRI to parse

        Returns:
            Dict with parsed components: installation_base, namespace_path, resource_ids, entity_id
        """
        try:
            # Remove base URI
            if not iri.startswith(self.installation_base_uri):
                return {"error": "IRI doesn't match this installation"}

            remaining = iri[len(self.installation_base_uri):].strip("/")

            # Remove installation prefix if present
            if self.installation_prefix and remaining.startswith(self.installation_prefix + "/"):
                remaining = remaining[len(self.installation_prefix + "/"):]

            # Split on fragment first
            if "#" in remaining:
                path_part, entity_id = remaining.split("#", 1)
            else:
                path_part = remaining.rstrip("/")
                entity_id = None

            # Parse path parts
            parts = path_part.split("/")

            # Identify 8-digit IDs vs namespace components
            resource_ids = []
            namespace_parts = []

            for part in parts:
                if is_8_digit_id(part):
                    resource_ids.append(part)
                else:
                    # Only add to namespace if no resource IDs found yet
                    if not resource_ids:
                        namespace_parts.append(part)

            namespace_path = "/".join(namespace_parts) if namespace_parts else None

            return {
                "installation_base": self.installation_base_uri,
                "installation_prefix": self.installation_prefix,
                "namespace_path": namespace_path,
                "resource_ids": resource_ids,
                "entity_id": entity_id,
                "full_path": path_part
            }

        except Exception as e:
            logger.error(f"Failed to parse IRI {iri}: {e}")
            return {"error": str(e)}

    def validate_installation_config(self) -> List[str]:
        """
        Validate the installation configuration.

        Returns:
            List of validation issues/warnings
        """
        issues = []

        base_uri = self.installation_base_uri

        # Check base URI format
        if not base_uri.startswith("http"):
            issues.append("Installation base URI should start with http:// or https://")

        # Check for proper domain format
        if not any(tld in base_uri for tld in [".mil", ".gov", ".com", ".org", ".edu", ".local"]):
            issues.append("Installation base URI should be a proper domain")

        # Check installation prefix
        if self.installation_prefix:
            if "/" in self.installation_prefix:
                issues.append("Installation prefix should not contain slashes")
            if not self.installation_prefix.isalnum():
                issues.append("Installation prefix should only contain alphanumeric characters")

        return issues

    def get_namespace_info(self, namespace_id: str) -> Dict:
        """
        Get complete namespace information.

        Args:
            namespace_id: UUID of namespace

        Returns:
            Dict with namespace details
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, name, type, path, prefix, status, description, owners
                        FROM public.namespace_registry
                        WHERE id = %s
                        """,
                        (namespace_id,)
                    )
                    result = cur.fetchone()
                    if result:
                        id, name, type, path, prefix, status, description, owners = result
                        return {
                            "id": id,
                            "name": name,
                            "type": type,
                            "path": path,
                            "prefix": prefix,
                            "status": status,
                            "description": description,
                            "owners": owners
                        }
                    return {"error": "Namespace not found"}
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get namespace info for {namespace_id}: {e}")
            return {"error": str(e)}


# Convenience function for getting URI service instance
def get_resource_uri_service(
    settings: Settings = None,
    db_service: DatabaseService = None
) -> ResourceURIService:
    """Get a ResourceURIService instance with proper dependencies."""
    if not settings:
        from .config import Settings
        settings = Settings()
    if not db_service:
        db_service = DatabaseService(settings)
    return ResourceURIService(settings, db_service)
