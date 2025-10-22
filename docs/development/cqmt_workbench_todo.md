# CQ/MT Workbench Implementation TODO

## Status Overview
**Current Phase**: Phase 1 (Core CRUD) → Phase 2 (Execution Engine)  
**Last Updated**: 2024-10-22  
**Branch**: feature/competency_question_3

## ✅ Completed Items

### Backend API (Phase 1)
- [x] CQ CRUD API endpoints (create, list, get, update, delete)
- [x] MT CRUD API endpoints (create, list, get, update, delete)
- [x] Database schema for CQs and microtheories
- [x] Authentication and authorization
- [x] MT description field support
- [x] MT triples support (view and edit)
- [x] MT cloning via API
- [x] Set default microtheory endpoint
- [x] CQ execution endpoint (`/cqs/{cq_id}/run`)
- [x] CQ run history endpoint
- [x] AI assist endpoints (SPARQL suggestion, ontology deltas)

### Frontend UI (Phase 1)
- [x] CQ list display with status badges
- [x] MT list display with default badges
- [x] CQ create/edit modal
- [x] MT create/edit modal
- [x] Microtheory selector in CQ modal
- [x] Status badges (Draft/Active/Deprecated for CQs, DEFAULT for MTs)
- [x] Form validation and error handling
- [x] Modal close after save
- [x] List refresh after CRUD operations

### Database
- [x] CQs table with all required fields
- [x] Microtheories table with description, updated_by, updated_at
- [x] CQ runs table for execution history
- [x] Foreign key constraints and indexes

---

## 🚧 In Progress

### Bug Fixes
- [ ] Test and verify microtheory update with triples works end-to-end
- [ ] Verify CQ execution actually runs against Fuseki
- [ ] Test contract validation logic

---

## 📋 Phase 1 Remaining: Core CRUD Operations

### Backend
- [ ] Add description field to CQ model if not present
- [ ] Verify SPARQL syntax validation works
- [ ] Add triple count endpoint for microtheories
- [ ] Implement proper error messages for all endpoints

### Frontend  
- [ ] Add MT triple editing via UI (currently only via modal)
- [ ] Add CQ parameter editing via UI
- [ ] Implement search/filter for CQ list
- [ ] Implement search/filter for MT list
- [ ] Add confirmation dialogs for destructive operations
- [ ] Add loading states for async operations
- [ ] Improve error message display

### Testing
- [ ] Run recovered test scripts to verify functionality
- [ ] Fix any failing tests
- [ ] Add end-to-end tests for CRUD workflows

---

## 📋 Phase 2: Execution Engine

### Backend Implementation
- [ ] **CRITICAL**: Verify SPARQL execution actually works
  - [ ] Test against Fuseki with real data
  - [ ] Verify named graph confinement works
  - [ ] Test parameter binding with {{var}} syntax
  - [ ] Handle SPARQL errors gracefully
  
- [ ] **CRITICAL**: Contract validation framework
  - [ ] Verify require_columns validation works
  - [ ] Verify min_rows validation works
  - [ ] Verify max_latency_ms validation works
  - [ ] Add max_rows validation if needed
  - [ ] Return detailed validation failure reasons

- [ ] Coverage calculation service
  - [ ] Calculate CQ pass/fail rates
  - [ ] Track coverage over time
  - [ ] Identify untested ontology areas

### Frontend Implementation  
- [ ] **CRITICAL**: CQ execution interface
  - [ ] Add "Run CQ" button to CQ cards
  - [ ] Create execution modal/panel
  - [ ] Allow MT selection for execution
  - [ ] Allow parameter input
  - [ ] Display execution results (pass/fail, data, latency)
  - [ ] Show validation failure details

- [ ] Execution history viewer
  - [ ] Show last 5 runs per CQ
  - [ ] Display pass/fail status in history
  - [ ] Show parameters used for each run
  - [ ] Link to full run details

- [ ] Coverage dashboard
  - [ ] Show overall pass rate
  - [ ] Show coverage by MT
  - [ ] Show coverage by ontology
  - [ ] Add trend charts

- [ ] Performance monitoring
  - [ ] Display execution times
  - [ ] Show slow queries warning
  - [ ] Add timeout indicators

### Testing
- [ ] SPARQL execution tests with real Fuseki data
- [ ] Contract validation tests (all validation types)
- [ ] Performance benchmarking
- [ ] Error handling tests (invalid SPARQL, etc.)
- [ ] Coverage calculation validation

