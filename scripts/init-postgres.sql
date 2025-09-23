-- ODRAS PostgreSQL Database Initialization Script
-- This script sets up the initial database schema for ODRAS

-- Create database schema for file storage
CREATE SCHEMA IF NOT EXISTS file_storage;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create file_storage tables (already handled by the Python service)
-- These are here for reference and manual setup if needed

-- File metadata table
CREATE TABLE IF NOT EXISTS file_storage.file_metadata (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    content_type VARCHAR(200),
    size BIGINT NOT NULL,
    hash_md5 VARCHAR(32),
    hash_sha256 VARCHAR(64),
    storage_path VARCHAR(500),
    storage_backend VARCHAR(50) DEFAULT 'postgresql',
    project_id UUID,
    tags JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- File content table (for PostgreSQL storage backend)
CREATE TABLE IF NOT EXISTS file_storage.file_content (
    file_id UUID PRIMARY KEY REFERENCES file_storage.file_metadata(file_id) ON DELETE CASCADE,
    content BYTEA NOT NULL,
    compressed BOOLEAN DEFAULT FALSE,
    encryption_key_id VARCHAR(255)
);

-- Projects table
CREATE TABLE IF NOT EXISTS public.projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- Users table (simple user directory)
CREATE TABLE IF NOT EXISTS public.users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project membership table (user to project with role)
CREATE TABLE IF NOT EXISTS public.project_members (
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(user_id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'owner', -- owner | editor | viewer
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

-- Ontologies registry per project
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

-- Requirements extraction jobs table
CREATE TABLE IF NOT EXISTS public.extraction_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(project_id),
    file_id UUID REFERENCES file_storage.file_metadata(file_id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    camunda_process_id VARCHAR(255),
    extraction_params JSONB DEFAULT '{}',
    results JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Extracted requirements table
CREATE TABLE IF NOT EXISTS public.requirements (
    requirement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    extraction_job_id UUID REFERENCES public.extraction_jobs(job_id),
    project_id UUID REFERENCES public.projects(project_id),
    file_id UUID REFERENCES file_storage.file_metadata(file_id),
    text TEXT NOT NULL,
    category VARCHAR(100),
    priority VARCHAR(50),
    state VARCHAR(50) DEFAULT 'Draft', -- Draft, Reviewed, Approved
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    extraction_method VARCHAR(100),
    source_location JSONB, -- page, section, line numbers etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ontology change log table
CREATE TABLE IF NOT EXISTS public.ontology_changes (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    change_type VARCHAR(100) NOT NULL, -- full_update, add_class, add_property, delete_entity
    backup_id UUID,
    change_description TEXT,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_file_metadata_project_id ON file_storage.file_metadata(project_id);
CREATE INDEX IF NOT EXISTS idx_file_metadata_created_at ON file_storage.file_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_file_metadata_hash_md5 ON file_storage.file_metadata(hash_md5);
CREATE INDEX IF NOT EXISTS idx_file_metadata_hash_sha256 ON file_storage.file_metadata(hash_sha256);
CREATE INDEX IF NOT EXISTS idx_file_metadata_storage_backend ON file_storage.file_metadata(storage_backend);
CREATE INDEX IF NOT EXISTS idx_file_metadata_tags ON file_storage.file_metadata USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_project_id ON public.extraction_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON public.extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_camunda_process_id ON public.extraction_jobs(camunda_process_id);

CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON public.requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_extraction_job_id ON public.requirements(extraction_job_id);
CREATE INDEX IF NOT EXISTS idx_requirements_state ON public.requirements(state);
CREATE INDEX IF NOT EXISTS idx_requirements_category ON public.requirements(category);
CREATE INDEX IF NOT EXISTS idx_requirements_confidence_score ON public.requirements(confidence_score);

CREATE INDEX IF NOT EXISTS idx_ontology_changes_user_id ON public.ontology_changes(user_id);
CREATE INDEX IF NOT EXISTS idx_ontology_changes_change_type ON public.ontology_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_ontology_changes_created_at ON public.ontology_changes(created_at);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at columns
CREATE TRIGGER update_file_metadata_updated_at BEFORE UPDATE ON file_storage.file_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ontologies_registry_updated_at BEFORE UPDATE ON public.ontologies_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extraction_jobs_updated_at BEFORE UPDATE ON public.extraction_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON public.requirements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Note: Default project is created by odras.sh script during init-db
-- This ensures proper user associations and project memberships

-- Grant permissions (adjust as needed for your security requirements)
-- GRANT ALL PRIVILEGES ON SCHEMA file_storage TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA file_storage TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;

COMMIT;

