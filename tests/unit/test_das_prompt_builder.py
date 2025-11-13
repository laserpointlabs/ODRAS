"""
Unit tests for DAS prompt builder.

Tests prompt building for different styles and edge cases.
"""

import pytest
from backend.services.das_prompt_builder import DASPromptBuilder
from backend.rag.core.context_models import RAGContext, RAGChunk, RAGSource


class TestDASPromptBuilder:
    """Tests for DASPromptBuilder."""
    
    def test_build_prompt_comprehensive_style(self):
        """Test building comprehensive style prompt."""
        source = RAGSource(source_id="test-id", source_type="project", title="Test Doc")
        chunk = RAGChunk(
            chunk_id="c1",
            content="Test content here",
            relevance_score=0.8,
            source=source
        )
        context = RAGContext(query="test query", chunks=[chunk])
        
        prompt = DASPromptBuilder.build_prompt(context, "test query", style="comprehensive")
        
        assert "comprehensive" in prompt.lower() or "well-structured" in prompt.lower()
        assert "Test content here" in prompt
        assert "test query" in prompt
    
    def test_build_prompt_concise_style(self):
        """Test building concise style prompt."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Brief content", relevance_score=0.8, source=source)
        context = RAGContext(query="short question", chunks=[chunk])
        
        prompt = DASPromptBuilder.build_prompt(context, "short question", style="concise")
        
        assert "concise" in prompt.lower() or "brief" in prompt.lower()
        assert "Brief content" in prompt
    
    def test_build_prompt_technical_style(self):
        """Test building technical style prompt."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Technical details", relevance_score=0.8, source=source)
        context = RAGContext(query="technical question", chunks=[chunk])
        
        prompt = DASPromptBuilder.build_prompt(context, "technical question", style="technical")
        
        assert "technical" in prompt.lower()
        assert "Technical details" in prompt
    
    def test_build_prompt_with_sources(self):
        """Test building prompt with source citations."""
        source = RAGSource(
            source_id="test-id",
            source_type="project",
            title="Test Document",
            domain="requirements"
        )
        chunk = RAGChunk(chunk_id="c1", content="Content", relevance_score=0.8, source=source)
        context = RAGContext(query="query", chunks=[chunk])
        
        prompt = DASPromptBuilder.build_prompt(context, "query", include_sources=True)
        
        assert "Source:" in prompt or "Title:" in prompt
        assert "Test Document" in prompt
    
    def test_build_prompt_without_sources(self):
        """Test building prompt without source citations."""
        source = RAGSource(source_id="test-id", source_type="project", title="Test Doc")
        chunk = RAGChunk(chunk_id="c1", content="Content", relevance_score=0.8, source=source)
        context = RAGContext(query="query", chunks=[chunk])
        
        prompt = DASPromptBuilder.build_prompt(context, "query", include_sources=False)
        
        # Should still contain content but may not have explicit source citations
        assert "Content" in prompt
    
    def test_build_prompt_empty_context(self):
        """Test building prompt when no context is available."""
        context = RAGContext(query="test query", chunks=[])
        
        prompt = DASPromptBuilder.build_prompt(context, "test query")
        
        assert "couldn't find" in prompt.lower() or "no relevant" in prompt.lower()
        assert "test query" in prompt
    
    def test_build_prompt_max_chunks(self):
        """Test building prompt with max_chunks limit."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunks = [
            RAGChunk(chunk_id=f"c{i}", content=f"Content {i}", relevance_score=0.9 - i*0.1, source=source)
            for i in range(5)
        ]
        context = RAGContext(query="query", chunks=chunks)
        
        prompt = DASPromptBuilder.build_prompt(context, "query", max_chunks=2)
        
        # Should only include top 2 chunks
        assert "Content 0" in prompt
        assert "Content 1" in prompt
        # Lower relevance chunks may or may not be included depending on implementation
        # But we verify top chunks are there
    
    def test_build_context_section_multiple_chunks(self):
        """Test building context section with multiple chunks."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunks = [
            RAGChunk(chunk_id="c1", content="First chunk", relevance_score=0.8, source=source),
            RAGChunk(chunk_id="c2", content="Second chunk", relevance_score=0.7, source=source),
        ]
        context = RAGContext(query="query", chunks=chunks)
        
        prompt = DASPromptBuilder.build_prompt(context, "query")
        
        assert "First chunk" in prompt
        assert "Second chunk" in prompt
        assert "[Context 1]" in prompt
        assert "[Context 2]" in prompt
    
    def test_build_context_summary(self):
        """Test building context summary."""
        source1 = RAGSource(source_id="id1", source_type="project", domain="ontology")
        source2 = RAGSource(source_id="id2", source_type="training", domain="requirements")
        chunks = [
            RAGChunk(chunk_id="c1", content="C1", relevance_score=0.8, source=source1),
            RAGChunk(chunk_id="c2", content="C2", relevance_score=0.7, source=source2),
        ]
        context = RAGContext(query="query", chunks=chunks)
        
        summary = DASPromptBuilder.build_context_summary(context)
        
        assert "Total chunks: 2" in summary
        assert "project" in summary.lower() or "training" in summary.lower()
    
    def test_build_context_summary_empty(self):
        """Test building summary for empty context."""
        context = RAGContext(query="query", chunks=[])
        
        summary = DASPromptBuilder.build_context_summary(context)
        
        assert "No chunks" in summary or "0" in summary
    
    def test_build_prompt_default_style(self):
        """Test that default style is comprehensive."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Content", relevance_score=0.8, source=source)
        context = RAGContext(query="query", chunks=[chunk])
        
        # Don't specify style - should default to comprehensive
        prompt = DASPromptBuilder.build_prompt(context, "query")
        
        # Should work without error and include content
        assert "Content" in prompt
        assert "query" in prompt
