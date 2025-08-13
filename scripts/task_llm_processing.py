#!/usr/bin/env python3
"""
External Task Script: Monte Carlo LLM Processing
This script is called by Camunda BPMN process to process requirements through LLM iterations.

Input Variables (from Camunda):
- requirements_list: JSON string of extracted requirements
- llm_provider: LLM provider (openai or ollama)
- llm_model: Model name to use
- iterations: Number of Monte Carlo iterations

Output Variables (set in Camunda):
- processed_requirements: JSON string of processed requirements with LLM results
- llm_results: JSON string of LLM processing metadata
"""

import json
import time
import sys
import os
import asyncio
from typing import Dict, List, Any, Optional

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings
from services.llm_team import LLMTeam
from services.persona_manager import PersonaManager


async def process_requirements_with_llm(requirements_list: List[Dict], llm_provider: str, 
                                llm_model: str, iterations: int, 
                                custom_personas: Optional[List[Dict]] = None, 
                                custom_prompts: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Process requirements through Monte Carlo LLM iterations.
    
    Args:
        requirements_list: List of extracted requirements
        llm_provider: LLM provider (openai or ollama)
        llm_model: Model name to use
        iterations: Number of Monte Carlo iterations
        custom_personas: Optional custom personas to use
        custom_prompts: Optional custom prompts to use
        
    Returns:
        Dict containing processed_requirements and llm_results
    """
    settings = Settings()
    settings.llm_provider = llm_provider
    settings.llm_model = llm_model
    
    llm_team = LLMTeam(settings)
    processed_requirements = []
    
    print(f"Processing {len(requirements_list)} requirements with {iterations} iterations each")
    print(f"Using {llm_provider} with model {llm_model}")
    
    processing_start_time = time.time()
    
    for req_idx, req in enumerate(requirements_list):
        print(f"Processing requirement {req_idx + 1}/{len(requirements_list)}: {req['id']}")
        
        req_results = []
        req_start_time = time.time()
        
        for i in range(iterations):
            print(f"  Iteration {i + 1}/{iterations}")
            
            try:
                # Call LLM team to analyze the requirement
                llm_result = _analyze_requirement_with_llm(llm_team, req, i, llm_provider, llm_model)
                
                # Add metadata
                result = {
                    'iteration': i + 1,
                    'provider': llm_provider,
                    'model': llm_model,
                    'requirement_id': req['id'],
                    'requirement_text': req['text'],
                    'llm_response': llm_result,
                    'confidence': _calculate_iteration_confidence(i, iterations, llm_result),
                    'processing_time': time.time(),
                    'status': 'success',
                    'iteration_duration': time.time() - req_start_time
                }
                
            except Exception as e:
                print(f"  Error in iteration {i + 1}: {e}")
                
                # Handle LLM processing errors
                result = {
                    'iteration': i + 1,
                    'provider': llm_provider,
                    'model': llm_model,
                    'requirement_id': req['id'],
                    'requirement_text': req['text'],
                    'llm_response': {'error': str(e)},
                    'confidence': 0.0,
                    'processing_time': time.time(),
                    'status': 'error',
                    'error_message': str(e),
                    'iteration_duration': time.time() - req_start_time
                }
            
            req_results.append(result)
            
            # Small delay to avoid overwhelming the LLM service
            time.sleep(0.1)
        
        # Calculate aggregate statistics for this requirement
        successful_results = [r for r in req_results if r['status'] == 'success']
        avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results) if successful_results else 0.0
        
        req_processing_time = time.time() - req_start_time
        
        processed_requirements.append({
            'original_requirement': req,
            'iterations': req_results,
            'average_confidence': avg_confidence,
            'successful_iterations': len(successful_results),
            'total_iterations': len(req_results),
            'total_processing_time': req_processing_time,
            'success_rate': len(successful_results) / len(req_results) if req_results else 0.0
        })
        
        print(f"  Completed requirement {req['id']} in {req_processing_time:.2f}s")
        print(f"  Average confidence: {avg_confidence:.3f}, Success rate: {len(successful_results)}/{len(req_results)}")
    
    total_processing_time = time.time() - processing_start_time
    
    return {
        'processed_requirements': processed_requirements,
        'llm_results': {
            'total_requirements_processed': len(processed_requirements),
            'total_iterations': len(processed_requirements) * iterations,
            'llm_provider': llm_provider,
            'llm_model': llm_model,
            'processing_timestamp': time.time(),
            'total_processing_time': total_processing_time,
            'average_processing_time_per_requirement': total_processing_time / len(processed_requirements) if processed_requirements else 0.0,
            'successful_iterations_total': sum(len([r for r in req['iterations'] if r['status'] == 'success']) for req in processed_requirements),
            'failed_iterations_total': sum(len([r for r in req['iterations'] if r['status'] == 'error']) for req in processed_requirements)
        }
    }


def _analyze_requirement_with_llm(llm_team: LLMTeam, requirement: Dict, iteration: int, 
                                 provider: str, model: str) -> Dict[str, Any]:
    """
    Analyze a single requirement using the LLM team.
    
    Args:
        llm_team: Configured LLM team instance
        requirement: Requirement to analyze
        iteration: Current iteration number
        provider: LLM provider name
        model: LLM model name
        
    Returns:
        LLM analysis result
    """
    # Create a structured prompt for the LLM
    prompt = _create_analysis_prompt(requirement, iteration)
    
    try:
        # For now, simulate LLM processing (replace with actual API calls)
        if provider == "openai":
            # OpenAI API call would go here
            result = _simulate_openai_analysis(requirement, iteration, prompt)
        else:  # ollama
            # Ollama API call would go here
            result = _simulate_ollama_analysis(requirement, iteration, prompt)
        
        return result
        
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        return {
            'error': str(e),
            'prompt': prompt,
            'provider': provider,
            'model': model
        }


def _create_analysis_prompt(requirement: Dict, iteration: int) -> str:
    """Create a structured prompt for LLM analysis."""
    
    prompt = f"""
    Analyze the following requirement and extract key information:
    
    Requirement: {requirement['text']}
    Category: {requirement.get('category', 'Unknown')}
    Source: {requirement.get('source_file', 'Unknown')}
    Iteration: {iteration + 1}
    
    Please provide:
    1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)
    2. Constraints and dependencies
    3. Performance requirements
    4. Quality attributes
    5. Confidence level (0.0-1.0)
    
    Format your response as JSON with the following structure:
    {{
        "extracted_entities": ["entity1", "entity2"],
        "constraints": ["constraint1", "constraint2"],
        "dependencies": ["dependency1", "dependency2"],
        "performance_requirements": ["perf1", "perf2"],
        "quality_attributes": ["quality1", "quality2"],
        "confidence": 0.85,
        "analysis_notes": "Brief analysis notes"
    }}
    """
    
    return prompt.strip()


def _simulate_openai_analysis(requirement: Dict, iteration: int, prompt: str) -> Dict[str, Any]:
    """Simulate OpenAI analysis (replace with actual API call)."""
    
    # Simulate different responses for each iteration
    base_entities = ['System', 'Component', 'Function', 'Interface']
    base_constraints = ['Performance', 'Security', 'Reliability']
    
    # Add some variation based on iteration
    if iteration % 3 == 0:
        entities = base_entities + ['Process']
        constraints = base_constraints + ['Scalability']
    elif iteration % 3 == 1:
        entities = base_entities + ['Subsystem']
        constraints = base_constraints + ['Maintainability']
    else:
        entities = base_entities + ['Module']
        constraints = base_constraints + ['Usability']
    
    return {
        'extracted_entities': entities,
        'constraints': constraints,
        'dependencies': [f'dep_{iteration}_{i}' for i in range(2)],
        'performance_requirements': [f'perf_{iteration}_{i}' for i in range(2)],
        'quality_attributes': [f'quality_{iteration}_{i}' for i in range(2)],
        'confidence': 0.8 + (iteration * 0.02),
        'analysis_notes': f'Analysis iteration {iteration + 1} for requirement {requirement["id"]}',
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'prompt_used': prompt[:200] + '...' if len(prompt) > 200 else prompt
    }


def _simulate_ollama_analysis(requirement: Dict, iteration: int, prompt: str) -> Dict[str, Any]:
    """Simulate Ollama analysis (replace with actual API call)."""
    
    # Simulate different responses for each iteration
    base_entities = ['System', 'Component', 'Function']
    base_constraints = ['Performance', 'Security']
    
    # Add some variation based on iteration
    if iteration % 2 == 0:
        entities = base_entities + ['Interface']
        constraints = base_constraints + ['Reliability']
    else:
        entities = base_entities + ['Process']
        constraints = base_constraints + ['Maintainability']
    
    return {
        'extracted_entities': entities,
        'constraints': constraints,
        'dependencies': [f'dep_{iteration}_{i}' for i in range(1)],
        'performance_requirements': [f'perf_{iteration}_{i}' for i in range(1)],
        'quality_attributes': [f'quality_{iteration}_{i}' for i in range(1)],
        'confidence': 0.7 + (iteration * 0.01),
        'analysis_notes': f'Analysis iteration {iteration + 1} for requirement {requirement["id"]}',
        'provider': 'ollama',
        'model': 'llama3:8b-instruct',
        'prompt_used': prompt[:200] + '...' if len(prompt) > 200 else prompt
    }


def _calculate_iteration_confidence(iteration: int, total_iterations: int, llm_result: Dict) -> float:
    """Calculate confidence for a specific iteration."""
    base_confidence = 0.7
    
    # Boost confidence for successful iterations
    if 'error' not in llm_result:
        base_confidence += 0.2
        
        # Add confidence based on extracted entities
        if 'extracted_entities' in llm_result and llm_result['extracted_entities']:
            base_confidence += 0.05
        
        # Add confidence based on constraints
        if 'constraints' in llm_result and llm_result['constraints']:
            base_confidence += 0.05
    
    # Slight variation based on iteration number
    base_confidence += (iteration * 0.01)
    
    # Ensure confidence is within bounds
    return min(1.0, max(0.1, base_confidence))


# Main execution function for Camunda
async def main():
    """Main function called by Camunda."""
    # This would be called by Camunda with the execution context
    # For now, this is a standalone script for testing
    
    # Test with sample requirements
    sample_requirements = [
        {
            'id': 'req_001',
            'text': 'The system shall provide user authentication.',
            'category': 'Security',
            'source_file': 'test_document.txt'
        },
        {
            'id': 'req_002',
            'text': 'The system must respond within 100ms.',
            'category': 'Performance',
            'source_file': 'test_document.txt'
        }
    ]
    
    result = await process_requirements_with_llm(
        requirements_list=sample_requirements,
        llm_provider='openai',
        llm_model='gpt-4o-mini',
        iterations=3
    )
    
    print("LLM Processing Results:")
    print(f"Total Requirements Processed: {result['llm_results']['total_requirements_processed']}")
    print(f"Total Iterations: {result['llm_results']['total_iterations']}")
    print(f"Total Processing Time: {result['llm_results']['total_processing_time']:.2f}s")
    print(f"Success Rate: {result['llm_results']['successful_iterations_total']}/{result['llm_results']['total_iterations']}")
    
    print("\nProcessed Requirements:")
    for req in result['processed_requirements']:
        print(f"  {req['original_requirement']['id']}: {req['original_requirement']['text']}")
        print(f"    Average Confidence: {req['average_confidence']:.3f}")
        print(f"    Success Rate: {req['success_rate']:.2f}")
        print(f"    Processing Time: {req['total_processing_time']:.2f}s")


def run_main():
    """Wrapper to run the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
