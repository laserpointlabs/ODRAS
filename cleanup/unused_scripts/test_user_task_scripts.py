#!/usr/bin/env python3
"""
Test script for user task external scripts.
This script tests the functionality of the new user task scripts.
"""

import sys
import os
import json

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Import the task functions
try:
    from task_handle_user_edits import handle_user_edits
    from task_rerun_extraction import rerun_requirements_extraction

    print("✅ Successfully imported user task scripts")
except ImportError as e:
    print(f"❌ Error importing user task scripts: {e}")
    sys.exit(1)


def test_user_edits():
    """Test the user edits functionality."""
    print("\n🧪 Testing User Edits Functionality...")

    # Sample requirements
    sample_requirements = [
        {
            "id": "req_001",
            "text": "The system shall provide user authentication.",
            "pattern": r"\b(shall|should|must|will)\b.*?[.!?]",
            "source_file": "test_document.txt",
            "extraction_confidence": 0.8,
            "timestamp": 1234567890,
            "category": "Security",
        },
        {
            "id": "req_002",
            "text": "The system must respond within 100ms.",
            "pattern": r"\b(shall|should|must|will)\b.*?[.!?]",
            "source_file": "test_document.txt",
            "extraction_confidence": 0.9,
            "timestamp": 1234567890,
            "category": "Performance",
        },
    ]

    # Sample user edits
    sample_user_edits = [
        {
            "edit_type": "modify",
            "requirement_id": "req_001",
            "field": "text",
            "new_value": "The system shall provide secure user authentication with multi-factor support.",
            "comment": "Enhanced security requirement",
        },
        {
            "edit_type": "add",
            "new_value": "The system must log all authentication attempts.",
            "category": "Security",
            "comment": "Added logging requirement",
        },
        {
            "edit_type": "delete",
            "requirement_id": "req_002",
            "reason": "Performance requirement too strict",
        },
    ]

    try:
        result = handle_user_edits(
            sample_requirements,
            sample_user_edits,
            "Sample document content",
            "test_document.txt",
        )

        print(f"✅ User edits processed successfully")
        print(f"   Total requirements: {result['edit_metadata']['total_requirements']}")
        print(f"   Edits applied: {result['edit_metadata']['edits_applied']}")
        print(f"   Edits rejected: {result['edit_metadata']['edits_rejected']}")
        print(f"   Validation passed: {result['edit_metadata']['validation_passed']}")

        if result["edit_metadata"]["edit_errors"]:
            print(f"   Edit errors: {result['edit_metadata']['edit_errors']}")

        return True

    except Exception as e:
        print(f"❌ Error testing user edits: {e}")
        return False


def test_rerun_extraction():
    """Test the rerun extraction functionality."""
    print("\n🧪 Testing Rerun Extraction Functionality...")

    # Sample document content
    sample_content = """
    The system shall provide user authentication.
    The system must respond within 100ms.
    The component shall interface with external APIs.
    The function will process data efficiently.
    The subsystem should be capable of handling 1000 concurrent users.
    """

    # Sample extraction parameters
    sample_parameters = {
        "confidence_threshold": 0.7,
        "min_text_length": 20,
        "categories_filter": ["Security", "Performance"],
        "custom_patterns": [r"\b(shall|must)\b.*?[.!?]"],
    }

    # Sample previous requirements
    sample_previous = [
        {
            "id": "req_001",
            "text": "The system shall provide user authentication.",
            "extraction_confidence": 0.8,
            "category": "Security",
        }
    ]

    try:
        result = rerun_requirements_extraction(
            sample_content, "test_document.txt", sample_parameters, sample_previous
        )

        print(f"✅ Rerun extraction processed successfully")
        print(f"   Total requirements: {result['rerun_metadata']['total_requirements']}")
        print(f"   New requirements: {len(result['rerun_metadata']['new_requirements'])}")
        print(f"   Modified requirements: {len(result['rerun_metadata']['modified_requirements'])}")
        print(f"   Removed requirements: {len(result['rerun_metadata']['removed_requirements'])}")

        summary = result["rerun_metadata"]["comparison_summary"]
        print(f"   Change percentage: {summary['change_percentage']:.1f}%")
        print(f"   Stability score: {summary['stability_score']:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Error testing rerun extraction: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting User Task Script Tests")
    print("=" * 50)

    # Test user edits
    edits_success = test_user_edits()

    # Test rerun extraction
    rerun_success = test_rerun_extraction()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   User Edits: {'✅ PASSED' if edits_success else '❌ FAILED'}")
    print(f"   Rerun Extraction: {'✅ PASSED' if rerun_success else '❌ FAILED'}")

    if edits_success and rerun_success:
        print("\n🎉 All tests passed! User task scripts are working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

