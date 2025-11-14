# ODRAS Refactoring Status & Restart Plan

**Last Updated**: 2025-01-XX  
**Status**: Phase 0 Complete - Testing Infrastructure Ready

## ✅ **COMPLETED WORK**

### Phase 2: RAG Modularization ✅ **COMPLETE**
- **Status**: Fully implemented and integrated
- **Location**: `backend/rag/` module structure exists
- **Key Files**:
  - `backend/rag/core/modular_rag_service.py` - Main RAG orchestrator
  - `backend/rag/storage/` - Vector store implementations
  - `backend/rag/retrieval/` - Retriever implementations
  - `backend/rag/chunking/` - Chunking implementations
  - `backend/rag/embedding/` - Embedding implementations
- **Integration**: ModularRAGService integrated into startup and DAS
- **Tests**: All passing
- **Reference**: See `docs/architecture/RAG_MODULARIZATION_STATUS.md`

### Phase 1.3-1.6: Backend Infrastructure ✅ **COMPLETE**
- **Status**: Backend refactoring infrastructure in place
- **Key Files**:
  - `backend/app_factory.py` - Application factory ✅
  - `backend/startup/` - Startup modules ✅
    - `initialize.py` - Centralized initialization
    - `database.py` - Database initialization
    - `services.py` - Service initialization (uses ModularRAGService)
    - `das.py` - DAS initialization
    - `events.py` - Event system initialization
    - `middleware.py` - Middleware configuration
    - `routers.py` - Router registration
  - `backend/api/core.py` - Core endpoints (auth, health, sync, projects) ✅
  - `backend/main.py` - Slimmed down to ~60 lines ✅

## ⚠️ **PARTIALLY COMPLETE**

### Phase 1.1: DAS Consolidation ⚠️ **MOSTLY COMPLETE - Minor Cleanup Needed**
- **Current State**: 
  - ✅ Backend API uses `/api/das/` prefix correctly
  - ✅ Backend service is `DASCoreEngine` (not DAS2)
  - ✅ Old DAS1 archived
  - ⚠️ Frontend has mixed references - some still use `/api/das2/`
- **What's Done**:
  - ✅ Single DAS implementation (`DASCoreEngine`)
  - ✅ API router uses `/api/das/` prefix
  - ✅ Backend code properly named
  - ✅ Old DAS1 archived
- **What's Remaining**:
  - [ ] Update frontend references from `/api/das2/` to `/api/das/` in:
    - `frontend/app.html` (lines 12405, 19433, 19680, 25908)
    - Verify `frontend/js/das/das-api.js` is correct (already uses `/api/das/`)
  - [ ] Remove any remaining DAS2 comments/references in backend
  - [ ] Update any documentation that references DAS2

### Phase 1.2: Ontology API Consolidation ⚠️ **PARTIALLY DONE**
- **Current State**:
  - Two separate routers exist:
    - `backend/api/ontology.py` - Singular `/api/ontology/` endpoints
    - `backend/api/ontology_registry.py` - Plural `/api/ontologies` endpoints
  - Both are registered in `backend/startup/routers.py`
- **What's Done**:
  - Routers separated from main.py
  - Clear separation of concerns
- **What's Remaining**:
  - [ ] Verify all endpoints are in routers (not in main.py)
  - [ ] Consider if consolidation into single router is needed OR
  - [ ] Document the two-router approach as intentional design
  - [ ] Ensure no endpoint conflicts or duplication

## ✅ **COMPLETED TODAY**

### Phase 0: Testing Infrastructure ✅ **COMPLETE**
- [x] Create `scripts/ci-local.sh` - Local CI replication ✅
- [x] Create `scripts/quality-check.sh` - Code quality checks ✅
- [x] Create `.pre-commit-config.yaml` - Pre-commit hooks ✅
- [x] Enhance `pytest.ini` with test categorization and parallel execution ✅
- [x] CI.yml already has coverage reporting (no changes needed)

**Files Created**:
- `scripts/ci-local.sh` - Mirrors GitHub Actions CI workflow
- `scripts/quality-check.sh` - Comprehensive code quality checks
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `docs/architecture/ONTOLOGY_API_DESIGN.md` - Ontology API design documentation

**Files Updated**:
- `frontend/app.html` - Updated 4 DAS2 references to DAS
- `pytest.ini` - Added parallel execution support

### Phase 3: Frontend Refactoring ❌ **NOT STARTED**
- [ ] Create `frontend/js/core/` - Core infrastructure
- [ ] Create `frontend/js/components/` - Shared components
- [ ] Extract workbench modules to `frontend/js/workbenches/`
- [ ] Create slim `frontend/index.html` (~300 lines)

### Phase 4: Data Management Foundation ❌ **NOT STARTED**
- [ ] Create `backend/services/data_manager.py`
- [ ] Create `backend/schemas/workbench_data.py`

## 🎯 **RESTART PLAN - Where to Continue**

### **IMMEDIATE NEXT STEPS** (After RAG/DAS Work)

