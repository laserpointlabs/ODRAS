"""
Federated Access API for ODRAS
Enables cross-installation artifact sharing via IRIs without authentication.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
import io

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.file_storage import get_file_storage_service, FileStorageService
from ..services.installation_iri_service import get_installation_iri_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/federated", tags=["Federated Access"])


def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService(Settings())


@router.get("/files/{file_id}/download")
async def federated_download_file(
    file_id: str,
    storage_service: FileStorageService = Depends(get_file_storage_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Download a public file via federated access.
    
    Allows external systems to download files using just the file ID
    from an IRI, without authentication (public files only).
    """
    try:
        logger.info(f"Federated download request for file: {file_id}")
        
        # Check if file is public
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_metadata.get("visibility") != "public":
            raise HTTPException(
                status_code=403, 
                detail="File is private. Contact installation for access."
            )
        
        # Retrieve file content
        file_data = await storage_service.retrieve_file(file_id)
        if file_data is None:
            raise HTTPException(status_code=404, detail="File content not found")

        # Create streaming response
        file_content = file_data["content"]
        filename = file_metadata.get("filename", f"file_{file_id}")
        content_type = file_metadata.get("content_type", "application/octet-stream")

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content)),
                "X-ODRAS-Installation": get_installation_iri_service().settings.installation_name,
                "X-ODRAS-Authority": get_installation_iri_service().settings.authority_contact,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed federated download for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/files/{file_id}/metadata")
