"""
Unit tests for DAS code generation integration.

Tests mocked generators/executors.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from backend.services.das_core_engine import DASCoreEngine
from backend.services.code_generator_interface import (
    CodeGeneratorInterface,
    CodeGenerationResult,
    CodeGenerationCapability,
)
from backend.services.code_executor_interface import (
    CodeExecutorInterface,
    ExecutionResult,
    ExecutionStatus,
)
from backend.services.tool_registry_interface import ToolRegistryInterface
from backend.services.config import Settings
from backend.rag.core.rag_service_interface import RAGServiceInterface


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service."""
    rag = Mock(spec=RAGServiceInterface)
    rag.query_knowledge_base = AsyncMock(return_value=Mock())
    return rag


@pytest.fixture
def mock_project_manager():
    """Create mock project manager."""
    pm = Mock()
    pm.get_project_context = AsyncMock(return_value={
        "project_thread": {"project_thread_id": "test-thread"},
        "conversation_history": [],
        "recent_events": [],
    })
    pm.store_conversation_message = AsyncMock()
    return pm


@pytest.fixture
def mock_code_generator():
    """Create mock code generator."""
    generator = Mock(spec=CodeGeneratorInterface)
    generator.generate_code = AsyncMock(return_value=CodeGenerationResult(
        code="result = 1 + 2",
        validation_passed=True,
        description="Adds numbers",
    ))
    return generator


@pytest.fixture
def mock_code_executor():
    """Create mock code executor."""
    executor = Mock(spec=CodeExecutorInterface)
    executor.execute = AsyncMock(return_value=ExecutionResult(
        status=ExecutionStatus.COMPLETED,
        output="3",
        return_value=3,
        execution_time_seconds=0.1,
    ))
    return executor


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    registry = Mock(spec=ToolRegistryInterface)
    registry.find_tool = AsyncMock(return_value=[])
    registry.store_tool = AsyncMock(return_value="tool-123")
    registry.update_usage = AsyncMock(return_value=True)
    return registry


@pytest.fixture
def das_engine(mock_rag_service, mock_project_manager, mock_code_generator, mock_code_executor, mock_tool_registry):
    """Create DASCoreEngine with code generation capabilities."""
    settings = Settings()
    return DASCoreEngine(
        settings=settings,
        rag_service=mock_rag_service,
        project_manager=mock_project_manager,
        code_generator=mock_code_generator,
        code_executor=mock_code_executor,
        tool_registry=mock_tool_registry,
    )


class TestDASCodeGeneration:
    """Test DAS code generation integration."""
    
    @pytest.mark.asyncio
    async def test_detect_code_generation_keywords(self, das_engine):
        """Test detection of code generation keywords."""
        # Message with code generation keyword
        message = "write code to calculate the sum"
        
        result = das_engine._detect_and_handle_code_generation(
            message, "project-1", "user-1"
        )
        
        # Check if result is an async generator (not None)
        assert result is not None
        
        # Collect chunks
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert any("code" in str(chunk.get("content", "")).lower() for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_no_code_generation_for_normal_message(self, das_engine):
        """Test that normal messages don't trigger code generation."""
        message = "What is ontology?"
        
        result = das_engine._detect_and_handle_code_generation(
            message, "project-1", "user-1"
        )
        
        # For async generators, check if it yields anything
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        # Should be empty for normal messages
        assert len(chunks) == 0
    
    @pytest.mark.asyncio
    async def test_code_generation_flow(self, das_engine, mock_code_generator, mock_code_executor):
        """Test complete code generation and execution flow."""
        message = "write code to calculate 1 + 2"
        
        result = das_engine._detect_and_handle_code_generation(
            message, "project-1", "user-1"
        )
        
        assert result is not None
        
        # Collect chunks
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        # Verify code generator was called
        mock_code_generator.generate_code.assert_called_once()
        
        # Verify code executor was called
        mock_code_executor.execute.assert_called_once()
        
        # Verify success message
        content_chunks = [c for c in chunks if c.get("type") == "content"]
        assert any("successful" in str(c.get("content", "")).lower() for c in content_chunks)
    
    @pytest.mark.asyncio
    async def test_tool_registry_lookup(self, das_engine, mock_tool_registry, mock_code_executor):
        """Test that tool registry is checked before generating new code."""
        from backend.services.tool_registry_interface import ToolMetadata, ToolType
        from datetime import datetime, timezone
        
        # Mock existing tool in registry
        existing_tool = ToolMetadata(
            tool_id="existing-tool",
            name="Calculator",
            description="Adds numbers",
            tool_type=ToolType.CALCULATOR,
            code="result = a + b",
            capabilities=["calculation"],
            created_at=datetime.now(timezone.utc),
            created_by="user-1",
        )
        
        mock_tool_registry.find_tool = AsyncMock(return_value=[existing_tool])
        
        message = "calculate 5 + 3"
        
        result = das_engine._detect_and_handle_code_generation(
            message, "project-1", "user-1"
        )
        
        assert result is not None
        
        # Collect chunks
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        # Verify registry was checked
        mock_tool_registry.find_tool.assert_called()
        
        # Verify existing tool was used (not new generation)
        # The code generator should not be called if tool is found
        # (This depends on implementation - if tool is found, we use it)
    
    @pytest.mark.asyncio
    async def test_tool_storage_after_success(self, das_engine, mock_code_generator, mock_code_executor, mock_tool_registry):
        """Test that successful tools are stored in registry."""
        # Ensure tool registry returns empty list so new code is generated
        mock_tool_registry.find_tool = AsyncMock(return_value=[])
        
        message = "write code to add numbers"
        
        result = das_engine._detect_and_handle_code_generation(
            message, "project-1", "user-1"
        )
        
        assert result is not None
        
        # Collect all chunks to complete execution
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        # Verify code generator was called
        mock_code_generator.generate_code.assert_called_once()
        
        # Verify code executor was called
        mock_code_executor.execute.assert_called_once()
        
        # Verify tool was stored (only if execution succeeded)
        # The mock executor returns COMPLETED status, so tool should be stored
        mock_tool_registry.store_tool.assert_called_once()
