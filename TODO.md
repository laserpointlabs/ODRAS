# ODRAS Development TODO

## 🚨 Critical Issues

### 1. IRI/URI Standardization (Major Refactor)
**Status**: 🔴 Not Started
**Priority**: High
**Branch**: `feature/iri-standardization` (needs dedicated branch)

**Description**: Standardize terminology and implementation to use IRI consistently throughout the codebase.

**Tasks**:
- [ ] Create dedicated branch for IRI standardization
- [ ] Rename `ResourceURIService` → `ResourceIRIService`
- [ ] Update all API responses to use "iri" instead of "uri"
- [ ] Standardize frontend variable names and UI labels
- [ ] Update database column names where appropriate
- [ ] Update documentation and comments
- [ ] Comprehensive testing of IRI generation
- [ ] Migration plan for existing data

**Impact**: Major refactor affecting multiple services, APIs, and frontend components.

---

## 🐛 Bug Fixes

### 2. Project URI Display Fix
**Status**: ✅ Completed
**Priority**: High
**Date**: 2024-12-19

**Description**: Fixed project information page to show complete URI with installation base URI.

**Changes Made**:
- Updated `frontend/app.html` to use `INSTALLATION_CONFIG.baseUri` in project URI construction
- Now displays: `https://xma-adt.usnc.mil/odras/core/{project-id}/`
- Instead of: `http://odras/core/{project-id}/`

### 3. Duplicate "odras" in IRI Generation
**Status**: ✅ Completed
**Priority**: High
**Date**: 2024-12-19

**Description**: Fixed hardcoded duplicate "odras" in ResourceURIService URI generation.

**Changes Made**:
- Removed hardcoded `/odras/` from `ResourceURIService` methods
- Updated database records to remove duplicate "odras"
- Fixed IRI display to show "No element selected" when ontology is deleted

---

## 🔧 Technical Debt

### 4. Frontend IRI Display Cleanup
**Status**: ✅ Completed
**Priority**: Medium
**Date**: 2024-12-19

**Description**: Fixed IRI display to properly clear when ontology is deleted.

**Changes Made**:
- Updated `updateElementIriDisplay()` to check for active ontology
- Shows "No element selected" when no ontology is active
- Hides copy button when no element is selected

### 5. Database Migration Cleanup
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Clean up temporary database fix script and ensure all migrations are properly documented.

**Tasks**:
- [ ] Remove temporary `fix_duplicate_odras_iris.py` script (already deleted)
- [ ] Document the database fix in migration history
- [ ] Ensure all URI generation uses centralized service

### 6. Connection Pool Management
**Status**: 🔴 Not Started
**Priority**: High

**Description**: Improve connection pool management to prevent pool exhaustion, particularly during Playwright testing sessions.

**Tasks**:
- [ ] Investigate current connection pool configuration
- [ ] Implement proper connection cleanup in test teardown
- [ ] Add connection pool monitoring and alerts
- [ ] Optimize connection pool size for testing workloads
- [ ] Add connection pool health checks
- [ ] Implement connection timeout handling
- [ ] Add connection pool metrics and logging

---

## 🚀 Feature Improvements

### 7. Ontology Question Tool
**Status**: 🔴 Not Started
**Priority**: High
**Documentation**: `docs/features/ONTOLOGY_QUESTION_DRIVEN_DEVELOPMENT.md`

**Description**: Create a question tool for the ontology workbench to help with ontological development and validation. This implements Question-Driven Ontology Development (OQDD) methodology.

**Implementation Phases** (16 weeks):

**Phase 1: Foundation (Weeks 1-2)**
- [ ] Create database schema for questions, concepts, mappings, validation
- [ ] Implement basic CRUD API endpoints for questions
- [ ] Create question listing with filtering/sorting
- [ ] Add question templates endpoint
- [ ] Set up Qdrant collection for question embeddings

**Phase 2: NLP Integration (Weeks 3-4)**
- [ ] Implement QuestionProcessor with spaCy and SentenceTransformer
- [ ] Build concept extraction pipeline
- [ ] Create question embedding generation
- [ ] Implement intent classification (purpose, input, output, structure, validation, constraint)
- [ ] Store embeddings in Qdrant with metadata

**Phase 3: DAS Training (Weeks 5-6)**
- [ ] Create DASQuestionTrainer service
- [ ] Implement knowledge extraction from questions
- [ ] Build pattern recognition system
- [ ] Integrate with DAS knowledge base
- [ ] Create training pipeline for new questions

**Phase 4: Ontology Generation (Weeks 7-9)**
- [ ] Implement OntologyGenerationService
- [ ] Build question-to-OWL element mapping
- [ ] Create conflict resolution system
- [ ] Apply OWL best practices optimization
- [ ] Integrate with Fuseki for ontology creation
- [ ] Add explanation generation for created elements

**Phase 5: Validation System (Weeks 10-11)**
- [ ] Create QuestionValidationService
- [ ] Implement question coverage checking
- [ ] Build gap analysis system
- [ ] Add metrics calculation (overall coverage, by category)
- [ ] Create recommendation engine
- [ ] Generate validation reports

