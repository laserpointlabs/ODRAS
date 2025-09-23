# ODRAS Feature Implementation: Ontology Editing & File Storage<br>
<br>
## Overview<br>
<br>
This document describes the implementation of two major features for ODRAS:<br>
<br>
1. **JSON-based Ontology Editing** with Fuseki server integration<br>
2. **Persistent File Storage** with multiple backend options (MinIO, PostgreSQL, Local)<br>
<br>
## Feature 1: JSON-based Ontology Editing<br>
<br>
### Implementation Details<br>
<br>
#### Core Components<br>
<br>
1. **OntologyManager** (`backend/services/ontology_manager.py`)<br>
   - Handles JSON ↔ RDF conversion<br>
   - Manages Fuseki server synchronization<br>
   - Provides ontology validation<br>
   - Supports CRUD operations on classes and properties<br>
<br>
2. **Ontology API** (`backend/api/ontology.py`)<br>
   - RESTful endpoints for ontology management<br>
   - JSON-based request/response formats<br>
   - Input validation using Pydantic models<br>
<br>
3. **Web Interface** (`frontend/ontology-editor.html`)<br>
   - Interactive ontology editor<br>
   - Real-time JSON editing<br>
   - Visual ontology browser<br>
<br>
#### Key Features<br>
<br>
- **JSON-based Editing**: Full ontology can be edited as JSON<br>
- **Fuseki Integration**: Automatic synchronization with Fuseki server<br>
- **Validation**: Schema validation before saving<br>
- **Backup & Restore**: Automatic backups on updates<br>
- **CRUD Operations**: Add/edit/delete classes and properties<br>
- **Export/Import**: Support for multiple RDF formats<br>
<br>
#### API Endpoints<br>
<br>
```<br>
GET    /api/ontology/                    - Get current ontology<br>
PUT    /api/ontology/                    - Update entire ontology<br>
POST   /api/ontology/classes             - Add new class<br>
POST   /api/ontology/properties          - Add new property<br>
DELETE /api/ontology/classes/{name}      - Delete class<br>
DELETE /api/ontology/properties/{name}   - Delete property<br>
GET    /api/ontology/statistics          - Get ontology statistics<br>
POST   /api/ontology/validate            - Validate ontology JSON<br>
POST   /api/ontology/import              - Import from RDF<br>
GET    /api/ontology/export/{format}     - Export to format<br>
```<br>
<br>
#### Base Ontology Structure<br>
<br>
The system includes a comprehensive base ontology with:<br>
- **Classes**: Requirement, Constraint, Component, Interface, Function, Process, Condition, Stakeholder, SourceDocument<br>
- **Object Properties**: constrained_by, satisfied_by, has_interface, realizes, triggered_by, originates_from<br>
- **Datatype Properties**: id, text, state, priority, created_at, updated_at<br>
<br>
## Feature 2: Persistent File Storage<br>
<br>
### Implementation Details<br>
<br>
#### Core Components<br>
<br>
1. **FileStorageService** (`backend/services/file_storage.py`)<br>
   - Abstraction layer over multiple storage backends<br>
   - File metadata management<br>
   - Hash-based deduplication support<br>
<br>
2. **Storage Backends**:<br>
   - **MinIOBackend**: S3-compatible object storage with presigned URLs<br>
   - **PostgreSQLBackend**: Database storage with BLOB support<br>
   - **LocalFilesystemBackend**: Local file storage (development/fallback)<br>
<br>
3. **File API** (`backend/api/files.py`)<br>
   - RESTful file management endpoints<br>
   - Upload/download/delete operations<br>
   - Batch upload support<br>
<br>
4. **DocumentProcessor** (`backend/services/document_processor.py`)<br>
   - Integrates file storage with existing workflows<br>
   - Handles file processing triggers<br>
