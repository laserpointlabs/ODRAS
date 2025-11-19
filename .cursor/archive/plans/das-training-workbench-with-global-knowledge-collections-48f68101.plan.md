<!-- 48f68101-8737-42db-a5b8-2d644818b133 d61bde22-00d4-453f-b548-c84e4b59e2fc -->
# RAG and DAS Architecture Improvements Plan

## Core Principles

1. **Decoupling First**: All components communicate through abstract interfaces, never concrete implementations
2. **Test Everything**: Every component must have unit tests, integration tests, and be verified in CI
3. **SQL-First Storage**: All text content stored in SQL, vector stores contain only IDs and metadata
4. **Incremental Migration**: Changes are backward-compatible and can be rolled out gradually

## Phase 1: DAS/RAG Decoupling (Foundation)

### 1.1 Define Structured Context Interface

- **File**: `backend/rag/core/context_models.py` (new)
- Create Pydantic models for RAG context:
- `RAGChunk`: Individual chunk with content, metadata, scores
- `RAGContext`: Collection of chunks with query metadata
- `RAGSource`: Source document information
- Ensure context is LLM-agnostic (no prompt formatting)
- **Testing**: `tests/unit/test_rag_context_models.py` - model validation, serialization, edge cases

### 1.2 Define RAG Service Interface (Abstract Base Class)

- **File**: `backend/rag/core/rag_service_interface.py` (new)
- Create abstract `RAGServiceInterface` with:
- `query_knowledge_base(query: str, context: Dict) -> RAGContext`
- `get_query_suggestions(context: Dict) -> List[str]`
- No LLM calls, no prompt formatting
- **Testing**: `tests/unit/test_rag_service_interface.py` - interface contract validation, mock implementations

### 1.3 Refactor ModularRAGService to Implement Interface

- **File**: `backend/rag/core/modular_rag_service.py`
- Update to implement `RAGServiceInterface`
- Update `query_knowledge_base()` to return `RAGContext` instead of formatted strings
- Keep response generation separate (optional helper method)
- Maintain backward compatibility during transition
- **Testing**: 
- `tests/unit/test_modular_rag_service.py` - mocked vector stores, embedding services
- `tests/integration/test_rag_service_integration.py` - real Qdrant, PostgreSQL, SQL-first verification

### 1.4 Update DAS Core Engine for Dependency Injection

- **File**: `backend/services/das_core_engine.py`
- Accept `RAGServiceInterface` in constructor (not concrete `ModularRAGService`)
- Modify `process_message_stream()` to:
- Call RAG service interface and receive `RAGContext`
- Format context into prompts (DAS controls prompt engineering)
- Handle context prioritization and chunk selection
- Add prompt templates for different query types
- **Testing**:
- `tests/unit/test_das_core_engine.py` - mocked RAG service, verify prompt formatting
- `tests/integration/test_das_rag_integration.py` - end-to-end DAS + RAG flow

### 1.5 Create RAG Context Formatter (Testable Service)

- **File**: `backend/services/das_prompt_builder.py` (new)
- Pure function/service: takes `RAGContext`, returns formatted prompt string
- Support different prompt styles (comprehensive, concise, technical)
- Handle source citations and metadata formatting
- **Testing**: `tests/unit/test_das_prompt_builder.py` - each prompt style, edge cases (empty context, etc.)

## Phase 2: Comprehensive System Indexing

### 2.1 Design Unified Index Schema

- **File**: `backend/odras_schema.sql`
- Create `system_index` table:
- `index_id`, `entity_type` (file, event, ontology, requirement, etc.)
- `entity_id`, `entity_uri`, `content_summary`
- `metadata` (JSONB), `tags` (array), `domain`
- `indexed_at`, `updated_at`
- Create `system_index_vectors` table (SQL-first pattern)
- **Testing**: `tests/integration/test_index_schema.py` - schema migration, constraints, indexes

### 2.2 Create Indexing Service Interface

- **File**: `backend/services/indexing_service_interface.py` (new)
- Abstract interface for indexing operations
- Methods: `index_entity()`, `update_index()`, `delete_index()`, `get_indexed_entities()`
- **Testing**: `tests/unit/test_indexing_interface.py` - interface contract, mock implementations

### 2.3 Create Indexing Service Implementation

- **File**: `backend/services/system_indexer.py` (new)
- Implement `IndexingServiceInterface`
- Index all system entities:
- Files (from MinIO + files table)
- Events (from project_threads events)
- Ontologies (from Fuseki)
- Requirements (from requirements tables)
- Conversations (from project_threads)
- Extract summaries and metadata automatically
- **Testing**:
- `tests/unit/test_system_indexer.py` - each entity type with mocked sources
- `tests/integration/test_indexing_integration.py` - real databases, verify SQL-first storage

