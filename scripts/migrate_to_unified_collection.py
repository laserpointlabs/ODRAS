"""
Migration script to consolidate knowledge collections into unified das_knowledge collection.

This script migrates:
- knowledge_chunks → das_knowledge (tag: knowledge_type=project)
- das_training_* → das_knowledge (tag: knowledge_type=training)
- system_index_vectors → das_knowledge (tag: knowledge_type=system)

Preserves all metadata and maintains SQL-first pattern.
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.config import Settings
from backend.services.db import DatabaseService
from backend.services.qdrant_service import get_qdrant_service
from backend.services.embedding_service import get_embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedCollectionMigrator:
    """Migrates existing collections to unified das_knowledge collection."""
    
    def __init__(self, settings: Settings = None):
        """Initialize migrator with dependencies."""
        self.settings = settings or Settings()
        self.db_service = DatabaseService(self.settings)
        self.qdrant_service = get_qdrant_service(self.settings)
        self.embedding_service = get_embedding_service(self.settings)
        
        self.unified_collection = "das_knowledge"
        self.migration_stats = {
            "project_chunks": 0,
            "training_chunks": 0,
            "system_chunks": 0,
            "errors": 0,
        }
    
    async def migrate_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all collections to unified collection.
        
        Args:
            dry_run: If True, only report what would be migrated without actually migrating
        
        Returns:
            Migration statistics
        """
        logger.info(f"Starting migration to unified collection (dry_run={dry_run})...")
        
        if not dry_run:
            # Ensure unified collection exists
            self.qdrant_service.ensure_collection(self.unified_collection, 384)
        
        # Migrate project chunks
        await self._migrate_project_chunks(dry_run)
        
        # Migrate training chunks
        await self._migrate_training_chunks(dry_run)
        
        # Migrate system index chunks
        await self._migrate_system_chunks(dry_run)
        
        logger.info(f"Migration complete. Stats: {self.migration_stats}")
        return self.migration_stats
    
    async def _migrate_project_chunks(self, dry_run: bool) -> None:
        """Migrate knowledge_chunks to unified collection."""
        logger.info("Migrating project chunks (knowledge_chunks)...")
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get all project chunks
                cur.execute("""
                    SELECT kc.id, kc.content, kc.token_count, kc.metadata, 
                           kc.embedding_model, kc.qdrant_point_id, kc.sequence_number,
                           ka.project_id, ka.document_type, ka.title, ka.id as asset_id
                    FROM knowledge_chunks kc
                    JOIN knowledge_assets ka ON kc.asset_id = ka.id
                    ORDER BY ka.project_id, kc.sequence_number
                """)
                chunks = cur.fetchall()
                
                logger.info(f"Found {len(chunks)} project chunks to migrate")
                
                if dry_run:
                    self.migration_stats["project_chunks"] = len(chunks)
                    return
                
                # Migrate vectors from Qdrant collections
                source_collections = ["knowledge_chunks", "knowledge_chunks_768"]
                vectors_to_migrate = []
                
                # Retrieve vectors from old collections
                for collection_name in source_collections:
                    try:
                        # Scroll through all points in collection
                        offset = None
                        while True:
                            scroll_result = self.qdrant_service.client.scroll(
                                collection_name=collection_name,
                                limit=100,
                                offset=offset,
                                with_payload=True,
                                with_vectors=True,
                            )
                            
                            if not scroll_result[0]:
                                break
                            
                            for point in scroll_result[0]:
                                payload = point.payload or {}
                                old_chunk_id = payload.get("chunk_id") or str(point.id)
                                
                                # Find matching SQL chunk
                                matching_chunk = next(
                                    (c for c in chunks if str(c[0]) == old_chunk_id or str(c[5]) == str(point.id)),
                                    None
                                )
                                
                                if matching_chunk:
                                    vectors_to_migrate.append({
                                        "point": point,
                                        "chunk_data": matching_chunk,
                                        "source_collection": collection_name,
                                    })
                            
                            offset = scroll_result[1]
                            if not offset:
                                break
                                
                    except Exception as e:
                        logger.warning(f"Could not scroll collection {collection_name}: {e}")
                
                logger.info(f"Found {len(vectors_to_migrate)} vectors to migrate")
                
                # Migrate each chunk with its vector
                migrated_original_chunk_ids = set()
                for vector_data in vectors_to_migrate:
                    point = vector_data["point"]
                    chunk = vector_data["chunk_data"]
                    original_chunk_id = str(chunk[0])
                    
                    if original_chunk_id in migrated_original_chunk_ids:
                        continue  # Already migrated
                    
                    try:
                        unified_chunk_id = await self._migrate_chunk_to_unified(
                            chunk_id=original_chunk_id,
                            content=chunk[1],
                            token_count=chunk[2] or 0,
                            metadata=chunk[3] or {},
                            embedding_model=chunk[4] or "all-MiniLM-L6-v2",
                            qdrant_point_id=str(point.id),
                            sequence_number=chunk[6] or 0,
                            knowledge_type="project",
                            project_id=str(chunk[7]) if chunk[7] else None,
                            domain=self._extract_domain(chunk[8], chunk[9]),
                            source_metadata={
                                "source_table": "knowledge_chunks",
                                "original_chunk_id": original_chunk_id,
                                "asset_id": str(chunk[10]),
                                "document_type": chunk[8],
                                "title": chunk[9],
                            },
                            vector=point.vector,  # Include vector for migration
                        )
                        
                        # Store vector in unified collection
                        unified_payload = {
                            "chunk_id": unified_chunk_id,
                            "knowledge_type": "project",
                            "domain": self._extract_domain(chunk[8], chunk[9]),
                            "project_id": str(chunk[7]) if chunk[7] else None,
                            **{k: v for k, v in (point.payload or {}).items() if k not in ["chunk_id", "text", "content"]}
                        }
                        
                        self.qdrant_service.store_vectors(
                            self.unified_collection,
                            [{
                                "id": unified_chunk_id,
                                "vector": point.vector,
                                "payload": unified_payload,
                            }]
                        )
                        
                        migrated_original_chunk_ids.add(original_chunk_id)
                        self.migration_stats["project_chunks"] += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate project chunk {original_chunk_id}: {e}")
                        self.migration_stats["errors"] += 1
                
                # Migrate chunks without vectors (regenerate embeddings)
                for chunk in chunks:
                    if str(chunk[0]) not in migrated_original_chunk_ids:
                        try:
                            unified_chunk_id = await self._migrate_chunk_to_unified(
                                chunk_id=str(chunk[0]),
                                content=chunk[1],
                                token_count=chunk[2] or 0,
                                metadata=chunk[3] or {},
                                embedding_model=chunk[4] or "all-MiniLM-L6-v2",
                                qdrant_point_id=None,  # No vector, will regenerate
                                sequence_number=chunk[6] or 0,
                                knowledge_type="project",
                                project_id=str(chunk[7]) if chunk[7] else None,
                                domain=self._extract_domain(chunk[8], chunk[9]),
                                source_metadata={
                                    "source_table": "knowledge_chunks",
                                    "original_chunk_id": str(chunk[0]),
                                    "asset_id": str(chunk[10]),
                                    "document_type": chunk[8],
                                    "title": chunk[9],
                                },
                            )
                            
                            # Regenerate embedding and store
                            embeddings = self.embedding_service.generate_embeddings(
                                [chunk[1]],
                                model_id=chunk[4] or "all-MiniLM-L6-v2"
                            )
                            
                            unified_payload = {
                                "chunk_id": unified_chunk_id,
                                "knowledge_type": "project",
                                "domain": self._extract_domain(chunk[8], chunk[9]),
                                "project_id": str(chunk[7]) if chunk[7] else None,
                            }
                            
                            self.qdrant_service.store_vectors(
                                self.unified_collection,
                                [{
                                    "id": unified_chunk_id,
                                    "vector": embeddings[0],
                                    "payload": unified_payload,
                                }]
                            )
                            
                            self.migration_stats["project_chunks"] += 1
                        except Exception as e:
                            logger.error(f"Failed to migrate project chunk {chunk[0]}: {e}")
                            self.migration_stats["errors"] += 1
                        
        finally:
            self.db_service._return(conn)
    
    async def _migrate_training_chunks(self, dry_run: bool) -> None:
        """Migrate das_training_chunks to unified collection."""
        logger.info("Migrating training chunks (das_training_chunks)...")
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get all training chunks
                cur.execute("""
                    SELECT dtc.chunk_id, dtc.content, dtc.token_count, dtc.metadata,
                           dtc.embedding_model, dtc.qdrant_point_id, dtc.sequence_number,
                           dtc.collection_id, dtc.asset_id,
                           dtcol.domain, dta.title
                    FROM das_training_chunks dtc
                    JOIN das_training_collections dtcol ON dtc.collection_id = dtcol.collection_id
                    JOIN das_training_assets dta ON dtc.asset_id = dta.asset_id
                    ORDER BY dtc.collection_id, dtc.sequence_number
                """)
                chunks = cur.fetchall()
                
                logger.info(f"Found {len(chunks)} training chunks to migrate")
                
                if dry_run:
                    self.migration_stats["training_chunks"] = len(chunks)
                    return
                
                # Migrate each chunk
                for chunk in chunks:
                    try:
                        await self._migrate_chunk_to_unified(
                            chunk_id=str(chunk[0]),
                            content=chunk[1],
                            token_count=chunk[2] or 0,
                            metadata=chunk[3] or {},
                            embedding_model=chunk[4] or "all-MiniLM-L6-v2",
                            qdrant_point_id=chunk[5],
                            sequence_number=chunk[6] or 0,
                            knowledge_type="training",
                            project_id=None,  # Training chunks are global
                            domain=chunk[9] or "general",
                            source_metadata={
                                "source_table": "das_training_chunks",
                                "original_chunk_id": str(chunk[0]),
                                "collection_id": str(chunk[7]),
                                "asset_id": str(chunk[8]),
                                "title": chunk[10],
                            }
                        )
                        self.migration_stats["training_chunks"] += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate training chunk {chunk[0]}: {e}")
                        self.migration_stats["errors"] += 1
                        
        finally:
            self.db_service._return(conn)
    
    async def _migrate_system_chunks(self, dry_run: bool) -> None:
        """Migrate system_index_vectors to unified collection."""
        logger.info("Migrating system chunks (system_index_vectors)...")
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get all system chunks
                cur.execute("""
                    SELECT siv.vector_id, siv.content, siv.token_count, siv.metadata,
                           siv.embedding_model, siv.qdrant_point_id, siv.sequence_number,
                           si.index_id, si.entity_type, si.entity_id, si.domain, si.project_id
                    FROM system_index_vectors siv
                    JOIN system_index si ON siv.index_id = si.index_id
                    ORDER BY si.index_id, siv.sequence_number
                """)
                chunks = cur.fetchall()
                
                logger.info(f"Found {len(chunks)} system chunks to migrate")
                
                if dry_run:
                    self.migration_stats["system_chunks"] = len(chunks)
                    return
                
                # Migrate each chunk
                for chunk in chunks:
                    try:
                        await self._migrate_chunk_to_unified(
                            chunk_id=str(chunk[0]),
                            content=chunk[1],
                            token_count=chunk[2] or 0,
                            metadata=chunk[3] or {},
                            embedding_model=chunk[4] or "all-MiniLM-L6-v2",
                            qdrant_point_id=chunk[5],
                            sequence_number=chunk[6] or 0,
                            knowledge_type="system",
                            project_id=str(chunk[11]) if chunk[11] else None,
                            domain=chunk[10] or chunk[8] or "general",
                            source_metadata={
                                "source_table": "system_index_vectors",
                                "original_vector_id": str(chunk[0]),
                                "index_id": str(chunk[7]),
                                "entity_type": chunk[8],
                                "entity_id": chunk[9],
                            }
                        )
                        self.migration_stats["system_chunks"] += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate system chunk {chunk[0]}: {e}")
                        self.migration_stats["errors"] += 1
                        
        finally:
            self.db_service._return(conn)
    
    async def _migrate_chunk_to_unified(
        self,
        chunk_id: str,
        content: str,
        token_count: int,
        metadata: Dict[str, Any],
        embedding_model: str,
        qdrant_point_id: Optional[str],
        sequence_number: int,
        knowledge_type: str,
        project_id: Optional[str],
        domain: str,
        source_metadata: Dict[str, Any],
        vector: Optional[List[float]] = None,
    ) -> str:
        """Migrate a single chunk to unified collection."""
        # Generate new unified chunk ID
        unified_chunk_id = uuid4()
        
        # Merge metadata
        unified_metadata = {
            **(metadata if isinstance(metadata, dict) else {}),
            **source_metadata,
        }
        
        # Store in unified SQL table
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO das_knowledge_chunks
                    (chunk_id, content, knowledge_type, domain, project_id, tags, metadata,
                     token_count, embedding_model, qdrant_point_id, qdrant_collection,
                     sequence_number, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    str(unified_chunk_id),
                    content,
                    knowledge_type,
                    domain,
                    project_id,
                    [],  # Tags can be extracted from metadata if needed
                    json.dumps(unified_metadata),
                    token_count,
                    embedding_model,
                    str(unified_chunk_id),  # Use unified chunk_id as Qdrant point ID
                    self.unified_collection,
                    sequence_number,
                ))
                conn.commit()
        finally:
            self.db_service._return(conn)
        
        return str(unified_chunk_id)
    
    def _extract_domain(self, document_type: Optional[str], title: Optional[str]) -> str:
        """Extract domain from document metadata."""
        if document_type:
            doc_type_lower = document_type.lower()
            if "ontology" in doc_type_lower:
                return "ontology"
            elif "requirement" in doc_type_lower:
                return "requirements"
            elif "acquisition" in doc_type_lower:
                return "acquisition"
        
        if title:
            title_lower = title.lower()
            if "ontology" in title_lower:
                return "ontology"
            elif "requirement" in title_lower:
                return "requirements"
        
        return "general"


async def main():
    """Main migration function."""
    import sys
    
    dry_run = "--dry-run" in sys.argv
    
    migrator = UnifiedCollectionMigrator()
    stats = await migrator.migrate_all(dry_run=dry_run)
    
    print("\n" + "="*60)
    print("Migration Statistics:")
    print("="*60)
    print(f"Project chunks: {stats['project_chunks']}")
    print(f"Training chunks: {stats['training_chunks']}")
    print(f"System chunks: {stats['system_chunks']}")
    print(f"Errors: {stats['errors']}")
    print("="*60)
    
    if dry_run:
        print("\n⚠️  DRY RUN - No data was migrated")
    else:
        print("\n✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
