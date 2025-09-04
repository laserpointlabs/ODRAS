# ODRAS BPMN Workflows

This document describes the new BPMN workflows implemented for the ODRAS system, converting the RAG pipeline and knowledge management processes into visual, orchestrated workflows.

## Overview

Two new BPMN workflows have been created to handle core ODRAS functionality:

1. **RAG Pipeline Process** (`rag_pipeline.bpmn`) - Document ingestion and RAG processing
2. **Add to Knowledge Process** (`add_to_knowledge.bpmn`) - Knowledge base management

These workflows provide visual process orchestration, human oversight capabilities, and robust error handling through the Camunda BPMN engine.

## RAG Pipeline Process

### Process Flow

```
Document Upload → Validate → Parse → Chunk → Generate Embeddings → Store Vector → Store Metadata → Update Index → Complete
```

### Key Features

- **Document Validation**: Checks file format, size, and content integrity
- **Flexible Parsing**: Supports PDF, DOCX, TXT, and Markdown formats
- **Smart Chunking**: Configurable chunk size and overlap with sentence preservation
- **Embedding Generation**: Vector embeddings for semantic search
- **Multi-Store Persistence**: Vector database, metadata storage, and search indexing
- **Error Handling**: Validation failures are properly routed and reported

### Process Variables

| Variable | Type | Description |
|----------|------|-------------|
| `document_content` | File/String | Raw document content or file path |
| `document_filename` | String | Original filename |
| `document_mime_type` | String | MIME type of document |
| `validation_result` | String | 'success' or 'failure' |
| `parsed_content` | String | Extracted text content |
| `chunks_created` | Array | List of document chunks |
| `embeddings_generated` | Array | Vector embeddings |
| `storage_results` | Object | Results from storage operations |

### External Task Scripts

- `task_validate_document.py` - Document validation and metadata extraction
- `task_parse_document.py` - Content extraction from various formats
- `task_chunk_document.py` - Text chunking with configurable parameters
- `task_generate_embeddings.py` - Vector embedding generation
- `task_store_vector_rag.py` - Vector database storage
- `task_store_metadata.py` - Document metadata persistence
- `task_update_search_index.py` - Search index updates

## Add to Knowledge Process

### Process Flow

```
Knowledge Request → Validate Input → Check Duplicates → Transform → Enrich → Quality Check → [Parallel Storage] → Update Index → Notify → Complete
                      ↓                    ↓                                    ↓
                  Review Input      Resolve Duplicates              Review Quality Issues
```

### Key Features

- **Input Validation**: Content quality and format validation
- **Duplicate Detection**: Semantic similarity search to identify duplicates
- **Human Review Points**: User tasks for validation, duplicate resolution, and quality review
- **Knowledge Transformation**: Standardization and enrichment of knowledge content
- **Parallel Storage**: Simultaneous storage in vector, graph, and RDF databases
- **Stakeholder Notification**: Automated notifications about knowledge additions
- **Quality Assurance**: Automated and manual quality checks

### Decision Gateways

1. **Input Valid?** - Routes to validation correction or duplicate check
2. **Duplicates Found?** - Routes to duplicate resolution or knowledge transformation
3. **Quality Acceptable?** - Routes to quality review or storage

### Process Variables

| Variable | Type | Description |
|----------|------|-------------|
| `knowledge_content` | String/Object | Raw knowledge content |
| `knowledge_format` | String | Format type ('text', 'json', 'structured') |
| `knowledge_metadata` | Object | Associated metadata (title, source, tags) |
| `input_validation_result` | String | 'valid' or 'invalid' |
| `duplicates_found` | String | 'true' or 'false' |
| `duplicate_candidates` | Array | List of potential duplicates |
| `quality_check_result` | String | 'accepted' or 'rejected' |
| `processed_knowledge` | Object | Final processed knowledge data |

### External Task Scripts

- `task_validate_knowledge_input.py` - Knowledge content and metadata validation
- `task_check_duplicate_knowledge.py` - Semantic duplicate detection
- `task_transform_knowledge.py` - Knowledge standardization and structuring
- `task_enrich_knowledge.py` - Contextual enrichment and linking
- `task_quality_assurance.py` - Automated quality checks
- `task_store_knowledge_vector.py` - Vector database storage
- `task_store_knowledge_graph.py` - Graph database storage
- `task_store_knowledge_rdf.py` - RDF triple store storage
- `task_update_knowledge_index.py` - Knowledge index updates
- `task_notify_stakeholders.py` - Stakeholder notifications

