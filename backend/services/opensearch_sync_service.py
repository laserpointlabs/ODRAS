"""
OpenSearch Sync Service

Provides bulk reindexing and sync repair capabilities to keep OpenSearch
in sync with PostgreSQL (source of truth).

Features:
- Bulk reindex from Postgres to OpenSearch
- Incremental sync (only updated chunks)
- Sync monitoring and metrics
- Drift detection and repair
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from backend.services.config import Settings
from backend.services.db import DatabaseService
from backend.rag.storage.text_search_factory import create_text_search_store
from backend.db.queries import now_utc

logger = logging.getLogger(__name__)


class OpenSearchSyncService:
    """
    Service for syncing PostgreSQL chunks to OpenSearch.
    
    Provides:
    - Bulk reindexing from Postgres
    - Incremental sync (only changed chunks)
    - Sync status monitoring
    - Drift detection
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.db_service = DatabaseService(self.settings)
        self.text_search_store = create_text_search_store(self.settings)
        
        if not self.text_search_store:
            logger.warning("OpenSearch not available - sync service will not function")

    async def reindex_all_chunks(
        self,
        project_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Reindex all chunks from PostgreSQL to OpenSearch.
        
        Args:
            project_id: Optional project filter (reindex only this project)
            batch_size: Number of chunks to process per batch
            
        Returns:
            Dict with sync statistics
        """
        if not self.text_search_store:
            return {
                "success": False,
                "error": "OpenSearch not available",
                "chunks_indexed": 0,
            }
        
        try:
            # Ensure index exists
            await self.text_search_store.ensure_index("knowledge_chunks")
            
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Build query to get all chunks
                    # Note: knowledge_chunks table doesn't have page/start_char/end_char
                    query = """
                        SELECT 
                            kc.id as chunk_id,
                            kc.content as text,
                            kc.sequence_number as chunk_index,
                            kc.asset_id as doc_id,
                            ka.project_id,
                            ka.title as asset_title,
                            ka.document_type,
                            kc.created_at
                        FROM knowledge_chunks kc
                        JOIN knowledge_assets ka ON kc.asset_id = ka.id
                    """
                    
                    if project_id:
                        query += " WHERE ka.project_id = %s"
                        cur.execute(query, (project_id,))
                    else:
                        cur.execute(query)
                    
                    all_chunks = cur.fetchall()
                    
                    logger.info(f"Found {len(all_chunks)} chunks to reindex")
                    
                    # Process in batches
                    chunks_indexed = 0
                    chunks_failed = 0
                    
                    for i in range(0, len(all_chunks), batch_size):
                        batch = all_chunks[i:i + batch_size]
                        documents = []
                        
                        for chunk in batch:
                            chunk_id = chunk[0]
                            text = chunk[1] or ""
                            chunk_index = chunk[2] or 0
                            doc_id = chunk[3]
                            project_id_val = chunk[4]
                            asset_title = chunk[5] or ""
                            document_type = chunk[6] or "document"
                            created_at = chunk[7]
                            
                            document = {
                                "chunk_id": chunk_id,
                                "original_chunk_id": chunk_id,
                                "content": text,
                                "text": text,
                                "title": asset_title,  # Use asset title
                                "project_id": project_id_val,
                                "asset_id": doc_id,
                                "doc_id": doc_id,
                                "chunk_index": chunk_index,
                                "document_type": document_type,
                                "created_at": created_at.isoformat() if created_at else now_utc().isoformat(),
                            }
                            documents.append(document)
                        
                        # Bulk index batch
                        try:
                            success = await self.text_search_store.bulk_index(
                                index="knowledge_chunks",
                                documents=documents,
                            )
                            if success:
                                chunks_indexed += len(documents)
                                logger.info(f"Indexed batch {i//batch_size + 1}: {len(documents)} chunks")
                            else:
                                chunks_failed += len(documents)
                                logger.warning(f"Failed to index batch {i//batch_size + 1}")
                        except Exception as e:
                            chunks_failed += len(documents)
                            logger.error(f"Error indexing batch {i//batch_size + 1}: {e}")
                    
                    return {
                        "success": True,
                        "chunks_indexed": chunks_indexed,
                        "chunks_failed": chunks_failed,
                        "total_chunks": len(all_chunks),
                    }
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Reindexing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_indexed": 0,
            }

    async def reindex_updated_chunks(
        self,
        since: Optional[datetime] = None,
        project_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Reindex only chunks that have been updated since a given time.
        
        Args:
            since: Only reindex chunks updated after this time (default: last 24 hours)
            project_id: Optional project filter
            batch_size: Number of chunks per batch
            
        Returns:
            Dict with sync statistics
        """
        if not self.text_search_store:
            return {
                "success": False,
                "error": "OpenSearch not available",
                "chunks_indexed": 0,
            }
        
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)
        
        try:
            await self.text_search_store.ensure_index("knowledge_chunks")
            
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Query for updated chunks (using created_at as proxy)
                    query = """
                        SELECT 
                            kc.id as chunk_id,
                            kc.content as text,
                            kc.sequence_number as chunk_index,
                            kc.asset_id as doc_id,
                            ka.project_id,
                            ka.title as asset_title,
                            ka.document_type,
                            kc.created_at
                        FROM knowledge_chunks kc
                        JOIN knowledge_assets ka ON kc.asset_id = ka.id
                        WHERE kc.created_at >= %s
                    """
                    
                    params = [since]
                    if project_id:
                        query += " AND ka.project_id = %s"
                        params.append(project_id)
                    
                    cur.execute(query, params)
                    updated_chunks = cur.fetchall()
                    
                    if not updated_chunks:
                        return {
                            "success": True,
                            "chunks_indexed": 0,
                            "total_chunks": 0,
                            "message": "No chunks updated since specified time",
                        }
                    
                    # Process in batches (same as reindex_all_chunks)
                    chunks_indexed = 0
                    chunks_failed = 0
                    
                    for i in range(0, len(updated_chunks), batch_size):
                        batch = updated_chunks[i:i + batch_size]
                        documents = []
                        
                        for chunk in batch:
                            chunk_id = chunk[0]
                            text = chunk[1] or ""
                            chunk_index = chunk[2] or 0
                            doc_id = chunk[3]
                            project_id_val = chunk[4]
                            asset_title = chunk[5] or ""
                            document_type = chunk[6] or "document"
                            created_at = chunk[7]
                            
                            document = {
                                "chunk_id": chunk_id,
                                "original_chunk_id": chunk_id,
                                "content": text,
                                "text": text,
                                "title": asset_title,
                                "project_id": project_id_val,
                                "asset_id": doc_id,
                                "doc_id": doc_id,
                                "chunk_index": chunk_index,
                                "document_type": document_type,
                                "created_at": created_at.isoformat() if created_at else now_utc().isoformat(),
                            }
                            documents.append(document)
                        
                        try:
                            success = await self.text_search_store.bulk_index(
                                index="knowledge_chunks",
                                documents=documents,
                            )
                            if success:
                                chunks_indexed += len(documents)
                            else:
                                chunks_failed += len(documents)
                        except Exception as e:
                            chunks_failed += len(documents)
                            logger.error(f"Error indexing batch: {e}")
                    
                    return {
                        "success": True,
                        "chunks_indexed": chunks_indexed,
                        "chunks_failed": chunks_failed,
                        "total_chunks": len(updated_chunks),
                    }
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Incremental reindexing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_indexed": 0,
            }

    async def get_sync_status(
        self,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get sync status metrics comparing Postgres and OpenSearch.
        
        Returns:
            Dict with counts, lag, and sync health metrics
        """
        if not self.text_search_store:
            return {
                "opensearch_available": False,
                "error": "OpenSearch not available",
            }
        
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Count chunks in Postgres
                    if project_id:
                        cur.execute(
                            """
                            SELECT COUNT(*) 
                            FROM knowledge_chunks kc
                            JOIN knowledge_assets ka ON kc.asset_id = ka.id
                            WHERE ka.project_id = %s
                            """,
                            (project_id,)
                        )
                    else:
                        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
                    pg_count = cur.fetchone()[0]
                    
                # Count chunks in OpenSearch (approximate via search)
                # Note: This is an approximation - for exact counts, use index stats API
                try:
                    # Simple search with size=0 to get count
                    response = await self.text_search_store.client.count(
                        index="knowledge_chunks",
                        body={"query": {"match_all": {}}}
                    )
                    os_count = response.get("count", 0)
                except Exception as e:
                    logger.warning(f"Could not get OpenSearch count: {e}")
                    os_count = None
                
                drift = pg_count - os_count if os_count is not None else None
                drift_percentage = (drift / pg_count * 100) if (drift and pg_count > 0) else None
                
                return {
                    "opensearch_available": True,
                    "postgres_count": pg_count,
                    "opensearch_count": os_count,
                    "drift": drift,
                    "drift_percentage": drift_percentage,
                    "in_sync": drift == 0 if drift is not None else None,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "opensearch_available": True,
                "error": str(e),
            }
