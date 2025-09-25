-- Fix data type mismatch in projects.created_by column
-- This column should be UUID to match users.user_id, not VARCHAR

-- Only run this if created_by is currently VARCHAR type
DO $$
BEGIN
    -- Check if created_by is VARCHAR type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects'
        AND column_name = 'created_by'
        AND data_type = 'character varying'
    ) THEN
        -- First, clear any invalid data
        UPDATE public.projects SET created_by = NULL WHERE created_by = '' OR created_by !~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';

        -- Change the column type to UUID
        ALTER TABLE public.projects ALTER COLUMN created_by TYPE UUID USING
          CASE
            WHEN created_by IS NULL OR created_by = '' THEN NULL
            WHEN created_by ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' THEN created_by::UUID
            ELSE NULL
          END;
    END IF;
END
$$;

-- Add foreign key constraint to users table (only if it doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_projects_created_by'
        AND table_name = 'projects'
    ) THEN
        ALTER TABLE public.projects
        ADD CONSTRAINT fk_projects_created_by
        FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_projects_created_by_uuid ON projects(created_by);