## Deployment

### Prerequisites

1. Camunda 7 running on `http://localhost:8080`
2. All data stores (Qdrant, Neo4j, Fuseki) running
3. ODRAS backend services available

### Deploy Workflows

```bash
# Deploy both workflows to Camunda
python scripts/deploy_bpmn_workflows.py
```

### Manual Deployment

1. Open Camunda Cockpit at `http://localhost:8080`
2. Go to Deployments
3. Upload `bpmn/rag_pipeline.bpmn` and `bpmn/add_to_knowledge.bpmn`
4. Verify deployment success

## Usage

### Starting RAG Pipeline

```bash
# Via REST API
curl -X POST "http://localhost:8080/engine-rest/process-definition/key/rag_pipeline_process/start" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "document_content": {"value": "path/to/document.pdf", "type": "String"},
      "document_filename": {"value": "document.pdf", "type": "String"}
    }
  }'
```

### Starting Add to Knowledge

```bash
# Via REST API
curl -X POST "http://localhost:8080/engine-rest/process-definition/key/add_to_knowledge_process/start" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "knowledge_content": {"value": "New knowledge content here", "type": "String"},
      "knowledge_format": {"value": "text", "type": "String"},
      "knowledge_metadata": {"value": "{\"title\": \"New Knowledge\", \"source\": \"User\"}", "type": "String"}
    }
  }'
```

## Monitoring

### Camunda Cockpit

Access `http://localhost:8080` to:

- Monitor process instances in real-time
- View process variables and execution history
- Handle user tasks (validation, duplicate resolution, quality review)
- Analyze process performance and bottlenecks
- Manage failed tasks and exceptions

### Process Analytics

The workflows provide comprehensive metrics:

- Processing times for each step
- Success/failure rates
- User task completion times
- Quality scores and validation results
- Storage performance metrics

## Configuration

### Chunking Configuration

Modify chunking parameters by setting process variables:

```json
{
  "chunk_size": {"value": 1000, "type": "Integer"},
  "overlap_size": {"value": 200, "type": "Integer"},
  "preserve_sentences": {"value": true, "type": "Boolean"}
}
```

### Duplicate Detection

Configure duplicate detection sensitivity:

```json
{
  "similarity_threshold": {"value": 0.85, "type": "Double"},
  "search_scope": {"value": "project", "type": "String"}
}
```

### Quality Thresholds

Set quality assurance parameters:

```json
{
  "min_content_length": {"value": 100, "type": "Integer"},
  "max_content_length": {"value": 50000, "type": "Integer"},
  "require_metadata_fields": {"value": "[\"title\", \"source\"]", "type": "String"}
}
```

## Error Handling

Both workflows include comprehensive error handling:

1. **Validation Errors**: Route to correction tasks or end events
2. **Processing Failures**: Logged with detailed error messages
3. **Storage Errors**: Retry mechanisms and fallback strategies
4. **Timeout Handling**: Configurable timeouts for long-running tasks
5. **Dead Letter Queue**: Failed tasks can be retried or escalated

## Extension Points

The BPMN workflows are designed for easy extension:

1. **Additional Validation Steps**: Add new validation tasks in sequence
2. **Custom Transformations**: Insert transformation tasks in the knowledge pipeline
3. **Notification Channels**: Add parallel notification tasks
4. **Quality Gates**: Insert additional quality check gateways
5. **Integration Points**: Add service tasks for external system integration

## Benefits

1. **Visual Process Management**: Non-technical stakeholders can understand and modify workflows
2. **Human Oversight**: User tasks provide control points for quality assurance
3. **Robust Error Handling**: Failed steps are clearly identified and can be retried
4. **Process Analytics**: Detailed metrics on processing times and success rates
5. **Scalability**: Parallel processing where possible, sequential where needed
6. **Auditability**: Complete audit trail of all process executions
7. **Flexibility**: Easy to modify processes without code changes

## Next Steps

1. **User Interface Integration**: Build UI components for user tasks
2. **Advanced Analytics**: Add process intelligence and optimization
3. **Custom Connectors**: Create connectors for external systems
4. **Process Variants**: Create specialized workflows for different document types
5. **Auto-Optimization**: Machine learning to optimize process parameters