<br>
#### Storage Features<br>
<br>
- **Multiple Backends**: Choose between MinIO, PostgreSQL, or local storage<br>
- **Persistent Storage**: Files are stored permanently, not just in memory<br>
- **Metadata Tracking**: Full file metadata with hash verification<br>
- **Deduplication**: Hash-based duplicate detection<br>
- **Project Association**: Files can be linked to projects<br>
- **Batch Operations**: Support for multiple file uploads<br>
- **Presigned URLs**: Secure direct access for MinIO backend<br>
<br>
#### API Endpoints<br>
<br>
```<br>
POST   /api/files/upload                 - Upload single file<br>
GET    /api/files/{id}/download          - Download file<br>
GET    /api/files/{id}/url               - Get file access URL<br>
DELETE /api/files/{id}                   - Delete file<br>
GET    /api/files/                       - List files<br>
POST   /api/files/batch/upload           - Batch upload<br>
POST   /api/files/{id}/process           - Trigger processing<br>
GET    /api/files/storage/info           - Storage backend info<br>
```<br>
<br>
### Database Schema<br>
<br>
Added PostgreSQL tables:<br>
- `file_storage.file_metadata` - File metadata and properties<br>
- `file_storage.file_content` - File content (for PostgreSQL backend)<br>
- `public.projects` - Project management<br>
- `public.extraction_jobs` - Processing job tracking<br>
- `public.requirements` - Extracted requirements<br>
- `public.ontology_changes` - Ontology change audit log<br>
<br>
### Docker Services<br>
<br>
Enhanced `docker-compose.yml` with:<br>
- **MinIO**: S3-compatible object storage (ports 9000, 9001)<br>
- **PostgreSQL**: Relational database (port 5432)<br>
- Automatic database initialization<br>
<br>
## Configuration<br>
<br>
### Environment Variables<br>
<br>
Added to `backend/services/config.py`:<br>
<br>
```python<br>
# File Storage Configuration<br>
storage_backend: str = "local"  # local | minio | postgresql<br>
<br>
# MinIO Configuration<br>
minio_endpoint: str = "localhost:9000"<br>
minio_access_key: str = "minioadmin"<br>
minio_secret_key: str = "minioadmin"<br>
minio_bucket_name: str = "odras-files"<br>
minio_secure: bool = False<br>
<br>
# PostgreSQL Configuration<br>
postgres_host: str = "localhost"<br>
postgres_port: int = 5432<br>
postgres_database: str = "odras"<br>
postgres_user: str = "postgres"<br>
postgres_password: str = "password"<br>
<br>
# Local Storage Configuration<br>
local_storage_path: str = "./storage/files"<br>
```<br>
<br>
### Dependencies<br>
<br>
Added to `requirements.txt`:<br>
- `minio>=7.1.0` - MinIO S3-compatible client<br>
- `psycopg2-binary>=2.9.0` - PostgreSQL client<br>
<br>
## Usage<br>
<br>
### Starting the System<br>
<br>
1. **Start Infrastructure**:<br>
   ```bash<br>
   docker compose up -d<br>
   ```<br>
<br>
2. **Install Dependencies**:<br>
   ```bash<br>
   pip install -r requirements.txt<br>
   ```<br>
<br>
3. **Start Backend**:<br>
   ```bash<br>
   uvicorn backend.main:app --reload --port 8000<br>
   ```<br>
<br>
### Accessing Features<br>
<br>
1. **Ontology Editor**: http://localhost:8000/ontology-editor<br>
2. **API Documentation**: http://localhost:8000/docs<br>
3. **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)<br>
4. **PostgreSQL**: localhost:5432 (postgres/password)<br>
<br>
### Example Usage<br>
<br>
#### 1. Upload a File with Storage<br>
```bash<br>
curl -X POST "http://localhost:8000/api/files/upload" \<br>
  -F "file=@requirements.txt" \<br>
  -F "project_id=test-project"<br>
```<br>
<br>
#### 2. Edit Ontology via JSON<br>
```bash<br>
curl -X PUT "http://localhost:8000/api/ontology/" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"metadata": {"name": "Updated Ontology"}, "classes": [...]}'<br>
```<br>
<br>
#### 3. Get Ontology Statistics<br>
```bash<br>
curl "http://localhost:8000/api/ontology/statistics"<br>
```<br>
<br>
## Integration with Existing System<br>
<br>
### File Upload Enhancement<br>
<br>
The existing `/api/upload` endpoint now:<br>
1. Stores files persistently using the new storage service<br>
2. Associates files with processing jobs<br>
3. Maintains file references throughout the workflow<br>
4. Supports retry processing of stored files<br>
<br>
### Workflow Integration<br>
<br>
- Files are stored with metadata before processing begins<br>
- Camunda workflows receive file IDs instead of temporary content<br>
- Processing status is tracked and associated with stored files<br>
- Failed processes can be retried without re-uploading<br>
<br>
## Benefits<br>
<br>
### Ontology Management<br>
- **User-Friendly**: JSON editing is more accessible than RDF/Turtle<br>
- **Version Control**: Built-in backup and restore capabilities<br>
- **Validation**: Prevents invalid ontology structures<br>
- **Extensible**: Easy to add new classes and properties<br>
- **Synchronized**: Changes are automatically pushed to Fuseki<br>
<br>
### File Storage<br>
- **Persistent**: Files survive system restarts and failures<br>
- **Scalable**: Choose appropriate backend for your scale<br>
- **Reliable**: Hash verification and metadata tracking<br>
- **Efficient**: Deduplication and optimized storage<br>
- **Integrated**: Seamless integration with existing workflows<br>
<br>
## Security Considerations<br>
<br>
- File uploads are validated for type and size<br>
- MinIO supports access control and encryption<br>
- PostgreSQL provides ACID compliance and backup support<br>
- API endpoints include proper error handling<br>
- File access can be restricted by project/user context<br>
<br>
## Future Enhancements<br>
<br>
- **User Authentication**: Role-based access control<br>
- **File Versioning**: Track file changes over time<br>
- **Advanced Search**: Full-text search across stored files<br>
- **Caching**: Redis caching for frequently accessed files<br>
- **CDN Integration**: CloudFront/CDN support for MinIO<br>
- **Compression**: Automatic file compression for storage efficiency<br>

