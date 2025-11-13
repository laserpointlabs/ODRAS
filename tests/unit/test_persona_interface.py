"""
Unit tests for PersonaInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from typing import List, Dict, Any

from backend.services.persona_interface import (
    PersonaInterface,
    PersonaRole,
    PersonaCapability,
    PersonaTask,
    PersonaResult,
)


class ConcretePersona(PersonaInterface):
    """Concrete implementation for testing."""
    
    def __init__(self, name: str, role: PersonaRole, capabilities: List[PersonaCapability]):
        self._name = name
        self._role = role
        self._capabilities = capabilities
        self._description = f"Test persona: {name}"
    
    async def process_task(self, task: PersonaTask) -> PersonaResult:
        """Process task."""
        return PersonaResult(
            task_id=task.task_id,
            result=f"Processed by {self._name}",
            confidence=0.9,
        )
    
    def get_role(self) -> PersonaRole:
        """Get role."""
        return self._role
    
    def get_capabilities(self) -> List[PersonaCapability]:
        """Get capabilities."""
        return self._capabilities
    
    def get_name(self) -> str:
        """Get name."""
        return self._name
    
    def get_description(self) -> str:
        """Get description."""
        return self._description
    
    async def can_handle_task(self, task: PersonaTask) -> bool:
        """Check if can handle task."""
        return True
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status."""
        return {"available": True, "busy": False}


class TestPersonaInterface:
    """Test PersonaInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PersonaInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        persona = ConcretePersona(
            "Test Researcher",
            PersonaRole.RESEARCHER,
            [PersonaCapability.INFORMATION_RETRIEVAL]
        )
        assert isinstance(persona, PersonaInterface)
        assert isinstance(persona, ABC)
    
    @pytest.mark.asyncio
    async def test_process_task(self):
        """Test processing a task."""
        persona = ConcretePersona(
            "Test Persona",
            PersonaRole.ANALYST,
            [PersonaCapability.DATA_ANALYSIS]
        )
        
        task = PersonaTask(
            task_id="task-1",
            description="Analyze data",
            context={"data": "test"},
        )
        
        result = await persona.process_task(task)
        
        assert result.task_id == "task-1"
        assert "Processed by" in result.result
    
    def test_get_role(self):
        """Test getting role."""
        persona = ConcretePersona(
            "Test Writer",
            PersonaRole.WRITER,
            [PersonaCapability.CONTENT_CREATION]
        )
        
        assert persona.get_role() == PersonaRole.WRITER
    
    def test_get_capabilities(self):
        """Test getting capabilities."""
        persona = ConcretePersona(
            "Test Persona",
            PersonaRole.RESEARCHER,
            [
                PersonaCapability.INFORMATION_RETRIEVAL,
                PersonaCapability.KNOWLEDGE_SYNTHESIS,
            ]
        )
        
        capabilities = persona.get_capabilities()
        assert len(capabilities) == 2
        assert PersonaCapability.INFORMATION_RETRIEVAL in capabilities
    
    def test_get_name(self):
        """Test getting name."""
        persona = ConcretePersona(
            "Test Name",
            PersonaRole.MODERATOR,
            [PersonaCapability.COORDINATION]
        )
        
        assert persona.get_name() == "Test Name"
    
    def test_get_description(self):
        """Test getting description."""
        persona = ConcretePersona(
            "Test Persona",
            PersonaRole.SPECIALIST,
            [PersonaCapability.CODE_GENERATION]
        )
        
        assert "Test persona" in persona.get_description()
    
    @pytest.mark.asyncio
    async def test_can_handle_task(self):
        """Test checking if persona can handle task."""
        persona = ConcretePersona(
            "Test Persona",
            PersonaRole.ANALYST,
            [PersonaCapability.DATA_ANALYSIS]
        )
        
        task = PersonaTask(
            task_id="task-1",
            description="Analyze",
            context={},
        )
        
        can_handle = await persona.can_handle_task(task)
        assert can_handle is True
    
    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting status."""
        persona = ConcretePersona(
            "Test Persona",
            PersonaRole.RESEARCHER,
            [PersonaCapability.INFORMATION_RETRIEVAL]
        )
        
        status = await persona.get_status()
        assert "available" in status


class TestPersonaTask:
    """Test PersonaTask."""
    
    def test_create_task(self):
        """Test creating a task."""
        task = PersonaTask(
            task_id="task-1",
            description="Test task",
            context={"key": "value"},
            priority=8,
        )
        
        assert task.task_id == "task-1"
        assert task.description == "Test task"
        assert task.context == {"key": "value"}
        assert task.priority == 8
    
    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = PersonaTask(
            task_id="task-1",
            description="Test",
            context={"data": "test"},
            dependencies=["task-0"],
        )
        
        data = task.to_dict()
        assert data["task_id"] == "task-1"
        assert "dependencies" in data


class TestPersonaResult:
    """Test PersonaResult."""
    
    def test_create_result(self):
        """Test creating a result."""
        result = PersonaResult(
            task_id="task-1",
            result="Test result",
            confidence=0.85,
        )
        
        assert result.task_id == "task-1"
        assert result.result == "Test result"
        assert result.confidence == 0.85
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = PersonaResult(
            task_id="task-1",
            result="Result",
            sources=[{"source": "test"}],
        )
        
        data = result.to_dict()
        assert data["task_id"] == "task-1"
        assert len(data["sources"]) == 1
