"""
Unit tests for TeamOrchestratorInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from unittest.mock import Mock, AsyncMock

from backend.services.team_orchestrator_interface import (
    TeamOrchestratorInterface,
    CoordinationStrategy,
    TeamResult,
)
from backend.services.persona_interface import PersonaTask, PersonaResult, PersonaInterface, PersonaRole, PersonaCapability


class ConcreteTeamOrchestrator(TeamOrchestratorInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._personas = {}
        self._strategy = CoordinationStrategy.MODERATOR
    
    async def coordinate_task(self, task, team_config=None):
        """Coordinate task."""
        return TeamResult(
            task_id=task.task_id,
            result="Coordinated result",
            persona_results=[],
        )
    
    async def add_persona(self, persona, role_in_team=None):
        """Add persona."""
        self._personas[persona.get_name()] = persona
        return True
    
    async def remove_persona(self, persona_name):
        """Remove persona."""
        if persona_name in self._personas:
            del self._personas[persona_name]
            return True
        return False
    
    async def get_team_status(self):
        """Get status."""
        return {"persona_count": len(self._personas)}
    
    async def get_team_members(self):
        """Get members."""
        return [{"name": name} for name in self._personas.keys()]
    
    def get_coordination_strategy(self):
        """Get strategy."""
        return self._strategy
    
    async def load_team_config(self, team_id_or_name):
        """Load config."""
        return True


class TestTeamOrchestratorInterface:
    """Test TeamOrchestratorInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TeamOrchestratorInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        orchestrator = ConcreteTeamOrchestrator()
        assert isinstance(orchestrator, TeamOrchestratorInterface)
        assert isinstance(orchestrator, ABC)
    
    @pytest.mark.asyncio
    async def test_coordinate_task(self):
        """Test coordinating a task."""
        orchestrator = ConcreteTeamOrchestrator()
        
        task = PersonaTask(
            task_id="task-1",
            description="Test task",
            context={},
        )
        
        result = await orchestrator.coordinate_task(task)
        
        assert result.task_id == "task-1"
        assert "Coordinated" in result.result
    
    @pytest.mark.asyncio
    async def test_add_persona(self):
        """Test adding a persona."""
        orchestrator = ConcreteTeamOrchestrator()
        
        mock_persona = Mock(spec=PersonaInterface)
        mock_persona.get_name.return_value = "Test Persona"
        
        added = await orchestrator.add_persona(mock_persona)
        
        assert added is True
    
    @pytest.mark.asyncio
    async def test_remove_persona(self):
        """Test removing a persona."""
        orchestrator = ConcreteTeamOrchestrator()
        
        mock_persona = Mock(spec=PersonaInterface)
        mock_persona.get_name.return_value = "Test Persona"
        
        await orchestrator.add_persona(mock_persona)
        removed = await orchestrator.remove_persona("Test Persona")
        
        assert removed is True
    
    @pytest.mark.asyncio
    async def test_get_team_status(self):
        """Test getting team status."""
        orchestrator = ConcreteTeamOrchestrator()
        
        status = await orchestrator.get_team_status()
        
        assert "persona_count" in status
    
    @pytest.mark.asyncio
    async def test_get_team_members(self):
        """Test getting team members."""
        orchestrator = ConcreteTeamOrchestrator()
        
        mock_persona = Mock(spec=PersonaInterface)
        mock_persona.get_name.return_value = "Test Persona"
        
        await orchestrator.add_persona(mock_persona)
        members = await orchestrator.get_team_members()
        
        assert len(members) == 1
        assert members[0]["name"] == "Test Persona"
    
    def test_get_coordination_strategy(self):
        """Test getting coordination strategy."""
        orchestrator = ConcreteTeamOrchestrator()
        
        strategy = orchestrator.get_coordination_strategy()
        
        assert isinstance(strategy, CoordinationStrategy)
    
    @pytest.mark.asyncio
    async def test_load_team_config(self):
        """Test loading team configuration."""
        orchestrator = ConcreteTeamOrchestrator()
        
        loaded = await orchestrator.load_team_config("team-1")
        
        assert loaded is True


class TestTeamResult:
    """Test TeamResult."""
    
    def test_create_result(self):
        """Test creating a team result."""
        result = TeamResult(
            task_id="task-1",
            result="Team result",
            persona_results=[],
        )
        
        assert result.task_id == "task-1"
        assert result.result == "Team result"
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        persona_result = PersonaResult(
            task_id="task-1",
            result="Persona result",
        )
        
        team_result = TeamResult(
            task_id="task-1",
            result="Team result",
            persona_results=[persona_result],
        )
        
        data = team_result.to_dict()
        assert data["task_id"] == "task-1"
        assert len(data["persona_results"]) == 1
