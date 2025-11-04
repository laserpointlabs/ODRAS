"""
Admin Configuration API Module

Handles admin-only configuration endpoints for RAG and file processing.
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException

from backend.api.core import get_db_service
from backend.services.auth import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/rag-config")
async def get_rag_config(
    admin_user: Dict = Depends(get_admin_user)
):
    """Get current RAG implementation configuration (Admin only)."""
    try:
        db_service = get_db_service()
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT rag_implementation, rag_bpmn_model, rag_model_version
                    FROM installation_config
                    WHERE is_active = TRUE
                    LIMIT 1
                """)
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Installation configuration not found")
                
                return {
                    "rag_implementation": result[0],
                    "rag_bpmn_model": result[1],
                    "rag_model_version": result[2],
                    "available_implementations": ["hardcoded", "bpmn"]
                }
        finally:
            db_service._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve RAG configuration: {str(e)}")


@router.put("/rag-config")
async def update_rag_config(
    config: Dict[str, str],
    user: Dict = Depends(get_admin_user)
):
    """Update RAG implementation configuration (Admin only)."""
    try:
        rag_implementation = config.get("rag_implementation")
        rag_bpmn_model = config.get("rag_bpmn_model")
        rag_model_version = config.get("rag_model_version")
        
        if not rag_implementation or rag_implementation not in ["hardcoded", "bpmn"]:
            raise HTTPException(
                status_code=400,
                detail="rag_implementation must be either 'hardcoded' or 'bpmn'"
            )
        
        # Validate BPMN-specific fields when BPMN is selected
        if rag_implementation == "bpmn":
            if not rag_bpmn_model:
                raise HTTPException(
                    status_code=400,
                    detail="rag_bpmn_model is required when using BPMN implementation"
                )
            if not rag_model_version:
                raise HTTPException(
                    status_code=400,
                    detail="rag_model_version is required when using BPMN implementation"
                )
        
        db_service = get_db_service()
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE installation_config
                    SET rag_implementation = %s, rag_bpmn_model = %s, rag_model_version = %s, updated_at = NOW()
                    WHERE is_active = TRUE
                """, (rag_implementation, rag_bpmn_model, rag_model_version))
                
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Installation configuration not found")
                
                conn.commit()
                logger.info(f"RAG configuration updated to '{rag_implementation}' (model: {rag_bpmn_model}, version: {rag_model_version}) by admin {user.get('username')}")
                
                return {
                    "success": True,
                    "rag_implementation": rag_implementation,
                    "rag_bpmn_model": rag_bpmn_model,
                    "rag_model_version": rag_model_version,
                    "message": f"RAG configuration updated to {rag_implementation}"
                }
        finally:
            db_service._return(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update RAG configuration: {str(e)}")


@router.get("/file-processing-config")
async def get_file_processing_config(
    admin_user: Dict = Depends(get_admin_user)
):
    """Get current file processing configuration (Admin only)."""
    try:
        db_service = get_db_service()
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT file_processing_implementation
                    FROM installation_config
                    WHERE is_active = true
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                
                if not result:
                    return {
                        "success": True,
                        "file_processing_implementation": "bpmn"
                    }
                
                return {
                    "success": True,
                    "file_processing_implementation": result[0] or "bpmn",
                    "available_implementations": ["hardcoded", "bpmn"]
                }
        finally:
            db_service._return(conn)
    
    except Exception as e:
        logger.error(f"Failed to retrieve file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file processing configuration: {str(e)}")


@router.put("/file-processing-config")
async def update_file_processing_config(
    config: Dict[str, str],
    user: Dict = Depends(get_admin_user)
):
    """Update file processing configuration (Admin only)."""
    try:
        file_processing_implementation = config.get("file_processing_implementation")
        
        if not file_processing_implementation or file_processing_implementation not in ["hardcoded", "bpmn"]:
            raise HTTPException(
                status_code=400,
                detail="file_processing_implementation must be either 'hardcoded' or 'bpmn'"
            )
        
        db_service = get_db_service()
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE installation_config
                    SET file_processing_implementation = %s,
                        updated_at = NOW()
                    WHERE is_active = true
                """, (file_processing_implementation,))
                
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="No active installation config found")
            
            conn.commit()
            logger.info(f"Updated file processing configuration to: {file_processing_implementation}")
            
            return {
                "success": True,
                "file_processing_implementation": file_processing_implementation,
                "message": f"File processing configuration updated to {file_processing_implementation}"
            }
        
        finally:
            db_service._return(conn)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file processing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update file processing configuration: {str(e)}")

