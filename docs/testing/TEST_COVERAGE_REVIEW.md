# Test Coverage Review for feature/individuals-tables-fixed

## Current CI Test Coverage

### ✅ Already in CI Workflow

1. **Individual Tables CRUD** (Step 9)
   - `tests/test_individuals_crud.py` ✅
   - Tests: CREATE, READ, UPDATE, DELETE operations
   - Tests Fuseki integration

2. **CQMT UI Test** (Step 6)
   - `scripts/cqmt_ui_test.py` ✅
   - Tests CQMT workbench UI functionality

3. **CQMT Dependency Tracking** (Step 7)
   - `tests/test_cqmt_dependency_tracking.py` ✅
   - Tests dependency validation and tracking

4. **Ontology Change Detection** (Step 8)
   - `tests/test_ontology_change_detection.py` ✅
   - Tests change detection for CQMT

---

## Missing Test Coverage

### ⚠️ Tests NOT in CI (Should Be Added)

1. **Class Migration Test** - `tests/test_class_migration.py`
   - **Purpose**: Tests class renaming migration for individuals
   - **Critical**: Ensures individuals are preserved when ontology classes are renamed
   - **Status**: Test file exists, not in CI

2. **Property Migration Test** - `tests/test_property_migration.py`
   - **Purpose**: Tests data property renaming migration for individuals
   - **Critical**: Ensures data is preserved when properties are renamed
   - **Status**: Test file exists, not in CI

3. **CQMT Workbench Complete Test** - `tests/test_cqmt_workbench_complete.py`
   - **Purpose**: Comprehensive CQ/MT Workbench test suite
   - **Tests**: CRUD operations, execution, validation for both CQs and Microtheories
   - **Status**: Test file exists (468 lines), not in CI

4. **CQMT Workbench Test** - `tests/test_cqmt_workbench.py`
   - **Purpose**: Additional CQMT workbench test coverage
   - **Status**: Test file exists, not in CI

---

## Recommendations

### High Priority (Add to CI)

1. **Add Class Migration Test**
   - Ensures individuals survive ontology class renames
   - Critical for data preservation during ontology evolution

2. **Add Property Migration Test**
   - Ensures individual properties survive property renames
   - Critical for data preservation during ontology evolution

3. **Add CQMT Workbench Complete Test**
   - Comprehensive test coverage for the integrated CQMT tab
   - Tests the actual UI functionality users interact with

### Medium Priority (Consider Adding)

4. **CQMT Workbench Test** (`test_cqmt_workbench.py`)
   - Additional test coverage, may overlap with complete test
   - Review for unique test cases

---

## Proposed CI Workflow Update

Add these test steps after Step 9:

```yaml
echo "🧪 Step 10: Class Migration Test..."
python -m pytest tests/test_class_migration.py -v --tb=short

echo "🧪 Step 11: Property Migration Test..."
python -m pytest tests/test_property_migration.py -v --tb=short

echo "🧪 Step 12: CQMT Workbench Complete Test..."
python -m pytest tests/test_cqmt_workbench_complete.py -v --tb=short
```

---

## Test Execution Order Rationale

1. **Basic CRUD** (individuals_crud) - Foundation tests
2. **Migration Tests** (class, property) - Ensure data preservation
3. **CQMT Integration** (workbench_complete) - Full workflow validation

This order ensures basic functionality works before testing advanced features.

---

*Generated: Test coverage review for feature/individuals-tables-fixed branch*
