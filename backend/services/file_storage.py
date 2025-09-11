"""
File Storage Service for ODRAS
Provides abstraction over different storage backends (MinIO, PostgreSQL, local filesystem).
"""

import hashlib
import json
import logging
import mimetypes
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

# Storage backend imports
try:
    from minio import Minio
    from minio.error import S3Error

    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.pool
    from psycopg2.extras import RealDictCursor

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from .config import Settings

logger = logging.getLogger(__name__)


class FileMetadata:
    """File metadata structure."""

    def __init__(
        self,
        file_id: str,
        filename: str,
        content_type: str,
        size: int,
        hash_md5: str,
        hash_sha256: str,
        storage_path: str,
        created_at: datetime,
        updated_at: datetime,
        project_id: Optional[str] = None,
        tags: Optional[Dict] = None,
        visibility: str = "private",  # "private" or "public"
        created_by: Optional[str] = None,  # User ID of file owner
    ):
        self.file_id = file_id
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.hash_md5 = hash_md5
        self.hash_sha256 = hash_sha256
        self.storage_path = storage_path
        self.created_at = created_at
        self.updated_at = updated_at
        self.project_id = project_id
        self.tags = tags or {}
        self.visibility = visibility
        self.created_by = created_by

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "hash_md5": self.hash_md5,
            "hash_sha256": self.hash_sha256,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "project_id": self.project_id,
            "tags": self.tags,
            "visibility": self.visibility,
            "created_by": self.created_by,
        }


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def store_file(self, file_id: str, content: bytes, metadata: FileMetadata) -> bool:
        """Store file content with metadata."""
        pass

    @abstractmethod
    async def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve file content by ID."""
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by ID."""
        pass

    @abstractmethod
    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Get a presigned URL for file access."""
        pass

    @abstractmethod
    async def list_files(
        self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files metadata if supported by backend."""
        pass

    @abstractmethod
    async def update_file_visibility(self, file_id: str, visibility: str) -> bool:
        """Update file visibility. Returns True if successful."""
        pass

    @abstractmethod
    async def list_files_with_visibility(
        self,
        project_id: Optional[str] = None,
        include_public: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List files with visibility support. If include_public=True, includes public files from other projects."""
        pass


class MinIOBackend(StorageBackend):
    """MinIO/S3-compatible storage backend."""

    def __init__(self, settings: Settings):
        if not MINIO_AVAILABLE:
            raise ImportError("MinIO client not available. Install with: pip install minio")

        self.settings = settings
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create/check MinIO bucket: {e}")

    async def store_file(self, file_id: str, content: bytes, metadata: FileMetadata) -> bool:
        """Store file in MinIO."""
        try:
            import json
            from io import BytesIO

            # Store file content
            content_stream = BytesIO(content)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=f"files/{file_id}",
                data=content_stream,
                length=len(content),
                content_type=metadata.content_type,
                metadata={
                    "filename": metadata.filename,
                    "project_id": metadata.project_id or "",
                    "created_at": metadata.created_at.isoformat(),
                    "hash_md5": metadata.hash_md5,
                    "hash_sha256": metadata.hash_sha256,
                },
            )

            # Store metadata as separate JSON object
            metadata_stream = BytesIO(json.dumps(metadata.to_dict()).encode("utf-8"))
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=f"metadata/{file_id}.json",
                data=metadata_stream,
                length=len(json.dumps(metadata.to_dict()).encode("utf-8")),
                content_type="application/json",
            )

            return True

        except S3Error as e:
            logger.error(f"Failed to store file in MinIO: {e}")
            return False

    async def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve file from MinIO."""
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=f"files/{file_id}"
            )
            try:
                data = response.read()
                return data
            finally:
                response.close()
                response.release_conn()

        except S3Error as e:
            logger.error(f"Failed to retrieve file from MinIO: {e}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from MinIO."""
        try:
            # Delete file content
            self.client.remove_object(bucket_name=self.bucket_name, object_name=f"files/{file_id}")

            # Delete metadata
            self.client.remove_object(
                bucket_name=self.bucket_name, object_name=f"metadata/{file_id}.json"
            )

            return True

        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO: {e}")
            return False

    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.client.stat_object(bucket_name=self.bucket_name, object_name=f"files/{file_id}")
            return True

        except S3Error:
            return False

    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Get presigned URL for file access."""
        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=f"files/{file_id}",
                expires=timedelta(seconds=expires_in),
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    async def list_files(
        self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files by scanning metadata objects in MinIO."""
        results: List[Dict[str, Any]] = []
        try:
            import json

            prefix = "metadata/"
            # MinIO list_objects is iterator
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            for obj in objects:
                if not obj.object_name or not obj.object_name.endswith(".json"):
                    continue
                resp = self.client.get_object(self.bucket_name, obj.object_name)
                try:
                    meta_json = resp.read().decode("utf-8")
                    meta = json.loads(meta_json)
                    if project_id and meta.get("project_id") != project_id:
                        continue
                    results.append(meta)
                    if len(results) >= limit:
                        break
                finally:
                    resp.close()
                    resp.release_conn()
            return results[offset : offset + limit]
        except Exception as e:
            logger.error(f"Failed to list files from MinIO: {e}")
            return []

    # Helpers to read/write metadata JSON (MVP convenience)
    def read_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        try:
            import json

            resp = self.client.get_object(self.bucket_name, f"metadata/{file_id}.json")
            try:
                meta_json = resp.read().decode("utf-8")
                return json.loads(meta_json)
            finally:
                resp.close()
                resp.release_conn()
        except Exception:
            return None

    def write_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        try:
            import json
            from io import BytesIO

            data = json.dumps(metadata).encode("utf-8")
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=f"metadata/{file_id}.json",
                data=BytesIO(data),
                length=len(data),
                content_type="application/json",
            )
            return True
        except Exception:
            return False

    async def update_file_visibility(self, file_id: str, visibility: str) -> bool:
        """Update file visibility in MinIO backend."""
        try:
            # Read existing metadata
            metadata = self.read_metadata(file_id)
            if not metadata:
                logger.error(f"File metadata not found: {file_id}")
                return False

            # Update visibility
            metadata["visibility"] = visibility
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Write back to MinIO
            return self.write_metadata(file_id, metadata)
        except Exception as e:
            logger.error(f"Failed to update file visibility: {e}")
            return False

    async def list_files_with_visibility(
        self,
        project_id: Optional[str] = None,
        include_public: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List files with visibility filtering."""
        logger.info(
            f"Filtering files for project_id: {project_id}, include_public: {include_public}"
        )
        try:
            # Get all metadata objects
            objects = self.client.list_objects(
                self.bucket_name, prefix="metadata/", recursive=False
            )
            results = []

            for obj in objects:
                if not obj.object_name or not obj.object_name.endswith(".json"):
                    continue

                file_id = obj.object_name.replace("metadata/", "").replace(".json", "")
                metadata = self.read_metadata(file_id)

                if metadata:
                    file_visibility = metadata.get("visibility", "private")
                    file_project_id = metadata.get("project_id")
                    logger.info(
                        f"Processing file {file_id}: project_id={file_project_id}, visibility={file_visibility}, filename={metadata.get('filename', 'unknown')}"
                    )

                    # Apply filtering logic
                    should_include = False

                    if project_id is None:
                        # No project filter - include all
                        should_include = True
                    elif file_project_id == project_id:
                        # Same project - always include
                        should_include = True
                    elif include_public and file_visibility == "public":
                        # Different project but file is public and we want public files
                        should_include = True

                    if should_include:
                        results.append(metadata)

            # Sort by created_at desc and apply pagination
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results[offset : offset + limit]

        except Exception as e:
            logger.error(f"Failed to list files with visibility from MinIO: {e}")
            return []


class PostgreSQLBackend(StorageBackend):
    """PostgreSQL storage backend (stores files as BLOBs)."""

    def __init__(self, settings: Settings, metadata_only: bool = False):
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL client not available. Install with: pip install psycopg2-binary"
            )

        self.settings = settings
        self.metadata_only = metadata_only  # When True, only store metadata in files table
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        self._create_tables()

    def _create_tables(self):
        """Create file storage tables if they don't exist."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                # Files table for metadata
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_storage (
                        file_id VARCHAR(255) PRIMARY KEY,
                        filename VARCHAR(500) NOT NULL,
                        content_type VARCHAR(200),
                        size BIGINT NOT NULL,
                        hash_md5 VARCHAR(32),
                        hash_sha256 VARCHAR(64),
                        storage_path VARCHAR(500),
                        project_id VARCHAR(255),
                        tags JSONB DEFAULT '{}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """
                )

                # File content table (using OID for large objects)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_content (
                        file_id VARCHAR(255) PRIMARY KEY REFERENCES file_storage(file_id) ON DELETE CASCADE,
                        content BYTEA NOT NULL
                    )
                """
                )

                # Indexes for better performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_file_storage_project_id ON file_storage(project_id);
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_file_storage_created_at ON file_storage(created_at);
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_file_storage_hash_md5 ON file_storage(hash_md5);
                """
                )

                conn.commit()

            self.connection_pool.putconn(conn)
            logger.info("PostgreSQL file storage tables created/verified")

        except psycopg2.Error as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")

    async def store_file(self, file_id: str, content: bytes, metadata: FileMetadata) -> bool:
        """Store file in PostgreSQL."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                # Insert metadata
                cursor.execute(
                    """
                    INSERT INTO files 
                    (id, filename, content_type, file_size, hash_md5, hash_sha256, 
                     storage_path, project_id, tags, created_at, updated_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        content_type = EXCLUDED.content_type,
                        file_size = EXCLUDED.file_size,
                        hash_md5 = EXCLUDED.hash_md5,
                        hash_sha256 = EXCLUDED.hash_sha256,
                        updated_at = EXCLUDED.updated_at
                """,
                    (
                        file_id,
                        metadata.filename,
                        metadata.content_type,
                        metadata.size,
                        metadata.hash_md5,
                        metadata.hash_sha256,
                        metadata.storage_path,
                        metadata.project_id,
                        json.dumps(metadata.tags or {}),  # Proper JSON serialization
                        metadata.created_at,
                        metadata.updated_at,
                        metadata.created_by,
                    ),
                )

                # Only insert content if not in metadata-only mode
                if not self.metadata_only:
                    cursor.execute(
                        """
                        INSERT INTO file_content (file_id, content)
                        VALUES (%s, %s)
                        ON CONFLICT (file_id) DO UPDATE SET
                            content = EXCLUDED.content
                    """,
                        (file_id, content),
                    )

                conn.commit()

            self.connection_pool.putconn(conn)
            return True

        except psycopg2.Error as e:
            logger.error(f"Failed to store file in PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return False

    async def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve file from PostgreSQL."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT content FROM file_content WHERE file_id = %s
                """,
                    (file_id,),
                )

                result = cursor.fetchone()
                if result:
                    return bytes(result[0])

            self.connection_pool.putconn(conn)
            return None

        except psycopg2.Error as e:
            logger.error(f"Failed to retrieve file from PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from PostgreSQL."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM files WHERE id = %s
                """,
                    (file_id,),
                )

                conn.commit()

            self.connection_pool.putconn(conn)
            return True

        except psycopg2.Error as e:
            logger.error(f"Failed to delete file from PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return False

    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists in PostgreSQL."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1 FROM files WHERE id = %s
                """,
                    (file_id,),
                )

                result = cursor.fetchone()

            self.connection_pool.putconn(conn)
            return result is not None

        except psycopg2.Error as e:
            logger.error(f"Failed to check file existence in PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return False

    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """PostgreSQL doesn't support presigned URLs, return API endpoint."""
        # Return the API endpoint for file access
        return f"/api/files/{file_id}/download"

    async def list_files(
        self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        # Not implemented: would query metadata table
        return []

    async def update_file_visibility(self, file_id: str, visibility: str) -> bool:
        """Update file visibility in PostgreSQL backend."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                import json

                cursor.execute(
                    """
                    UPDATE files 
                    SET metadata = metadata || %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (json.dumps({"visibility": visibility}), file_id),
                )

                affected_rows = cursor.rowcount
                conn.commit()

            self.connection_pool.putconn(conn)
            return affected_rows > 0

        except psycopg2.Error as e:
            logger.error(f"Failed to update file visibility in PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return False

    async def list_files_with_visibility(
        self,
        project_id: Optional[str] = None,
        include_public: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List files with visibility filtering for PostgreSQL backend."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query with visibility filtering
                where_conditions = []
                params = []

                if project_id is not None:
                    if include_public:
                        # Same project OR public files
                        where_conditions.append(
                            "((metadata->>'project_id' = %s) OR (metadata->>'visibility' = 'public'))"
                        )
                        params.append(project_id)
                    else:
                        # Same project only
                        where_conditions.append("metadata->>'project_id' = %s")
                        params.append(project_id)

                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)

                query = (
                    """
                    SELECT id as file_id, filename, content_type, file_size as size, hash_md5, hash_sha256,
                           storage_path, created_at, updated_at, metadata
                    FROM files 
                    """
                    + where_clause  # nosec B608
                    + """
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """
                )

                cursor.execute(query, params + [limit, offset])

                results = []
                for row in cursor.fetchall():
                    metadata = row.get("metadata") or {}
                    result = {
                        "file_id": row["file_id"],
                        "filename": row["filename"],
                        "content_type": row["content_type"],
                        "size": row["size"],
                        "hash_md5": row["hash_md5"],
                        "hash_sha256": row["hash_sha256"],
                        "storage_path": row["storage_path"],
                        "created_at": (
                            row["created_at"].isoformat() if row["created_at"] else None
                        ),
                        "updated_at": (
                            row["updated_at"].isoformat() if row["updated_at"] else None
                        ),
                        "project_id": metadata.get("project_id"),
                        "tags": metadata.get("tags", {}),
                        "visibility": metadata.get("visibility", "private"),
                    }
                    results.append(result)

            self.connection_pool.putconn(conn)
            return results

        except psycopg2.Error as e:
            logger.error(f"Failed to list files with visibility from PostgreSQL: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return []


class LocalFilesystemBackend(StorageBackend):
    """Local filesystem storage backend (for development/fallback)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage_path = Path(settings.local_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.storage_path / "files").mkdir(exist_ok=True)
        (self.storage_path / "metadata").mkdir(exist_ok=True)

    async def store_file(self, file_id: str, content: bytes, metadata: FileMetadata) -> bool:
        """Store file on local filesystem."""
        try:
            # Store file content
            file_path = self.storage_path / "files" / file_id
            file_path.write_bytes(content)

            # Store metadata
            metadata_path = self.storage_path / "metadata" / f"{file_id}.json"
            import json

            metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2))

            return True

        except Exception as e:
            logger.error(f"Failed to store file locally: {e}")
            return False

    async def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve file from local filesystem."""
        try:
            file_path = self.storage_path / "files" / file_id
            if file_path.exists():
                return file_path.read_bytes()
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve file locally: {e}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from local filesystem."""
        try:
            file_path = self.storage_path / "files" / file_id
            metadata_path = self.storage_path / "metadata" / f"{file_id}.json"

            if file_path.exists():
                file_path.unlink()

            if metadata_path.exists():
                metadata_path.unlink()

            return True

        except Exception as e:
            logger.error(f"Failed to delete file locally: {e}")
            return False

    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists on local filesystem."""
        file_path = self.storage_path / "files" / file_id
        return file_path.exists()

    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Return API endpoint for local file access."""
        return f"/api/files/{file_id}/download"

    async def list_files(
        self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        try:
            import json

            results: List[Dict[str, Any]] = []
            meta_dir = self.storage_path / "metadata"
            for p in sorted(meta_dir.glob("*.json")):
                meta = json.loads(p.read_text())
                if project_id and meta.get("project_id") != project_id:
                    continue
                results.append(meta)
                if len(results) >= limit:
                    break
            return results[offset : offset + limit]
        except Exception as e:
            logger.error(f"Failed to list local files: {e}")
            return []

    # Helpers to read/write metadata JSON (MVP convenience)
    def read_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        try:
            import json

            metadata_path = self.storage_path / "metadata" / f"{file_id}.json"
            if not metadata_path.exists():
                return None
            return json.loads(metadata_path.read_text())
        except Exception:
            return None

    def write_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        try:
            import json

            metadata_path = self.storage_path / "metadata" / f"{file_id}.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            return True
        except Exception:
            return False

    async def update_file_visibility(self, file_id: str, visibility: str) -> bool:
        """Update file visibility in local filesystem backend."""
        try:
            # Read existing metadata
            metadata = self.read_metadata(file_id)
            if not metadata:
                logger.error(f"File metadata not found: {file_id}")
                return False

            # Update visibility
            metadata["visibility"] = visibility
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Write back to filesystem
            return self.write_metadata(file_id, metadata)
        except Exception as e:
            logger.error(f"Failed to update file visibility: {e}")
            return False

    async def list_files_with_visibility(
        self,
        project_id: Optional[str] = None,
        include_public: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List files with visibility filtering for local filesystem backend."""
        try:
            metadata_dir = self.storage_path / "metadata"
            if not metadata_dir.exists():
                return []

            results = []
            for metadata_file in metadata_dir.glob("*.json"):
                file_id = metadata_file.stem
                metadata = self.read_metadata(file_id)

                if metadata:
                    file_visibility = metadata.get("visibility", "private")
                    file_project_id = metadata.get("project_id")

                    # Apply filtering logic
                    should_include = False

                    if project_id is None:
                        # No project filter - include all
                        should_include = True
                    elif file_project_id == project_id:
                        # Same project - always include
                        should_include = True
                    elif include_public and file_visibility == "public":
                        # Different project but file is public and we want public files
                        should_include = True

                    if should_include:
                        results.append(metadata)

            # Sort by created_at desc and apply pagination
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results[offset : offset + limit]

        except Exception as e:
            logger.error(f"Failed to list files with visibility from local filesystem: {e}")
            return []


class FileStorageService:
    """Main file storage service that manages different backends."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = self._initialize_backend()

        # Initialize metadata store (always use PostgreSQL if available, else local)
        if POSTGRES_AVAILABLE and settings.storage_backend != "local":
            # Use metadata-only mode when PostgreSQL is not the primary storage backend
            metadata_only = settings.storage_backend != "postgresql"
            self.metadata_backend = PostgreSQLBackend(settings, metadata_only=metadata_only)
        else:
            self.metadata_backend = None

    def _initialize_backend(self) -> StorageBackend:
        """Initialize the appropriate storage backend."""
        backend_type = self.settings.storage_backend.lower()

        if backend_type == "minio":
            if not MINIO_AVAILABLE:
                raise RuntimeError(
                    "MinIO backend requested but 'minio' client is not installed. Install with: pip install minio"
                )
            try:
                return MinIOBackend(self.settings)
            except Exception as e:
                # Do not silently fall back; make the error explicit
                raise RuntimeError(f"Failed to initialize MinIO backend: {e}")
        elif backend_type == "postgresql":
            if not POSTGRES_AVAILABLE:
                raise RuntimeError(
                    "PostgreSQL backend requested but client is not installed. Install with: pip install psycopg2-binary"
                )
            try:
                return PostgreSQLBackend(self.settings)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize PostgreSQL backend: {e}")
        elif backend_type == "local":
            return LocalFilesystemBackend(self.settings)
        else:
            # Unknown backend => explicit error
            raise RuntimeError(
                f"Unknown storage backend '{backend_type}'. Use one of: local|minio|postgresql"
            )

    def _calculate_hashes(self, content: bytes) -> tuple[str, str]:
        """Calculate MD5 and SHA256 hashes for content."""
        md5_hash = hashlib.md5(content, usedforsecurity=False).hexdigest()
        sha256_hash = hashlib.sha256(content).hexdigest()
        return md5_hash, sha256_hash

    async def store_file(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[Dict] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store a file and return metadata.

        Args:
            content: File content as bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            project_id: Associated project ID
            tags: Additional metadata tags
            created_by: User ID of file owner

        Returns:
            Dict containing file metadata and storage result
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())

            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or "application/octet-stream"

            # Calculate file hashes
            md5_hash, sha256_hash = self._calculate_hashes(content)

            # Create metadata
            now = datetime.now(timezone.utc)
            metadata = FileMetadata(
                file_id=file_id,
                filename=filename,
                content_type=content_type,
                size=len(content),
                hash_md5=md5_hash,
                hash_sha256=sha256_hash,
                storage_path=f"{self.settings.storage_backend}/{file_id}",
                created_at=now,
                updated_at=now,
                project_id=project_id,
                tags=tags or {},
                visibility="private",  # All files are private by default
                created_by=created_by,
            )

            # Store file using backend
            success = await self.backend.store_file(file_id, content, metadata)

            if success:
                # If using MinIO (or other non-PostgreSQL backends), also store metadata in PostgreSQL
                if self.metadata_backend and self.settings.storage_backend != "postgresql":
                    try:
                        metadata_success = await self.metadata_backend.store_file(
                            file_id, content, metadata
                        )
                        if not metadata_success:
                            logger.warning(
                                f"Failed to store metadata in PostgreSQL for file {file_id}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error storing metadata in PostgreSQL for file {file_id}: {e}"
                        )

                return {
                    "success": True,
                    "file_id": file_id,
                    "metadata": metadata.to_dict(),
                    "message": "File stored successfully",
                }
            else:
                return {"success": False, "error": "Failed to store file in backend"}

        except Exception as e:
            logger.error(f"Failed to store file: {e}")
            return {"success": False, "error": f"Storage failed: {str(e)}"}

    async def retrieve_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file by ID.

        Args:
            file_id: Unique file identifier

        Returns:
            Dict containing file content and metadata, or None if not found
        """
        try:
            # Check if file exists
            if not await self.backend.file_exists(file_id):
                return None

            # Retrieve content
            content = await self.backend.retrieve_file(file_id)
            if content is None:
                return None

            # Get metadata (if using separate metadata backend)
            # For now, we'll reconstruct basic metadata
            return {"file_id": file_id, "content": content, "size": len(content)}

        except Exception as e:
            logger.error(f"Failed to retrieve file {file_id}: {e}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file by ID.

        Args:
            file_id: Unique file identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.backend.delete_file(file_id)

        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL for file access.

        Args:
            file_id: Unique file identifier
            expires_in: URL expiration time in seconds

        Returns:
            URL string or None if not available
        """
        try:
            return await self.backend.get_file_url(file_id, expires_in)

        except Exception as e:
            logger.error(f"Failed to get file URL for {file_id}: {e}")
            return None

    async def list_files(
        self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files via backend (MinIO/local supported)."""
        return await self.backend.list_files(project_id, limit, offset)

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the current storage configuration."""
        return {
            "backend_type": self.settings.storage_backend,
            "backend_available": True,
            "features": {
                "presigned_urls": self.settings.storage_backend == "minio",
                "metadata_storage": POSTGRES_AVAILABLE
                or self.settings.storage_backend == "postgresql",
                "deduplication": True,  # Based on hash comparison
            },
        }

    # Helpers for metadata patching (MVP for local/minio)
    def _read_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        backend = self.backend
        try:
            if isinstance(backend, LocalFilesystemBackend):
                return backend.read_metadata(file_id)
            if isinstance(backend, MinIOBackend):
                return backend.read_metadata(file_id)
        except Exception:
            return None
        return None

    def _write_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        backend = self.backend
        try:
            if isinstance(backend, LocalFilesystemBackend):
                return backend.write_metadata(file_id, metadata)
            if isinstance(backend, MinIOBackend):
                return backend.write_metadata(file_id, metadata)
        except Exception:
            return False
        return False

    async def update_file_tags(self, file_id: str, new_tags: Dict[str, Any]) -> bool:
        import copy
        from datetime import datetime, timezone

        meta = self._read_metadata(file_id)
        if not meta:
            return False
        merged = copy.deepcopy(meta)
        tags = dict(merged.get("tags") or {})
        tags.update(new_tags or {})
        merged["tags"] = tags
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self._write_metadata(file_id, merged)

    async def update_file_visibility(self, file_id: str, visibility: str) -> bool:
        """
        Update file visibility.

        Args:
            file_id: Unique file identifier
            visibility: "private" or "public"

        Returns:
            True if successful, False otherwise
        """
        if visibility not in ["private", "public"]:
            logger.error(f"Invalid visibility value: {visibility}")
            return False

        try:
            return await self.backend.update_file_visibility(file_id, visibility)
        except Exception as e:
            logger.error(f"Failed to update file visibility: {e}")
            return False

    async def list_files_with_visibility(
        self,
        project_id: Optional[str] = None,
        include_public: bool = False,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        is_admin: bool = False,
        db=None,
    ) -> List[Dict[str, Any]]:
        """
        List files with visibility support and user-based filtering.

        Args:
            project_id: Filter by project ID (optional)
            include_public: Include public files from other projects
            limit: Maximum number of results
            offset: Result offset for pagination
            user_id: Current user ID for permission checking
            is_admin: Whether the user is an admin
            db: Database service for project membership checking

        Returns:
            List of file metadata dictionaries filtered by user permissions
        """
        try:
            # Get all files first
            all_files = await self.backend.list_files_with_visibility(
                project_id, include_public, limit * 2, 0
            )

            # Apply user-based filtering with ownership checks
            filtered_files = []
            for file_data in all_files:
                file_project_id = file_data.get("project_id")
                file_visibility = file_data.get("visibility", "private")
                file_created_by = file_data.get("created_by")

                should_include = False

                if is_admin:
                    # Admins can see all files
                    should_include = True
                elif file_created_by == user_id:
                    # Users can always see their own files
                    should_include = True
                elif file_visibility == "public":
                    # Public files are visible to project members or globally
                    if project_id is not None:
                        if file_project_id == project_id:
                            # Public file in requested project - include it
                            should_include = True
                        elif include_public:
                            # Include public files from other projects if requested
                            should_include = True
                    elif file_project_id and db and user_id:
                        # Check if user is member of file's project for public files
                        try:
                            is_member = db.is_user_member(
                                project_id=file_project_id, user_id=user_id
                            )
                            if is_member:
                                should_include = True
                        except Exception as e:
                            logger.warning(
                                f"Failed to check project membership for user {user_id}, project {file_project_id}: {e}"
                            )
                # Note: Private files are only visible to their owner (checked above) or admins

                if should_include:
                    filtered_files.append(file_data)
                    if len(filtered_files) >= limit:
                        break

            # Apply pagination to filtered results
            return filtered_files[offset : offset + limit]

        except Exception as e:
            logger.error(f"Failed to list files with visibility and user filtering: {e}")
            return []

    async def get_file_content(self, file_id: str) -> Optional[bytes]:
        """
        Get file content by file ID.

        Args:
            file_id: Unique file identifier

        Returns:
            File content as bytes or None if not found
        """
        try:
            file_data = await self.retrieve_file(file_id)
            if file_data and "content" in file_data:
                return file_data["content"]
            return None
        except Exception as e:
            logger.error(f"Failed to get file content for {file_id}: {e}")
            return None

    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata by file ID.

        Args:
            file_id: Unique file identifier

        Returns:
            File metadata dict or None if not found
        """
        try:
            # Always try to get metadata from PostgreSQL database first
            # This works for all backends since metadata is always stored in PostgreSQL
            metadata = await self._get_metadata_from_db(file_id)
            if metadata:
                return metadata

            # Fallback: For other backends, use retrieve_file and extract basic metadata
            file_data = await self.retrieve_file(file_id)
            if file_data:
                return {
                    "file_id": file_data.get("file_id"),
                    "filename": "unknown",  # Need to get from backend-specific metadata
                    "content_type": "application/octet-stream",
                    "size": file_data.get("size", 0),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get file metadata for {file_id}: {e}")
            return None

    async def _get_metadata_from_db(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata from PostgreSQL database."""
        try:
            # Create a direct PostgreSQL connection for metadata
            # Metadata is always stored in PostgreSQL regardless of storage backend
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                database=self.settings.postgres_database,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
            )
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, content_type, file_size, hash_md5, hash_sha256,
                           storage_path, project_id, tags, created_at, updated_at, metadata, created_by
                    FROM files 
                    WHERE id = %s
                    """,
                    (file_id,),
                )

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get metadata from database for {file_id}: {e}")
            return None
        finally:
            try:
                conn.close()
            except:
                pass


# Global service instance
_file_storage_service = None


def get_file_storage_service() -> FileStorageService:
    """Get the global file storage service instance."""
    global _file_storage_service
    if _file_storage_service is None:
        settings = Settings()
        _file_storage_service = FileStorageService(settings)
    return _file_storage_service
