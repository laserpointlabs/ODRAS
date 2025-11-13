"""
RAG Context Models

Structured data models for RAG context that are LLM-agnostic.
These models represent retrieved knowledge chunks and their metadata
without any prompt formatting or LLM-specific concerns.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RAGSource(BaseModel):
    """Source document information for a RAG chunk."""
    
    source_id: str = Field(..., description="Unique identifier for the source document")
    source_type: str = Field(..., description="Type of source (project, training, system)")
    title: Optional[str] = Field(None, description="Title of the source document")
    file_id: Optional[str] = Field(None, description="File ID if from file storage")
    collection_id: Optional[str] = Field(None, description="Collection ID if applicable")
    collection_name: Optional[str] = Field(None, description="Collection name")
    project_id: Optional[str] = Field(None, description="Project ID if project-scoped")
    domain: Optional[str] = Field(None, description="Domain category (ontology, requirements, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source metadata")


class RAGChunk(BaseModel):
    """Individual knowledge chunk with content and metadata."""
    
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    content: str = Field(..., description="Full text content of the chunk")
    relevance_score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    source: RAGSource = Field(..., description="Source document information")
    sequence_number: Optional[int] = Field(None, description="Sequence number within source document")
    token_count: Optional[int] = Field(None, description="Approximate token count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "uuid-here",
                "content": "The system shall provide authentication...",
                "relevance_score": 0.85,
                "source": {
                    "source_id": "doc-uuid",
                    "source_type": "project",
                    "title": "Requirements Document",
                    "project_id": "proj-uuid"
                },
                "sequence_number": 5,
                "token_count": 150
            }
        }


class RAGContext(BaseModel):
    """Collection of RAG chunks with query metadata."""
    
    query: str = Field(..., description="Original query that generated this context")
    chunks: List[RAGChunk] = Field(default_factory=list, description="Retrieved knowledge chunks")
    total_chunks_found: int = Field(0, description="Total number of chunks found (may be more than returned)")
    query_metadata: Dict[str, Any] = Field(default_factory=dict, description="Query processing metadata")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="When context was retrieved")
    
    def get_chunks_by_source_type(self, source_type: str) -> List[RAGChunk]:
        """Filter chunks by source type."""
        return [chunk for chunk in self.chunks if chunk.source.source_type == source_type]
    
    def get_chunks_by_domain(self, domain: str) -> List[RAGChunk]:
        """Filter chunks by domain."""
        return [chunk for chunk in self.chunks if chunk.source.domain == domain]
    
    def get_top_chunks(self, top_k: int) -> List[RAGChunk]:
        """Get top K chunks by relevance score."""
        sorted_chunks = sorted(self.chunks, key=lambda c: c.relevance_score, reverse=True)
        return sorted_chunks[:top_k]
    
    def get_all_content(self) -> str:
        """Get all chunk content concatenated."""
        return "\n\n".join(chunk.content for chunk in self.chunks)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the authentication requirements?",
                "chunks": [
                    {
                        "chunk_id": "uuid-1",
                        "content": "The system shall provide authentication...",
                        "relevance_score": 0.85,
                        "source": {
                            "source_id": "doc-uuid",
                            "source_type": "project",
                            "title": "Requirements Document"
                        }
                    }
                ],
                "total_chunks_found": 5,
                "query_metadata": {
                    "similarity_threshold": 0.3,
                    "collections_searched": ["knowledge_chunks"]
                }
            }
        }
