-- Knowledge Management Database Schema
-- Migration 001: Core knowledge management tables

-- Knowledge Assets Table
CREATE TABLE IF NOT EXISTS knowledge_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_file_id UUID REFERENCES files(id) ON DELETE CASCADE,
  project_id UUID NOT NULL,
  title VARCHAR(512) NOT NULL,
  document_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
  content_summary TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version VARCHAR(20) DEFAULT '1.0.0',
  status VARCHAR(20) DEFAULT 'active', -- active, archived, processing, failed
  processing_stats JSONB DEFAULT '{}'::jsonb
);

-- Indexes for knowledge_assets
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_assets(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_assets(document_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge_assets(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_file ON knowledge_assets(source_file_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_metadata ON knowledge_assets USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge_assets(created_at);

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

-- Indexes for knowledge_chunks
CREATE INDEX IF NOT EXISTS idx_chunks_asset ON knowledge_chunks(asset_id);
CREATE INDEX IF NOT EXISTS idx_chunks_sequence ON knowledge_chunks(asset_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON knowledge_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_qdrant ON knowledge_chunks(qdrant_point_id);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON knowledge_chunks USING GIN(metadata);

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

-- Indexes for knowledge_relationships
CREATE INDEX IF NOT EXISTS idx_relationships_source ON knowledge_relationships(source_asset_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON knowledge_relationships(target_asset_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON knowledge_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_neo4j ON knowledge_relationships(neo4j_relationship_id);

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

-- Indexes for processing jobs
CREATE INDEX IF NOT EXISTS idx_processing_jobs_asset ON knowledge_processing_jobs(asset_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON knowledge_processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_type ON knowledge_processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created ON knowledge_processing_jobs(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for auto-updating updated_at on knowledge_assets
CREATE TRIGGER update_knowledge_assets_updated_at 
    BEFORE UPDATE ON knowledge_assets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE knowledge_assets IS 'Core knowledge assets derived from uploaded files';
COMMENT ON TABLE knowledge_chunks IS 'Text chunks with embeddings and metadata for semantic search';
COMMENT ON TABLE knowledge_relationships IS 'Relationships between knowledge assets and chunks for graph queries';
COMMENT ON TABLE knowledge_processing_jobs IS 'Async processing job tracking for knowledge pipeline';

COMMENT ON COLUMN knowledge_assets.source_file_id IS 'Reference to original file in files table';
COMMENT ON COLUMN knowledge_assets.document_type IS 'Type classification: requirements, specification, knowledge, reference';
COMMENT ON COLUMN knowledge_assets.processing_stats IS 'Statistics about processing: chunk_count, token_count, etc.';

COMMENT ON COLUMN knowledge_chunks.qdrant_point_id IS 'UUID reference to vector point in Qdrant';
COMMENT ON COLUMN knowledge_chunks.token_count IS 'Number of tokens in the chunk content';

COMMENT ON COLUMN knowledge_relationships.neo4j_relationship_id IS 'Reference to relationship ID in Neo4j graph';
COMMENT ON COLUMN knowledge_relationships.confidence_score IS 'AI confidence score for relationship extraction (0.0-1.0)';
