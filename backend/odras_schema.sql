-- =====================================
-- ODRAS Database Schema
-- Consolidated Alpha Schema - Single File
-- =====================================
-- This replaces all individual migration files during alpha phase
-- Once we have production deployments, we'll switch back to migrations

-- =====================================
-- EXTENSIONS
-- =====================================

-- Enable UUID extension for auto-generated UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================
-- AUTHENTICATION & USER MANAGEMENT
-- =====================================

-- Users table with authentication support
CREATE TABLE IF NOT EXISTS public.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    salt VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    iri VARCHAR(1000) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Authentication tokens table for persistent sessions
CREATE TABLE IF NOT EXISTS public.auth_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of the token for security
    user_id UUID NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================
-- PROJECT & NAMESPACE MANAGEMENT
-- =====================================

-- Installation configuration for IRI generation
CREATE TABLE IF NOT EXISTS installation_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_name VARCHAR(255) NOT NULL,           -- 'XMA-ADT', 'AFIT-Research'
    installation_type VARCHAR(50) NOT NULL,            -- 'usn', 'usaf', 'usa', 'industry'
    top_level_domain VARCHAR(10) NOT NULL,             -- 'mil', 'gov', 'com', 'edu'
    base_uri VARCHAR(500) NOT NULL UNIQUE,             -- 'https://xma-adt.usn.mil'
    organization VARCHAR(255) NOT NULL,                -- 'U.S. Navy XMA-ADT'
    program_office VARCHAR(255),                       -- 'Naval Air Systems Command'
    authority_contact VARCHAR(255),                    -- Responsible authority
    rag_implementation VARCHAR(20) DEFAULT 'hardcoded' NOT NULL, -- 'hardcoded' or 'bpmn'
    rag_bpmn_model VARCHAR(100),                       -- Selected BPMN model key
    rag_model_version VARCHAR(20),                     -- Selected model version
    file_processing_implementation VARCHAR(20) DEFAULT 'hardcoded' NOT NULL, -- 'hardcoded' or 'bpmn'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prefix registry for organizational prefixes
CREATE TABLE IF NOT EXISTS prefix_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prefix VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    owner VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'archived')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT prefix_format_check CHECK (prefix ~ '^[a-z][a-z0-9]{1,19}$')
);

-- Domain registry for project classification
CREATE TABLE IF NOT EXISTS domain_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    owner VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'archived')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT domain_format_check CHECK (domain ~ '^[a-z][a-z0-9-]{1,49}$')
);

-- Namespace registry for ontology management
CREATE TABLE IF NOT EXISTS namespace_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('core', 'service', 'domain', 'program', 'project', 'industry', 'vocab', 'shapes', 'align')),
    path VARCHAR(500) NOT NULL, -- dod/core, usn/core, etc.
    prefix VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'released', 'deprecated')),
    owners TEXT[], -- email addresses
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, type),
    UNIQUE(prefix)
);

-- Namespace version management
CREATE TABLE IF NOT EXISTS namespace_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL, -- 2025-09-01, v1.0.0
    version_iri VARCHAR(1000) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'released', 'deprecated')),
    created_at TIMESTAMP DEFAULT NOW(),
    released_at TIMESTAMP NULL,
    UNIQUE(namespace_id, version)
);

-- Namespace class definitions (versioned)
CREATE TABLE IF NOT EXISTS namespace_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES namespace_versions(id) ON DELETE CASCADE,
    local_name VARCHAR(255) NOT NULL, -- Class1, AirVehicle
    label VARCHAR(500) NOT NULL, -- "Air Vehicle", "Mission"
    iri VARCHAR(1000) NOT NULL, -- Full IRI
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(version_id, local_name)
);

-- Namespace import dependencies
CREATE TABLE IF NOT EXISTS namespace_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_version_id UUID REFERENCES namespace_versions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_namespace_id, target_namespace_id)
);

-- Projects table
CREATE TABLE IF NOT EXISTS public.projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    domain VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deprecated')),
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    iri VARCHAR(1000) UNIQUE
);

-- Project membership
CREATE TABLE IF NOT EXISTS public.project_members (
    user_id UUID NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(project_id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, project_id)
);

-- Ontologies registry per project (required for DAS ontology context)
CREATE TABLE IF NOT EXISTS public.ontologies_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    graph_iri TEXT UNIQUE NOT NULL,
    label TEXT,
    role VARCHAR(20) DEFAULT 'base', -- base | import | unknown
    is_reference BOOLEAN DEFAULT FALSE, -- TRUE for admin-created reference ontologies
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================
-- FILE & KNOWLEDGE MANAGEMENT
-- =====================================

-- Files table for knowledge management compatibility
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    content_type VARCHAR(200),
    file_size BIGINT NOT NULL,
    storage_backend VARCHAR(50) DEFAULT 'local',
    storage_path VARCHAR(500),
    storage_key VARCHAR(500), -- For cloud storage backends
    hash_md5 VARCHAR(32),
    hash_sha256 VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '{}',
    iri VARCHAR(1000) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    is_deleted BOOLEAN DEFAULT FALSE,
    -- Processing status fields
    status VARCHAR(50) DEFAULT 'new', -- new, processing, processed, failed
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT
);

-- File content table (for database storage backend)
CREATE TABLE IF NOT EXISTS file_content (
    file_id UUID PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    content BYTEA NOT NULL,
    compressed BOOLEAN DEFAULT FALSE,
    encryption_key_id VARCHAR(255)
);

-- Knowledge Assets Table
CREATE TABLE IF NOT EXISTS knowledge_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    project_id UUID NOT NULL,
    title VARCHAR(512) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
    content_summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    iri VARCHAR(1000) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version VARCHAR(20) DEFAULT '1.0.0',
    status VARCHAR(20) DEFAULT 'active', -- active, archived, processing, failed
    processing_stats JSONB DEFAULT '{}'::jsonb,
    -- Public asset functionality
    is_public BOOLEAN DEFAULT FALSE,
    made_public_at TIMESTAMPTZ,
    made_public_by VARCHAR(255),
    -- Orphaned assets management
    traceability_status VARCHAR(50) DEFAULT 'linked' CHECK (traceability_status IN ('linked', 'orphaned', 'archived')),
    orphaned_at TIMESTAMPTZ,
    orphaned_reason VARCHAR(255)
);

