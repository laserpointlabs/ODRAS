"""
Project Relationship Service for ODRAS

Manages cousin relationships between projects for cross-domain coordination.
Handles creation, validation, and querying of project relationships.
"""

import logging
from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class ProjectRelationshipService:
    """
    Service for managing cousin relationships between projects.
    
    Cousin relationships enable cross-domain coordination and collaboration
    without automatic knowledge flow (knowledge requires explicit links).
    """

    def __init__(self, settings: Settings = None, db_service: DatabaseService = None):
        self.settings = settings or Settings()
        self.db_service = db_service or DatabaseService(self.settings)

    def create_cousin_relationship(
        self,
        source_project_id: str,
        target_project_id: str,
        relationship_type: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a cousin relationship between projects."""
        try:
            # Validate relationship
            validation_result = self._validate_relationship(
                source_project_id, target_project_id, relationship_type
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
                        """INSERT INTO public.project_relationships 
                           (source_project_id, target_project_id, relationship_type, 
                            description, created_by)
                           VALUES (%s, %s, %s, %s, %s)
                           RETURNING relationship_id""",
                        (source_project_id, target_project_id, relationship_type,
                         description, created_by),
                    )
                    
                    relationship_id = cur.fetchone()[0]
                    conn.commit()
                    
                    return {
                        "success": True,
                        "relationship_id": relationship_id
                    }
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to create cousin relationship: {e}")
            return {
                "success": False,
                "error": f"Failed to create relationship: {str(e)}"
            }

    def get_cousin_projects(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all cousin projects (projects with relationships)."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get both directions: where project is source or target
                    cur.execute(
                        """
                        (SELECT r.relationship_id, r.relationship_type, r.description, r.created_at,
                                p.project_id, p.name, p.domain, p.project_level, 
                                p.publication_status, 'outgoing' as direction
                         FROM public.project_relationships r
                         JOIN public.projects p ON r.target_project_id = p.project_id
                         WHERE r.source_project_id = %s)
                        UNION
                        (SELECT r.relationship_id, r.relationship_type, r.description, r.created_at,
                                p.project_id, p.name, p.domain, p.project_level,
                                p.publication_status, 'incoming' as direction
                         FROM public.project_relationships r
                         JOIN public.projects p ON r.source_project_id = p.project_id
                         WHERE r.target_project_id = %s)
                        ORDER BY created_at DESC
                        """,
                        (project_id, project_id),
                    )
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get cousin projects for {project_id}: {e}")
            return []

    def get_relationships(
        self, 
        project_id: str, 
        relationship_type: Optional[str] = None,
        direction: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get project relationships with optional filtering."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT r.relationship_id, r.source_project_id, r.target_project_id,
                               r.relationship_type, r.description, r.created_at,
                               p1.name as source_name, p1.domain as source_domain,
                               p2.name as target_name, p2.domain as target_domain
                        FROM public.project_relationships r
                        JOIN public.projects p1 ON r.source_project_id = p1.project_id
                        JOIN public.projects p2 ON r.target_project_id = p2.project_id
                        WHERE (r.source_project_id = %s OR r.target_project_id = %s)
                    """
                    params = [project_id, project_id]
                    
                    if relationship_type:
                        query += " AND r.relationship_type = %s"
                        params.append(relationship_type)
                    
                    query += " ORDER BY r.created_at DESC"
                    
                    cur.execute(query, params)
                    relationships = [dict(row) for row in cur.fetchall()]
                    
                    # Filter by direction if specified
                    if direction:
                        if direction == "outgoing":
                            relationships = [r for r in relationships if r["source_project_id"] == project_id]
                        elif direction == "incoming":
                            relationships = [r for r in relationships if r["target_project_id"] == project_id]
                    
                    return relationships
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to get relationships for project {project_id}: {e}")
            return []

    def delete_relationship(self, relationship_id: str) -> Dict[str, Any]:
        """Delete a cousin relationship."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.project_relationships WHERE relationship_id = %s",
                        (relationship_id,),
                    )
                    
                    if cur.rowcount == 0:
                        return {"success": False, "error": "Relationship not found"}
                    
                    conn.commit()
                    return {"success": True}
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to delete relationship {relationship_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to delete relationship: {str(e)}"
            }

    def _validate_relationship(
        self, source_project_id: str, target_project_id: str, relationship_type: str
    ) -> Dict[str, Any]:
        """Validate cousin relationship."""
        try:
            # Basic validation
            if source_project_id == target_project_id:
                return {"valid": False, "error": "Project cannot be cousin to itself"}
            
            # Validate both projects exist
            source_project = self.db_service.get_project(source_project_id)
            target_project = self.db_service.get_project(target_project_id)
            
            if not source_project:
                return {"valid": False, "error": "Source project not found"}
            if not target_project:
                return {"valid": False, "error": "Target project not found"}
            
            # Validate relationship type
            valid_types = ["coordinates_with", "depends_on", "similar_to", "integrates_with"]
            if relationship_type not in valid_types:
                return {
                    "valid": False,
                    "error": f"Invalid relationship type. Must be one of: {valid_types}"
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}


# Convenience function for getting service instance
def get_project_relationship_service(
    settings: Settings = None, db_service: DatabaseService = None
) -> ProjectRelationshipService:
    """Get a ProjectRelationshipService instance with proper dependencies."""
    return ProjectRelationshipService(settings, db_service)
