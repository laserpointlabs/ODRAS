-- Create projects table for ODRAS project management
-- Projects are created within namespaces and contain ontologies

-- Add missing columns to existing projects table
-- Note: namespace_id foreign key will be added in migration 010 after namespace_registry is created
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS namespace_id UUID;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS domain VARCHAR(255);
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deprecated'));

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_projects_namespace_id ON projects(namespace_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_projects_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_projects_updated_at();

