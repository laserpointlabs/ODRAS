-- Migration 015: Installation-Specific IRI Management
-- Implements installation-specific IRI structure for better military/government compliance

-- Add IRI columns to existing tables
ALTER TABLE files 
ADD COLUMN IF NOT EXISTS iri VARCHAR(1000) UNIQUE;

ALTER TABLE knowledge_assets 
ADD COLUMN IF NOT EXISTS iri VARCHAR(1000) UNIQUE;

ALTER TABLE public.projects 
ADD COLUMN IF NOT EXISTS iri VARCHAR(1000) UNIQUE;

ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS iri VARCHAR(1000) UNIQUE;

-- Add installation configuration table
CREATE TABLE IF NOT EXISTS installation_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_name VARCHAR(255) NOT NULL,           -- 'XMA-ADT', 'AFIT-Research'
    installation_type VARCHAR(50) NOT NULL,            -- 'usn', 'usaf', 'usa', 'industry'
    top_level_domain VARCHAR(10) NOT NULL,             -- 'mil', 'gov', 'com', 'edu'
    base_uri VARCHAR(500) NOT NULL UNIQUE,             -- 'https://xma-adt.usn.mil'
    organization VARCHAR(255) NOT NULL,                -- 'U.S. Navy XMA-ADT'
    program_office VARCHAR(255),                       -- 'Naval Air Systems Command'
    authority_contact VARCHAR(255),                    -- Responsible authority
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default installation config
INSERT INTO installation_config (
    installation_name, 
    installation_type, 
    top_level_domain, 
    base_uri, 
    organization,
    program_office
) VALUES (
    'XMA-ADT',
    'usn', 
    'mil',
    'https://xma-adt.usn.mil',
    'U.S. Navy XMA-ADT',
    'Naval Air Systems Command'
) ON CONFLICT (base_uri) DO NOTHING;

-- Create indexes for IRI lookups
CREATE INDEX IF NOT EXISTS idx_files_iri ON files(iri);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_iri ON knowledge_assets(iri);
CREATE INDEX IF NOT EXISTS idx_projects_iri ON public.projects(iri);
CREATE INDEX IF NOT EXISTS idx_users_iri ON public.users(iri);
CREATE INDEX IF NOT EXISTS idx_installation_config_base_uri ON installation_config(base_uri);

-- Create IRI resolution function
CREATE OR REPLACE FUNCTION resolve_iri(target_iri VARCHAR(1000))
RETURNS TABLE(
    resource_type VARCHAR(50),
    resource_id UUID,
    resource_data JSONB
) AS $$
BEGIN
    -- Check files
    IF EXISTS (SELECT 1 FROM files WHERE iri = target_iri) THEN
        RETURN QUERY
        SELECT 'file'::VARCHAR(50), f.id, 
               jsonb_build_object(
                   'type', 'file',
                   'id', f.id,
                   'filename', f.filename,
                   'content_type', f.content_type,
                   'size', f.file_size,
                   'created_at', f.created_at,
                   'iri', f.iri
               )
        FROM files f WHERE f.iri = target_iri;
        RETURN;
    END IF;
    
    -- Check knowledge assets
    IF EXISTS (SELECT 1 FROM knowledge_assets WHERE iri = target_iri) THEN
        RETURN QUERY
        SELECT 'knowledge_asset'::VARCHAR(50), ka.id,
               jsonb_build_object(
                   'type', 'knowledge_asset',
                   'id', ka.id,
                   'title', ka.title,
                   'document_type', ka.document_type,
                   'status', ka.status,
                   'traceability_status', ka.traceability_status,
                   'created_at', ka.created_at,
                   'iri', ka.iri
               )
        FROM knowledge_assets ka WHERE ka.iri = target_iri;
        RETURN;
    END IF;
    
    -- Check projects
    IF EXISTS (SELECT 1 FROM public.projects WHERE iri = target_iri) THEN
        RETURN QUERY
        SELECT 'project'::VARCHAR(50), p.project_id,
               jsonb_build_object(
                   'type', 'project',
                   'id', p.project_id,
                   'name', p.name,
                   'description', p.description,
                   'domain', p.domain,
                   'created_at', p.created_at,
                   'iri', p.iri
               )
        FROM public.projects p WHERE p.iri = target_iri;
        RETURN;
    END IF;
    
    -- Check users
    IF EXISTS (SELECT 1 FROM public.users WHERE iri = target_iri) THEN
        RETURN QUERY
        SELECT 'user'::VARCHAR(50), u.user_id,
               jsonb_build_object(
                   'type', 'user',
                   'id', u.user_id,
                   'username', u.username,
                   'display_name', u.display_name,
                   'created_at', u.created_at,
                   'iri', u.iri
               )
        FROM public.users u WHERE u.iri = target_iri;
        RETURN;
    END IF;
    
    -- Resource not found
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE installation_config IS 'Installation-specific configuration for IRI generation';
COMMENT ON COLUMN files.iri IS 'Globally unique IRI for this file resource';
COMMENT ON COLUMN knowledge_assets.iri IS 'Globally unique IRI for this knowledge asset';
COMMENT ON COLUMN public.projects.iri IS 'Globally unique IRI for this project';
COMMENT ON COLUMN public.users.iri IS 'Globally unique IRI for this user';
COMMENT ON FUNCTION resolve_iri IS 'Resolves an IRI to its resource type and metadata';

