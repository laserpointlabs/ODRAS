# Document History & Cleanup Log

This document tracks all documentation changes, consolidations, and deletions to maintain historical record.

## Major Documentation Consolidation - November 2025

**Branch:** `cleanup/documentation-consolidation`  
**Date:** November 2025  
**Total Documents Before:** 199 markdown files  
**Total Documents After:** ~35 consolidated guides  
**Reduction:** 82% reduction (164 files consolidated/archived)

### Consolidation Strategy

This major cleanup consolidated 199 markdown files into ~35 comprehensive guides, dramatically reducing documentation sprawl and improving Cursor context management.

#### Phase 1: Root Directory Cleanup ✅

**Files Moved from Root:**
- `TEST_COVERAGE_REVIEW.md` → `docs/testing/TEST_COVERAGE_REVIEW.md`
- `TEST_RESULTS_SUMMARY.md` → `docs/testing/TEST_RESULTS_SUMMARY.md`
- `BRANCH_CLEANUP_CHECKLIST.md` → `docs/development/BRANCH_CLEANUP_CHECKLIST.md`
- `BRANCH_REVIEW_competency_questions.md` → `docs/development/BRANCH_REVIEW_competency_questions.md`
- `MVP_VENDOR_EVALUATION_PLAN.md` → `docs/development/MVP_VENDOR_EVALUATION_PLAN.md`
- `CQMT_API_CHEATSHEET.md` → `docs/development/CQMT_API_CHEATSHEET.md`
- `ISSUES_SUMMARY.md` → `docs/development/ISSUES_SUMMARY.md`
- `TODO.md` → `docs/development/TODO.md`

**Test Files Moved:**
- `setup_test_knowledge_data.py` → `scripts/setup_test_knowledge_data.py`
- `test_cqmt_dependencies.sh` → `scripts/test_cqmt_dependencies.sh`
- `test_env_config.txt` → `tests/test_env_config.txt`
- `conftest.py` → Removed (duplicate of `tests/conftest.py`)
- `.pre-commit-config.yaml` → `.config/.pre-commit-config.yaml`

**Result:** Root directory now contains only essential system files (README.md, requirements.txt, docker-compose.yml, odras.sh, install.sh, pytest.ini, etc.)

#### Phase 2: RAG Architecture Consolidation ✅

**Consolidated into:** `docs/architecture/RAG_ARCHITECTURE.md`

**Merged 8 documents:**
- `HYBRID_RAG_ARCHITECTURE.md`
- `HYBRID_RAG_IMPLEMENTATION_PAPER.md`
- `rag_analysis_report.md`
- `rag_improved.md`
- `rag_plus_implementation.md`
- `RAG_plus_study1.md`
- `rag_query_implementation.md`
- `CURRENT_STATUS.md`

**Archived to:** `docs/archive/rag-architecture/`

**New Consolidated Guide Includes:**
- Architecture overview and components
- Data flow and storage patterns
- Ingestion and query pipelines
- BPMN workflow implementation
- Current status and roadmap
- Best practices and recommendations
- Implementation details
- Troubleshooting guide

#### Phase 3: CQMT Documentation Consolidation ✅

**Consolidated into:**
- `docs/development/CQMT_GUIDE.md` (Main implementation guide)
- `docs/development/CQMT_TESTING_GUIDE.md` (Testing documentation)

**Merged 31+ documents:**
- All CQMT phase completion summaries
- Implementation roadmaps
- Architectural assessments
- API testing examples
- Manual testing guides
- Coverage analysis plans
- Versioning strategy discussions

**Archived to:** `docs/archive/cqmt/`

**New Consolidated Guides Include:**
- Architecture overview
- Core concepts (CQs, MTs, TDOD)
- Implementation phases
- API reference
- Synchronization and dependency management
- Versioning strategy
- Usage guide
- Testing procedures

#### Phase 4: CURRENT_STATUS Files Consolidation ✅

**Consolidated into:**
- `docs/workbenches/WORKBENCH_STATUS.md` (All workbench status)
- `docs/architecture/ARCHITECTURE_STATUS.md` (All architecture status)

**Consolidated 19 CURRENT_STATUS.md files:**
- 13 workbench status files → `WORKBENCH_STATUS.md`
- 5 architecture status files → `ARCHITECTURE_STATUS.md`
- 1 RAG status file (already archived)

**Archived to:** `docs/archive/status-files/`

