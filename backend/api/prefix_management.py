"""
Prefix Management API for ODRAS
Controls organizational prefixes used in namespace creation
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
router = APIRouter(prefix="/api/admin/prefixes", tags=["prefix-management"])


# Pydantic models for request/response
class PrefixCreate(BaseModel):
    prefix: str = Field(
        ...,
        description="Prefix (lowercase letters and numbers only, 2-20 chars, e.g., 'dod', 'industry', 'lockheed')",
    )
    description: str = Field(..., description="Description of what the prefix represents")
    owner: str = Field(..., description="Owner email address")

    @validator("prefix")
    def validate_prefix(cls, v):
        # Validate prefix format: lowercase letters and numbers only, start with letter, 2-20 chars
        # Single word prefixes only - compound prefixes should be created from existing active prefixes
        if not re.match(r"^[a-z][a-z0-9]{1,19}$", v):
            raise ValueError(
                "Prefix must be lowercase letters and numbers only, start with letter, 2-20 characters"
            )
        return v


class PrefixUpdate(BaseModel):
    description: Optional[str] = Field(None, description="Updated description")
    owner: Optional[str] = Field(None, description="Updated owner email")
    status: Optional[str] = Field(None, description="Status: active, deprecated, archived")


class PrefixResponse(BaseModel):
    id: str
    prefix: str
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


# Prefix Management Endpoints


@router.post("/", response_model=PrefixResponse)
def create_prefix(
    prefix: PrefixCreate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Create a new prefix (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if prefix already exists
                cur.execute("SELECT id FROM prefix_registry WHERE prefix = %s", (prefix.prefix,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Prefix already exists")

                # Insert new prefix
                prefix_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO prefix_registry (id, prefix, description, owner, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        prefix_id,
                        prefix.prefix,
                        prefix.description,
                        prefix.owner,
                        admin_user["username"],
                    ),
                )
                conn.commit()

                # Return the created prefix
                cur.execute("SELECT * FROM prefix_registry WHERE id = %s", (prefix_id,))
                result = cur.fetchone()

                return PrefixResponse(
                    id=result[0],
                    prefix=result[1],
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
        logger.error(f"Error creating prefix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[PrefixResponse])
def list_prefixes(
    db: DatabaseService = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    """List all prefixes (public endpoint for namespace creation)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM prefix_registry"
                params = []

                if status_filter and status_filter != "all":
                    query += " WHERE status = %s"
                    params.append(status_filter)
                elif not status_filter:
                    query += " WHERE status = 'active'"

                query += " ORDER BY prefix ASC"

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    PrefixResponse(
                        id=row[0],
                        prefix=row[1],
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
        logger.error(f"Error listing prefixes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{prefix_id}", response_model=PrefixResponse)
def update_prefix(
    prefix_id: str,
    update_data: PrefixUpdate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Update prefix metadata (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if prefix exists
                cur.execute("SELECT prefix FROM prefix_registry WHERE id = %s", (prefix_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Prefix not found")

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
                params.append(prefix_id)

                query = f"UPDATE prefix_registry SET {', '.join(update_fields)} WHERE id = %s"
                cur.execute(query, params)
                conn.commit()

                # Return updated prefix
                cur.execute("SELECT * FROM prefix_registry WHERE id = %s", (prefix_id,))
                result = cur.fetchone()

                return PrefixResponse(
                    id=result[0],
                    prefix=result[1],
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
        logger.error(f"Error updating prefix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{prefix_id}")
def delete_prefix(
    prefix_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Delete a prefix (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if prefix exists
                cur.execute("SELECT prefix FROM prefix_registry WHERE id = %s", (prefix_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Prefix not found")

                # Check if prefix is used in any namespaces
                cur.execute(
                    "SELECT COUNT(*) FROM namespace_registry WHERE prefix = %s",
                    (result[0],),
                )
                usage_count = cur.fetchone()[0]
                if usage_count > 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete prefix '{result[0]}' - it is used by {usage_count} namespace(s)",
                    )

                # Delete the prefix
                cur.execute("DELETE FROM prefix_registry WHERE id = %s", (prefix_id,))
                conn.commit()

                return {"message": f"Prefix '{result[0]}' deleted successfully"}
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prefix: {e}")
        raise HTTPException(status_code=500, detail=str(e))
