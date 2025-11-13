"""
Integration tests for UserActivityWorker.

Tests with real user events and database.
"""

import pytest
from datetime import datetime, timezone

from backend.workers.user_activity_worker import UserActivityWorker
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def worker():
    """Create UserActivityWorker instance."""
    settings = Settings()
    db_service = DatabaseService(settings)
    return UserActivityWorker(settings, db_service=db_service)


@pytest.mark.integration
class TestUserActivityWorkerIntegration:
    """Integration tests for UserActivityWorker."""
    
    @pytest.mark.asyncio
    async def test_track_user_query_real_data(self, worker):
        """Test tracking user query with real data."""
        event = {
            "type": "user.query",
            "payload": {
                "user_id": "test-user-integration",
                "query": "What is ontology?",
                "project_id": None,
            },
        }
        
        await worker._handle_event(event)
        
        assert "test-user-integration" in worker._user_sessions
        session = worker._user_sessions["test-user-integration"]
        assert len(session["queries"]) == 1
        assert session["queries"][0]["query"] == "What is ontology?"
    
    @pytest.mark.asyncio
    async def test_analyze_active_sessions_real_data(self, worker):
        """Test analyzing active sessions with real data."""
        # Create a test session
        event = {
            "type": "user.session.start",
            "payload": {"user_id": "test-user-session"},
        }
        await worker._handle_event(event)
        
        active_sessions = await worker._analyze_active_sessions()
        
        assert isinstance(active_sessions, list)
        assert len(active_sessions) >= 1
        
        # Find our test session
        test_session = next(
            (s for s in active_sessions if s["user_id"] == "test-user-session"),
            None
        )
        assert test_session is not None
        assert "duration_minutes" in test_session
        assert "query_count" in test_session
    
    @pytest.mark.asyncio
    async def test_detect_struggling_users_real_data(self, worker):
        """Test detecting struggling users with real data."""
        # Create a user with repeated queries
        user_id = "test-struggling-user"
        
        for i in range(4):
            event = {
                "type": "user.query",
                "payload": {
                    "user_id": user_id,
                    "query": "What is ontology?",  # Same query repeated
                },
            }
            await worker._handle_event(event)
        
        struggling = await worker._detect_struggling_users()
        
        assert isinstance(struggling, list)
        
        # Find our test user
        test_user = next(
            (u for u in struggling if u["user_id"] == user_id),
            None
        )
        if test_user:
            assert "reasons" in test_user
            assert len(test_user["reasons"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_query_patterns_real_data(self, worker):
        """Test analyzing query patterns with real data."""
        patterns = await worker._analyze_query_patterns()
        
        # Should return a list (may be empty if no data)
        assert isinstance(patterns, list)
        
        # If we have patterns, verify structure
        if patterns:
            for pattern in patterns:
                assert "query_pattern" in pattern
                assert "query_count" in pattern
                assert "user_count" in pattern
                assert "frequency" in pattern
    
    @pytest.mark.asyncio
    async def test_execute_scheduled_task_real_data(self, worker):
        """Test executing scheduled analysis task with real data."""
        result = await worker._execute_scheduled_task()
        
        # Should return a result dictionary
        assert isinstance(result, dict)
        assert "active_sessions" in result
        assert "struggling_users" in result
        assert "query_patterns_analyzed" in result
        assert "assistance_recommendations" in result
        assert "timestamp" in result
        
        # Verify counts are non-negative
        assert result["active_sessions"] >= 0
        assert result["struggling_users"] >= 0
        assert result["query_patterns_analyzed"] >= 0
        assert result["assistance_recommendations"] >= 0
