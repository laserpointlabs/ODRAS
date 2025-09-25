-- Migration 017: Unified ID Generation System
-- Replace gen_random_uuid() with generate_odras_id() for consistent 8-digit IDs across the system

-- Create unified ODRAS ID generation function 
-- This replaces gen_random_uuid() and generates 8-digit IDs in XXXX-XXXX format
CREATE OR REPLACE FUNCTION generate_odras_id() RETURNS VARCHAR(9) AS $$
DECLARE
    chars VARCHAR(36) := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    result VARCHAR(9);
    first_part VARCHAR(4);
    second_part VARCHAR(4);
    i INTEGER;
BEGIN
    -- Generate first 4 characters
    first_part := '';
    FOR i IN 1..4 LOOP
        first_part := first_part || substr(chars, (random() * 35)::integer + 1, 1);
    END LOOP;

    -- Generate second 4 characters  
    second_part := '';
    FOR i IN 1..4 LOOP
        second_part := second_part || substr(chars, (random() * 35)::integer + 1, 1);
    END LOOP;

    result := first_part || '-' || second_part;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the unified ID system
COMMENT ON FUNCTION generate_odras_id() IS 
'Unified ODRAS ID generator - replaces gen_random_uuid() across the system.
Generates 8-digit IDs in XXXX-XXXX format using uppercase letters and digits.
This is the SINGLE SOURCE OF TRUTH for ID generation in ODRAS.
Format: [A-Z0-9]{4}-[A-Z0-9]{4} (1.6 billion unique combinations)';

-- Create validation function for ODRAS IDs
CREATE OR REPLACE FUNCTION validate_odras_id(id_text VARCHAR(9)) RETURNS BOOLEAN AS $$
BEGIN
    -- Check if the input matches the XXXX-XXXX pattern
    RETURN id_text ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_odras_id(VARCHAR) IS 
'Validates ODRAS ID format - ensures ID matches XXXX-XXXX pattern with uppercase letters and digits only.';

-- Create helper function to check if a string is a valid ODRAS ID
CREATE OR REPLACE FUNCTION is_odras_id(id_text TEXT) RETURNS BOOLEAN AS $$
BEGIN
    -- Handle NULL input
    IF id_text IS NULL OR length(id_text) != 9 THEN
        RETURN FALSE;
    END IF;
    
    RETURN validate_odras_id(id_text::VARCHAR(9));
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION is_odras_id(TEXT) IS 
'Convenience function to check if any text string is a valid ODRAS ID format.';

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 017_unified_id_generation.sql completed successfully';
    RAISE NOTICE 'Created unified ODRAS ID generation functions:';
    RAISE NOTICE '  - generate_odras_id(): Replaces gen_random_uuid()';
    RAISE NOTICE '  - validate_odras_id(): Validates XXXX-XXXX format';
    RAISE NOTICE '  - is_odras_id(): Checks if text is valid ODRAS ID';
    RAISE NOTICE 'Use generate_odras_id() instead of gen_random_uuid() for all new tables';
END $$;