---

## 📋 Phase 3: Ontology Context Management

### Backend Implementation
- [ ] Ontology selection service (already exists?)
- [ ] Import resolution functionality
- [ ] Context switching logic
- [ ] Namespace management
- [ ] Ontology validation

### Frontend Implementation
- [ ] Ontology selector component (exists in tab)
- [ ] Import viewer
- [ ] Context switching interface
- [ ] Namespace display
- [ ] Ontology validation feedback

### Testing
- [ ] Ontology selection tests
- [ ] Import resolution tests
- [ ] Context switching tests
- [ ] Namespace handling tests

---

## 📋 Phase 4: Advanced Features

### Backend Implementation
- [ ] MT cloning functionality (exists via API)
- [ ] Bulk import/export for CQs
- [ ] Bulk import/export for MTs
- [ ] Advanced search for CQs
- [ ] Advanced search for MTs
- [ ] Scheduled execution (low priority)
- [ ] Performance optimization

### Frontend Implementation
- [ ] MT cloning UI (enhance existing)
- [ ] Bulk operations UI (import/export buttons)
- [ ] Advanced search UI
- [ ] Filter by status, date, etc.
- [ ] Sort options

### Testing
- [ ] Cloning functionality tests
- [ ] Bulk operations tests
- [ ] Search and filter tests

---

## 📋 Phase 5: AI Integration

### Backend Implementation
- [ ] DAS integration for CQ generation (stub exists)
- [ ] LLM-based query optimization
- [ ] AI contract validation
- [ ] Intelligent error analysis
- [ ] Recommendation engine

### Frontend Implementation
- [ ] AI assistant interface
- [ ] CQ generation UI (exists but needs integration)
- [ ] Query optimization suggestions
- [ ] Contract validation feedback
- [ ] Recommendation display

### Testing
- [ ] AI integration tests
- [ ] CQ generation accuracy tests
- [ ] Query optimization tests

---

## 🎯 Immediate Next Steps (Priority Order)

### 1. **CRITICAL**: Test and Fix CQ Execution
   - Run a CQ against real Fuseki data
   - Verify SPARQL execution works
   - Verify results are returned correctly
   - Fix any issues found

### 2. **CRITICAL**: Test and Fix Contract Validation
   - Verify require_columns validation
   - Verify min_rows validation
   - Verify max_latency_ms validation
   - Return detailed failure reasons

### 3. **HIGH**: Implement CQ Execution UI
   - Add "Run CQ" button to CQ cards
   - Create execution modal
   - Display results with pass/fail status
   - Show execution time and data

### 4. **HIGH**: Run Test Suite
   - Execute recovered test scripts
   - Fix any failing tests
   - Ensure all CRUD operations work

### 5. **MEDIUM**: Improve Error Handling
   - Better error messages
   - Loading states
   - Confirmation dialogs
   - Validation feedback

### 6. **MEDIUM**: Coverage Dashboard
   - Calculate and display pass rates
   - Show execution history
   - Add basic charts/visualizations

---

## 🔍 Known Issues

1. **Microtheory Update**: May need testing after adding updated_by column
2. **CQ Execution**: Not verified against real Fuseki data yet
3. **Contract Validation**: Logic exists but needs testing
4. **Triple Editing**: UI exists but needs end-to-end testing
5. **Test Suite**: Need to run recovered tests to identify gaps

---

## 📊 Success Criteria

### Functional Requirements
- [ ] All CRUD operations work correctly for CQs and MTs
- [ ] CQ execution produces accurate results
- [ ] Contract validation works as specified
- [ ] Coverage analysis provides meaningful insights
- [ ] UI is intuitive and responsive

### Performance Requirements
- [ ] CQ execution completes within 30 seconds
- [ ] UI responds within 2 seconds for all operations
- [ ] Coverage calculations complete within 10 seconds
- [ ] System supports 100+ CQs and 20+ MTs per project

### Usability Requirements
- [ ] Intuitive user interface for all operations
- [ ] Clear error messages and guidance
- [ ] Responsive design
- [ ] Good visual feedback (loading states, badges, etc.)

---

## 📝 Notes

- Most backend API endpoints are complete
- Frontend CRUD is functional but needs testing
- Execution engine exists but needs verification
- Coverage analysis is not yet implemented
- AI features have stubs but need integration
- Test suite recovered from deleted branch

---

---

