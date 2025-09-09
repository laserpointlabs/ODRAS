#!/usr/bin/env python3
"""
External Task Script: Rerun Requirements Extraction
This script is called by Camunda BPMN process to rerun requirements extraction with different parameters.

Input Variables (from Camunda):
- document_content: Raw text content of the document
- document_filename: Name of the uploaded file
- extraction_parameters: JSON string of new extraction parameters
- previous_requirements: JSON string of previously extracted requirements for comparison

Output Variables (set in Camunda):
- rerun_requirements: JSON string of newly extracted requirements
- rerun_metadata: JSON string of rerun metadata and comparison results
"""

import json
import re
import time
import sys
import os
from typing import Dict, List, Any, Optional

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings


def rerun_requirements_extraction(
    document_content: str,
    document_filename: str,
    extraction_parameters: Dict[str, Any],
    previous_requirements: List[Dict],
) -> Dict[str, Any]:
    """
    Rerun requirements extraction with new parameters.

    Args:
        document_content: Raw text content of the document
        document_filename: Name of the uploaded file
        extraction_parameters: New extraction parameters
        previous_requirements: Previously extracted requirements for comparison

    Returns:
        Dict containing rerun_requirements and rerun_metadata
    """

    rerun_start_time = time.time()

    # Extract new requirements using the task_extract_requirements logic
    # Import the function from the existing script
    try:
        from task_extract_requirements import extract_requirements_from_document
    except ImportError:
        # Fallback to local implementation if import fails
        extract_requirements_from_document = _extract_requirements_fallback

    # Apply custom extraction parameters
    custom_patterns = extraction_parameters.get("custom_patterns", [])
    confidence_threshold = extraction_parameters.get("confidence_threshold", 0.6)
    min_text_length = extraction_parameters.get("min_text_length", 15)
    categories_filter = extraction_parameters.get("categories_filter", [])

    # Extract requirements with custom parameters
    extraction_result = extract_requirements_from_document(document_content, document_filename)

    # Apply custom filtering
    filtered_requirements = _apply_custom_filters(
        extraction_result["requirements_list"],
        custom_patterns,
        confidence_threshold,
        min_text_length,
        categories_filter,
    )

    # Compare with previous extraction
    comparison_result = _compare_extractions(previous_requirements, filtered_requirements)

    # Add rerun metadata
    for req in filtered_requirements:
        req["extraction_run"] = "rerun"
        req["rerun_timestamp"] = time.time()
        req["rerun_parameters"] = extraction_parameters

    rerun_time = time.time() - rerun_start_time

    return {
        "rerun_requirements": filtered_requirements,
        "rerun_metadata": {
            "total_requirements": len(filtered_requirements),
            "previous_total": len(previous_requirements),
            "new_requirements": comparison_result["new_requirements"],
            "modified_requirements": comparison_result["modified_requirements"],
            "removed_requirements": comparison_result["removed_requirements"],
            "extraction_parameters": extraction_parameters,
            "document_filename": document_filename,
            "rerun_timestamp": time.time(),
            "rerun_duration": rerun_time,
            "rerun_method": "parameter_adjustment",
            "comparison_summary": comparison_result["summary"],
        },
    }


def _apply_custom_filters(
    requirements: List[Dict],
    custom_patterns: List[str],
    confidence_threshold: float,
    min_text_length: int,
    categories_filter: List[str],
) -> List[Dict]:
    """
    Apply custom filters to extracted requirements.

    Args:
        requirements: List of extracted requirements
        custom_patterns: Custom regex patterns to apply
        confidence_threshold: Minimum confidence score
        min_text_length: Minimum text length
        categories_filter: Categories to include

    Returns:
        Filtered list of requirements
    """

    filtered = []

    for req in requirements:
        # Apply confidence threshold
        if req.get("extraction_confidence", 0) < confidence_threshold:
            continue

        # Apply text length filter
        if len(req.get("text", "")) < min_text_length:
            continue

        # Apply category filter
        if categories_filter and req.get("category") not in categories_filter:
            continue

        # Apply custom pattern matching if specified
        if custom_patterns:
            text = req.get("text", "").lower()
            pattern_matched = False
            for pattern in custom_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    pattern_matched = True
                    break
            if not pattern_matched:
                continue

        filtered.append(req)

    return filtered


def _compare_extractions(previous: List[Dict], current: List[Dict]) -> Dict[str, Any]:
    """
    Compare two sets of extracted requirements.

    Args:
        previous: Previously extracted requirements
        current: Currently extracted requirements

    Returns:
        Dict with comparison results
    """

    # Create lookup dictionaries
    prev_lookup = {req["id"]: req for req in previous}
    curr_lookup = {req["id"]: req for req in current}

    new_requirements = []
    modified_requirements = []
    removed_requirements = []

    # Find new requirements
    for req_id, req in curr_lookup.items():
        if req_id not in prev_lookup:
            new_requirements.append(req)
        else:
            # Check for modifications
            prev_req = prev_lookup[req_id]
            if _has_significant_changes(prev_req, req):
                modified_requirements.append(
                    {
                        "id": req_id,
                        "previous": prev_req,
                        "current": req,
                        "changes": _identify_changes(prev_req, req),
                    }
                )

    # Find removed requirements
    for req_id, req in prev_lookup.items():
        if req_id not in curr_lookup:
            removed_requirements.append(req)

    # Generate summary
    total_changes = len(new_requirements) + len(modified_requirements) + len(removed_requirements)
    change_percentage = (total_changes / len(previous)) * 100 if previous else 0

    return {
        "new_requirements": new_requirements,
        "modified_requirements": modified_requirements,
        "removed_requirements": removed_requirements,
        "summary": {
            "total_changes": total_changes,
            "change_percentage": change_percentage,
            "stability_score": max(0, 100 - change_percentage),
            "new_count": len(new_requirements),
            "modified_count": len(modified_requirements),
            "removed_count": len(removed_requirements),
        },
    }