### 2.4 Integrate Indexing into RAG (Decoupled)

- **File**: `backend/rag/core/modular_rag_service.py`
- Accept `IndexingServiceInterface` as optional dependency
- Query system index alongside knowledge chunks when available
- Tag system index entries with `source_type: "system"`
- **Testing**:
- `tests/unit/test_rag_indexing.py` - mocked indexer, verify integration logic
- `tests/integration/test_rag_with_indexing.py` - real indexer, verify retrieval

### 2.5 Event-Driven Indexing Worker

- **File**: `backend/services/indexing_worker.py` (new)
- Listen to system events (file uploads, ontology changes, etc.)
- Automatically index new/updated entities
- Update vector embeddings when content changes
- **Testing**:
- `tests/unit/test_indexing_worker.py` - mocked event sources, verify processing
- `tests/integration/test_indexing_worker_events.py` - real events, verify indexing

## Phase 3: Unified Knowledge Collection Migration

### 3.1 Design Unified Collection Schema

- **File**: `backend/odras_schema.sql`
- Create `das_knowledge_chunks` table (SQL-first):
- `chunk_id`, `content` (source of truth)
- `knowledge_type` (project, training, system)
- `domain` (ontology, requirements, acquisition, etc.)
- `project_id` (nullable for global knowledge)
- `tags` (array), `metadata` (JSONB)
- `embedding_model`, `qdrant_point_id`
- **Testing**: `tests/integration/test_unified_schema.py` - schema, constraints, indexes, performance

### 3.2 Create Unified Collection in Qdrant

- **File**: `odras.sh` (init_databases function)
- Create `das_knowledge` collection (384-dim, supports 1536 via separate field)
- Update `backend/services/qdrant_service.py` to support unified collection
- **Testing**: `tests/integration/test_qdrant_unified_collection.py` - creation, metadata filtering

### 3.3 Migration Script (Testable)

- **File**: `scripts/migrate_to_unified_collection.py` (new)
- Migrate existing collections:
- `knowledge_chunks` → `das_knowledge` (tag: `knowledge_type=project`)
- `das_training_*` → `das_knowledge` (tag: `knowledge_type=training`)
- Preserve all metadata as tags/metadata fields
- Verify data integrity after migration
- **Testing**:
- `tests/unit/test_migration_logic.py` - migration logic with test data
- `tests/integration/test_migration_integration.py` - real collections, verify integrity
- `tests/integration/test_migration_rollback.py` - rollback capability

### 3.4 Update RAG Service for Unified Collection (Decoupled)

- **File**: `backend/rag/core/modular_rag_service.py`
- Replace multi-collection queries with single collection + metadata filters
- Update `_retrieve_relevant_chunks()` to use unified collection
- Filter by `knowledge_type`, `domain`, `project_id` via metadata
- **Testing**:
- `tests/unit/test_rag_unified_collection.py` - mocked vector store, verify filtering
- `tests/integration/test_rag_unified_integration.py` - real Qdrant, verify performance
- `tests/performance/test_rag_query_performance.py` - benchmark query times

### 3.5 Update Training Data Processor

- **File**: `backend/services/das_training_processor.py`
- Store new training data in unified `das_knowledge` collection
- Tag with `knowledge_type=training` and appropriate `domain`
- **Testing**: 
- `tests/unit/test_training_processor_unified.py` - tagging logic
- `tests/integration/test_training_unified_integration.py` - end-to-end processing

## Phase 4: Proactive Workers and Monitoring

### 4.1 Define Worker Interface

- **File**: `backend/services/worker_interface.py` (new)
- Abstract base class for all workers
- Methods: `process_event()`, `run_scheduled()`, `get_status()`
- **Testing**: `tests/unit/test_worker_interface.py` - interface contract, mock implementations

### 4.2 Event-Driven Worker Framework

- **File**: `backend/services/proactive_workers.py` (new)
- Worker base class implementing `WorkerInterface`
- Event subscription mechanism (decoupled from event source)
- Worker registry and lifecycle management
- **Testing**:
- `tests/unit/test_worker_framework.py` - mocked event sources, verify lifecycle
- `tests/integration/test_worker_framework_events.py` - real events, verify processing

### 4.3 Knowledge Review Worker

- **File**: `backend/workers/knowledge_review_worker.py` (new)
- Implement `WorkerInterface`
- Periodically review knowledge by domain
- Identify unused/low-quality chunks
- Suggest knowledge improvements to admins
- **Testing**:
- `tests/unit/test_knowledge_review_worker.py` - mocked data, verify analysis logic
- `tests/integration/test_knowledge_review_integration.py` - real knowledge base

