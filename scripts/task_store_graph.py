#!/usr/bin/env python3
"""
External Task Script: Store Results in Graph Database
This script is called by Camunda BPMN process to store processed requirements in Neo4j.

Input Variables (from Camunda):
- processed_requirements: JSON string of processed requirements with LLM results

Output Variables (set in Camunda):
- graph_store_status: JSON string of graph storage status and metadata
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


def store_results_in_graph_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Neo4j graph database.
    
    Args:
        processed_requirements: List of processed requirements with LLM results
        
    Returns:
        Dict containing graph store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)
    
    graph_store_status = {
        'database': 'Neo4j',
        'nodes_created': 0,
        'relationships_created': 0,
        'status': 'success',
        'errors': [],
        'metadata': {}
    }
    
    storage_start_time = time.time()
    
    try:
        # Prepare graph triples
        triples = []
        
        for req_idx, req in enumerate(processed_requirements):
            print(f"Processing requirement {req_idx + 1}/{len(processed_requirements)}: {req['original_requirement']['id']}")
            
            req_id = req['original_requirement']['id']
            
            # Create requirement node
            triples.extend([
                (f"req:{req_id}", "TYPE", "Requirement"),
                (f"req:{req_id}", "HAS_TEXT", req['original_requirement']['text']),
                (f"req:{req_id}", "CATEGORY", req['original_requirement'].get('category', 'Unknown')),
                (f"req:{req_id}", "SOURCE_FILE", req['original_requirement'].get('source_file', 'Unknown')),
                (f"req:{req_id}", "EXTRACTION_CONFIDENCE", str(req['original_requirement'].get('extraction_confidence', 0.0))),
                (f"req:{req_id}", "EXTRACTION_TIMESTAMP", str(req['original_requirement'].get('timestamp', time.time())))
            ])
            
            for iter_idx, iteration in enumerate(req['iterations']):
                if iteration['status'] == 'success':
                    iter_id = f"{req_id}_{iteration['iteration']}"
                    
                    # Create iteration node
                    triples.extend([
                        (f"iter:{iter_id}", "TYPE", "Iteration"),
                        (f"iter:{iter_id}", "ITERATION_NUMBER", str(iteration['iteration'])),
                        (f"iter:{iter_id}", "USES_MODEL", iteration['model']),
                        (f"iter:{iter_id}", "HAS_CONFIDENCE", str(iteration['confidence'])),
                        (f"iter:{iter_id}", "PROVIDER", iteration['provider']),
                        (f"iter:{iter_id}", "PROCESSING_TIME", str(iteration['processing_time']))
                    ])
                    
                    # Link requirement to iteration
                    triples.append((f"req:{req_id}", "HAS_ITERATION", f"iter:{iter_id}"))
                    
                    # Extract entities from LLM response (if available)
                    if 'extracted_entities' in iteration['llm_response']:
                        for entity in iteration['llm_response']['extracted_entities']:
                            entity_id = f"ent:{entity}_{iter_id}"
                            triples.extend([
                                (entity_id, "TYPE", "Entity"),
                                (entity_id, "NAME", entity),
                                (entity_id, "CATEGORY", _categorize_entity(entity)),
                                (f"iter:{iter_id}", "EXTRACTS_ENTITY", entity_id)
                            ])
                    
                    # Extract constraints from LLM response
                    if 'constraints' in iteration['llm_response']:
                        for constraint in iteration['llm_response']['constraints']:
                            constraint_id = f"constraint:{constraint}_{iter_id}"
                            triples.extend([
                                (constraint_id, "TYPE", "Constraint"),
                                (constraint_id, "NAME", constraint),
                                (f"iter:{iter_id}", "IDENTIFIES_CONSTRAINT", constraint_id),
                                (f"req:{req_id}", "HAS_CONSTRAINT", constraint_id)
                            ])
                    
                    # Extract dependencies from LLM response
                    if 'dependencies' in iteration['llm_response']:
                        for dependency in iteration['llm_response']['dependencies']:
                            dependency_id = f"dep:{dependency}_{iter_id}"
                            triples.extend([
                                (dependency_id, "TYPE", "Dependency"),
                                (dependency_id, "NAME", dependency),
                                (f"iter:{iter_id}", "IDENTIFIES_DEPENDENCY", dependency_id),
                                (f"req:{req_id}", "HAS_DEPENDENCY", dependency_id)
                            ])
                    
                    # Extract performance requirements
                    if 'performance_requirements' in iteration['llm_response']:
                        for perf_req in iteration['llm_response']['performance_requirements']:
                            perf_id = f"perf:{perf_req}_{iter_id}"
                            triples.extend([
                                (perf_id, "TYPE", "PerformanceRequirement"),
                                (perf_id, "NAME", perf_req),
                                (f"iter:{iter_id}", "IDENTIFIES_PERFORMANCE", perf_id),
                                (f"req:{req_id}", "HAS_PERFORMANCE_REQUIREMENT", perf_id)
                            ])
                    
                    # Extract quality attributes
                    if 'quality_attributes' in iteration['llm_response']:
                        for quality_attr in iteration['llm_response']['quality_attributes']:
                            quality_id = f"quality:{quality_attr}_{iter_id}"
                            triples.extend([
                                (quality_id, "TYPE", "QualityAttribute"),
                                (quality_id, "NAME", quality_attr),
                                (f"iter:{iter_id}", "IDENTIFIES_QUALITY", quality_id),
                                (f"req:{req_id}", "HAS_QUALITY_ATTRIBUTE", quality_id)
                            ])
                    
                    print(f"  Created graph nodes for iteration {iteration['iteration']}")
        
        # Store in graph database
        if triples:
            print(f"Storing {len(triples)} graph triples in Neo4j...")
            
            try:
                persistence.write_graph(triples)
                
                # Count unique nodes and relationships
                unique_nodes = set()
                for triple in triples:
                    unique_nodes.add(triple[0])  # Subject
                    unique_nodes.add(triple[2])  # Object (if it's a node, not a literal)
                
                graph_store_status['nodes_created'] = len(unique_nodes)
                graph_store_status['relationships_created'] = len(triples)
                
                print(f"Successfully created {len(unique_nodes)} nodes and {len(triples)} relationships")
                
            except Exception as e:
                print(f"Error storing in graph database: {e}")
                graph_store_status['status'] = 'partial_success'
                graph_store_status['errors'].append(f"Graph storage error: {str(e)}")
        else:
            print("No graph triples to store")
        
        # Calculate storage statistics
        storage_time = time.time() - storage_start_time
        graph_store_status['metadata'].update({
            'storage_duration': storage_time,
            'triples_per_second': len(triples) / storage_time if storage_time > 0 else 0,
            'total_requirements_processed': len(processed_requirements),
            'total_iterations_processed': sum(len(req['iterations']) for req in processed_requirements),
            'successful_iterations': sum(len([iter for iter in req['iterations'] if iter['status'] == 'success']) for req in processed_requirements),
            'storage_timestamp': time.time()
        })
        
        print(f"Graph storage completed in {storage_time:.2f}s")
        print(f"Created {graph_store_status['nodes_created']} nodes and {graph_store_status['relationships_created']} relationships in Neo4j")
        
    except Exception as e:
        graph_store_status['status'] = 'error'
        graph_store_status['errors'].append(str(e))
        print(f"Error in graph storage: {e}")
    
    return graph_store_status


def _categorize_entity(entity_name: str) -> str:
    """Categorize entity based on name patterns."""
    entity_lower = entity_name.lower()
    
    if any(word in entity_lower for word in ['system', 'component', 'module', 'subsystem']):
        return 'SystemComponent'
    elif any(word in entity_lower for word in ['interface', 'api', 'protocol']):
        return 'Interface'
    elif any(word in entity_lower for word in ['function', 'process', 'operation']):
        return 'Function'
    elif any(word in entity_lower for word in ['condition', 'trigger', 'event']):
        return 'Condition'
    elif any(word in entity_lower for word in ['user', 'actor', 'stakeholder']):
        return 'Actor'
    else:
        return 'Entity'


def _create_graph_schema() -> Dict[str, Any]:
    """Create graph schema for Neo4j."""
    # This would define the graph schema including constraints and indexes
    # For now, return a placeholder
    return {
        'constraints': [
            'CREATE CONSTRAINT requirement_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE',
            'CREATE CONSTRAINT iteration_id IF NOT EXISTS FOR (i:Iteration) REQUIRE i.id IS UNIQUE',
            'CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE'
        ],
        'indexes': [
            'CREATE INDEX requirement_category IF NOT EXISTS FOR (r:Requirement) ON (r.category)',
            'CREATE INDEX iteration_provider IF NOT EXISTS FOR (i:Iteration) ON (i.provider)',
            'CREATE INDEX entity_category IF NOT EXISTS FOR (e:Entity) ON (e.category)'
        ]
    }


def _validate_triple(triple: tuple) -> bool:
    """Validate graph triple before storage."""
    if len(triple) != 3:
        return False
    
    subject, predicate, obj = triple
    
    # Basic validation
    if not subject or not predicate:
        return False
    
    # Subject should be a node identifier
    if not isinstance(subject, str) or not subject:
        return False
    
    # Predicate should be a relationship type
    if not isinstance(predicate, str) or not predicate:
        return False
    
    return True


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
                'extraction_confidence': 0.9,
                'timestamp': time.time()
            },
            'iterations': [
                {
                    'status': 'success',
                    'requirement_id': 'req_001',
                    'requirement_text': 'The system shall provide user authentication.',
                    'llm_response': {
                        'extracted_entities': ['System', 'Authentication'],
                        'constraints': ['Security', 'Privacy'],
                        'dependencies': ['User Management'],
                        'performance_requirements': ['Response Time'],
                        'quality_attributes': ['Reliability']
                    },
                    'provider': 'openai',
                    'model': 'gpt-4o-mini',
                    'confidence': 0.85,
                    'iteration': 1,
                    'processing_time': time.time()
                }
            ]
        }
    ]
    
    result = store_results_in_graph_db(sample_processed_requirements)
    
    print("Graph Storage Results:")
    print(f"Status: {result['status']}")
    print(f"Nodes Created: {result['nodes_created']}")
    print(f"Relationships Created: {result['relationships_created']}")
    print(f"Storage Duration: {result['metadata']['storage_duration']:.2f}s")
    
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