**New Consolidated Status Documents Include:**
- Overview of all workbenches/architectures
- Implementation status for each component
- Completed, in-progress, and pending features
- Testing status
- Next priorities
- Cross-component dependencies

#### Phase 5: CI/CD Testing Consolidation ✅

**Consolidated into:** `docs/development/CI_CD_GUIDE.md`

**Merged 7 documents:**
- `CI_TESTING_STRATEGY.md`
- `CI_SMOKE_TEST_ANALYSIS.md`
- `CI_SMOKE_TEST_FIX_COMPLETE.md`
- `CI_SMOKE_TEST_FIX_PROPOSAL.md`
- `CI_CD_TESTING_GUIDE.md`
- `BOTH_SMOKE_TESTS_FIXED.md`
- `SMOKE_TEST_CLARIFICATION.md`

**Archived to:** `docs/archive/ci-cd/`

**New Consolidated Guide Includes:**
- Quick start guide
- Tiered testing strategy (unit/integration/full)
- Test structure overview
- Smoke test procedures
- GitHub Actions workflows
- Testing best practices
- Troubleshooting

#### Phase 6: Local LLM and Individuals Consolidation ✅

**Consolidated into:**
- `docs/development/LOCAL_LLM_GUIDE.md`
- `docs/development/INDIVIDUALS_GUIDE.md`

**Merged 7 documents:**
- `LOCAL_LLM_SETUP.md`
- `LOCAL_LLM_QUICKREF.md`
- `OLLAMA_GPU_SETUP_GUIDE.md`
- `INDIVIDUALS_SUMMARY.md`
- `INDIVIDUALS_CREATION_PLAN.md`
- `INDIVIDUALS_CREATION_DESIGN_DISCUSSION.md`
- `INDIVIDUALS_ARCHITECTURE_ANALYSIS.md`

**Archived to:** `docs/archive/local-llm/` and `docs/archive/individuals/`

**New Consolidated Guides Include:**
- Model recommendations and selection
- Setup and configuration
- GPU setup instructions
- Quick reference
- Architecture analysis
- Design decisions
- Implementation plans

### Archive Organization

**New Archive Structure:**
- `docs/archive/rag-architecture/` - Historical RAG docs (8 files)
- `docs/archive/cqmt/` - Historical CQMT docs (31+ files)
- `docs/archive/status-files/` - Individual status files (19 files)
- `docs/archive/ci-cd/` - Historical CI/CD docs (7 files)
- `docs/archive/local-llm/` - Historical LLM setup docs (3 files)
- `docs/archive/individuals/` - Historical individuals docs (4 files)
- `docs/archive/historical/` - Other historical docs

### Key Benefits

**Improved Cursor Context:**
- Reduced from 199 to ~35 files (82% reduction)
- Cleaner root directory (only essential files)
- Better organized documentation structure
- Easier to find relevant information

**Better Documentation:**
- Comprehensive guides instead of fragmented docs
- Clear consolidation of related topics
- Historical docs preserved in archive
- Easier maintenance and updates

**Maintained History:**
- All original documents preserved in archive
- Document history tracked in this file
- Git history maintains full record
- Easy to reference original documents if needed

### Files Preserved

**Core Documentation (Kept Active):**
- `README.md` - Main project documentation
- `docs/WORKBENCH_OVERVIEW.md` - Workbench overview
- `docs/DOCUMENT_HISTORY.md` - This file
- All consolidated guides (RAG_ARCHITECTURE.md, CQMT_GUIDE.md, etc.)
- All workbench and architecture guides

**Essential Guides:**
- Architecture guides in `docs/architecture/`
- Development guides in `docs/development/`
- Workbench guides in `docs/workbenches/`
- Deployment guides in `docs/deployment/`
- Testing guides in `docs/testing/`

### Verification

**File Count:**
- Before: 199 markdown files
- After: ~35 consolidated guides
- Reduction: 164 files (82%)

**Root Directory:**
- Before: 8+ markdown files
- After: 1 markdown file (README.md)
- Status: ✅ Clean

**Archive:**
- All historical docs preserved
- Organized by topic
- Easy to reference if needed

---

## New Documentation - January 4, 2025

### Publishing and Domain Architecture
**Created:** `docs/architecture/PUBLISHING_ARCHITECTURE.md`
**Purpose:** Comprehensive publishing mechanism for project artifacts and network collaboration
**Size:** 500+ lines
**Status:** Active - Core publishing system design

