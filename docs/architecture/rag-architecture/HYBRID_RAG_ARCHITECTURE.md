# Hybrid RAG Architecture - Clean Implementation

## Current State Analysis

**What we have:**
1. **PostgreSQL** (`doc_chunk` table): Full text content stored with metadata
2. **Qdrant**: Vector embeddings with IDs-only payloads (no text)
3. **OpenSearch**: Attempted integration but not working properly

**The Problem:**
- We're trying to add OpenSearch as a separate index when we already have the text in PostgreSQL
- OpenSearch indexing is not syncing with PostgreSQL content
- Keyword search returns 0 results because OpenSearch isn't properly indexed

## Recommended Architecture (Based on Industry Best Practices)

### Option 1: PostgreSQL Native Hybrid Search (RECOMMENDED)

**Use PostgreSQL's built-in capabilities:**
- **pgvector extension**: For vector similarity search (if we want to consolidate)
- **PostgreSQL Full-Text Search (FTS)**: Built-in keyword search on `doc_chunk.text`
- **Combine both**: Single database, single query, better performance

**Pros:**
- No additional services needed
- Data stays in one place (PostgreSQL)
- PostgreSQL FTS is mature and fast
- Can combine vector + FTS in single SQL query
- Simpler architecture

**Implementation:**
```sql
-- Add FTS index to doc_chunk table
CREATE INDEX idx_doc_chunk_fts ON doc_chunk USING gin(to_tsvector('english', text));

-- Hybrid query example:
WITH vector_results AS (
  SELECT chunk_id, embedding <-> query_embedding AS distance
  FROM doc_chunk_vectors  -- if using pgvector
  WHERE embedding <-> query_embedding < 0.8
  ORDER BY distance LIMIT 10
),
fts_results AS (
  SELECT chunk_id, ts_rank(to_tsvector('english', text), query_tsquery) AS rank
  FROM doc_chunk
  WHERE to_tsvector('english', text) @@ query_tsquery
  ORDER BY rank DESC LIMIT 10
)
-- Combine and deduplicate using RRF
```

### Option 2: PostgreSQL FTS + Qdrant (SIMPLER FOR CURRENT ARCHITECTURE)

**Use what we have:**
- **PostgreSQL**: Source of truth for text, use FTS for keyword search
- **Qdrant**: Keep for vector search (already working)
- **No OpenSearch**: Remove it, use PostgreSQL FTS instead

**Pros:**
- Minimal changes to existing code
- PostgreSQL FTS is already available
- No additional services to manage
- Text already in PostgreSQL, just need to add FTS index

**Implementation:**
1. Add FTS index to `doc_chunk.text`
2. Create PostgreSQL FTS search function
3. Combine Qdrant vector results + PostgreSQL FTS results using RRF
4. Remove OpenSearch dependency

### Option 3: Keep OpenSearch BUT Fix the Architecture

**If we want OpenSearch:**
- **PostgreSQL**: Source of truth (doc_chunk table)
- **Qdrant**: Vector embeddings
- **OpenSearch**: Mirror of PostgreSQL content (not a separate index)

**Key Fix:**
- OpenSearch must be populated from PostgreSQL, not indexed separately
- When a document is ingested → store in PostgreSQL → sync to OpenSearch
- When querying → use Qdrant for vectors + OpenSearch for keywords → merge results

**Current Problem:**
- OpenSearch is empty because we're not syncing from PostgreSQL
- Test data is indexed directly to OpenSearch, bypassing the real flow

## Recommended Path Forward

**Option 2 is the cleanest for our current architecture:**
1. Use PostgreSQL FTS for keyword search (already have the text)
2. Keep Qdrant for vector search (already working)
3. Combine results using RRF (already implemented)
4. Remove OpenSearch complexity

**Why this is better:**
- Simpler: One less service to manage
- Faster: No network hop for keyword search
- More reliable: Text is already in PostgreSQL
- Industry standard: PostgreSQL FTS is well-established

## Implementation Steps

1. **Add PostgreSQL FTS index:**
   ```sql
   ALTER TABLE doc_chunk ADD COLUMN text_search_vector tsvector;
   CREATE INDEX idx_doc_chunk_fts ON doc_chunk USING gin(text_search_vector);
   ```

2. **Update ingestion to populate FTS vector:**
   ```sql
   UPDATE doc_chunk SET text_search_vector = to_tsvector('english', text);
   ```

3. **Create PostgreSQL FTS search function:**
   ```python
   def search_fts(conn, query_text: str, limit: int = 10):
       tsquery = query_text.replace(' ', ' & ')
       sql = """
       SELECT chunk_id, ts_rank(text_search_vector, to_tsquery('english', %s)) AS rank
       FROM doc_chunk
       WHERE text_search_vector @@ to_tsquery('english', %s)
       ORDER BY rank DESC
       LIMIT %s
       """
       # Execute and return results
   ```

4. **Update HybridRetriever to use PostgreSQL FTS instead of OpenSearch:**
   - Replace `TextSearchStore` with `PostgreSQLFTSStore`
   - Remove OpenSearch dependency

5. **Update tests to use PostgreSQL FTS**

## Migration Path

1. **Phase 1**: Add PostgreSQL FTS alongside OpenSearch (both work)
2. **Phase 2**: Switch HybridRetriever to use PostgreSQL FTS
3. **Phase 3**: Remove OpenSearch once PostgreSQL FTS is proven
4. **Phase 4**: Clean up OpenSearch code and dependencies


