-- Knowledge Management Public Assets
-- Migration 002: Add public asset functionality and admin controls

-- Add is_public column to knowledge_assets table
ALTER TABLE knowledge_assets 
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

-- Add made_public_at and made_public_by for audit trail
ALTER TABLE knowledge_assets 
ADD COLUMN IF NOT EXISTS made_public_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS made_public_by VARCHAR(255);

-- Create index for public assets query performance
CREATE INDEX IF NOT EXISTS idx_knowledge_public ON knowledge_assets(is_public);
CREATE INDEX IF NOT EXISTS idx_knowledge_public_project ON knowledge_assets(is_public, project_id);

-- Comments for documentation
COMMENT ON COLUMN knowledge_assets.is_public IS 'True if asset is visible across all projects (admin controlled)';
COMMENT ON COLUMN knowledge_assets.made_public_at IS 'Timestamp when asset was made public';
COMMENT ON COLUMN knowledge_assets.made_public_by IS 'User ID who made the asset public (admin only)';