**Created:** `docs/architecture/DOMAIN_DRIVEN_ARCHITECTURE.md`
**Purpose:** Domain-driven design framework for ODRAS business logic organization
**Size:** 400+ lines
**Status:** Active - Domain architecture foundation

**Created:** `docs/workbenches/publishing-workbench/CURRENT_STATUS.md`
**Purpose:** Publishing workbench implementation status and roadmap
**Size:** 200+ lines
**Status:** Active - Publishing workbench development

**Updated:** `docs/WORKBENCH_OVERVIEW.md`
**Changes:** Added Publishing workbench, updated workbench count to 14
**Status:** Active - Updated workbench overview

**Updated:** `docs/architecture/event-architecture/CURRENT_STATUS.md`
**Changes:** Added publishing events, subscription events, network events
**Status:** Active - Enhanced event architecture

## New Documentation - October 12, 2025

### Workbench and Architecture Organization
**Created:** `docs/WORKBENCH_OVERVIEW.md`
**Purpose:** Comprehensive overview of reorganized workbench and architecture documentation
**Branch:** `cursor/organize-odras-documentation-folders-d83a`
**Size:** 200+ lines
**Status:** Active - Primary reference for workbench organization

**New Structure Created:**
- `docs/workbenches/` - Individual workbench documentation
  - `cqmt-workbench/` - Conceptual Query Management Tool
  - `ontology-workbench/` - Ontology management and editing
  - `requirements-workbench/` - Requirements analysis and management
  - `das-workbench/` - Distributed Autonomous System management
  - `knowledge-management-workbench/` - Knowledge management and retrieval
  - `conceptualizer-workbench/` - AI-powered system conceptualization
  - `configurator-workbench/` - Manual configuration capabilities
  - `tabularizer-workbench/` - Transform individuals into structured tables
  - `thread-manager-workbench/` - DAS conversation thread management
  - `event-management-workbench/` - Event flow management and monitoring
  - `data-management-workbench/` - Central data orchestration and integration
  - `pubsub-workbench/` - Publish/subscribe messaging management
  - `process-workbench/` - BPMN process management and execution
- `docs/architecture/` - Architecture component documentation
  - `core-architecture/` - Fundamental system structure
  - `database-architecture/` - Data storage and management
  - `rag-architecture/` - Retrieval-Augmented Generation
  - `event-architecture/` - Event-driven communication
  - `integration-architecture/` - External system integration
  - `REFACTOR_ARCHITECTURE.md` - Critical refactoring strategy
  - `PLUGGABLE_ARCHITECTURE.md` - Plugin-based architecture design

**Key Benefits:**
- Clear separation of workbench and architecture concerns
- Status tracking with `CURRENT_STATUS.md` files for each component
- Priority management with defined next steps
- Dependency mapping between components
- Testing status visibility

**Files Moved:**
- CQMT documentation → `workbenches/cqmt-workbench/`
- Ontology documentation → `workbenches/ontology-workbench/`
- DAS documentation → `workbenches/das-workbench/`
- Thread Manager documentation → `workbenches/thread-manager-workbench/`
- RAG documentation → `architecture/rag-architecture/`
- Database documentation → `architecture/database-architecture/`

**Status Documents Created:**
- Each workbench and architecture component now has a `CURRENT_STATUS.md` file
- Tracks implementation status, completed features, in-progress work, and pending features
- Includes technical debt, next priorities, dependencies, and testing status
- Provides clear visibility into what needs to be completed
- **Total Workbenches**: 9 (5 core + 4 specialized)
- **Total Architecture Components**: 5

## New Documentation - October 12, 2025

### Ontology Imports Persistence Issues - Lessons Learned
**Created:** `docs/development/ONTOLOGY_IMPORTS_PERSISTENCE_ISSUES.md`
**Purpose:** Document failed attempt to fix ontology imports persistence for future reference
**Branch:** `fix/ontology_imports` (16 commits, October 11, 2025)
**Outcome:** Branch abandoned without merge - architectural refactor needed instead
**Size:** 450+ lines
**Status:** Reference documentation - Do not merge branch code

**Problems Documented:**
- Import disappearance on browser refresh
- LocalStorage vs Fuseki synchronization issues
- Data corruption during save operations
- Imported node position persistence failures
- Three-way state management conflicts (Canvas ↔ LocalStorage ↔ Fuseki)

