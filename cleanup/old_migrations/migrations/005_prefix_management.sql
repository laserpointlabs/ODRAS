-- Prefix Management Schema for ODRAS
-- Controls organizational prefixes used in namespace creation

-- Prefix registry table
CREATE TABLE prefix_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prefix VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    owner VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'archived')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);

-- Add constraint to ensure prefix follows naming rules
-- Lowercase letters and numbers only, start with letter, 2-20 characters
ALTER TABLE prefix_registry ADD CONSTRAINT prefix_format_check
CHECK (prefix ~ '^[a-z][a-z0-9]{1,19}$');

-- Create index for faster lookups
CREATE INDEX idx_prefix_registry_prefix ON prefix_registry(prefix);
CREATE INDEX idx_prefix_registry_status ON prefix_registry(status);

-- Insert some default prefixes
INSERT INTO prefix_registry (prefix, description, owner, created_by) VALUES
('dod', 'Department of Defense', 'admin@odras.local', 'admin@odras.local'),
('usn', 'US Navy', 'admin@odras.local', 'admin@odras.local'),
('usaf', 'US Air Force', 'admin@odras.local', 'admin@odras.local'),
('army', 'US Army', 'admin@odras.local', 'admin@odras.local'),
('gov', 'Government', 'admin@odras.local', 'admin@odras.local'),
('nasa', 'NASA', 'admin@odras.local', 'admin@odras.local'),
('boeing', 'Boeing', 'admin@odras.local', 'admin@odras.local'),
('lockheed', 'Lockheed Martin', 'admin@odras.local', 'admin@odras.local');


