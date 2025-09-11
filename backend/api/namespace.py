"""
Namespace Management API for ODRAS Phase 1
Provides admin-controlled namespace and version management with Fuseki as single source of truth
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
from backend.services.namespace_sync import NamespaceSyncService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/namespaces", tags=["namespace-management"])


# Pydantic models for request/response
class NamespaceCreate(BaseModel):
    name: str = Field(..., description="Namespace name (e.g., 'dod-core')")
    type: str = Field(
        ...,
        description="Namespace type: core, domain, program, project, industry, vocab, shapes, align",
    )
    path: str = Field(..., description="Namespace path (e.g., 'dod/core')")
    prefix: str = Field(..., description="Namespace prefix (e.g., 'dod')")
    description: Optional[str] = Field(None, description="Namespace description")
    owners: List[str] = Field(default_factory=list, description="Owner email addresses")


class NamespaceUpdate(BaseModel):
    description: Optional[str] = None
    owners: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="Status: draft, released, deprecated")


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


class VersionCreate(BaseModel):
    version: str = Field(..., description="Version identifier (e.g., '2025-01-01')")
    description: Optional[str] = Field(None, description="Version description")


class VersionResponse(BaseModel):
    id: str
    namespace_id: str
    version: str
    version_iri: str
    status: str
    created_at: datetime
    released_at: Optional[datetime]


class ClassCreate(BaseModel):
    local_name: str = Field(..., description="Local class name (e.g., 'AirVehicle')")
    label: str = Field(..., description="Human-readable label (e.g., 'Air Vehicle')")
    comment: Optional[str] = Field(None, description="Class comment/description")


class ClassResponse(BaseModel):
    id: str
    version_id: str
    local_name: str
    label: str
    iri: str
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClassUpdate(BaseModel):
    label: Optional[str] = None
    comment: Optional[str] = None


# Dependency to get database service
def get_db():
    settings = Settings()
    return DatabaseService(settings)


# Dependency to get namespace sync service
def get_namespace_sync():
    return NamespaceSyncService()


# Namespace Management Endpoints


@router.post("/", response_model=NamespaceResponse)
async def create_namespace(
    namespace: NamespaceCreate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Create a new namespace (admin only)"""
    try:
        # Validate namespace type
        valid_types = [
            "core",
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
        existing = await db.fetch_one(
            "SELECT id FROM namespace_registry WHERE name = $1 AND type = $2",
            namespace.name,
            namespace.type,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Namespace '{namespace.name}' of type '{namespace.type}' already exists",
            )

        # Check if prefix already exists
        existing_prefix = await db.fetch_one(
            "SELECT id FROM namespace_registry WHERE prefix = $1", namespace.prefix
        )
        if existing_prefix:
            raise HTTPException(
                status_code=400, detail=f"Prefix '{namespace.prefix}' already exists"
            )

        # Create namespace
        namespace_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO namespace_registry (id, name, type, path, prefix, description, owners, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'draft')
            """,
            namespace_id,
            namespace.name,
            namespace.type,
            namespace.path,
            namespace.prefix,
            namespace.description,
            namespace.owners,
        )

        # Create initial version
        version_id = str(uuid.uuid4())
        version_iri = f"https://w3id.org/defense/{namespace.path}/{namespace.version}"
        await db.execute(
            """
            INSERT INTO namespace_versions (id, namespace_id, version, version_iri, status)
            VALUES ($1, $2, $3, $4, 'draft')
            """,
            version_id,
            namespace_id,
            "2025-01-01",
            version_iri,
        )

        # Fetch and return created namespace
        result = await db.fetch_one("SELECT * FROM namespace_registry WHERE id = $1", namespace_id)

        return NamespaceResponse(
            id=result["id"],
            name=result["name"],
            type=result["type"],
            path=result["path"],
            prefix=result["prefix"],
            status=result["status"],
            owners=result["owners"],
            description=result["description"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

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
async def get_namespace(
    namespace_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Get namespace details (admin only)"""
    try:
        result = await db.fetch_one("SELECT * FROM namespace_registry WHERE id = $1", namespace_id)

        if not result:
            raise HTTPException(status_code=404, detail="Namespace not found")

        return NamespaceResponse(
            id=result["id"],
            name=result["name"],
            type=result["type"],
            path=result["path"],
            prefix=result["prefix"],
            status=result["status"],
            owners=result["owners"],
            description=result["description"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

    except Exception as e:
        logger.error(f"Error getting namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{namespace_id}", response_model=NamespaceResponse)
async def update_namespace(
    namespace_id: str,
    namespace_update: NamespaceUpdate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Update namespace metadata (admin only)"""
    try:
        # Check if namespace exists
        existing = await db.fetch_one(
            "SELECT * FROM namespace_registry WHERE id = $1", namespace_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Namespace not found")

        # Build update query dynamically
        update_fields = []
        params = []
        param_count = 1

        if namespace_update.description is not None:
            update_fields.append(f"description = ${param_count}")
            params.append(namespace_update.description)
            param_count += 1

        if namespace_update.owners is not None:
            update_fields.append(f"owners = ${param_count}")
            params.append(namespace_update.owners)
            param_count += 1

        if namespace_update.status is not None:
            update_fields.append(f"status = ${param_count}")
            params.append(namespace_update.status)
            param_count += 1

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append(f"updated_at = NOW()")
        params.append(namespace_id)

        query = f"""
        UPDATE namespace_registry 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        """

        await db.execute(query, *params)

        # Fetch and return updated namespace
        result = await db.fetch_one("SELECT * FROM namespace_registry WHERE id = $1", namespace_id)

        return NamespaceResponse(
            id=result["id"],
            name=result["name"],
            type=result["type"],
            path=result["path"],
            prefix=result["prefix"],
            status=result["status"],
            owners=result["owners"],
            description=result["description"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

    except Exception as e:
        logger.error(f"Error updating namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Version Management Endpoints


@router.post("/{namespace_id}/versions", response_model=VersionResponse)
async def create_version(
    namespace_id: str,
    version: VersionCreate,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Create a new version for a namespace (admin only)"""
    try:
        # Check if namespace exists
        namespace = await db.fetch_one(
            "SELECT * FROM namespace_registry WHERE id = $1", namespace_id
        )
        if not namespace:
            raise HTTPException(status_code=404, detail="Namespace not found")

        # Check if version already exists
        existing = await db.fetch_one(
            "SELECT id FROM namespace_versions WHERE namespace_id = $1 AND version = $2",
            namespace_id,
            version.version,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Version '{version.version}' already exists for this namespace",
            )

        # Create version
        version_id = str(uuid.uuid4())
        version_iri = f"https://w3id.org/defense/{namespace['path']}/{version.version}"

        await db.execute(
            """
            INSERT INTO namespace_versions (id, namespace_id, version, version_iri, status)
            VALUES ($1, $2, $3, $4, 'draft')
            """,
            version_id,
            namespace_id,
            version.version,
            version_iri,
        )

        # Fetch and return created version
        result = await db.fetch_one("SELECT * FROM namespace_versions WHERE id = $1", version_id)

        return VersionResponse(
            id=result["id"],
            namespace_id=result["namespace_id"],
            version=result["version"],
            version_iri=result["version_iri"],
            status=result["status"],
            created_at=result["created_at"],
            released_at=result["released_at"],
        )

    except Exception as e:
        logger.error(f"Error creating version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{namespace_id}/versions", response_model=List[VersionResponse])
async def list_versions(
    namespace_id: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """List all versions for a namespace (admin only)"""
    try:
        results = await db.fetch_all(
            "SELECT * FROM namespace_versions WHERE namespace_id = $1 ORDER BY created_at DESC",
            namespace_id,
        )

        return [
            VersionResponse(
                id=row["id"],
                namespace_id=row["namespace_id"],
                version=row["version"],
                version_iri=row["version_iri"],
                status=row["status"],
                created_at=row["created_at"],
                released_at=row["released_at"],
            )
            for row in results
        ]

    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Class Management Endpoints


@router.post("/{namespace_id}/versions/{version}/classes", response_model=ClassResponse)
async def create_class(
    namespace_id: str,
    version: str,
    class_data: ClassCreate,
    db: DatabaseService = Depends(get_db),
    namespace_sync: NamespaceSyncService = Depends(get_namespace_sync),
    admin_user=Depends(get_admin_user),
):
    """Create a new class in a namespace version (admin only)"""
    try:
        # Get version details
        version_info = await db.fetch_one(
            """
            SELECT nv.*, nr.path, nr.prefix 
            FROM namespace_versions nv
            JOIN namespace_registry nr ON nv.namespace_id = nr.id
            WHERE nv.namespace_id = $1 AND nv.version = $2
            """,
            namespace_id,
            version,
        )

        if not version_info:
            raise HTTPException(status_code=404, detail="Version not found")

        # Check if class already exists in this version
        existing = await db.fetch_one(
            "SELECT id FROM namespace_classes WHERE version_id = $1 AND local_name = $2",
            version_info["id"],
            class_data.local_name,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Class '{class_data.local_name}' already exists in this version",
            )

        # Create class
        class_id = str(uuid.uuid4())
        iri = f"https://w3id.org/defense/{version_info['path']}#{class_data.local_name}"

        await db.execute(
            """
            INSERT INTO namespace_classes (id, version_id, local_name, label, iri, comment)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            class_id,
            version_info["id"],
            class_data.local_name,
            class_data.label,
            iri,
            class_data.comment,
        )

        # Sync to Fuseki
        class_sync_data = {
            "iri": iri,
            "local_name": class_data.local_name,
            "label": class_data.label,
            "comment": class_data.comment,
        }

        sync_success = await namespace_sync.sync_class_to_fuseki(
            version_info["path"], version, class_sync_data
        )

        if not sync_success:
            logger.warning(
                f"Failed to sync class {class_data.local_name} to Fuseki, but database record created"
            )

        # Fetch and return created class
        result = await db.fetch_one("SELECT * FROM namespace_classes WHERE id = $1", class_id)

        return ClassResponse(
            id=result["id"],
            version_id=result["version_id"],
            local_name=result["local_name"],
            label=result["label"],
            iri=result["iri"],
            comment=result["comment"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

    except Exception as e:
        logger.error(f"Error creating class: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{namespace_id}/versions/{version}/classes", response_model=List[ClassResponse])
async def list_classes(
    namespace_id: str,
    version: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """List all classes in a namespace version (admin only)"""
    try:
        # Get version ID
        version_info = await db.fetch_one(
            "SELECT id FROM namespace_versions WHERE namespace_id = $1 AND version = $2",
            namespace_id,
            version,
        )

        if not version_info:
            raise HTTPException(status_code=404, detail="Version not found")

        results = await db.fetch_all(
            "SELECT * FROM namespace_classes WHERE version_id = $1 ORDER BY local_name",
            version_info["id"],
        )

        return [
            ClassResponse(
                id=row["id"],
                version_id=row["version_id"],
                local_name=row["local_name"],
                label=row["label"],
                iri=row["iri"],
                comment=row["comment"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in results
        ]

    except Exception as e:
        logger.error(f"Error listing classes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{namespace_id}/versions/{version}/classes/{class_id}",
    response_model=ClassResponse,
)
async def update_class(
    namespace_id: str,
    version: str,
    class_id: str,
    class_update: ClassUpdate,
    db: DatabaseService = Depends(get_db),
    namespace_sync: NamespaceSyncService = Depends(get_namespace_sync),
    admin_user=Depends(get_admin_user),
):
    """Update a class in a namespace version (admin only)"""
    try:
        # Get version ID
        version_info = await db.fetch_one(
            "SELECT id FROM namespace_versions WHERE namespace_id = $1 AND version = $2",
            namespace_id,
            version,
        )

        if not version_info:
            raise HTTPException(status_code=404, detail="Version not found")

        # Check if class exists
        existing = await db.fetch_one(
            "SELECT * FROM namespace_classes WHERE id = $1 AND version_id = $2",
            class_id,
            version_info["id"],
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Class not found")

        # Build update query
        update_fields = []
        params = []
        param_count = 1

        if class_update.label is not None:
            update_fields.append(f"label = ${param_count}")
            params.append(class_update.label)
            param_count += 1

        if class_update.comment is not None:
            update_fields.append(f"comment = ${param_count}")
            params.append(class_update.comment)
            param_count += 1

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append(f"updated_at = NOW()")
        params.extend([class_id, version_info["id"]])

        query = f"""
        UPDATE namespace_classes 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count} AND version_id = ${param_count + 1}
        """

        await db.execute(query, *params)

        # Sync changes to Fuseki
        if class_update.label is not None or class_update.comment is not None:
            # Get namespace path for Fuseki sync
            namespace_info = await db.fetch_one(
                "SELECT path FROM namespace_registry WHERE id = $1", namespace_id
            )

            if namespace_info:
                sync_success = await namespace_sync.update_class_in_fuseki(
                    namespace_info["path"],
                    version,
                    existing["iri"],
                    class_update.label or existing["label"],
                    (
                        class_update.comment
                        if class_update.comment is not None
                        else existing["comment"]
                    ),
                )

                if not sync_success:
                    logger.warning(
                        f"Failed to sync class {existing['local_name']} update to Fuseki"
                    )

        # Fetch and return updated class
        result = await db.fetch_one("SELECT * FROM namespace_classes WHERE id = $1", class_id)

        return ClassResponse(
            id=result["id"],
            version_id=result["version_id"],
            local_name=result["local_name"],
            label=result["label"],
            iri=result["iri"],
            comment=result["comment"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

    except Exception as e:
        logger.error(f"Error updating class: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{namespace_id}/versions/{version}/release")
async def release_version(
    namespace_id: str,
    version: str,
    db: DatabaseService = Depends(get_db),
    admin_user=Depends(get_admin_user),
):
    """Release a version (admin only)"""
    try:
        # Get version info
        version_info = await db.fetch_one(
            "SELECT * FROM namespace_versions WHERE namespace_id = $1 AND version = $2",
            namespace_id,
            version,
        )

        if not version_info:
            raise HTTPException(status_code=404, detail="Version not found")

        if version_info["status"] == "released":
            raise HTTPException(status_code=400, detail="Version is already released")

        # Update version status to released
        await db.execute(
            """
            UPDATE namespace_versions 
            SET status = 'released', released_at = NOW()
            WHERE id = $1
            """,
            version_info["id"],
        )

        return {"message": f"Version {version} released successfully"}

    except Exception as e:
        logger.error(f"Error releasing version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Public endpoints for namespace discovery (no admin required)


@router.get("/public/namespaces", response_model=List[Dict[str, Any]])
async def list_public_namespaces(
    db: DatabaseService = Depends(get_db),
    type_filter: Optional[str] = Query(None, description="Filter by namespace type"),
):
    """List public namespaces for import discovery"""
    try:
        query = """
        SELECT nr.*, nv.version, nv.version_iri, nv.status as version_status
        FROM namespace_registry nr
        LEFT JOIN namespace_versions nv ON nr.id = nv.namespace_id AND nv.status = 'released'
        WHERE nr.status = 'released'
        """
        params = []

        if type_filter:
            query += " AND nr.type = $" + str(len(params) + 1)
            params.append(type_filter)

        query += " ORDER BY nr.created_at DESC"

        results = await db.fetch_all(query, *params)

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "path": row["path"],
                "prefix": row["prefix"],
                "description": row["description"],
                "version": row["version"],
                "version_iri": row["version_iri"],
                "version_status": row["version_status"],
            }
            for row in results
        ]

    except Exception as e:
        logger.error(f"Error listing public namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/public/namespaces/{namespace_id}/versions/{version}/classes",
    response_model=List[ClassResponse],
)
async def list_public_classes(
    namespace_id: str, version: str, db: DatabaseService = Depends(get_db)
):
    """List classes in a public namespace version for imports"""
    try:
        # Get version ID
        version_info = await db.fetch_one(
            """
            SELECT nv.id 
            FROM namespace_versions nv
            JOIN namespace_registry nr ON nv.namespace_id = nr.id
            WHERE nv.namespace_id = $1 AND nv.version = $2 AND nv.status = 'released' AND nr.status = 'released'
            """,
            namespace_id,
            version,
        )

        if not version_info:
            raise HTTPException(status_code=404, detail="Version not found or not released")

        results = await db.fetch_all(
            "SELECT * FROM namespace_classes WHERE version_id = $1 ORDER BY local_name",
            version_info["id"],
        )

        return [
            ClassResponse(
                id=row["id"],
                version_id=row["version_id"],
                local_name=row["local_name"],
                label=row["label"],
                iri=row["iri"],
                comment=row["comment"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in results
        ]

    except Exception as e:
        logger.error(f"Error listing public classes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
