"""
Installation-Specific IRI Service for ODRAS
Provides installation-aware IRI generation following military/government domain conventions.
"""

import logging
import uuid
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from datetime import datetime, timezone

from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class InstallationIRIService:
    """
    Installation-specific IRI generation service.
    
    Generates IRIs using installation-specific domains:
    https://{installation}.{service}.{tld}/program/{program}/project/{project}/{resource_type}/{resource}
    
    Examples:
    - https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf
    - https://afit-research.usaf.mil/core/ontologies/mission-planning
    """

    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
        
        # Parse installation configuration
        self.installation_name = settings.installation_name.lower()
        self.installation_type = settings.installation_type.lower()
        self.top_level_domain = settings.top_level_domain.lower()
        
        # Build installation-specific base URI
        self.installation_base_uri = self._build_installation_uri()
        
        logger.info(f"Initialized InstallationIRIService with base: {self.installation_base_uri}")

    def _build_installation_uri(self) -> str:
        """
        Build installation-specific base URI from configuration.
        
        Format: https://{installation}.{service}.{tld}
        Example: https://xma-adt.usn.mil
        """
        # Use configured base URI if it follows the installation-specific pattern
        configured_uri = self.settings.installation_base_uri.rstrip("/")
        
        # Check if configured URI follows installation-specific pattern
        expected_pattern = f"{self.installation_name}.{self.installation_type}.{self.top_level_domain}"
        if expected_pattern in configured_uri:
            return configured_uri
        
        # Generate installation-specific URI
        installation_uri = f"https://{self.installation_name}.{self.installation_type}.{self.top_level_domain}"
        
        logger.warning(
            f"Configured base URI '{configured_uri}' doesn't follow installation pattern. "
            f"Generated: '{installation_uri}'"
        )
        
        return installation_uri

    def _get_project_hierarchy(self, project_id: str) -> Dict[str, Optional[str]]:
        """
        Get project hierarchy information for IRI generation.
        
        Returns:
            Dict with program, project, namespace info
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.project_id, p.name as project_name, p.domain,
                               n.path as namespace_path, n.name as namespace_name,
                               n.type as namespace_type
                        FROM public.projects p
                        LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                        WHERE p.project_id = %s
                    """, (project_id,))
                    
                    result = cur.fetchone()
                    if result:
                        project_id, project_name, domain, namespace_path, namespace_name, namespace_type = result
                        
                        # Parse program from namespace path (e.g., 'usn/adt/x1' -> program='adt')
                        program = None
                        if namespace_path:
                            parts = namespace_path.split('/')
                            if len(parts) >= 2:
                                program = parts[1]  # Second part is typically program
                        
                        return {
                            "project_id": project_id,
                            "project_name": project_name,
                            "domain": domain,
                            "program": program,
                            "namespace_path": namespace_path,
                            "namespace_name": namespace_name,
                            "namespace_type": namespace_type
                        }
                    
                    return {"project_id": project_id}
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to get project hierarchy for {project_id}: {e}")
            return {"project_id": project_id, "error": str(e)}

    def generate_file_iri(self, project_id: str, filename: str, file_id: str) -> str:
        """
        Generate installation-specific IRI for a file.
        
        Format: https://{installation}.{service}.{tld}/program/{program}/project/{project}/files/{file_id}
        """
        hierarchy = self._get_project_hierarchy(project_id)
        program = hierarchy.get("program")
        
        safe_filename = self._sanitize_name(filename)
        
        if program:
            return f"{self.installation_base_uri}/program/{program}/project/{project_id}/files/{file_id}"
        else:
            # Fallback for projects without program
            return f"{self.installation_base_uri}/project/{project_id}/files/{file_id}"

    def generate_knowledge_iri(self, project_id: str, asset_title: str, asset_id: str) -> str:
        """
        Generate installation-specific IRI for a knowledge asset.
        
        Format: https://{installation}.{service}.{tld}/program/{program}/project/{project}/knowledge/{asset_id}
        """
        hierarchy = self._get_project_hierarchy(project_id)
        program = hierarchy.get("program")
        
        if program:
            return f"{self.installation_base_uri}/program/{program}/project/{project_id}/knowledge/{asset_id}"
        else:
            # Fallback for projects without program
            return f"{self.installation_base_uri}/project/{project_id}/knowledge/{asset_id}"

    def generate_project_iri(self, project_id: str) -> str:
        """
        Generate installation-specific IRI for a project.
        
        Format: https://{installation}.{service}.{tld}/program/{program}/project/{project_id}
        """
        hierarchy = self._get_project_hierarchy(project_id)
        program = hierarchy.get("program")
        
        if program:
            return f"{self.installation_base_uri}/program/{program}/project/{project_id}"
        else:
            return f"{self.installation_base_uri}/project/{project_id}"

    def generate_user_iri(self, user_id: str, username: str) -> str:
        """
        Generate installation-specific IRI for a user.
        
        Format: https://{installation}.{service}.{tld}/users/{username}
        """
        safe_username = self._sanitize_name(username)
        return f"{self.installation_base_uri}/users/{safe_username}"

    def generate_ontology_iri(self, project_id: str, ontology_name: str) -> str:
        """
        Generate installation-specific IRI for an ontology.
        
        Format: https://{installation}.{service}.{tld}/program/{program}/project/{project}/ontologies/{name}
        """
        hierarchy = self._get_project_hierarchy(project_id)
        program = hierarchy.get("program")
        safe_name = self._sanitize_name(ontology_name)
        
        if program:
            return f"{self.installation_base_uri}/program/{program}/project/{project_id}/ontologies/{safe_name}"
        else:
            return f"{self.installation_base_uri}/project/{project_id}/ontologies/{safe_name}"

    def generate_core_iri(self, resource_type: str, resource_name: str) -> str:
        """
        Generate installation-specific IRI for core resources.
        
        Format: https://{installation}.{service}.{tld}/core/{resource_type}/{name}
        """
        safe_type = self._sanitize_name(resource_type)
        safe_name = self._sanitize_name(resource_name)
        return f"{self.installation_base_uri}/core/{safe_type}/{safe_name}"

    def parse_iri_components(self, iri: str) -> Dict[str, Optional[str]]:
        """
        Parse an installation IRI into its components.
        
        Returns:
            Dict with installation, program, project, resource_type, resource_id
        """
        try:
            if not iri.startswith(self.installation_base_uri):
                return {"error": "IRI doesn't match this installation"}
            
            path = iri[len(self.installation_base_uri):].strip("/")
            parts = path.split("/")
            
            components = {"installation_base": self.installation_base_uri}
            
            if len(parts) >= 2 and parts[0] == "program":
                components["program"] = parts[1]
                if len(parts) >= 4 and parts[2] == "project":
                    components["project_id"] = parts[3]
                    if len(parts) >= 6:
                        components["resource_type"] = parts[4]
                        components["resource_id"] = parts[5]
            elif len(parts) >= 2 and parts[0] == "core":
                components["scope"] = "core"
                components["resource_type"] = parts[1]
                if len(parts) >= 3:
                    components["resource_id"] = parts[2]
            elif len(parts) >= 2 and parts[0] == "project":
                components["project_id"] = parts[1]
                if len(parts) >= 4:
                    components["resource_type"] = parts[2]
                    components["resource_id"] = parts[3]
            
            return components
            
        except Exception as e:
            logger.error(f"Failed to parse IRI {iri}: {e}")
            return {"error": str(e)}

    def validate_installation_config(self) -> List[str]:
        """
        Validate installation configuration for IRI compliance.
        
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check base URI format
        base_uri = self.installation_base_uri
        
        if not base_uri.startswith("https://"):
            issues.append("Installation base URI should use HTTPS for security")
        
        # Check for installation-specific pattern
        expected_pattern = f"{self.installation_name}.{self.installation_type}.{self.top_level_domain}"
        if expected_pattern not in base_uri:
            issues.append(
                f"Base URI should follow pattern: https://{expected_pattern}/ "
                f"(current: {base_uri})"
            )
        
        # Check TLD compliance
        valid_tlds = ["mil", "gov", "com", "edu", "org"]
        if self.top_level_domain not in valid_tlds:
            issues.append(f"Top-level domain should be one of: {valid_tlds}")
        
        # Check installation type
        valid_types = ["usn", "usaf", "usa", "usmc", "ussf", "industry", "research", "government"]
        if self.installation_type not in valid_types:
            issues.append(f"Installation type should be one of: {valid_types}")
        
        return issues

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in IRIs."""
        if not name:
            return "unnamed"
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        sanitized = name.lower().strip()
        sanitized = sanitized.replace(" ", "-")
        sanitized = sanitized.replace("_", "-")
        
        # Remove any characters that aren't alphanumeric or hyphens
        import re
        sanitized = re.sub(r"[^a-z0-9\-]", "", sanitized)
        
        # Remove multiple consecutive hyphens and leading/trailing hyphens
        sanitized = re.sub(r"-+", "-", sanitized).strip("-")
        
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


# Convenience function
def get_installation_iri_service(settings: Settings = None, db_service: DatabaseService = None) -> InstallationIRIService:
    """Get an InstallationIRIService instance with proper dependencies."""
    if not settings:
        settings = Settings()
    if not db_service:
        db_service = DatabaseService(settings)
    return InstallationIRIService(settings, db_service)

