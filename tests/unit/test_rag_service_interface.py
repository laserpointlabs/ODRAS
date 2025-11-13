"""
Unit tests for RAG service interface.

Tests interface contract validation and mock implementations.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock

from backend.rag.core.rag_service_interface import RAGServiceInterface
from backend.rag.core.context_models import RAGContext, RAGChunk, RAGSource


class MockRAGService(RAGServiceInterface):
    """Mock implementation of RAGServiceInterface for testing."""
    
    def __init__(self):
        self.query_knowledge_base_mock = AsyncMock()
        self.get_query_suggestions_mock = AsyncMock()
        self.store_conversation_messages_mock = AsyncMock()
    
    async def query_knowledge_base(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> RAGContext:
        """Mock implementation."""
        return await self.query_knowledge_base_mock(query, context)
    
    async def get_query_suggestions(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Mock implementation."""
        return await self.get_query_suggestions_mock(context)
    
    async def store_conversation_messages(
        self,
        thread_id: str,
        messages: List[Dict[str, Any]],
        project_id: str = None,
    ) -> None:
        """Mock implementation."""
        return await self.store_conversation_messages_mock(thread_id, messages, project_id)


class TestRAGServiceInterface:
    """Tests for RAGServiceInterface contract."""
    
    @pytest.mark.asyncio
    async def test_query_knowledge_base_returns_rag_context(self):
        """Test that query_knowledge_base returns RAGContext."""
        mock_service = MockRAGService()
        
        # Setup mock to return a RAGContext
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Test", relevance_score=0.8, source=source)
        expected_context = RAGContext(query="test query", chunks=[chunk])
        
        mock_service.query_knowledge_base_mock.return_value = expected_context
        
        result = await mock_service.query_knowledge_base("test query", {})
        assert isinstance(result, RAGContext)
        assert result.query == "test query"
        assert len(result.chunks) == 1
    
    @pytest.mark.asyncio
    async def test_query_knowledge_base_receives_context(self):
        """Test that query_knowledge_base receives context properly."""
        mock_service = MockRAGService()
        
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Test", relevance_score=0.8, source=source)
        context = RAGContext(query="test", chunks=[chunk])
        mock_service.query_knowledge_base_mock.return_value = context
        
        test_context = {
            "project_id": "proj-123",
            "user_id": "user-456",
            "max_chunks": 10
        }
        
        await mock_service.query_knowledge_base("test query", test_context)
        
        # Verify mock was called with correct arguments
        mock_service.query_knowledge_base_mock.assert_called_once()
        call_args = mock_service.query_knowledge_base_mock.call_args
        assert call_args[0][0] == "test query"
        assert call_args[0][1] == test_context
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_returns_list(self):
        """Test that get_query_suggestions returns a list of strings."""
        mock_service = MockRAGService()
        mock_service.get_query_suggestions_mock.return_value = [
            "What is the system architecture?",
            "Tell me about the requirements",
            "Explain the ontology structure"
        ]
        
        suggestions = await mock_service.get_query_suggestions({})
        assert isinstance(suggestions, list)
        assert len(suggestions) == 3
        assert all(isinstance(s, str) for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_receives_context(self):
        """Test that get_query_suggestions receives context."""
        mock_service = MockRAGService()
        mock_service.get_query_suggestions_mock.return_value = []
        
        test_context = {"project_id": "proj-123"}
        await mock_service.get_query_suggestions(test_context)
        
        mock_service.get_query_suggestions_mock.assert_called_once_with(test_context)
    
    @pytest.mark.asyncio
    async def test_store_conversation_messages(self):
        """Test that store_conversation_messages can be called."""
        mock_service = MockRAGService()
        mock_service.store_conversation_messages_mock.return_value = None
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        await mock_service.store_conversation_messages("thread-123", messages, "proj-456")
        
        mock_service.store_conversation_messages_mock.assert_called_once_with(
            "thread-123",
            messages,
            "proj-456"
        )
    
    def test_interface_cannot_be_instantiated(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RAGServiceInterface()
    
    def test_mock_implementation_is_valid(self):
        """Test that MockRAGService properly implements the interface."""
        # Should be able to instantiate
        service = MockRAGService()
        assert isinstance(service, RAGServiceInterface)
        
        # Should have all required methods
        assert hasattr(service, 'query_knowledge_base')
        assert hasattr(service, 'get_query_suggestions')
        assert hasattr(service, 'store_conversation_messages')
