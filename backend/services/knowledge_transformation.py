"""
Knowledge Transformation Service.

Orchestrates the complete pipeline for transforming uploaded documents into
queryable knowledge assets with embeddings, chunks, and graph relationships.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
from datetime import datetime, timezone
import asyncio
from dataclasses import asdict

from .config import Settings
from .db import DatabaseService  
from .file_storage import get_file_storage_service
from .qdrant_service import get_qdrant_service
from .neo4j_service import get_neo4j_service
from .embedding_service import get_embedding_service
from .chunking_service import get_chunking_service, DocumentChunk

logger = logging.getLogger(__name__)

class KnowledgeTransformationService:
    """
    Service for transforming documents into knowledge assets.
    
    Orchestrates the complete pipeline from raw files to searchable knowledge
    including chunking, embedding generation, and relationship extraction.
    """
    
    def __init__(self, settings: Settings = None):
        """Initialize transformation service with all dependencies."""
        self.settings = settings or Settings()
        
        # Initialize services
        self.db_service = DatabaseService(self.settings)
        self.file_storage_service = get_file_storage_service()
        self.qdrant_service = get_qdrant_service(self.settings)
        self.neo4j_service = get_neo4j_service(self.settings)
        self.embedding_service = get_embedding_service(self.settings)
        self.chunking_service = get_chunking_service(self.settings)
        
        logger.info("Knowledge transformation service initialized")
    
    async def create_processing_job(
        self, 
        asset_id: str, 
        job_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a processing job record.
        
        Args:
            asset_id: Knowledge asset ID
            job_type: Type of processing job
            metadata: Optional job metadata
            
        Returns:
            Job ID
        """
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_processing_jobs 
                    (id, asset_id, job_type, status, progress_percent, started_at, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    job_id, asset_id, job_type, 'running', 0, now, now, json.dumps(metadata or {})
                ))
                conn.commit()
                
            logger.info(f"Created processing job {job_id} for asset {asset_id}")
            return job_id
            
        finally:
            self.db_service._return(conn)
    
    async def create_knowledge_asset(
        self,
        source_file_id: str,
        project_id: str,
        title: str,
        document_type: str = 'unknown',
        processing_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a knowledge asset record.
        
        Args:
            source_file_id: ID of the source file
            project_id: Project ID
            title: Asset title
            document_type: Type of document
            processing_options: Processing configuration
            
        Returns:
            Asset ID
        """
        asset_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_assets 
                    (id, source_file_id, project_id, title, document_type, status, 
                     created_at, updated_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    asset_id, source_file_id, project_id, title, document_type, 
                    'processing', now, now, json.dumps(processing_options or {})
                ))
                conn.commit()
                
            logger.info(f"Created knowledge asset {asset_id} for file {source_file_id}")
            return asset_id
            
        finally:
            self.db_service._return(conn)
    
    async def update_job_progress(
        self, 
        job_id: str, 
        progress_percent: int,
        status: str = 'running',
        error_message: Optional[str] = None
    ):
        """Update processing job progress."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                if status == 'completed':
                    cur.execute("""
                        UPDATE knowledge_processing_jobs 
                        SET progress_percent = %s, status = %s, completed_at = %s, error_message = %s
                        WHERE id = %s
                    """, (progress_percent, status, datetime.now(timezone.utc), error_message, job_id))
                else:
                    cur.execute("""
                        UPDATE knowledge_processing_jobs 
                        SET progress_percent = %s, status = %s, error_message = %s
                        WHERE id = %s
                    """, (progress_percent, status, error_message, job_id))
                conn.commit()
                
        finally:
            self.db_service._return(conn)
    
    async def extract_text_content(self, file_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text content from a file.
        
        Args:
            file_id: File ID to extract content from
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            # Get file metadata
            file_metadata = await self.file_storage_service.get_file_metadata(file_id)
            if not file_metadata:
                raise ValueError(f"File {file_id} not found")
            
            # Get file content
            content = await self.file_storage_service.get_file_content(file_id)
            if not content:
                raise ValueError(f"Could not retrieve content for file {file_id}")
            
            # Extract text based on content type
            content_type = file_metadata.get('content_type', 'application/octet-stream')
            filename = file_metadata.get('filename', 'unknown')
            
            if content_type.startswith('text/') or content_type == 'application/octet-stream':
                # Plain text or binary treated as text
                try:
                    extracted_text = content.decode('utf-8')
                except UnicodeDecodeError:
                    extracted_text = content.decode('utf-8', errors='ignore')
                    logger.warning(f"Unicode decode errors in file {file_id}, some characters ignored")
                    
            elif content_type == 'application/pdf':
                # TODO: Implement PDF text extraction
                logger.warning(f"PDF text extraction not yet implemented for file {file_id}")
                extracted_text = f"[PDF content extraction not implemented: {filename}]"
                
            else:
                logger.warning(f"Unsupported content type {content_type} for file {file_id}")
                extracted_text = f"[Unsupported file type: {content_type}]"
            
            extraction_metadata = {
                'filename': filename,
                'content_type': content_type,
                'original_size': len(content),
                'extracted_text_length': len(extracted_text),
                'extraction_method': 'utf8_decode'
            }
            
            logger.info(f"Extracted {len(extracted_text)} characters from file {file_id}")
            return extracted_text, extraction_metadata
            
        except Exception as e:
            logger.error(f"Text extraction failed for file {file_id}: {str(e)}")
            raise RuntimeError(f"Text extraction failed: {str(e)}")
    

    
    async def store_chunks_in_database(
        self, 
        asset_id: str, 
        chunks: List[DocumentChunk],
        embedding_model: str
    ) -> List[str]:
        """
        Store chunks in PostgreSQL database.
        
        Args:
            asset_id: Knowledge asset ID
            chunks: List of document chunks
            embedding_model: Model used for embeddings
            
        Returns:
            List of chunk IDs
        """
        chunk_ids = []
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                for chunk in chunks:
                    chunk_id = str(uuid4())
                    chunk_ids.append(chunk_id)
                    
                    # Prepare chunk metadata
                    chunk_metadata = {
                        'section_path': chunk.metadata.section_path,
                        'page_number': chunk.metadata.page_number,
                        'cross_references': chunk.metadata.cross_references or [],
                        'extracted_entities': chunk.metadata.extracted_entities or {},
                        'confidence_score': chunk.metadata.confidence_score,
                        'start_char': chunk.metadata.start_char,
                        'end_char': chunk.metadata.end_char
                    }
                    
                    cur.execute("""
                        INSERT INTO knowledge_chunks 
                        (id, asset_id, sequence_number, chunk_type, content, token_count, 
                         metadata, embedding_model, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        chunk_id, asset_id, chunk.metadata.sequence_number, 
                        chunk.metadata.chunk_type, chunk.content, chunk.metadata.token_count,
                        json.dumps(chunk_metadata), embedding_model, datetime.now(timezone.utc)
                    ))
                
                conn.commit()
                logger.info(f"Stored {len(chunks)} chunks for asset {asset_id}")
                
        finally:
            self.db_service._return(conn)
        
        return chunk_ids
    
    async def generate_and_store_embeddings(
        self, 
        chunks: List[DocumentChunk],
        chunk_ids: List[str],
        asset_id: str,
        project_id: str,
        embedding_model: str = 'all-MiniLM-L6-v2',
        collection_name: str = 'knowledge_chunks'
    ) -> List[str]:
        """
        Generate embeddings and store in Qdrant.
        
        Args:
            chunks: List of document chunks
            chunk_ids: Corresponding chunk IDs from database
            asset_id: Knowledge asset ID
            embedding_model: Embedding model to use
            collection_name: Qdrant collection name
            
        Returns:
            List of Qdrant point IDs
        """
        try:
            # Ensure collection exists
            model_info = self.embedding_service.get_model_info(embedding_model)
            if not model_info:
                raise ValueError(f"Unknown embedding model: {embedding_model}")
            
            vector_size = model_info['dimensions']
            self.qdrant_service.ensure_collection(collection_name, vector_size)
            
            # Extract text content for embedding
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} chunks using {embedding_model}")
            embeddings = self.embedding_service.generate_embeddings(texts, embedding_model)
            
            # Prepare vectors for Qdrant
            vectors_data = []
            qdrant_point_ids = []
            
            for i, (chunk, chunk_id, embedding) in enumerate(zip(chunks, chunk_ids, embeddings)):
                qdrant_point_id = str(uuid4())
                qdrant_point_ids.append(qdrant_point_id)
                
                # Create payload with metadata for filtering
                payload = {
                    'chunk_id': chunk_id,
                    'asset_id': asset_id,
                    'project_id': project_id,
                    'chunk_type': chunk.metadata.chunk_type,
                    'sequence_number': chunk.metadata.sequence_number,
                    'token_count': chunk.metadata.token_count,
                    'content_preview': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content
                }
                
                vectors_data.append({
                    'id': qdrant_point_id,
                    'vector': embedding,
                    'payload': payload
                })
            
            # Store vectors in Qdrant
            stored_ids = self.qdrant_service.store_vectors(collection_name, vectors_data)
            
            # Update chunk records with Qdrant point IDs
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    for chunk_id, qdrant_point_id in zip(chunk_ids, qdrant_point_ids):
                        cur.execute("""
                            UPDATE knowledge_chunks 
                            SET qdrant_point_id = %s 
                            WHERE id = %s
                        """, (qdrant_point_id, chunk_id))
                    conn.commit()
            finally:
                self.db_service._return(conn)
            
            logger.info(f"Stored {len(stored_ids)} vectors in Qdrant collection {collection_name}")
            return qdrant_point_ids
            
        except Exception as e:
            logger.error(f"Embedding generation and storage failed: {str(e)}")
            raise RuntimeError(f"Embedding storage failed: {str(e)}")
    
    async def update_asset_processing_stats(
        self, 
        asset_id: str, 
        stats: Dict[str, Any]
    ):
        """Update knowledge asset with processing statistics."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE knowledge_assets 
                    SET processing_stats = %s, status = %s, updated_at = %s
                    WHERE id = %s
                """, (json.dumps(stats), 'active', datetime.now(timezone.utc), asset_id))
                conn.commit()
                
            logger.info(f"Updated processing stats for asset {asset_id}")
            
        finally:
            self.db_service._return(conn)
    
    async def transform_file_to_knowledge(
        self,
        file_id: str,
        project_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Main orchestration method to transform a file into a knowledge asset.
        
        Args:
            file_id: Source file ID
            project_id: Project ID
            processing_options: Optional processing configuration
            
        Returns:
            Knowledge asset ID
        """
        processing_config = {
            'chunking_strategy': 'hybrid',
            'chunk_size': 512,
            'chunk_overlap': 50,
            'embedding_model': 'all-MiniLM-L6-v2',
            'extract_relationships': True,
            **(processing_options or {})
        }
        
        job_id = None
        asset_id = None
        
        try:
            logger.info(f"Starting knowledge transformation for file {file_id}")
            
            # Step 1: Extract text content
            logger.info("Step 1: Extracting text content")
            extracted_text, extraction_metadata = await self.extract_text_content(file_id)
            
            if not extracted_text.strip():
                raise ValueError("No text content could be extracted from file")
            
            # Step 2: Create knowledge asset
            logger.info("Step 2: Creating knowledge asset")
            file_metadata = await self.file_storage_service.get_file_metadata(file_id)
            title = file_metadata.get('filename', f'Asset from file {file_id}')
            
            asset_id = await self.create_knowledge_asset(
                source_file_id=file_id,
                project_id=project_id,
                title=title,
                document_type=processing_config.get('document_type', 'unknown'),
                processing_options=processing_config
            )
            
            # Step 3: Create processing job
            job_id = await self.create_processing_job(
                asset_id=asset_id,
                job_type='full_process',
                metadata={'file_id': file_id, 'processing_config': processing_config}
            )
            
            await self.update_job_progress(job_id, 20, 'running')
            
            # Step 4: Chunk the content
            logger.info("Step 4: Chunking document content")
            chunks = self.chunking_service.chunk_document(
                extracted_text,
                document_metadata=extraction_metadata,
                chunking_config=processing_config
            )
            
            if not chunks:
                raise ValueError("No chunks could be generated from content")
            
            await self.update_job_progress(job_id, 40, 'running')
            
            # Step 5: Store chunks in database
            logger.info("Step 5: Storing chunks in database")
            chunk_ids = await self.store_chunks_in_database(
                asset_id, chunks, processing_config['embedding_model']
            )
            
            await self.update_job_progress(job_id, 60, 'running')
            
            # Step 6: Generate and store embeddings
            logger.info("Step 6: Generating and storing embeddings")
            qdrant_point_ids = await self.generate_and_store_embeddings(
                chunks, chunk_ids, asset_id, project_id, processing_config['embedding_model']
            )
            
            await self.update_job_progress(job_id, 80, 'running')
            
            # Step 7: Update processing statistics
            logger.info("Step 7: Updating processing statistics")
            chunk_stats = self.chunking_service.get_chunking_stats(chunks)
            processing_stats = {
                'chunk_count': len(chunks),
                'token_count': chunk_stats['total_tokens'],
                'avg_tokens_per_chunk': chunk_stats['avg_tokens_per_chunk'],
                'embedding_model': processing_config['embedding_model'],
                'chunking_strategy': processing_config['chunking_strategy'],
                'processing_completed_at': datetime.now(timezone.utc).isoformat(),
                **extraction_metadata
            }
            
            await self.update_asset_processing_stats(asset_id, processing_stats)
            await self.update_job_progress(job_id, 100, 'completed')
            
            logger.info(f"Successfully transformed file {file_id} to knowledge asset {asset_id}")
            logger.info(f"Generated {len(chunks)} chunks with {chunk_stats['total_tokens']} total tokens")
            
            return asset_id
            
        except Exception as e:
            error_msg = f"Knowledge transformation failed for file {file_id}: {str(e)}"
            logger.error(error_msg)
            
            # Update job status if we have a job ID
            if job_id:
                await self.update_job_progress(job_id, 0, 'failed', str(e))
            
            # Update asset status if we have an asset ID
            if asset_id:
                conn = self.db_service._conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE knowledge_assets 
                            SET status = %s, updated_at = %s
                            WHERE id = %s
                        """, ('failed', datetime.now(timezone.utc), asset_id))
                        conn.commit()
                finally:
                    self.db_service._return(conn)
            
            raise RuntimeError(error_msg)

# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_knowledge_transformation_service(settings: Settings = None) -> KnowledgeTransformationService:
    """Get configured knowledge transformation service instance."""
    return KnowledgeTransformationService(settings)

async def transform_file_to_knowledge_asset(
    file_id: str,
    project_id: str,
    processing_options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Utility function to transform a file to knowledge asset.
    
    Args:
        file_id: Source file ID
        project_id: Project ID 
        processing_options: Optional processing configuration
        
    Returns:
        Knowledge asset ID
    """
    service = get_knowledge_transformation_service()
    return await service.transform_file_to_knowledge(file_id, project_id, processing_options)


