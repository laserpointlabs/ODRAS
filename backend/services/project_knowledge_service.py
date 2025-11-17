"""
Project Knowledge Service for ODRAS

Manages knowledge visibility and access across the project lattice.
Implements domain-wide knowledge dissemination and explicit cross-domain knowledge links.
"""

import logging
from typing import Dict, List, Optional, Any

from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class ProjectKnowledgeService:
    """
    Service for managing knowledge visibility and access in the project lattice.
    
    Implements the knowledge flow model from PROJECT_LATTICE_AND_KNOWLEDGE_FLOW.md:
    - In-domain knowledge: Domain-wide dissemination for published projects
    - Cross-domain knowledge: Explicit links required
    - Parent-child knowledge: Flows downward through layers
    """

    def __init__(self, settings: Settings = None, db_service: DatabaseService = None):
        self.settings = settings or Settings()
        self.db_service = db_service or DatabaseService(self.settings)

    def get_visible_knowledge(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all knowledge visible to a project.
        
        Returns:
            - In-domain published projects
            - Cross-domain projects with explicit links  
            - Parent chain (if cross-layer)
        """
        try:
            project = self._get_project(project_id)
            if not project:
                return []
            
            visible = []
            
            # 1. In-domain knowledge (domain-wide dissemination)
            if project.get("domain"):
                domain_projects = self.get_domain_knowledge(
                    project["domain"], publication_status="published"
                )
                # Exclude self
                domain_projects = [p for p in domain_projects if p["project_id"] != project_id]
                visible.extend(domain_projects)
            
            # 2. Cross-domain knowledge (explicit links)
            cross_domain_projects = self.get_cross_domain_knowledge(project_id)
            visible.extend(cross_domain_projects)
            
            # 3. Parent chain (cross-layer inheritance)
            parent_lineage = self.db_service.get_project_lineage(project_id)
            for parent in parent_lineage:
                if parent.get("publication_status") == "published":
                    # Only inherit from higher abstraction layers
                    parent_level = parent.get("project_level")
                    project_level = project.get("project_level")
                    
                    if (parent_level is not None and project_level is not None and 
                        parent_level < project_level):
                        visible.append(parent)
            
            # Remove duplicates by project_id
            seen_ids = set()
            unique_visible = []
            for proj in visible:
                proj_id = proj["project_id"]
                if proj_id not in seen_ids:
                    seen_ids.add(proj_id)
                    unique_visible.append(proj)
            
            return unique_visible
            
        except Exception as e:
            logger.error(f"Failed to get visible knowledge for project {project_id}: {e}")
            return []

    def get_domain_knowledge(
        self, domain: str, publication_status: str = "published"
    ) -> List[Dict[str, Any]]:
        """Get all published knowledge in a domain."""
        try:
            return self.db_service.get_domain_projects(domain, publication_status)
        except Exception as e:
            logger.error(f"Failed to get domain knowledge for {domain}: {e}")
            return []

    def get_cross_domain_knowledge(self, project_id: str) -> List[Dict[str, Any]]:
        """Get projects linked via explicit cross-domain knowledge links."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT p.project_id, p.name, p.domain, p.project_level, 
                                  p.publication_status, p.published_at,
                                  l.link_type, l.confidence, l.identified_by
                           FROM public.projects p
                           JOIN public.cross_domain_knowledge_links l ON l.target_project_id = p.project_id
                           WHERE l.source_project_id = %s
                           AND l.status = 'approved'
                           AND p.publication_status = 'published'
                           ORDER BY p.domain, p.name""",
                        (project_id,),
                    )
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get cross-domain knowledge for project {project_id}: {e}")
            return []

    def create_knowledge_link(
        self,
        source_project_id: str,
        target_project_id: str,
        link_type: str,
        identified_by: str = "user",
        confidence: Optional[float] = None,
        created_by: Optional[str] = None,
        source_element_iri: Optional[str] = None,
        target_element_iri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create explicit cross-domain knowledge link."""
        try:
            # Validate link (must be cross-domain)
            validation_result = self._validate_cross_domain_link(
                source_project_id, target_project_id
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO public.cross_domain_knowledge_links 
                           (source_project_id, target_project_id, link_type, source_element_iri, 
                            target_element_iri, identified_by, confidence, created_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING link_id, status""",
                        (source_project_id, target_project_id, link_type, source_element_iri,
                         target_element_iri, identified_by, confidence, created_by),
                    )
                    result = cur.fetchone()
                    conn.commit()
                    
                    return {
                        "success": True,
                        "link_id": result[0],
                        "status": result[1]
                    }
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to create knowledge link: {e}")
            return {
                "success": False,
                "error": f"Failed to create knowledge link: {str(e)}"
            }

    def approve_knowledge_link(
        self, link_id: str, approved_by: str
    ) -> Dict[str, Any]:
        """Approve a proposed cross-domain knowledge link."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE public.cross_domain_knowledge_links 
                           SET status = 'approved', approved_by = %s, approved_at = NOW()
                           WHERE link_id = %s AND status = 'proposed'""",
                        (approved_by, link_id),
                    )
                    
                    if cur.rowcount == 0:
                        return {
                            "success": False,
                            "error": "Knowledge link not found or already processed"
                        }
                    
                    conn.commit()
                    return {"success": True}
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to approve knowledge link {link_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to approve knowledge link: {str(e)}"
            }

    def get_knowledge_links(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all cross-domain knowledge links for a project."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT l.link_id, l.source_project_id, l.target_project_id,
                                  l.link_type, l.source_element_iri, l.target_element_iri,
                                  l.identified_by, l.confidence, l.status, l.approved_by,
                                  l.approved_at, l.created_at,
                                  p.name as target_project_name, p.domain as target_domain
                           FROM public.cross_domain_knowledge_links l
                           JOIN public.projects p ON l.target_project_id = p.project_id
                           WHERE l.source_project_id = %s
                           ORDER BY l.created_at DESC""",
                        (project_id,),
                    )
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get knowledge links for project {project_id}: {e}")
            return []

    def delete_knowledge_link(self, link_id: str) -> Dict[str, Any]:
        """Delete a cross-domain knowledge link."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.cross_domain_knowledge_links WHERE link_id = %s",
                        (link_id,),
                    )
                    
                    if cur.rowcount == 0:
                        return {"success": False, "error": "Knowledge link not found"}
                    
                    conn.commit()
                    return {"success": True}
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to delete knowledge link {link_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to delete knowledge link: {str(e)}"
            }

    def _get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project info."""
        return self.db_service.get_project(project_id)

    def _validate_cross_domain_link(
        self, source_project_id: str, target_project_id: str
    ) -> Dict[str, Any]:
        """Validate cross-domain knowledge link."""
        try:
            source_project = self._get_project(source_project_id)
            target_project = self._get_project(target_project_id)
            
            if not source_project:
                return {"valid": False, "error": "Source project not found"}
            if not target_project:
                return {"valid": False, "error": "Target project not found"}
            
            # Must be different domains
            source_domain = source_project.get("domain")
            target_domain = target_project.get("domain")
            
            if source_domain == target_domain:
                return {
                    "valid": False,
                    "error": (
                        "Cross-domain knowledge links must be between different domains. "
                        f"Both projects are in '{source_domain}' domain. "
                        "Use in-domain dissemination instead."
                    )
                }
            
            # Target must be published
            target_status = target_project.get("publication_status")
            if target_status != "published":
                return {
                    "valid": False,
                    "error": (
                        f"Target project must be published to create knowledge link. "
                        f"Current status: {target_status}"
                    )
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}


# Convenience function for getting service instance
def get_project_knowledge_service(
    settings: Settings = None, db_service: DatabaseService = None
) -> ProjectKnowledgeService:
    """Get a ProjectKnowledgeService instance with proper dependencies."""
    return ProjectKnowledgeService(settings, db_service)
