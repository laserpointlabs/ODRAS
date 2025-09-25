"""
Unified ID Generator for ODRAS
Generates RFC 3987-compliant 8-digit stable identifiers for ALL resources.

This is the SINGLE SOURCE OF TRUTH for ID generation across ODRAS.
Replaces all UUID generation (both PostgreSQL gen_random_uuid() and Python uuid.uuid4()).

Standards Compliance:
- RFC 3987: Uses only URL-safe characters (A-Z, 0-9, hyphen)
- W3C Cool URIs: IDs never change regardless of label changes
- 8-digit format: XXXX-XXXX (1.6 billion unique combinations)
- Consistent across database and application layers

Usage:
- Database: Use generate_odras_id() function in PostgreSQL
- Python: Use generate_id() from this module
- IRIs: Use generate_8_digit_id() for IRI fragments
"""

import logging
import random
import string
from typing import Optional

logger = logging.getLogger(__name__)


class StableIDGenerator:
    """
    Generates stable 8-digit IDs in XXXX-XXXX format.

    Format: [A-Z0-9]{4}-[A-Z0-9]{4}
    Examples: B459-34TY, X7R9-M2K8, F1A3-9Z5B

    Benefits:
    - Human readable for debugging
    - Typeable when needed
    - URL-safe (no encoding required)
    - Adequate space (36^8 = 1.6 billion combinations)
    - Consistent 9-character format with hyphen
    """

    def __init__(self):
        # Use uppercase letters and digits only (36 characters)
        self.chars = string.ascii_uppercase + string.digits  # A-Z, 0-9

    def generate_8_digit_id(self) -> str:
        """
        Generate 8-digit stable ID in XXXX-XXXX format.

        Returns:
            8-digit ID like "B459-34TY"
        """
        first_part = ''.join(random.choices(self.chars, k=4))
        second_part = ''.join(random.choices(self.chars, k=4))
        return f"{first_part}-{second_part}"

    def validate_8_digit_id(self, id_string: str) -> bool:
        """
        Validate that a string matches 8-digit ID format.

        Args:
            id_string: String to validate

        Returns:
            True if valid 8-digit ID format
        """
        import re
        pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}$'
        return bool(re.match(pattern, id_string))

    def is_8_digit_id(self, id_string: str) -> bool:
        """
        Check if string is a valid 8-digit ID.
        Alias for validate_8_digit_id for convenience.
        """
        return self.validate_8_digit_id(id_string)


# Global instance for convenience
_id_generator = StableIDGenerator()


# ==============================================================================
# UNIFIED ID GENERATION - USE THESE FUNCTIONS EVERYWHERE
# ==============================================================================

def generate_id() -> str:
    """
    UNIFIED ID GENERATOR - Use this everywhere instead of UUID generation.
    
    This is the main function that should replace:
    - PostgreSQL: gen_random_uuid()  
    - Python: uuid.uuid4()
    - Any other UUID generation
    
    Returns:
        8-digit ID like "B459-34TY"
    """
    return _id_generator.generate_8_digit_id()


def generate_8_digit_id() -> str:
    """
    Generate 8-digit stable ID - alias for generate_id().
    Kept for backward compatibility with existing IRI generation code.

    Returns:
        8-digit ID like "B459-34TY"
    """
    return generate_id()


def validate_id(id_string: str) -> bool:
    """
    Validate ODRAS ID format.
    
    Args:
        id_string: String to validate

    Returns:
        True if valid ODRAS ID format
    """
    return _id_generator.validate_8_digit_id(id_string)


def is_valid_id(id_string: str) -> bool:
    """
    Check if string is a valid ODRAS ID.
    
    Args:
        id_string: String to check

    Returns:
        True if valid ODRAS ID format
    """
    return validate_id(id_string)


# ==============================================================================
# LEGACY/COMPATIBILITY FUNCTIONS 
# ==============================================================================

def validate_8_digit_id(id_string: str) -> bool:
    """
    Legacy function - use validate_id() instead.
    Kept for backward compatibility.
    """
    return validate_id(id_string)


def is_8_digit_id(id_string: str) -> bool:
    """
    Legacy function - use is_valid_id() instead.  
    Kept for backward compatibility.
    """
    return is_valid_id(id_string)


# For testing and debugging
if __name__ == "__main__":
    generator = StableIDGenerator()

    # Generate some test IDs
    print("Generated 8-digit IDs:")
    for i in range(10):
        test_id = generator.generate_8_digit_id()
        is_valid = generator.validate_8_digit_id(test_id)
        print(f"  {test_id} - Valid: {is_valid}")

    # Test validation
    print("\nValidation tests:")
    test_cases = [
        "B459-34TY",  # Valid
        "X7R9-M2K8",  # Valid
        "b459-34ty",  # Invalid (lowercase)
        "B459-34T",   # Invalid (too short)
        "B459-34TYZ", # Invalid (too long)
        "B45934TY",   # Invalid (no hyphen)
        "B459-34T!",  # Invalid (special char)
    ]

    for test_case in test_cases:
        is_valid = generator.validate_8_digit_id(test_case)
        print(f"  '{test_case}' - Valid: {is_valid}")
