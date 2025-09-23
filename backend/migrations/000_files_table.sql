-- File Management Database Schema
-- Migration 000: Core files table for knowledge management compatibility

-- Create the files table that knowledge management system expects
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_files_hash_md5 ON files(hash_md5);
CREATE INDEX IF NOT EXISTS idx_files_hash_sha256 ON files(hash_sha256);
CREATE INDEX IF NOT EXISTS idx_files_metadata ON files USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_files_tags ON files USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_files_storage_backend ON files(storage_backend);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);

-- File content table (for database storage backend)
CREATE TABLE IF NOT EXISTS file_content (
  file_id UUID PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
  content BYTEA NOT NULL,
  compressed BOOLEAN DEFAULT FALSE,
  encryption_key_id VARCHAR(255)
);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON files
    FOR EACH ROW EXECUTE FUNCTION update_files_updated_at();

-- Comments for documentation
COMMENT ON TABLE files IS 'Core files table compatible with knowledge management system';
COMMENT ON COLUMN files.status IS 'Processing status: new, processing, processed, failed';
COMMENT ON COLUMN files.metadata IS 'File processing metadata and custom attributes';
COMMENT ON COLUMN files.tags IS 'User-defined tags including docType and classification';
COMMENT ON COLUMN files.storage_key IS 'Key/path for cloud storage backends (S3, MinIO, etc)';
COMMENT ON COLUMN files.storage_path IS 'Local filesystem path for local backend';