def _has_significant_changes(prev_req: Dict, curr_req: Dict) -> bool:
    """
    Check if there are significant changes between two requirements.

    Args:
        prev_req: Previous requirement
        curr_req: Current requirement

    Returns:
        True if significant changes detected
    """

    # Check text changes
    if prev_req.get("text") != curr_req.get("text"):
        return True

    # Check confidence changes
    prev_conf = prev_req.get("extraction_confidence", 0)
    curr_conf = curr_req.get("extraction_confidence", 0)
    if abs(prev_conf - curr_conf) > 0.1:  # 10% threshold
        return True

    # Check category changes
    if prev_req.get("category") != curr_req.get("category"):
        return True

    return False


def _identify_changes(prev_req: Dict, curr_req: Dict) -> List[Dict]:
    """
    Identify specific changes between two requirements.

    Args:
        prev_req: Previous requirement
        curr_req: Current requirement

    Returns:
        List of change descriptions
    """

    changes = []

    # Text changes
    if prev_req.get("text") != curr_req.get("text"):
        changes.append(
            {
                "field": "text",
                "old_value": prev_req.get("text"),
                "new_value": curr_req.get("text"),
                "change_type": "modification",
            }
        )

    # Confidence changes
    prev_conf = prev_req.get("extraction_confidence", 0)
    curr_conf = curr_req.get("extraction_confidence", 0)
    if prev_conf != curr_conf:
        changes.append(
            {
                "field": "extraction_confidence",
                "old_value": prev_conf,
                "new_value": curr_conf,
                "change_type": "modification",
            }
        )

    # Category changes
    if prev_req.get("category") != curr_req.get("category"):
        changes.append(
            {
                "field": "category",
                "old_value": prev_req.get("category"),
                "new_value": curr_req.get("category"),
                "change_type": "modification",
            }
        )

    return changes


def _extract_requirements_fallback(document_content: str, document_filename: str) -> Dict[str, Any]:
    """
    Fallback requirements extraction if import fails.

    Args:
        document_content: Raw text content of the document
        document_filename: Name of the uploaded file

    Returns:
        Dict containing requirements_list and extraction_metadata
    """

    # Basic requirement patterns
    requirement_patterns = [
        r"\b(shall|should|must|will)\b.*?[.!?]",
        r"\b(required|requirement|needed|necessary)\b.*?[.!?]",
        r"\b(system|component|function|subsystem)\s+(shall|must|will)\b.*?[.!?]",
    ]

    requirements = []
    for pattern in requirement_patterns:
        matches = re.findall(pattern, document_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                match = " ".join(match)

            clean_text = match.strip()
            if len(clean_text) > 10:
                requirements.append(
                    {
                        "id": f"req_{len(requirements):03d}",
                        "text": clean_text,
                        "pattern": pattern,
                        "source_file": document_filename,
                        "extraction_confidence": 0.8,
                        "timestamp": time.time(),
                        "category": "General",
                    }
                )

    return {
        "requirements_list": requirements,
        "extraction_metadata": {
            "total_requirements": len(requirements),
            "patterns_used": len(requirement_patterns),
            "source_file": document_filename,
            "extraction_timestamp": time.time(),
            "extraction_method": "fallback_regex",
        },
    }


# Main execution function for Camunda
def main():
    """Main function called by Camunda."""
    # This would be called by Camunda with the execution context
    # For now, this is a standalone script for testing

    # Test with sample data
    sample_content = """
    The system shall provide user authentication.
    The system must respond within 100ms.
    The component shall interface with external APIs.
    The function will process data efficiently.
    The subsystem should be capable of handling 1000 concurrent users.
    """

    sample_parameters = {
        "confidence_threshold": 0.7,
        "min_text_length": 20,
        "categories_filter": ["Security", "Performance"],
        "custom_patterns": [r"\b(shall|must)\b.*?[.!?]"],
    }

    sample_previous = [
        {
            "id": "req_001",
            "text": "The system shall provide user authentication.",
            "extraction_confidence": 0.8,
            "category": "Security",
        }
    ]

    result = rerun_requirements_extraction(
        sample_content, "test_document.txt", sample_parameters, sample_previous
    )

    print("Rerun Extraction Results:")
    print(f"Total Requirements: {result['rerun_metadata']['total_requirements']}")
    print(f"New Requirements: {result['rerun_metadata']['new_requirements']}")
    print(f"Modified Requirements: {result['rerun_metadata']['modified_requirements']}")
    print(f"Removed Requirements: {result['rerun_metadata']['removed_requirements']}")
    print(f"Rerun Duration: {result['rerun_metadata']['rerun_duration']:.3f}s")

    summary = result["rerun_metadata"]["comparison_summary"]
    print(f"\nComparison Summary:")
    print(f"  Total Changes: {summary['total_changes']}")
    print(f"  Change Percentage: {summary['change_percentage']:.1f}%")
    print(f"  Stability Score: {summary['stability_score']:.1f}%")

    print("\nRerun Requirements:")
    for req in result["rerun_requirements"]:
        print(f"  {req['id']}: {req['text'][:80]}...")
        print(
            f"    Category: {req.get('category', 'Unknown')}, Confidence: {req.get('extraction_confidence', 0):.2f}"
        )


if __name__ == "__main__":
    main()