**Attempted Solutions (All Failed):**
1. Backend synchronization - Fuseki as source of truth
2. Import system overhaul - atomic imports only
3. LocalStorage restoration fixes
4. Imported node position persistence changes
5. Data corruption prevention measures

**Diagnostic Tools Created:**
- Debug functions: `debugImports()`, `checkDataIntegrity()`, `emergencyReload()`
- Extensive logging with emoji prefixes
- Import synchronization verification
- Position persistence testing

**Root Causes Identified:**
- No clear source of truth between three storage layers
- Missing import lifecycle state machine
- Race conditions between async operations
- 15,000+ line monolithic frontend file (architectural debt)

**Recommended Future Approach:**
- Full architectural refactor with proper state management library
- Single source of truth (Fuseki) with localStorage as cache only
- Break up monolithic app.html into testable modules
- Test-driven development for import lifecycle

**Key Lesson:** Incremental fixes on architectural problems don't work - need planned refactor
## New Documentation - October 11, 2025

### Ontology Inheritance System Implementation
**Created:** `docs/features/ONTOLOGY_INHERITANCE_SYSTEM.md`
**Purpose:** Comprehensive documentation of successful ontology inheritance system implementation
**Issue:** Need for class inheritance with "is_a" relationships where child classes inherit parent properties in individuals tables
**Solution:** Complete inheritance system with multiple parents, cross-project support, conflict resolution
**Size:** 350+ lines
**Status:** Active - Core inheritance system operational

**Key Features Implemented:**
- Multiple parent inheritance with conflict resolution
- Cross-project inheritance from reference ontologies
- Abstract class support with UI validation  
- Enhanced properties panel with parent selection dropdown
- Individuals tables show inherited properties with visual indicators (↑)
- Property range conflict resolution (xsd:float > string)
- URI mapping between display names and RDF storage

**Test Case Confirmed Working:**
- Object class (ID property) → PhysicalObject class (Mass, Length properties) → Aircraft class (vendor property)
- Aircraft individuals table correctly displays: Name, ID↑, Mass↑, Length↑, vendor, Actions
- All inherited properties properly marked with inheritance indicators

**Modified Files:**
- `backend/services/ontology_manager.py` - Core inheritance engine with recursive resolution
- `backend/api/ontology.py` - New inheritance API endpoints 
- `frontend/app.html` - Multi-select parent UI, RDF conversion fixes, inheritance table generation

**API Endpoints Added:**
- `GET /api/ontology/classes/{class_name}/all-properties` - Returns inherited properties
- `GET /api/ontology/available-parents` - Lists available parent classes
- `GET /api/ontology/classes/{class_name}/hierarchy` - Returns inheritance tree
- `PUT /api/ontology/classes/{class_name}` - Updates class with inheritance data

**Remaining Minor Issues Identified:**
- Property duplication in RDF (workaround: conflict resolution active)
- UI field duplication in properties panel (cosmetic)
- Abstract class checkbox persistence refinement needed
- Parent selection persistence timing improvements

## New Documentation - October 7, 2025

### RAG System Stabilization Guide
**Created:** `docs/development/RAG_STABILIZATION_GUIDE.md`
**Purpose:** Comprehensive documentation of RAG system fixes and improvements
**Issue:** UAS names query only returned 2 platforms instead of 9, source attribution failures
**Solution:** Enhanced chunk retrieval, fixed deduplication logic, improved source attribution
**Size:** 400+ lines
**Status:** Active - Primary reference for RAG system troubleshooting

**Key Changes Documented:**
- Increased chunk limits from 25 to 50 in DAS2 core engine
- Lowered similarity threshold from 0.15 to 0.1 for better coverage
- Modified deduplication to allow 3 chunks per document instead of 1
- Fixed source attribution by adding asset_id and document_type to chunk payloads
- Enhanced external task worker context from 3 to 10-15 chunks
- Created comprehensive test script for RAG validation

**Results Achieved:**
- UAS names query now returns all 9 platforms (was 2)
- Source attribution shows correct document titles (was "Unknown Document")
- Chunk retrieval increased from 3 to 9 chunks per query
- Response quality significantly improved with comprehensive details

**Modified Files:**
- `backend/services/das2_core_engine.py` - Chunk limits and thresholds
- `backend/services/rag_service.py` - Source attribution and deduplication
- `backend/services/store.py` - Chunk payload fields
- `backend/services/external_task_worker.py` - Context chunks
- `scripts/single_query_test.py` - NEW - Comprehensive test script
- `scripts/ci_rag_test.py` - NEW - Automated CI test script
- `.github/workflows/ci.yml` - Added RAG testing to CI pipeline

