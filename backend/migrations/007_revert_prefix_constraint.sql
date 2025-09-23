-- Revert prefix constraint to only allow single-word prefixes
-- This removes the compound prefix functionality and enforces atomic prefixes only

ALTER TABLE prefix_registry DROP CONSTRAINT prefix_format_check;
ALTER TABLE prefix_registry ADD CONSTRAINT prefix_format_check
CHECK (prefix ~ '^[a-z][a-z0-9]{1,19}$');

