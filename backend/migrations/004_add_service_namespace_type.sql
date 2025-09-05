-- Add service namespace type to existing constraint
-- This migration updates the namespace_registry table to include 'service' as a valid type

-- First, drop the existing constraint
ALTER TABLE namespace_registry DROP CONSTRAINT namespace_registry_type_check;

-- Add the new constraint with 'service' included
ALTER TABLE namespace_registry ADD CONSTRAINT namespace_registry_type_check 
    CHECK (type IN ('core', 'service', 'domain', 'program', 'project', 'industry', 'vocab', 'shapes', 'align'));

