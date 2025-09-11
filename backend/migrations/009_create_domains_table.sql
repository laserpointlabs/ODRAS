-- Domain Management Schema for ODRAS
-- Controls organizational domains used for project classification

-- Domain registry table
CREATE TABLE IF NOT EXISTS domain_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    owner VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'archived')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);

-- Add constraint to ensure domain follows naming rules
-- Lowercase letters, numbers, and hyphens only, start with letter, 2-50 characters
ALTER TABLE domain_registry ADD CONSTRAINT domain_format_check 
CHECK (domain ~ '^[a-z][a-z0-9-]{1,49}$');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_domain_registry_domain ON domain_registry(domain);
CREATE INDEX IF NOT EXISTS idx_domain_registry_status ON domain_registry(status);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_domain_registry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_domain_registry_updated_at
    BEFORE UPDATE ON domain_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_domain_registry_updated_at();

-- Insert some default domains
INSERT INTO domain_registry (domain, description, owner, created_by) VALUES
('avionics', 'Aircraft electronics and flight systems', 'admin@odras.local', 'admin'),
('mission-planning', 'Mission planning and execution systems', 'admin@odras.local', 'admin'),
('systems-engineering', 'Systems engineering processes and methodologies', 'admin@odras.local', 'admin'),
('logistics', 'Supply chain and logistics management', 'admin@odras.local', 'admin'),
('cybersecurity', 'Cybersecurity and information assurance', 'admin@odras.local', 'admin'),
('communications', 'Communication systems and protocols', 'admin@odras.local', 'admin'),
('radar-systems', 'Radar and sensor technologies', 'admin@odras.local', 'admin'),
('weapons-systems', 'Weapons and armament systems', 'admin@odras.local', 'admin');

