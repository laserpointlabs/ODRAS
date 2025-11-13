"""
Unit tests for DASTeamOrchestrator.

Tests team coordination with mocked personas.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from backend.services.das_team_orchestrator import DASTeamOrchestrator
from backend.services.persona_interface import PersonaTask, PersonaResult, PersonaRole, PersonaCapability
from backend.services.team_orchestrator_interface import CoordinationStrategy
from backend.services.config import Settings
from backend.services.das_personas import PersonaFactory


@pytest.fixture
def settings():
    """Create settings instance."""
    return Settings()


@pytest.fixture
def persona_factory(settings):
    """Create persona factory."""
    return PersonaFactory(settings)


@pytest.fixture
def orchestrator(settings, persona_factory):
    """Create team orchestrator."""
    return DASTeamOrchestrator(settings, persona_factory=persona_factory)


@pytest.fixture
def mock_persona():
    """Create mock persona."""
    persona = Mock()
    persona.get_name.return_value = "Test Persona"
    persona.get_role.return_value = PersonaRole.RESEARCHER
    persona.get_capabilities.return_value = [PersonaCapability.INFORMATION_RETRIEVAL]
    persona.get_description.return_value = "Test description"
    persona.can_handle_task = AsyncMock(return_value=True)
    persona.process_task = AsyncMock(return_value=PersonaResult(
        task_id="task-1",
        result="Persona result",
    ))
    persona.get_status = AsyncMock(return_value={"available": True})
    return persona


class TestDASTeamOrchestrator:
    """Test DASTeamOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_add_persona(self, orchestrator, mock_persona):
        """Test adding a persona to team."""
        added = await orchestrator.add_persona(mock_persona)
        
        assert added is True
        
        members = await orchestrator.get_team_members()
        assert len(members) == 1
        assert members[0]["name"] == "Test Persona"
    
    @pytest.mark.asyncio
    async def test_remove_persona(self, orchestrator, mock_persona):
        """Test removing a persona from team."""
        await orchestrator.add_persona(mock_persona)
        
        removed = await orchestrator.remove_persona("Test Persona")
        
        assert removed is True
        
        members = await orchestrator.get_team_members()
        assert len(members) == 0
    
    @pytest.mark.asyncio
    async def test_get_team_status(self, orchestrator, mock_persona):
        """Test getting team status."""
        await orchestrator.add_persona(mock_persona)
        
        status = await orchestrator.get_team_status()
        
        assert status["persona_count"] == 1
        assert "coordination_strategy" in status
    
    @pytest.mark.asyncio
    async def test_coordinate_task_moderator(self, orchestrator, mock_persona):
        """Test coordinating task with moderator strategy."""
        await orchestrator.add_persona(mock_persona)
        
        task = PersonaTask(
            task_id="task-1",
            description="Coordinate this task",
            context={},
        )
        
        result = await orchestrator.coordinate_task(task)
        
        assert result.task_id == "task-1"
        assert result.result is not None
    
    @pytest.mark.asyncio
    async def test_coordinate_task_parallel(self, orchestrator, mock_persona):
        """Test coordinating task with parallel strategy."""
        await orchestrator.add_persona(mock_persona)
        orchestrator._coordination_strategy = CoordinationStrategy.PARALLEL
        
        task = PersonaTask(
            task_id="task-1",
            description="Process in parallel",
            context={},
        )
        
        result = await orchestrator.coordinate_task(task)
        
        assert result.task_id == "task-1"
        assert len(result.persona_results) >= 0
    
    @pytest.mark.asyncio
    async def test_coordinate_task_sequential(self, orchestrator, mock_persona):
        """Test coordinating task with sequential strategy."""
        await orchestrator.add_persona(mock_persona)
        orchestrator._coordination_strategy = CoordinationStrategy.SEQUENTIAL
        
        task = PersonaTask(
            task_id="task-1",
            description="Process sequentially",
            context={},
        )
        
        result = await orchestrator.coordinate_task(task)
        
        assert result.task_id == "task-1"
        assert result.result is not None
    
    @pytest.mark.asyncio
    async def test_load_team_config(self, orchestrator):
        """Test loading team configuration from database."""
        # Mock database query
        with patch.object(orchestrator.db_service, '_conn') as mock_conn:
            mock_cursor = Mock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchone.return_value = None  # Team not found
            
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            loaded = await orchestrator.load_team_config("nonexistent-team")
            
            assert loaded is False
    
    def test_get_coordination_strategy(self, orchestrator):
        """Test getting coordination strategy."""
        strategy = orchestrator.get_coordination_strategy()
        
        assert isinstance(strategy, CoordinationStrategy)
        assert strategy == CoordinationStrategy.MODERATOR
