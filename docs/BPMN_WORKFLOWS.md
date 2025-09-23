# ODRAS BPMN Workflows<br>
<br>
This document describes the new BPMN workflows implemented for the ODRAS system, converting the RAG pipeline and knowledge management processes into visual, orchestrated workflows.<br>
<br>
## Overview<br>
<br>
Two new BPMN workflows have been created to handle core ODRAS functionality:<br>
<br>
1. **RAG Pipeline Process** (`rag_pipeline.bpmn`) - Document ingestion and RAG processing<br>
2. **Add to Knowledge Process** (`add_to_knowledge.bpmn`) - Knowledge base management<br>
<br>
These workflows provide visual process orchestration, human oversight capabilities, and robust error handling through the Camunda BPMN engine.<br>
<br>
## RAG Pipeline Process<br>
<br>
### Process Flow<br>
<br>
```<br>
Document Upload → Validate → Parse → Chunk → Generate Embeddings → Store Vector → Store Metadata → Update Index → Complete<br>
```<br>
<br>
### Key Features<br>
<br>
- **Document Validation**: Checks file format, size, and content integrity<br>
- **Flexible Parsing**: Supports PDF, DOCX, TXT, and Markdown formats<br>
- **Smart Chunking**: Configurable chunk size and overlap with sentence preservation<br>
- **Embedding Generation**: Vector embeddings for semantic search<br>
- **Multi-Store Persistence**: Vector database, metadata storage, and search indexing<br>
- **Error Handling**: Validation failures are properly routed and reported<br>
<br>
### Process Variables<br>
<br>
| Variable | Type | Description |<br>
|----------|------|-------------|<br>
| `document_content` | File/String | Raw document content or file path |<br>
| `document_filename` | String | Original filename |<br>
| `document_mime_type` | String | MIME type of document |<br>
| `validation_result` | String | 'success' or 'failure' |<br>
| `parsed_content` | String | Extracted text content |<br>
| `chunks_created` | Array | List of document chunks |<br>
| `embeddings_generated` | Array | Vector embeddings |<br>
| `storage_results` | Object | Results from storage operations |<br>
<br>
### External Task Scripts<br>
<br>
- `task_validate_document.py` - Document validation and metadata extraction<br>
- `task_parse_document.py` - Content extraction from various formats<br>
- `task_chunk_document.py` - Text chunking with configurable parameters<br>
- `task_generate_embeddings.py` - Vector embedding generation<br>
- `task_store_vector_rag.py` - Vector database storage<br>
- `task_store_metadata.py` - Document metadata persistence<br>
- `task_update_search_index.py` - Search index updates<br>
<br>
## Add to Knowledge Process<br>
<br>
### Process Flow<br>
<br>
```<br>
Knowledge Request → Validate Input → Check Duplicates → Transform → Enrich → Quality Check → [Parallel Storage] → Update Index → Notify → Complete<br>
                      ↓                    ↓                                    ↓<br>
                  Review Input      Resolve Duplicates              Review Quality Issues<br>
```<br>
<br>
### Key Features<br>
<br>
- **Input Validation**: Content quality and format validation<br>
- **Duplicate Detection**: Semantic similarity search to identify duplicates<br>
- **Human Review Points**: User tasks for validation, duplicate resolution, and quality review<br>
- **Knowledge Transformation**: Standardization and enrichment of knowledge content<br>
- **Parallel Storage**: Simultaneous storage in vector, graph, and RDF databases<br>
- **Stakeholder Notification**: Automated notifications about knowledge additions<br>
- **Quality Assurance**: Automated and manual quality checks<br>
<br>
### Decision Gateways<br>
<br>
1. **Input Valid?** - Routes to validation correction or duplicate check<br>
2. **Duplicates Found?** - Routes to duplicate resolution or knowledge transformation<br>
3. **Quality Acceptable?** - Routes to quality review or storage<br>
<br>
### Process Variables<br>
<br>
| Variable | Type | Description |<br>
|----------|------|-------------|<br>
| `knowledge_content` | String/Object | Raw knowledge content |<br>
| `knowledge_format` | String | Format type ('text', 'json', 'structured') |<br>
| `knowledge_metadata` | Object | Associated metadata (title, source, tags) |<br>
| `input_validation_result` | String | 'valid' or 'invalid' |<br>
| `duplicates_found` | String | 'true' or 'false' |<br>
| `duplicate_candidates` | Array | List of potential duplicates |<br>
| `quality_check_result` | String | 'accepted' or 'rejected' |<br>
| `processed_knowledge` | Object | Final processed knowledge data |<br>
<br>
### External Task Scripts<br>
<br>
- `task_validate_knowledge_input.py` - Knowledge content and metadata validation<br>
- `task_check_duplicate_knowledge.py` - Semantic duplicate detection<br>
- `task_transform_knowledge.py` - Knowledge standardization and structuring<br>
- `task_enrich_knowledge.py` - Contextual enrichment and linking<br>
- `task_quality_assurance.py` - Automated quality checks<br>
- `task_store_knowledge_vector.py` - Vector database storage<br>
- `task_store_knowledge_graph.py` - Graph database storage<br>
- `task_store_knowledge_rdf.py` - RDF triple store storage<br>
- `task_update_knowledge_index.py` - Knowledge index updates<br>
- `task_notify_stakeholders.py` - Stakeholder notifications<br>
<br>
## Deployment<br>
<br>
### Prerequisites<br>
<br>
1. Camunda 7 running on `http://localhost:8080`<br>
2. All data stores (Qdrant, Neo4j, Fuseki) running<br>
3. ODRAS backend services available<br>
<br>
### Deploy Workflows<br>
<br>
```bash<br>
# Deploy both workflows to Camunda<br>
python scripts/deploy_bpmn_workflows.py<br>
```<br>
<br>
### Manual Deployment<br>
<br>
1. Open Camunda Cockpit at `http://localhost:8080`<br>
2. Go to Deployments<br>
3. Upload `bpmn/rag_pipeline.bpmn` and `bpmn/add_to_knowledge.bpmn`<br>
4. Verify deployment success<br>
<br>
## Usage<br>
<br>
### Starting RAG Pipeline<br>
<br>
```bash<br>
# Via REST API<br>
curl -X POST "http://localhost:8080/engine-rest/process-definition/key/rag_pipeline_process/start" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{<br>
    "variables": {<br>
      "document_content": {"value": "path/to/document.pdf", "type": "String"},<br>
      "document_filename": {"value": "document.pdf", "type": "String"}<br>
    }<br>
  }'<br>
```<br>
<br>
### Starting Add to Knowledge<br>
<br>
```bash<br>
# Via REST API<br>
curl -X POST "http://localhost:8080/engine-rest/process-definition/key/add_to_knowledge_process/start" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{<br>
    "variables": {<br>
      "knowledge_content": {"value": "New knowledge content here", "type": "String"},<br>
      "knowledge_format": {"value": "text", "type": "String"},<br>
      "knowledge_metadata": {"value": "{\"title\": \"New Knowledge\", \"source\": \"User\"}", "type": "String"}<br>
    }<br>
  }'<br>
```<br>
<br>
## Monitoring<br>
<br>
### Camunda Cockpit<br>
<br>
Access `http://localhost:8080` to:<br>
<br>
- Monitor process instances in real-time<br>
- View process variables and execution history<br>
- Handle user tasks (validation, duplicate resolution, quality review)<br>
- Analyze process performance and bottlenecks<br>
- Manage failed tasks and exceptions<br>
<br>
### Process Analytics<br>
<br>
The workflows provide comprehensive metrics:<br>
<br>
- Processing times for each step<br>
- Success/failure rates<br>
- User task completion times<br>
- Quality scores and validation results<br>
- Storage performance metrics<br>
<br>
## Configuration<br>
<br>
### Chunking Configuration<br>
<br>
Modify chunking parameters by setting process variables:<br>
<br>
```json<br>
{<br>
  "chunk_size": {"value": 1000, "type": "Integer"},<br>
  "overlap_size": {"value": 200, "type": "Integer"},<br>
  "preserve_sentences": {"value": true, "type": "Boolean"}<br>
}<br>
```<br>
<br>
### Duplicate Detection<br>
<br>
Configure duplicate detection sensitivity:<br>
<br>
```json<br>
{<br>
  "similarity_threshold": {"value": 0.85, "type": "Double"},<br>
  "search_scope": {"value": "project", "type": "String"}<br>
}<br>
```<br>
<br>
### Quality Thresholds<br>
<br>
Set quality assurance parameters:<br>
<br>
```json<br>
{<br>
  "min_content_length": {"value": 100, "type": "Integer"},<br>
  "max_content_length": {"value": 50000, "type": "Integer"},<br>
  "require_metadata_fields": {"value": "[\"title\", \"source\"]", "type": "String"}<br>
}<br>
```<br>
<br>
## Error Handling<br>
<br>
Both workflows include comprehensive error handling:<br>
<br>
1. **Validation Errors**: Route to correction tasks or end events<br>
2. **Processing Failures**: Logged with detailed error messages<br>
3. **Storage Errors**: Retry mechanisms and fallback strategies<br>
4. **Timeout Handling**: Configurable timeouts for long-running tasks<br>
5. **Dead Letter Queue**: Failed tasks can be retried or escalated<br>
<br>
## Extension Points<br>
<br>
The BPMN workflows are designed for easy extension:<br>
<br>
1. **Additional Validation Steps**: Add new validation tasks in sequence<br>
2. **Custom Transformations**: Insert transformation tasks in the knowledge pipeline<br>
3. **Notification Channels**: Add parallel notification tasks<br>
4. **Quality Gates**: Insert additional quality check gateways<br>
5. **Integration Points**: Add service tasks for external system integration<br>
<br>
## Benefits<br>
<br>
1. **Visual Process Management**: Non-technical stakeholders can understand and modify workflows<br>
2. **Human Oversight**: User tasks provide control points for quality assurance<br>
3. **Robust Error Handling**: Failed steps are clearly identified and can be retried<br>
4. **Process Analytics**: Detailed metrics on processing times and success rates<br>
5. **Scalability**: Parallel processing where possible, sequential where needed<br>
6. **Auditability**: Complete audit trail of all process executions<br>
7. **Flexibility**: Easy to modify processes without code changes<br>
<br>
## Next Steps<br>
<br>
1. **User Interface Integration**: Build UI components for user tasks<br>
2. **Advanced Analytics**: Add process intelligence and optimization<br>
3. **Custom Connectors**: Create connectors for external systems<br>
4. **Process Variants**: Create specialized workflows for different document types<br>
5. **Auto-Optimization**: Machine learning to optimize process parameters<br>
<br>
<br>
<br>
<br>

