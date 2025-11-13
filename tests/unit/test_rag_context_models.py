"""
Unit tests for RAG context models.

Tests model validation, serialization, and edge cases.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.rag.core.context_models import RAGSource, RAGChunk, RAGContext


class TestRAGSource:
    """Tests for RAGSource model."""
    
    def test_create_minimal_source(self):
        """Test creating a source with minimal required fields."""
        source = RAGSource(
            source_id="test-id",
            source_type="project"
        )
        assert source.source_id == "test-id"
        assert source.source_type == "project"
        assert source.title is None
        assert source.metadata == {}
    
    def test_create_full_source(self):
        """Test creating a source with all fields."""
        source = RAGSource(
            source_id="test-id",
            source_type="training",
            title="Test Document",
            file_id="file-uuid",
            collection_id="coll-uuid",
            collection_name="das_training_ontology",
            project_id="proj-uuid",
            domain="ontology",
            metadata={"key": "value"}
        )
        assert source.source_id == "test-id"
        assert source.source_type == "training"
        assert source.title == "Test Document"
        assert source.domain == "ontology"
    
    def test_source_validation_requires_source_id(self):
        """Test that source_id is required."""
        with pytest.raises(ValidationError):
            RAGSource(source_type="project")
    
    def test_source_validation_requires_source_type(self):
        """Test that source_type is required."""
        with pytest.raises(ValidationError):
            RAGSource(source_id="test-id")


class TestRAGChunk:
    """Tests for RAGChunk model."""
    
    def test_create_minimal_chunk(self):
        """Test creating a chunk with minimal required fields."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(
            chunk_id="chunk-id",
            content="Test content",
            relevance_score=0.5,
            source=source
        )
        assert chunk.chunk_id == "chunk-id"
        assert chunk.content == "Test content"
        assert chunk.relevance_score == 0.5
        assert chunk.source.source_id == "test-id"
    
    def test_create_full_chunk(self):
        """Test creating a chunk with all fields."""
        source = RAGSource(source_id="test-id", source_type="training", domain="ontology")
        chunk = RAGChunk(
            chunk_id="chunk-id",
            content="Test content",
            relevance_score=0.85,
            source=source,
            sequence_number=5,
            token_count=150,
            metadata={"key": "value"}
        )
        assert chunk.sequence_number == 5
        assert chunk.token_count == 150
        assert chunk.metadata == {"key": "value"}
    
    def test_chunk_validation_requires_chunk_id(self):
        """Test that chunk_id is required."""
        source = RAGSource(source_id="test-id", source_type="project")
        with pytest.raises(ValidationError):
            RAGChunk(
                content="Test",
                relevance_score=0.5,
                source=source
            )
    
    def test_chunk_validation_requires_content(self):
        """Test that content is required."""
        source = RAGSource(source_id="test-id", source_type="project")
        with pytest.raises(ValidationError):
            RAGChunk(
                chunk_id="chunk-id",
                relevance_score=0.5,
                source=source
            )
    
    def test_chunk_validation_requires_relevance_score(self):
        """Test that relevance_score is required."""
        source = RAGSource(source_id="test-id", source_type="project")
        with pytest.raises(ValidationError):
            RAGChunk(
                chunk_id="chunk-id",
                content="Test",
                source=source
            )
    
    def test_chunk_validation_score_range(self):
        """Test that relevance_score should be between 0 and 1."""
        source = RAGSource(source_id="test-id", source_type="project")
        # Valid scores
        chunk1 = RAGChunk(chunk_id="c1", content="Test", relevance_score=0.0, source=source)
        chunk2 = RAGChunk(chunk_id="c2", content="Test", relevance_score=1.0, source=source)
        chunk3 = RAGChunk(chunk_id="c3", content="Test", relevance_score=0.5, source=source)
        assert chunk1.relevance_score == 0.0
        assert chunk2.relevance_score == 1.0
        assert chunk3.relevance_score == 0.5
        
        # Note: Pydantic doesn't validate ranges by default, but we can add custom validators if needed


