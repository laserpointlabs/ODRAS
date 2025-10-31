# GitHub Issues Summary - Created Today

## Date: January 2025

## Bug Fixes

### #49 - Ontology renaming breaks individual data associations
- **Problem:** Renaming classes/ontologies causes individuals to lose data properties
- **Solution:** Alias-based renaming system with unique internal identifiers
- **Status:** OPEN

### #66 - Class name change breaks individuals associated with that class
- **Priority:** High
- **Status:** OPEN
- **Problem:** Changing a class name results in updates to many individual tables, breaking individuals associated with that class
- **Impact:** Individual Tables CRUD operations fail when class is renamed. Test marked as XFAIL: `tests/test_class_migration.py`
- **Root Cause:** Class renaming updates lots of individual tables - complex operation that needs further work
- **Solution Needed:** Implement robust class migration system that:
  - Updates all individual table references
  - Preserves individual data properties
  - Maintains referential integrity across database tables
  - Handles bulk updates efficiently
- **Test Status:** Marked as `@pytest.mark.xfail` with reason: "Class renaming updates many individual tables - complex operation needing further work"
- **GitHub Issue:** #66
- **Related:** Issue #49, #64 (similar renaming problems)

### #64 - Renaming ontology breaks all individuals
- **Priority:** High
- **Status:** OPEN (GitHub Issue #64)
- **Problem:** Renaming the ontology breaks all individuals associated with that ontology
- **Impact:** All individuals become inaccessible or lose their associations when ontology is renamed
- **Solution:** Maintain original ontology name and use alias for display/naming
  - Store original ontology IRI/name in database as immutable identifier
  - Use alias/display name for user-facing operations
  - Update all queries and references to use original identifier
  - Preserve backward compatibility during transition
- **Related:** Issue #49, #66 (similar renaming problems)

### #63 - Individual Tables Workbench shows 0 count instead of actual sum
- **Priority:** Medium
- **Status:** OPEN (GitHub Issue #63)
- **Problem:** Individual Tables workbench displays 0 for individual counts even when individuals exist in the table
- **Impact:** Users cannot see how many individuals are in each class table
- **Location:** `frontend/app.html` - Individual Tables display area
- **Solution:** 
  - Fix count calculation/sum logic in `loadIndividualTablesInterface()` or `showIndividualTable()` functions
  - Ensure API returns correct count when fetching individuals
  - Display actual sum of individuals in table header/card
- **Affected Functions:** 
  - `loadIndividualTablesForCurrentOntology()`
  - `loadIndividualTablesInterface()`
  - `showIndividualTable()`

### #65 - CQMT Microtheories need DAS-driven workflow
- **Priority:** High
- **Status:** OPEN (GitHub Issue #65)
- **Problem:** Many microtheories created from test scripts, but not sure they're actually running. Don't want users manually creating microtheories.
- **Impact:** CQMT workflow is fragmented - users manually creating microtheories instead of guided workflow
- **Solution:** Implement DAS-driven CQMT workflow:
  1. Use DAS to work with user in discussion form to capture Competency Questions
  2. Automate development of microtheories based on captured CQs
  3. Remove or restrict manual microtheory creation
  4. Integrate DAS conversation flow into CQMT tab
- **Requirements:**
  - DAS conversation interface in CQMT tab
  - Natural language CQ capture and parsing
  - Automatic microtheory generation from CQ context
  - Validation and refinement workflow
- **Related:** CQMT Workbench, DAS Integration

### #55 - Critical Backend Refactoring
- **Problem:** main.py is 3,764 lines - monolithic file blocking plugin migration
- **Solution:** Refactor into modular structure (app_factory.py, startup/ modules)
- **Status:** OPEN
- **Priority:** CRITICAL BLOCKER

### #56 - Critical Frontend Refactoring
- **Problem:** app.html is 31,522 lines - monolithic file blocking plugin migration
- **Solution:** Refactor into modular structure (js/core/, js/components/, js/workbenches/)
- **Status:** OPEN
- **Priority:** CRITICAL BLOCKER

## Foundation Infrastructure (Blocking MVP)

### #52 - Plugin Infrastructure
- **Problem:** Need plugin system for modular architecture
- **Solution:** Plugin manifest, registry, loader, interfaces
- **Blocks:** All plugin-based workbenches
- **Status:** OPEN

### Event Bus Infrastructure
- **Problem:** Need event-driven architecture
- **Solution:** Event bus, schema registry, data contracts
- **Blocks:** Event management, pub/sub
- **Status:** OPEN

### #53 - Process Engine
- **Problem:** Camunda is external dependency, complex integration
- **Solution:** Native ODRAS process engine with BPMN 2.0 support
- **Blocks:** Process Management Workbench
- **Status:** OPEN

### #54 - Data Manager Workbench
- **Problem:** Need central data orchestration layer
- **Solution:** Data connectors, pipelines, subscriptions
- **Critical:** First plugin to migrate
- **Status:** OPEN

### API Gateway
- **Problem:** Need dynamic route registration
- **Solution:** Dynamic plugin routes, versioning, OpenAPI generation
- **Status:** OPEN

### Schema Registry
- **Problem:** Need data contracts between plugins
- **Solution:** Schema validation, version compatibility
- **Status:** OPEN

## MVP: Vendor Evaluation Workflow

### #50 - Requirements Import
- **Purpose:** Import from capabilities documents to individuals table
- **Workflow:** Upload → Extract → Create Requirements individuals
- **Status:** OPEN

### Requirements Validation
- **Purpose:** Validate requirements before conceptualization
- **Features:** Format validation, completeness, duplicates, quality scoring
- **Status:** OPEN

### #51 - Vendor Import
- **Purpose:** Import vendor individuals (Bell, Lockheed)
- **Features:** Vendor tagging, multi-vendor support
- **Status:** OPEN

### #52 (second) - System Ontology Creation
- **Purpose:** Generate system ontology from conceptualized requirements
- **Workflow:** Gather individuals → Deduplicate → Create ontology structure
- **Status:** OPEN

### System Ontology Validation
- **Purpose:** Validate system ontology completeness and consistency
- **Features:** Completeness checks, relationship validation, gap detection
- **Status:** OPEN

### #53 (second) - Tabularizer Vendor Evaluation
- **Purpose:** Specialized tables, pivots, statistics for vendor evaluation
- **Features:** Gap analysis, coverage matrices, comparison views
- **Status:** OPEN

### Complete Tabularizer Workbench
- **Purpose:** Comprehensive Tabularizer from plugin architecture plan
- **Features:** Dynamic comparison tables, pivot views, statistical analysis
- **Status:** OPEN

### #54 (second) - Officer Notes Tracking
- **Purpose:** Capture qualitative analysis during vendor evaluation
- **Features:** Rich text notes, linking, search/filter, export
- **Status:** OPEN

### #55 (second) - DAS Gap Analysis Integration
- **Purpose:** Leverage DAS for gap validation and solution evaluation
- **Use Cases:** Gap validation, solution evaluation, coverage analysis
- **Status:** OPEN

## UI/UX Enhancements

### Thread Tagging System
- **Purpose:** Tag and filter conversations in DAS dock
- **Tags:** conversation, concept, validation, refinement
- **Status:** OPEN

### Multiple Conversation Tabs
- **Purpose:** Tab-based interface for multiple conversation threads
- **Features:** New conversation button, close/reopen tabs, history viewer
- **Status:** OPEN

## New Workbenches

### Context Management Workbench
- **Purpose:** Manage DAS prompts, personas, agent teaming
- **Features:** Prompt library, persona designer, DAS self-improvement
- **Status:** OPEN

### Process Management Workbench
- **Purpose:** Visual process designer and monitor
- **Features:** BPMN designer, process analytics, testing interface
- **Blocks:** Process Engine (#53)
- **Status:** OPEN

### Data Management Workbench
- **Purpose:** ETL, connectors, pub/sub across projects
- **Features:** ETL designer, connectors, scheduler, pub/sub messaging
- **Status:** OPEN

### Event Management Workbench
- **Purpose:** Event coupling across projects
- **Features:** Event system, routing, impact analysis
- **Status:** OPEN

### Project Network Workbench
- **Purpose:** Parent/child relationships and gray test network
- **Features:** Project hierarchy, network graph, DAS auto-generation
- **Vision:** Generate entire acquisition programs from interconnected projects
- **Status:** OPEN

## Summary Statistics

- **Total Issues Created:** ~30+
- **Bug Fixes:** 7 (including #49, #63, #64, #65, #66, and XFAIL tests)
- **Enhancements:** 1 (#67 - Chat History Integration)
- **Critical Blockers:** 2 (Backend/Frontend refactoring)
- **Foundation Infrastructure:** 6
- **MVP Features:** 8
- **UI/UX:** 2
- **New Workbenches:** 5
- **Known Test Failures (XFAIL):** 2 (Migration tests documented)

## Critical Path

```
BLOCKERS (Must Do First):
#55 Backend Refactoring → #56 Frontend Refactoring
   ↓
#52 Plugin Infrastructure
   ↓
Event Bus + #53 Process Engine + #54 Data Manager
   ↓
MVP WORKFLOW:
#50 Requirements Import → Validation → Conceptualization →
Deduplication → #52 System Ontology → #51 Vendor Import →
#53 Tabularizer → #54 Notes → #55 DAS Analysis → COMPLETE
```

## Next Steps

1. **IMMEDIATE:** Address critical blockers (#55, #56)
2. **Phase 1:** Implement foundation infrastructure
3. **Phase 2:** Requirements and validation
4. **Phase 3:** Conceptualization and ontology
5. **Phase 4:** Vendor evaluation workflow
6. **Phase 5:** UI enhancements and new workbenches

---

### #67 - Integrate Cursor Chat History into ODRAS Knowledge Base for DAS Training
- **Priority:** High
- **Status:** OPEN (GitHub Issue #67)
- **Type:** Enhancement
- **What Happened:** Chat history recovery/extraction from Cursor (104 sessions, 2,055 conversations, 658MB)
- **Why:** Preserve development knowledge, decisions, patterns for DAS training
- **Extraction Date:** October 31, 2025
- **Branch:** feature/individuals-tables-fixed (extraction performed here)
- **Current Status:**
  - ✅ Phase 0: Extraction complete (script created, history extracted)
  - ❌ Phase 1: Chunking & knowledge extraction (not started)
  - ❌ Phase 2: Storage integration (not started)
  - ❌ Phase 3: DAS integration (not started)
  - ❌ Phase 4: Query interface (not started)
- **Files:** 
  - `scripts/cursor_chat_extractor.py`
  - `docs/development/CURSOR_CHAT_HISTORY_INTEGRATION.md`
  - `data/cursor_chat_backups/` (104 sessions)
- **GitHub:** https://github.com/laserpointlabs/ODRAS/issues/67

## Recent Issues (October 2025 - feature/individuals-tables-fixed Branch)

### #61 - Conceptualizer Should Store Individuals in Fuseki for CQ Compatibility
**Priority**: High  
**Status**: Open  
**Problem**: DAS conceptualizer stores individuals only in PostgreSQL, but CQs query Fuseki via SPARQL  
**Impact**: CQs return 0 rows, can't validate ontology  
**Solution**: Modify conceptualizer to store in both PostgreSQL AND Fuseki  
**Workaround**: Use `scripts/sync_das_individuals_to_fuseki.py` to manually sync

### #62 - Conceptualizer Should Store Relationships with rdf:type for CQ Queries
**Priority**: High  
**Status**: Open  
**Problem**: DAS conceptualizer stores relationships in configurations, but target instances lack rdf:type triples in Fuseki  
**Impact**: CQs that query for instances with relationships return 0 rows (instances exist but can't be type-matched)  
**Solution**: When storing conceptualizer results to Fuseki, ensure all relationship target instances have proper rdf:type triples  
**Workaround**: Modified `scripts/sync_das_individuals_to_fuseki.py` to add rdf:type for configuration-based instances

### XFAIL Tests - Migration Functionality
**Date**: October 31, 2025  
**Status**: Documented as Expected Failures  
**Branch**: feature/individuals-tables-fixed

#### Test Class Migration (`tests/test_class_migration.py`)
- **Status**: ⚠️ XFAIL (Marked with `@pytest.mark.xfail`)
- **Reason**: Class renaming updates many individual tables - complex operation needing further work
- **CI Behavior**: Test runs but failure doesn't fail CI (`|| true` in workflow)
- **Issue Reference**: #66 (GitHub Issue #66)
- **Test Location**: `tests/test_class_migration.py::test_class_rename_migration`

#### Test Property Migration (`tests/test_property_migration.py`)
- **Status**: ⚠️ XFAIL (Marked with `@pytest.mark.xfail`)
- **Reason**: Property renaming updates many individual tables - complex operation needing further work
- **CI Behavior**: Test runs but failure doesn't fail CI (`|| true` in workflow)
- **Issue Reference**: #66 (related to class migration complexity)
- **Test Location**: `tests/test_property_migration.py::test_property_rename_migration`

**CI Configuration**: Both tests are included in `.github/workflows/ci.yml` Steps 10-11 with XFAIL handling
