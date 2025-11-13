"""
Unit tests for DAS Core Engine with decoupled RAG interface.

Tests DAS integration with RAGServiceInterface using mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.das_core_engine import DASCoreEngine
from backend.rag.core.context_models import RAGContext, RAGChunk, RAGSource
from backend.rag.core.rag_service_interface import RAGServiceInterface


class MockRAGService(RAGServiceInterface):
    """Mock RAG service for testing DAS."""
    
    def __init__(self):
        self.query_knowledge_base_mock = AsyncMock()
        self.get_query_suggestions_mock = AsyncMock()
        self.store_conversation_messages_mock = AsyncMock()
    
    async def query_knowledge_base(self, query: str, context: dict):
        return await self.query_knowledge_base_mock(query, context)
    
    async def get_query_suggestions(self, context: dict):
        return await self.get_query_suggestions_mock(context)
    
    async def store_conversation_messages(self, thread_id: str, messages: list, project_id: str = None):
        return await self.store_conversation_messages_mock(thread_id, messages, project_id)


class TestDASCoreEngine:
    """Tests for DAS Core Engine with decoupled RAG."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.llm_model = "test-model"
        settings.llm_provider = "test-provider"
        settings.llm_api_key = "test-key"
        settings.llm_base_url = "http://test-url"
        return settings
    
    @pytest.fixture
    def mock_project_manager(self):
        """Create mock project manager."""
        manager = MagicMock()
        manager.get_project_context = AsyncMock(return_value={})
        manager.get_or_create_project_thread = AsyncMock(return_value="test-thread-id")
        manager.get_conversation_history = AsyncMock(return_value=[])
        manager.get_recent_events = AsyncMock(return_value=[])
        manager.get_project_metadata = AsyncMock(return_value={})
        manager.store_conversation_message = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        return MagicMock()
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create mock RAG service."""
        return MockRAGService()
    
    @pytest.fixture
    def das_engine(self, mock_settings, mock_rag_service, mock_project_manager, mock_db_service):
        """Create DAS engine instance."""
        return DASCoreEngine(
            settings=mock_settings,
            rag_service=mock_rag_service,
            project_manager=mock_project_manager,
            db_service=mock_db_service
        )
    
    def test_das_accepts_rag_service_interface(self, mock_settings, mock_rag_service, mock_project_manager, mock_db_service):
        """Test that DAS accepts RAGServiceInterface."""
        engine = DASCoreEngine(
            settings=mock_settings,
            rag_service=mock_rag_service,
            project_manager=mock_project_manager,
            db_service=mock_db_service
        )
        assert engine.rag_service == mock_rag_service
        assert isinstance(engine.rag_service, RAGServiceInterface)
    
    def test_das_has_prompt_builder(self, das_engine):
        """Test that DAS has a prompt builder."""
        assert hasattr(das_engine, 'prompt_builder')
        assert das_engine.prompt_builder is not None
    
    @pytest.mark.asyncio
    async def test_das_calls_rag_interface_method(self, das_engine, mock_rag_service):
        """Test that DAS calls RAG interface method correctly."""
        # Setup mock RAG context
        source = RAGSource(source_id="test-id", source_type="project", title="Test Doc")
        chunk = RAGChunk(
            chunk_id="c1",
            content="Test content",
            relevance_score=0.8,
            source=source
        )
        rag_context = RAGContext(query="test query", chunks=[chunk])
        
        mock_rag_service.query_knowledge_base_mock.return_value = rag_context
        
        # Mock the LLM call to avoid actual HTTP requests
        async def mock_llm_stream():
            yield {"type": "content", "content": "Test response"}
            yield {"type": "done", "metadata": {}}
        das_engine._call_llm_streaming = mock_llm_stream
        
        # Mock project manager methods (already set in fixture, but ensure they're async)
        das_engine.project_manager.get_or_create_project_thread = AsyncMock(return_value="test-thread-id")
        das_engine.project_manager.get_conversation_history = AsyncMock(return_value=[])
        das_engine.project_manager.get_recent_events = AsyncMock(return_value=[])
        das_engine.project_manager.get_project_metadata = AsyncMock(return_value={})
        
        # Mock database service
        das_engine.db_service.get_project_comprehensive = MagicMock(return_value={"name": "Test Project"})
        
        # Call process_message_stream
        async for chunk in das_engine.process_message_stream(
            project_id="test-proj",
            message="test message",
            user_id="test-user"
        ):
            if chunk.get("type") == "content":
                break  # Just get first chunk
        
        # Verify RAG service was called with correct interface signature
        mock_rag_service.query_knowledge_base_mock.assert_called_once()
        call_args = mock_rag_service.query_knowledge_base_mock.call_args
        assert call_args[0][0] == "test message"  # query
        assert isinstance(call_args[0][1], dict)  # context dict
        assert call_args[0][1]["project_id"] == "test-proj"
        assert call_args[0][1]["user_id"] == "test-user"
    
    @pytest.mark.asyncio
    async def test_das_uses_prompt_builder(self, das_engine, mock_rag_service):
        """Test that DAS uses prompt builder to format RAG context."""
        # Setup mock RAG context
        source = RAGSource(source_id="test-id", source_type="project", title="Test Doc")
        chunk = RAGChunk(
            chunk_id="c1",
            content="Test content",
            relevance_score=0.8,
            source=source
        )
        rag_context = RAGContext(query="test query", chunks=[chunk])
        
        mock_rag_service.query_knowledge_base_mock.return_value = rag_context
        
        # Mock the LLM call
        das_engine._call_llm_streaming = AsyncMock(return_value=iter(["Test response"]))
        
        # Mock project manager
        das_engine.project_manager.get_project_context = AsyncMock(return_value={})
        das_engine.project_manager.store_conversation_message = AsyncMock()
        
        # Mock database service
        das_engine.db_service.get_project_comprehensive = MagicMock(return_value={"name": "Test Project"})
        
        # Spy on prompt builder
        original_build = das_engine.prompt_builder._build_context_section
        build_called = False
        
        def spy_build(*args, **kwargs):
            nonlocal build_called
            build_called = True
            return original_build(*args, **kwargs)
        
        das_engine.prompt_builder._build_context_section = spy_build
        
        # Call process_message_stream
        async for chunk in das_engine.process_message_stream(
            project_id="test-proj",
            message="test message",
            user_id="test-user"
        ):
            if chunk.get("type") == "content":
                break
        
        # Verify prompt builder was used
        assert build_called, "Prompt builder should be used to format RAG context"
    
    @pytest.mark.asyncio
    async def test_das_handles_empty_rag_context(self, das_engine, mock_rag_service):
        """Test that DAS handles empty RAG context gracefully."""
        # Setup empty RAG context
        rag_context = RAGContext(query="test query", chunks=[])
        mock_rag_service.query_knowledge_base_mock.return_value = rag_context
        
        # Mock the LLM call
        das_engine._call_llm_streaming = AsyncMock(return_value=iter(["Test response"]))
        
        # Mock project manager
        das_engine.project_manager.get_project_context = AsyncMock(return_value={})
        das_engine.project_manager.store_conversation_message = AsyncMock()
        
        # Mock database service
        das_engine.db_service.get_project_comprehensive = MagicMock(return_value={"name": "Test Project"})
        
        # Call process_message_stream - should not raise error
        async for chunk in das_engine.process_message_stream(
            project_id="test-proj",
            message="test message",
            user_id="test-user"
        ):
            if chunk.get("type") == "content":
                break
        
        # Should complete without error
        assert True
