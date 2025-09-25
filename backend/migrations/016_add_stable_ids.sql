-- Add 8-digit stable IDs to all resource tables
-- This migration adds stable_id columns for the new 8-digit ID system

-- Add stable_id to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS stable_id VARCHAR(9) UNIQUE;

-- Add index for stable_id lookups
CREATE INDEX IF NOT EXISTS idx_projects_stable_id ON projects(stable_id);

-- Add stable_id to ontologies_registry table
ALTER TABLE ontologies_registry ADD COLUMN IF NOT EXISTS stable_id VARCHAR(9) UNIQUE;
CREATE INDEX IF NOT EXISTS idx_ontologies_stable_id ON ontologies_registry(stable_id);

-- Add stable_id to files table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'files') THEN
        ALTER TABLE files ADD COLUMN IF NOT EXISTS stable_id VARCHAR(9) UNIQUE;
        CREATE INDEX IF NOT EXISTS idx_files_stable_id ON files(stable_id);
    END IF;
END $$;

-- Add stable_id to knowledge_assets table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'knowledge_assets') THEN
        ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS stable_id VARCHAR(9) UNIQUE;
        CREATE INDEX IF NOT EXISTS idx_knowledge_assets_stable_id ON knowledge_assets(stable_id);
    END IF;
END $$;

-- Add stable_id to requirements table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'requirements') THEN
        ALTER TABLE requirements ADD COLUMN IF NOT EXISTS stable_id VARCHAR(9) UNIQUE;
        CREATE INDEX IF NOT EXISTS idx_requirements_stable_id ON requirements(stable_id);
    END IF;
END $$;

-- Create function to generate 8-digit stable IDs in database
CREATE OR REPLACE FUNCTION generate_8_digit_id() RETURNS VARCHAR(9) AS $$
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

-- Update existing records with stable IDs (only if they don't already have one)
DO $$
DECLARE
    rec RECORD;
    new_id VARCHAR(9);
    max_attempts INTEGER := 100;
    attempt INTEGER;
BEGIN
    -- Update projects without stable_id
    FOR rec IN SELECT project_id FROM projects WHERE stable_id IS NULL LOOP
        attempt := 0;
        LOOP
            new_id := generate_8_digit_id();

            -- Check if this ID is already used in projects
            IF NOT EXISTS (SELECT 1 FROM projects WHERE stable_id = new_id) THEN
                UPDATE projects SET stable_id = new_id WHERE project_id = rec.project_id;
                EXIT;
            END IF;

            attempt := attempt + 1;
            IF attempt >= max_attempts THEN
                RAISE EXCEPTION 'Failed to generate unique stable_id for project % after % attempts', rec.project_id, max_attempts;
            END IF;
        END LOOP;
    END LOOP;

    -- Update ontologies_registry without stable_id
    FOR rec IN SELECT id FROM ontologies_registry WHERE stable_id IS NULL LOOP
        attempt := 0;
        LOOP
            new_id := generate_8_digit_id();

            -- Check if this ID is already used in ontologies
            IF NOT EXISTS (SELECT 1 FROM ontologies_registry WHERE stable_id = new_id) THEN
                UPDATE ontologies_registry SET stable_id = new_id WHERE id = rec.id;
                EXIT;
            END IF;

            attempt := attempt + 1;
            IF attempt >= max_attempts THEN
                RAISE EXCEPTION 'Failed to generate unique stable_id for ontology % after % attempts', rec.id, max_attempts;
            END IF;
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Successfully generated stable IDs for existing projects and ontologies';
END $$;

-- Add constraints to ensure stable_id format is correct (only if not exists)
DO $$
BEGIN
    -- Add constraint to projects table if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'projects_stable_id_format'
        AND table_name = 'projects'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_stable_id_format
            CHECK (stable_id ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$');
    END IF;

    -- Add constraint to ontologies_registry table if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'ontologies_stable_id_format'
        AND table_name = 'ontologies_registry'
    ) THEN
        ALTER TABLE ontologies_registry ADD CONSTRAINT ontologies_stable_id_format
            CHECK (stable_id ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$');
    END IF;

    -- Add similar constraints to other tables if they exist
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'files') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'files_stable_id_format'
            AND table_name = 'files'
        ) THEN
            ALTER TABLE files ADD CONSTRAINT files_stable_id_format
                CHECK (stable_id ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$');
        END IF;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'knowledge_assets') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'knowledge_assets_stable_id_format'
            AND table_name = 'knowledge_assets'
        ) THEN
            ALTER TABLE knowledge_assets ADD CONSTRAINT knowledge_assets_stable_id_format
                CHECK (stable_id ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$');
        END IF;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'requirements') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'requirements_stable_id_format'
            AND table_name = 'requirements'
        ) THEN
            ALTER TABLE requirements ADD CONSTRAINT requirements_stable_id_format
                CHECK (stable_id ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$');
        END IF;
    END IF;
END $$;

-- Create view for easy lookups by stable_id (with correct column names)
CREATE OR REPLACE VIEW stable_id_lookup AS
SELECT
    'project' as resource_type,
    stable_id,
    project_id::text as internal_id,  -- Cast UUID to text for consistency
    name as resource_name,
    description as resource_description,
    created_at
FROM projects
WHERE stable_id IS NOT NULL

UNION ALL

SELECT
    'ontology' as resource_type,
    stable_id,
    id::text as internal_id,  -- Cast UUID to text for consistency
    label as resource_name,  -- Fixed: ontologies_registry has 'label' not 'name'
    NULL as resource_description,  -- ontologies_registry doesn't have description
    created_at
FROM ontologies_registry
WHERE stable_id IS NOT NULL;

-- Add comment explaining the stable ID system
COMMENT ON FUNCTION generate_8_digit_id() IS
'Generates RFC 3987-compliant 8-digit stable identifiers in XXXX-XXXX format using uppercase letters and digits only.';

COMMENT ON VIEW stable_id_lookup IS
'Unified view for looking up any resource by its 8-digit stable ID across all resource types.';

-- Log successful completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 016_add_stable_ids.sql completed successfully';
    RAISE NOTICE 'Added stable_id columns to projects and ontologies_registry tables';
    RAISE NOTICE 'Generated stable IDs for existing records';
    RAISE NOTICE 'Added format constraints and indexes';
    RAISE NOTICE 'Created stable_id_lookup view for unified lookups';
END $$;
