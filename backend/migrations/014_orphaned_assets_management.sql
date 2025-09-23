-- Migration 014: Orphaned Assets Management
-- Implements hybrid approach for file deletion and knowledge asset preservation

-- Add traceability status column to knowledge assets
ALTER TABLE knowledge_assets
ADD COLUMN IF NOT EXISTS traceability_status VARCHAR(50) DEFAULT 'linked'
CHECK (traceability_status IN ('linked', 'orphaned', 'archived'));

-- Add orphaned timestamp for tracking
ALTER TABLE knowledge_assets
ADD COLUMN IF NOT EXISTS orphaned_at TIMESTAMPTZ;

-- Add orphaned reason for audit trail
ALTER TABLE knowledge_assets
ADD COLUMN IF NOT EXISTS orphaned_reason VARCHAR(255);

-- Update existing assets to have 'linked' status
UPDATE knowledge_assets
SET traceability_status = 'linked'
WHERE traceability_status IS NULL;

-- Create index for efficient orphaned asset queries
CREATE INDEX IF NOT EXISTS idx_knowledge_traceability_status ON knowledge_assets(traceability_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_orphaned_at ON knowledge_assets(orphaned_at);

-- Modify the foreign key constraint to SET NULL instead of CASCADE
-- First, drop the existing constraint
ALTER TABLE knowledge_assets
DROP CONSTRAINT IF EXISTS knowledge_assets_source_file_id_fkey;

-- Add new constraint with SET NULL behavior
ALTER TABLE knowledge_assets
ADD CONSTRAINT knowledge_assets_source_file_id_fkey
FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE SET NULL;

-- Create trigger to mark assets as orphaned when source file is deleted
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

-- Apply trigger to knowledge_assets table
DROP TRIGGER IF EXISTS trigger_mark_orphaned_asset ON knowledge_assets;
CREATE TRIGGER trigger_mark_orphaned_asset
    BEFORE UPDATE ON knowledge_assets
    FOR EACH ROW
    WHEN (OLD.source_file_id IS DISTINCT FROM NEW.source_file_id)
    EXECUTE FUNCTION mark_orphaned_asset();

-- Comments for documentation
COMMENT ON COLUMN knowledge_assets.traceability_status IS 'Tracks relationship to source file: linked, orphaned, archived';
COMMENT ON COLUMN knowledge_assets.orphaned_at IS 'Timestamp when asset became orphaned (source file deleted)';
COMMENT ON COLUMN knowledge_assets.orphaned_reason IS 'Reason why asset became orphaned for audit trail';
COMMENT ON TRIGGER trigger_mark_orphaned_asset ON knowledge_assets IS 'Automatically marks assets as orphaned when source file is deleted';