#### **Step 1: Complete DAS Consolidation** (1-2 hours)
**Priority**: MEDIUM - Minor cleanup needed

1. **Update Frontend References**:
   ```bash
   # Find remaining /api/das2/ references
   grep -n "/api/das2" frontend/app.html
   
   # Update these specific lines in frontend/app.html:
   # - Line 12405: assumptions endpoint
   # - Line 19433: history endpoint  
   # - Line 19680: delete conversation endpoint
   # - Line 25908: thread endpoint
   ```

2. **Verify Backend**:
   ```bash
   # Check for any remaining DAS2 references in backend
   grep -r "das2\|DAS2" backend/ --include="*.py" | grep -v archive | grep -v __pycache__
   ```

3. **Test**:
   - Verify DAS functionality still works
   - Test frontend DAS interface
   - Check logs for any errors

#### **Step 2: Verify Ontology API Consolidation** (1 day)
**Priority**: MEDIUM - Ensure consistency

1. **Audit Endpoints**:
   ```bash
   # Check if any ontology endpoints still in main.py
   grep -n "ontology\|ontologies" backend/main.py
   
   # List all ontology endpoints
   grep -E "@.*router\.(get|post|put|delete)" backend/api/ontology*.py
   ```

2. **Document Decision**:
   - If two routers are intentional → Document the design
   - If consolidation needed → Plan consolidation

3. **Test**:
   - Verify all ontology endpoints work
   - Check for conflicts

#### **Step 3: Start Testing Infrastructure** (2-3 days)
**Priority**: HIGH - Enables safe refactoring

1. **Create Local CI Script**:
   - Mirror `.github/workflows/ci.yml`
   - Enable local testing before push

2. **Add Pre-commit Hooks**:
   - Code formatting (black)
   - Linting (flake8)
   - Fast tests

3. **Test Coverage**:
   - Add coverage reporting
   - Set coverage thresholds

### **MEDIUM-TERM NEXT STEPS**

#### **Step 4: Frontend Refactoring** (1-2 weeks)
**Priority**: MEDIUM - Large effort, can be incremental

1. **Start with Core Infrastructure**:
   - Extract `frontend/js/core/` modules
   - Extract `frontend/js/components/` modules
   - Test incrementally

2. **Extract Workbenches One at a Time**:
   - Start with Requirements Workbench
   - Test thoroughly before moving to next
   - Follow pattern established in backend

#### **Step 5: Data Management Foundation** (1 week)
**Priority**: LOW - Prepares for plugin architecture

1. **Create Data Manager Service**
2. **Define Workbench Data Contracts**
3. **Integrate with existing workbenches**

## 📋 **CHECKLIST FOR RESTART**

### Before Starting Work
- [ ] Review current branch status
- [ ] Check for uncommitted changes
- [ ] Review recent commits (RAG/DAS work)
- [ ] Verify tests pass
- [ ] Check logs for errors

### During Work
- [ ] Work on one task at a time
- [ ] Test after each change
- [ ] Check logs after each change
- [ ] Update this status document
- [ ] Commit frequently with clear messages

### After Each Phase
- [ ] Run full test suite
- [ ] Check logs
- [ ] Verify functionality manually
- [ ] Update plan document
- [ ] Document any issues or decisions

## 🔍 **VERIFICATION COMMANDS**

```bash
# Check DAS references
grep -r "das2\|DAS2" backend/ --include="*.py" | grep -v archive | grep -v __pycache__

# Check ontology endpoints
grep -E "@.*router\.(get|post|put|delete)" backend/api/ontology*.py

# Check main.py size
wc -l backend/main.py

# Check frontend size
wc -l frontend/app.html

# Run tests
pytest tests/ -v

# Check logs
./odras.sh logs | tail -50
```

## 📚 **REFERENCE DOCUMENTS**

- **RAG Status**: `docs/architecture/RAG_MODULARIZATION_STATUS.md`
- **Refactoring Plan**: `.cursor/plans/odras-mvp-refactoring-plan-9ab58978.plan.md`
- **Plugin Plan**: `.cursor/plans/plugin-architecture-decoupling-1a95a09b.plan.md`
- **Ontology Endpoints**: `docs/development/ONTOLOGY_ENDPOINTS_GUIDE.md`

## 🎯 **SUCCESS CRITERIA**

### Phase 1 Complete When:
- [ ] Single DAS implementation (no DAS2 references)
- [ ] All ontology endpoints in routers (not main.py)
- [ ] main.py remains ~60 lines
- [ ] All tests pass
- [ ] No breaking changes

### Phase 0 Complete When:
- [ ] `scripts/ci-local.sh` works
- [ ] Pre-commit hooks installed
- [ ] Test coverage reporting works
- [ ] Quality checks automated

### Phase 3 Complete When:
- [ ] `frontend/index.html` is ~300 lines
- [ ] Workbenches extracted to modules
- [ ] All functionality works
- [ ] No breaking changes

---

**Next Action**: Start with Step 1 (DAS Consolidation) - Complete the renaming work that was started but not finished.
