"""
Unit tests for LearningInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from backend.services.learning_interface import (
    LearningInterface,
    InteractionRecord,
    InteractionType,
    FeedbackType,
    LearningInsight,
)


class ConcreteLearningSystem(LearningInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._interactions = {}
        self._insights = {}
    
    async def record_interaction(self, interaction):
        """Record interaction."""
        self._interactions[interaction.interaction_id] = interaction
        return True
    
    async def learn_from_feedback(self, interaction_id, feedback_type, feedback_text=None):
        """Learn from feedback."""
        if interaction_id in self._interactions:
            interaction = self._interactions[interaction_id]
            interaction.feedback = feedback_type
            return True
        return False
    
    async def learn_from_correction(self, interaction_id, correction, corrected_response):
        """Learn from correction."""
        if interaction_id in self._interactions:
            interaction = self._interactions[interaction_id]
            interaction.correction = correction
            return True
        return False
    
    async def get_improvements(self, persona_name=None, domain=None, limit=10):
        """Get improvements."""
        return list(self._insights.values())[:limit]
    
    async def get_interaction_history(self, user_id=None, project_id=None, interaction_type=None, limit=50):
        """Get interaction history."""
        interactions = list(self._interactions.values())
        if user_id:
            interactions = [i for i in interactions if i.user_id == user_id]
        return interactions[:limit]
    
    async def analyze_patterns(self, domain=None, time_period_days=30):
        """Analyze patterns."""
        return {"patterns": []}
    
    async def apply_learning(self, insight_id, persona_name=None):
        """Apply learning."""
        return insight_id in self._insights


class TestLearningInterface:
    """Test LearningInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LearningInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        learning = ConcreteLearningSystem()
        assert isinstance(learning, LearningInterface)
        assert isinstance(learning, ABC)
    
    @pytest.mark.asyncio
    async def test_record_interaction(self):
        """Test recording an interaction."""
        learning = ConcreteLearningSystem()
        
        interaction = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id="project-1",
            query="What is an ontology?",
            response="An ontology is...",
            context={},
        )
        
        recorded = await learning.record_interaction(interaction)
        
        assert recorded is True
    
    @pytest.mark.asyncio
    async def test_learn_from_feedback(self):
        """Test learning from feedback."""
        learning = ConcreteLearningSystem()
        
        interaction = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id=None,
            query="Test",
            response="Response",
            context={},
        )
        
        await learning.record_interaction(interaction)
        learned = await learning.learn_from_feedback(
            "interaction-1",
            FeedbackType.POSITIVE,
        )
        
        assert learned is True
    
    @pytest.mark.asyncio
    async def test_learn_from_correction(self):
        """Test learning from correction."""
        learning = ConcreteLearningSystem()
        
        interaction = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id=None,
            query="Test",
            response="Wrong response",
            context={},
        )
        
        await learning.record_interaction(interaction)
        learned = await learning.learn_from_correction(
            "interaction-1",
            "The correct answer is...",
            "Correct response",
        )
        
        assert learned is True
    
    @pytest.mark.asyncio
    async def test_get_improvements(self):
        """Test getting improvements."""
        learning = ConcreteLearningSystem()
        
        improvements = await learning.get_improvements()
        
        assert isinstance(improvements, list)
    
    @pytest.mark.asyncio
    async def test_get_interaction_history(self):
        """Test getting interaction history."""
        learning = ConcreteLearningSystem()
        
        interaction = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id=None,
            query="Test",
            response="Response",
            context={},
        )
        
        await learning.record_interaction(interaction)
        history = await learning.get_interaction_history(user_id="user-1")
        
        assert len(history) == 1
        assert history[0].interaction_id == "interaction-1"
    
    @pytest.mark.asyncio
    async def test_analyze_patterns(self):
        """Test analyzing patterns."""
        learning = ConcreteLearningSystem()
        
        patterns = await learning.analyze_patterns()
        
        assert isinstance(patterns, dict)
    
    @pytest.mark.asyncio
    async def test_apply_learning(self):
        """Test applying learning."""
        learning = ConcreteLearningSystem()
        
        insight = LearningInsight(
            insight_id="insight-1",
            insight_type="improvement",
            description="Test insight",
            confidence=0.8,
            recommendations=["Do X"],
        )
        learning._insights["insight-1"] = insight
        
        applied = await learning.apply_learning("insight-1")
        
        assert applied is True


class TestInteractionRecord:
    """Test InteractionRecord."""
    
    def test_create_record(self):
        """Test creating an interaction record."""
        record = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.QUERY,
            user_id="user-1",
            project_id="project-1",
            query="Test query",
            response="Test response",
            context={"persona": "Researcher"},
        )
        
        assert record.interaction_id == "interaction-1"
        assert record.interaction_type == InteractionType.QUERY
    
    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        record = InteractionRecord(
            interaction_id="interaction-1",
            interaction_type=InteractionType.FEEDBACK,
            user_id="user-1",
            project_id=None,
            query="Test",
            response="Response",
            context={},
        )
        
        data = record.to_dict()
        assert data["interaction_id"] == "interaction-1"
        assert data["interaction_type"] == "feedback"


class TestLearningInsight:
    """Test LearningInsight."""
    
    def test_create_insight(self):
        """Test creating a learning insight."""
        insight = LearningInsight(
            insight_id="insight-1",
            insight_type="pattern",
            description="Test insight",
            confidence=0.9,
            recommendations=["Recommendation 1"],
        )
        
        assert insight.insight_id == "insight-1"
        assert insight.confidence == 0.9
    
    def test_insight_to_dict(self):
        """Test converting insight to dictionary."""
        insight = LearningInsight(
            insight_id="insight-1",
            insight_type="improvement",
            description="Test",
            confidence=0.8,
            recommendations=[],
        )
        
        data = insight.to_dict()
        assert data["insight_id"] == "insight-1"
        assert data["confidence"] == 0.8
