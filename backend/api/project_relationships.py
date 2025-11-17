"""
Project Relationship API endpoints for ODRAS

Manages cousin relationships, knowledge links, and hierarchy queries.
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.project_knowledge_service import ProjectKnowledgeService
from ..services.project_relationship_service import ProjectRelationshipService
from ..services.event_subscription_service import EventSubscriptionService
from ..services.auth import get_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Get services
def get_db() -> DatabaseService:
    return DatabaseService(Settings())

def get_knowledge_service() -> ProjectKnowledgeService:
    return ProjectKnowledgeService()

def get_relationship_service() -> ProjectRelationshipService:
    return ProjectRelationshipService()

def get_events_service() -> EventSubscriptionService:
    return EventSubscriptionService()

# Request models
class CreateRelationshipRequest(BaseModel):
    target_project_id: str
    relationship_type: str
    description: Optional[str] = None

class CreateKnowledgeLinkRequest(BaseModel):
    target_project_id: str
    link_type: str
    source_element_iri: Optional[str] = None
    target_element_iri: Optional[str] = None
    identified_by: str = "user"
    confidence: Optional[float] = None

class CreateSubscriptionRequest(BaseModel):
    event_type: str
    source_project_id: Optional[str] = None

class PublishEventRequest(BaseModel):
    event_type: str
    data: Dict[str, Any]


# ===========================================
# COUSIN RELATIONSHIP ENDPOINTS
# ===========================================

@router.post("/api/projects/{project_id}/relationships")
async def create_relationship(
    project_id: str,
    request: CreateRelationshipRequest,
    user=Depends(get_user),
    relationship_service: ProjectRelationshipService = Depends(get_relationship_service),
):
    """Create a cousin relationship between projects."""
    try:
        result = relationship_service.create_cousin_relationship(
            source_project_id=project_id,
            target_project_id=request.target_project_id,
            relationship_type=request.relationship_type,
            description=request.description,
            created_by=user.get("user_id"),
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "relationship_id": result["relationship_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")


@router.get("/api/projects/{project_id}/relationships")
async def list_relationships(
    project_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    direction: Optional[str] = Query(None, description="Filter by direction (incoming/outgoing)"),
    user=Depends(get_user),
    relationship_service: ProjectRelationshipService = Depends(get_relationship_service),
):
    """List all relationships for a project."""
    try:
        relationships = relationship_service.get_relationships(
            project_id, relationship_type, direction
        )
        
        return {
            "success": True,
            "relationships": relationships
        }
        
    except Exception as e:
        logger.error(f"Failed to list relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list relationships: {str(e)}")


@router.delete("/api/projects/{project_id}/relationships/{relationship_id}")
async def delete_relationship(
    project_id: str,
    relationship_id: str,
    user=Depends(get_user),
    relationship_service: ProjectRelationshipService = Depends(get_relationship_service),
):
    """Delete a cousin relationship."""
    try:
        # Verify project access (user must be member or admin)
        db_service = get_db()
        if not user.get("is_admin", False) and not db_service.is_user_member(project_id, user["user_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to modify this project")
        
        result = relationship_service.delete_relationship(relationship_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete relationship: {str(e)}")


# ===========================================
# HIERARCHY QUERY ENDPOINTS
# ===========================================

@router.get("/api/projects/{project_id}/children")
async def get_child_projects(
    project_id: str,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db),
):
    """Get all direct child projects."""
    try:
        children = db_service.get_child_projects(project_id)
        return {
            "success": True,
            "children": children
        }
        
    except Exception as e:
        logger.error(f"Failed to get child projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get children: {str(e)}")


@router.get("/api/projects/{project_id}/parent")
async def get_parent_project(
    project_id: str,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db),
):
    """Get parent project if exists."""
    try:
        parent = db_service.get_parent_project(project_id)
        return {
            "success": True,
            "parent": parent
        }
        
    except Exception as e:
        logger.error(f"Failed to get parent project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get parent: {str(e)}")


@router.get("/api/projects/{project_id}/cousins")
async def get_cousin_projects(
    project_id: str,
    user=Depends(get_user),
    relationship_service: ProjectRelationshipService = Depends(get_relationship_service),
):
    """Get all cousin projects (with relationships)."""
    try:
        cousins = relationship_service.get_cousin_projects(project_id)
        return {
            "success": True,
            "cousins": cousins
        }
        
    except Exception as e:
        logger.error(f"Failed to get cousin projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cousins: {str(e)}")


@router.get("/api/projects/{project_id}/lineage")
async def get_project_lineage(
    project_id: str,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db),
):
    """Get complete parent lineage up to L0."""
    try:
        lineage = db_service.get_project_lineage(project_id)
        return {
            "success": True,
            "lineage": lineage
        }
        
    except Exception as e:
        logger.error(f"Failed to get project lineage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get lineage: {str(e)}")


# ===========================================
# CROSS-DOMAIN KNOWLEDGE LINK ENDPOINTS
# ===========================================

@router.post("/api/projects/{project_id}/knowledge-links")
async def create_knowledge_link(
    project_id: str,
    request: CreateKnowledgeLinkRequest,
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """Create explicit cross-domain knowledge link."""
    try:
        result = knowledge_service.create_knowledge_link(
            source_project_id=project_id,
            target_project_id=request.target_project_id,
            link_type=request.link_type,
            source_element_iri=request.source_element_iri,
            target_element_iri=request.target_element_iri,
            identified_by=request.identified_by,
            confidence=request.confidence,
            created_by=user.get("user_id"),
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create knowledge link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge link: {str(e)}")


@router.get("/api/projects/{project_id}/knowledge-links")
async def list_knowledge_links(
    project_id: str,
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """List all cross-domain knowledge links for a project."""
    try:
        links = knowledge_service.get_knowledge_links(project_id)
        return {
            "success": True,
            "knowledge_links": links
        }
        
    except Exception as e:
        logger.error(f"Failed to list knowledge links: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge links: {str(e)}")


@router.put("/api/projects/{project_id}/knowledge-links/{link_id}/approve")
async def approve_knowledge_link(
    project_id: str,
    link_id: str,
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """Approve DAS-suggested knowledge link (SME approval)."""
    try:
        result = knowledge_service.approve_knowledge_link(
            link_id=link_id,
            approved_by=user.get("user_id")
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve knowledge link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve knowledge link: {str(e)}")


@router.delete("/api/projects/{project_id}/knowledge-links/{link_id}")
async def delete_knowledge_link(
    project_id: str,
    link_id: str,
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """Delete a cross-domain knowledge link."""
    try:
        # Verify project access
        db_service = get_db()
        if not user.get("is_admin", False) and not db_service.is_user_member(project_id, user["user_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to modify this project")
        
        result = knowledge_service.delete_knowledge_link(link_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge link: {str(e)}")


# ===========================================
# KNOWLEDGE VISIBILITY ENDPOINTS
# ===========================================

@router.get("/api/projects/{project_id}/visible-knowledge")
async def get_visible_knowledge(
    project_id: str,
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """Get all knowledge visible to this project."""
    try:
        visible_knowledge = knowledge_service.get_visible_knowledge(project_id)
        return {
            "success": True,
            "visible_knowledge": visible_knowledge
        }
        
    except Exception as e:
        logger.error(f"Failed to get visible knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visible knowledge: {str(e)}")


@router.get("/api/projects/{project_id}/domain-knowledge")
async def get_domain_knowledge(
    project_id: str,
    publication_status: Optional[str] = Query("published", description="Filter by publication status"),
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
    db_service: DatabaseService = Depends(get_db),
):
    """Get all knowledge in project's domain."""
    try:
        # Get project to find its domain
        project = db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        domain = project.get("domain")
        if not domain:
            return {"success": True, "domain_knowledge": []}
        
        domain_knowledge = knowledge_service.get_domain_knowledge(domain, publication_status)
        return {
            "success": True,
            "domain": domain,
            "domain_knowledge": domain_knowledge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get domain knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get domain knowledge: {str(e)}")


# ===========================================
# EVENT SUBSCRIPTION ENDPOINTS
# ===========================================

@router.post("/api/projects/{project_id}/subscriptions")
async def create_event_subscription(
    project_id: str,
    request: CreateSubscriptionRequest,
    user=Depends(get_user),
    event_service: EventSubscriptionService = Depends(get_events_service),
):
    """Subscribe project to an event type."""
    try:
        result = event_service.subscribe_to_event(
            project_id=project_id,
            event_type=request.event_type,
            source_project_id=request.source_project_id,
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.get("/api/projects/{project_id}/subscriptions")
async def list_event_subscriptions(
    project_id: str,
    user=Depends(get_user),
    event_service: EventSubscriptionService = Depends(get_events_service),
):
    """List all event subscriptions for a project."""
    try:
        subscriptions = event_service.get_subscriptions(project_id)
        return {
            "success": True,
            "subscriptions": subscriptions
        }
        
    except Exception as e:
        logger.error(f"Failed to list subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list subscriptions: {str(e)}")


@router.delete("/api/projects/{project_id}/subscriptions/{subscription_id}")
async def delete_event_subscription(
    project_id: str,
    subscription_id: str,
    user=Depends(get_user),
    event_service: EventSubscriptionService = Depends(get_events_service),
):
    """Delete an event subscription."""
    try:
        # Verify project access
        db_service = get_db()
        if not user.get("is_admin", False) and not db_service.is_user_member(project_id, user["user_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to modify this project")
        
        result = event_service.delete_subscription(subscription_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete subscription: {str(e)}")


@router.post("/api/projects/{project_id}/publish-event")
async def publish_project_event(
    project_id: str,
    request: PublishEventRequest,
    user=Depends(get_user),
    event_service: EventSubscriptionService = Depends(get_events_service),
):
    """Publish an event from this project."""
    try:
        # Verify project access
        db_service = get_db()
        if not user.get("is_admin", False) and not db_service.is_user_member(project_id, user["user_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to publish from this project")
        
        result = event_service.publish_event(
            source_project_id=project_id,
            event_type=request.event_type,
            event_data=request.data,
            created_by=user.get("user_id"),
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {str(e)}")


@router.get("/api/projects/{project_id}/subscribers")
async def get_event_subscribers(
    project_id: str,
    event_type: str = Query(..., description="Event type to check subscribers for"),
    user=Depends(get_user),
    event_service: EventSubscriptionService = Depends(get_events_service),
):
    """Get all projects subscribed to this project's events."""
    try:
        subscribers = event_service.get_subscribers(event_type, project_id)
        return {
            "success": True,
            "event_type": event_type,
            "subscribers": subscribers
        }
        
    except Exception as e:
        logger.error(f"Failed to get subscribers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subscribers: {str(e)}")


# ===========================================
# ENHANCED PROJECT LIST ENDPOINTS
# ===========================================

@router.get("/api/projects/by-level/{level}")
async def list_projects_by_level(
    level: int,
    domain: Optional[str] = Query(None, description="Filter by domain"),
    publication_status: Optional[str] = Query(None, description="Filter by publication status"),
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db),
):
    """List projects by layer level with optional filters."""
    try:
        if level not in [0, 1, 2, 3]:
            raise HTTPException(
                status_code=400, 
                detail="Level must be 0 (L0), 1 (L1), 2 (L2), or 3 (L3)"
            )
        
        # Build query with filters
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT p.project_id, p.name, p.description, p.domain, p.project_level,
                           p.publication_status, p.published_at, p.created_at
                    FROM public.projects p
                    JOIN public.project_members pm ON p.project_id = pm.project_id
                    WHERE pm.user_id = %s AND p.project_level = %s
                """
                params = [user["user_id"], level]
                
                if domain:
                    query += " AND p.domain = %s"
                    params.append(domain)
                
                if publication_status:
                    query += " AND p.publication_status = %s"
                    params.append(publication_status)
                
                query += " ORDER BY p.name"
                
                cur.execute(query, params)
                projects = [dict(row) for row in cur.fetchall()]
                
                return {
                    "success": True,
                    "level": level,
                    "projects": projects
                }
        finally:
            db_service._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list projects by level: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/api/projects/by-domain/{domain}")
async def list_projects_by_domain(
    domain: str,
    publication_status: Optional[str] = Query("published", description="Filter by publication status"),
    user=Depends(get_user),
    knowledge_service: ProjectKnowledgeService = Depends(get_knowledge_service),
):
    """List all projects in a domain."""
    try:
        projects = knowledge_service.get_domain_knowledge(domain, publication_status)
        return {
            "success": True,
            "domain": domain,
            "publication_status": publication_status,
            "projects": projects
        }
        
    except Exception as e:
        logger.error(f"Failed to list projects by domain: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")
