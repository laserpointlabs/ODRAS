"""
Simple Namespace Management API for ODRAS Phase 1
Provides basic admin-controlled namespace management
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from backend.services.db import DatabaseService
from backend.services.auth import get_admin_user
from backend.services.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/namespaces", tags=["namespace-management"])

# Public router for non-admin endpoints
public_router = APIRouter(prefix="/api/namespaces", tags=["public-namespaces"])


# Pydantic models for request/response
class NamespaceCreate(BaseModel):
    name: str = Field(..., description="Namespace name (e.g., 'dod-core')")
    type: str = Field(
        ...,
        description="Namespace type: core, service, domain, program, project, industry, vocab, shapes, align",
    )
    path: str = Field(..., description="Namespace path (e.g., 'dod/core')")
    prefix: str = Field(..., description="Namespace prefix (e.g., 'dod')")
    description: Optional[str] = Field(None, description="Namespace description")
    owners: List[str] = Field(default_factory=list, description="Owner email addresses")


class NamespaceUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Namespace status: draft, released, deprecated")
    owners: Optional[List[str]] = Field(None, description="Owner email addresses")
    description: Optional[str] = Field(None, description="Namespace description")


class NamespaceResponse(BaseModel):
    id: str
    name: str
    type: str
    path: str
    prefix: str
    status: str
    owners: List[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


# Dependency to get database service
def get_db():
    settings = Settings()
    return DatabaseService(settings)


# Namespace Management Endpoints


@router.post("/", response_model=NamespaceResponse)
def create_namespace(
    namespace: NamespaceCreate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Create a new namespace (admin only)"""
    try:
        # Validate namespace type
        valid_types = [
            "core",
            "service",
            "domain",
            "program",
            "project",
            "industry",
            "vocab",
            "shapes",
            "align",
        ]
        if namespace.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid namespace type. Must be one of: {', '.join(valid_types)}",
            )

        # Check if namespace name already exists
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM namespace_registry WHERE name = %s AND type = %s",
                    (namespace.name, namespace.type),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Namespace '{namespace.name}' of type '{namespace.type}' already exists",
                    )

                # Check if this namespace path already exists (not individual prefixes)
                cur.execute(
                    "SELECT id FROM namespace_registry WHERE path = %s",
                    (namespace.path,),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Namespace path '{namespace.path}' already exists",
                    )

                # Validate that prefix components (excluding the type) exist in prefix_registry
                path_components = namespace.path.split("/")
                valid_namespace_types = [
                    "core",
                    "service",
                    "domain",
                    "program",
                    "project",
                    "industry",
                    "vocab",
                    "shapes",
                    "align",
                ]

                # Check if the last component is a namespace type - if so, exclude it from prefix validation
                prefixes_to_validate = path_components
                if path_components and path_components[-1] in valid_namespace_types:
                    prefixes_to_validate = path_components[:-1]  # Exclude the type suffix

                for prefix in prefixes_to_validate:
                    if prefix:  # Skip empty components
                        cur.execute(
                            "SELECT id FROM prefix_registry WHERE prefix = %s AND status = 'active'",
                            (prefix,),
                        )
                        if not cur.fetchone():
                            raise HTTPException(
                                status_code=400,
                                detail=f"Prefix '{prefix}' does not exist or is not active. Create it in Prefix Management first.",
                            )

                # Create namespace
                namespace_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO namespace_registry (id, name, type, path, prefix, description, owners, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft')
                    """,
                    (
                        namespace_id,
                        namespace.name,
                        namespace.type,
                        namespace.path,
                        namespace.prefix,
                        namespace.description,
                        namespace.owners,
                    ),
                )
                conn.commit()

                # Create initial version
                version_id = str(uuid.uuid4())
                version_iri = f"https://w3id.org/defense/{namespace.path}/2025-01-01"
                cur.execute(
                    """
                    INSERT INTO namespace_versions (id, namespace_id, version, version_iri, status)
                    VALUES (%s, %s, %s, %s, 'draft')
                    """,
                    (version_id, namespace_id, "2025-01-01", version_iri),
                )
                conn.commit()

                # Fetch and return created namespace
                cur.execute("SELECT * FROM namespace_registry WHERE id = %s", (namespace_id,))
                result = cur.fetchone()

                return NamespaceResponse(
                    id=result[0],
                    name=result[1],
                    type=result[2],
                    path=result[3],
                    prefix=result[4],
                    status=result[5],
                    owners=result[6],
                    description=result[7],
                    created_at=result[8],
                    updated_at=result[9],
                )
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Error creating namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[NamespaceResponse])
def list_namespaces(
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
    type_filter: Optional[str] = Query(None, description="Filter by namespace type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    """List all namespaces (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM namespace_registry WHERE 1=1"
                params = []

                if type_filter:
                    query += " AND type = %s"
                    params.append(type_filter)

                if status_filter:
                    query += " AND status = %s"
                    params.append(status_filter)

                query += " ORDER BY created_at DESC"

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    NamespaceResponse(
                        id=row[0],  # id
                        name=row[1],  # name
                        type=row[2],  # type
                        path=row[3],  # path
                        prefix=row[4],  # prefix
                        status=row[5],  # status
                        owners=row[6],  # owners
                        description=row[7],  # description
                        created_at=row[8],  # created_at
                        updated_at=row[9],  # updated_at
                    )
                    for row in results
                ]
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Error listing namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{namespace_id}", response_model=NamespaceResponse)
def get_namespace(
    namespace_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Get namespace details (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM namespace_registry WHERE id = %s", (namespace_id,))
                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Namespace not found")

                return NamespaceResponse(
                    id=result[0],
                    name=result[1],
                    type=result[2],
                    path=result[3],
                    prefix=result[4],
                    status=result[5],
                    owners=result[6],
                    description=result[7],
                    created_at=result[8],
                    updated_at=result[9],
                )
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Error getting namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{namespace_id}", response_model=NamespaceResponse)
def update_namespace(
    namespace_id: str,
    update_data: NamespaceUpdate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Update namespace metadata (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if namespace exists
                cur.execute("SELECT id FROM namespace_registry WHERE id = %s", (namespace_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Namespace not found")

                # Update namespace
                cur.execute(
                    """
                    UPDATE namespace_registry 
                    SET status = %s, owners = %s, description = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        update_data.status,
                        update_data.owners,
                        update_data.description,
                        namespace_id,
                    ),
                )
                conn.commit()

                # Fetch and return updated namespace
                cur.execute("SELECT * FROM namespace_registry WHERE id = %s", (namespace_id,))
                result = cur.fetchone()

                return NamespaceResponse(
                    id=result[0],
                    name=result[1],
                    type=result[2],
                    path=result[3],
                    prefix=result[4],
                    status=result[5],
                    owners=result[6],
                    description=result[7],
                    created_at=result[8],
                    updated_at=result[9],
                )
        finally:
            db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Public endpoints for namespace discovery (no admin required)


@public_router.get("/public/namespaces", response_model=List[Dict[str, Any]])
def list_public_namespaces(
    db: DatabaseService = Depends(get_db),
    type_filter: Optional[str] = Query(None, description="Filter by namespace type"),
):
    """List public namespaces for import discovery"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = """
                SELECT nr.*, nv.version, nv.version_iri, nv.status as version_status
                FROM namespace_registry nr
                LEFT JOIN namespace_versions nv ON nr.id = nv.namespace_id AND nv.status = 'released'
                WHERE nr.status = 'released'
                """
                params = []

                if type_filter:
                    query += " AND nr.type = %s"
                    params.append(type_filter)

                query += " ORDER BY nr.created_at DESC"

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    {
                        "id": row[0],  # id
                        "name": row[1],  # name
                        "type": row[2],  # type
                        "path": row[3],  # path
                        "prefix": row[4],  # prefix
                        "description": row[7],  # description
                        "version": row[10] if len(row) > 10 else None,  # version
                        "version_iri": (row[11] if len(row) > 11 else None),  # version_iri
                        "version_status": (row[12] if len(row) > 12 else None),  # version_status
                    }
                    for row in results
                ]
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Error listing public namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@public_router.get("/available/namespaces", response_model=List[Dict[str, Any]])
def list_available_namespaces(
    db: DatabaseService = Depends(get_db),
    type_filter: Optional[str] = Query(None, description="Filter by namespace type"),
):
    """List all available namespaces for project ontology creation (includes draft and released)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                query = """
                SELECT nr.*, nv.version, nv.version_iri, nv.status as version_status
                FROM namespace_registry nr
                LEFT JOIN namespace_versions nv ON nr.id = nv.namespace_id AND nv.status = 'released'
                WHERE nr.status IN ('draft', 'released')
                """
                params = []

                if type_filter:
                    query += " AND nr.type = %s"
                    params.append(type_filter)

                query += " ORDER BY nr.status DESC, nr.created_at DESC"

                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    {
                        "id": row[0],  # id
                        "name": row[1],  # name
                        "type": row[2],  # type
                        "path": row[3],  # path
                        "prefix": row[4],  # prefix
                        "status": row[5],  # status
                        "owners": row[6],  # owners
                        "description": row[7],  # description
                        "version": row[8],  # version
                        "version_iri": row[9],  # version_iri
                        "version_status": row[10],  # version_status
                    }
                    for row in results
                ]
        finally:
            db._return(conn)

    except Exception as e:
        logger.error(f"Error listing available namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{namespace_id}")
def delete_namespace(
    namespace_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Delete a namespace (admin only)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if namespace exists
                cur.execute("SELECT name FROM namespace_registry WHERE id = %s", (namespace_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Namespace not found")

                # Check if namespace has any ontologies (optional safety check)
                # You might want to add this check depending on your requirements

                # Delete the namespace
                cur.execute("DELETE FROM namespace_registry WHERE id = %s", (namespace_id,))
                conn.commit()

                return {"message": f"Namespace '{result[0]}' deleted successfully"}
        finally:
            db._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Public endpoint for released namespaces (no authentication required)
@public_router.get("/released", response_model=List[NamespaceResponse])
def list_released_namespaces(db: DatabaseService = Depends(get_db)):
    """List all released namespaces (public endpoint for project creation)"""
    try:
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM namespace_registry 
                    WHERE status = 'released' 
                    ORDER BY path ASC
                """
                )
                results = cur.fetchall()

                return [
                    NamespaceResponse(
                        id=row[0],
                        name=row[1],
                        type=row[2],
                        path=row[3],
                        prefix=row[4],
                        status=row[5],
                        owners=row[6] or [],
                        description=row[7],
                        created_at=row[8],
                        updated_at=row[9],
                    )
                    for row in results
                ]
        finally:
            db._return(conn)
    except Exception as e:
        logger.error(f"Error listing released namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
