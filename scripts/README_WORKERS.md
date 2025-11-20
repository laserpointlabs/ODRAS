# Essential Worker Scripts

## ⚠️ DO NOT MOVE OR DELETE

These scripts are **REQUIRED** for ODRAS BPMN workflow processing:

- `run_external_task_worker.py` - Complex worker for RAG query processing and advanced tasks
- `simple_external_worker.py` - Simple worker for file upload processing tasks

## Purpose

These workers are started automatically by `odras.sh` when:
- Starting the application (`./odras.sh start`)
- Initializing databases (`./odras.sh init-db`)
- Deploying BPMN workflows

## What They Do

### Complex Worker (`run_external_task_worker.py`)
- Handles RAG query pipeline tasks
- Processes knowledge management workflows
- Manages document ingestion and enrichment

### Simple Worker (`simple_external_worker.py`)
- Executes file upload processing steps:
  - `extract-text` → `step_extract_text.py`
  - `chunk-document` → `step_chunk_document.py`
  - `generate-embeddings` → `step_generate_embeddings.py`
  - `create-knowledge-asset` → `step_create_knowledge_asset.py`
  - `store-vector-chunks` → `step_store_vector_chunks.py`
  - `activate-knowledge-asset` → `step_activate_knowledge_asset.py`

## Status

These scripts are **ACTIVE** and **ESSENTIAL**. They should never be moved to `cleanup/unused_scripts/`.

## References

- `odras.sh` lines 707-798 (worker startup functions)
- BPMN workflows in `bpmn/` directory depend on these workers
- Documentation: `docs/architecture/RAG_ARCHITECTURE.md`
