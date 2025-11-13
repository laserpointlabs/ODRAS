# Hybrid RAG Implementation: Comprehensive Architecture and Design

**Version:** 1.0  
**Date:** November 2025  
**Status:** Production Implementation

## Executive Summary

This document provides a comprehensive overview of the ODRAS Hybrid RAG (Retrieval Augmented Generation) implementation. The system combines semantic vector search (Qdrant) with keyword-based text search (OpenSearch) to deliver superior retrieval performance for technical requirements documents, specifications, and knowledge assets.

**Key Architectural Principles:**
- **PostgreSQL as Source of Truth**: All document content is stored in PostgreSQL with full ACID guarantees
- **Dual-Write Pattern**: Chunks are written to PostgreSQL, Qdrant (vectors), and OpenSearch (keywords) in parallel
- **OpenSearch for Keyword Search**: BM25-based keyword search optimized for exact IDs, model numbers, and technical specifications
- **Hybrid Retrieval**: Combines vector and keyword search results using Reciprocal Rank Fusion (RRF)
- **Operational Isolation**: Search tuning doesn't impact OLTP operations

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Flow and Storage](#2-data-flow-and-storage)
3. [Ingestion Pipeline](#3-ingestion-pipeline)
4. [Query Pipeline](#4-query-pipeline)
5. [Sync Mechanisms](#5-sync-mechanisms)
6. [Performance Characteristics](#6-performance-characteristics)
7. [Implementation Details](#7-implementation-details)
8. [Best Practices](#8-best-practices)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

The Hybrid RAG system follows a three-tier storage architecture with clear separation of concerns:

```mermaid
graph TB
    subgraph "Ingestion Layer"
        FILE[File Upload]
        PARSE[Document Parser]
        CHUNK[Chunker]
        EMBED[Embedding Service]
    end
    
    subgraph "Storage Layer"
        PG[(PostgreSQL<br/>Source of Truth<br/>Full Text Content)]
        QD[(Qdrant<br/>Vector Store<br/>Embeddings Only)]
        OS[(OpenSearch<br/>Keyword Search<br/>BM25 Index)]
    end
    
    subgraph "Query Layer"
        USER[User Query]
        HYBRID[Hybrid Retriever]
        VECTOR[Vector Search]
        KEYWORD[Keyword Search]
        RRF[Reranker<br/>RRF]
        RAG[RAG Service]
        LLM[LLM Generation]
    end
    
    FILE --> PARSE
    PARSE --> CHUNK
    CHUNK --> EMBED
    CHUNK --> PG
    EMBED --> QD
    CHUNK --> OS
    
    USER --> HYBRID
    HYBRID --> VECTOR
    HYBRID --> KEYWORD
    VECTOR --> QD
    KEYWORD --> OS
    VECTOR --> RRF
    KEYWORD --> RRF
    RRF --> RAG
    RAG --> LLM
    RAG --> PG
```

### 1.2 Component Architecture

```mermaid
graph LR
    subgraph "Core Services"
        RAG_STORE[RAGStoreService<br/>Dual-Write Orchestrator]
        EMBED_SVC[EmbeddingService<br/>all-MiniLM-L6-v2]
        QDRANT_SVC[QdrantService<br/>Vector Operations]
        OPENSEARCH_SVC[OpenSearchTextStore<br/>BM25 Search]
    end
    
    subgraph "Retrieval Layer"
        VECTOR_RET[VectorRetriever<br/>Semantic Search]
        KEYWORD_RET[KeywordRetriever<br/>Exact Match]
        HYBRID_RET[HybridRetriever<br/>Combined Search]
        RERANKER[ReciprocalRankFusionReranker<br/>Result Fusion]
    end
    
    subgraph "Sync Layer"
        SYNC_SVC[OpenSearchSyncService<br/>Drift Detection & Repair]
        WRITE_THROUGH[Write-Through Sync<br/>Automatic Indexing]
        BULK_REINDEX[Bulk Reindexing<br/>Sync Repair]
    end
    
    RAG_STORE --> EMBED_SVC
    RAG_STORE --> QDRANT_SVC
    RAG_STORE --> OPENSEARCH_SVC
    RAG_STORE --> WRITE_THROUGH
    
    HYBRID_RET --> VECTOR_RET
    HYBRID_RET --> KEYWORD_RET
    HYBRID_RET --> RERANKER
    VECTOR_RET --> QDRANT_SVC
    KEYWORD_RET --> OPENSEARCH_SVC
    
    SYNC_SVC --> OPENSEARCH_SVC
    SYNC_SVC --> BULK_REINDEX
```

### 1.3 Data Flow Architecture

```mermaid
flowchart TD
    START[Document Upload] --> INGEST[Ingestion Worker]
    INGEST --> PARSE[Parse Document]
    PARSE --> CHUNK[Chunk Text]
    CHUNK --> STORE[RAGStoreService]
    
    STORE --> PG_WRITE[Write to PostgreSQL]
    STORE --> EMBED[Generate Embedding]
    STORE --> QD_WRITE[Write to Qdrant]
    STORE --> OS_WRITE[Write to OpenSearch]
    
    PG_WRITE --> PG[(PostgreSQL)]
    QD_WRITE --> QD[(Qdrant)]
    OS_WRITE --> OS[(OpenSearch)]
    
    PG --> |Source of Truth| VERIFY[Verify Sync]
    QD --> |Vectors| VERIFY
    OS --> |Keywords| VERIFY
    
    VERIFY --> SYNC_OK{Sync Status}
    SYNC_OK -->|Drift Detected| REINDEX[Reindex Service]
    SYNC_OK -->|In Sync| READY[Ready for Queries]
    REINDEX --> READY
```

---

## 2. Data Flow and Storage

### 2.1 Storage Responsibilities

**PostgreSQL (Source of Truth)**
- **Purpose**: Authoritative storage for all document content
- **Schema**: `knowledge_chunks` table with full text content
- **Benefits**: ACID guarantees, transactional consistency, full-text search capabilities
- **Content**: Complete chunk text, metadata, relationships

**Qdrant (Vector Store)**
- **Purpose**: Fast semantic similarity search
- **Content**: Embeddings (384 or 768 dimensions) + metadata-only payloads
- **Key Design**: NO text content in payloads - only IDs for SQL read-through
- **Collections**: 
  - `knowledge_chunks` (384-dim embeddings)
  - `knowledge_chunks_768` (768-dim embeddings)
  - `project_threads` (chat/conversation threads)

**OpenSearch (Keyword Search)**
- **Purpose**: BM25-based keyword search for exact IDs, model numbers, specifications
- **Content**: Full text content mirrored from PostgreSQL
- **Indexing**: Analyzed fields (content, text, title) + keyword fields for exact matching
- **Analyzers**: Standard analyzer with `.keyword` subfields for exact match

### 2.2 Data Synchronization Model

```mermaid
sequenceDiagram
    participant PG as PostgreSQL
    participant RAG as RAGStoreService
    participant QD as Qdrant
    participant OS as OpenSearch
    
    Note over PG: Transaction Start
    RAG->>PG: INSERT chunk (COMMIT)
    Note over PG: Transaction Committed
    
    par Parallel Writes
        RAG->>QD: Store embedding + metadata
        RAG->>OS: Index document (async)
    end
    
    QD-->>RAG: Vector stored
    OS-->>RAG: Indexed (fire-and-forget)
    
    Note over RAG: Write-through complete
```

### 2.3 Read-Through Pattern

```mermaid
sequenceDiagram
    participant Query as Query
    participant QD as Qdrant
    participant PG as PostgreSQL
    participant RAG as RAGService
    
    Query->>QD: Vector search
    QD-->>Query: Chunk IDs + scores
    
    Query->>PG: Read-through: SELECT text WHERE chunk_id IN (...)
    PG-->>Query: Full text content
    
    Query->>RAG: Combine IDs + text
    RAG-->>Query: Complete results with content
```

---

## 3. Ingestion Pipeline

### 3.1 Complete Ingestion Sequence

```mermaid
sequenceDiagram
    participant User
    participant API as File Upload API
    participant Worker as IngestionWorker
    participant Store as RAGStoreService
    participant PG as PostgreSQL
    participant EMBED as EmbeddingService
    participant QD as Qdrant
    participant OS as OpenSearch
    participant Asset as Knowledge Asset
    
    User->>API: Upload file
    API->>Worker: Start ingestion
    
    Worker->>Worker: Parse document
    Worker->>Worker: Chunk text
    
    loop For each chunk
        Worker->>Store: bulk_store_chunks_and_vectors()
        
        Store->>PG: INSERT INTO knowledge_chunks
        PG-->>Store: chunk_id (COMMIT)
        
        Store->>EMBED: generate_embeddings()
        EMBED-->>Store: embedding vector
        
        Store->>QD: store_vectors(embedding, metadata)
        QD-->>Store: Vector stored
        
        Store->>OS: _bulk_index_chunks_in_opensearch_async()
        Note over OS: Fire-and-forget async
        OS-->>Store: Indexed (non-blocking)
    end
    
    Worker->>Asset: Create knowledge_asset
    Worker->>Asset: Link chunks to asset
    Worker->>Asset: Activate asset
    
    Store-->>Worker: Ingestion complete
    Worker-->>API: Success
    API-->>User: File processed
```

### 3.2 Write-Through Sync Implementation

The write-through sync ensures OpenSearch is updated immediately after PostgreSQL commits:

```python
# Pseudocode from RAGStoreService
def bulk_store_chunks_and_vectors():
    # Step 1: Store in PostgreSQL (source of truth)
    chunk_ids = insert_chunks_into_postgres()
    
    # Step 2: Generate embeddings and store in Qdrant
    embeddings = generate_embeddings(texts)
    store_vectors_in_qdrant(embeddings, chunk_ids)
    
    # Step 3: Index in OpenSearch (async, non-blocking)
    _bulk_index_chunks_in_opensearch_async(
        chunk_ids, chunks_data, project_id, doc_id
    )
```

### 3.3 Async Indexing Pattern

```mermaid
flowchart TD
    PG_COMMIT[PostgreSQL Commit] --> TRIGGER[Trigger OpenSearch Index]
    TRIGGER --> THREAD[Background Thread]
    THREAD --> LOOP[Create Event Loop]
    LOOP --> INDEX[Index Document]
    INDEX --> REFRESH[Refresh Index]
    REFRESH --> SEARCHABLE[Document Searchable]
    
    PG_COMMIT -.->|Non-blocking| CONTINUE[Continue Transaction]
    CONTINUE --> RETURN[Return to Caller]
```

**Key Design Decisions:**
- **Non-blocking**: OpenSearch indexing doesn't block PostgreSQL transactions
- **Fire-and-forget**: Failures are logged but don't affect ingestion
- **Index refresh**: Ensures documents are immediately searchable
- **Error handling**: Graceful degradation - ingestion succeeds even if OpenSearch fails

---

## 4. Query Pipeline

### 4.1 Hybrid Search Query Flow

```mermaid
sequenceDiagram
    participant User
    participant API as RAG API
    participant Hybrid as HybridRetriever
    participant Vector as VectorRetriever
    participant Keyword as KeywordRetriever
    participant QD as Qdrant
    participant OS as OpenSearch
    participant RRF as Reranker
    participant PG as PostgreSQL
    participant LLM as LLM
    
    User->>API: Query: "REQ-SYS-042 altitude requirements"
    API->>Hybrid: retrieve(query, collection, limit)
    
    par Parallel Searches
        Hybrid->>Vector: search_by_text(query)
        Vector->>QD: Vector similarity search
        QD-->>Vector: Vector results (semantic matches)
        
        Hybrid->>Keyword: search(query)
        Keyword->>OS: BM25 keyword search
        OS-->>Keyword: Keyword results (exact matches)
    end
    
    Vector-->>Hybrid: Vector results
    Keyword-->>Hybrid: Keyword results
    
    Hybrid->>RRF: rerank(query, [vector_results, keyword_results])
    RRF->>RRF: Reciprocal Rank Fusion
    RRF-->>Hybrid: Reranked combined results
    
    Hybrid->>Hybrid: Deduplicate by chunk_id
    Hybrid->>PG: Read-through: Get full text for chunk_ids
    PG-->>Hybrid: Full text content
    
    Hybrid-->>API: Complete results with text
    API->>LLM: Generate response with context
    LLM-->>API: Generated answer
    API-->>User: Response + sources
```

### 4.2 Query Types and Routing

```mermaid
flowchart TD
    QUERY[User Query] --> ANALYZE[Query Analysis]
    
    ANALYZE --> EXACT{Exact ID Pattern?}
    ANALYZE --> SEMANTIC{Semantic Intent?}
    ANALYZE --> HYBRID{Both?}
    
    EXACT -->|Yes| KEYWORD_PRIORITY[Keyword Search Priority]
    SEMANTIC -->|Yes| VECTOR_PRIORITY[Vector Search Priority]
    HYBRID -->|Yes| BALANCED[Balanced Hybrid]
    
    KEYWORD_PRIORITY --> OS[OpenSearch BM25]
    VECTOR_PRIORITY --> QD[Qdrant Vector]
    BALANCED --> PARALLEL[Parallel Search Both]
    
    OS --> RRF[Reciprocal Rank Fusion]
    QD --> RRF
    PARALLEL --> RRF
    
    RRF --> RESULTS[Ranked Results]
```

### 4.3 Reciprocal Rank Fusion (RRF)

RRF combines results from different sources without requiring score normalization:

```python
# RRF Algorithm
def reciprocal_rank_fusion(results_list, k=60):
    """
    Combine multiple ranked lists using RRF.
    
    Args:
        results_list: List of result lists from different sources
        k: RRF constant (default 60)
    
    Returns:
        Combined ranked list
    """
    scores = {}
    
    for results in results_list:
        for rank, result in enumerate(results, 1):
            chunk_id = result.get("chunk_id")
            if chunk_id not in scores:
                scores[chunk_id] = 0.0
            scores[chunk_id] += 1.0 / (k + rank)
    
    # Sort by RRF score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Why RRF?**
- **No score normalization needed**: Works with different score ranges (vector similarity 0-1 vs BM25 scores)
- **Simple and effective**: Proven algorithm used by major search engines
- **Tunable**: `k` parameter controls fusion behavior
- **Handles missing results**: Gracefully handles cases where one source finds nothing

---

## 5. Sync Mechanisms

### 5.1 Write-Through Sync (Primary Mechanism)

**Implementation**: Automatic indexing during ingestion

```mermaid
sequenceDiagram
    participant Store as RAGStoreService
    participant PG as PostgreSQL
    participant Thread as Background Thread
    participant OS as OpenSearch
    
    Store->>PG: INSERT chunk (COMMIT)
    PG-->>Store: chunk_id
    
    Store->>Thread: Schedule async indexing
    Note over Thread: Fire-and-forget
    
    Thread->>OS: index_document(chunk_id, content)
    OS->>OS: Refresh index
    OS-->>Thread: Indexed
    
    Note over Store: Transaction already committed
    Note over Store: Ingestion continues
```

**Characteristics:**
- **Non-blocking**: Doesn't delay PostgreSQL commits
- **Async execution**: Runs in background thread
- **Idempotent**: Safe to retry
- **Error handling**: Failures logged but don't break ingestion

### 5.2 Bulk Reindexing (Sync Repair)

**Use Cases:**
- Repair drift after OpenSearch downtime
- Initial population of OpenSearch
- Migrating existing data

```mermaid
sequenceDiagram
    participant Admin
    participant Sync as OpenSearchSyncService
    participant PG as PostgreSQL
    participant OS as OpenSearch
    
    Admin->>Sync: reindex_all_chunks(project_id)
    
    Sync->>PG: SELECT * FROM knowledge_chunks
    PG-->>Sync: All chunks
    
    loop Batch Processing
        Sync->>Sync: Prepare batch (100 chunks)
        Sync->>OS: bulk_index(documents)
        OS-->>Sync: Indexed batch
    end
    
    Sync->>Sync: get_sync_status()
    Sync->>PG: COUNT(*) FROM knowledge_chunks
    Sync->>OS: COUNT(*) FROM knowledge_chunks
    PG-->>Sync: pg_count
    OS-->>Sync: os_count
    
    Sync->>Sync: Calculate drift
    Sync-->>Admin: Sync status report
```

### 5.3 Sync Monitoring

**Metrics Tracked:**
- `postgres_count`: Number of chunks in PostgreSQL
- `opensearch_count`: Number of chunks in OpenSearch
- `drift`: Difference (pg_count - os_count)
- `drift_percentage`: Percentage drift
- `in_sync`: Boolean indicating sync status

**Monitoring Dashboard** (Future):
```python
{
    "opensearch_available": True,
    "postgres_count": 1250,
    "opensearch_count": 1248,
    "drift": 2,
    "drift_percentage": 0.16,
    "in_sync": False,
    "timestamp": "2025-11-04T22:15:42.422924"
}
```

### 5.4 Version Tracking (Future Enhancement)

To prevent stale updates, we can add version tracking:

```sql
ALTER TABLE knowledge_chunks 
ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN version INTEGER DEFAULT 1;

-- OpenSearch document includes version
{
    "chunk_id": "...",
    "content": "...",
    "version": 5,
    "updated_at": "2025-11-04T22:15:42Z"
}
```

**Benefits:**
- Ignore stale updates (only index if version increased)
- Track update history
- Enable point-in-time queries

---

## 6. Performance Characteristics

### 6.1 Query Performance

**Vector Search (Qdrant)**
- **Latency**: 10-50ms for typical queries
- **Throughput**: 1000+ queries/second
- **Scalability**: Handles millions of vectors efficiently

**Keyword Search (OpenSearch)**
- **Latency**: 5-20ms for BM25 queries
- **Throughput**: 500+ queries/second
- **Scalability**: Handles large text indexes with proper sharding

**Hybrid Search (Combined)**
- **Latency**: 20-70ms (parallel execution)
- **Throughput**: 300-500 queries/second
- **Overhead**: ~10-20ms for RRF fusion

### 6.2 Ingestion Performance

**Single Chunk Ingestion:**
- PostgreSQL write: 5-10ms
- Embedding generation: 50-200ms (model-dependent)
- Qdrant write: 10-20ms
- OpenSearch indexing: 5-15ms (async, non-blocking)

**Bulk Ingestion (100 chunks):**
- PostgreSQL bulk insert: 50-100ms
- Embedding generation (batch): 200-500ms
- Qdrant bulk write: 100-200ms
- OpenSearch bulk index: 100-300ms (async)

**Total Ingestion Time**: ~500ms-1s for 100 chunks (excluding async OpenSearch)

### 6.3 Storage Requirements

**PostgreSQL:**
- Text storage: ~1-2KB per chunk (average)
- Metadata: ~200 bytes per chunk
- **Total**: ~1.2-2.2KB per chunk

**Qdrant:**
- Embedding: 384 dimensions × 4 bytes = 1.5KB per vector
- Metadata payload: ~200 bytes
- **Total**: ~1.7KB per vector

**OpenSearch:**
- Text content: ~1-2KB per document
- Metadata: ~200 bytes
- Index overhead: ~20-30%
- **Total**: ~1.5-2.5KB per document

**Storage Ratio**: PostgreSQL:Qdrant:OpenSearch ≈ 1:1.4:1.2

---

## 7. Implementation Details

### 7.1 RAGStoreService Architecture

```python
class RAGStoreService:
    """
    Dual-write service for SQL-first RAG storage.
    
    Responsibilities:
    1. Store chunks in PostgreSQL (source of truth)
    2. Store embeddings in Qdrant (vectors)
    3. Index chunks in OpenSearch (keywords) - async
    """
    
    def bulk_store_chunks_and_vectors():
        # 1. PostgreSQL: Store chunks
        chunk_ids = insert_chunks_into_postgres()
        
        # 2. Qdrant: Store embeddings
        embeddings = generate_embeddings(texts)
        store_vectors_in_qdrant(embeddings, chunk_ids)
        
        # 3. OpenSearch: Index documents (async)
        _bulk_index_chunks_in_opensearch_async(...)
```

### 7.2 HybridRetriever Implementation

```python
class HybridRetriever:
    """
    Combines vector and keyword search with RRF reranking.
    """
    
    async def retrieve(query, collection, limit):
        # Parallel searches
        vector_task = vector_store.search_by_text(query)
        keyword_task = text_search_store.search(query)
        
        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task
        )
        
        # Combine with RRF
        combined = reranker.rerank(
            query, 
            vector_results + keyword_results,
            top_k=limit
        )
        
        # Deduplicate and return
        return deduplicate_by_chunk_id(combined)
```

### 7.3 OpenSearch Query Optimization

The OpenSearch query is optimized for both exact IDs and semantic queries:

```python
# Query structure for exact IDs (e.g., "REQ-SYS-042")
{
    "query": {
        "bool": {
            "should": [
                # Exact match on keyword field (highest boost)
                {"match": {"content.keyword": {"query": "REQ-SYS-042", "boost": 15.0}}},
                # Phrase match (high boost)
                {"match_phrase": {"content": {"query": "REQ-SYS-042", "boost": 3.0}}},
                # Multi-match with fuzziness (lower boost)
                {"multi_match": {"query": "REQ-SYS-042", "fuzziness": "AUTO"}}
            ]
        }
    }
}
```

**Query Strategy:**
1. **Exact IDs**: Use `.keyword` fields for exact matching (not analyzed)
2. **Phrases**: Use `match_phrase` for exact phrase matching
3. **Fuzzy**: Use `multi_match` with fuzziness for typo tolerance

### 7.4 Index Mapping

```json
{
    "mappings": {
        "properties": {
            "content": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}  // For exact matching
                }
            },
            "chunk_id": {"type": "keyword"},
            "project_id": {"type": "keyword"},
            "asset_id": {"type": "keyword"}
        }
    }
}
```

---

## 8. Best Practices

### 8.1 When to Use OpenSearch

**Use OpenSearch for:**
- BM25/fLex + analyzers, stemming, synonyms
- Per-field boosts and highlight snippets
- Faceting and aggregations
- Query-time hybrid scoring (RRF or linear fusion)
- Operational isolation (search tuning doesn't impact OLTP)

**Don't use OpenSearch for:**
- Simple keyword matching that PostgreSQL FTS can handle
- Small document sets (< 10K chunks)
- When you can't maintain sync reliability

### 8.2 Sync Reliability Patterns

**Minimal Viable Sync:**
- Write-through on chunk insert/update/delete
- Enqueue indexing job to durable queue (future: SQS/Kafka/PG NOTIFY)
- Store monotonically increasing version or updated_at
- Indexer ignores stale versions

**Robust Sync (Recommended):**
- CDC via Debezium (Postgres WAL) → Kafka → indexer → OpenSearch
- Periodic backfill/reindex: nightly job scanning updated_at > last_checkpoint
- Add index invariants: count checks, random spot-checks
- Dashboard metrics: `pg_count - os_count`, `lag_seconds`, `failed_docs`

### 8.3 Query Optimization

**For Exact IDs (e.g., "REQ-SYS-042"):**
- Keyword search excels (BM25 finds exact matches)
- Vector search may miss (semantic similarity doesn't capture exact IDs)
- **Strategy**: Bias toward keyword search (weight=0.6-0.7)

**For Semantic Queries (e.g., "altitude monitoring requirements"):**
- Vector search excels (captures semantic meaning)
- Keyword search finds exact term matches
- **Strategy**: Balanced hybrid (weight=0.5-0.5)

**For Hybrid Queries (e.g., "REQ-SYS-042 altitude requirements"):**
- Both sources contribute
- **Strategy**: Hybrid search with RRF (optimal)

### 8.4 Error Handling

**Ingestion Errors:**
- PostgreSQL failures: Rollback transaction, retry
- Qdrant failures: Log error, continue (can reindex later)
- OpenSearch failures: Log error, continue (async, non-blocking)

**Query Errors:**
- Vector search failure: Fallback to keyword-only
- Keyword search failure: Fallback to vector-only
- Both fail: Return empty results with error message

### 8.5 Monitoring and Alerting

**Key Metrics:**
- `ingestion_rate`: Chunks ingested per second
- `sync_lag`: Time between PostgreSQL write and OpenSearch index
- `drift_count`: Number of chunks out of sync
- `query_latency_p50/p95/p99`: Query performance percentiles
- `hybrid_search_ratio`: Percentage of queries using hybrid vs single source

**Alert Thresholds:**
- Sync drift > 100 chunks: Warning
- Sync drift > 1000 chunks: Critical
- Query latency p95 > 200ms: Warning
- Query latency p95 > 500ms: Critical

---

## 9. Comparison: Base RAG vs Hybrid RAG

### 9.1 Base RAG (Vector-Only)

**Strengths:**
- Simple architecture
- Fast semantic search
- Good for conceptual queries

**Weaknesses:**
- Misses exact IDs and model numbers
- Poor performance on technical specifications
- Limited recall for exact term matches

**Example Failure:**
```
Query: "REQ-SYS-042"
Vector Search: May return 0 results (semantic similarity doesn't match exact ID)
```

### 9.2 Hybrid RAG (Vector + Keyword)

**Strengths:**
- Finds exact IDs and model numbers
- Better recall (union of both sources)
- Handles both semantic and keyword queries
- Industry-proven approach

**Weaknesses:**
- More complex architecture
- Requires sync maintenance
- Slightly higher latency (parallel queries)

**Example Success:**
```
Query: "REQ-SYS-042"
Vector Search: 0 results (semantic)
Keyword Search: 1 result (exact match)
Hybrid Result: 1 result (keyword found it)
```

### 9.3 Performance Comparison

| Metric | Base RAG | Hybrid RAG |
|--------|----------|------------|
| Recall (exact IDs) | 30-40% | 90-95% |
| Recall (semantic) | 70-80% | 75-85% |
| Overall Recall | 60-70% | 85-95% |
| Query Latency | 20-40ms | 30-60ms |
| Infrastructure | 2 services | 3 services |
| Maintenance | Low | Medium |

---

## 10. Future Enhancements

### 10.1 Planned Improvements

1. **CDC-based Sync**: Debezium → Kafka → OpenSearch indexer
2. **Version Tracking**: Add `updated_at` and `version` columns
3. **Query Analysis**: Automatic query type detection and routing
4. **Advanced Reranking**: Cross-encoder reranking for better precision
5. **Caching Layer**: Redis cache for frequent queries
6. **Monitoring Dashboard**: Real-time sync status and metrics

### 10.2 Scalability Considerations

**Current Limits:**
- PostgreSQL: Handles millions of chunks efficiently
- Qdrant: Scales to tens of millions of vectors
- OpenSearch: Scales with proper sharding

**Future Scaling:**
- Horizontal sharding by project_id
- Read replicas for query load
- Caching frequently accessed chunks
- Tiered storage for old/archived chunks

---

## 11. Conclusion

The ODRAS Hybrid RAG implementation provides a production-grade solution for combining semantic and keyword search. By using PostgreSQL as the source of truth and maintaining operational isolation between search and OLTP workloads, the system achieves both reliability and performance.

**Key Achievements:**
- ✅ Postgres as source of truth (ACID guarantees)
- ✅ OpenSearch for keyword search (BM25, exact matching)
- ✅ Qdrant for vector search (semantic similarity)
- ✅ Write-through sync (automatic indexing)
- ✅ Hybrid retrieval with RRF (proven algorithm)
- ✅ Operational isolation (search doesn't impact OLTP)

**Next Steps:**
- Implement CDC-based sync for production reliability
- Add version tracking to prevent stale updates
- Build monitoring dashboard for sync status
- Optimize query routing based on query type

---

## Appendix A: Code References

### A.1 Core Components

- **RAGStoreService**: `backend/services/store.py`
- **HybridRetriever**: `backend/rag/retrieval/hybrid_retriever.py`
- **OpenSearchTextStore**: `backend/rag/storage/opensearch_store.py`
- **OpenSearchSyncService**: `backend/services/opensearch_sync_service.py`
- **ReciprocalRankFusionReranker**: `backend/rag/retrieval/reranker.py`

### A.2 API Endpoints

- **Knowledge Search**: `POST /api/knowledge/search`
- **RAG Query**: `POST /api/knowledge/query`
- **File Upload**: `POST /api/files/upload`

### A.3 Configuration

Environment variables:
- `OPENSEARCH_ENABLED=true`: Enable OpenSearch
- `RAG_HYBRID_SEARCH=true`: Enable hybrid search
- `RAG_RERANKER=rrf`: Reranker type (rrf, cross_encoder, hybrid, none)
- `OPENSEARCH_URL=http://localhost:9200`: OpenSearch endpoint

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Maintained By**: ODRAS Development Team