## New Documentation - October 6, 2025

### Database Connection Pool Troubleshooting Guide
**Created:** `docs/development/DATABASE_CONNECTION_POOL_TROUBLESHOOTING.md`
**Purpose:** Comprehensive troubleshooting guide for database connection pool issues
**Issue:** Users unable to login after idle periods due to stale database connections (Oct 2025)
**Solution:** TCP keepalive, connection validation, pool size reduction, background monitoring
**Size:** 518 lines
**Status:** Active - Primary reference for connection pool debugging

**Key Changes Documented:**
- Added TCP keepalive to PostgreSQL connections (keepalives=1, idle=30s, interval=10s, count=5)
- Implemented connection health checks in `_conn()` method
- Reduced connection pool from 5-50 to 2-20 connections
- Created background monitor task (`backend/services/db_monitor.py`)
- Improved connection return logic with validation

**Modified Files:**
- `backend/services/db.py` - Core connection pool changes
- `backend/services/config.py` - Pool size configuration
- `backend/services/db_monitor.py` - NEW - Background monitoring
- `backend/main.py` - Startup event integration

## Document Cleanup - September 23, 2025

**Branch:** `cleanup/repo-cleanup`
**Commit:** [Commit hash will be added after commit]
**Total Documents Before:** 74
**Total Documents After:** 27 (63% reduction)
**Additional Cleanup:** Moved all top-level .md files to docs/ folder

### 📋 Consolidation Strategy

#### 1. DAS Documentation → `docs/architecture/DAS_COMPREHENSIVE_GUIDE.md`
**Consolidated from 6 documents:**
- `DAS_Architecture_and_Implementation_Plan.md`
- `DAS_Current_Architecture_Documentation.md`
- `DAS_MVP_Implementation_Summary.md`
- `DAS_Tomorrow_Goals_Knowledge_and_API_Execution.md`
- `Digital_Assistance_System_(DAS)_MVP_Specification.md`
- `Session_Intelligence_and_Event_Capture_for_DAS.md`

#### 2. Testing Documentation → `docs/development/TESTING_GUIDE.md`
**Consolidated from 5 documents:**
- `TESTING_AND_VALIDATION_GUIDE.md`
- `TESTING_ENFORCEMENT_GUIDE.md`
- `TESTING_ENFORCEMENT_SUMMARY.md`
- `TESTING_IMPLEMENTATION_SUMMARY.md`
- `architecture/DATABASE_SCHEMA_TESTING_GUIDE.md`

#### 3. Ontology Workbench → `docs/features/ONTOLOGY_WORKBENCH_GUIDE.md`
**Consolidated from 4 documents:**
- `features/ontology_workbench_mvp.md`
- `features/ontology_workbench_post_mvp.md`
- `features/ontology-workbench-upgrade-plan.md`
- `ontology_import_equivalence_system.md`

#### 4. File Management → `docs/features/FILE_MANAGEMENT_GUIDE.md`
**Consolidated from 3 documents:**
- `features/file_management_workbench_mvp.md`
- `features/file_management_status_2024.md`
- `features/data_manager_workbench_spec.md`

#### 5. Namespace Management → `docs/features/NAMESPACE_MANAGEMENT_GUIDE.md`
**Consolidated from 5 documents:**
- `namespace/Namespace_White_Paper.md`
- `namespace/namespace_mvp.md`
- `namespace/namespace_implementation_plan.md`
- `namespace/installation_examples.md`
- `namespace-organization-uri-design.md`

### 🗑️ Documents Deleted

#### Historical/Planning Documents (Completed Work)
- `archive/mvp_week2_deliverables.md` - Historical planning document
- `archive/mvp_week2_executive_summary.md` - Historical planning document
- `archive/odras_mvp_updates_week2.md` - Historical planning document
- `archive/todo_morning_next_steps.md` - Outdated todo list
- `ODRAS_Heilmeier_Catechism.md` - Historical planning document
- `ODRAS_Heilmeier_Executive_Summary.md` - Historical planning document
- `project_todos.md` - Outdated project todos
- `phase2_quick_reference.md` - Outdated phase planning
- `REFACTORING_SUMMARY.md` - Work completed
- `REVIEW_INTERFACE_IMPLEMENTATION.md` - Implementation completed

