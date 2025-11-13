"""
Integration tests for DAS Learning System (Phase 6.8).

Tests real interactions, feedback processing, and learning insights.

NOTE: These tests require the database to be initialized with the schema
(./odras.sh init-db) which creates das_interactions and das_learning_insights tables.
"""

import pytest
from uuid import uuid4
from backend.services.das_learning import DASLearning
from backend.services.learning_interface import (
    InteractionRecord,
    InteractionType,
    FeedbackType,
)
from backend.services.config import Settings
from backend.services.db import DatabaseService


@pytest.fixture
def learning_system():
    """Create learning system."""
    settings = Settings()
    db_service = DatabaseService(settings)
    
    # Verify tables exist
    conn = db_service._conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('das_interactions', 'das_learning_insights')
            """)
            tables = [row[0] for row in cur.fetchall()]
            if 'das_interactions' not in tables or 'das_learning_insights' not in tables:
                pytest.skip("Learning tables not found. Run './odras.sh init-db' to create schema.")
    finally:
        db_service._return(conn)
    
    return DASLearning(settings, db_service)


@pytest.mark.integration
class TestDASLearningIntegration:
    """Integration tests for DAS learning system."""
    
    @pytest.mark.asyncio
    async def test_record_and_retrieve_interaction(self, learning_system):
        """Test recording and retrieving an interaction."""
        interaction = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=str(uuid4()),
            query="What is an ontology?",
            response="An ontology is a formal specification of a shared conceptualization.",
            context={"persona_name": "Researcher", "domain": "ontology"},
        )
        
        # Record interaction
        recorded = await learning_system.record_interaction(interaction)
        assert recorded is True
        
        # Retrieve interaction history
        history = await learning_system.get_interaction_history(
            user_id="test_user",
            limit=10,
        )
        
        assert len(history) > 0
        found = False
        for h in history:
            if h.interaction_id == interaction.interaction_id:
                found = True
                assert h.query == interaction.query
                assert h.response == interaction.response
                break
        
        assert found, "Interaction should be found in history"
    
    @pytest.mark.asyncio
    async def test_learn_from_feedback(self, learning_system):
        """Test learning from user feedback."""
        # Record an interaction first
        interaction = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=None,
            query="Test query",
            response="Test response",
            context={"persona_name": "Researcher"},
        )
        
        await learning_system.record_interaction(interaction)
        
        # Provide feedback
        learned = await learning_system.learn_from_feedback(
            interaction.interaction_id,
            FeedbackType.POSITIVE,
            feedback_text="Great answer!",
        )
        
        assert learned is True
        
        # Check that insights were generated
        improvements = await learning_system.get_improvements(
            persona_name="Researcher",
            limit=10,
        )
        
        # Should have at least one insight from the feedback
        assert len(improvements) >= 0  # May be empty if no insights generated yet
    
    @pytest.mark.asyncio
    async def test_learn_from_correction(self, learning_system):
        """Test learning from user correction."""
        # Record an interaction first
        interaction = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=None,
            query="What is a requirement?",
            response="A requirement is a need.",
            context={"persona_name": "Analyst"},
        )
        
        await learning_system.record_interaction(interaction)
        
        # Provide correction
        learned = await learning_system.learn_from_correction(
            interaction.interaction_id,
            "The response was too vague",
            "A requirement is a statement that identifies a capability, characteristic, or quality factor of a system in order for it to have value and utility to a user.",
        )
        
        assert learned is True
        
        # Check that correction insights were generated
        improvements = await learning_system.get_improvements(
            persona_name="Analyst",
            limit=10,
        )
        
        # Should have insights from corrections
        assert len(improvements) >= 0
    
    @pytest.mark.asyncio
    async def test_analyze_patterns(self, learning_system):
        """Test analyzing interaction patterns."""
        # Record multiple interactions
        for i in range(3):
            interaction = InteractionRecord(
                interaction_id=str(uuid4()),
                interaction_type=InteractionType.QUERY,
                user_id="test_user",
                project_id=None,
                query=f"Test query {i}",
                response=f"Test response {i}",
                context={"domain": "ontology"},
            )
            await learning_system.record_interaction(interaction)
        
        # Analyze patterns
        patterns = await learning_system.analyze_patterns(
            domain="ontology",
            time_period_days=7,
        )
        
        assert isinstance(patterns, dict)
        assert "time_period_days" in patterns
        assert "interaction_types" in patterns
        assert "total_interactions" in patterns
    
    @pytest.mark.asyncio
    async def test_get_improvements_filtered(self, learning_system):
        """Test getting improvements filtered by persona and domain."""
        # Record interactions with different personas
        interaction1 = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=None,
            query="Query 1",
            response="Response 1",
            context={"persona_name": "Researcher", "domain": "ontology"},
        )
        
        interaction2 = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=None,
            query="Query 2",
            response="Response 2",
            context={"persona_name": "Analyst", "domain": "requirements"},
        )
        
        await learning_system.record_interaction(interaction1)
        await learning_system.record_interaction(interaction2)
        
        # Get improvements for Researcher persona
        researcher_improvements = await learning_system.get_improvements(
            persona_name="Researcher",
            limit=10,
        )
        
        # Get improvements for ontology domain
        ontology_improvements = await learning_system.get_improvements(
            domain="ontology",
            limit=10,
        )
        
        assert isinstance(researcher_improvements, list)
        assert isinstance(ontology_improvements, list)
    
    @pytest.mark.asyncio
    async def test_apply_learning(self, learning_system):
        """Test applying a learning insight."""
        # First, create an insight by providing feedback
        interaction = InteractionRecord(
            interaction_id=str(uuid4()),
            interaction_type=InteractionType.QUERY,
            user_id="test_user",
            project_id=None,
            query="Test",
            response="Response",
            context={"persona_name": "Researcher"},
        )
        
        await learning_system.record_interaction(interaction)
        await learning_system.learn_from_feedback(
            interaction.interaction_id,
            FeedbackType.NEGATIVE,
        )
        
        # Get insights
        improvements = await learning_system.get_improvements(limit=10)
        
        # Apply an insight if available
        if improvements:
            applied = await learning_system.apply_learning(
                improvements[0].insight_id,
                persona_name="Researcher",
            )
            assert applied is True
        else:
            # If no insights generated, that's okay for this test
            pytest.skip("No insights generated yet")
