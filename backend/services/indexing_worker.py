"""
Indexing Worker Service

Event-driven worker that automatically indexes system entities when events occur.
Listens to system events and indexes files, ontologies, requirements, etc.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from .config import Settings
from .db import DatabaseService
from .indexing_service_interface import IndexingServiceInterface

logger = logging.getLogger(__name__)


class IndexingWorker:
    """
    Worker that listens to system events and automatically indexes entities.
    
    This worker:
    - Monitors project_event table for new events
    - Extracts entity information from events
    - Indexes entities using IndexingServiceInterface
    - Updates indexes when entities change
    """
    
    def __init__(
        self,
        settings: Settings,
        indexing_service: IndexingServiceInterface,
        db_service: Optional[DatabaseService] = None,
    ):
        """
        Initialize indexing worker.
        
        Args:
            settings: Application settings
            indexing_service: Indexing service implementation
            db_service: Optional database service
        """
        self.settings = settings
        self.indexing_service = indexing_service
        self.db_service = db_service or DatabaseService(settings)
        self.running = False
        self.poll_interval = 30  # Poll every 30 seconds
        
        logger.info("Indexing Worker initialized")
    
    async def start(self) -> None:
        """Start the indexing worker."""
        if self.running:
            logger.warning("Indexing worker already running")
            return
        
        self.running = True
        logger.info("Indexing worker started")
        
        # Start background task
        asyncio.create_task(self._worker_loop())
    
    async def stop(self) -> None:
        """Stop the indexing worker."""
        self.running = False
        logger.info("Indexing worker stopped")
    
    async def _worker_loop(self) -> None:
        """Main worker loop that processes events."""
        last_processed_at = datetime.utcnow() - timedelta(minutes=5)  # Start from 5 minutes ago
        
        while self.running:
            try:
                # Process new events
                await self._process_new_events(last_processed_at)
                
                # Update last processed timestamp
                last_processed_at = datetime.utcnow()
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in indexing worker loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _process_new_events(self, since: datetime) -> None:
        """Process events since the given timestamp."""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Get new events
                    cur.execute("""
                        SELECT event_id, project_id, event_type, event_data, semantic_summary, created_at
                        FROM project_event
                        WHERE created_at > %s
                        ORDER BY created_at ASC
                        LIMIT 100
                    """, (since,))
                    events = cur.fetchall()
                    
                    if not events:
                        return
                    
                    logger.debug(f"Processing {len(events)} events for indexing")
                    
                    for event_row in events:
                        event_id, project_id, event_type, event_data, semantic_summary, created_at = event_row
                        await self._process_event(
                            event_id=str(event_id),
                            project_id=str(project_id) if project_id else None,
                            event_type=event_type,
                            event_data=event_data or {},
                            semantic_summary=semantic_summary,
                            created_at=created_at
                        )
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to process new events: {e}")
    
    async def _process_event(
        self,
        event_id: str,
        project_id: Optional[str],
        event_type: str,
        event_data: Dict[str, Any],
        semantic_summary: Optional[str],
        created_at: datetime,
    ) -> None:
        """Process a single event and index relevant entities."""
        try:
            # Map event types to indexing actions
            indexing_actions = {
                "file_uploaded": self._index_file_event,
                "file_processing_completed": self._index_file_event,
                "ontology_created": self._index_ontology_event,
                "ontology_modified": self._index_ontology_event,
                "ontology_saved": self._index_ontology_event,
                "class_created": self._index_ontology_event,
                "class_updated": self._index_ontology_event,
                "knowledge_asset_created": self._index_knowledge_asset_event,
                "knowledge_asset_updated": self._index_knowledge_asset_event,
                "das_interaction": self._index_conversation_event,
                "das_question": self._index_conversation_event,
                "das_response": self._index_conversation_event,
            }
            
            action = indexing_actions.get(event_type)
            if action:
                await action(event_id, project_id, event_data, semantic_summary)
            else:
                logger.debug(f"No indexing action for event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Failed to process event {event_id}: {e}")
    
    async def _index_file_event(
        self,
        event_id: str,
        project_id: Optional[str],
        event_data: Dict[str, Any],
        semantic_summary: Optional[str],
    ) -> None:
        """Index a file entity from event."""
        try:
            file_id = event_data.get("file_id") or event_data.get("id")
            if not file_id:
                logger.debug(f"No file_id in event data: {event_data}")
                return
            
            # Get file metadata from database
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, filename, content_type, metadata, tags
                        FROM files
                        WHERE id = %s
                    """, (file_id,))
                    row = cur.fetchone()
                    
                    if not row:
                        logger.debug(f"File not found: {file_id}")
                        return
                    
                    file_id_db, filename, content_type, metadata, tags = row
                    
                    # Create content summary
                    content_summary = semantic_summary or f"File: {filename}"
                    if metadata and isinstance(metadata, dict):
                        if metadata.get("description"):
                            content_summary += f"\n{metadata['description']}"
                    
                    # Index the file
                    await self.indexing_service.index_entity(
                        entity_type="file",
                        entity_id=str(file_id_db),
                        content_summary=content_summary,
                        project_id=project_id,
                        metadata={
                            "filename": filename,
                            "content_type": content_type,
                            "event_id": event_id,
                        },
                        tags=list(tags) if tags else [],
                        domain="files"
                    )
                    
                    logger.info(f"Indexed file: {filename} ({file_id_db})")
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to index file event: {e}")
    
    async def _index_ontology_event(
        self,
        event_id: str,
        project_id: Optional[str],
        event_data: Dict[str, Any],
        semantic_summary: Optional[str],
    ) -> None:
        """Index an ontology entity from event."""
        try:
            graph_iri = event_data.get("graph_iri") or event_data.get("iri")
            if not graph_iri:
                logger.debug(f"No graph_iri in event data: {event_data}")
                return
            
            # Get ontology metadata
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT graph_iri, label, role
                        FROM ontologies_registry
                        WHERE graph_iri = %s
                    """, (graph_iri,))
                    row = cur.fetchone()
                    
                    if not row:
                        logger.debug(f"Ontology not found: {graph_iri}")
                        return
                    
                    graph_iri_db, label, role = row
                    
                    # Create content summary
                    content_summary = semantic_summary or f"Ontology: {label or graph_iri}"
                    
                    # Index the ontology
                    await self.indexing_service.index_entity(
                        entity_type="ontology",
                        entity_id=graph_iri_db,
                        content_summary=content_summary,
                        project_id=project_id,
                        entity_uri=graph_iri_db,
                        metadata={
                            "label": label,
                            "role": role,
                            "event_id": event_id,
                        },
                        domain="ontology"
                    )
                    
                    logger.info(f"Indexed ontology: {label} ({graph_iri_db})")
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to index ontology event: {e}")
    
    async def _index_knowledge_asset_event(
        self,
        event_id: str,
        project_id: Optional[str],
        event_data: Dict[str, Any],
        semantic_summary: Optional[str],
    ) -> None:
        """Index a knowledge asset from event."""
        try:
            asset_id = event_data.get("asset_id") or event_data.get("id")
            if not asset_id:
                logger.debug(f"No asset_id in event data: {event_data}")
                return
            
            # Get asset metadata
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, title, document_type, description, metadata
                        FROM knowledge_assets
                        WHERE id = %s
                    """, (asset_id,))
                    row = cur.fetchone()
                    
                    if not row:
                        logger.debug(f"Knowledge asset not found: {asset_id}")
                        return
                    
                    asset_id_db, title, document_type, description, metadata = row
                    
                    # Create content summary
                    content_summary = semantic_summary or description or f"Knowledge asset: {title}"
                    
                    # Index the asset
                    await self.indexing_service.index_entity(
                        entity_type="knowledge_asset",
                        entity_id=str(asset_id_db),
                        content_summary=content_summary,
                        project_id=project_id,
                        metadata={
                            "title": title,
                            "document_type": document_type,
                            "event_id": event_id,
                        },
                        domain="knowledge"
                    )
                    
                    logger.info(f"Indexed knowledge asset: {title} ({asset_id_db})")
                    
            finally:
                self.db_service._return(conn)
                
        except Exception as e:
            logger.error(f"Failed to index knowledge asset event: {e}")
    
    async def _index_conversation_event(
        self,
        event_id: str,
        project_id: Optional[str],
        event_data: Dict[str, Any],
        semantic_summary: Optional[str],
    ) -> None:
        """Index a conversation/DAS interaction from event."""
        try:
            thread_id = event_data.get("thread_id") or event_data.get("project_thread_id")
            if not thread_id:
                logger.debug(f"No thread_id in event data: {event_data}")
                return
            
            # Create content summary from semantic summary or event data
            content_summary = semantic_summary or event_data.get("message") or event_data.get("content", "")
            
            if not content_summary:
                return
            
            # Index the conversation event
            await self.indexing_service.index_entity(
                entity_type="conversation",
                entity_id=f"{thread_id}:{event_id}",
                content_summary=content_summary,
                project_id=project_id,
                metadata={
                    "thread_id": thread_id,
                    "event_id": event_id,
                    "event_type": event_data.get("event_type", "das_interaction"),
                },
                domain="conversation"
            )
            
            logger.debug(f"Indexed conversation event: {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to index conversation event: {e}")
    
    async def process_event_immediate(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        project_id: Optional[str] = None,
        semantic_summary: Optional[str] = None,
    ) -> None:
        """
        Process an event immediately (for synchronous indexing).
        
        This can be called directly when events occur, bypassing the polling loop.
        """
        event_id = event_data.get("event_id") or str(uuid4())
        await self._process_event(
            event_id=event_id,
            project_id=project_id,
            event_type=event_type,
            event_data=event_data,
            semantic_summary=semantic_summary,
            created_at=datetime.utcnow()
        )
