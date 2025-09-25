-- Namespace Management Schema for ODRAS
-- Phase 1: Core namespace management with Fuseki as source of truth

-- Namespace registry table
CREATE TABLE IF NOT EXISTS namespace_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('core', 'domain', 'program', 'project', 'industry', 'vocab', 'shapes', 'align')),
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

-- Version management table
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

-- Class definitions (versioned)
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

-- Import dependencies (for validation)
CREATE TABLE IF NOT EXISTS namespace_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_version_id UUID REFERENCES namespace_versions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_namespace_id, target_namespace_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_namespace_registry_type ON namespace_registry(type);
CREATE INDEX IF NOT EXISTS idx_namespace_registry_status ON namespace_registry(status);
CREATE INDEX IF NOT EXISTS idx_namespace_versions_namespace_id ON namespace_versions(namespace_id);
CREATE INDEX IF NOT EXISTS idx_namespace_versions_status ON namespace_versions(status);
CREATE INDEX IF NOT EXISTS idx_namespace_classes_version_id ON namespace_classes(version_id);
CREATE INDEX IF NOT EXISTS idx_namespace_imports_source ON namespace_imports(source_namespace_id);
CREATE INDEX IF NOT EXISTS idx_namespace_imports_target ON namespace_imports(target_namespace_id);

-- Insert default namespaces for existing ODRAS functionality (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM namespace_registry WHERE name = 'odras-core' AND type = 'core') THEN
        INSERT INTO namespace_registry (name, type, path, prefix, status, owners, description) VALUES
        ('odras-core', 'core', 'odras/core', 'odras', 'released', ARRAY['admin@odras.local'], 'ODRAS Core Ontology'),
        ('odras-admin', 'core', 'odras/admin', 'admin', 'released', ARRAY['admin@odras.local'], 'ODRAS Admin Reference Ontologies');
    END IF;
END $$;

-- Create initial versions for existing namespaces (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM namespace_versions nv
        JOIN namespace_registry nr ON nv.namespace_id = nr.id
        WHERE nr.name = 'odras-core' AND nv.version = '2025-01-01'
    ) THEN
        INSERT INTO namespace_versions (namespace_id, version, version_iri, status, released_at)
        SELECT
            id,
            '2025-01-01',
            'https://w3id.org/defense/odras/' || type || '/' || name || '/2025-01-01',
            'released',
            NOW()
        FROM namespace_registry
        WHERE name IN ('odras-core', 'odras-admin');
    END IF;
END $$;

-- Now that namespace_registry exists, add the foreign key constraint to projects table
-- This was deferred from migration 008 to avoid dependency issues
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_projects_namespace_id'
        AND table_name = 'projects'
    ) THEN
        ALTER TABLE public.projects
        ADD CONSTRAINT fk_projects_namespace_id
        FOREIGN KEY (namespace_id) REFERENCES namespace_registry(id) ON DELETE CASCADE;
    END IF;
END $$;
