# CQMT Workbench - Low Hanging Fruit

## ✅ Completed (Phases 1 & 2)

### Phase 1: Dependency Tracking ✅
- Database: `mt_ontology_dependencies` table created
- Service: `CQMTDependencyTracker` implemented
- API: 3 endpoints added (dependencies, validation, impact-analysis)
- Testing: Unit tests passing
- CI: Integrated

### Phase 2: Change Detection ✅
- Service: `OntologyChangeDetector` implemented
- Integration: Hooked into save workflow
- Parser: Hardened for prefixes
- Testing: 5/5 tests passing
- CI: Integrated

## 🎯 Low Hanging Fruit (Quick Wins)

### 1. Database Migration Script ⚡ Quick (30 min)
**Task**: Create migration script for existing MTs
- Extract dependencies from all existing MTs
- Populate dependency table
- **Impact**: Makes Phase 1 complete for production data
- **Effort**: Low - simple script using existing service
- **File**: `scripts/migrate_existing_mt_dependencies.py`

```python
# Pseudo-code
for mt in existing_mts:
    dependencies = dependency_tracker.extract_dependencies(mt.iri)
    dependency_tracker.store_dependencies(mt.id, dependencies)
```

### 2. Change History Endpoint ⚡ Quick (30 min)
**Task**: Create `GET /api/ontology/{graph_iri}/changes` endpoint
- Returns recent changes to ontology
- Uses existing change detection logic
- **Impact**: Enables UI to show change history
- **Effort**: Low - wraps existing service
- **File**: Add to `backend/api/ontology.py`

### 3. Document API Endpoints ⚡ Quick (20 min)
**Task**: Document dependency and change detection endpoints
- Update API docs with new endpoints
- Add examples
- **Impact**: Better developer experience
- **Effort**: Low - documentation only
- **File**: Update `docs/features/CQMT_WORKBENCH_SPECIFICATION.md`

### 4. Add Debug Endpoint ⚡ Quick (15 min)
**Task**: Add debug endpoint to check ontology elements
- Shows current elements in Fuseki
- Useful for troubleshooting
- **Impact**: Easier debugging
- **Effort**: Low - simple query endpoint
- **File**: Add to `backend/api/ontology.py`

## 🚀 Medium Effort (1-2 hours)

### 5. Simple UI Notification ⚡ Medium (1 hour)
**Task**: Show basic notification on ontology save
- Display change summary in toast/alert
- Shows: "X elements added, Y deleted, affects Z MTs"
- **Impact**: Immediate user feedback
- **Effort**: Medium - basic UI work
- **Files**: Update ontology editor UI

### 6. Validation Badge ⚡ Medium (1 hour)
**Task**: Add validation status badge to MT list
- Shows green/yellow/red based on dependencies
- Links to validation details
- **Impact**: Visual feedback on MT health
- **Effort**: Medium - UI component
- **Files**: Update MT list view

## ⏱️ While Waiting for CI

**Best Quick Win**: **Migration Script** (30 min)
- Makes Phase 1 complete for production
- Uses existing code we just tested
- Single script to write
- Immediately useful

**Next Best**: **Change History Endpoint** (30 min)
- Very simple to implement
- Enabled by existing Phase 2 code
- Adds value without complexity

## Recommendation

**Do Migration Script Now** ⚡
1. Takes 30 minutes
2. Makes Phase 1 complete
3. Uses tested code
4. No dependencies on CI

Want me to create the migration script?
