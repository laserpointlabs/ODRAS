-- Namespace Management Schema for ODRAS
-- Phase 1: Core namespace management with Fuseki as source of truth

-- Namespace registry table
CREATE TABLE namespace_registry (
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
CREATE TABLE namespace_versions (
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
CREATE TABLE namespace_classes (
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
CREATE TABLE namespace_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_namespace_id UUID REFERENCES namespace_registry(id) ON DELETE CASCADE,
    target_version_id UUID REFERENCES namespace_versions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_namespace_id, target_namespace_id)
);

-- Indexes for performance
CREATE INDEX idx_namespace_registry_type ON namespace_registry(type);
CREATE INDEX idx_namespace_registry_status ON namespace_registry(status);
CREATE INDEX idx_namespace_versions_namespace_id ON namespace_versions(namespace_id);
CREATE INDEX idx_namespace_versions_status ON namespace_versions(status);
CREATE INDEX idx_namespace_classes_version_id ON namespace_classes(version_id);
CREATE INDEX idx_namespace_imports_source ON namespace_imports(source_namespace_id);
CREATE INDEX idx_namespace_imports_target ON namespace_imports(target_namespace_id);

-- Insert default namespaces for existing ODRAS functionality
INSERT INTO namespace_registry (name, type, path, prefix, status, owners, description) VALUES
('odras-core', 'core', 'odras/core', 'odras', 'released', ARRAY['admin@odras.local'], 'ODRAS Core Ontology'),
('odras-admin', 'core', 'odras/admin', 'admin', 'released', ARRAY['admin@odras.local'], 'ODRAS Admin Reference Ontologies');

-- Create initial versions for existing namespaces
INSERT INTO namespace_versions (namespace_id, version, version_iri, status, released_at)
SELECT
    id,
    '2025-01-01',
    'https://w3id.org/defense/odras/' || type || '/' || name || '/2025-01-01',
    'released',
    NOW()
FROM namespace_registry
WHERE name IN ('odras-core', 'odras-admin');

-- Now that namespace_registry exists, add the foreign key constraint to projects table
-- This was deferred from migration 008 to avoid dependency issues
ALTER TABLE public.projects
ADD CONSTRAINT fk_projects_namespace_id
FOREIGN KEY (namespace_id) REFERENCES namespace_registry(id) ON DELETE CASCADE;


