#!/usr/bin/env python3
"""
External Task Script: Store Results in Vector Database
This script is called by Camunda BPMN process to store processed requirements in Qdrant.

Input Variables (from Camunda):
- processed_requirements: JSON string of processed requirements with LLM results

Output Variables (set in Camunda):
- vector_store_status: JSON string of vector storage status and metadata
"""

import json
import time
import sys
import os
from typing import Dict, List, Any

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings
from services.persistence import PersistenceLayer
from services.embeddings import SimpleHasherEmbedder


def store_results_in_vector_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Qdrant vector database.
    
    Args:
        processed_requirements: List of processed requirements with LLM results
        
    Returns:
        Dict containing vector store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)
    embedder = SimpleHasherEmbedder()
    
    vector_store_status = {
        'database': 'Qdrant',
        'collections_created': 0,
        'vectors_stored': 0,
        'status': 'success',
        'errors': [],
        'metadata': {}
    }
    
    storage_start_time = time.time()
    
    try:
        # Create collection if it doesn't exist
        collection_name = f"odras_requirements_{int(time.time())}"
        vector_store_status['collections_created'] = 1
        vector_store_status['metadata']['collection_name'] = collection_name
        
        print(f"Creating collection: {collection_name}")
        
        # Prepare vectors and payloads
        vectors = []
        payloads = []
        
        for req_idx, req in enumerate(processed_requirements):
            print(f"Processing requirement {req_idx + 1}/{len(processed_requirements)}: {req['original_requirement']['id']}")
            
            for iter_idx, iteration in enumerate(req['iterations']):
                if iteration['status'] == 'success':
                    # Create embedding for the requirement text
                    text = iteration['requirement_text']
                    vector = embedder.embed([text])[0]
                    
                    # Prepare comprehensive payload
                    payload = {
                        'id': f"{iteration['requirement_id']}_{iteration['iteration']}",
                        'requirement_text': text,
                        'requirement_id': iteration['requirement_id'],
                        'requirement_category': req['original_requirement'].get('category', 'Unknown'),
                        'llm_response': iteration['llm_response'],
                        'provider': iteration['provider'],
                        'model': iteration['model'],
                        'confidence': iteration['confidence'],
                        'iteration_number': iteration['iteration'],
                        'timestamp': iteration['processing_time'],
                        'collection': collection_name,
                        'source_file': req['original_requirement'].get('source_file', 'Unknown'),
                        'extraction_confidence': req['original_requirement'].get('extraction_confidence', 0.0),
                        'processing_metadata': {
                            'total_processing_time': req.get('total_processing_time', 0.0),
                            'success_rate': req.get('success_rate', 0.0),
                            'average_confidence': req.get('average_confidence', 0.0)
                        }
                    }
                    
                    # Add extracted entities if available
                    if 'extracted_entities' in iteration['llm_response']:
                        payload['extracted_entities'] = iteration['llm_response']['extracted_entities']
                    
                    # Add constraints if available
                    if 'constraints' in iteration['llm_response']:
                        payload['constraints'] = iteration['llm_response']['constraints']
                    
                    # Add dependencies if available
                    if 'dependencies' in iteration['llm_response']:
                        payload['dependencies'] = iteration['llm_response']['dependencies']
                    
                    vectors.append(vector)
                    payloads.append(payload)
                    
                    print(f"  Prepared vector for iteration {iteration['iteration']}")
        
        # Store in vector database
        if vectors and payloads:
            print(f"Storing {len(vectors)} vectors in Qdrant...")
            
            try:
                persistence.upsert_vector_records(vectors, payloads)
                vector_store_status['vectors_stored'] = len(vectors)
                print(f"Successfully stored {len(vectors)} vectors")
                
            except Exception as e:
                print(f"Error storing vectors: {e}")
                vector_store_status['status'] = 'partial_success'
                vector_store_status['errors'].append(f"Vector storage error: {str(e)}")
        else:
            print("No vectors to store")
        
        # Calculate storage statistics
        storage_time = time.time() - storage_start_time
        vector_store_status['metadata'].update({
            'storage_duration': storage_time,
            'vectors_per_second': len(vectors) / storage_time if storage_time > 0 else 0,
            'total_requirements_processed': len(processed_requirements),
            'total_iterations_processed': sum(len(req['iterations']) for req in processed_requirements),
            'successful_iterations': sum(len([iter for iter in req['iterations'] if iter['status'] == 'success']) for req in processed_requirements),
            'storage_timestamp': time.time()
        })
        
        print(f"Vector storage completed in {storage_time:.2f}s")
        print(f"Stored {vector_store_status['vectors_stored']} vectors in Qdrant")
        
    except Exception as e:
        vector_store_status['status'] = 'error'
        vector_store_status['errors'].append(str(e))
        print(f"Error in vector storage: {e}")
    
    return vector_store_status


def _validate_payload(payload: Dict) -> bool:
    """Validate payload before storage."""
    required_fields = ['id', 'requirement_text', 'requirement_id', 'provider', 'model']
    
    for field in required_fields:
        if field not in payload or not payload[field]:
            return False
    
    return True


def _create_search_index(collection_name: str) -> Dict[str, Any]:
    """Create search index for the collection."""
    # This would create appropriate search indexes in Qdrant
    # For now, return a placeholder
    return {
        'index_type': 'HNSW',
        'metric': 'Cosine',
        'dimensions': 128,  # Adjust based on your embedder
        'collection': collection_name
    }


def _optimize_payload_size(payload: Dict) -> Dict:
    """Optimize payload size for vector storage."""
    # Remove very long text fields that might exceed storage limits
    optimized = payload.copy()
    
    # Truncate very long text fields
    if 'requirement_text' in optimized and len(optimized['requirement_text']) > 1000:
        optimized['requirement_text'] = optimized['requirement_text'][:1000] + '...'
    
    if 'llm_response' in optimized and isinstance(optimized['llm_response'], dict):
        # Truncate long LLM responses
        for key, value in optimized['llm_response'].items():
            if isinstance(value, str) and len(value) > 500:
                optimized['llm_response'][key] = value[:500] + '...'
    
    return optimized


# Main execution function for Camunda
def main():
    """Main function called by Camunda."""
    # This would be called by Camunda with the execution context
    # For now, this is a standalone script for testing
    
    # Test with sample processed requirements
    sample_processed_requirements = [
        {
            'original_requirement': {
                'id': 'req_001',
                'text': 'The system shall provide user authentication.',
                'category': 'Security',
                'source_file': 'test_document.txt',
                'extraction_confidence': 0.9
            },
            'iterations': [
                {
                    'status': 'success',
                    'requirement_id': 'req_001',
                    'requirement_text': 'The system shall provide user authentication.',
                    'llm_response': {
                        'extracted_entities': ['System', 'Authentication'],
                        'constraints': ['Security', 'Privacy'],
                        'dependencies': ['User Management']
                    },
                    'provider': 'openai',
                    'model': 'gpt-4o-mini',
                    'confidence': 0.85,
                    'iteration': 1,
                    'processing_time': time.time()
                }
            ],
            'total_processing_time': 2.5,
            'success_rate': 1.0,
            'average_confidence': 0.85
        }
    ]
    
    result = store_results_in_vector_db(sample_processed_requirements)
    
    print("Vector Storage Results:")
    print(f"Status: {result['status']}")
    print(f"Vectors Stored: {result['vectors_stored']}")
    print(f"Collections Created: {result['collections_created']}")
    print(f"Storage Duration: {result['metadata']['storage_duration']:.2f}s")
    
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    main()

