#!/usr/bin/env python3
"""
External Task Script: Extract Requirements from Document
This script is called by Camunda BPMN process to extract requirements using keyword patterns.

Input Variables (from Camunda):
- document_content: Raw text content of the document
- document_filename: Name of the uploaded file

Output Variables (set in Camunda):
- requirements_list: JSON string of extracted requirements
- extraction_metadata: JSON string of extraction metadata
"""

import json
import re
import time
import sys
import os

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings


def extract_requirements_from_document(document_content: str, document_filename: str) -> dict:
    """
    Extract requirements from document using enhanced keyword patterns.

    Args:
        document_content: Raw text content of the document
        document_filename: Name of the uploaded file

    Returns:
        Dict containing requirements_list and extraction_metadata
    """
    # Enhanced requirement patterns for better extraction
    requirement_patterns = [
        # Modal verb patterns (most common)
        r"\b(shall|should|must|will)\b.*?[.!?]",
        r"\b(required|requirement|needed|necessary)\b.*?[.!?]",
        r"\b(system|component|function|subsystem)\s+(shall|must|will)\b.*?[.!?]",
        # Performance patterns
        r"\b(within|less than|greater than|at least|maximum|minimum)\b.*?[.!?]",
        r"\b(respond|response|latency|throughput)\s+(shall|must|will)\b.*?[.!?]",
        # Interface patterns
        r"\b(interface|connect|communicate|interact|integrate)\b.*?[.!?]",
        r"\b(api|protocol|format|standard)\s+(shall|must|will)\b.*?[.!?]",
        # Constraint patterns
        r"\b(constrained|limited|bounded|not exceed|restricted)\b.*?[.!?]",
        r"\b(security|privacy|compliance)\s+(shall|must|will)\b.*?[.!?]",
        # Capability patterns
        r"\b(capable|ability|capability|enable|support)\b.*?[.!?]",
        r"\b(feature|functionality)\s+(shall|must|will)\b.*?[.!?]",
        # Quality patterns
        r"\b(reliability|availability|maintainability)\s+(shall|must|will)\b.*?[.!?]",
        r"\b(testable|verifiable|measurable)\b.*?[.!?]",
    ]

    requirements = []
    extraction_start_time = time.time()

    for pattern_idx, pattern in enumerate(requirement_patterns):
        matches = re.findall(pattern, document_content, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            if isinstance(match, tuple):
                match = " ".join(match)

            # Clean up the requirement text
            clean_text = match.strip()

            # Filter out very short matches and common false positives
            if len(clean_text) > 15 and not _is_false_positive(clean_text):
                requirements.append(
                    {
                        "id": f"req_{len(requirements):03d}",
                        "text": clean_text,
                        "pattern": pattern,
                        "pattern_id": pattern_idx,
                        "source_file": document_filename,
                        "extraction_confidence": _calculate_confidence(clean_text, pattern),
                        "timestamp": time.time(),
                        "line_number": _find_line_number(document_content, clean_text),
                        "category": _categorize_requirement(clean_text),
                    }
                )

    # Remove duplicates based on text similarity
    unique_requirements = _deduplicate_requirements(requirements)

    extraction_time = time.time() - extraction_start_time

    return {
        "requirements_list": unique_requirements,
        "extraction_metadata": {
            "total_requirements": len(unique_requirements),
            "total_matches": len(requirements),
            "patterns_used": len(requirement_patterns),
            "source_file": document_filename,
            "extraction_timestamp": time.time(),
            "extraction_duration": extraction_time,
            "duplicates_removed": len(requirements) - len(unique_requirements),
            "extraction_method": "regex_patterns",
            "confidence_threshold": 0.6,
        },
    }


def _is_false_positive(text: str) -> bool:
    """Check if extracted text is likely a false positive."""
    false_positive_patterns = [
        r"^\s*(the|a|an)\s+",  # Starts with articles
        r"^\s*[A-Z][a-z]+\s+is\s+",  # "Something is..." statements
        r"^\s*this\s+",  # Starts with "this"
        r"^\s*it\s+",  # Starts with "it"
        r"^\s*we\s+",  # Starts with "we"
        r"^\s*you\s+",  # Starts with "you"
        r"^\s*they\s+",  # Starts with "they"
    ]

    for pattern in false_positive_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    return False


def _calculate_confidence(text: str, pattern: str) -> float:
    """Calculate confidence score for extracted requirement."""
    base_confidence = 0.7

    # Boost confidence for strong modal verbs
    if re.search(r"\b(shall|must)\b", text, re.IGNORECASE):
        base_confidence += 0.2

    # Boost confidence for specific technical terms
    technical_terms = [
        "system",
        "component",
        "interface",
        "function",
        "performance",
        "security",
    ]
    for term in technical_terms:
        if term.lower() in text.lower():
            base_confidence += 0.05

    # Reduce confidence for very long or very short text
    if len(text) > 200:
        base_confidence -= 0.1
    elif len(text) < 20:
        base_confidence -= 0.1

    return min(1.0, max(0.1, base_confidence))


def _find_line_number(content: str, text: str) -> int:
    """Find the approximate line number where text appears."""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if text.strip() in line:
            return i
    return 0


def _categorize_requirement(text: str) -> str:
    """Categorize requirement based on content."""
    text_lower = text.lower()

    if any(word in text_lower for word in ["shall", "must", "will"]):
        if any(word in text_lower for word in ["performance", "speed", "latency", "throughput"]):
            return "Performance"
        elif any(
            word in text_lower
            for word in ["security", "privacy", "authentication", "authorization"]
        ):
            return "Security"
        elif any(word in text_lower for word in ["interface", "api", "protocol", "format"]):
            return "Interface"
        elif any(word in text_lower for word in ["reliability", "availability", "maintainability"]):
            return "Quality"
        else:
            return "Functional"
    else:
        return "Other"


def _deduplicate_requirements(requirements: list) -> list:
    """Remove duplicate requirements based on text similarity."""
    unique_requirements = []
    seen_texts = set()

    for req in requirements:
        # Normalize text for comparison
        normalized_text = re.sub(r"\s+", " ", req["text"].lower().strip())

        # Check if this is a duplicate
        is_duplicate = False
        for seen_text in seen_texts:
            if _calculate_similarity(normalized_text, seen_text) > 0.8:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_requirements.append(req)
            seen_texts.add(normalized_text)

    return unique_requirements


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using simple word overlap."""
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


# Main execution function for Camunda
def main():
    """Main function called by Camunda."""
    # This would be called by Camunda with the execution context
    # For now, this is a standalone script for testing

    # Test with sample content
    sample_content = """
    The system shall provide user authentication.
    The system must respond within 100ms.
    The component shall interface with external APIs.
    The function will process data efficiently.
    The subsystem should be capable of handling 1000 concurrent users.
    The system shall maintain 99.9% availability.
    The interface must support JSON and XML formats.
    """

    result = extract_requirements_from_document(sample_content, "test_document.txt")

    print("Extraction Results:")
    print(f"Total Requirements: {result['extraction_metadata']['total_requirements']}")
    print(f"Extraction Time: {result['extraction_metadata']['extraction_duration']:.3f}s")
    print("\nRequirements:")
    for req in result["requirements_list"]:
        print(f"  {req['id']}: {req['text'][:80]}...")
        print(f"    Category: {req['category']}, Confidence: {req['extraction_confidence']:.2f}")


if __name__ == "__main__":
    main()

