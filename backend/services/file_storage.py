"""
File Storage Service for ODRAS
Provides abstraction over different storage backends (MinIO, PostgreSQL, local filesystem).
"""

import hashlib
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
    async def list_files(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List files metadata if supported by backend."""
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
            response = self.client.get_object(bucket_name=self.bucket_name, object_name=f"files/{file_id}")
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
            self.client.remove_object(bucket_name=self.bucket_name, object_name=f"metadata/{file_id}.json")

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
                bucket_name=self.bucket_name, object_name=f"files/{file_id}", expires=timedelta(seconds=expires_in)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    async def list_files(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List files by scanning metadata objects in MinIO."""
        results: List[Dict[str, Any]] = []
        try:
            import json

            prefix = "metadata/"
            # MinIO list_objects is iterator
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            for obj in objects:
                if not obj.object_name.endswith(".json"):
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


class PostgreSQLBackend(StorageBackend):
    """PostgreSQL storage backend (stores files as BLOBs)."""

    def __init__(self, settings: Settings):
        if not POSTGRES_AVAILABLE:
            raise ImportError("PostgreSQL client not available. Install with: pip install psycopg2-binary")

        self.settings = settings
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
                    INSERT INTO file_storage 
                    (file_id, filename, content_type, size, hash_md5, hash_sha256, 
                     storage_path, project_id, tags, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        content_type = EXCLUDED.content_type,
                        size = EXCLUDED.size,
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
                        str(metadata.tags),
                        metadata.created_at,
                        metadata.updated_at,
                    ),
                )

                # Insert content
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
                    DELETE FROM file_storage WHERE file_id = %s
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
                    SELECT 1 FROM file_storage WHERE file_id = %s
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

    async def list_files(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        # Not implemented: would query metadata table
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

    async def list_files(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
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


class FileStorageService:
    """Main file storage service that manages different backends."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = self._initialize_backend()

        # Initialize metadata store (always use PostgreSQL if available, else local)
        if POSTGRES_AVAILABLE and settings.storage_backend != "local":
            self.metadata_backend = PostgreSQLBackend(settings)
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
            raise RuntimeError(f"Unknown storage backend '{backend_type}'. Use one of: local|minio|postgresql")

    def _calculate_hashes(self, content: bytes) -> tuple[str, str]:
        """Calculate MD5 and SHA256 hashes for content."""
        md5_hash = hashlib.md5(content).hexdigest()
        sha256_hash = hashlib.sha256(content).hexdigest()
        return md5_hash, sha256_hash

    async def store_file(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Store a file and return metadata.

        Args:
            content: File content as bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            project_id: Associated project ID
            tags: Additional metadata tags

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
            )

            # Store file using backend
            success = await self.backend.store_file(file_id, content, metadata)

            if success:
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

    async def list_files(self, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List files via backend (MinIO/local supported)."""
        return await self.backend.list_files(project_id, limit, offset)

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the current storage configuration."""
        return {
            "backend_type": self.settings.storage_backend,
            "backend_available": True,
            "features": {
                "presigned_urls": self.settings.storage_backend == "minio",
                "metadata_storage": POSTGRES_AVAILABLE or self.settings.storage_backend == "postgresql",
                "deduplication": True,  # Based on hash comparison
            },
        }
