#!/usr/bin/env python3
"""
External Task Script: Process User Query
Extract intent, key terms, and prepare query for retrieval.
"""

import json
import sys
import os
import re
from typing import Dict, Any, List
import time

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings


def process_user_query(query: str, query_metadata: Dict = None) -> Dict[str, Any]:
    """
    Process and understand user query intent.
    
    Args:
        query: Raw user query string
        query_metadata: Additional query context (user_id, session_id, etc.)
        
    Returns:
        Dict containing processed query information
    """
    result = {
        'processed_query': {},
        'query_analysis': {},
        'search_parameters': {},
        'processing_status': 'success',
        'errors': []
    }
    
    if query_metadata is None:
        query_metadata = {}
    
    try:
        # Clean the query
        cleaned_query = query.strip()
        if not cleaned_query:
            result['processing_status'] = 'failure'
            result['errors'].append("Empty query provided")
            return result
        
        # Basic query analysis
        word_count = len(cleaned_query.split())
        char_count = len(cleaned_query)
        
        # Extract key terms (simple approach - remove stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must'}
        
        words = re.findall(r'\b\w+\b', cleaned_query.lower())
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Classify query type
        query_type = classify_query_type(cleaned_query)
        
        # Detect question intent
        question_patterns = {
            'what': r'\bwhat\b',
            'how': r'\bhow\b',
            'why': r'\bwhy\b',
            'when': r'\bwhen\b',
            'where': r'\bwhere\b',
            'who': r'\bwho\b',
            'which': r'\bwhich\b'
        }
        
        question_intent = []
        for intent, pattern in question_patterns.items():
            if re.search(pattern, cleaned_query.lower()):
                question_intent.append(intent)
        
        # Extract domain-specific terms (requirements, system, etc.)
        domain_terms = extract_domain_terms(cleaned_query)
        
        # Build processed query
        result['processed_query'] = {
            'original_query': query,
            'cleaned_query': cleaned_query,
            'key_terms': key_terms,
            'question_intent': question_intent,
            'query_type': query_type,
            'domain_terms': domain_terms,
            'word_count': word_count,
            'char_count': char_count,
            'query_metadata': query_metadata,
            'processing_timestamp': time.time()
        }
        
        # Query analysis metrics
        result['query_analysis'] = {
            'complexity_score': calculate_complexity_score(cleaned_query, key_terms),
            'specificity_score': calculate_specificity_score(key_terms, domain_terms),
            'question_confidence': len(question_intent) / len(question_patterns),
            'has_technical_terms': len(domain_terms) > 0,
            'estimated_answer_type': estimate_answer_type(query_type, question_intent)
        }
        
        # Search parameters for retrieval
        result['search_parameters'] = {
            'primary_terms': key_terms[:5],  # Top 5 key terms
            'secondary_terms': key_terms[5:10] if len(key_terms) > 5 else [],
            'search_boost_terms': domain_terms,
            'semantic_search_weight': 0.7,
            'keyword_search_weight': 0.3,
            'min_similarity_threshold': 0.6,
            'max_results': 20,
            'rerank_top_k': 10
        }
        
        print(f"Processed user query successfully")
        print(f"Key terms: {key_terms[:5]}")
        print(f"Query type: {query_type}")
        print(f"Question intent: {question_intent}")
        
    except Exception as e:
        result['processing_status'] = 'failure'
        result['errors'].append(f"Query processing error: {str(e)}")
        print(f"Query processing failed: {str(e)}")
    
    return result


def classify_query_type(query: str) -> str:
    """Classify the type of query."""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['define', 'definition', 'what is', 'what are']):
        return 'definition'
    elif any(word in query_lower for word in ['how to', 'how do', 'how can', 'steps', 'process']):
        return 'procedural'
    elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
        return 'comparison'
    elif any(word in query_lower for word in ['list', 'enumerate', 'show me', 'give me']):
        return 'enumeration'
    elif '?' in query:
        return 'question'
    else:
        return 'informational'


def extract_domain_terms(query: str) -> List[str]:
    """Extract domain-specific terms from the query."""
    domain_keywords = [
        # Requirements terms
        'requirement', 'requirements', 'shall', 'must', 'should', 'specification',
        'constraint', 'functional', 'non-functional', 'performance',
        # System terms  
        'system', 'component', 'interface', 'architecture', 'design',
        'implementation', 'module', 'service', 'api',
        # Process terms
        'process', 'workflow', 'procedure', 'methodology', 'framework',
        'pipeline', 'integration', 'deployment',
        # Quality terms
        'quality', 'testing', 'validation', 'verification', 'compliance',
        'security', 'reliability', 'scalability', 'maintainability'
    ]
    
    query_words = re.findall(r'\b\w+\b', query.lower())
    found_terms = [word for word in query_words if word in domain_keywords]
    return list(set(found_terms))  # Remove duplicates


def calculate_complexity_score(query: str, key_terms: List[str]) -> float:
    """Calculate query complexity score (0-1)."""
    # Factors: length, technical terms, sentence structure
    length_score = min(len(query) / 200, 1.0)  # Normalize to max 200 chars
    term_score = min(len(key_terms) / 10, 1.0)  # Normalize to max 10 terms
    structure_score = 0.5 if '?' in query or any(word in query.lower() for word in ['and', 'or', 'but']) else 0.3
    
    return (length_score + term_score + structure_score) / 3


def calculate_specificity_score(key_terms: List[str], domain_terms: List[str]) -> float:
    """Calculate query specificity score (0-1)."""
    if not key_terms:
        return 0.0
    
    domain_ratio = len(domain_terms) / len(key_terms) if key_terms else 0
    term_diversity = len(set(key_terms)) / len(key_terms) if key_terms else 0
    
    return (domain_ratio + term_diversity) / 2


def estimate_answer_type(query_type: str, question_intent: List[str]) -> str:
    """Estimate what type of answer the user expects."""
    if query_type == 'definition':
        return 'explanation'
    elif query_type == 'procedural':
        return 'step_by_step'
    elif query_type == 'comparison':
        return 'comparative_analysis'
    elif query_type == 'enumeration':
        return 'list_format'
    elif 'how' in question_intent:
        return 'instructional'
    elif 'what' in question_intent:
        return 'descriptive'
    elif 'why' in question_intent:
        return 'explanatory'
    else:
        return 'informational'


def main():
    """Main function for testing."""
    if len(sys.argv) > 1:
        query = sys.argv[1]
        metadata = {}
        
        if len(sys.argv) > 2:
            try:
                metadata = json.loads(sys.argv[2])
            except:
                metadata = {'user_context': sys.argv[2]}
        
        result = process_user_query(query, metadata)
        print(json.dumps(result, indent=2, default=str))
        return result
    
    return {
        'processed_query': {'original_query': 'test query'},
        'query_analysis': {'complexity_score': 0.5},
        'search_parameters': {'primary_terms': ['test']},
        'processing_status': 'success',
        'errors': []
    }


if __name__ == "__main__":
    main()




