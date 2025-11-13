"""
User Activity Monitor Worker

Proactive worker that monitors user work patterns, detects when users struggle
(repeated queries, long sessions), and proactively suggests help or knowledge.
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


class UserActivityWorker(BaseProactiveWorker):
    """
    Worker that monitors user activity patterns.
    
    Monitors:
    - User work patterns and session duration
    - Repeated queries (indicating struggle)
    - Long sessions (indicating complexity)
    - Query patterns and success rates
    - Proactively suggests help or knowledge
    """
    
    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        """Initialize user activity worker."""
        super().__init__(settings, db_service)
        self.db_service = db_service or DatabaseService(settings)
        
        # Activity thresholds
        self.repeated_query_threshold = 3  # Same query 3+ times
        self.long_session_threshold_minutes = 60  # Session > 60 minutes
        self.struggle_query_threshold = 5  # 5+ queries in short time indicates struggle
        self.struggle_time_window_minutes = 15  # Within 15 minutes
        
        # Track user sessions
        self._user_sessions: Dict[str, Dict[str, Any]] = {}
    
    @property
    def worker_name(self) -> str:
        return "user-activity-worker"
    
    @property
    def worker_type(self) -> str:
        return "monitor"
    
    @property
    def schedule_interval(self) -> Optional[int]:
        return 300  # Run every 5 minutes
    
    @property
    def subscribed_events(self) -> List[str]:
        return [
            "user.query",
            "user.session.start",
            "user.session.end",
            "das.response.generated",
            "user.action",
        ]
    
    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle user activity events.
        
        Tracks user patterns and detects struggling users.
        """
        event_type = event.get("type") or event.get("event_type")
        payload = event.get("payload", {})
        user_id = payload.get("user_id") or payload.get("user")
        
        if not user_id:
            return
        
        if event_type == "user.query":
            await self._track_user_query(user_id, payload)
        elif event_type == "user.session.start":
            await self._track_session_start(user_id, payload)
        elif event_type == "user.session.end":
            await self._track_session_end(user_id, payload)
        elif event_type == "das.response.generated":
            await self._track_das_response(user_id, payload)
        elif event_type == "user.action":
            await self._track_user_action(user_id, payload)
    
    async def _execute_scheduled_task(self) -> Optional[Dict[str, Any]]:
        """
        Execute scheduled user activity analysis.
        
        Analyzes user patterns and generates proactive assistance.
        """
        logger.info(f"{self.worker_name} starting scheduled analysis")
        
        try:
            # Analyze active sessions
            active_sessions = await self._analyze_active_sessions()
            
            # Detect struggling users
            struggling_users = await self._detect_struggling_users()
            
            # Analyze query patterns
            query_patterns = await self._analyze_query_patterns()
            
            # Generate proactive assistance
            assistance = await self._generate_proactive_assistance(
                struggling_users=struggling_users,
                active_sessions=active_sessions,
                query_patterns=query_patterns,
            )
            
            # Store assistance recommendations
            await self._store_assistance_recommendations(assistance)
            
            result = {
                "active_sessions": len(active_sessions),
                "struggling_users": len(struggling_users),
                "query_patterns_analyzed": len(query_patterns),
                "assistance_recommendations": len(assistance),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Update metrics
            self._status.metrics.update({
                "last_analysis": datetime.now(timezone.utc).isoformat(),
                "active_sessions_count": len(active_sessions),
                "struggling_users_count": len(struggling_users),
            })
            
            logger.info(f"{self.worker_name} analysis complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"{self.worker_name} analysis failed: {e}")
            raise
    
    async def _track_user_query(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Track user query."""
        query_text = payload.get("query") or payload.get("question", "")
        project_id = payload.get("project_id")
        
        # Update session tracking
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = {
                "start_time": datetime.now(timezone.utc),
                "queries": [],
                "project_id": project_id,
            }
        
        session = self._user_sessions[user_id]
        session["queries"].append({
            "query": query_text,
            "timestamp": datetime.now(timezone.utc),
            "project_id": project_id,
        })
        session["last_activity"] = datetime.now(timezone.utc)
        
        # Store query in database for analysis
        await self._store_user_query(user_id, query_text, project_id)
    
    async def _track_session_start(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Track session start."""
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = {
                "start_time": datetime.now(timezone.utc),
                "queries": [],
                "project_id": payload.get("project_id"),
            }
    
    async def _track_session_end(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Track session end."""
        if user_id in self._user_sessions:
            session = self._user_sessions[user_id]
            session["end_time"] = datetime.now(timezone.utc)
            session["duration_minutes"] = (
                (session["end_time"] - session["start_time"]).total_seconds() / 60
            )
            
            # Store session summary
            await self._store_session_summary(user_id, session)
            
            # Remove from active sessions
            del self._user_sessions[user_id]
    
    async def _track_das_response(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Track DAS response generation."""
        success = payload.get("success", True)
        response_length = len(payload.get("response", ""))
        
        if user_id in self._user_sessions:
            session = self._user_sessions[user_id]
            if session["queries"]:
                session["queries"][-1]["response_success"] = success
                session["queries"][-1]["response_length"] = response_length
    
    async def _track_user_action(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Track user actions."""
        action_type = payload.get("action_type")
        
        if user_id in self._user_sessions:
            session = self._user_sessions[user_id]
            session["last_activity"] = datetime.now(timezone.utc)
            if "actions" not in session:
                session["actions"] = []
            session["actions"].append({
                "type": action_type,
                "timestamp": datetime.now(timezone.utc),
            })
    
    async def _analyze_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Analyze currently active user sessions.
        
        Returns:
            List of active session dictionaries
        """
        active_sessions = []
        now = datetime.now(timezone.utc)
        
        for user_id, session in self._user_sessions.items():
            duration_minutes = (now - session["start_time"]).total_seconds() / 60
            
            active_sessions.append({
                "user_id": user_id,
                "duration_minutes": duration_minutes,
                "query_count": len(session.get("queries", [])),
                "project_id": session.get("project_id"),
                "is_long_session": duration_minutes > self.long_session_threshold_minutes,
            })
        
        return active_sessions
    
    async def _detect_struggling_users(self) -> List[Dict[str, Any]]:
        """
        Detect users who may be struggling.
        
        Criteria:
        - Repeated queries (same query multiple times)
        - Many queries in short time
        - Long sessions with many queries
        - Low success rate on DAS responses
        """
        struggling_users = []
        
        # Check in-memory sessions
        for user_id, session in self._user_sessions.items():
            queries = session.get("queries", [])
            if len(queries) < 2:
                continue
            
            # Check for repeated queries
            query_texts = [q.get("query", "") for q in queries]
            query_counts = defaultdict(int)
            for query_text in query_texts:
                query_counts[query_text.lower().strip()] += 1
            
            repeated_queries = [
                q for q, count in query_counts.items()
                if count >= self.repeated_query_threshold
            ]
            
            # Check for many queries in short time
            if len(queries) >= self.struggle_query_threshold:
                recent_queries = [
                    q for q in queries
                    if (datetime.now(timezone.utc) - q["timestamp"]).total_seconds() / 60
                    < self.struggle_time_window_minutes
                ]
                many_recent_queries = len(recent_queries) >= self.struggle_query_threshold
            else:
                many_recent_queries = False
            
            # Check session duration
            duration_minutes = (
                (datetime.now(timezone.utc) - session["start_time"]).total_seconds() / 60
            )
            long_session = duration_minutes > self.long_session_threshold_minutes
            
            # Check success rate
            successful_responses = sum(
                1 for q in queries
                if q.get("response_success", True)
            )
            success_rate = successful_responses / len(queries) if queries else 1.0
            
            if repeated_queries or many_recent_queries or (long_session and len(queries) > 10) or success_rate < 0.5:
                struggling_users.append({
                    "user_id": user_id,
                    "reasons": [],
                    "repeated_queries": repeated_queries,
                    "query_count": len(queries),
                    "duration_minutes": duration_minutes,
                    "success_rate": success_rate,
                    "project_id": session.get("project_id"),
                })
                
                if repeated_queries:
                    struggling_users[-1]["reasons"].append("repeated_queries")
                if many_recent_queries:
                    struggling_users[-1]["reasons"].append("many_recent_queries")
                if long_session:
                    struggling_users[-1]["reasons"].append("long_session")
                if success_rate < 0.5:
                    struggling_users[-1]["reasons"].append("low_success_rate")
        
        # Also check database for historical patterns
        db_struggling = await self._detect_struggling_users_from_db()
        struggling_users.extend(db_struggling)
        
        return struggling_users
    
    async def _detect_struggling_users_from_db(self) -> List[Dict[str, Any]]:
        """Detect struggling users from database history."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Find users with many queries in recent time window
                time_window = datetime.now(timezone.utc) - timedelta(minutes=self.struggle_time_window_minutes)
                
                # Query user activity from project_threads or conversations table
                # Try project_threads first, fallback to checking if table exists
                try:
                    cur.execute("""
                        SELECT 
                            user_id,
                            COUNT(*) as query_count,
                            COUNT(DISTINCT project_id) as project_count
                        FROM project_threads
                        WHERE created_at > %s
                        GROUP BY user_id
                        HAVING COUNT(*) >= %s
                    """, (time_window, self.struggle_query_threshold))
                except Exception:
                    # Table might not exist or have different name
                    # Return empty list if we can't query
                    return []
                
                rows = cur.fetchall()
                struggling_users = []
                
                for row in rows:
                    user_id, query_count, project_count = row
                    struggling_users.append({
                        "user_id": str(user_id),
                        "reasons": ["many_recent_queries"],
                        "query_count": query_count,
                        "project_count": project_count,
                    })
                
                return struggling_users
        finally:
            self.db_service._return(conn)
    
    async def _analyze_query_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze query patterns across users.
        
        Returns:
            List of query pattern dictionaries
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get common query patterns from project_threads or conversations
                try:
                    cur.execute("""
                        SELECT 
                            LOWER(TRIM(message_text)) as normalized_query,
                            COUNT(*) as query_count,
                            COUNT(DISTINCT user_id) as user_count
                        FROM project_threads
                        WHERE message_text IS NOT NULL
                        AND created_at > NOW() - INTERVAL '7 days'
                        GROUP BY LOWER(TRIM(message_text))
                        HAVING COUNT(*) >= 3
                        ORDER BY query_count DESC
                        LIMIT 20
                    """)
                except Exception:
                    # Table might not exist or have different name
                    # Return empty list if we can't query
                    return []
                
                rows = cur.fetchall()
                patterns = []
                
                for row in rows:
                    normalized_query, query_count, user_count = row
                    patterns.append({
                        "query_pattern": normalized_query,
                        "query_count": query_count,
                        "user_count": user_count,
                        "frequency": "high" if query_count >= 10 else "medium",
                    })
                
                return patterns
        finally:
            self.db_service._return(conn)
    
    async def _generate_proactive_assistance(
        self,
        struggling_users: List[Dict[str, Any]],
        active_sessions: List[Dict[str, Any]],
        query_patterns: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate proactive assistance recommendations.
        
        Returns:
            List of assistance recommendation dictionaries
        """
        assistance = []
        
        # Assistance for struggling users
        for user in struggling_users:
            user_id = user["user_id"]
            reasons = user.get("reasons", [])
            
            if "repeated_queries" in reasons:
                assistance.append({
                    "type": "repeated_query_help",
                    "user_id": user_id,
                    "priority": "high",
                    "title": "You've asked similar questions multiple times",
                    "message": "It looks like you're looking for information on a specific topic. Would you like me to help you find comprehensive information or suggest relevant knowledge?",
                    "suggested_action": "provide_comprehensive_answer",
                    "project_id": user.get("project_id"),
                })
            
            if "many_recent_queries" in reasons:
                assistance.append({
                    "type": "many_queries_help",
                    "user_id": user_id,
                    "priority": "medium",
                    "title": "You've asked several questions recently",
                    "message": "I notice you've been asking many questions. Would you like me to help you find training materials or documentation that might answer multiple questions at once?",
                    "suggested_action": "suggest_training_materials",
                    "project_id": user.get("project_id"),
                })
            
            if "long_session" in reasons:
                assistance.append({
                    "type": "long_session_help",
                    "user_id": user_id,
                    "priority": "low",
                    "title": "You've been working for a while",
                    "message": "You've been working for over an hour. Would you like to take a break or save your progress?",
                    "suggested_action": "suggest_break",
                    "project_id": user.get("project_id"),
                })
        
        # Assistance for common query patterns
        for pattern in query_patterns:
            if pattern["frequency"] == "high":
                assistance.append({
                    "type": "common_query_knowledge",
                    "priority": "medium",
                    "title": f"Common question: '{pattern['query_pattern'][:50]}...'",
                    "message": f"This question has been asked {pattern['query_count']} times by {pattern['user_count']} users. Consider adding this to the knowledge base.",
                    "suggested_action": "add_to_knowledge_base",
                    "query_pattern": pattern["query_pattern"],
                })
        
        return assistance
    
    async def _store_assistance_recommendations(self, assistance: List[Dict[str, Any]]) -> None:
        """
        Store assistance recommendations for users.
        
        In future, this could send notifications or store in a recommendations table.
        """
        if not assistance:
            return
        
        logger.info(f"{self.worker_name} storing {len(assistance)} assistance recommendations")
        
        # For now, just log recommendations
        # In future, send to user dashboard or notification system
        for rec in assistance:
            logger.info(f"Assistance: {rec.get('title')} for user {rec.get('user_id', 'all')}")
    
    async def _store_user_query(self, user_id: str, query_text: str, project_id: Optional[str]) -> None:
        """Store user query in database for analysis."""
        # Queries are already stored in project_threads table
        # This method could add additional tracking if needed
        pass
    
    async def _store_session_summary(self, user_id: str, session: Dict[str, Any]) -> None:
        """Store session summary in database."""
        # Could store in a user_sessions table for historical analysis
        pass
