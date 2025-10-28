# GitHub Issues Summary - Created Today

## Date: January 2025

## Bug Fixes

### #49 - Ontology renaming breaks individual data associations
- **Problem:** Renaming classes/ontologies causes individuals to lose data properties
- **Solution:** Alias-based renaming system with unique internal identifiers
- **Status:** OPEN

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

- **Total Issues Created:** ~25+
- **Bug Fixes:** 3
- **Critical Blockers:** 2 (Backend/Frontend refactoring)
- **Foundation Infrastructure:** 6
- **MVP Features:** 8
- **UI/UX:** 2
- **New Workbenches:** 5

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




