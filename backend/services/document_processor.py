"""
Document Processing Service for ODRAS
Integrates file storage with existing Camunda BPMN workflows.
"""

import logging
from typing import Dict, Any, Optional
from .config import Settings
from .file_storage import FileStorageService

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Handles document upload, storage, and processing workflow integration.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.file_storage = FileStorageService(settings)
    
    async def process_uploaded_document(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        iterations: int = 10,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded document through the complete ODRAS workflow.
        
        Args:
            file_content: The file content as bytes
            filename: Original filename
            content_type: MIME type of the file
            iterations: Number of Monte Carlo iterations
            llm_provider: LLM provider to use
            llm_model: LLM model to use
            project_id: Associated project ID
            
        Returns:
            Dict containing processing results and metadata
        """
        try:
            # Step 1: Store the file persistently
            storage_result = await self.file_storage.store_file(
                content=file_content,
                filename=filename,
                content_type=content_type,
                project_id=project_id,
                tags={
                    "processing_status": "uploaded",
                    "llm_provider": llm_provider,
                    "llm_model": llm_model,
                    "iterations": iterations
                }
            )
            
            if not storage_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to store file: {storage_result['error']}"
                }
            
            file_id = storage_result["file_id"]
            logger.info(f"File stored successfully with ID: {file_id}")
            
            # Step 2: Decode text content for processing
            try:
                document_text = file_content.decode('utf-8', errors='ignore')
            except Exception as e:
                logger.warning(f"Failed to decode file as UTF-8: {e}")
                document_text = ""
            
            # Step 3: Start Camunda BPMN process with file reference
            from backend.main import start_camunda_process
            
            process_id = await start_camunda_process(
                document_content=document_text,
                document_filename=filename,
                llm_provider=llm_provider,
                llm_model=llm_model,
                iterations=iterations,
                file_id=file_id  # Pass the stored file ID
            )
            
            if not process_id:
                # If Camunda process failed, we should still keep the file
                # but update its status
                await self._update_file_status(file_id, "process_failed")
                return {
                    "success": False,
                    "error": "Failed to start Camunda process",
                    "file_id": file_id  # Return file_id so user can retry processing
                }
            
            # Step 4: Update file status to processing
            await self._update_file_status(file_id, "processing")
            
            return {
                "success": True,
                "file_id": file_id,
                "process_id": process_id,
                "filename": filename,
                "size": len(file_content),
                "content_type": content_type,
                "message": "Document uploaded and processing started",
                "storage_backend": self.settings.storage_backend,
                "metadata": storage_result["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Failed to process uploaded document: {e}")
            return {
                "success": False,
                "error": f"Document processing failed: {str(e)}"
            }
    
    async def retry_processing(
        self,
        file_id: str,
        iterations: int = 10,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Retry processing of a previously uploaded file.
        
        Args:
            file_id: Stored file ID
            iterations: Number of Monte Carlo iterations
            llm_provider: LLM provider to use
            llm_model: LLM model to use
            
        Returns:
            Dict containing retry results
        """
        try:
            # Retrieve the stored file
            file_data = await self.file_storage.retrieve_file(file_id)
            if file_data is None:
                return {
                    "success": False,
                    "error": f"File {file_id} not found"
                }
            
            # Get file content and decode
            file_content = file_data["content"]
            document_text = file_content.decode('utf-8', errors='ignore')
            
            # Start new Camunda process
            from backend.main import start_camunda_process
            
            process_id = await start_camunda_process(
                document_content=document_text,
                document_filename=f"retry_{file_id}",
                llm_provider=llm_provider,
                llm_model=llm_model,
                iterations=iterations,
                file_id=file_id
            )
            
            if not process_id:
                await self._update_file_status(file_id, "retry_failed")
                return {
                    "success": False,
                    "error": "Failed to start retry process"
                }
            
            await self._update_file_status(file_id, "retry_processing")
            
            return {
                "success": True,
                "file_id": file_id,
                "process_id": process_id,
                "message": "File processing retry started"
            }
            
        except Exception as e:
            logger.error(f"Failed to retry processing for file {file_id}: {e}")
            return {
                "success": False,
                "error": f"Retry failed: {str(e)}"
            }
    
    async def get_processing_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get the current processing status of a file.
        
        Args:
            file_id: Stored file ID
            
        Returns:
            Dict containing status information
        """
        try:
            # Check if file exists
            file_data = await self.file_storage.retrieve_file(file_id)
            if file_data is None:
                return {
                    "success": False,
                    "error": f"File {file_id} not found"
                }
            
            # For now, return basic status
            # In a full implementation, you'd query the processing database
            return {
                "success": True,
                "file_id": file_id,
                "status": "stored",
                "message": "File is stored and available for processing"
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing status for file {file_id}: {e}")
            return {
                "success": False,
                "error": f"Status check failed: {str(e)}"
            }
    
    async def _update_file_status(self, file_id: str, status: str):
        """
        Update the processing status of a file.
        
        Args:
            file_id: Stored file ID
            status: New status
        """
        try:
            # In a full implementation, you'd update the file metadata
            # with the new status. For now, we'll just log it.
            logger.info(f"File {file_id} status updated to: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update file status for {file_id}: {e}")
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """
        Get information about supported file formats.
        
        Returns:
            Dict containing supported formats and processing capabilities
        """
        return {
            "supported_formats": [
                {
                    "extension": ".txt",
                    "mime_type": "text/plain",
                    "description": "Plain text documents"
                },
                {
                    "extension": ".md",
                    "mime_type": "text/markdown",
                    "description": "Markdown documents"
                },
                {
                    "extension": ".pdf",
                    "mime_type": "application/pdf",
                    "description": "PDF documents (text extraction)"
                },
                {
                    "extension": ".docx",
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "description": "Microsoft Word documents"
                }
            ],
            "max_file_size": "100MB",
            "processing_capabilities": [
                "Requirements extraction",
                "Monte Carlo analysis",
                "LLM-powered processing",
                "Ontology mapping"
            ],
            "storage_backends": ["local", "minio", "postgresql"]
        }
