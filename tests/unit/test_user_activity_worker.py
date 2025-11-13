"""
Unit tests for UserActivityWorker.

Tests user activity monitoring logic with mocked data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from backend.workers.user_activity_worker import UserActivityWorker
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def mock_db_service():
    """Create mock database service."""
    db = Mock(spec=DatabaseService)
    db._conn = Mock()
    db._return = Mock()
    return db


@pytest.fixture
def worker(mock_db_service):
    """Create UserActivityWorker instance."""
    settings = Settings()
    return UserActivityWorker(settings, db_service=mock_db_service)


class TestUserActivityWorker:
    """Test UserActivityWorker."""
    
    def test_worker_properties(self, worker):
        """Test worker properties."""
        assert worker.worker_name == "user-activity-worker"
        assert worker.worker_type == "monitor"
        assert worker.schedule_interval == 300  # 5 minutes
        assert "user.query" in worker.subscribed_events
    
    @pytest.mark.asyncio
    async def test_track_user_query(self, worker):
        """Test tracking user query."""
        event = {
            "type": "user.query",
            "payload": {
                "user_id": "test-user",
                "query": "What is ontology?",
                "project_id": "test-project",
            },
        }
        
        await worker._handle_event(event)
        
        assert "test-user" in worker._user_sessions
        session = worker._user_sessions["test-user"]
        assert len(session["queries"]) == 1
        assert session["queries"][0]["query"] == "What is ontology?"
    
    @pytest.mark.asyncio
    async def test_track_repeated_queries(self, worker):
        """Test detecting repeated queries."""
        # Mock database call
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        worker.db_service._conn.return_value = mock_conn
        
        user_id = "test-user"
        
        # Add same query multiple times
        for i in range(4):
            event = {
                "type": "user.query",
                "payload": {
                    "user_id": user_id,
                    "query": "What is ontology?",
                },
            }
            await worker._handle_event(event)
        
        struggling = await worker._detect_struggling_users()
        
        assert len(struggling) >= 1
        struggling_user = next((u for u in struggling if u["user_id"] == user_id), None)
        assert struggling_user is not None
        assert "repeated_queries" in struggling_user["reasons"]
    
    @pytest.mark.asyncio
    async def test_track_many_recent_queries(self, worker):
        """Test detecting many queries in short time."""
        # Mock database call
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        worker.db_service._conn.return_value = mock_conn
        
        user_id = "test-user"
        
        # Add many queries quickly
        for i in range(6):
            event = {
                "type": "user.query",
                "payload": {
                    "user_id": user_id,
                    "query": f"Question {i}",
                },
            }
            await worker._handle_event(event)
        
        struggling = await worker._detect_struggling_users()
        
        assert len(struggling) >= 1
        struggling_user = next((u for u in struggling if u["user_id"] == user_id), None)
        assert struggling_user is not None
        assert "many_recent_queries" in struggling_user["reasons"]
    
    @pytest.mark.asyncio
    async def test_track_long_session(self, worker):
        """Test detecting long sessions."""
        user_id = "test-user"
        
        # Start session
        event = {
            "type": "user.session.start",
            "payload": {"user_id": user_id},
        }
        await worker._handle_event(event)
        
        # Simulate long session by setting start time in the past
        worker._user_sessions[user_id]["start_time"] = datetime.now(timezone.utc) - timedelta(minutes=70)
        
        # Add some queries
        for i in range(5):
            query_event = {
                "type": "user.query",
                "payload": {
                    "user_id": user_id,
                    "query": f"Question {i}",
                },
            }
            await worker._handle_event(query_event)
        
        active_sessions = await worker._analyze_active_sessions()
        
        assert len(active_sessions) == 1
        assert active_sessions[0]["is_long_session"] is True
    
    @pytest.mark.asyncio
    async def test_generate_proactive_assistance(self, worker):
        """Test generating proactive assistance."""
        struggling_users = [
            {
                "user_id": "user-1",
                "reasons": ["repeated_queries", "many_recent_queries"],
                "project_id": "project-1",
            },
            {
                "user_id": "user-2",
                "reasons": ["long_session"],
                "project_id": "project-2",
            },
        ]
        
        active_sessions = []
        query_patterns = [
            {
                "query_pattern": "what is ontology",
                "query_count": 15,
                "user_count": 5,
                "frequency": "high",
            },
        ]
        
        assistance = await worker._generate_proactive_assistance(
            struggling_users=struggling_users,
            active_sessions=active_sessions,
            query_patterns=query_patterns,
        )
        
        assert len(assistance) >= 3  # At least 3 assistance items
        
        # Check for repeated query help
        repeated_help = next(
            (a for a in assistance if a["type"] == "repeated_query_help"),
            None
        )
        assert repeated_help is not None
        assert repeated_help["user_id"] == "user-1"
        
        # Check for many queries help
        many_queries_help = next(
            (a for a in assistance if a["type"] == "many_queries_help"),
            None
        )
        assert many_queries_help is not None
        
        # Check for common query knowledge
        common_query_help = next(
            (a for a in assistance if a["type"] == "common_query_knowledge"),
            None
        )
        assert common_query_help is not None
    
    @pytest.mark.asyncio
    async def test_execute_scheduled_task(self, worker):
        """Test executing scheduled analysis task."""
        # Mock analysis methods
        with patch.object(worker, '_analyze_active_sessions', new_callable=AsyncMock) as mock_active, \
             patch.object(worker, '_detect_struggling_users', new_callable=AsyncMock) as mock_struggling, \
             patch.object(worker, '_analyze_query_patterns', new_callable=AsyncMock) as mock_patterns, \
             patch.object(worker, '_generate_proactive_assistance', new_callable=AsyncMock) as mock_assistance, \
             patch.object(worker, '_store_assistance_recommendations', new_callable=AsyncMock) as mock_store:
            
            mock_active.return_value = []
            mock_struggling.return_value = []
            mock_patterns.return_value = []
            mock_assistance.return_value = []
            
            result = await worker._execute_scheduled_task()
            
            assert result is not None
            assert "active_sessions" in result
            assert "struggling_users" in result
            assert "query_patterns_analyzed" in result
            assert "assistance_recommendations" in result
            
            # Verify all methods were called
            mock_active.assert_called_once()
            mock_struggling.assert_called_once()
            mock_patterns.assert_called_once()
            mock_assistance.assert_called_once()
            mock_store.assert_called_once()
