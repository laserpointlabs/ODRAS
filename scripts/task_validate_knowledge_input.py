#!/usr/bin/env python3
"""
External Task Script: Validate Knowledge Input for Add to Knowledge Process
This script is called by Camunda BPMN process to validate knowledge input.

Input Variables (from Camunda):
- knowledge_content: Raw knowledge content (text, JSON, etc.)
- knowledge_format: Format of knowledge (text, json, structured)
- knowledge_metadata: Associated metadata (source, author, tags, etc.)

Output Variables (set in Camunda):
- input_validation_result: 'valid' or 'invalid'
- validation_feedback: List of validation messages and suggestions
- processed_knowledge: Cleaned and structured knowledge data
"""

import json
import sys
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the backend directory to the path so we can import our services  
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings


def validate_knowledge_input(
    content: str, 
    format_type: str = 'text', 
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Validate knowledge input for addition to knowledge base.
    
    Args:
        content: Raw knowledge content
        format_type: Format of knowledge ('text', 'json', 'structured')
        metadata: Associated metadata
        
    Returns:
        Dict containing validation results and processed knowledge
    """
    validation_result = {
        'input_validation_result': 'valid',
        'validation_feedback': [],
        'processed_knowledge': {},
        'quality_scores': {}
    }
    
    if metadata is None:
        metadata = {}
    
    try:
        # Basic content validation
        if not content or not content.strip():
            validation_result['input_validation_result'] = 'invalid'
            validation_result['validation_feedback'].append(
                "Knowledge content cannot be empty"
            )
            return validation_result
        
        # Check minimum content length
        min_length = 10  # Minimum 10 characters
        if len(content.strip()) < min_length:
            validation_result['input_validation_result'] = 'invalid'
            validation_result['validation_feedback'].append(
                f"Knowledge content too short (minimum {min_length} characters)"
            )
            return validation_result
        
        # Check maximum content length
        max_length = 100000  # Maximum 100k characters
        if len(content) > max_length:
            validation_result['input_validation_result'] = 'invalid'
            validation_result['validation_feedback'].append(
                f"Knowledge content too long (maximum {max_length} characters)"
            )
            return validation_result
        
        # Validate format-specific requirements
        processed_content = content
        
        if format_type == 'json':
            try:
                json_data = json.loads(content)
                processed_content = json_data
                validation_result['validation_feedback'].append("Valid JSON format detected")
            except json.JSONDecodeError as e:
                validation_result['input_validation_result'] = 'invalid'
                validation_result['validation_feedback'].append(f"Invalid JSON format: {str(e)}")
                return validation_result
        
        # Content quality checks
        quality_scores = {}
        
        # Check for meaningful content (not just whitespace/punctuation)
        meaningful_chars = re.sub(r'[\s\W]', '', content)
        if len(meaningful_chars) < 5:
            validation_result['input_validation_result'] = 'invalid'
            validation_result['validation_feedback'].append(
                "Content lacks meaningful information"
            )
            return validation_result
        
        # Calculate readability score (simple version)
        words = len(content.split())
        sentences = len(re.split(r'[.!?]+', content))
        avg_words_per_sentence = words / max(sentences, 1)
        quality_scores['word_count'] = words
        quality_scores['sentence_count'] = sentences
        quality_scores['avg_words_per_sentence'] = avg_words_per_sentence
        
        # Check for extremely long sentences (readability issue)
        if avg_words_per_sentence > 50:
            validation_result['validation_feedback'].append(
                "Content has very long sentences, consider breaking them down for better readability"
            )
        
        # Validate required metadata fields
        required_fields = ['title', 'source']
        missing_fields = []
        
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result['validation_feedback'].append(
                f"Missing required metadata fields: {', '.join(missing_fields)}"
            )
            # Don't fail validation, but provide feedback
        
        # Validate metadata values
        if 'title' in metadata:
            title = metadata['title'].strip()
            if len(title) < 5:
                validation_result['validation_feedback'].append(
                    "Title should be at least 5 characters long"
                )
            elif len(title) > 200:
                validation_result['validation_feedback'].append(
                    "Title is too long (maximum 200 characters)"
                )
        
        # Check for potential sensitive information (basic patterns)
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email pattern
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, content):
                validation_result['validation_feedback'].append(
                    "Content may contain sensitive information - please review"
                )
                break
        
        # Structure the processed knowledge
        validation_result['processed_knowledge'] = {
            'content': processed_content,
            'format': format_type,
            'metadata': {
                **metadata,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'content_stats': {
                    'character_count': len(content),
                    'word_count': words,
                    'sentence_count': sentences
                }
            },
            'quality_indicators': {
                'length_appropriate': min_length <= len(content) <= max_length,
                'has_meaningful_content': len(meaningful_chars) >= 5,
                'readability_acceptable': avg_words_per_sentence <= 50
            }
        }
        
        validation_result['quality_scores'] = quality_scores
        
        print(f"Knowledge input validation successful")
        print(f"Content length: {len(content)} characters")
        print(f"Word count: {words}")
        print(f"Format: {format_type}")
        
    except Exception as e:
        validation_result['input_validation_result'] = 'invalid'
        validation_result['validation_feedback'].append(f"Validation error: {str(e)}")
        print(f"Knowledge validation failed: {str(e)}")
    
    return validation_result


def main():
    """
    Main function for Camunda external task execution.
    Reads process variables and returns validation results.
    """
    # For testing, use command line arguments
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            # If argument is a file path, read the content
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                content = f.read()
            format_type = sys.argv[2] if len(sys.argv) > 2 else 'text'
        else:
            # If argument is direct content
            content = sys.argv[1]
            format_type = sys.argv[2] if len(sys.argv) > 2 else 'text'
        
        metadata = {
            'title': 'Test Knowledge',
            'source': 'CLI Test',
            'author': 'System'
        }
        
        result = validate_knowledge_input(content, format_type, metadata)
        print(json.dumps(result, indent=2))
        return result
    
    # In production, this would be called by Camunda with process variables
    return {
        'input_validation_result': 'valid',
        'validation_feedback': ['Sample validation successful'],
        'processed_knowledge': {'status': 'processed'},
        'quality_scores': {'test_score': 100}
    }


if __name__ == "__main__":
    main()