-- Knowledge Chunks Table
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES knowledge_assets(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    chunk_type VARCHAR(50) NOT NULL DEFAULT 'text', -- text, title, table, list, code
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding_model VARCHAR(100),
    qdrant_point_id UUID, -- Reference to Qdrant vector
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(asset_id, sequence_number)
);

-- Knowledge Relationships Table (for graph relationships)
CREATE TABLE IF NOT EXISTS knowledge_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_asset_id UUID REFERENCES knowledge_assets(id) ON DELETE CASCADE,
    target_asset_id UUID REFERENCES knowledge_assets(id) ON DELETE CASCADE,
    source_chunk_id UUID REFERENCES knowledge_chunks(id) ON DELETE SET NULL,
    target_chunk_id UUID REFERENCES knowledge_chunks(id) ON DELETE SET NULL,
    relationship_type VARCHAR(100) NOT NULL, -- references, depends_on, implements, contains, etc.
    confidence_score REAL DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    neo4j_relationship_id BIGINT, -- Reference to Neo4j relationship
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_asset_id, target_asset_id, relationship_type)
);

-- Processing Jobs Table (for tracking async processing)
CREATE TABLE IF NOT EXISTS knowledge_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES knowledge_assets(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- chunk, embed, extract_relationships, full_process
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- =====================================
-- INDEXES FOR PERFORMANCE
-- =====================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON public.users(is_admin);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_iri ON public.users(iri);

-- Auth tokens indexes
CREATE INDEX IF NOT EXISTS idx_auth_tokens_token_hash ON public.auth_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON public.auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON public.auth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_is_active ON public.auth_tokens(is_active);

-- Installation config indexes
CREATE INDEX IF NOT EXISTS idx_installation_config_base_uri ON installation_config(base_uri);

-- Prefix registry indexes
CREATE INDEX IF NOT EXISTS idx_prefix_registry_prefix ON prefix_registry(prefix);
CREATE INDEX IF NOT EXISTS idx_prefix_registry_status ON prefix_registry(status);

-- Domain registry indexes
CREATE INDEX IF NOT EXISTS idx_domain_registry_domain ON domain_registry(domain);
CREATE INDEX IF NOT EXISTS idx_domain_registry_status ON domain_registry(status);

-- Namespace registry indexes
CREATE INDEX IF NOT EXISTS idx_namespace_registry_type ON namespace_registry(type);
CREATE INDEX IF NOT EXISTS idx_namespace_registry_status ON namespace_registry(status);
CREATE INDEX IF NOT EXISTS idx_namespace_versions_namespace_id ON namespace_versions(namespace_id);
CREATE INDEX IF NOT EXISTS idx_namespace_versions_status ON namespace_versions(status);
CREATE INDEX IF NOT EXISTS idx_namespace_classes_version_id ON namespace_classes(version_id);
CREATE INDEX IF NOT EXISTS idx_namespace_imports_source ON namespace_imports(source_namespace_id);
CREATE INDEX IF NOT EXISTS idx_namespace_imports_target ON namespace_imports(target_namespace_id);

-- Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_name ON public.projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_namespace_id ON public.projects(namespace_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON public.projects(created_by);
CREATE INDEX IF NOT EXISTS idx_projects_iri ON public.projects(iri);
CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON public.project_members(user_id);
CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON public.project_members(project_id);

-- Files indexes
CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_files_hash_md5 ON files(hash_md5);
CREATE INDEX IF NOT EXISTS idx_files_hash_sha256 ON files(hash_sha256);
CREATE INDEX IF NOT EXISTS idx_files_metadata ON files USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_files_tags ON files USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_files_storage_backend ON files(storage_backend);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);
CREATE INDEX IF NOT EXISTS idx_files_iri ON files(iri);

-- Knowledge assets indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_assets(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_assets(document_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge_assets(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_file ON knowledge_assets(source_file_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_metadata ON knowledge_assets USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge_assets(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_public ON knowledge_assets(is_public);
CREATE INDEX IF NOT EXISTS idx_knowledge_public_project ON knowledge_assets(is_public, project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_traceability_status ON knowledge_assets(traceability_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_orphaned_at ON knowledge_assets(orphaned_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_assets_iri ON knowledge_assets(iri);

-- Knowledge chunks indexes
CREATE INDEX IF NOT EXISTS idx_chunks_asset ON knowledge_chunks(asset_id);
CREATE INDEX IF NOT EXISTS idx_chunks_sequence ON knowledge_chunks(asset_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON knowledge_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_qdrant ON knowledge_chunks(qdrant_point_id);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON knowledge_chunks USING GIN(metadata);

-- Knowledge relationships indexes
CREATE INDEX IF NOT EXISTS idx_relationships_source ON knowledge_relationships(source_asset_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON knowledge_relationships(target_asset_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON knowledge_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_neo4j ON knowledge_relationships(neo4j_relationship_id);

-- Processing jobs indexes
CREATE INDEX IF NOT EXISTS idx_processing_jobs_asset ON knowledge_processing_jobs(asset_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON knowledge_processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_type ON knowledge_processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created ON knowledge_processing_jobs(created_at);

-- =====================================
-- TRIGGERS AND FUNCTIONS
-- =====================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to update files updated_at timestamp
CREATE OR REPLACE FUNCTION update_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to update users updated_at timestamp
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to update projects updated_at timestamp
CREATE OR REPLACE FUNCTION update_projects_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to update domain registry updated_at timestamp
CREATE OR REPLACE FUNCTION update_domain_registry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to mark assets as orphaned when source file is deleted
CREATE OR REPLACE FUNCTION mark_orphaned_asset()
RETURNS TRIGGER AS $$
BEGIN
    -- When source_file_id becomes NULL, mark as orphaned
    IF OLD.source_file_id IS NOT NULL AND NEW.source_file_id IS NULL THEN
        NEW.traceability_status = 'orphaned';
        NEW.orphaned_at = NOW();
        NEW.orphaned_reason = 'Source file deleted';
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM public.auth_tokens
    WHERE expires_at < NOW() OR is_active = FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to update token last used timestamp
CREATE OR REPLACE FUNCTION update_token_last_used(token_hash_param VARCHAR(64))
RETURNS void AS $$
BEGIN
    UPDATE public.auth_tokens
    SET last_used_at = NOW()
    WHERE token_hash = token_hash_param AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to resolve IRIs to resources
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

-- =====================================
-- TRIGGERS
-- =====================================

-- Trigger for files updated_at
CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON files
    FOR EACH ROW EXECUTE FUNCTION update_files_updated_at();

-- Trigger for knowledge_assets updated_at
CREATE TRIGGER update_knowledge_assets_updated_at
    BEFORE UPDATE ON knowledge_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for users updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_users_updated_at();

-- Trigger for projects updated_at
CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_projects_updated_at();

-- Trigger for ontologies_registry updated_at
CREATE TRIGGER update_ontologies_registry_updated_at
    BEFORE UPDATE ON public.ontologies_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for domain registry updated_at
DROP TRIGGER IF EXISTS trigger_domain_registry_updated_at ON domain_registry;
CREATE TRIGGER trigger_domain_registry_updated_at
    BEFORE UPDATE ON domain_registry
    FOR EACH ROW EXECUTE FUNCTION update_domain_registry_updated_at();

-- Trigger to mark assets as orphaned when source file is deleted
CREATE TRIGGER trigger_mark_orphaned_asset
    BEFORE UPDATE ON knowledge_assets
    FOR EACH ROW
    WHEN (OLD.source_file_id IS DISTINCT FROM NEW.source_file_id)
    EXECUTE FUNCTION mark_orphaned_asset();

-- =====================================
-- DEFAULT DATA
-- =====================================

-- Insert default installation config
INSERT INTO installation_config (
    installation_name,
    installation_type,
    top_level_domain,
    base_uri,
    organization,
    program_office,
    rag_implementation,
    rag_bpmn_model,
    rag_model_version
) VALUES (
    'XMA-ADT',
    'usn',
    'mil',
    'https://xma-adt.usn.mil',
    'U.S. Navy XMA-ADT',
    'Naval Air Systems Command',
    'hardcoded',
    NULL,
    NULL
) ON CONFLICT (base_uri) DO NOTHING;

-- Insert default prefixes
INSERT INTO prefix_registry (prefix, description, owner, created_by) VALUES
('dod', 'Department of Defense', 'admin@odras.local', 'admin@odras.local'),
('usn', 'US Navy', 'admin@odras.local', 'admin@odras.local'),
('usaf', 'US Air Force', 'admin@odras.local', 'admin@odras.local'),
('army', 'US Army', 'admin@odras.local', 'admin@odras.local'),
('gov', 'Government', 'admin@odras.local', 'admin@odras.local'),
('nasa', 'NASA', 'admin@odras.local', 'admin@odras.local'),
('boeing', 'Boeing', 'admin@odras.local', 'admin@odras.local'),
('lockheed', 'Lockheed Martin', 'admin@odras.local', 'admin@odras.local')
ON CONFLICT (prefix) DO NOTHING;

-- Insert default domains
INSERT INTO domain_registry (domain, description, owner, created_by) VALUES
('avionics', 'Aircraft electronics and flight systems', 'admin@odras.local', 'admin'),
('mission-planning', 'Mission planning and execution systems', 'admin@odras.local', 'admin'),
('systems-engineering', 'Systems engineering processes and methodologies', 'admin@odras.local', 'admin'),
('logistics', 'Supply chain and logistics management', 'admin@odras.local', 'admin'),
('cybersecurity', 'Cybersecurity and information assurance', 'admin@odras.local', 'admin'),
('communications', 'Communication systems and protocols', 'admin@odras.local', 'admin'),
('radar-systems', 'Radar and sensor technologies', 'admin@odras.local', 'admin'),
('weapons-systems', 'Weapons and armament systems', 'admin@odras.local', 'admin')
ON CONFLICT (domain) DO NOTHING;

-- Insert default namespaces
INSERT INTO namespace_registry (name, type, path, prefix, status, owners, description) VALUES
('odras-core', 'core', 'odras/core', 'odras', 'released', ARRAY['admin@odras.local'], 'ODRAS Core Ontology'),
('odras-admin', 'core', 'odras/admin', 'admin', 'released', ARRAY['admin@odras.local'], 'ODRAS Admin Reference Ontologies')
ON CONFLICT (name, type) DO NOTHING;

-- Create initial versions for existing namespaces
INSERT INTO namespace_versions (namespace_id, version, version_iri, status, released_at)
SELECT
    id,
    '2025-01-01',
    'https://w3id.org/defense/odras/' || type || '/' || name || '/2025-01-01',
    'released',
    NOW()
FROM namespace_registry
WHERE name IN ('odras-core', 'odras-admin')
ON CONFLICT (namespace_id, version) DO NOTHING;

-- =====================================
-- DOCUMENTATION COMMENTS
-- =====================================

-- Table comments
COMMENT ON TABLE public.users IS 'User accounts for authentication and authorization';
COMMENT ON TABLE public.auth_tokens IS 'Persistent storage for authentication tokens to survive server restarts';
COMMENT ON TABLE installation_config IS 'Installation-specific configuration for IRI generation';
COMMENT ON TABLE public.projects IS 'Projects that users can work on';
COMMENT ON TABLE public.project_members IS 'Membership relationships between users and projects';
COMMENT ON TABLE files IS 'Core files table compatible with knowledge management system';
COMMENT ON TABLE knowledge_assets IS 'Core knowledge assets derived from uploaded files';
COMMENT ON TABLE knowledge_chunks IS 'Text chunks with embeddings and metadata for semantic search';
COMMENT ON TABLE knowledge_relationships IS 'Relationships between knowledge assets and chunks for graph queries';
COMMENT ON TABLE knowledge_processing_jobs IS 'Async processing job tracking for knowledge pipeline';

-- Column comments
COMMENT ON COLUMN public.users.is_admin IS 'Whether the user has administrative privileges';
COMMENT ON COLUMN public.users.iri IS 'Globally unique IRI for this user';
COMMENT ON COLUMN public.auth_tokens.token_hash IS 'SHA-256 hash of the actual token for security';
COMMENT ON COLUMN public.auth_tokens.expires_at IS 'Token expiration time (default 24 hours)';
COMMENT ON COLUMN public.auth_tokens.last_used_at IS 'Last time this token was used for authentication';
COMMENT ON COLUMN public.project_members.role IS 'User role in the project (admin, member, viewer)';
COMMENT ON COLUMN public.projects.iri IS 'Globally unique IRI for this project';
COMMENT ON COLUMN files.status IS 'Processing status: new, processing, processed, failed';
COMMENT ON COLUMN files.metadata IS 'File processing metadata and custom attributes';
COMMENT ON COLUMN files.tags IS 'User-defined tags including docType and classification';
COMMENT ON COLUMN files.storage_key IS 'Key/path for cloud storage backends (S3, MinIO, etc)';
COMMENT ON COLUMN files.storage_path IS 'Local filesystem path for local backend';
COMMENT ON COLUMN files.iri IS 'Globally unique IRI for this file resource';
COMMENT ON COLUMN knowledge_assets.source_file_id IS 'Reference to original file in files table';
COMMENT ON COLUMN knowledge_assets.document_type IS 'Type classification: requirements, specification, knowledge, reference';
COMMENT ON COLUMN knowledge_assets.processing_stats IS 'Statistics about processing: chunk_count, token_count, etc.';
COMMENT ON COLUMN knowledge_assets.is_public IS 'True if asset is visible across all projects (admin controlled)';
COMMENT ON COLUMN knowledge_assets.made_public_at IS 'Timestamp when asset was made public';
COMMENT ON COLUMN knowledge_assets.made_public_by IS 'User ID who made the asset public (admin only)';
COMMENT ON COLUMN knowledge_assets.traceability_status IS 'Tracks relationship to source file: linked, orphaned, archived';
COMMENT ON COLUMN knowledge_assets.orphaned_at IS 'Timestamp when asset became orphaned (source file deleted)';
COMMENT ON COLUMN knowledge_assets.orphaned_reason IS 'Reason why asset became orphaned for audit trail';
COMMENT ON COLUMN knowledge_assets.iri IS 'Globally unique IRI for this knowledge asset';
COMMENT ON COLUMN knowledge_chunks.qdrant_point_id IS 'UUID reference to vector point in Qdrant';
COMMENT ON COLUMN knowledge_chunks.token_count IS 'Number of tokens in the chunk content';
COMMENT ON COLUMN knowledge_relationships.neo4j_relationship_id IS 'Reference to relationship ID in Neo4j graph';
COMMENT ON COLUMN knowledge_relationships.confidence_score IS 'AI confidence score for relationship extraction (0.0-1.0)';

-- =====================================
-- RAG SQL-FIRST TABLES
-- =====================================

-- RAG document metadata table
CREATE TABLE IF NOT EXISTS doc (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG document chunks with full text content (source of truth)
CREATE TABLE IF NOT EXISTS doc_chunk (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES doc(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG chat message history
CREATE TABLE IF NOT EXISTS chat_message (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project thread metadata (SQL-first)
CREATE TABLE IF NOT EXISTS project_thread (
    project_thread_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
    goals TEXT,
    current_workbench TEXT
);

-- Individual project events (SQL-first)
CREATE TABLE IF NOT EXISTS project_event (
    event_id TEXT PRIMARY KEY,
    project_thread_id TEXT NOT NULL REFERENCES project_thread(project_thread_id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    context_snapshot JSONB DEFAULT '{}',
    semantic_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Thread conversation messages
CREATE TABLE IF NOT EXISTS thread_conversation (
    conversation_id TEXT PRIMARY KEY,
    project_thread_id TEXT NOT NULL REFERENCES project_thread(project_thread_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG SQL-first indexes for performance
CREATE INDEX IF NOT EXISTS idx_doc_chunk_doc ON doc_chunk(doc_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_doc_chunk_doc_id ON doc_chunk(doc_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_project ON chat_message(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_created ON chat_message(created_at);

CREATE INDEX IF NOT EXISTS idx_project_thread_project ON project_thread(project_id);
CREATE INDEX IF NOT EXISTS idx_project_thread_created_by ON project_thread(created_by);
CREATE INDEX IF NOT EXISTS idx_project_thread_status ON project_thread(status);

CREATE INDEX IF NOT EXISTS idx_project_event_thread ON project_event(project_thread_id);
CREATE INDEX IF NOT EXISTS idx_project_event_project ON project_event(project_id);
CREATE INDEX IF NOT EXISTS idx_project_event_type ON project_event(event_type);
CREATE INDEX IF NOT EXISTS idx_project_event_created ON project_event(created_at);

CREATE INDEX IF NOT EXISTS idx_thread_conversation_thread ON thread_conversation(project_thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_conversation_role ON thread_conversation(role);
CREATE INDEX IF NOT EXISTS idx_thread_conversation_created ON thread_conversation(created_at);

-- Function comments
COMMENT ON FUNCTION resolve_iri IS 'Resolves an IRI to its resource type and metadata';
COMMENT ON TRIGGER trigger_mark_orphaned_asset ON knowledge_assets IS 'Automatically marks assets as orphaned when source file is deleted';

-- RAG table comments
COMMENT ON TABLE doc IS 'RAG document metadata for SQL-first storage';
COMMENT ON TABLE doc_chunk IS 'RAG document chunks with full text content as source of truth';
COMMENT ON TABLE chat_message IS 'RAG chat conversation history';
COMMENT ON TABLE project_thread IS 'SQL-first project thread metadata - no full text content';
COMMENT ON TABLE project_event IS 'Individual project events as source of truth for event content';
COMMENT ON TABLE thread_conversation IS 'Conversation messages separate from project events';
COMMENT ON COLUMN doc_chunk.text IS 'Full text content - source of truth for RAG chunks';
COMMENT ON COLUMN chat_message.role IS 'Message role: user or assistant';
COMMENT ON COLUMN project_event.event_data IS 'Full event data stored in SQL, not vectors';
COMMENT ON COLUMN project_event.semantic_summary IS 'Optional semantic summary for embedding';

-- =====================================
-- REQUIREMENTS WORKBENCH SCHEMA
-- =====================================

-- Enhanced requirements table for comprehensive requirements management
CREATE TABLE IF NOT EXISTS requirements_enhanced (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(project_id) ON DELETE CASCADE,
    
    -- Basic requirement information
    requirement_identifier VARCHAR(100) NOT NULL, -- REQ-001, SYS-REQ-001, etc.
    requirement_title VARCHAR(500) NOT NULL,
    requirement_text TEXT NOT NULL,
    requirement_rationale TEXT,
    
    -- Categorization
    requirement_type VARCHAR(50) NOT NULL CHECK (requirement_type IN ('functional', 'non_functional', 'performance', 'safety', 'security', 'interface', 'operational', 'design', 'implementation')),
    category VARCHAR(100), -- Navigation, Communications, Power, etc.
    subcategory VARCHAR(100), -- GPS, INS, Radio, etc.
    
    -- Priority and status
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    state VARCHAR(20) DEFAULT 'draft' CHECK (state IN ('draft', 'review', 'approved', 'published', 'deprecated', 'cancelled', 'imported')),
    
    -- Import tracking
    is_immutable BOOLEAN DEFAULT false,
    source_requirement_id UUID, -- Original requirement ID from source project
    source_project_id UUID REFERENCES projects(project_id) ON DELETE SET NULL,
    source_project_iri VARCHAR(1000), -- Source project IRI for complete traceability
    source_namespace_path VARCHAR(500), -- Source project namespace path
    source_namespace_prefix VARCHAR(100), -- Source project namespace prefix
    
    -- Traceability
    source_document_id UUID REFERENCES files(id) ON DELETE SET NULL,
    source_section VARCHAR(255), -- Section 3.2.1, Page 45, etc.
    parent_requirement_id UUID REFERENCES requirements_enhanced(requirement_id) ON DELETE SET NULL,
    derived_from_requirement_id UUID REFERENCES requirements_enhanced(requirement_id) ON DELETE SET NULL,
    
    -- Verification
    verification_method VARCHAR(50) CHECK (verification_method IN ('test', 'analysis', 'inspection', 'demonstration', 'review')),
    verification_criteria TEXT,
    verification_status VARCHAR(20) DEFAULT 'not_started' CHECK (verification_status IN ('not_started', 'in_progress', 'passed', 'failed', 'waived')),
    verification_results TEXT,
    verification_date TIMESTAMPTZ,
    
    -- Publishing
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    published_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    
    -- Metadata
    iri VARCHAR(1000) UNIQUE,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    
    -- Extraction metadata
    extraction_confidence DECIMAL(3,2), -- 0.00 to 1.00
    extraction_method VARCHAR(50), -- manual, regex, ai, keyword
    extraction_job_id UUID,
    
    UNIQUE(project_id, requirement_identifier)
);

-- Constraints table for thresholds, objectives, KPCs, KPPs
CREATE TABLE IF NOT EXISTS requirements_constraints (
    constraint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements_enhanced(requirement_id) ON DELETE CASCADE,
    
    -- Constraint identification
    constraint_type VARCHAR(50) NOT NULL CHECK (constraint_type IN ('threshold', 'objective', 'kpc', 'kpp', 'design', 'interface', 'environmental', 'equation')),
    constraint_name VARCHAR(200) NOT NULL,
    constraint_description TEXT NOT NULL,
    
    -- Quantitative values
    value_type VARCHAR(20) CHECK (value_type IN ('numeric', 'range', 'enumeration', 'boolean', 'text', 'equation')),
    numeric_value DECIMAL(20,6),
    numeric_unit VARCHAR(50),
    range_min DECIMAL(20,6),
    range_max DECIMAL(20,6),
    range_unit VARCHAR(50),
    text_value TEXT,
    enumeration_values JSONB, -- Array of allowed values
    equation_expression TEXT, -- Mathematical constraint equations (SysMLv2-lite ready)
    equation_parameters JSONB, -- Parameters and their ontology IRIs for future SysMLv2-lite integration
    
    -- Verification
    measurement_method VARCHAR(100),
    tolerance DECIMAL(10,4),
    tolerance_unit VARCHAR(50),
    
    -- Metadata
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    source_document_id UUID REFERENCES files(id) ON DELETE SET NULL,
    source_section VARCHAR(255),
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual Tables configuration for ontology individual management
CREATE TABLE IF NOT EXISTS individual_tables_config (
    table_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    graph_iri TEXT NOT NULL,
    ontology_label VARCHAR(255) NOT NULL,
    ontology_structure JSONB NOT NULL,
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per project-ontology combination
    UNIQUE(project_id, graph_iri)
);

-- Individual instances stored as structured data with ontology validation
CREATE TABLE IF NOT EXISTS individual_instances (
    instance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES individual_tables_config(table_id) ON DELETE CASCADE,
    class_name VARCHAR(100) NOT NULL,
    instance_name VARCHAR(255) NOT NULL,
    instance_uri TEXT NOT NULL,
    
    -- Properties stored as JSON for flexibility
    properties JSONB NOT NULL DEFAULT '{}',
    
    -- Validation status
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('valid', 'invalid', 'pending', 'warning')),
    validation_errors JSONB DEFAULT '[]',
    
    -- Source information
    source_type VARCHAR(50) DEFAULT 'manual' CHECK (source_type IN ('manual', 'requirements_workbench', 'external_import', 'das_generated')),
    source_reference TEXT,
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per table-class-name combination
    UNIQUE(table_id, class_name, instance_name)
);

-- Data mapping configurations for external data import
CREATE TABLE IF NOT EXISTS data_mapping_configs (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES individual_tables_config(table_id) ON DELETE CASCADE,
    mapping_name VARCHAR(255) NOT NULL,
    source_format VARCHAR(50) NOT NULL, -- 'json', 'csv', 'xml', 'markdown'
    target_class VARCHAR(100) NOT NULL,
    
    -- Mapping configuration as JSON
    field_mappings JSONB NOT NULL,
    transformation_rules JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Import history tracking
CREATE TABLE IF NOT EXISTS individual_import_history (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES individual_tables_config(table_id) ON DELETE CASCADE,
    mapping_id UUID REFERENCES data_mapping_configs(mapping_id) ON DELETE SET NULL,
    
    -- Import details
    import_type VARCHAR(50) NOT NULL, -- 'requirements_workbench', 'external_data', 'das_analysis'
    source_info JSONB NOT NULL,
    records_processed INTEGER DEFAULT 0,
    records_successful INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Results
    import_status VARCHAR(20) DEFAULT 'pending' CHECK (import_status IN ('pending', 'completed', 'failed', 'partial')),
    error_log JSONB DEFAULT '[]',
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for Individual Tables
CREATE INDEX IF NOT EXISTS idx_individual_tables_project ON individual_tables_config(project_id);
CREATE INDEX IF NOT EXISTS idx_individual_tables_graph ON individual_tables_config(graph_iri);
CREATE INDEX IF NOT EXISTS idx_individual_instances_table ON individual_instances(table_id);
CREATE INDEX IF NOT EXISTS idx_individual_instances_class ON individual_instances(class_name);
CREATE INDEX IF NOT EXISTS idx_individual_instances_validation ON individual_instances(validation_status);
CREATE INDEX IF NOT EXISTS idx_data_mapping_table ON data_mapping_configs(table_id);
CREATE INDEX IF NOT EXISTS idx_import_history_table ON individual_import_history(table_id);

-- Multi-user notes for requirements collaboration
CREATE TABLE IF NOT EXISTS requirements_notes (
    note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements_enhanced(requirement_id) ON DELETE CASCADE,
    
    -- Note content
    note_text TEXT NOT NULL,
    note_type VARCHAR(50) DEFAULT 'general' CHECK (note_type IN ('general', 'issue', 'clarification', 'change_request', 'verification', 'review')),
    
    -- Collaboration
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    resolution_text TEXT,
    
    -- Visibility
    visibility VARCHAR(20) DEFAULT 'project' CHECK (visibility IN ('private', 'project', 'public')),
    
    -- References
    references_note_id UUID REFERENCES requirements_notes(note_id) ON DELETE SET NULL, -- For replies
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Requirements change history for tracking all changes
CREATE TABLE IF NOT EXISTS requirements_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements_enhanced(requirement_id) ON DELETE CASCADE,
    
    -- Change details
    change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('created', 'text_updated', 'status_changed', 'verification_updated', 'published', 'deprecated')),
    change_description TEXT,
    
    -- Previous and new values
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    
    -- Change metadata
    change_reason TEXT,
    impact_assessment TEXT,
    
    -- Auditing
    changed_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    version_before INTEGER,
    version_after INTEGER
);

-- Requirements extraction configuration for document parsing
CREATE TABLE IF NOT EXISTS requirements_extraction_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(project_id) ON DELETE CASCADE,
    
    -- Configuration details
    config_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Keyword patterns for extraction
    functional_keywords JSONB DEFAULT '["shall", "must", "will", "should"]',
    performance_keywords JSONB DEFAULT '["performance", "speed", "accuracy", "throughput", "latency"]',
    constraint_keywords JSONB DEFAULT '["threshold", "objective", "minimum", "maximum", "limit", "range"]',
    
    -- Regex patterns
    requirement_patterns JSONB DEFAULT '["\\b[A-Z]+-[0-9]+\\b", "\\bREQ-[0-9]+\\b", "\\b[0-9]+\\.[0-9]+\\.[0-9]+\\b"]',
    constraint_patterns JSONB DEFAULT '["\\b(minimum|maximum|at least|no more than|between)\\s+[0-9]+", "\\b[0-9]+(\\.[0-9]+)?\\s*(m|ft|kg|lb|sec|min|hr)\\b"]',
    
    -- Processing options
    ignore_case BOOLEAN DEFAULT TRUE,
    min_confidence DECIMAL(3,2) DEFAULT 0.7,
    extract_context BOOLEAN DEFAULT TRUE,
    context_window_size INTEGER DEFAULT 100,
    
    -- Document type specific settings
    document_types JSONB DEFAULT '["requirements", "specification", "sow", "cdd"]',
    section_filters JSONB DEFAULT '[]', -- Only extract from specific sections
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(project_id, config_name)
);

-- Requirements extraction jobs for tracking document processing
CREATE TABLE IF NOT EXISTS requirements_extraction_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(project_id) ON DELETE CASCADE,
    config_id UUID REFERENCES requirements_extraction_config(config_id) ON DELETE SET NULL,
    
    -- Job details
    job_name VARCHAR(200),
    source_document_id UUID REFERENCES files(id) ON DELETE CASCADE,
    extraction_type VARCHAR(50) DEFAULT 'document' CHECK (extraction_type IN ('document', 'batch', 'manual')),
    
    -- Processing status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress_percent INTEGER DEFAULT 0,
    
    -- Results
    requirements_found INTEGER DEFAULT 0,
    constraints_found INTEGER DEFAULT 0,
    requirements_created INTEGER DEFAULT 0,
    constraints_created INTEGER DEFAULT 0,
    
    -- Processing details
    processing_log TEXT,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_duration_seconds INTEGER,
    
    -- Auditing
    created_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- DAS review sessions for tracking AI-assisted requirement reviews
CREATE TABLE IF NOT EXISTS requirements_das_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements_enhanced(requirement_id) ON DELETE CASCADE,
    
    -- Review details
    review_type VARCHAR(50) DEFAULT 'improvement' CHECK (review_type IN ('improvement', 'validation', 'gap_analysis', 'consistency')),
    original_text TEXT NOT NULL,
    suggested_text TEXT,
    
    -- DAS analysis
    das_confidence DECIMAL(3,2), -- 0.00 to 1.00
    improvement_areas JSONB DEFAULT '[]', -- Array of improvement categories
    issues_found JSONB DEFAULT '[]', -- Array of specific issues
    suggestions JSONB DEFAULT '[]', -- Array of specific suggestions
    
    -- User feedback
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    accepted BOOLEAN,
    applied_suggestions JSONB DEFAULT '[]', -- Which suggestions were applied
    
    -- Review metadata
    das_model_version VARCHAR(50),
    review_context JSONB DEFAULT '{}', -- Context provided to DAS
    
    -- Auditing
    reviewed_by UUID REFERENCES public.users(user_id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- REQUIREMENTS WORKBENCH INDEXES
-- =====================================

-- Requirements enhanced indexes
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_project ON requirements_enhanced(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_identifier ON requirements_enhanced(project_id, requirement_identifier);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_type ON requirements_enhanced(requirement_type);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_state ON requirements_enhanced(state);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_priority ON requirements_enhanced(priority);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_published ON requirements_enhanced(is_published);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_source ON requirements_enhanced(source_document_id);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_parent ON requirements_enhanced(parent_requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_verification ON requirements_enhanced(verification_status);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_created_by ON requirements_enhanced(created_by);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_tags ON requirements_enhanced USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_metadata ON requirements_enhanced USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_requirements_enhanced_iri ON requirements_enhanced(iri);

-- Constraints indexes
CREATE INDEX IF NOT EXISTS idx_constraints_requirement ON requirements_constraints(requirement_id);
CREATE INDEX IF NOT EXISTS idx_constraints_type ON requirements_constraints(constraint_type);
CREATE INDEX IF NOT EXISTS idx_constraints_source ON requirements_constraints(source_document_id);
CREATE INDEX IF NOT EXISTS idx_constraints_priority ON requirements_constraints(priority);

-- Notes indexes
CREATE INDEX IF NOT EXISTS idx_notes_requirement ON requirements_notes(requirement_id);
CREATE INDEX IF NOT EXISTS idx_notes_type ON requirements_notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_resolved ON requirements_notes(is_resolved);
CREATE INDEX IF NOT EXISTS idx_notes_created_by ON requirements_notes(created_by);
CREATE INDEX IF NOT EXISTS idx_notes_references ON requirements_notes(references_note_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON requirements_notes(created_at);

-- History indexes
CREATE INDEX IF NOT EXISTS idx_history_requirement ON requirements_history(requirement_id);
CREATE INDEX IF NOT EXISTS idx_history_change_type ON requirements_history(change_type);
CREATE INDEX IF NOT EXISTS idx_history_changed_by ON requirements_history(changed_by);
CREATE INDEX IF NOT EXISTS idx_history_changed_at ON requirements_history(changed_at);

-- Extraction config indexes
CREATE INDEX IF NOT EXISTS idx_extraction_config_project ON requirements_extraction_config(project_id);
CREATE INDEX IF NOT EXISTS idx_extraction_config_active ON requirements_extraction_config(is_active);
CREATE INDEX IF NOT EXISTS idx_extraction_config_default ON requirements_extraction_config(is_default);

-- Extraction jobs indexes
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_project ON requirements_extraction_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON requirements_extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_document ON requirements_extraction_jobs(source_document_id);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_created ON requirements_extraction_jobs(created_at);

-- DAS reviews indexes
CREATE INDEX IF NOT EXISTS idx_das_reviews_requirement ON requirements_das_reviews(requirement_id);
CREATE INDEX IF NOT EXISTS idx_das_reviews_type ON requirements_das_reviews(review_type);
CREATE INDEX IF NOT EXISTS idx_das_reviews_accepted ON requirements_das_reviews(accepted);
CREATE INDEX IF NOT EXISTS idx_das_reviews_reviewed_by ON requirements_das_reviews(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_das_reviews_reviewed_at ON requirements_das_reviews(reviewed_at);

-- =====================================
-- REQUIREMENTS WORKBENCH FUNCTIONS
-- =====================================

-- Function to update requirement version and history
CREATE OR REPLACE FUNCTION update_requirement_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment version
    NEW.version = OLD.version + 1;
    NEW.updated_at = NOW();
    
    -- Create history entry for the change
    INSERT INTO requirements_history (
        requirement_id,
        change_type,
        change_description,
        field_name,
        old_value,
        new_value,
        changed_by,
        version_before,
        version_after
    ) VALUES (
        NEW.requirement_id,
        'text_updated',
        'Requirement text updated',
        'requirement_text',
        OLD.requirement_text,
        NEW.requirement_text,
        NEW.updated_by,
        OLD.version,
        NEW.version
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to create extraction statistics
CREATE OR REPLACE FUNCTION update_extraction_job_stats(job_id_param UUID)
RETURNS void AS $$
BEGIN
    UPDATE requirements_extraction_jobs 
    SET 
        requirements_created = (
            SELECT COUNT(*) FROM requirements_enhanced 
            WHERE extraction_job_id = job_id_param
        ),
        constraints_created = (
            SELECT COUNT(*) FROM requirements_constraints rc
            JOIN requirements_enhanced re ON rc.requirement_id = re.requirement_id
            WHERE re.extraction_job_id = job_id_param
        ),
        updated_at = NOW()
    WHERE job_id = job_id_param;
END;
$$ LANGUAGE plpgsql;

-- Function to auto-assign requirement identifiers
CREATE OR REPLACE FUNCTION auto_assign_requirement_identifier()
RETURNS TRIGGER AS $$
DECLARE
    next_number INTEGER;
    new_identifier VARCHAR(100);
BEGIN
    -- Only auto-assign if identifier is not provided
    IF NEW.requirement_identifier IS NULL OR NEW.requirement_identifier = '' THEN
        -- Get the next sequential number for this project
        SELECT COALESCE(MAX(
            CAST(REGEXP_REPLACE(requirement_identifier, '^REQ-', '') AS INTEGER)
        ), 0) + 1
        INTO next_number
        FROM requirements_enhanced
        WHERE project_id = NEW.project_id 
        AND requirement_identifier ~ '^REQ-[0-9]+$';
        
        -- Format as REQ-001, REQ-002, etc.
        new_identifier = 'REQ-' || LPAD(next_number::TEXT, 3, '0');
        
        -- Ensure uniqueness (in case of race conditions)
        WHILE EXISTS (
            SELECT 1 FROM requirements_enhanced 
            WHERE project_id = NEW.project_id 
            AND requirement_identifier = new_identifier
        ) LOOP
            next_number = next_number + 1;
            new_identifier = 'REQ-' || LPAD(next_number::TEXT, 3, '0');
        END LOOP;
        
        NEW.requirement_identifier = new_identifier;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================
-- REQUIREMENTS WORKBENCH TRIGGERS
-- =====================================

-- Trigger to update requirement version when text changes
CREATE TRIGGER trigger_requirement_version_update
    BEFORE UPDATE ON requirements_enhanced
    FOR EACH ROW
    WHEN (OLD.requirement_text IS DISTINCT FROM NEW.requirement_text)
    EXECUTE FUNCTION update_requirement_version();

-- Trigger to update timestamps
CREATE TRIGGER trigger_requirements_enhanced_updated_at
    BEFORE UPDATE ON requirements_enhanced
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_requirements_constraints_updated_at
    BEFORE UPDATE ON requirements_constraints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_requirements_notes_updated_at
    BEFORE UPDATE ON requirements_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_requirements_extraction_config_updated_at
    BEFORE UPDATE ON requirements_extraction_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_requirements_das_reviews_updated_at
    BEFORE UPDATE ON requirements_das_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to auto-assign requirement identifiers
CREATE TRIGGER trigger_auto_assign_requirement_identifier
    BEFORE INSERT ON requirements_enhanced
    FOR EACH ROW
    EXECUTE FUNCTION auto_assign_requirement_identifier();

-- =====================================
-- REQUIREMENTS WORKBENCH COMMENTS
-- =====================================

-- Table comments
COMMENT ON TABLE requirements_enhanced IS 'Comprehensive requirements management with full workbench capabilities';
COMMENT ON TABLE requirements_constraints IS 'Constraints, thresholds, objectives, KPCs, and KPPs associated with requirements';
COMMENT ON TABLE requirements_notes IS 'Multi-user collaborative notes and comments on requirements';
COMMENT ON TABLE requirements_history IS 'Complete change history and audit trail for all requirements';
COMMENT ON TABLE requirements_extraction_config IS 'Configuration for automated requirements extraction from documents';
COMMENT ON TABLE requirements_extraction_jobs IS 'Tracking of document processing and requirements extraction jobs';
COMMENT ON TABLE requirements_das_reviews IS 'DAS AI-assisted requirement review sessions and improvements';

-- Column comments for requirements_enhanced
COMMENT ON COLUMN requirements_enhanced.requirement_identifier IS 'Unique identifier within project (REQ-001, SYS-REQ-001, etc.)';
COMMENT ON COLUMN requirements_enhanced.requirement_rationale IS 'Explanation of why this requirement exists';
COMMENT ON COLUMN requirements_enhanced.verification_method IS 'How the requirement will be verified (test, analysis, inspection, demonstration, review)';
COMMENT ON COLUMN requirements_enhanced.is_published IS 'Whether requirement is available for use in other projects';
COMMENT ON COLUMN requirements_enhanced.extraction_confidence IS 'AI confidence score for automatically extracted requirements';
COMMENT ON COLUMN requirements_enhanced.extraction_job_id IS 'Reference to extraction job that created this requirement';

-- Column comments for constraints
COMMENT ON COLUMN requirements_constraints.constraint_type IS 'Type of constraint: threshold, objective, KPC, KPP, design, interface, environmental';
COMMENT ON COLUMN requirements_constraints.value_type IS 'Data type of constraint value: numeric, range, enumeration, boolean, text';
COMMENT ON COLUMN requirements_constraints.enumeration_values IS 'JSON array of allowed values for enumeration type constraints';

-- Column comments for notes
COMMENT ON COLUMN requirements_notes.visibility IS 'Note visibility: private (creator only), project (project members), public (all users)';
COMMENT ON COLUMN requirements_notes.references_note_id IS 'Reference to parent note for threaded discussions';

-- Column comments for DAS reviews
COMMENT ON COLUMN requirements_das_reviews.improvement_areas IS 'JSON array of improvement categories identified by DAS';
COMMENT ON COLUMN requirements_das_reviews.issues_found IS 'JSON array of specific issues found by DAS analysis';
COMMENT ON COLUMN requirements_das_reviews.applied_suggestions IS 'JSON array of DAS suggestions that were applied by user';

-- =====================================
-- REQUIREMENTS WORKBENCH MIGRATIONS
-- =====================================

-- Migration: Add equation constraint support for SysMLv2-lite integration
-- These fields support mathematical constraint expressions and ontology-based parameters
DO $$
BEGIN
    -- Add equation_expression column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'requirements_constraints' 
        AND column_name = 'equation_expression'
    ) THEN
        ALTER TABLE requirements_constraints 
        ADD COLUMN equation_expression TEXT;
        
        COMMENT ON COLUMN requirements_constraints.equation_expression IS 'Mathematical constraint equations (SysMLv2-lite ready)';
    END IF;

    -- Add equation_parameters column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'requirements_constraints' 
        AND column_name = 'equation_parameters'
    ) THEN
        ALTER TABLE requirements_constraints 
        ADD COLUMN equation_parameters JSONB;
        
        COMMENT ON COLUMN requirements_constraints.equation_parameters IS 'Parameters and their ontology IRIs for SysMLv2-lite integration';
    END IF;

    -- Update constraint_type check constraint to include 'equation' type
    ALTER TABLE requirements_constraints DROP CONSTRAINT IF EXISTS requirements_constraints_constraint_type_check;
    ALTER TABLE requirements_constraints 
    ADD CONSTRAINT requirements_constraints_constraint_type_check 
    CHECK (constraint_type IN ('threshold', 'objective', 'kpc', 'kpp', 'design', 'interface', 'environmental', 'equation'));

    -- Update value_type check constraint to include 'equation' type
    ALTER TABLE requirements_constraints DROP CONSTRAINT IF EXISTS requirements_constraints_value_type_check;
    ALTER TABLE requirements_constraints 
    ADD CONSTRAINT requirements_constraints_value_type_check 
    CHECK (value_type IN ('numeric', 'range', 'enumeration', 'boolean', 'text', 'equation'));

    RAISE NOTICE 'Requirements constraint equation support migration completed';
END
$$;

-- =====================================
-- REQUIREMENTS IMPORT TRACEABILITY MIGRATION
-- =====================================
-- Add import traceability columns for cross-project requirements import
-- This migration will be applied automatically if columns are missing

DO $$ 
BEGIN
    -- Add source_project_iri if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'requirements_enhanced' AND column_name = 'source_project_iri') THEN
        ALTER TABLE requirements_enhanced ADD COLUMN source_project_iri VARCHAR(1000);
        RAISE NOTICE 'Added source_project_iri column to requirements_enhanced';
    END IF;
    
    -- Add source_namespace_path if it doesn't exist  
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'requirements_enhanced' AND column_name = 'source_namespace_path') THEN
        ALTER TABLE requirements_enhanced ADD COLUMN source_namespace_path VARCHAR(500);
        RAISE NOTICE 'Added source_namespace_path column to requirements_enhanced';
    END IF;
    
    -- Add source_namespace_prefix if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'requirements_enhanced' AND column_name = 'source_namespace_prefix') THEN
        ALTER TABLE requirements_enhanced ADD COLUMN source_namespace_prefix VARCHAR(100);
        RAISE NOTICE 'Added source_namespace_prefix column to requirements_enhanced';
    END IF;
    
    -- Ensure 'imported' state is in CHECK constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c 
        JOIN pg_class t ON c.conrelid = t.oid 
        WHERE t.relname = 'requirements_enhanced' 
        AND c.conname = 'requirements_enhanced_state_check'
        AND pg_get_constraintdef(c.oid) LIKE '%imported%'
    ) THEN
        ALTER TABLE requirements_enhanced DROP CONSTRAINT IF EXISTS requirements_enhanced_state_check;
        ALTER TABLE requirements_enhanced ADD CONSTRAINT requirements_enhanced_state_check 
            CHECK (state IN ('draft', 'review', 'approved', 'published', 'deprecated', 'cancelled', 'imported'));
        RAISE NOTICE 'Updated state CHECK constraint to include imported';
    END IF;
    
    RAISE NOTICE 'Requirements import traceability migration completed';
END
$$;
