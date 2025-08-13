#!/usr/bin/env python3
"""
External Task Script: Store Results in RDF Database
This script is called by Camunda BPMN process to store processed requirements in Fuseki.

Input Variables (from Camunda):
- processed_requirements: JSON string of processed requirements with LLM results

Output Variables (set in Camunda):
- rdf_store_status: JSON string of RDF storage status and metadata
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


def store_results_in_rdf_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Fuseki RDF database.
    
    Args:
        processed_requirements: List of processed requirements with LLM results
        
    Returns:
        Dict containing RDF store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)
    
    rdf_store_status = {
        'database': 'Fuseki',
        'triples_created': 0,
        'graphs_created': 1,
        'status': 'success',
        'errors': [],
        'metadata': {}
    }
    
    storage_start_time = time.time()
    
    try:
        # Prepare RDF triples in Turtle format
        ttl_lines = []
        
        # Add namespace declarations
        ttl_lines.extend([
            "@prefix odras: <http://example.com/odras#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix prov: <http://www.w3.org/ns/prov#> .",
            "@prefix dcterms: <http://purl.org/dc/terms/> .",
            ""
        ])
        
        # Add ontology definitions
        ttl_lines.extend([
            "# ODRAS Ontology Definitions",
            "odras:Requirement a rdfs:Class .",
            "odras:Iteration a rdfs:Class .",
            "odras:Entity a rdfs:Class .",
            "odras:Constraint a rdfs:Class .",
            "odras:Dependency a rdfs:Class .",
            "odras:PerformanceRequirement a rdfs:Class .",
            "odras:QualityAttribute a rdfs:Class .",
            "",
            "# Object Properties",
            "odras:hasIteration a rdf:Property .",
            "odras:extractsEntity a rdf:Property .",
            "odras:identifiesConstraint a rdf:Property .",
            "odras:identifiesDependency a rdf:Property .",
            "odras:identifiesPerformance a rdf:Property .",
            "odras:identifiesQuality a rdf:Property .",
            "odras:hasConstraint a rdf:Property .",
            "odras:hasDependency a rdf:Property .",
            "odras:hasPerformanceRequirement a rdf:Property .",
            "odras:hasQualityAttribute a rdf:Property .",
            ""
        ])
        
        for req_idx, req in enumerate(processed_requirements):
            print(f"Processing requirement {req_idx + 1}/{len(processed_requirements)}: {req['original_requirement']['id']}")
            
            req_id = req['original_requirement']['id']
            req_uri = f"odras:requirement_{req_id}"
            
            # Requirement triples
            ttl_lines.extend([
                f"# Requirement: {req_id}",
                f"{req_uri} a odras:Requirement .",
                f"{req_uri} odras:hasText \"{_escape_text(req['original_requirement']['text'])}\" .",
                f"{req_uri} odras:category \"{req['original_requirement'].get('category', 'Unknown')}\" .",
                f"{req_uri} odras:sourceFile \"{req['original_requirement'].get('source_file', 'Unknown')}\" .",
                f"{req_uri} odras:extractionConfidence {req['original_requirement'].get('extraction_confidence', 0.0)} .",
                f"{req_uri} odras:extractionTimestamp \"{_format_timestamp(req['original_requirement'].get('timestamp', time.time()))}\"^^xsd:dateTime .",
                f"{req_uri} prov:wasGeneratedBy odras:extractionProcess .",
                ""
            ])
            
            for iter_idx, iteration in enumerate(req['iterations']):
                if iteration['status'] == 'success':
                    iter_uri = f"odras:iteration_{req_id}_{iteration['iteration']}"
                    
                    # Iteration triples
                    ttl_lines.extend([
                        f"# Iteration: {req_id}_{iteration['iteration']}",
                        f"{iter_uri} a odras:Iteration .",
                        f"{iter_uri} odras:iterationNumber {iteration['iteration']} .",
                        f"{iter_uri} odras:usesModel \"{iteration['model']}\" .",
                        f"{iter_uri} odras:hasConfidence {iteration['confidence']} .",
                        f"{iter_uri} odras:provider \"{iteration['provider']}\" .",
                        f"{iter_uri} odras:processingTimestamp \"{_format_timestamp(iteration['processing_time'])}\"^^xsd:dateTime .",
                        f"{req_uri} odras:hasIteration {iter_uri} .",
                        f"{iter_uri} prov:wasGeneratedBy odras:llmProcess .",
                        ""
                    ])
                    
                    # Extract entities from LLM response
                    if 'extracted_entities' in iteration['llm_response']:
                        for entity in iteration['llm_response']['extracted_entities']:
                            entity_uri = f"odras:entity_{_sanitize_uri(entity)}_{req_id}_{iteration['iteration']}"
                            ttl_lines.extend([
                                f"# Entity: {entity}",
                                f"{entity_uri} a odras:Entity .",
                                f"{entity_uri} odras:name \"{entity}\" .",
                                f"{entity_uri} odras:category \"{_categorize_entity(entity)}\" .",
                                f"{iter_uri} odras:extractsEntity {entity_uri} .",
                                ""
                            ])
                    
                    # Extract constraints from LLM response
                    if 'constraints' in iteration['llm_response']:
                        for constraint in iteration['llm_response']['constraints']:
                            constraint_uri = f"odras:constraint_{_sanitize_uri(constraint)}_{req_id}_{iteration['iteration']}"
                            ttl_lines.extend([
                                f"# Constraint: {constraint}",
                                f"{constraint_uri} a odras:Constraint .",
                                f"{constraint_uri} odras:name \"{constraint}\" .",
                                f"{iter_uri} odras:identifiesConstraint {constraint_uri} .",
                                f"{req_uri} odras:hasConstraint {constraint_uri} .",
                                ""
                            ])
                    
                    # Extract dependencies from LLM response
                    if 'dependencies' in iteration['llm_response']:
                        for dependency in iteration['llm_response']['dependencies']:
                            dependency_uri = f"odras:dependency_{_sanitize_uri(dependency)}_{req_id}_{iteration['iteration']}"
                            ttl_lines.extend([
                                f"# Dependency: {dependency}",
                                f"{dependency_uri} a odras:Dependency .",
                                f"{dependency_uri} odras:name \"{dependency}\" .",
                                f"{iter_uri} odras:identifiesDependency {dependency_uri} .",
                                f"{req_uri} odras:hasDependency {dependency_uri} .",
                                ""
                            ])
                    
                    # Extract performance requirements
                    if 'performance_requirements' in iteration['llm_response']:
                        for perf_req in iteration['llm_response']['performance_requirements']:
                            perf_uri = f"odras:perf_{_sanitize_uri(perf_req)}_{req_id}_{iteration['iteration']}"
                            ttl_lines.extend([
                                f"# Performance Requirement: {perf_req}",
                                f"{perf_uri} a odras:PerformanceRequirement .",
                                f"{perf_uri} odras:name \"{perf_req}\" .",
                                f"{iter_uri} odras:identifiesPerformance {perf_uri} .",
                                f"{req_uri} odras:hasPerformanceRequirement {perf_uri} .",
                                ""
                            ])
                    
                    # Extract quality attributes
                    if 'quality_attributes' in iteration['llm_response']:
                        for quality_attr in iteration['llm_response']['quality_attributes']:
                            quality_uri = f"odras:quality_{_sanitize_uri(quality_attr)}_{req_id}_{iteration['iteration']}"
                            ttl_lines.extend([
                                f"# Quality Attribute: {quality_attr}",
                                f"{quality_uri} a odras:QualityAttribute .",
                                f"{quality_uri} odras:name \"{quality_attr}\" .",
                                f"{iter_uri} odras:identifiesQuality {quality_uri} .",
                                f"{req_uri} odras:hasQualityAttribute {quality_uri} .",
                                ""
                            ])
                    
                    print(f"  Created RDF triples for iteration {iteration['iteration']}")
        
        # Store in RDF database
        if len(ttl_lines) > 20:  # More than just namespace declarations and ontology
            ttl_content = "\n".join(ttl_lines)
            
            try:
                persistence.write_rdf(ttl_content)
                
                # Count actual triples (lines ending with .)
                rdf_store_status['triples_created'] = len([line for line in ttl_lines if line.strip().endswith('.')])
                
                print(f"Successfully created {rdf_store_status['triples_created']} RDF triples")
                
            except Exception as e:
                print(f"Error storing in RDF database: {e}")
                rdf_store_status['status'] = 'partial_success'
                rdf_store_status['errors'].append(f"RDF storage error: {str(e)}")
        else:
            print("No RDF triples to store")
        
        # Calculate storage statistics
        storage_time = time.time() - storage_start_time
        rdf_store_status['metadata'].update({
            'storage_duration': storage_time,
            'triples_per_second': rdf_store_status['triples_created'] / storage_time if storage_time > 0 else 0,
            'total_requirements_processed': len(processed_requirements),
            'total_iterations_processed': sum(len(req['iterations']) for req in processed_requirements),
            'successful_iterations': sum(len([iter for iter in req['iterations'] if iter['status'] == 'success']) for req in processed_requirements),
            'storage_timestamp': time.time(),
            'ttl_content_length': len(ttl_content) if 'ttl_content' in locals() else 0
        })
        
        print(f"RDF storage completed in {storage_time:.2f}s")
        print(f"Created {rdf_store_status['triples_created']} RDF triples in Fuseki")
        
    except Exception as e:
        rdf_store_status['status'] = 'error'
        rdf_store_status['errors'].append(str(e))
        print(f"Error in RDF storage: {e}")
    
    return rdf_store_status


def _escape_text(text: str) -> str:
    """Escape text for Turtle format."""
    # Basic escaping for Turtle literals
    escaped = text.replace('\\', '\\\\')
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace('\n', '\\n')
    escaped = escaped.replace('\r', '\\r')
    escaped = escaped.replace('\t', '\\t')
    return escaped


def _format_timestamp(timestamp: float) -> str:
    """Format timestamp for RDF."""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.isoformat()


def _sanitize_uri(text: str) -> str:
    """Sanitize text for use in URIs."""
    # Remove special characters and replace spaces with underscores
    sanitized = text.replace(' ', '_')
    sanitized = sanitized.replace('-', '_')
    sanitized = sanitized.replace('(', '')
    sanitized = sanitized.replace(')', '')
    sanitized = sanitized.replace('[', '')
    sanitized = sanitized.replace(']', '')
    sanitized = sanitized.replace('{', '')
    sanitized = sanitized.replace('}', '')
    sanitized = sanitized.replace(':', '_')
    sanitized = sanitized.replace(';', '_')
    sanitized = sanitized.replace(',', '_')
    sanitized = sanitized.replace('.', '_')
    sanitized = sanitized.replace('!', '')
    sanitized = sanitized.replace('?', '')
    sanitized = sanitized.replace('"', '')
    sanitized = sanitized.replace("'", '')
    sanitized = sanitized.replace('\\', '_')
    sanitized = sanitized.replace('/', '_')
    sanitized = sanitized.replace('|', '_')
    sanitized = sanitized.replace('&', '_')
    sanitized = sanitized.replace('=', '_')
    sanitized = sanitized.replace('+', '_')
    sanitized = sanitized.replace('*', '_')
    sanitized = sanitized.replace('%', '_')
    sanitized = sanitized.replace('#', '_')
    sanitized = sanitized.replace('@', '_')
    sanitized = sanitized.replace('$', '_')
    sanitized = sanitized.replace('^', '_')
    sanitized = sanitized.replace('~', '_')
    sanitized = sanitized.replace('`', '')
    
    # Remove multiple consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized


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


def _create_rdf_schema() -> Dict[str, Any]:
    """Create RDF schema for Fuseki."""
    # This would define the RDF schema including classes and properties
    # For now, return a placeholder
    return {
        'classes': [
            'odras:Requirement',
            'odras:Iteration',
            'odras:Entity',
            'odras:Constraint',
            'odras:Dependency',
            'odras:PerformanceRequirement',
            'odras:QualityAttribute'
        ],
        'properties': [
            'odras:hasIteration',
            'odras:extractsEntity',
            'odras:identifiesConstraint',
            'odras:identifiesDependency',
            'odras:identifiesPerformance',
            'odras:identifiesQuality'
        ]
    }


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
    
    result = store_results_in_rdf_db(sample_processed_requirements)
    
    print("RDF Storage Results:")
    print(f"Status: {result['status']}")
    print(f"Triples Created: {result['triples_created']}")
    print(f"Graphs Created: {result['graphs_created']}")
    print(f"Storage Duration: {result['metadata']['storage_duration']:.2f}s")
    
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    main()


