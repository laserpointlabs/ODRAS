"""
Unified IRI Service for ODRAS
Clean, tenant-aware IRI generation for all resource types.
No legacy compatibility - modern implementation only.
"""

import logging
import uuid
import re
from typing import Dict, Optional
from urllib.parse import quote

from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class TenantContext:
    """Tenant context for IRI generation"""
    
    def __init__(self, tenant_id: str, tenant_code: str, tenant_name: str, base_iri: str):
        self.tenant_id = tenant_id
        self.tenant_code = tenant_code  # Short code for IRIs (usn-adt, afit-research)
        self.tenant_name = tenant_name  # Display name (USN ADT, AFIT Research)
        self.base_iri = base_iri.rstrip("/")  # Tenant-specific base IRI


class ResourceContext:
    """Resource context information for IRI generation"""
    
    def __init__(self, project_id: Optional[str] = None, namespace_path: Optional[str] = None,
                 project_name: Optional[str] = None, domain: Optional[str] = None):
        self.project_id = project_id
        self.namespace_path = namespace_path
        self.project_name = project_name
        self.domain = domain


class UnifiedIRIService:
    """
    Single, authoritative IRI generation service for all ODRAS resources.
    
    Clean tenant-aware IRI patterns:
    - Projects: {tenant_base}/{namespace}/{project_uuid}/
    - Ontologies: {tenant_base}/{namespace}/{project_uuid}/ontologies/{name}
    - Knowledge: {tenant_base}/{namespace}/{project_uuid}/knowledge/{id}
    - Files: {tenant_base}/{namespace}/{project_uuid}/files/{id}
    - Users: {tenant_base}/users/{username}
    """

    def __init__(self, tenant_context: TenantContext, db_service: Optional[DatabaseService] = None):
        self.tenant = tenant_context
        self.db_service = db_service
        
        # System tenant (tenant_id: 00000000-0000-0000-0000-000000000000)
        self.is_system_tenant = tenant_context.tenant_id == "00000000-0000-0000-0000-000000000000"
        
        logger.debug(f"Initialized UnifiedIRIService for tenant: {tenant_context.tenant_code}")

    # =======================
    # Core IRI Generation Methods
    # =======================

    def generate_project_iri(self, project_id: str) -> str:
        """
        Generate tenant-aware project IRI.
        Format: {tenant_base}/{namespace}/{project_uuid}/
        Example: https://odras.navy.mil/usn-adt/se/abc123-def456/
        """
        resource_context = self._get_resource_context(project_id)
        
        if resource_context.namespace_path:
            return f"{self.tenant.base_iri}/{resource_context.namespace_path}/{project_id}/"
        else:
            # Fallback for projects without namespace
            return f"{self.tenant.base_iri}/projects/{project_id}/"

    def generate_ontology_iri(self, project_id: str, ontology_name: str) -> str:
        """
        Generate ontology IRI.
        Format: {tenant_base}/{namespace}/{project_uuid}/ontologies/{name}
        """
        project_iri = self.generate_project_iri(project_id)
        safe_name = self._sanitize_name(ontology_name)
        return f"{project_iri}ontologies/{safe_name}"

    def generate_ontology_entity_iri(self, project_id: str, ontology_name: str, entity_name: str) -> str:
        """
        Generate ontology entity IRI (class, property, individual).
        Format: {tenant_base}/{namespace}/{project_uuid}/ontologies/{name}#{entity}
        """
        ontology_iri = self.generate_ontology_iri(project_id, ontology_name)
        safe_entity = self._sanitize_name(entity_name)
        return f"{ontology_iri}#{safe_entity}"

    def generate_knowledge_iri(self, project_id: str, knowledge_id: str) -> str:
        """
        Generate knowledge asset IRI.
        Format: {tenant_base}/{namespace}/{project_uuid}/knowledge/{id}
        """
        project_iri = self.generate_project_iri(project_id)
        safe_id = self._sanitize_name(knowledge_id)
        return f"{project_iri}knowledge/{safe_id}"

    def generate_file_iri(self, project_id: str, file_id: str) -> str:
        """
        Generate file IRI.
        Format: {tenant_base}/{namespace}/{project_uuid}/files/{id}
        """
        project_iri = self.generate_project_iri(project_id)
        safe_id = self._sanitize_name(file_id)
        return f"{project_iri}files/{safe_id}"

    def generate_user_iri(self, username: str) -> str:
        """
        Generate user IRI (tenant-scoped).
        Format: {tenant_base}/users/{username}
        """
        safe_username = self._sanitize_name(username)
        return f"{self.tenant.base_iri}/users/{safe_username}"

    def generate_requirement_iri(self, project_id: str, requirement_id: str) -> str:
        """
        Generate requirement IRI.
        Format: {tenant_base}/{namespace}/{project_uuid}/requirements/{id}
        """
        project_iri = self.generate_project_iri(project_id)
        safe_id = self._sanitize_name(requirement_id)
        return f"{project_iri}requirements/{safe_id}"

    def generate_das_iri(self, resource_type: str, resource_id: str) -> str:
        """
        Generate DAS-related IRI.
        Format: {tenant_base}/das/{resource_type}/{id}
        """
        safe_type = self._sanitize_name(resource_type)
        safe_id = self._sanitize_name(resource_id)
        return f"{self.tenant.base_iri}/das/{safe_type}/{safe_id}"

    # =======================
    # IRI Parsing and Analysis
    # =======================

    def parse_iri_components(self, iri: str) -> Dict[str, Optional[str]]:
        """
        Parse an IRI into its components.
        
        Returns:
            Dict with tenant_code, namespace_path, project_id, resource_type, resource_id
        """
        try:
            if not iri.startswith(self.tenant.base_iri):
                return {"error": "IRI doesn't match this tenant"}

            path = iri[len(self.tenant.base_iri):].strip("/")
            parts = path.split("/")

            components = {
                "tenant_code": self.tenant.tenant_code,
                "tenant_base": self.tenant.base_iri
            }

            # Parse standard pattern: /{namespace}/{project}/{resource_type}/{resource_id}
            if len(parts) >= 2:
                if self._is_uuid(parts[-2]):  # Second-to-last part is project UUID
                    # Standard project-based pattern
                    project_idx = -1
                    for i, part in enumerate(parts):
                        if self._is_uuid(part):
                            project_idx = i
                            break
                    
                    if project_idx > 0:
                        # Namespace path is everything before project UUID
                        components["namespace_path"] = "/".join(parts[:project_idx])
                    components["project_id"] = parts[project_idx]
                    
                    if len(parts) > project_idx + 1:
                        components["resource_type"] = parts[project_idx + 1]
                    if len(parts) > project_idx + 2:
                        components["resource_id"] = parts[project_idx + 2]
                
                elif parts[0] == "users":
                    # User pattern
                    components["resource_type"] = "user"
                    components["resource_id"] = parts[1] if len(parts) > 1 else None
                    
                elif parts[0] == "das":
                    # DAS pattern
                    components["scope"] = "das"
                    components["resource_type"] = parts[1] if len(parts) > 1 else None
                    components["resource_id"] = parts[2] if len(parts) > 2 else None
                    
                else:
                    # Other patterns
                    components["resource_type"] = parts[0]
                    components["resource_id"] = parts[1] if len(parts) > 1 else None

            return components

        except Exception as e:
            logger.error(f"Failed to parse IRI {iri}: {e}")
            return {"error": str(e)}

    def extract_project_id_from_iri(self, iri: str) -> Optional[str]:
        """Extract project UUID from any ODRAS IRI."""
        components = self.parse_iri_components(iri)
        return components.get("project_id")

    # =======================
    # Database Integration
    # =======================

    def _get_resource_context(self, project_id: str) -> ResourceContext:
        """Get resource context information from database."""
        if not self.db_service:
            return ResourceContext(project_id=project_id)
            
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.name as project_name, p.domain,
                               n.path as namespace_path
                        FROM public.projects p
                        LEFT JOIN public.namespace_registry n ON n.id = p.namespace_id
                        WHERE p.project_id = %s AND p.tenant_id = %s
                    """, (project_id, self.tenant.tenant_id))
                    
                    result = cur.fetchone()
                    if result:
                        project_name, domain, namespace_path = result
                        return ResourceContext(
                            project_id=project_id,
                            project_name=project_name,
                            domain=domain,
                            namespace_path=namespace_path
                        )
                    
                    return ResourceContext(project_id=project_id)
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.warning(f"Failed to get resource context for project {project_id}: {e}")
            return ResourceContext(project_id=project_id)

    # =======================
    # Validation
    # =======================

    def validate_tenant_iri_compliance(self) -> list[str]:
        """
        Validate tenant IRI configuration for compliance with ODRAS standards.
        
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check base IRI format
        base_iri = self.tenant.base_iri
        
        if not base_iri.startswith("https://"):
            issues.append("Tenant base IRI should use HTTPS for security")
        
        # Check tenant code format (kebab-case, 3-50 chars)
        tenant_code = self.tenant.tenant_code
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', tenant_code):
            issues.append("Tenant code must be kebab-case (lowercase, hyphens only)")
            
        if len(tenant_code) < 3 or len(tenant_code) > 50:
            issues.append("Tenant code must be 3-50 characters long")
        
        # Check for reserved tenant codes
        reserved_codes = ["system", "admin", "api", "www", "mail", "ftp"]
        if tenant_code in reserved_codes:
            issues.append(f"Tenant code '{tenant_code}' is reserved")
        
        # Check base IRI structure
        valid_tlds = [".mil", ".gov", ".com", ".edu", ".org"]
        if not any(tld in base_iri for tld in valid_tlds):
            issues.append("Base IRI should use a standard TLD (.mil, .gov, .com, .edu, .org)")
        
        return issues

    # =======================
    # Utility Methods
    # =======================

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in IRIs.
        Follows RFC 3987 IRI specifications and ODRAS naming conventions.
        """
        if not name:
            return "unnamed"

        # Convert to lowercase and replace spaces/underscores with hyphens
        sanitized = name.lower().strip()
        sanitized = sanitized.replace(" ", "-")
        sanitized = sanitized.replace("_", "-")

        # Remove any characters that aren't alphanumeric, hyphens, or periods
        sanitized = re.sub(r"[^a-z0-9\-\.]", "", sanitized)

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

    # =======================
    # Standard Namespace Mappings
    # =======================

    def get_standard_namespace_mappings(self) -> Dict[str, str]:
        """Get standard external namespace mappings for ontology imports."""
        return {
            # Government/DoD ontologies
            "gov": "https://w3id.org/defense/gov/core#",
            "dod": "https://w3id.org/defense/dod/core#",
            # Service ontologies
            "usn": "https://w3id.org/defense/usn/core#",
            "usaf": "https://w3id.org/defense/usaf/core#",
            "usa": "https://w3id.org/defense/usa/core#",
            "usmc": "https://w3id.org/defense/usmc/core#",
            "ussf": "https://w3id.org/defense/ussf/core#",
            # Domain ontologies
            "mission": "https://w3id.org/defense/dod/joint/mission#",
            "logistics": "https://w3id.org/defense/dod/joint/logistics#",
            # Standard ontologies
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "dct": "http://purl.org/dc/terms/",
        }


# =======================
# Factory Functions
# =======================

def create_tenant_context(tenant_id: str, tenant_code: str, tenant_name: str, base_iri: str) -> TenantContext:
    """Factory function to create TenantContext."""
    return TenantContext(tenant_id, tenant_code, tenant_name, base_iri)


def get_unified_iri_service(tenant_context: TenantContext, db_service: Optional[DatabaseService] = None) -> UnifiedIRIService:
    """Factory function to create UnifiedIRIService instance."""
    return UnifiedIRIService(tenant_context, db_service)


def get_system_tenant_iri_service(settings: Settings, db_service: Optional[DatabaseService] = None) -> UnifiedIRIService:
    """Get UnifiedIRIService instance for the system tenant."""
    system_tenant = TenantContext(
        tenant_id="00000000-0000-0000-0000-000000000000",
        tenant_code="system",
        tenant_name="System Resources",
        base_iri=f"{settings.installation_base_uri}/system"
    )
    return UnifiedIRIService(system_tenant, db_service)
