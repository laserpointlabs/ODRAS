"""
IRI Resolution API for ODRAS
Makes installation-specific IRIs dereferenceable by providing resource metadata and content.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.installation_iri_service import get_installation_iri_service
from ..services.auth import get_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iri", tags=["IRI Resolution"])


class IRIResolutionResponse(BaseModel):
    """Response for IRI resolution."""
    iri: str
    resource_type: str
    resource_id: str
    metadata: Dict[str, Any]
    content_url: Optional[str] = None
    resolved_at: str


def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService(Settings())


@router.get("/resolve")
async def resolve_iri(
    iri: str = Query(..., description="IRI to resolve"),
    include_content: bool = Query(False, description="Include content URL in response"),
    format: str = Query("json", description="Response format: json, rdf, turtle"),
    db: DatabaseService = Depends(get_db_service),
    user: Dict = Depends(get_user),
):
    """
    Resolve an IRI to its resource metadata.

    Makes ODRAS IRIs dereferenceable by returning resource information.
    Supports files, knowledge assets, projects, and users.
    """
    try:
        logger.info(f"Resolving IRI: {iri} for user {user.get('user_id')}")

        # Parse IRI to understand what we're looking for
        iri_service = get_installation_iri_service()
        components = iri_service.parse_iri_components(iri)

        if "error" in components:
            raise HTTPException(status_code=400, detail=f"Invalid IRI: {components['error']}")

        # Use database function to resolve IRI
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM resolve_iri(%s)", (iri,))
                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="IRI not found")

                resource_type, resource_id, resource_data = result

                # Check access permissions based on resource type
                if resource_type == "file":
                    # Check if user has access to the file's project
                    file_project_id = resource_data.get("project_id")
                    if file_project_id and not user.get("is_admin", False):
                        if not db.is_user_member(project_id=file_project_id, user_id=user["user_id"]):
                            raise HTTPException(status_code=403, detail="Access denied to this resource")

                elif resource_type == "knowledge_asset":
                    # Check if user has access to the knowledge asset's project
                    asset_project_id = resource_data.get("project_id")
                    if asset_project_id and not user.get("is_admin", False):
                        if not db.is_user_member(project_id=asset_project_id, user_id=user["user_id"]):
                            # Check if it's a public asset
                            if not resource_data.get("is_public", False):
                                raise HTTPException(status_code=403, detail="Access denied to this resource")

                # Generate content URL if requested
                content_url = None
                if include_content:
                    if resource_type == "file":
                        content_url = f"/api/files/{resource_id}/content"
                    elif resource_type == "knowledge_asset":
                        content_url = f"/api/knowledge/assets/{resource_id}/content"

                return IRIResolutionResponse(
                    iri=iri,
                    resource_type=resource_type,
                    resource_id=str(resource_id),
                    metadata=resource_data,
                    content_url=content_url,
                    resolved_at=datetime.now().isoformat()
                )

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve IRI {iri}: {e}")
        raise HTTPException(status_code=500, detail=f"IRI resolution failed: {str(e)}")


@router.get("/validate")
async def validate_iri_format(
    iri: str = Query(..., description="IRI to validate"),
):
    """
    Validate IRI format and structure.

    Checks if an IRI follows the installation-specific format without checking existence.
    """
    try:
        iri_service = get_installation_iri_service()
        components = iri_service.parse_iri_components(iri)

        if "error" in components:
            return {
                "valid": False,
                "error": components["error"],
                "iri": iri
            }

        return {
            "valid": True,
            "iri": iri,
            "components": components,
            "installation_base": iri_service.installation_base_uri
        }

    except Exception as e:
        logger.error(f"Failed to validate IRI {iri}: {e}")
        raise HTTPException(status_code=500, detail=f"IRI validation failed: {str(e)}")


@router.get("/installation-config")
async def get_installation_config(
    db: DatabaseService = Depends(get_db_service),
    user: Dict = Depends(get_user),
):
    """
    Get installation configuration for IRI generation.

    Returns the current installation configuration including base URI,
    organization info, and example IRI patterns.
    """
    try:
        # Get installation config from database
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT installation_name, installation_type, top_level_domain,
                           base_uri, organization, program_office, authority_contact
                    FROM installation_config
                    WHERE is_active = TRUE
                    LIMIT 1
                """)

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Installation configuration not found")

                config = dict(zip([
                    "installation_name", "installation_type", "top_level_domain",
                    "base_uri", "organization", "program_office", "authority_contact"
                ], result))

                # Generate example IRIs
                iri_service = get_installation_iri_service()
                examples = {
                    "project": f"{config['base_uri']}/program/abc/project/12345678-1234-1234-1234-123456789abc",
                    "file": f"{config['base_uri']}/program/abc/project/12345678-1234-1234-1234-123456789abc/files/requirements.pdf",
                    "knowledge": f"{config['base_uri']}/program/abc/project/12345678-1234-1234-1234-123456789abc/knowledge/mission-analysis",
                    "ontology": f"{config['base_uri']}/program/abc/project/12345678-1234-1234-1234-123456789abc/ontologies/requirements",
                    "core": f"{config['base_uri']}/core/ontologies/odras-base"
                }

                return {
                    "installation_config": config,
                    "iri_examples": examples,
                    "validation": iri_service.validate_installation_config()
                }

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get installation config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get installation config: {str(e)}")


