"""
Knowledge Review Worker

Proactive worker that periodically reviews knowledge by domain, identifies
unused/low-quality chunks, and suggests knowledge improvements to admins.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from ..services.proactive_workers import BaseProactiveWorker
from ..services.config import Settings
from ..services.db import DatabaseService

logger = logging.getLogger(__name__)


class KnowledgeReviewWorker(BaseProactiveWorker):
    """
    Worker that reviews knowledge quality and usage patterns.
    
    Reviews knowledge by domain:
    - Identifies unused/low-quality chunks
    - Detects knowledge gaps
    - Suggests improvements to admins
    - Tracks knowledge usage patterns
    """
    
    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        """Initialize knowledge review worker."""
        super().__init__(settings, db_service)
        self.db_service = db_service or DatabaseService(settings)
        
        # Review thresholds
        self.unused_threshold_days = 90  # Chunks not accessed in 90 days
        self.low_quality_threshold_score = 0.3  # Low similarity scores
        self.min_access_count = 3  # Minimum access count to be considered "used"
    
    @property
    def worker_name(self) -> str:
        return "knowledge-review-worker"
    
    @property
    def worker_type(self) -> str:
        return "review"
    
    @property
    def schedule_interval(self) -> Optional[int]:
        return 86400  # Run daily (24 hours)
    
    @property
    def subscribed_events(self) -> List[str]:
        return [
            "knowledge.chunk.accessed",
            "knowledge.chunk.created",
            "knowledge.chunk.updated",
            "knowledge.asset.uploaded",
        ]
    
    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle knowledge-related events.
        
        Tracks knowledge access patterns for review.
        """
        event_type = event.get("type") or event.get("event_type")
        
        if event_type == "knowledge.chunk.accessed":
            await self._track_chunk_access(event.get("payload", {}))
        elif event_type == "knowledge.chunk.created":
            await self._track_chunk_creation(event.get("payload", {}))
        elif event_type == "knowledge.asset.uploaded":
            await self._track_asset_upload(event.get("payload", {}))
    
    async def _execute_scheduled_task(self) -> Optional[Dict[str, Any]]:
        """
        Execute scheduled knowledge review.
        
        Reviews knowledge by domain and generates recommendations.
        """
        logger.info(f"{self.worker_name} starting scheduled review")
        
        try:
            # Review by domain
            review_results = await self._review_by_domain()
            
            # Identify unused chunks
            unused_chunks = await self._identify_unused_chunks()
            
            # Identify low-quality chunks
            low_quality_chunks = await self._identify_low_quality_chunks()
            
            # Detect knowledge gaps
            knowledge_gaps = await self._detect_knowledge_gaps()
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                unused_chunks=unused_chunks,
                low_quality_chunks=low_quality_chunks,
                knowledge_gaps=knowledge_gaps,
                review_results=review_results,
            )
            
            # Store recommendations for admin review
            await self._store_recommendations(recommendations)
            
            result = {
                "reviewed_domains": len(review_results),
                "unused_chunks": len(unused_chunks),
                "low_quality_chunks": len(low_quality_chunks),
                "knowledge_gaps": len(knowledge_gaps),
                "recommendations": len(recommendations),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Update metrics
            self._status.metrics.update({
                "last_review": datetime.now(timezone.utc).isoformat(),
                "total_reviewed": sum(len(r.get("chunks", [])) for r in review_results.values()),
                "unused_count": len(unused_chunks),
                "low_quality_count": len(low_quality_chunks),
            })
            
            logger.info(f"{self.worker_name} review complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"{self.worker_name} review failed: {e}")
            raise
    
    async def _review_by_domain(self) -> Dict[str, Dict[str, Any]]:
        """
        Review knowledge chunks by domain.
        
        Returns:
            Dictionary mapping domain to review results
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get chunk statistics by domain
                cur.execute("""
                    SELECT 
                        domain,
                        knowledge_type,
                        COUNT(*) as chunk_count,
                        AVG(token_count) as avg_tokens,
                        MIN(created_at) as oldest_chunk,
                        MAX(created_at) as newest_chunk
                    FROM das_knowledge_chunks
                    WHERE domain IS NOT NULL
                    GROUP BY domain, knowledge_type
                    ORDER BY domain, knowledge_type
                """)
                
                rows = cur.fetchall()
                review_results = {}
                
                for row in rows:
                    domain, knowledge_type, chunk_count, avg_tokens, oldest, newest = row
                    key = f"{domain}:{knowledge_type}"
                    
                    review_results[key] = {
                        "domain": domain,
                        "knowledge_type": knowledge_type,
                        "chunk_count": chunk_count,
                        "avg_tokens": float(avg_tokens) if avg_tokens else 0,
                        "oldest_chunk": oldest.isoformat() if oldest else None,
                        "newest_chunk": newest.isoformat() if newest else None,
                    }
                
                return review_results
        finally:
            self.db_service._return(conn)
    
    async def _identify_unused_chunks(self) -> List[Dict[str, Any]]:
        """
        Identify chunks that haven't been accessed recently.
        
        Returns:
            List of unused chunk dictionaries
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Find chunks created more than threshold days ago
                # that haven't been accessed (we'll track access in future)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.unused_threshold_days)
                
                cur.execute("""
                    SELECT 
                        chunk_id,
                        domain,
                        knowledge_type,
                        created_at,
                        token_count,
                        metadata->>'title' as title
                    FROM das_knowledge_chunks
                    WHERE created_at < %s
                    AND (metadata->>'access_count' IS NULL 
                         OR (metadata->>'access_count')::int < %s)
                    ORDER BY created_at ASC
                    LIMIT 100
                """, (cutoff_date, self.min_access_count))
                
                rows = cur.fetchall()
                unused_chunks = []
                
                for row in rows:
                    chunk_id, domain, knowledge_type, created_at, token_count, title = row
                    unused_chunks.append({
                        "chunk_id": str(chunk_id),
                        "domain": domain,
                        "knowledge_type": knowledge_type,
                        "created_at": created_at.isoformat() if created_at else None,
                        "token_count": token_count,
                        "title": title,
                        "days_since_creation": (datetime.now(timezone.utc) - created_at).days if created_at else None,
                    })
                
                return unused_chunks
        finally:
            self.db_service._return(conn)
    
    async def _identify_low_quality_chunks(self) -> List[Dict[str, Any]]:
        """
        Identify chunks that may be low quality.
        
        Criteria:
        - Very short chunks (< 50 tokens)
        - Very long chunks (> 2000 tokens)
        - Chunks with low similarity scores in past queries
        
        Returns:
            List of low-quality chunk dictionaries
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Find chunks that are too short or too long
                cur.execute("""
                    SELECT 
                        chunk_id,
                        domain,
                        knowledge_type,
                        token_count,
                        LENGTH(content) as content_length,
                        metadata->>'title' as title
                    FROM das_knowledge_chunks
                    WHERE token_count < 50 OR token_count > 2000
                    ORDER BY token_count ASC
                    LIMIT 100
                """)
                
                rows = cur.fetchall()
                low_quality_chunks = []
                
                for row in rows:
                    chunk_id, domain, knowledge_type, token_count, content_length, title = row
                    quality_issue = "too_short" if token_count < 50 else "too_long"
                    
                    low_quality_chunks.append({
                        "chunk_id": str(chunk_id),
                        "domain": domain,
                        "knowledge_type": knowledge_type,
                        "token_count": token_count,
                        "content_length": content_length,
                        "title": title,
                        "quality_issue": quality_issue,
                    })
                
                return low_quality_chunks
        finally:
            self.db_service._return(conn)
    
    async def _detect_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        Detect potential knowledge gaps by analyzing domain coverage.
        
        Returns:
            List of knowledge gap dictionaries
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get domain coverage statistics
                cur.execute("""
                    SELECT 
                        domain,
                        knowledge_type,
                        COUNT(*) as chunk_count,
                        COUNT(DISTINCT project_id) as project_count
                    FROM das_knowledge_chunks
                    WHERE domain IS NOT NULL
                    GROUP BY domain, knowledge_type
                    HAVING COUNT(*) < 10
                    ORDER BY chunk_count ASC
                """)
                
                rows = cur.fetchall()
                knowledge_gaps = []
                
                for row in rows:
                    domain, knowledge_type, chunk_count, project_count = row
                    knowledge_gaps.append({
                        "domain": domain,
                        "knowledge_type": knowledge_type,
                        "chunk_count": chunk_count,
                        "project_count": project_count,
                        "gap_reason": "insufficient_coverage",
                    })
                
                return knowledge_gaps
        finally:
            self.db_service._return(conn)
    
    async def _generate_recommendations(
        self,
        unused_chunks: List[Dict[str, Any]],
        low_quality_chunks: List[Dict[str, Any]],
        knowledge_gaps: List[Dict[str, Any]],
        review_results: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on review findings.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Recommendations for unused chunks
        if unused_chunks:
            recommendations.append({
                "type": "unused_chunks",
                "priority": "medium",
                "title": f"Review {len(unused_chunks)} unused knowledge chunks",
                "description": f"Found {len(unused_chunks)} chunks that haven't been accessed recently. Consider archiving or updating them.",
                "action": "review_unused",
                "affected_chunks": len(unused_chunks),
                "domains": list(set(c.get("domain") for c in unused_chunks if c.get("domain"))),
            })
        
        # Recommendations for low-quality chunks
        if low_quality_chunks:
            recommendations.append({
                "type": "low_quality_chunks",
                "priority": "high",
                "title": f"Improve {len(low_quality_chunks)} low-quality knowledge chunks",
                "description": f"Found {len(low_quality_chunks)} chunks with quality issues (too short or too long). Consider splitting or merging them.",
                "action": "improve_quality",
                "affected_chunks": len(low_quality_chunks),
                "domains": list(set(c.get("domain") for c in low_quality_chunks if c.get("domain"))),
            })
        
        # Recommendations for knowledge gaps
        if knowledge_gaps:
            recommendations.append({
                "type": "knowledge_gaps",
                "priority": "high",
                "title": f"Fill {len(knowledge_gaps)} knowledge gaps",
                "description": f"Found {len(knowledge_gaps)} domains with insufficient knowledge coverage. Consider adding more training data.",
                "action": "add_knowledge",
                "affected_domains": [g.get("domain") for g in knowledge_gaps],
            })
        
        return recommendations
    
    async def _store_recommendations(self, recommendations: List[Dict[str, Any]]) -> None:
        """
        Store recommendations for admin review.
        
        In future, this could store in a recommendations table or send notifications.
        """
        if not recommendations:
            return
        
        logger.info(f"{self.worker_name} storing {len(recommendations)} recommendations")
        
        # For now, just log recommendations
        # In future, store in database table or send to admin dashboard
        for rec in recommendations:
            logger.info(f"Recommendation: {rec.get('title')} (Priority: {rec.get('priority')})")
    
    async def _track_chunk_access(self, payload: Dict[str, Any]) -> None:
        """Track when a chunk is accessed."""
        chunk_id = payload.get("chunk_id")
        if not chunk_id:
            return
        
        # Update access count in metadata
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get current metadata
                cur.execute("""
                    SELECT metadata FROM das_knowledge_chunks WHERE chunk_id = %s
                """, (chunk_id,))
                row = cur.fetchone()
                
                if row and row[0]:
                    metadata = row[0] if isinstance(row[0], dict) else {}
                    access_count = metadata.get("access_count", 0) + 1
                    metadata["access_count"] = access_count
                    metadata["last_accessed"] = datetime.now(timezone.utc).isoformat()
                    
                    # Update metadata (convert dict to JSON string for psycopg2)
                    cur.execute("""
                        UPDATE das_knowledge_chunks
                        SET metadata = %s::jsonb
                        WHERE chunk_id = %s
                    """, (json.dumps(metadata), chunk_id))
                    conn.commit()
        finally:
            self.db_service._return(conn)
    
    async def _track_chunk_creation(self, payload: Dict[str, Any]) -> None:
        """Track when a chunk is created."""
        # Could track creation patterns for analysis
        pass
    
    async def _track_asset_upload(self, payload: Dict[str, Any]) -> None:
        """Track when an asset is uploaded."""
        # Could trigger immediate review of new knowledge
        pass
