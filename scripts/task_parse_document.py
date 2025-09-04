#!/usr/bin/env python3
"""
External Task Script: Parse Document Content
Extract text content from various document formats (PDF, DOCX, TXT, etc.)
"""

import json
import sys
import os
from typing import Dict, Any
import time
from pathlib import Path

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings


def parse_document(document_path: str, filename: str = None, mime_type: str = None) -> Dict[str, Any]:
    """
    Parse document content and extract text.
    
    Args:
        document_path: Path to the document file
        filename: Original filename (optional)
        mime_type: MIME type of document (optional)
        
    Returns:
        Dict containing parsed content and metadata
    """
    parse_result = {
        'parsed_content': '',
        'parsing_stats': {},
        'document_structure': {},
        'processing_status': 'success',
        'errors': []
    }
    
    start_time = time.time()
    
    try:
        if not os.path.exists(document_path):
            parse_result['processing_status'] = 'failure'
            parse_result['errors'].append(f"Document file not found: {document_path}")
            return parse_result
        
        file_path = Path(document_path)
        file_extension = file_path.suffix.lower()
        
        # Parse based on file type
        if file_extension == '.txt' or mime_type == 'text/plain':
            content = parse_text_file(document_path)
        elif file_extension == '.pdf' or mime_type == 'application/pdf':
            content = parse_pdf_file(document_path)
        elif file_extension in ['.docx', '.doc'] or 'word' in str(mime_type):
            content = parse_word_file(document_path)
        elif file_extension == '.md' or mime_type == 'text/markdown':
            content = parse_markdown_file(document_path)
        else:
            # Fallback to text parsing
            content = parse_text_file(document_path)
        
        if not content.strip():
            parse_result['processing_status'] = 'failure'
            parse_result['errors'].append("No content could be extracted from document")
            return parse_result
        
        parse_result['parsed_content'] = content
        
        # Calculate parsing statistics
        processing_time = time.time() - start_time
        word_count = len(content.split())
        char_count = len(content)
        line_count = len(content.split('\n'))
        
        parse_result['parsing_stats'] = {
            'processing_time_seconds': processing_time,
            'character_count': char_count,
            'word_count': word_count,
            'line_count': line_count,
            'file_size_bytes': os.path.getsize(document_path),
            'parser_used': get_parser_type(file_extension, mime_type)
        }
        
        # Basic document structure analysis
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        parse_result['document_structure'] = {
            'paragraph_count': len(paragraphs),
            'average_paragraph_length': sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            'has_headings': detect_headings(content),
            'has_lists': detect_lists(content),
            'estimated_reading_time_minutes': word_count / 200  # Average reading speed
        }
        
        print(f"Successfully parsed document: {filename or document_path}")
        print(f"Extracted {word_count} words, {char_count} characters")
        print(f"Processing time: {processing_time:.2f} seconds")
        
    except Exception as e:
        parse_result['processing_status'] = 'failure'
        parse_result['errors'].append(f"Document parsing error: {str(e)}")
        print(f"Document parsing failed: {str(e)}")
    
    return parse_result


def parse_text_file(file_path: str) -> str:
    """Parse plain text file."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # If all encodings fail, read as binary and decode with error handling
    with open(file_path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def parse_pdf_file(file_path: str) -> str:
    """Parse PDF file content."""
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            content = []
            for page in pdf_reader.pages:
                content.append(page.extract_text())
            return '\n'.join(content)
    except ImportError:
        # Fallback: try to read as text (won't work for real PDFs)
        return f"PDF parsing not available (PyPDF2 not installed): {file_path}"
    except Exception as e:
        raise Exception(f"PDF parsing failed: {str(e)}")


def parse_word_file(file_path: str) -> str:
    """Parse Word document content."""
    try:
        import docx
        doc = docx.Document(file_path)
        content = []
        for paragraph in doc.paragraphs:
            content.append(paragraph.text)
        return '\n'.join(content)
    except ImportError:
        # Fallback: try to read as text (won't work for real Word docs)
        return f"Word document parsing not available (python-docx not installed): {file_path}"
    except Exception as e:
        raise Exception(f"Word document parsing failed: {str(e)}")


def parse_markdown_file(file_path: str) -> str:
    """Parse Markdown file content."""
    # For now, treat as plain text
    # Could be enhanced to remove markdown formatting
    return parse_text_file(file_path)


def get_parser_type(file_extension: str, mime_type: str) -> str:
    """Determine which parser was used."""
    if file_extension == '.pdf' or mime_type == 'application/pdf':
        return 'pdf_parser'
    elif file_extension in ['.docx', '.doc'] or 'word' in str(mime_type):
        return 'word_parser'
    elif file_extension == '.md' or mime_type == 'text/markdown':
        return 'markdown_parser'
    else:
        return 'text_parser'


def detect_headings(content: str) -> bool:
    """Detect if content has heading structures."""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        # Check for markdown headings
        if line.startswith('#'):
            return True
        # Check for underlined headings
        if len(line) > 0 and len(line) < 100:
            next_line_idx = lines.index(line) + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if next_line and all(c in '=-_' for c in next_line):
                    return True
    return False


def detect_lists(content: str) -> bool:
    """Detect if content has list structures."""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        # Check for markdown lists
        if line.startswith(('- ', '* ', '+ ')) or (len(line) > 2 and line[0].isdigit() and line[1:3] == '. '):
            return True
    return False


def main():
    """Main function for testing."""
    if len(sys.argv) > 1:
        document_path = sys.argv[1]
        filename = os.path.basename(document_path)
        
        result = parse_document(document_path, filename)
        print(json.dumps(result, indent=2))
        return result
    
    return {
        'parsed_content': 'Sample parsed content',
        'parsing_stats': {'word_count': 3},
        'document_structure': {'paragraph_count': 1},
        'processing_status': 'success',
        'errors': []
    }


if __name__ == "__main__":
    main()