# =============================================================================
# FEDERATED ACCESS ENDPOINTS (No Authentication Required)
# =============================================================================

@router.get("/public/resolve")
async def public_resolve_iri(
    iri: str = Query(..., description="IRI to resolve"),
    format: str = Query("json", description="Response format: json, rdf, turtle"),
    include_content_url: bool = Query(True, description="Include content access URL"),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Public IRI resolution endpoint for federated access.

    Allows external ODRAS installations and systems to resolve IRIs
    without authentication. Only returns public resources or metadata.

    This enables cross-installation artifact sharing and referencing.
    """
    try:
        logger.info(f"Public IRI resolution request: {iri}")

        # Parse IRI to understand what we're looking for
        iri_service = get_installation_iri_service()
        components = iri_service.parse_iri_components(iri)

        if "error" in components:
            raise HTTPException(status_code=400, detail=f"Invalid IRI: {components['error']}")

        # Use database function to resolve IRI
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM resolve_iri(%s)", (iri,))
                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="IRI not found")

                resource_type, resource_id, resource_data = result

                # For federated access, only return public resources or basic metadata
                if resource_type == "file":
                    # Check if file is public
                    if resource_data.get("visibility") != "public":
                        # Return basic metadata only for private files
                        return {
                            "iri": iri,
                            "resource_type": resource_type,
                            "status": "private",
                            "installation": iri_service.installation_base_uri,
                            "message": "This resource is private to this installation",
                            "contact": iri_service.settings.authority_contact
                        }

                elif resource_type == "knowledge_asset":
                    # Check if knowledge asset is public
                    if not resource_data.get("is_public", False):
                        return {
                            "iri": iri,
                            "resource_type": resource_type,
                            "status": "private",
                            "installation": iri_service.installation_base_uri,
                            "message": "This knowledge asset is private to this installation",
                            "contact": iri_service.settings.authority_contact
                        }

                # Generate federated access URLs
                access_urls = {}
                if include_content_url:
                    if resource_type == "file":
                        access_urls["download"] = f"{iri_service.installation_base_uri}/api/federated/files/{resource_id}/download"
                        access_urls["metadata"] = f"{iri_service.installation_base_uri}/api/federated/files/{resource_id}/metadata"
                    elif resource_type == "knowledge_asset":
                        access_urls["content"] = f"{iri_service.installation_base_uri}/api/federated/knowledge/{resource_id}/content"
                        access_urls["metadata"] = f"{iri_service.installation_base_uri}/api/federated/knowledge/{resource_id}/metadata"
                        access_urls["search"] = f"{iri_service.installation_base_uri}/api/federated/knowledge/{resource_id}/search"

                return {
                    "iri": iri,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id),
                    "status": "public",
                    "installation": iri_service.installation_base_uri,
                    "metadata": resource_data,
                    "access_urls": access_urls,
                    "resolved_at": datetime.now().isoformat(),
                    "authority": {
                        "organization": iri_service.settings.installation_organization,
                        "contact": iri_service.settings.authority_contact,
                        "installation": iri_service.settings.installation_name
                    }
                }

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve public IRI {iri}: {e}")
        raise HTTPException(status_code=500, detail=f"Public IRI resolution failed: {str(e)}")


@router.get("/public/artifact/{resource_type}/{resource_id}/metadata")
async def get_public_artifact_metadata(
    resource_type: str,
    resource_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get public artifact metadata by resource type and ID.

    Enables external systems to access artifact metadata using
    just the resource type and ID from an IRI.
    """
    try:
        logger.info(f"Public metadata request: {resource_type}/{resource_id}")

        conn = db._conn()
        try:
            with conn.cursor() as cur:
                if resource_type == "files":
                    cur.execute("""
                        SELECT f.*, 'file' as resource_type
                        FROM files f
                        WHERE f.id = %s AND (f.metadata->>'visibility' = 'public' OR f.metadata IS NULL)
                    """, (resource_id,))

                elif resource_type == "knowledge":
                    cur.execute("""
                        SELECT ka.*, 'knowledge_asset' as resource_type
                        FROM knowledge_assets ka
                        WHERE ka.id = %s AND ka.is_public = TRUE
                    """, (resource_id,))

                else:
                    raise HTTPException(status_code=400, detail="Unsupported resource type")

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Public resource not found")

                # Convert to dict
                resource_dict = dict(zip([desc[0] for desc in cur.description], result))

                # Generate access URLs
                iri_service = get_installation_iri_service()
                base_url = iri_service.installation_base_uri

                access_urls = {
                    "download": f"{base_url}/api/federated/{resource_type}/{resource_id}/download",
                    "metadata": f"{base_url}/api/federated/{resource_type}/{resource_id}/metadata"
                }

                return {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "metadata": resource_dict,
                    "access_urls": access_urls,
                    "installation": {
                        "base_uri": base_url,
                        "organization": iri_service.settings.installation_organization,
                        "contact": iri_service.settings.authority_contact
                    },
                    "accessed_at": datetime.now().isoformat()
                }

        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get public artifact metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get artifact metadata: {str(e)}")

