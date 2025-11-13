"""
Unit tests for DAS personas.

Tests each persona's role-specific behavior.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from backend.services.das_personas import (
    ResearcherPersona,
    AnalystPersona,
    WriterPersona,
    ModeratorPersona,
)
from backend.services.persona_interface import PersonaTask, PersonaRole, PersonaCapability
from backend.services.config import Settings


@pytest.fixture
def settings():
    """Create settings instance."""
    return Settings()


@pytest.fixture
def researcher(settings):
    """Create researcher persona."""
    return ResearcherPersona(settings)


@pytest.fixture
def analyst(settings):
    """Create analyst persona."""
    return AnalystPersona(settings)


@pytest.fixture
def writer(settings):
    """Create writer persona."""
    return WriterPersona(settings)


@pytest.fixture
def moderator(settings):
    """Create moderator persona."""
    return ModeratorPersona(settings)


class TestResearcherPersona:
    """Test Researcher persona."""
    
    def test_get_role(self, researcher):
        """Test getting role."""
        assert researcher.get_role() == PersonaRole.RESEARCHER
    
    def test_get_capabilities(self, researcher):
        """Test getting capabilities."""
        capabilities = researcher.get_capabilities()
        assert PersonaCapability.INFORMATION_RETRIEVAL in capabilities
        assert PersonaCapability.KNOWLEDGE_SYNTHESIS in capabilities
    
    def test_get_name(self, researcher):
        """Test getting name."""
        assert researcher.get_name() == "Researcher"
    
    @pytest.mark.asyncio
    async def test_can_handle_research_task(self, researcher):
        """Test that researcher can handle research tasks."""
        task = PersonaTask(
            task_id="task-1",
            description="Find information about ontologies",
            context={},
        )
        
        can_handle = await researcher.can_handle_task(task)
        assert can_handle is True
    
    @pytest.mark.asyncio
    async def test_process_task(self, researcher):
        """Test processing a task."""
        task = PersonaTask(
            task_id="task-1",
            description="Find information about requirements",
            context={"sources": [{"title": "Source 1"}]},
        )
        
        with patch.object(researcher, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Here is the information about requirements..."
            
            result = await researcher.process_task(task)
            
            assert result.task_id == "task-1"
            assert "information" in result.result.lower()
            assert len(result.sources) == 1


class TestAnalystPersona:
    """Test Analyst persona."""
    
    def test_get_role(self, analyst):
        """Test getting role."""
        assert analyst.get_role() == PersonaRole.ANALYST
    
    def test_get_capabilities(self, analyst):
        """Test getting capabilities."""
        capabilities = analyst.get_capabilities()
        assert PersonaCapability.DATA_ANALYSIS in capabilities
        assert PersonaCapability.QUALITY_REVIEW in capabilities
    
    @pytest.mark.asyncio
    async def test_can_handle_analysis_task(self, analyst):
        """Test that analyst can handle analysis tasks."""
        task = PersonaTask(
            task_id="task-1",
            description="Analyze the data patterns",
            context={},
        )
        
        can_handle = await analyst.can_handle_task(task)
        assert can_handle is True


class TestWriterPersona:
    """Test Writer persona."""
    
    def test_get_role(self, writer):
        """Test getting role."""
        assert writer.get_role() == PersonaRole.WRITER
    
    def test_get_capabilities(self, writer):
        """Test getting capabilities."""
        capabilities = writer.get_capabilities()
        assert PersonaCapability.CONTENT_CREATION in capabilities
    
    @pytest.mark.asyncio
    async def test_can_handle_writing_task(self, writer):
        """Test that writer can handle writing tasks."""
        task = PersonaTask(
            task_id="task-1",
            description="Write documentation about the system",
            context={},
        )
        
        can_handle = await writer.can_handle_task(task)
        assert can_handle is True


class TestModeratorPersona:
    """Test Moderator persona."""
    
    def test_get_role(self, moderator):
        """Test getting role."""
        assert moderator.get_role() == PersonaRole.MODERATOR
    
    def test_get_capabilities(self, moderator):
        """Test getting capabilities."""
        capabilities = moderator.get_capabilities()
        assert PersonaCapability.COORDINATION in capabilities
    
    @pytest.mark.asyncio
    async def test_can_handle_coordination_task(self, moderator):
        """Test that moderator can handle coordination tasks."""
        task = PersonaTask(
            task_id="task-1",
            description="Coordinate the team to complete this complex task",
            context={},
        )
        
        can_handle = await moderator.can_handle_task(task)
        assert can_handle is True
    
    @pytest.mark.asyncio
    async def test_cannot_handle_simple_task(self, moderator):
        """Test that moderator doesn't handle simple, non-coordination tasks."""
        task = PersonaTask(
            task_id="task-1",
            description="What is an ontology?",
            context={},
        )
        
        can_handle = await moderator.can_handle_task(task)
        assert can_handle is False


class TestPersonaStatus:
    """Test persona status management."""
    
    @pytest.mark.asyncio
    async def test_status_changes_during_task(self, researcher):
        """Test that status changes when processing task."""
        initial_status = await researcher.get_status()
        assert initial_status["available"] is True
        assert initial_status["busy"] is False
        
        task = PersonaTask(
            task_id="task-1",
            description="Find information",
            context={},
        )
        
        with patch.object(researcher, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Result"
            
            # Process task
            await researcher.process_task(task)
            
            # Status should be back to available after task
            final_status = await researcher.get_status()
            assert final_status["available"] is True
            assert final_status["busy"] is False
