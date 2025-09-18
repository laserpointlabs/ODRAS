-- Update prefix format constraint to allow compound prefixes
-- Drop the old constraint
ALTER TABLE prefix_registry DROP CONSTRAINT IF EXISTS prefix_format_check;

-- Add new constraint that allows compound prefixes with slashes
-- Format: lowercase letters, numbers, and slashes only, start with letter, 2-50 characters
-- Cannot start or end with slash, no consecutive slashes
ALTER TABLE prefix_registry ADD CONSTRAINT prefix_format_check
CHECK (prefix ~ '^[a-z][a-z0-9/]{1,49}$' AND prefix !~ '^/' AND prefix !~ '/$' AND prefix !~ '//');

-- Update the prefix column length to accommodate compound prefixes
ALTER TABLE prefix_registry ALTER COLUMN prefix TYPE VARCHAR(100);