### 4.4 User Activity Monitor

- **File**: `backend/workers/user_activity_worker.py` (new)
- Implement `WorkerInterface`
- Monitor user work patterns
- Detect when users struggle (repeated queries, long sessions)
- Proactively suggest help or knowledge
- **Testing**:
- `tests/unit/test_user_activity_worker.py` - mocked activity data
- `tests/integration/test_user_activity_integration.py` - real user events

### 4.5 Scheduled Task System (Decoupled)

- **File**: `backend/services/task_scheduler.py` (new)
- Abstract scheduler interface
- Schedule periodic tasks (daily knowledge review, weekly analysis)
- Use Celery or similar for distributed task execution
- Integrate with existing worker infrastructure
- **Testing**:
- `tests/unit/test_task_scheduler.py` - mocked scheduler, verify scheduling logic
- `tests/integration/test_task_scheduler_integration.py` - real scheduling, verify execution

## Phase 5: DAS Runtime Code Generation

### 5.1 Define Code Generation Interface

- **File**: `backend/services/code_generator_interface.py` (new)
- Abstract interface for code generation
- Methods: `generate_code()`, `validate_code()`, `get_supported_capabilities()`
- **Testing**: `tests/unit/test_code_generator_interface.py` - interface contract, mocks

### 5.2 Code Generation Service

- **File**: `backend/services/das_code_generator.py` (new)
- Implement `CodeGeneratorInterface`
- Generate Python code for:
- Data fetching (from APIs, databases)
- Calculations and transformations
- Knowledge creation workflows
- Use LLM to generate code based on user intent
- **Testing**:
- `tests/unit/test_code_generator.py` - mocked LLM, verify code generation scenarios
- `tests/integration/test_code_generator_integration.py` - real LLM, verify code quality

### 5.3 Define Code Execution Interface

- **File**: `backend/services/code_executor_interface.py` (new)
- Abstract interface for code execution
- Methods: `execute()`, `validate_safety()`, `get_execution_status()`
- **Testing**: `tests/unit/test_code_executor_interface.py` - interface contract, mocks

### 5.4 Sandboxed Execution Environment

- **File**: `backend/services/code_executor.py` (new)
- Implement `CodeExecutorInterface`
- Execute generated code in isolated environment
- Security: restricted imports, resource limits, timeout
- Capture output and errors safely
- **Testing**:
- `tests/unit/test_code_executor.py` - security restrictions, resource limits
- `tests/integration/test_code_executor_integration.py` - real code execution
- `tests/security/test_code_executor_security.py` - penetration tests, access control

### 5.5 Tool Registry Interface

- **File**: `backend/services/tool_registry_interface.py` (new)
- Abstract interface for tool storage
- Methods: `store_tool()`, `find_tool()`, `update_usage()`
- **Testing**: `tests/unit/test_tool_registry_interface.py` - interface contract, mocks

### 5.6 Tool Registry Implementation

- **File**: `backend/services/das_tool_registry.py` (new)
- Implement `ToolRegistryInterface`
- Store successful generated tools
- Metadata: purpose, inputs, outputs, usage_count
- Allow DAS to reuse tools instead of regenerating
- **Testing**:
- `tests/unit/test_tool_registry.py` - CRUD operations
- `tests/integration/test_tool_registry_integration.py` - real storage, verify retrieval

### 5.7 Integration with DAS (Decoupled)

- **File**: `backend/services/das_core_engine.py`
- Accept `CodeGeneratorInterface` and `CodeExecutorInterface` as dependencies
- Detect when user needs code generation
- Generate or retrieve tool from registry
- Execute and return results
- **Testing**:
- `tests/unit/test_das_code_generation.py` - mocked generators/executors
- `tests/integration/test_das_code_generation_integration.py` - end-to-end flow

## Phase 6: DAS Team Personas and MCP Integration

### 6.1 Define Persona Interface

- **File**: `backend/services/persona_interface.py` (new)
- Abstract interface for personas
- Methods: `process_task()`, `get_capabilities()`, `get_role()`
- **Testing**: `tests/unit/test_persona_interface.py` - interface contract, mock personas

### 6.2 Persona System Implementation

- **File**: `backend/services/das_personas.py` (new)
- Implement `PersonaInterface` for each role:
- Researcher (finds information)
- Analyst (analyzes data)
- Writer (creates content)
- Moderator (coordinates team)
- Each persona has specialized prompts and capabilities
- **Testing**:
- `tests/unit/test_das_personas.py` - each persona, verify role-specific behavior
- `tests/integration/test_personas_integration.py` - real LLM, verify persona responses