## 📋 SPARQL Query Builder Implementation (NEW)

### Phase 1: Prefix Management (Quick Win)
**Goal**: Eliminate manual prefix typing by auto-injecting project-specific prefixes

#### Backend
- [ ] Create `GET /api/cqmt/projects/{project_id}/prefixes` endpoint
  - [ ] Extract namespace from ontology graph IRI
  - [ ] Return project-specific prefixes
  - [ ] Include standard prefixes (rdf, rdfs, owl)
  - [ ] Return default namespace for project

#### Frontend
- [ ] Add "Insert Prefixes" button to CQ modal
- [ ] Call prefixes API on CQ modal open
- [ ] Auto-inject prefixes into SPARQL editor
- [ ] Show prefix list in tooltip or helper text
- [ ] Update "Suggest SPARQL" to use project prefixes instead of hardcoded

#### Testing
- [ ] Test prefix generation for different projects
- [ ] Verify prefix injection doesn't duplicate existing prefixes
- [ ] Test with projects having multiple ontologies

---

### Phase 2: Test Query Endpoint
**Goal**: Enable SPARQL testing during CQ creation without saving

#### Backend
- [ ] Create `POST /api/cqmt/test-query` endpoint
  - [ ] Accept SPARQL, mt_iri, project_id
  - [ ] Reuse existing CQ execution logic
  - [ ] Execute against Fuseki with microtheory context
  - [ ] Return results without creating CQ run record
  - [ ] Handle SPARQL syntax errors gracefully
  - [ ] Set reasonable timeout (30 seconds)

#### Frontend
- [ ] Add "Test Query" button to CQ modal
- [ ] Create query results display panel
- [ ] Show microtheory selector for testing
- [ ] Display results (columns, rows, execution time)
- [ ] Show error messages for failed queries
- [ ] Add loading state during query execution

#### Testing
- [ ] Test query execution with valid SPARQL
- [ ] Test with invalid SPARQL (syntax errors)
- [ ] Test timeout handling
- [ ] Test against empty microtheory
- [ ] Test against microtheory with data

---

### Phase 3: Query Builder Modal
**Goal**: Interactive SPARQL query building experience

#### Backend
- [ ] Enhance prefix handling for multiple ontologies
- [ ] Add query optimization suggestions (optional)

#### Frontend
- [ ] Create new SPARQL Query Builder modal component
- [ ] Integrate prefix auto-injection
- [ ] Integrate test query functionality
- [ ] Add problem statement input
- [ ] Add toolbar with actions
- [ ] Display test results inline
- [ ] Add "Use This Query" button to insert into CQ
- [ ] Replace current "Suggest SPARQL" button with "Open Query Builder"

#### Testing
- [ ] Test modal workflow end-to-end
- [ ] Test query building and testing
- [ ] Test inserting query into CQ form
- [ ] Test modal with multiple ontologies

---

### Phase 4: DAS Integration
**Goal**: AI-powered SPARQL query generation using actual ontology terms

#### Backend
- [ ] Enhance `/api/cqmt/assist/suggest-sparql` endpoint
  - [ ] Accept project_id and ontology_graph_iri parameters
  - [ ] Load ontology classes/properties using `/api/ontology/` endpoint
  - [ ] Send ontology context to DAS
  - [ ] Generate SPARQL using actual ontology terms
  - [ ] Return query with correct prefixes and IRIs
  - [ ] Add confidence score to response
  - [ ] Return multiple query variations

#### Frontend
- [ ] Add "Suggest with DAS" button to Query Builder
- [ ] Show loading state during DAS processing
- [ ] Display generated query in editor
- [ ] Show confidence score and notes
- [ ] Allow user to select between query variations
- [ ] Add "improve query" option for refinement

#### Testing
- [ ] Test DAS integration with real ontology
- [ ] Verify generated queries use correct IRIs
- [ ] Test with ontologies having no classes
- [ ] Test confidence score accuracy
- [ ] Test query variations generation

---

## 🔗 Related Documents

- [CQMT Workbench Specification](CQMT_WORKBENCH_SPECIFICATION.md)
- [CQMT Workbench Guide](CQMT_WORKBENCH_GUIDE.md)
- [SPARQL Query Builder Plan](CQMT_SPARQL_QUERY_BUILDER_PLAN.md)
- [Test Files](../tests/test_cqmt_workbench.py)
- [API Endpoints](../../backend/api/cqmt.py)
