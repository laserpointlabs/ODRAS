"""
Unit tests for DASLearning.

Tests learning logic and feedback processing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.services.das_learning import DASLearning
from backend.services.learning_interface import (
    InteractionRecord,
    InteractionType,
    FeedbackType,
    LearningInsight,
)
from backend.services.config import Settings


@pytest.fixture
def settings():
    """Create settings instance."""
    return Settings()


@pytest.fixture
def learning_system(settings):
    """Create learning system."""
    return DASLearning(settings)


class TestDASLearning:
    """Test DASLearning."""
    
    @pytest.mark.asyncio
    async def test_record_interaction(self, learning_system):
        """Test recording an interaction."""
        interaction = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id="project-1",
            query="What is an ontology?",
            response="An ontology is...",
            context={"persona": "Researcher"},
        )
        
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            recorded = await learning_system.record_interaction(interaction)
            
            assert recorded is True
    
    @pytest.mark.asyncio
    async def test_learn_from_feedback(self, learning_system):
        """Test learning from feedback."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            mock_cursor.rowcount = 1
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            with patch.object(learning_system, '_generate_insights_from_feedback', new_callable=AsyncMock):
                learned = await learning_system.learn_from_feedback(
                    "interaction-1",
                    FeedbackType.POSITIVE,
                )
                
                assert learned is True
    
    @pytest.mark.asyncio
    async def test_learn_from_correction(self, learning_system):
        """Test learning from correction."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            mock_cursor.rowcount = 1
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            with patch.object(learning_system, '_generate_insights_from_correction', new_callable=AsyncMock):
                learned = await learning_system.learn_from_correction(
                    "interaction-1",
                    "The correct answer is...",
                    "Corrected response",
                )
                
                assert learned is True
    
    @pytest.mark.asyncio
    async def test_get_improvements(self, learning_system):
        """Test getting improvements."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchall.return_value = []
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            improvements = await learning_system.get_improvements()
            
            assert isinstance(improvements, list)
    
    @pytest.mark.asyncio
    async def test_get_interaction_history(self, learning_system):
        """Test getting interaction history."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchall.return_value = []
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            history = await learning_system.get_interaction_history(user_id="user-1")
            
            assert isinstance(history, list)
    
    @pytest.mark.asyncio
    async def test_analyze_patterns(self, learning_system):
        """Test analyzing patterns."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchall.return_value = []
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            patterns = await learning_system.analyze_patterns()
            
            assert isinstance(patterns, dict)
    
    @pytest.mark.asyncio
    async def test_apply_learning(self, learning_system):
        """Test applying learning."""
        with patch.object(learning_system.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute.return_value = None
            mock_cursor.rowcount = 1
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            
            applied = await learning_system.apply_learning("insight-1")
            
            assert applied is True