### 6.3 Team Orchestration Interface

- **File**: `backend/services/team_orchestrator_interface.py` (new)
- Abstract interface for team coordination
- Methods: `coordinate_task()`, `add_persona()`, `get_team_status()`
- **Testing**: `tests/unit/test_team_orchestrator_interface.py` - interface contract, mocks

### 6.4 Team Orchestration Implementation

- **File**: `backend/services/das_team_orchestrator.py` (new)
- Implement `TeamOrchestratorInterface`
- Coordinate multiple personas
- Moderator assigns tasks to appropriate personas
- Combine persona outputs into final response
- **Testing**:
- `tests/unit/test_team_orchestrator.py` - mocked personas, verify coordination
- `tests/integration/test_team_orchestrator_integration.py` - real personas, verify output

### 6.5 MCP Client Interface

- **File**: `backend/services/mcp_client_interface.py` (new)
- Abstract interface for MCP operations
- Methods: `discover_servers()`, `call_tool()`, `get_capabilities()`
- **Testing**: `tests/unit/test_mcp_client_interface.py` - interface contract, mocks

### 6.6 MCP Integration Implementation

- **File**: `backend/services/das_mcp_client.py` (new)
- Implement `MCPClientInterface`
- Discover available MCP servers
- Allow DAS to call MCP tools when needed
- Cache MCP server capabilities
- **Testing**:
- `tests/unit/test_mcp_client.py` - mocked MCP servers, verify tool calls
- `tests/integration/test_mcp_client_integration.py` - real MCP servers, verify discovery

### 6.7 Learning Interface

- **File**: `backend/services/learning_interface.py` (new)
- Abstract interface for learning system
- Methods: `record_interaction()`, `learn_from_feedback()`, `get_improvements()`
- **Testing**: `tests/unit/test_learning_interface.py` - interface contract, mocks

### 6.8 Learning from Interactions Implementation

- **File**: `backend/services/das_learning.py` (new)
- Implement `LearningInterface`
- Store successful interactions
- Learn from user corrections
- Improve persona behavior over time
- **Testing**:
- `tests/unit/test_das_learning.py` - learning logic, feedback processing
- `tests/integration/test_das_learning_integration.py` - real interactions, verify improvements

## CI Testing Integration

### Test Organization

- **Unit Tests**: `tests/unit/test_*.py` - Fast, isolated, mocked dependencies
- **Integration Tests**: `tests/integration/test_*.py` - Real services, slower
- **Performance Tests**: `tests/performance/test_*.py` - Benchmarks, timeouts
- **Security Tests**: `tests/security/test_*.py` - Code execution, access control

### CI Workflow Updates

- **File**: `.github/workflows/ci.yml`
- Add test execution stages:

1. Unit tests (parallel execution, fast feedback)
2. Integration tests (sequential, require full stack)
3. Performance tests (benchmark critical paths)
4. Security tests (code execution sandbox validation)

- All tests must pass before merge
- Test coverage reporting (aim for >80% coverage)

### Test Execution Order

1. **Unit Tests** (fastest, no dependencies)

- All interface contracts
- All service logic with mocks
- All model validation

2. **Integration Tests** (require services)

- RAG → DAS flow
- Indexing → RAG flow
- Code generation → execution flow
- Worker event processing

3. **Performance Tests** (benchmark)

- RAG query latency
- Collection migration performance
- Code execution timeouts

4. **Security Tests** (validation)

- Code execution sandbox
- Access control for knowledge
- Input validation

### Test Data Management

- **Fixtures**: `tests/fixtures/` - Reusable test data
- **Mocks**: `tests/mocks/` - Mock implementations of interfaces
- **Test Databases**: Created/destroyed per test run
- **Isolation**: Each test is independent, no shared state

## Success Criteria

1. **Decoupling**: All components communicate through interfaces, zero direct dependencies on concrete implementations
2. **Test Coverage**: >80% code coverage for all new code
3. **CI Integration**: All tests run in CI, must pass before merge
4. **Backward Compatibility**: Existing functionality continues to work during migration
5. **Performance**: No regression in query times, indexing performance acceptable
6. **Security**: Code execution sandbox prevents unauthorized access

## Migration Strategy

- **Incremental**: Each phase can be deployed independently
- **Feature Flags**: Use environment variables to enable/disable new features
- **Rollback**: Each migration includes rollback capability
- **Monitoring**: Track performance and errors during migration

### To-dos

- [ ] Complete RAG refactoring - integrate ModularRAGService into startup
- [ ] Update DAS to use ModularRAGService
- [ ] Update all RAGService references to use ModularRAGService
- [ ] Test RAG integration and verify functionality