class TestRAGContext:
    """Tests for RAGContext model."""
    
    def test_create_minimal_context(self):
        """Test creating context with minimal fields."""
        context = RAGContext(query="test query")
        assert context.query == "test query"
        assert context.chunks == []
        assert context.total_chunks_found == 0
        assert isinstance(context.retrieved_at, datetime)
    
    def test_create_context_with_chunks(self):
        """Test creating context with chunks."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk1 = RAGChunk(chunk_id="c1", content="Content 1", relevance_score=0.8, source=source)
        chunk2 = RAGChunk(chunk_id="c2", content="Content 2", relevance_score=0.6, source=source)
        
        context = RAGContext(
            query="test query",
            chunks=[chunk1, chunk2],
            total_chunks_found=2
        )
        assert len(context.chunks) == 2
        assert context.total_chunks_found == 2
    
    def test_get_chunks_by_source_type(self):
        """Test filtering chunks by source type."""
        source1 = RAGSource(source_id="id1", source_type="project")
        source2 = RAGSource(source_id="id2", source_type="training")
        chunk1 = RAGChunk(chunk_id="c1", content="C1", relevance_score=0.8, source=source1)
        chunk2 = RAGChunk(chunk_id="c2", content="C2", relevance_score=0.6, source=source2)
        chunk3 = RAGChunk(chunk_id="c3", content="C3", relevance_score=0.7, source=source1)
        
        context = RAGContext(query="test", chunks=[chunk1, chunk2, chunk3])
        project_chunks = context.get_chunks_by_source_type("project")
        assert len(project_chunks) == 2
        assert all(c.source.source_type == "project" for c in project_chunks)
    
    def test_get_chunks_by_domain(self):
        """Test filtering chunks by domain."""
        source1 = RAGSource(source_id="id1", source_type="project", domain="ontology")
        source2 = RAGSource(source_id="id2", source_type="project", domain="requirements")
        chunk1 = RAGChunk(chunk_id="c1", content="C1", relevance_score=0.8, source=source1)
        chunk2 = RAGChunk(chunk_id="c2", content="C2", relevance_score=0.6, source=source2)
        
        context = RAGContext(query="test", chunks=[chunk1, chunk2])
        ontology_chunks = context.get_chunks_by_domain("ontology")
        assert len(ontology_chunks) == 1
        assert ontology_chunks[0].source.domain == "ontology"
    
    def test_get_top_chunks(self):
        """Test getting top K chunks by relevance."""
        source = RAGSource(source_id="id1", source_type="project")
        chunks = [
            RAGChunk(chunk_id="c1", content="C1", relevance_score=0.5, source=source),
            RAGChunk(chunk_id="c2", content="C2", relevance_score=0.9, source=source),
            RAGChunk(chunk_id="c3", content="C3", relevance_score=0.7, source=source),
        ]
        context = RAGContext(query="test", chunks=chunks)
        
        top_2 = context.get_top_chunks(2)
        assert len(top_2) == 2
        assert top_2[0].relevance_score == 0.9
        assert top_2[1].relevance_score == 0.7
    
    def test_get_all_content(self):
        """Test getting all chunk content concatenated."""
        source = RAGSource(source_id="id1", source_type="project")
        chunks = [
            RAGChunk(chunk_id="c1", content="Content 1", relevance_score=0.8, source=source),
            RAGChunk(chunk_id="c2", content="Content 2", relevance_score=0.6, source=source),
        ]
        context = RAGContext(query="test", chunks=chunks)
        
        content = context.get_all_content()
        assert "Content 1" in content
        assert "Content 2" in content
        assert "\n\n" in content  # Should be separated by double newline
    
    def test_get_all_content_empty(self):
        """Test getting content when no chunks."""
        context = RAGContext(query="test")
        assert context.get_all_content() == ""
    
    def test_context_serialization(self):
        """Test that context can be serialized to JSON."""
        source = RAGSource(source_id="test-id", source_type="project")
        chunk = RAGChunk(chunk_id="c1", content="Test", relevance_score=0.8, source=source)
        context = RAGContext(query="test query", chunks=[chunk])
        
        # Should be able to convert to dict
        context_dict = context.model_dump()
        assert context_dict["query"] == "test query"
        assert len(context_dict["chunks"]) == 1
        
        # Should be able to convert to JSON
        json_str = context.model_dump_json()
        assert "test query" in json_str
        assert "c1" in json_str
