"""
DAS Prompt Builder

Pure service for building prompts from RAG context.
This service is decoupled from RAG and handles prompt formatting
for different styles and use cases.
"""

from typing import List, Optional
from backend.rag.core.context_models import RAGContext, RAGChunk


class DASPromptBuilder:
    """
    Builds prompts from RAG context for DAS.
    
    This service is responsible for formatting RAG context into
    prompts that can be sent to LLMs. It supports different
    prompt styles and handles source citations.
    """
    
    @staticmethod
    def build_prompt(
        rag_context: RAGContext,
        user_query: str,
        style: str = "comprehensive",
        include_sources: bool = True,
        max_chunks: Optional[int] = None,
    ) -> str:
        """
        Build a prompt from RAG context.
        
        Args:
            rag_context: RAG context containing retrieved chunks
            user_query: User's original query
            style: Prompt style ("comprehensive", "concise", "technical")
            include_sources: Whether to include source citations
            max_chunks: Maximum number of chunks to include (None for all)
        
        Returns:
            Formatted prompt string
        """
        if not rag_context.chunks:
            return DASPromptBuilder._build_empty_context_prompt(user_query)
        
        # Select chunks to include
        chunks_to_include = rag_context.chunks
        if max_chunks:
            chunks_to_include = rag_context.get_top_chunks(max_chunks)
        
        # Build context section
        context_section = DASPromptBuilder._build_context_section(
            chunks_to_include,
            include_sources=include_sources
        )
        
        # Build system prompt based on style
        system_prompt = DASPromptBuilder._get_system_prompt(style)
        
        # Combine into final prompt
        prompt = f"""{system_prompt}

CONTEXT FROM KNOWLEDGE BASE:
{context_section}

USER QUESTION: {user_query}

Please provide a helpful answer based on the context above. {"Include source citations when referencing specific information." if include_sources else ""}
"""
        return prompt
    
    @staticmethod
    def _build_context_section(
        chunks: List[RAGChunk],
        include_sources: bool = True,
    ) -> str:
        """Build the context section from chunks."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            source_info = ""
            if include_sources:
                source_parts = []
                if chunk.source.title:
                    source_parts.append(f"Title: {chunk.source.title}")
                if chunk.source.domain:
                    source_parts.append(f"Domain: {chunk.source.domain}")
                if chunk.source.source_type:
                    source_parts.append(f"Type: {chunk.source.source_type}")
                
                if source_parts:
                    source_info = f" [Source: {', '.join(source_parts)}]"
            
            context_parts.append(
                f"[Context {i}]{source_info}\n{chunk.content}"
            )
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def _get_system_prompt(style: str) -> str:
        """Get system prompt based on style."""
        prompts = {
            "comprehensive": """You are a knowledgeable assistant helping users understand information from their knowledge base.
Provide comprehensive, well-structured answers using the provided context.
Include relevant details and explain concepts clearly.
Always ground your response in the provided context.""",
            
            "concise": """You are a helpful assistant providing concise, direct answers.
Give brief, to-the-point responses using only the most relevant information.
Be clear and avoid unnecessary elaboration.""",
            
            "technical": """You are a technical expert providing detailed technical responses.
Include specific technical details, specifications, and implementation notes.
Use precise terminology and provide actionable information.""",
        }
        
        return prompts.get(style, prompts["comprehensive"])
    
    @staticmethod
    def _build_empty_context_prompt(user_query: str) -> str:
        """Build prompt when no context is available."""
        return f"""You are a helpful assistant.

USER QUESTION: {user_query}

I couldn't find any relevant information in the knowledge base to answer your question.
Please provide a general response or suggest how the user might refine their question.
"""
    
    @staticmethod
    def build_context_summary(rag_context: RAGContext) -> str:
        """
        Build a summary of the RAG context for logging/debugging.
        
        Args:
            rag_context: RAG context to summarize
        
        Returns:
            Summary string
        """
        if not rag_context.chunks:
            return "No chunks retrieved"
        
        source_types = {}
        domains = {}
        
        for chunk in rag_context.chunks:
            source_type = chunk.source.source_type or "unknown"
            source_types[source_type] = source_types.get(source_type, 0) + 1
            
            if chunk.source.domain:
                domains[chunk.source.domain] = domains.get(chunk.source.domain, 0) + 1
        
        summary_parts = [
            f"Total chunks: {len(rag_context.chunks)}",
            f"Source types: {dict(source_types)}",
        ]
        
        if domains:
            summary_parts.append(f"Domains: {dict(domains)}")
        
        return "; ".join(summary_parts)
