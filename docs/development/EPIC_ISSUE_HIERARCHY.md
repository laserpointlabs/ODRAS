# Epic Issue Hierarchy - ODRAS Development Tracking

## Overview

This document tracks the top-level epic issues and their relationships to lower-level implementation issues.

**Last Updated:** October 31, 2025

## Top-Level Epics

### #69 - Complete ODRAS MVP - Workbench Improvements and New Features
**Priority:** High  
**Timeline:** 6-8 weeks  
**Status:** OPEN  
**GitHub:** https://github.com/laserpointlabs/ODRAS/issues/69

**Strategy:** MVP-First with Incremental Refactoring

**Components:**
1. **CQMT Workbench Cleanup**
   - #63: Individual Tables shows 0 count
   - #64: Renaming ontology breaks all individuals
   - #65: CQMT Microtheories need DAS-driven workflow
   - #66: Class name change breaks individuals

2. **Ontology Workbench Improvements**
   - #63: Individual Tables shows 0 count
   - #64: Renaming ontology breaks all individuals
   - #66: Class name change breaks individuals
   - #49: Ontology renaming breaks individual data associations

3. **Conceptualizer Enhancements**
   - #61: Conceptualizer should store individuals in Fuseki for CQ compatibility

4. **New Workbenches (Built as Plugins)**
   - Configurator Workbench (NEW - as plugin)
   - Tabularizer Workbench (NEW - as plugin)
   - #54: Data Manager Workbench (as plugin)

5. **DAS Enhancements**
   - #70: Thread Restore Functionality (separate epic, part of MVP)
   - #67: DAS Training System (Chat History Integration)

---

### #70 - Thread Restore Functionality - DAS Workflow Reliability
**Priority:** High  
**Status:** OPEN  
**Type:** Enhancement  
**GitHub:** https://github.com/laserpointlabs/ODRAS/issues/70

**Scope:**
- Thread persistence and restore
- Conversation history management
- Thread state recovery
- Project thread continuity
- Session restore across browser/app restarts

**Related:**
- Part of MVP Epic (#69)
- Enhances DAS reliability (#65, #67)

---

### #71 - Incremental Refactoring Strategy - Build Foundation While Delivering MVP
**Priority:** High  
**Status:** OPEN  
**Type:** Refactoring  
**GitHub:** https://github.com/laserpointlabs/ODRAS/issues/71

**Strategy:** Refactor code as you touch it, build new components in refactored pattern

**Phase 1: MVP Completion (Weeks 1-8)**
- Refactor existing workbenches as you fix/improve them
- Build new workbenches (configurator, tabularizer, data manager) as plugins
- Extract touched code to modules

**Phase 2: Complete Refactoring (Weeks 9-12)**
- #55: Critical Backend Refactoring (break up main.py)
- #56: Critical Frontend Refactoring (break up app.html)
- Event bus implementation
- Data mapping via ontologies

**Related Issues:**
- #55: Critical Backend Refactoring
- #56: Critical Frontend Refactoring
- #52: Plugin Infrastructure
- Related epic: #69 (MVP Completion)

---

## Issue Relationships

### Epic #69 (MVP Completion) → Lower-Level Issues
```
#69: Complete ODRAS MVP
├── #63: Individual Tables shows 0 count
├── #64: Renaming ontology breaks all individuals
├── #65: CQMT Microtheories need DAS-driven workflow
├── #66: Class name change breaks individuals
├── #49: Ontology renaming breaks individual data associations
├── #61: Conceptualizer should store individuals in Fuseki
├── #54: Data Manager Workbench
├── #67: DAS Training System (Chat History Integration)
└── #70: Thread Restore Functionality (related epic)
```

### Epic #71 (Incremental Refactoring) → Lower-Level Issues
```
#71: Incremental Refactoring Strategy
├── #55: Critical Backend Refactoring (Phase 2)
├── #56: Critical Frontend Refactoring (Phase 2)
└── #52: Plugin Infrastructure
```

### Cross-Epic Relationships
- #70 (Thread Restore) is part of #69 (MVP Completion)
- #71 (Refactoring) runs parallel to #69 (MVP Completion)
- #69 and #71 share strategy: Build new components in refactored pattern

---

## Success Criteria

### MVP Completion (#69)
- ✅ All MVP features working
- ✅ End-to-end workflow functional
- ✅ Thread restore working reliably
- ✅ DAS trained on ODRAS knowledge base
- ✅ 3+ workbenches built as plugins (validates architecture)

### Thread Restore (#70)
- ✅ Threads persist reliably
- ✅ Conversation history maintained
- ✅ Thread state restorable
- ✅ Works across browser sessions

### Incremental Refactoring (#71)
- ✅ Existing workbenches incrementally refactored
- ✅ New workbenches built as plugins
- ✅ Plugin architecture validated
- ✅ Monolithic files reduced in size
- ✅ Foundation ready for full refactor

---

## Strategy Document
See: `docs/development/MVP_VS_REFACTOR_STRATEGY.md`

---

*This hierarchy enables tracking MVP completion, refactoring progress, and dependencies between related work.*
