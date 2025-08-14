# ODRAS Feature Implementation: Ontology Editing & File Storage

## Overview

This document describes the implementation of two major features for ODRAS:

1. **JSON-based Ontology Editing** with Fuseki server integration
2. **Persistent File Storage** with multiple backend options (MinIO, PostgreSQL, Local)

## Feature 1: JSON-based Ontology Editing

### Implementation Details

#### Core Components

1. **OntologyManager** (`backend/services/ontology_manager.py`)
   - Handles JSON ↔ RDF conversion
   - Manages Fuseki server synchronization
   - Provides ontology validation
   - Supports CRUD operations on classes and properties

2. **Ontology API** (`backend/api/ontology.py`)
   - RESTful endpoints for ontology management
   - JSON-based request/response formats
   - Input validation using Pydantic models

3. **Web Interface** (`frontend/ontology-editor.html`)
   - Interactive ontology editor
   - Real-time JSON editing
   - Visual ontology browser

#### Key Features

- **JSON-based Editing**: Full ontology can be edited as JSON
- **Fuseki Integration**: Automatic synchronization with Fuseki server
- **Validation**: Schema validation before saving
- **Backup & Restore**: Automatic backups on updates
- **CRUD Operations**: Add/edit/delete classes and properties
- **Export/Import**: Support for multiple RDF formats

#### API Endpoints

```
GET    /api/ontology/                    - Get current ontology
PUT    /api/ontology/                    - Update entire ontology
POST   /api/ontology/classes             - Add new class
POST   /api/ontology/properties          - Add new property
DELETE /api/ontology/classes/{name}      - Delete class
DELETE /api/ontology/properties/{name}   - Delete property
GET    /api/ontology/statistics          - Get ontology statistics
POST   /api/ontology/validate            - Validate ontology JSON
POST   /api/ontology/import              - Import from RDF
GET    /api/ontology/export/{format}     - Export to format
```

#### Base Ontology Structure

The system includes a comprehensive base ontology with:
- **Classes**: Requirement, Constraint, Component, Interface, Function, Process, Condition, Stakeholder, SourceDocument
- **Object Properties**: constrained_by, satisfied_by, has_interface, realizes, triggered_by, originates_from
- **Datatype Properties**: id, text, state, priority, created_at, updated_at

## Feature 2: Persistent File Storage

### Implementation Details

#### Core Components

1. **FileStorageService** (`backend/services/file_storage.py`)
   - Abstraction layer over multiple storage backends
   - File metadata management
   - Hash-based deduplication support

2. **Storage Backends**:
   - **MinIOBackend**: S3-compatible object storage with presigned URLs
   - **PostgreSQLBackend**: Database storage with BLOB support
   - **LocalFilesystemBackend**: Local file storage (development/fallback)

3. **File API** (`backend/api/files.py`)
   - RESTful file management endpoints
   - Upload/download/delete operations
   - Batch upload support

4. **DocumentProcessor** (`backend/services/document_processor.py`)
   - Integrates file storage with existing workflows
   - Handles file processing triggers

#### Storage Features

- **Multiple Backends**: Choose between MinIO, PostgreSQL, or local storage
- **Persistent Storage**: Files are stored permanently, not just in memory
- **Metadata Tracking**: Full file metadata with hash verification
- **Deduplication**: Hash-based duplicate detection
- **Project Association**: Files can be linked to projects
- **Batch Operations**: Support for multiple file uploads
- **Presigned URLs**: Secure direct access for MinIO backend

#### API Endpoints

```
POST   /api/files/upload                 - Upload single file
GET    /api/files/{id}/download          - Download file
GET    /api/files/{id}/url               - Get file access URL
DELETE /api/files/{id}                   - Delete file
GET    /api/files/                       - List files
POST   /api/files/batch/upload           - Batch upload
POST   /api/files/{id}/process           - Trigger processing
GET    /api/files/storage/info           - Storage backend info
```

### Database Schema

Added PostgreSQL tables:
- `file_storage.file_metadata` - File metadata and properties
- `file_storage.file_content` - File content (for PostgreSQL backend)
- `public.projects` - Project management
- `public.extraction_jobs` - Processing job tracking
- `public.requirements` - Extracted requirements
- `public.ontology_changes` - Ontology change audit log

### Docker Services

Enhanced `docker-compose.yml` with:
- **MinIO**: S3-compatible object storage (ports 9000, 9001)
- **PostgreSQL**: Relational database (port 5432)
- Automatic database initialization

## Configuration

### Environment Variables

Added to `backend/services/config.py`:

```python
# File Storage Configuration
storage_backend: str = "local"  # local | minio | postgresql

# MinIO Configuration
minio_endpoint: str = "localhost:9000"
minio_access_key: str = "minioadmin"
minio_secret_key: str = "minioadmin"
minio_bucket_name: str = "odras-files"
minio_secure: bool = False

# PostgreSQL Configuration  
postgres_host: str = "localhost"
postgres_port: int = 5432
postgres_database: str = "odras"
postgres_user: str = "postgres"
postgres_password: str = "password"

# Local Storage Configuration
local_storage_path: str = "./storage/files"
```

### Dependencies

Added to `requirements.txt`:
- `minio>=7.1.0` - MinIO S3-compatible client
- `psycopg2-binary>=2.9.0` - PostgreSQL client

## Usage

### Starting the System

1. **Start Infrastructure**:
   ```bash
   docker compose up -d
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Backend**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

### Accessing Features

1. **Ontology Editor**: http://localhost:8000/ontology-editor
2. **API Documentation**: http://localhost:8000/docs
3. **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
4. **PostgreSQL**: localhost:5432 (postgres/password)

### Example Usage

#### 1. Upload a File with Storage
```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -F "file=@requirements.txt" \
  -F "project_id=test-project"
```

#### 2. Edit Ontology via JSON
```bash
curl -X PUT "http://localhost:8000/api/ontology/" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "Updated Ontology"}, "classes": [...]}'
```

#### 3. Get Ontology Statistics
```bash
curl "http://localhost:8000/api/ontology/statistics"
```

## Integration with Existing System

### File Upload Enhancement

The existing `/api/upload` endpoint now:
1. Stores files persistently using the new storage service
2. Associates files with processing jobs
3. Maintains file references throughout the workflow
4. Supports retry processing of stored files

### Workflow Integration

- Files are stored with metadata before processing begins
- Camunda workflows receive file IDs instead of temporary content
- Processing status is tracked and associated with stored files
- Failed processes can be retried without re-uploading

## Benefits

### Ontology Management
- **User-Friendly**: JSON editing is more accessible than RDF/Turtle
- **Version Control**: Built-in backup and restore capabilities
- **Validation**: Prevents invalid ontology structures
- **Extensible**: Easy to add new classes and properties
- **Synchronized**: Changes are automatically pushed to Fuseki

### File Storage
- **Persistent**: Files survive system restarts and failures
- **Scalable**: Choose appropriate backend for your scale
- **Reliable**: Hash verification and metadata tracking
- **Efficient**: Deduplication and optimized storage
- **Integrated**: Seamless integration with existing workflows

## Security Considerations

- File uploads are validated for type and size
- MinIO supports access control and encryption
- PostgreSQL provides ACID compliance and backup support
- API endpoints include proper error handling
- File access can be restricted by project/user context

## Future Enhancements

- **User Authentication**: Role-based access control
- **File Versioning**: Track file changes over time
- **Advanced Search**: Full-text search across stored files
- **Caching**: Redis caching for frequently accessed files
- **CDN Integration**: CloudFront/CDN support for MinIO
- **Compression**: Automatic file compression for storage efficiency