#### Implementation Status Documents (Work Complete)
- `archive/USER_TASK_IMPLEMENTATION_STATUS.md` - Implementation completed
- `archive/USER_TASK_INTEGRATION.md` - Implementation completed
- `archive/DEVELOPMENT_STATUS.md` - Outdated status document
- `FEATURE_IMPLEMENTATION.md` - Work completed

#### Experimental/Unused Features
- `ProkOS/ProkOS.md` - Experimental feature not implemented
- `ProkOS/build_prompt.md` - Experimental feature not implemented
- `ProkOS/procos_spec.md` - Experimental feature not implemented
- `ProkOS/why_this_works.md` - Experimental feature not implemented
- `shacl_discussion.md` - Feature not implemented
- `shacl_example.md` - Feature not implemented

#### Concept Documents (Superseded by Implementation)
- `archive/concept_need_reviewed.md` - Concept superseded
- `archive/concept_needs.md` - Concept superseded
- `archive/concept_tool_spec.md` - Concept superseded

#### Testing Setup (Superseded by Current Testing)
- `archive/test_data_setup_guide.md` - Superseded by current test framework
- `archive/HOW_TO_TEST_CHANGES.md` - Superseded by current testing guide

#### Miscellaneous
- `archive/LABELS.md` - GitHub labels (not needed in docs)
- `archive/OLLAMA_GPU_SETUP.md` - Specific setup guide (moved to deployment if needed)
- `NDIA/meia_spec.md` - Specific client document (can be archived separately)

### 📚 Documents Preserved

#### Core Documentation (Kept as-is)
- `README.md` - Main project documentation
- `ROADMAP.md` - Future planning
- `AUTHENTICATION_SYSTEM.md` - Current system documentation
- `IRI_SYSTEM_OVERVIEW.md` - Current system documentation
- `USER_MANAGEMENT_UI.md` - Current system documentation

#### Architecture (Consolidated + Key Docs)
- `architecture/DAS_COMPREHENSIVE_GUIDE.md` - **NEW CONSOLIDATED**
- `architecture/DATABASE_SCHEMA_MANAGEMENT_SUMMARY.md` - Current system

#### Deployment
- `deployment/INSTALLATION_AND_IRI_SETUP.md` - Current deployment guide
- `deployment/INSTALLATION_SPECIFIC_IRI_CONFIG.md` - Current configuration
- `deployment/FEDERATED_ACCESS_QUICK_REFERENCE.md` - Current system

#### Development (Consolidated + Key Docs)
- `development/TESTING_GUIDE.md` - **NEW CONSOLIDATED**
- `development/BPMN_LLM_Integration_Guide.md` - Current integration guide
- `development/BPMN_WORKFLOWS.md` - Current workflow documentation

#### Features (All Consolidated)
- `features/ONTOLOGY_WORKBENCH_GUIDE.md` - **NEW CONSOLIDATED**
- `features/FILE_MANAGEMENT_GUIDE.md` - **NEW CONSOLIDATED**
- `features/NAMESPACE_MANAGEMENT_GUIDE.md` - **NEW CONSOLIDATED**
- `features/knowledge_management_mvp.md` - Current feature

#### Specifications
- `ODRAS_Advanced_Features_Specification.md` - Current specification
- `ODRAS_Use_Cases.md` - Current use cases
- `Ontology-Driven Requirements Analysis System (ODRAS).md` - Core specification

#### Implementation Guides
- `rag_query_implementation.md` - Current implementation
- `ontology_state_persistence.md` - Current implementation
- `reference_ontologies_feature.md` - Current feature
- `Project_Thread_Intelligence_Architecture.md` - Current architecture
- `PERSONA_PROMPT_README.md` - Current system

---

## Future Document Management

### Guidelines for New Documents
1. **Consolidate similar topics** into comprehensive guides
2. **Archive completed work** rather than keeping implementation docs
3. **Use clear naming conventions** with categories
4. **Regular cleanup** every 3-6 months
5. **Historical tracking** in this document

### Document Categories
- **Architecture** - System design and technical specifications
- **Features** - User-facing feature documentation
- **Deployment** - Installation and configuration
- **Development** - Developer guides and processes
- **Archive** - Historical documents (if needed for reference)

### Naming Conventions
- Use UPPERCASE for consolidated guides: `DAS_COMPREHENSIVE_GUIDE.md`
- Use descriptive names: `ONTOLOGY_WORKBENCH_GUIDE.md`
- Include version/date for specifications: `API_SPEC_v2.md`
