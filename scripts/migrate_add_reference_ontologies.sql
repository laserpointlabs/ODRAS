-- Migration script to add is_reference column to ontologies_registry table
-- Run this script if you have an existing database that needs the new column

-- Add the is_reference column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'ontologies_registry' 
        AND column_name = 'is_reference'
    ) THEN
        ALTER TABLE public.ontologies_registry 
        ADD COLUMN is_reference BOOLEAN DEFAULT FALSE;
        
        -- Add a comment to document the column
        COMMENT ON COLUMN public.ontologies_registry.is_reference IS 'TRUE for admin-created reference ontologies that can be imported by other projects';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'ontologies_registry' 
AND column_name = 'is_reference';
