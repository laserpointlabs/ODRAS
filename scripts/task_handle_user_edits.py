#!/usr/bin/env python3
"""
External Task Script: Handle User Edits to Requirements
This script is called by Camunda BPMN process to process user edits to extracted requirements.

Input Variables (from Camunda):
- requirements_list: JSON string of extracted requirements
- user_edits: JSON string of user modifications to requirements
- document_content: Original document content for reference

Output Variables (set in Camunda):
- edited_requirements: JSON string of requirements after user edits
- edit_metadata: JSON string of edit metadata and audit trail
"""

import json
import time
import sys
import os
from typing import Dict, List, Any, Optional

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings


def handle_user_edits(requirements_list: List[Dict], user_edits: List[Dict], 
                      document_content: str, document_filename: str) -> Dict[str, Any]:
    """
    Process user edits to extracted requirements.
    
    Args:
        requirements_list: List of extracted requirements
        user_edits: List of user modifications
        document_content: Original document content
        document_filename: Name of the source document
        
    Returns:
        Dict containing edited_requirements and edit_metadata
    """
    
    edit_start_time = time.time()
    
    # Create a copy of requirements to modify
    edited_requirements = []
    for req in requirements_list:
        edited_req = req.copy()
        edited_req['last_modified'] = time.time()
        edited_req['modification_history'] = []
        edited_requirements.append(edited_req)
    
    # Apply user edits
    edits_applied = 0
    edits_rejected = 0
    edit_errors = []
    
    for edit in user_edits:
        try:
            edit_result = _apply_single_edit(edited_requirements, edit)
            if edit_result['success']:
                edits_applied += 1
                # Add to modification history
                for req in edited_requirements:
                    if req['id'] == edit_result['requirement_id']:
                        req['modification_history'].append({
                            'timestamp': time.time(),
                            'edit_type': edit.get('edit_type', 'manual'),
                            'field': edit.get('field', 'text'),
                            'old_value': edit_result.get('old_value'),
                            'new_value': edit_result.get('new_value'),
                            'user_comment': edit.get('comment', '')
                        })
            else:
                edits_rejected += 1
                edit_errors.append(edit_result['error'])
        except Exception as e:
            edits_rejected += 1
            edit_errors.append(f"Error processing edit: {str(e)}")
    
    # Validate edited requirements
    validation_result = _validate_edited_requirements(edited_requirements)
    
    edit_time = time.time() - edit_start_time
    
    return {
        'edited_requirements': edited_requirements,
        'edit_metadata': {
            'total_requirements': len(edited_requirements),
            'edits_applied': edits_applied,
            'edits_rejected': edits_rejected,
            'edit_errors': edit_errors,
            'validation_passed': validation_result['passed'],
            'validation_errors': validation_result['errors'],
            'document_filename': document_filename,
            'edit_timestamp': time.time(),
            'edit_duration': edit_time,
            'edit_method': 'user_manual'
        }
    }


def _apply_single_edit(requirements: List[Dict], edit: Dict) -> Dict[str, Any]:
    """
    Apply a single user edit to a requirement.
    
    Args:
        requirements: List of requirements to modify
        edit: Single edit operation
        
    Returns:
        Dict with edit result information
    """
    
    edit_type = edit.get('edit_type', 'modify')
    requirement_id = edit.get('requirement_id')
    field = edit.get('field', 'text')
    new_value = edit.get('new_value')
    
    # Find the requirement to edit
    target_req = None
    for req in requirements:
        if req['id'] == requirement_id:
            target_req = req
            break
    
    if not target_req:
        return {
            'success': False,
            'error': f"Requirement with ID {requirement_id} not found"
        }
    
    if edit_type == 'modify':
        # Modify existing field
        if field not in target_req:
            return {
                'success': False,
                'error': f"Field '{field}' not found in requirement"
            }
        
        old_value = target_req[field]
        target_req[field] = new_value
        target_req['last_modified'] = time.time()
        
        return {
            'success': True,
            'requirement_id': requirement_id,
            'field': field,
            'old_value': old_value,
            'new_value': new_value
        }
    
    elif edit_type == 'add':
        # Add new requirement
        new_req = {
            'id': f"req_user_{len(requirements):03d}",
            'text': new_value,
            'pattern': 'user_manual',
            'source_file': requirements[0].get('source_file', 'unknown') if requirements else 'unknown',
            'extraction_confidence': 1.0,  # User-defined, high confidence
            'timestamp': time.time(),
            'category': edit.get('category', 'user_defined'),
            'last_modified': time.time(),
            'modification_history': []
        }
        requirements.append(new_req)
        
        return {
            'success': True,
            'requirement_id': new_req['id'],
            'field': 'text',
            'old_value': None,
            'new_value': new_value
        }
    
    elif edit_type == 'delete':
        # Mark requirement as deleted (soft delete)
        target_req['deleted'] = True
        target_req['deletion_timestamp'] = time.time()
        target_req['deletion_reason'] = edit.get('reason', 'User request')
        
        return {
            'success': True,
            'requirement_id': requirement_id,
            'field': 'deleted',
            'old_value': False,
            'new_value': True
        }
    
    else:
        return {
            'success': False,
            'error': f"Unknown edit type: {edit_type}"
        }