**Phase 6: UI Development (Weeks 12-14)**
- [ ] Create Question Manager table view with filtering
- [ ] Build question creation/edit forms
- [ ] Add question detail view with concept visualization
- [ ] Create validation dashboard with charts
- [ ] Build DAS assistance panel
- [ ] Add gap analysis visualization
- [ ] Implement question templates UI

**Phase 7: Testing & Refinement (Weeks 15-16)**
- [ ] Unit tests for NLP pipeline
- [ ] Integration tests for DAS training
- [ ] End-to-end tests for generation workflow
- [ ] Performance tests for large question sets
- [ ] User acceptance testing
- [ ] Documentation and training materials

**Key Features**:
- **Question Categories**: Purpose, Inputs, Outputs, Structure, Validation, Constraints
- **Metadata Fields**: Question text, category, priority, status, tags, created date, last modified
- **NLP Processing**: Automatic concept extraction, intent classification, embedding generation
- **DAS Integration**: 3-phase training (embedding, pattern recognition, element association)
- **Ontology Generation**: Automated creation of OWL elements from questions
- **Validation Workflow**: Real-time coverage analysis and gap identification
- **Templates**: Pre-built question sets for common ontology types
- **Analytics**: Track question completion and ontology development progress
- **Traceability**: Bidirectional links between questions and ontology elements

**Expected Outcomes**:
- 70% reduction in ontology development time
- 90%+ coverage of domain requirements
- Reduced defects through automated validation
- Better collaboration between technical and domain experts
- Living documentation through question-answer pairs

**API Endpoints**:
```
POST   /api/v1/projects/{project_id}/ontologies/{ontology_id}/questions
GET    /api/v1/projects/{project_id}/ontologies/{ontology_id}/questions
GET    /api/v1/projects/{project_id}/ontologies/{ontology_id}/questions/{question_id}
PUT    /api/v1/projects/{project_id}/ontologies/{ontology_id}/questions/{question_id}
DELETE /api/v1/projects/{project_id}/ontologies/{ontology_id}/questions/{question_id}
POST   /api/v1/questions/{question_id}/analyze
POST   /api/v1/das/train-questions
POST   /api/v1/das/generate-ontology
POST   /api/v1/das/validate-ontology
GET    /api/v1/das/validation-report
GET    /api/v1/question-templates
```

**Database Tables**:
- `ontology_questions`: Core question data
- `question_concepts`: Extracted concepts from NLP
- `question_element_mapping`: Links between questions and ontology elements
- `question_validation`: Validation results

**Impact**: Transforms ontology development from ad-hoc process into structured, validated, AI-assisted workflow. Significantly improves quality, completeness, and development speed.

### 8. Project Access Permissions
**Status**: 🔴 Not Started
**Priority**: Medium

**Description**: Fix project access issues where users can't see projects they should have access to.

**Tasks**:
- [ ] Investigate project membership validation
- [ ] Fix project dropdown population
- [ ] Ensure proper project selection workflow
- [ ] Test with different user roles

### 9. Installation Configuration Management
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Improve installation configuration loading and validation.

**Tasks**:
- [ ] Add configuration validation on startup
- [ ] Improve error handling for missing configuration
- [ ] Add configuration health checks
- [ ] Document configuration requirements

---

## 📋 Code Quality

### 10. Frontend Code Organization
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Improve frontend code organization and reduce duplication.

**Tasks**:
- [ ] Extract common IRI handling functions
- [ ] Consolidate duplicate code patterns
- [ ] Improve error handling consistency
- [ ] Add JSDoc comments for complex functions

### 11. Backend Service Consistency
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Ensure consistent patterns across backend services.

**Tasks**:
- [ ] Standardize error handling across services
- [ ] Improve logging consistency
- [ ] Add service health checks
- [ ] Document service interfaces

---

## 🧪 Testing

### 12. IRI Generation Testing
**Status**: 🔴 Not Started
**Priority**: High

**Description**: Comprehensive testing of IRI generation across all services.

**Tasks**:
- [ ] Unit tests for ResourceURIService
- [ ] Integration tests for IRI generation
- [ ] Frontend tests for IRI display
- [ ] End-to-end tests for complete IRI workflow

---

## 📚 Documentation

### 13. IRI Standards Documentation
**Status**: 🔴 Not Started
**Priority**: Medium

**Description**: Document IRI standards and usage patterns for the project.

**Tasks**:
- [ ] Create IRI standards guide
- [ ] Document URI vs IRI usage decisions
- [ ] Add examples of proper IRI construction
- [ ] Update API documentation

---

## 🎯 Next Actions

1. **Immediate**: Test the completed fixes (project URI display, IRI cleanup)
2. **Short-term**: Create branch for IRI standardization planning
3. **Medium-term**: Address project access permissions
4. **High Priority**: Design and implement Ontology Question Tool
5. **Long-term**: Implement comprehensive IRI standardization

---

## 📝 Notes

- All completed items are marked with ✅ and include completion date
- High priority items should be addressed first
- IRI standardization is a major refactor that needs careful planning
- Consider breaking large tasks into smaller, manageable chunks
- Always test changes thoroughly before marking as complete
- **Ontology Question Tool**: See comprehensive architecture document at `docs/features/ONTOLOGY_QUESTION_DRIVEN_DEVELOPMENT.md` for full implementation details, benefits analysis, and system design

---

*Last Updated: 2025-10-04*
