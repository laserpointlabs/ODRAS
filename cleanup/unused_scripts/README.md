# Unused Scripts - Safety Archive

This folder contains scripts that were removed during the repository cleanup on September 23, 2025, but are preserved as a safety net in case they're needed later.

## Scripts in this folder:

### BPMN Task Scripts (not referenced in .bpmn files):
- `task_chunk_document.py` - Document chunking task
- `task_generate_embeddings.py` - Embedding generation task  
- `task_parse_document.py` - Document parsing task
- `task_process_user_query.py` - User query processing task
- `task_retrieve_context.py` - Context retrieval task
- `task_validate_document.py` - Document validation task

### Test Scripts (redundant/obsolete):
- `camunda_rag_test.py` - Camunda RAG testing
- `comprehensive_rag_test.py` - Comprehensive RAG testing
- `test_camunda_integration.py` - Camunda integration tests
- `test_document_ingestion_pipeline.py` - Document ingestion tests
- `test_user_task_scripts.py` - User task script tests

### Utility Scripts (unused):
- `check_floating_data.py` - Check for floating data
- `cleanup_floating_data.py` - Clean up floating data

## Removal Criteria:
- Scripts not referenced in BPMN workflow files
- Test scripts superseded by `run_comprehensive_tests.py`
- Utility scripts with no references in codebase
- Scripts identified as redundant during analysis

## Recovery:
If any of these scripts are needed:
1. Copy back to `scripts/` folder
2. Ensure any dependencies are available
3. Test functionality before use
4. Update any references if needed

## Deletion Plan:
After testing ODRAS for a period and confirming no issues:
- This entire `cleanup/` folder can be safely deleted
- All changes are preserved in Git history for permanent recovery
- Document history is tracked in `docs/DOCUMENT_HISTORY.md`

---
*Created during repository cleanup - Branch: cleanup/repo-cleanup*
*Commit: [commit hash will be added]*
