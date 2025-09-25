# Unified ID Generation System for ODRAS

## Overview

ODRAS now uses a **unified 8-digit ID generation system** instead of traditional 32-character UUIDs. This provides consistency, human readability, and maintains RFC 3987 compliance for IRI generation.

## Key Features

- **Single Source of Truth**: All ID generation uses the same module
- **8-Digit Format**: `XXXX-XXXX` using uppercase letters and digits (A-Z, 0-9)
- **1.6 Billion Combinations**: 36^8 unique possibilities
- **Human Readable**: Easy to type, debug, and communicate
- **URL Safe**: No encoding required for web use
- **RFC 3987 Compliant**: Perfect for IRI/URI generation

## Usage

### Python Services

```python
from backend.services.stable_id_generator import generate_id, validate_id

# Generate a new ID
new_id = generate_id()  # Returns: "B459-34TY"

# Validate an ID
is_valid = validate_id("B459-34TY")  # Returns: True
```

### PostgreSQL Database

```sql
-- Generate new ID
SELECT generate_odras_id();  -- Returns: 'C00P-O3CU'

-- Validate ID format
SELECT validate_odras_id('B459-34TY');  -- Returns: true

-- Check if text is valid ID
SELECT is_odras_id('some-text');  -- Returns: false
```

### Table Creation (New Tables)

For new tables, use `generate_odras_id()` instead of `gen_random_uuid()`:

```sql
CREATE TABLE my_table (
    id VARCHAR(9) PRIMARY KEY DEFAULT generate_odras_id(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Migration from UUIDs

### What We've Changed

1. **Python Services**:
   - ✅ `backend/services/db.py` - Updated to use `generate_id()`
   - ✅ `backend/services/qdrant_service.py` - Updated to use `generate_id()`
   - ✅ `scripts/step_store_vector_chunks.py` - Updated to use `generate_id()`
   - ✅ `tests/conftest.py` - Updated to use `generate_id()`

2. **Database Functions**:
   - ✅ Created `generate_odras_id()` function to replace `gen_random_uuid()`
   - ✅ Added validation functions: `validate_odras_id()` and `is_odras_id()`

3. **Existing Tables**:
   - Current tables still use UUID columns for backward compatibility
   - New `stable_id` columns added using VARCHAR(9) format
   - Future migration will convert primary keys to 8-digit format

## Functions Reference

### Python Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `generate_id()` | **MAIN FUNCTION** - Use everywhere | `str` - 8-digit ID |
| `validate_id(id)` | Validate ODRAS ID format | `bool` |
| `is_valid_id(id)` | Alias for validate_id() | `bool` |
| `generate_8_digit_id()` | Legacy alias for generate_id() | `str` |

### PostgreSQL Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `generate_odras_id()` | **MAIN FUNCTION** - Replaces gen_random_uuid() | `VARCHAR(9)` |
| `validate_odras_id(id)` | Validate ODRAS ID format | `BOOLEAN` |
| `is_odras_id(text)` | Check if text is valid ODRAS ID | `BOOLEAN` |

## Implementation Details

### ID Format Specification

- **Pattern**: `^[A-Z0-9]{4}-[A-Z0-9]{4}$`
- **Length**: Always 9 characters (including hyphen)
- **Characters**: Uppercase letters (A-Z) and digits (0-9)
- **Separator**: Single hyphen at position 5

### Examples of Valid IDs

- `B459-34TY`
- `X7R9-M2K8`
- `F1A3-9Z5B`
- `9ABC-DEF0`
- `ZZZZ-9999`

### Invalid Examples

- `b459-34ty` (lowercase)
- `B459-34T` (too short)
- `B459-34TYZ` (too long)
- `B45934TY` (no hyphen)
- `B459-34T!` (special characters)

## File Structure

```
backend/services/stable_id_generator.py  # Main unified module
backend/migrations/017_unified_id_generation.sql  # Database functions
```

## Benefits

1. **Consistency**: Same format across database and application
2. **Debuggability**: Human-readable IDs make debugging easier
3. **Performance**: Shorter strings = better database performance
4. **Maintainability**: Single module to maintain instead of scattered UUID usage
5. **Standards Compliance**: Perfect for semantic web and IRI generation

## Future Work

- **Column Type Migration**: Convert existing UUID columns to VARCHAR(9)
- **Full System Adoption**: Update remaining services to use unified IDs
- **Documentation**: Update API docs to reflect new ID format

## Testing

The unified ID system has been tested:

- ✅ PostgreSQL functions generate valid 8-digit IDs
- ✅ Python module generates valid 8-digit IDs
- ✅ Validation functions work correctly
- ✅ Integration with existing services (Qdrant, database)

## Legacy Support

For backward compatibility:
- Existing UUID columns continue to work
- Legacy function names still available
- Migration path preserves existing functionality

---

**Migration 017**: `017_unified_id_generation.sql` - Adds database functions
**Module**: `backend/services/stable_id_generator.py` - Python implementation
