# CQMT Migration Script - Clarification

## When to Run Migration Script

### ✅ What Happens Automatically (No Migration Needed)

**NEW MTs** created AFTER Phase 1 deployment automatically get dependencies:
- `create_microtheory()` calls `dependency_tracker.extract_dependencies()`
- `update_microtheory()` calls `dependency_tracker.extract_dependencies()` 
- Dependencies are stored automatically

**CI Tests** don't need migration:
- CI starts with clean database (`./odras.sh init-db`)
- Any MTs created during tests are NEW
- They automatically get dependencies
- No migration script needed

### ⚠️ What Needs Migration (One-Time Only)

**EXISTING MTs** created BEFORE Phase 1 deployment:
- Created when dependencies weren't tracked
- Need ONE-TIME migration to populate `mt_ontology_dependencies` table
- Run migration script ONCE after deploying Phase 1

## Do We Need It in CI?

**NO** - The migration script is NOT needed in CI because:

1. **CI starts fresh**: `./odras.sh init-db` creates empty database
2. **All MTs are new**: Any MTs created during CI are new
3. **Auto-tracking works**: Phase 1 code automatically extracts dependencies
4. **No old data**: No existing MTs to migrate

## When to Run It

### Production Deployment
```
1. Deploy Phase 1 code
2. Run migration script ONCE: python scripts/migrate_existing_mt_dependencies.py
3. Done - all existing MTs now have dependencies tracked
```

### Developer Environments
```
- If you have existing MTs before pulling Phase 1 code
- Run migration script once
- Then all NEW MTs will auto-track dependencies
```

### CI Pipeline
```
- NO MIGRATION NEEDED
- Fresh database every run
- New MTs auto-track dependencies
```

## Summary

**Migration Script**:
- ✅ Needed: ONE-TIME after Phase 1 deployment
- ❌ NOT needed: In CI (fresh database)
- ❌ NOT needed: For new MTs (auto-tracked)

**Current Workflow**:
1. Create MT → Dependencies extracted automatically ✅
2. Update MT → Dependencies re-extracted automatically ✅
3. Save ontology → Change detection runs ✅

**CI Structure**:
- Existing CI tests are fine
- No changes needed
- New MTs in tests get dependencies automatically

## Recommendation

**For Current CI**: No changes needed. CI tests work fine as-is.

**For Production**: Run migration script once after deploying:
```bash
python scripts/migrate_existing_mt_dependencies.py
```

**For Future**: All new MTs automatically get dependencies tracked.