def _validate_edited_requirements(requirements: List[Dict]) -> Dict[str, Any]:
    """
    Validate edited requirements for consistency and completeness.
    
    Args:
        requirements: List of edited requirements
        
    Returns:
        Dict with validation results
    """
    
    validation_errors = []
    
    for req in requirements:
        # Skip deleted requirements
        if req.get('deleted', False):
            continue
        
        # Check required fields
        if not req.get('text', '').strip():
            validation_errors.append(f"Requirement {req['id']}: Empty text")
        
        if not req.get('id'):
            validation_errors.append(f"Requirement missing ID: {req}")
        
        # Check text length
        if len(req.get('text', '')) < 10:
            validation_errors.append(f"Requirement {req['id']}: Text too short")
        
        # Check confidence range
        confidence = req.get('extraction_confidence', 0)
        if not (0.0 <= confidence <= 1.0):
            validation_errors.append(f"Requirement {req['id']}: Invalid confidence {confidence}")
    
    return {
        'passed': len(validation_errors) == 0,
        'errors': validation_errors,
        'total_requirements': len([r for r in requirements if not r.get('deleted', False)])
    }


# Main execution function for Camunda
def main():
    """Main function called by Camunda."""
    # This would be called by Camunda with the execution context
    # For now, this is a standalone script for testing
    
    # Test with sample data
    sample_requirements = [
        {
            'id': 'req_001',
            'text': 'The system shall provide user authentication.',
            'pattern': r'\b(shall|should|must|will)\b.*?[.!?]',
            'source_file': 'test_document.txt',
            'extraction_confidence': 0.8,
            'timestamp': time.time(),
            'category': 'Security'
        }
    ]
    
    sample_user_edits = [
        {
            'edit_type': 'modify',
            'requirement_id': 'req_001',
            'field': 'text',
            'new_value': 'The system shall provide secure user authentication with multi-factor support.',
            'comment': 'Enhanced security requirement'
        },
        {
            'edit_type': 'add',
            'new_value': 'The system must log all authentication attempts.',
            'category': 'Security',
            'comment': 'Added logging requirement'
        }
    ]
    
    result = handle_user_edits(sample_requirements, sample_user_edits, 
                              "Sample document content", "test_document.txt")
    
    print("User Edit Results:")
    print(f"Total Requirements: {result['edit_metadata']['total_requirements']}")
    print(f"Edits Applied: {result['edit_metadata']['edits_applied']}")
    print(f"Edits Rejected: {result['edit_metadata']['edits_rejected']}")
    print(f"Validation Passed: {result['edit_metadata']['validation_passed']}")
    print(f"Edit Duration: {result['edit_metadata']['edit_duration']:.3f}s")
    
    if result['edit_metadata']['edit_errors']:
        print("\nEdit Errors:")
        for error in result['edit_metadata']['edit_errors']:
            print(f"  - {error}")
    
    print("\nEdited Requirements:")
    for req in result['edited_requirements']:
        if not req.get('deleted', False):
            print(f"  {req['id']}: {req['text'][:80]}...")
            if req['modification_history']:
                print(f"    Modifications: {len(req['modification_history'])}")


if __name__ == "__main__":
    main()
