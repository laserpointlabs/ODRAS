"""
Domain Management API for ODRAS
Controls organizational domains used for project classification
"""

import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator

from backend.services.db import DatabaseService
from backend.services.auth import get_admin_user
from backend.services.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/domains", tags=["domain-management"])

# Public router for non-admin endpoints
public_router = APIRouter(prefix="/api/domains", tags=["public-domains"])


# Pydantic models for request/response
class DomainCreate(BaseModel):
    domain: str = Field(
        ...,
        description="Domain name (lowercase letters, numbers, hyphens only, 2-50 chars)",
    )
    description: str = Field(..., description="Description of what the domain represents")
    owner: str = Field(..., description="Owner email address")

    @validator("domain")
    def validate_domain(cls, v):
        # Validate domain format: lowercase letters, numbers, hyphens only, start with letter, 2-50 chars
        if not re.match(r"^[a-z][a-z0-9-]{1,49}$", v):
            raise ValueError(
                "Domain must be lowercase letters, numbers, and hyphens only, start with letter, 2-50 characters"
            )
        return v


class DomainUpdate(BaseModel):
    description: Optional[str] = Field(None, description="Updated description")
    owner: Optional[str] = Field(None, description="Updated owner email")
    status: Optional[str] = Field(None, description="Status: active, deprecated, archived")


class DomainResponse(BaseModel):
    id: str
    domain: str
    description: str
    owner: str
    status: str
    created_at: str
    updated_at: str
    created_by: str


# Dependency injection
def get_db():
    settings = Settings()
    return DatabaseService(settings)


# Domain Management Endpoints (Admin Only)


@router.post("/", response_model=DomainResponse)
def create_domain(
    domain: DomainCreate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Create a new domain (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if domain already exists
                cur.execute("SELECT id FROM domain_registry WHERE domain = %s", (domain.domain,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Domain already exists")

                # Insert new domain
                domain_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO domain_registry (id, domain, description, owner, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        domain_id,
                        domain.domain,
                        domain.description,
                        domain.owner,
                        admin_user["username"],
                    ),
                )
                conn.commit()

                # Return the created domain
                cur.execute("SELECT * FROM domain_registry WHERE id = %s", (domain_id,))
                result = cur.fetchone()

                return DomainResponse(
                    id=result[0],
                    domain=result[1],
                    description=result[2],
                    owner=result[3],
                    status=result[4],
                    created_at=result[5].isoformat(),
                    updated_at=result[6].isoformat(),
                    created_by=result[7],
                )
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Get a specific domain by ID (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM domain_registry WHERE id = %s", (domain_id,))
                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Domain not found")

                return DomainResponse(
                    id=result[0],
                    domain=result[1],
                    description=result[2],
                    owner=result[3],
                    status=result[4],
                    created_at=result[5].isoformat(),
                    updated_at=result[6].isoformat(),
                    created_by=result[7],
                )
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DomainResponse])
def list_domains(
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    """List all domains (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM domain_registry"
                params = []

                if status_filter and status_filter != "all":
                    query += " WHERE status = %s"
                    params.append(status_filter)
                elif not status_filter:
                    query += " WHERE status = 'active'"

                query += " ORDER BY domain ASC"

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    DomainResponse(
                        id=row[0],
                        domain=row[1],
                        description=row[2],
                        owner=row[3],
                        status=row[4],
                        created_at=row[5].isoformat(),
                        updated_at=row[6].isoformat(),
                        created_by=row[7],
                    )
                    for row in results
                ]
        finally:
            db._return(conn)
    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{domain_id}", response_model=DomainResponse)
def update_domain(
    domain_id: str,
    update_data: DomainUpdate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Update domain metadata (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if domain exists
                cur.execute("SELECT domain FROM domain_registry WHERE id = %s", (domain_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Domain not found")

                # Build update query dynamically
                update_fields = []
                params = []

                if update_data.description is not None:
                    update_fields.append("description = %s")
                    params.append(update_data.description)

                if update_data.owner is not None:
                    update_fields.append("owner = %s")
                    params.append(update_data.owner)

                if update_data.status is not None:
                    update_fields.append("status = %s")
                    params.append(update_data.status)

                if not update_fields:
                    raise HTTPException(status_code=400, detail="No fields to update")

                update_fields.append("updated_at = NOW()")
                params.append(domain_id)

                query = f"UPDATE domain_registry SET {', '.join(update_fields)} WHERE id = %s"
                cur.execute(query, params)
                conn.commit()

                # Return updated domain
                cur.execute("SELECT * FROM domain_registry WHERE id = %s", (domain_id,))
                result = cur.fetchone()

                return DomainResponse(
                    id=result[0],
                    domain=result[1],
                    description=result[2],
                    owner=result[3],
                    status=result[4],
                    created_at=result[5].isoformat(),
                    updated_at=result[6].isoformat(),
                    created_by=result[7],
                )
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{domain_id}")
def delete_domain(
    domain_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Delete a domain (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if domain exists
                cur.execute("SELECT domain FROM domain_registry WHERE id = %s", (domain_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Domain not found")

                # Check if domain is used in any projects (when we add domain field to projects)
                # cur.execute("SELECT COUNT(*) FROM projects WHERE domain = %s", (result[0],))
                # usage_count = cur.fetchone()[0]
                # if usage_count > 0:
                #     raise HTTPException(
                #         status_code=400,
                #         detail=f"Cannot delete domain '{result[0]}' - it is used by {usage_count} project(s)"
                #     )

                # Delete the domain
                cur.execute("DELETE FROM domain_registry WHERE id = %s", (domain_id,))
                conn.commit()

                return {"message": f"Domain '{result[0]}' deleted successfully"}
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Public endpoint for active domains (no authentication required)
@public_router.get("/active", response_model=List[DomainResponse])
def list_active_domains(db: DatabaseService = Depends(get_db)):
    """List all active domains (public endpoint for project creation)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM domain_registry
                    WHERE status = 'active'
                    ORDER BY domain ASC
                """
                )
                results = cur.fetchall()

                return [
                    DomainResponse(
                        id=row[0],
                        domain=row[1],
                        description=row[2],
                        owner=row[3],
                        status=row[4],
                        created_at=row[5].isoformat(),
                        updated_at=row[6].isoformat(),
                        created_by=row[7],
                    )
                    for row in results
                ]
        finally:
            db._return(conn)
    except Exception as e:
        logger.error(f"Error listing active domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))