async def federated_get_file_metadata(
    file_id: str,
    storage_service: FileStorageService = Depends(get_file_storage_service),
):
    """
    Get public file metadata via federated access.
    """
    try:
        logger.info(f"Federated metadata request for file: {file_id}")
        
        file_metadata = await storage_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_metadata.get("visibility") != "public":
            raise HTTPException(
                status_code=403,
                detail="File metadata is private. Contact installation for access."
            )
        
        # Return sanitized metadata (remove internal fields)
        public_metadata = {
            "file_id": file_metadata["file_id"],
            "filename": file_metadata["filename"],
            "content_type": file_metadata["content_type"],
            "size": file_metadata["size"],
            "created_at": file_metadata["created_at"],
            "iri": file_metadata.get("iri"),
            "tags": file_metadata.get("tags", {}),
            "installation": {
                "organization": get_installation_iri_service().settings.installation_organization,
                "contact": get_installation_iri_service().settings.authority_contact,
                "base_uri": get_installation_iri_service().installation_base_uri
            }
        }
        
        return public_metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get federated file metadata {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Metadata access failed: {str(e)}")


@router.get("/knowledge/{asset_id}/content")
async def federated_get_knowledge_content(
    asset_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get public knowledge asset content via federated access.
    
    Enables external systems to access knowledge content and analysis results.
    """
    try:
        logger.info(f"Federated knowledge content request: {asset_id}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if knowledge asset is public
                cur.execute("""
                    SELECT ka.*, f.filename as source_filename
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    WHERE ka.id = %s AND ka.is_public = TRUE
                """, (asset_id,))
                
                asset_row = cur.fetchone()
                if not asset_row:
                    raise HTTPException(
                        status_code=404, 
                        detail="Public knowledge asset not found"
                    )
                
                asset_dict = dict(zip([desc[0] for desc in cur.description], asset_row))
                
                # Get all chunks for this asset
                cur.execute("""
                    SELECT content, chunk_type, sequence_number, token_count, metadata
                    FROM knowledge_chunks 
                    WHERE asset_id = %s 
                    ORDER BY sequence_number
                """, (asset_id,))
                
                chunk_rows = cur.fetchall()
                chunks = []
                total_tokens = 0
                
                for chunk_row in chunk_rows:
                    content, chunk_type, seq_num, token_count, metadata = chunk_row
                    chunks.append({
                        "content": content,
                        "chunk_type": chunk_type,
                        "sequence_number": seq_num,
                        "token_count": token_count or 0,
                        "metadata": metadata or {}
                    })
                    total_tokens += token_count or 0
                
                # Combine all chunk content
                full_content = "\\n\\n".join([chunk["content"] for chunk in chunks])
                
                return {
                    "iri": asset_dict.get("iri"),
                    "asset_id": asset_id,
                    "title": asset_dict["title"],
                    "document_type": asset_dict["document_type"],
                    "status": asset_dict["status"],
                    "traceability_status": asset_dict.get("traceability_status", "linked"),
                    "content": full_content,
                    "chunks": chunks,
                    "total_chunks": len(chunks),
                    "total_tokens": total_tokens,
                    "created_at": asset_dict["created_at"].isoformat() if asset_dict["created_at"] else None,
                    "source_filename": asset_dict.get("source_filename"),
                    "installation": {
                        "organization": get_installation_iri_service().settings.installation_organization,
                        "contact": get_installation_iri_service().settings.authority_contact,
                        "base_uri": get_installation_iri_service().installation_base_uri
                    },
                    "accessed_at": datetime.now().isoformat()
                }
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get federated knowledge content {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge access failed: {str(e)}")


@router.get("/knowledge/{asset_id}/metadata")
async def federated_get_knowledge_metadata(
    asset_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get public knowledge asset metadata via federated access.
    """
    try:
        logger.info(f"Federated knowledge metadata request: {asset_id}")
        
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ka.id, ka.title, ka.document_type, ka.status, ka.created_at,
                           ka.iri, ka.traceability_status, ka.content_summary,
                           f.filename as source_filename
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id = f.id
                    WHERE ka.id = %s AND ka.is_public = TRUE
                """, (asset_id,))
                
                result = cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Public knowledge asset not found"
                    )
                
                asset_dict = dict(zip([desc[0] for desc in cur.description], result))
                
                return {
                    "asset_id": asset_id,
                    "iri": asset_dict.get("iri"),
                    "title": asset_dict["title"],
                    "document_type": asset_dict["document_type"],
                    "status": asset_dict["status"],
                    "traceability_status": asset_dict.get("traceability_status", "linked"),
                    "content_summary": asset_dict.get("content_summary"),
                    "created_at": asset_dict["created_at"].isoformat() if asset_dict["created_at"] else None,
                    "source_filename": asset_dict.get("source_filename"),
                    "installation": {
                        "organization": get_installation_iri_service().settings.installation_organization,
                        "contact": get_installation_iri_service().settings.authority_contact,
                        "base_uri": get_installation_iri_service().installation_base_uri
                    },
                    "accessed_at": datetime.now().isoformat()
                }
                
        finally:
            db._return(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get federated knowledge metadata {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Metadata access failed: {str(e)}")


@router.get("/installations/discover")
async def discover_installation():
    """
    Installation discovery endpoint for federated systems.
    
    Allows external systems to discover this installation's capabilities,
    supported resource types, and contact information.
    """
    try:
        iri_service = get_installation_iri_service()
        
        return {
            "installation": {
                "name": iri_service.settings.installation_name,
                "type": iri_service.settings.installation_type,
                "organization": iri_service.settings.installation_organization,
                "base_uri": iri_service.installation_base_uri,
                "contact": iri_service.settings.authority_contact,
                "program_office": iri_service.settings.installation_program_office
            },
            "capabilities": {
                "supported_resource_types": ["files", "knowledge", "ontologies", "projects"],
                "supported_formats": ["json", "rdf", "turtle"],
                "federated_access": True,
                "public_resolution": True
            },
            "endpoints": {
                "iri_resolution": f"{iri_service.installation_base_uri}/api/iri/public/resolve",
                "file_download": f"{iri_service.installation_base_uri}/api/federated/files/{{file_id}}/download",
                "knowledge_content": f"{iri_service.installation_base_uri}/api/federated/knowledge/{{asset_id}}/content",
                "discovery": f"{iri_service.installation_base_uri}/api/federated/installations/discover"
            },
            "discovered_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed installation discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
