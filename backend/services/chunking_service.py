"""
Chunking Service for Knowledge Management.

Provides text chunking capabilities including:
- Fixed-size chunking with overlap
- Semantic chunking (sentence/paragraph boundaries)
- Hybrid chunking strategies
- Document structure preservation
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
    
    # Download required NLTK data if not already present
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    sent_tokenize = None
    word_tokenize = None

from .config import Settings

logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    chunk_id: str
    sequence_number: int
    chunk_type: str  # text, title, header, list, table, code
    start_char: int
    end_char: int
    token_count: int
    sentence_count: int
    confidence_score: float
    section_path: Optional[str] = None
    page_number: Optional[int] = None
    cross_references: List[str] = None
    extracted_entities: Dict[str, List[str]] = None

@dataclass
class DocumentChunk:
    """A document chunk with content and metadata."""
    content: str
    metadata: ChunkMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary representation."""
        return {
            'content': self.content,
            'chunk_id': self.metadata.chunk_id,
            'sequence_number': self.metadata.sequence_number,
            'chunk_type': self.metadata.chunk_type,
            'start_char': self.metadata.start_char,
            'end_char': self.metadata.end_char,
            'token_count': self.metadata.token_count,
            'sentence_count': self.metadata.sentence_count,
            'confidence_score': self.metadata.confidence_score,
            'section_path': self.metadata.section_path,
            'page_number': self.metadata.page_number,
            'cross_references': self.metadata.cross_references or [],
            'extracted_entities': self.metadata.extracted_entities or {}
        }

