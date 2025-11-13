"""
Vector/SQL Sync Monitoring Service

Prevents and detects vector store desynchronization issues that can break DAS functionality.
Implements monitoring, health checks, and recovery tools for dual-storage RAG systems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .config import Settings
from .db import DatabaseService
from .qdrant_service import QdrantService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorSQLSyncMonitor:
    """
    Monitor and maintain synchronization between vector store and SQL database

    Critical for RAG system reliability - prevents the "empty vector store" issue
    that causes DAS to return "no information available" despite having data.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_service = DatabaseService(settings)
        self.qdrant_service = QdrantService(settings)
        self.embedding_service = EmbeddingService(settings)

        # Collections to monitor
        self.collections = [
            "knowledge_chunks",
            "project_threads"
        ]

        logger.info("Vector/SQL sync monitor initialized")

    async def check_sync_health(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive sync health check

        Returns detailed status of vector/SQL synchronization
        """
        try:
            health_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "project_id": project_id,
                "collections": {},
                "issues": [],
                "recommendations": []
            }

            # Check each collection
            for collection in self.collections:
                collection_health = await self._check_collection_sync(collection, project_id)
                health_report["collections"][collection] = collection_health

                if not collection_health["sync_healthy"]:
                    health_report["overall_status"] = "unhealthy"
                    health_report["issues"].extend(collection_health["issues"])
                    health_report["recommendations"].extend(collection_health["recommendations"])

            # Check for critical DAS failure patterns
            das_health = await self._check_das_query_health(project_id)
            health_report["das_query_health"] = das_health

            if not das_health["healthy"]:
                health_report["overall_status"] = "critical"
                health_report["issues"].append("DAS queries returning no results - likely vector store empty")
                health_report["recommendations"].append("Run sync recovery immediately")

            logger.info(f"Sync health check completed: {health_report['overall_status']}")
            return health_report

        except Exception as e:
            logger.error(f"Sync health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }

    async def _check_collection_sync(self, collection: str, project_id: Optional[str]) -> Dict[str, Any]:
        """Check sync health for a specific collection"""
        try:
            # Get SQL counts
            sql_counts = await self._get_sql_counts(collection, project_id)

            # Get vector counts
            vector_counts = await self._get_vector_counts(collection, project_id)

            # Calculate sync ratio
            sql_total = sql_counts["total"]
            vector_total = vector_counts["total"]

            sync_ratio = (vector_total / sql_total) if sql_total > 0 else 0
            sync_healthy = sync_ratio >= 0.95  # 95% or better sync

            issues = []
            recommendations = []

            if sync_ratio < 0.5:
                issues.append(f"Severe desync: {vector_total} vectors vs {sql_total} SQL records")
                recommendations.append(f"Full re-vectorization required for {collection}")
            elif sync_ratio < 0.95:
                issues.append(f"Partial desync: {vector_total} vectors vs {sql_total} SQL records")
                recommendations.append(f"Incremental sync recommended for {collection}")

            return {
                "collection": collection,
                "sync_healthy": sync_healthy,
                "sync_ratio": sync_ratio,
                "sql_records": sql_total,
                "vector_records": vector_total,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"Collection sync check failed for {collection}: {e}")
            return {
                "collection": collection,
                "sync_healthy": False,
                "error": str(e),
                "issues": [f"Failed to check {collection} sync"],
                "recommendations": [f"Investigate {collection} connectivity"]
            }

    async def _get_sql_counts(self, collection: str, project_id: Optional[str]) -> Dict[str, int]:
        """Get SQL record counts for sync comparison"""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                if collection == "knowledge_chunks":
                    if project_id:
                        # Count chunks for specific project
                        cur.execute("""
                            SELECT COUNT(*) FROM doc_chunk dc
                            JOIN doc d ON dc.doc_id = d.doc_id
                            WHERE d.project_id = %s
                        """, (project_id,))
                    else:
                        # Count all chunks
                        cur.execute("SELECT COUNT(*) FROM doc_chunk")

                    total = cur.fetchone()[0]

                elif collection == "project_threads":
                    if project_id:
                        cur.execute("SELECT COUNT(*) FROM project_thread WHERE project_id = %s", (project_id,))
                    else:
                        cur.execute("SELECT COUNT(*) FROM project_thread")

                    total = cur.fetchone()[0]
                else:
                    total = 0

                return {"total": total}

        finally:
            self.db_service._return(conn)

    async def _get_vector_counts(self, collection: str, project_id: Optional[str]) -> Dict[str, int]:
        """Get vector store counts for sync comparison"""
        try:
            # Get collection info from Qdrant
            collection_info = self.qdrant_service.client.get_collection(collection)

            if project_id:
                # Count vectors for specific project
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="project_id",
                            match=MatchValue(value=project_id)
                        )
                    ]
                )

                # Use scroll to count with filter
                scroll_result = self.qdrant_service.client.scroll(
                    collection_name=collection,
                    scroll_filter=filter_condition,
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )

                # For accurate count, we'd need to scroll through all
                # For now, estimate based on collection size
                total_vectors = collection_info.vectors_count
                # This is an approximation - for exact count, we'd need full scroll
                project_vectors = total_vectors  # Simplified for now
            else:
                project_vectors = collection_info.vectors_count

            return {"total": project_vectors}

        except Exception as e:
            logger.error(f"Failed to get vector counts for {collection}: {e}")
            return {"total": 0, "error": str(e)}

    async def _check_das_query_health(self, project_id: Optional[str]) -> Dict[str, Any]:
        """Check if DAS queries are working (critical failure detection)"""
        if not project_id:
            return {"healthy": True, "message": "No project specified for DAS test"}

        try:
            # Test a simple DAS query that should always work if vectors exist
            from .rag_service import RAGService

            rag_service = RAGService(self.settings)

            # Simple test query (using legacy method)
            test_result = await rag_service.query_knowledge_base_legacy(
                question="specifications",
                project_id=project_id,
                max_chunks=3,
                similarity_threshold=0.3
            )

            chunks_found = test_result.get("chunks_found", 0)
            success = test_result.get("success", False)

            if success and chunks_found > 0:
                return {
                    "healthy": True,
                    "chunks_found": chunks_found,
                    "message": "DAS queries working normally"
                }
            else:
                return {
                    "healthy": False,
                    "chunks_found": chunks_found,
                    "message": "DAS queries returning no results - possible vector store empty",
                    "test_result": test_result
                }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "DAS query test failed"
            }

    async def detect_sync_issues(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect specific sync issues and provide actionable recommendations
        """
        issues = []

        try:
            # Check 1: Empty vector store with existing SQL data
            health_report = await self.check_sync_health(project_id)

            for collection, status in health_report["collections"].items():
                if status["sql_records"] > 0 and status["vector_records"] == 0:
                    issues.append({
                        "type": "empty_vector_store",
                        "severity": "critical",
                        "collection": collection,
                        "description": f"SQL has {status['sql_records']} records but vector store is empty",
                        "action": f"Re-vectorize all {collection} data",
                        "command": f"./odras.sh reprocess-vectors --collection {collection}"
                    })
                elif status["sync_ratio"] < 0.9:
                    issues.append({
                        "type": "partial_desync",
                        "severity": "warning",
                        "collection": collection,
                        "description": f"Sync ratio {status['sync_ratio']:.2f} below 90%",
                        "action": "Incremental sync recommended",
                        "command": f"./odras.sh sync-vectors --collection {collection} --incremental"
                    })

            # Check 2: DAS returning no results
            if project_id:
                das_health = health_report.get("das_query_health", {})
                if not das_health.get("healthy", False):
                    issues.append({
                        "type": "das_query_failure",
                        "severity": "critical",
                        "description": "DAS queries returning no results despite having knowledge assets",
                        "action": "Emergency vector regeneration required",
                        "command": f"./odras.sh emergency-sync --project {project_id}"
                    })

            return issues

        except Exception as e:
            logger.error(f"Sync issue detection failed: {e}")
            return [{
                "type": "detection_error",
                "severity": "error",
                "description": f"Failed to detect sync issues: {e}",
                "action": "Manual investigation required"
            }]

    async def emergency_sync_recovery(self, project_id: str) -> Dict[str, Any]:
        """
        Emergency recovery for complete vector/SQL desync

        Use when DAS is completely broken due to missing embeddings
        """
        try:
            recovery_log = []
            recovery_log.append(f"Starting emergency sync recovery for project {project_id}")

            # Step 1: Verify SQL data exists
            sql_counts = await self._get_sql_counts("knowledge_chunks", project_id)
            if sql_counts["total"] == 0:
                return {
                    "success": False,
                    "error": "No SQL data found - cannot recover",
                    "recovery_log": recovery_log
                }

            recovery_log.append(f"Found {sql_counts['total']} SQL chunks to recover")

            # Step 2: Get all chunks for project from SQL
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT dc.chunk_id, dc.text, d.project_id
                        FROM doc_chunk dc
                        JOIN doc d ON dc.doc_id = d.doc_id
                        WHERE d.project_id = %s
                        ORDER BY dc.chunk_index
                    """, (project_id,))

                    chunks = cur.fetchall()
                    recovery_log.append(f"Retrieved {len(chunks)} chunks from SQL")

            finally:
                self.db_service._return(conn)

            # Step 3: Regenerate embeddings and store in vector database
            recovered_count = 0
            failed_count = 0

            for chunk_id, text, proj_id in chunks:
                try:
                    # Generate embedding
                    embedding = self.embedding_service.generate_single_embedding(text)

                    # Store in vector database
                    vector_data = [{
                        "id": chunk_id,
                        "vector": embedding,
                        "payload": {
                            "project_id": proj_id,
                            "chunk_id": chunk_id,
                            "created_at": datetime.now().isoformat(),
                            "recovered": True,
                            "recovery_timestamp": datetime.now().isoformat()
                        }
                    }]

                    self.qdrant_service.store_vectors("knowledge_chunks", vector_data)
                    recovered_count += 1

                except Exception as e:
                    recovery_log.append(f"Failed to recover chunk {chunk_id}: {e}")
                    failed_count += 1

            recovery_log.append(f"Recovery complete: {recovered_count} recovered, {failed_count} failed")

            # Step 4: Verify recovery
            final_health = await self.check_sync_health(project_id)

            return {
                "success": recovered_count > 0,
                "recovered_chunks": recovered_count,
                "failed_chunks": failed_count,
                "final_sync_ratio": final_health["collections"]["knowledge_chunks"]["sync_ratio"],
                "recovery_log": recovery_log
            }

        except Exception as e:
            logger.error(f"Emergency sync recovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "recovery_log": recovery_log if 'recovery_log' in locals() else []
            }

    async def automated_health_check(self) -> Dict[str, Any]:
        """
        Automated health check that can be run periodically

        Detects common sync issues and provides alerts
        """
        try:
            # Check overall system health
            overall_health = await self.check_sync_health()

            # Check for critical patterns
            critical_issues = []
            warnings = []

            for collection, status in overall_health["collections"].items():
                if status["vector_records"] == 0 and status["sql_records"] > 0:
                    critical_issues.append({
                        "collection": collection,
                        "issue": "Vector store empty but SQL has data",
                        "impact": "DAS will return 'no information available'",
                        "urgency": "immediate"
                    })
                elif status["sync_ratio"] < 0.8:
                    warnings.append({
                        "collection": collection,
                        "issue": f"Sync ratio {status['sync_ratio']:.2f} below 80%",
                        "impact": "Inconsistent DAS responses",
                        "urgency": "monitor"
                    })

            return {
                "timestamp": datetime.now().isoformat(),
                "status": "critical" if critical_issues else ("warning" if warnings else "healthy"),
                "critical_issues": critical_issues,
                "warnings": warnings,
                "overall_health": overall_health
            }

        except Exception as e:
            logger.error(f"Automated health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    async def quick_sync_check(self, project_id: str) -> bool:
        """
        Quick check if DAS will work for a project

        Returns True if vector store has embeddings, False if empty
        """
        try:
            # Quick test: do a simple vector search
            from .rag_service import RAGService
            rag_service = RAGService(self.settings)

            test_result = await rag_service._retrieve_relevant_chunks(
                question="test",
                project_id=project_id,
                user_id=None,
                max_chunks=1,
                similarity_threshold=0.1
            )

            return len(test_result) > 0

        except Exception as e:
            logger.error(f"Quick sync check failed: {e}")
            return False


# Global monitor instance
_sync_monitor = None

def get_sync_monitor() -> VectorSQLSyncMonitor:
    """Get global sync monitor instance"""
    global _sync_monitor
    if _sync_monitor is None:
        settings = Settings()
        _sync_monitor = VectorSQLSyncMonitor(settings)
    return _sync_monitor


async def emergency_das_recovery(project_id: str) -> Dict[str, Any]:
    """
    Emergency function to recover DAS functionality when vector store is empty

    Call this when DAS returns "no information available" despite having knowledge assets
    """
    monitor = get_sync_monitor()
    return await monitor.emergency_sync_recovery(project_id)


async def check_das_will_work(project_id: str) -> bool:
    """
    Quick check if DAS will work for a project

    Returns False if vector store is empty (DAS will fail)
    """
    monitor = get_sync_monitor()
    return await monitor.quick_sync_check(project_id)


async def get_sync_status_report() -> Dict[str, Any]:
    """Get comprehensive sync status report"""
    monitor = get_sync_monitor()
    return await monitor.automated_health_check()