class ChunkingService:
    """
    Service for chunking documents into semantically meaningful segments.
    
    Supports multiple chunking strategies with configurable parameters
    and document structure awareness.
    """
    
    def __init__(self, settings: Settings = None):
        """Initialize chunking service with configuration."""
        self.settings = settings or Settings()
        
        # Default chunking parameters
        self.default_config = {
            'chunk_size': 512,  # Target chunk size in tokens
            'chunk_overlap': 50,  # Overlap between chunks in tokens
            'min_chunk_size': 50,  # Minimum viable chunk size
            'max_chunk_size': 1024,  # Maximum chunk size
            'strategy': 'hybrid',  # fixed, semantic, hybrid
            'preserve_structure': True,  # Try to preserve document structure
            'split_on_sentence': True,  # Prefer sentence boundaries
            'extract_entities': False,  # Extract named entities (requires NLP models)
            'confidence_threshold': 0.7  # Minimum confidence for semantic splits
        }
        
        logger.info("Chunking service initialized")
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text using simple heuristics.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple approximation: ~4 characters per token for English text
        # This is rough but sufficient for chunking decisions
        if NLTK_AVAILABLE and word_tokenize:
            try:
                tokens = word_tokenize(text)
                return len(tokens)
            except:
                pass
        
        # Fallback: character-based estimation
        return max(1, len(text) // 4)
    
    def extract_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Extract sentences with their character positions.
        
        Args:
            text: Input text
            
        Returns:
            List of (sentence, start_pos, end_pos) tuples
        """
        sentences = []
        
        if NLTK_AVAILABLE and sent_tokenize:
            try:
                # Use NLTK sentence tokenizer
                sentence_spans = list(sent_tokenize(text, language='english'))
                
                # Find character positions
                current_pos = 0
                for sentence in sentence_spans:
                    start_pos = text.find(sentence, current_pos)
                    if start_pos >= 0:
                        end_pos = start_pos + len(sentence)
                        sentences.append((sentence, start_pos, end_pos))
                        current_pos = end_pos
                    
                return sentences
            except:
                logger.warning("NLTK sentence tokenization failed, falling back to regex")
        
        # Fallback: regex-based sentence splitting
        sentence_pattern = r'(?<=[.!?])\s+'
        sentence_parts = re.split(sentence_pattern, text)
        
        current_pos = 0
        for part in sentence_parts:
            if part.strip():
                start_pos = text.find(part, current_pos)
                if start_pos >= 0:
                    end_pos = start_pos + len(part)
                    sentences.append((part, start_pos, end_pos))
                    current_pos = end_pos
        
        return sentences
    
    def detect_document_structure(self, text: str) -> Dict[str, Any]:
        """
        Detect document structure elements like headers, lists, etc.
        
        Args:
            text: Input document text
            
        Returns:
            Structure information dictionary
        """
        structure = {
            'headers': [],
            'lists': [],
            'tables': [],
            'code_blocks': [],
            'paragraphs': []
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detect headers (markdown style)
            if re.match(r'^#{1,6}\s+', line_stripped):
                level = len(line_stripped) - len(line_stripped.lstrip('#'))
                header_text = line_stripped.lstrip('# ').strip()
                structure['headers'].append({
                    'line_number': i,
                    'level': level,
                    'text': header_text,
                    'char_start': text.find(line),
                    'char_end': text.find(line) + len(line)
                })
            
            # Detect lists (basic patterns)
            elif re.match(r'^\s*[-*+]\s+', line_stripped) or re.match(r'^\s*\d+\.\s+', line_stripped):
                structure['lists'].append({
                    'line_number': i,
                    'text': line_stripped,
                    'char_start': text.find(line),
                    'char_end': text.find(line) + len(line)
                })
            
            # Detect potential code blocks (indented or fenced)
            elif line.startswith('    ') or line_stripped.startswith('```'):
                structure['code_blocks'].append({
                    'line_number': i,
                    'text': line_stripped,
                    'char_start': text.find(line),
                    'char_end': text.find(line) + len(line)
                })
        
        return structure
    
    def chunk_fixed_size(
        self, 
        text: str, 
        chunk_size: int = 512,
        overlap: int = 50,
        preserve_sentences: bool = True
    ) -> List[DocumentChunk]:
        """
        Chunk text using fixed-size strategy with optional overlap.
        
        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in tokens
            overlap: Overlap size in tokens
            preserve_sentences: Try to split at sentence boundaries
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        if not text.strip():
            return chunks
        
        # Get sentences if preserving boundaries
        sentences = self.extract_sentences(text) if preserve_sentences else [(text, 0, len(text))]
        
        current_chunk = ""
        current_start = 0
        chunk_sentences = []
        sequence_number = 0
        
        for sentence, sent_start, sent_end in sentences:
            # Estimate tokens in current chunk + this sentence
            potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
            potential_tokens = self.estimate_token_count(potential_chunk)
            
            # If adding this sentence exceeds chunk size, finalize current chunk
            if potential_tokens > chunk_size and current_chunk:
                # Create chunk from current content
                chunk_end = chunk_sentences[-1][2] if chunk_sentences else current_start + len(current_chunk)
                
                chunks.append(DocumentChunk(
                    content=current_chunk.strip(),
                    metadata=ChunkMetadata(
                        chunk_id=str(uuid4()),
                        sequence_number=sequence_number,
                        chunk_type='text',
                        start_char=current_start,
                        end_char=chunk_end,
                        token_count=self.estimate_token_count(current_chunk),
                        sentence_count=len(chunk_sentences),
                        confidence_score=1.0  # Fixed size chunks have high confidence
                    )
                ))
                
                sequence_number += 1
                
                # Start new chunk with overlap
                if overlap > 0 and chunk_sentences:
                    # Keep last few sentences for overlap
                    overlap_sentences = chunk_sentences[-overlap//10:] if len(chunk_sentences) > overlap//10 else chunk_sentences
                    current_chunk = " ".join([s[0] for s in overlap_sentences])
                    current_start = overlap_sentences[0][1]
                    chunk_sentences = overlap_sentences[:]
                else:
                    current_chunk = ""
                    current_start = sent_start
                    chunk_sentences = []
            
            # Add current sentence to chunk
            current_chunk += (" " if current_chunk else "") + sentence
            chunk_sentences.append((sentence, sent_start, sent_end))
            
            if not current_chunk:
                current_start = sent_start
        
        # Handle remaining content
        if current_chunk.strip():
            chunk_end = chunk_sentences[-1][2] if chunk_sentences else current_start + len(current_chunk)
            
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                metadata=ChunkMetadata(
                    chunk_id=str(uuid4()),
                    sequence_number=sequence_number,
                    chunk_type='text',
                    start_char=current_start,
                    end_char=chunk_end,
                    token_count=self.estimate_token_count(current_chunk),
                    sentence_count=len(chunk_sentences),
                    confidence_score=1.0
                )
            ))
        
        logger.info(f"Created {len(chunks)} fixed-size chunks from {len(text)} characters")
        return chunks
    
    def chunk_semantic(
        self, 
        text: str,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        confidence_threshold: float = 0.7
    ) -> List[DocumentChunk]:
        """
        Chunk text using semantic boundaries (paragraphs, sections, etc.).
        
        Args:
            text: Input text to chunk
            min_chunk_size: Minimum chunk size in tokens
            max_chunk_size: Maximum chunk size in tokens
            confidence_threshold: Minimum confidence for semantic splits
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        if not text.strip():
            return chunks
        
        # Detect document structure
        structure = self.detect_document_structure(text)
        
        # Split by paragraphs as primary semantic unit
        paragraphs = re.split(r'\n\s*\n', text)
        
        sequence_number = 0
        current_position = 0
        
        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                current_position = text.find('\n\n', current_position) + 2
                continue
            
            para_start = text.find(para_text, current_position)
            para_end = para_start + len(para_text)
            para_tokens = self.estimate_token_count(para_text)
            
            # Determine chunk type based on structure
            chunk_type = 'text'
            confidence = 0.8  # Base confidence for paragraph-based splitting
            
            # Check if this paragraph contains structure elements
            for header in structure['headers']:
                if header['char_start'] >= para_start and header['char_end'] <= para_end:
                    chunk_type = 'title'
                    confidence = 0.95
                    break
            
            for code_block in structure['code_blocks']:
                if code_block['char_start'] >= para_start and code_block['char_end'] <= para_end:
                    chunk_type = 'code'
                    confidence = 0.9
                    break
            
            # Handle different sized paragraphs
            if para_tokens <= max_chunk_size and para_tokens >= min_chunk_size:
                # Perfect size - use as single chunk
                chunks.append(DocumentChunk(
                    content=para_text,
                    metadata=ChunkMetadata(
                        chunk_id=str(uuid4()),
                        sequence_number=sequence_number,
                        chunk_type=chunk_type,
                        start_char=para_start,
                        end_char=para_end,
                        token_count=para_tokens,
                        sentence_count=len(self.extract_sentences(para_text)),
                        confidence_score=confidence
                    )
                ))
                sequence_number += 1
                
            elif para_tokens > max_chunk_size:
                # Too large - split further using sentence boundaries
                sub_chunks = self.chunk_fixed_size(
                    para_text, 
                    chunk_size=max_chunk_size,
                    overlap=0,
                    preserve_sentences=True
                )
                
                for sub_chunk in sub_chunks:
                    # Adjust positions relative to original text
                    sub_chunk.metadata.start_char += para_start
                    sub_chunk.metadata.end_char += para_start
                    sub_chunk.metadata.sequence_number = sequence_number
                    sub_chunk.metadata.chunk_type = chunk_type
                    sub_chunk.metadata.confidence_score = confidence * 0.8  # Lower confidence for forced splits
                    chunks.append(sub_chunk)
                    sequence_number += 1
                    
            else:
                # Too small - could merge with adjacent paragraphs (simplified approach: keep as-is)
                if para_tokens >= min_chunk_size // 2:  # Keep if not too tiny
                    chunks.append(DocumentChunk(
                        content=para_text,
                        metadata=ChunkMetadata(
                            chunk_id=str(uuid4()),
                            sequence_number=sequence_number,
                            chunk_type=chunk_type,
                            start_char=para_start,
                            end_char=para_end,
                            token_count=para_tokens,
                            sentence_count=len(self.extract_sentences(para_text)),
                            confidence_score=confidence * 0.6  # Lower confidence for small chunks
                        )
                    ))
                    sequence_number += 1
            
            current_position = para_end
        
        logger.info(f"Created {len(chunks)} semantic chunks from {len(text)} characters")
        return chunks
    
    def chunk_hybrid(
        self,
        text: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text using hybrid strategy (semantic first, fixed-size fallback).
        
        Args:
            text: Input text to chunk
            config: Chunking configuration parameters
            
        Returns:
            List of DocumentChunk objects
        """
        # Merge with default config
        chunk_config = {**self.default_config, **(config or {})}
        
        if not text.strip():
            return []
        
        # Try semantic chunking first
        try:
            semantic_chunks = self.chunk_semantic(
                text,
                min_chunk_size=chunk_config['min_chunk_size'],
                max_chunk_size=chunk_config['max_chunk_size'],
                confidence_threshold=chunk_config['confidence_threshold']
            )
            
            # Check if semantic chunking produced reasonable results
            if semantic_chunks:
                total_chars = sum(chunk.metadata.end_char - chunk.metadata.start_char for chunk in semantic_chunks)
                coverage = total_chars / len(text) if text else 0
                
                if coverage > 0.8:  # Good coverage, use semantic chunks
                    logger.info(f"Using semantic chunking strategy with {len(semantic_chunks)} chunks")
                    return semantic_chunks
            
        except Exception as e:
            logger.warning(f"Semantic chunking failed, falling back to fixed-size: {str(e)}")
        
        # Fallback to fixed-size chunking
        logger.info("Falling back to fixed-size chunking strategy")
        return self.chunk_fixed_size(
            text,
            chunk_size=chunk_config['chunk_size'],
            overlap=chunk_config['chunk_overlap'],
            preserve_sentences=chunk_config['split_on_sentence']
        )
    
    def chunk_document(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        chunking_config: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Main chunking interface for documents.
        
        Args:
            text: Input document text
            document_metadata: Optional document metadata (filename, type, etc.)
            chunking_config: Optional chunking configuration
            
        Returns:
            List of DocumentChunk objects
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for chunking")
                return []
            
            # Merge configurations
            config = {**self.default_config, **(chunking_config or {})}
            
            # Choose chunking strategy
            strategy = config.get('strategy', 'hybrid')
            
            if strategy == 'fixed':
                chunks = self.chunk_fixed_size(
                    text,
                    chunk_size=config['chunk_size'],
                    overlap=config['chunk_overlap'],
                    preserve_sentences=config['split_on_sentence']
                )
            elif strategy == 'semantic':
                chunks = self.chunk_semantic(
                    text,
                    min_chunk_size=config['min_chunk_size'],
                    max_chunk_size=config['max_chunk_size'],
                    confidence_threshold=config['confidence_threshold']
                )
            else:  # hybrid
                chunks = self.chunk_hybrid(text, config)
            
            # Add document metadata to chunks if provided
            if document_metadata:
                for chunk in chunks:
                    if 'filename' in document_metadata:
                        chunk.metadata.section_path = document_metadata['filename']
                    if 'page_number' in document_metadata:
                        chunk.metadata.page_number = document_metadata['page_number']
            
            logger.info(f"Chunked document into {len(chunks)} chunks using {strategy} strategy")
            return chunks
            
        except Exception as e:
            logger.error(f"Document chunking failed: {str(e)}")
            raise RuntimeError(f"Chunking failed: {str(e)}")
    
    def get_chunking_stats(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Get statistics about a set of chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {'total_chunks': 0}
        
        token_counts = [chunk.metadata.token_count for chunk in chunks]
        chunk_types = [chunk.metadata.chunk_type for chunk in chunks]
        confidences = [chunk.metadata.confidence_score for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'avg_tokens_per_chunk': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'chunk_types': {t: chunk_types.count(t) for t in set(chunk_types)},
            'avg_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences)
        }

# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_chunking_service(settings: Settings = None) -> ChunkingService:
    """Get configured chunking service instance."""
    return ChunkingService(settings)

def chunk_text_simple(
    text: str, 
    chunk_size: int = 512,
    overlap: int = 50,
    strategy: str = 'hybrid'
) -> List[Dict[str, Any]]:
    """
    Simple utility function to chunk text and return dictionaries.
    
    Args:
        text: Input text
        chunk_size: Target chunk size in tokens
        overlap: Overlap size in tokens
        strategy: Chunking strategy (fixed, semantic, hybrid)
        
    Returns:
        List of chunk dictionaries
    """
    service = get_chunking_service()
    config = {
        'chunk_size': chunk_size,
        'chunk_overlap': overlap,
        'strategy': strategy
    }
    
    chunks = service.chunk_document(text, chunking_config=config)
    return [chunk.to_dict() for chunk in chunks]
