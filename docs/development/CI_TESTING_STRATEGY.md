# CI Testing Strategy - Best Practices

## Current State
- **Full stack integration tests** on every commit/PR
- **45-minute timeout** - comprehensive but slow
- **12+ test steps** - thorough but blocks development

## Recommended: Tiered Testing Strategy

### Tier 1: Fast Unit Tests (Every Commit)
**Duration**: < 2 minutes  
**Purpose**: Quick feedback on code changes  
**Runs on**: Every push, every PR

```bash
# Unit tests only - no services required
pytest tests/unit/ -v --tb=short -m "unit and not slow"
pytest tests/ -v --tb=short -m "unit and not integration and not slow"
```

**What to include**:
- All `@pytest.mark.unit` tests
- Fast isolated tests (no database/services)
- Interface/contract tests
- Fast RAG unit tests (mocked)

### Tier 2: Integration Tests (PRs Only)
**Duration**: 10-15 minutes  
**Purpose**: Verify integration with services  
**Runs on**: Pull requests, not every commit

```bash
# Integration tests - requires services
pytest tests/ -v --tb=short -m "integration and not slow"
pytest tests/api/test_core_functionality.py -v  # Critical path only
```

**What to include**:
- Core API functionality
- Critical integration paths
- RAG integration tests (subset)
- Training data initialization

### Tier 3: Full Suite (Merge to Main)
**Duration**: 30-45 minutes  
**Purpose**: Comprehensive validation  
**Runs on**: Merge to main, nightly builds

```bash
# Everything - full comprehensive suite
# Current full test suite
```

**What to include**:
- All integration tests
- Slow tests
- Comprehensive DAS tests
- Full RAG evaluation
- All CRUD operations

## Implementation Strategy

### Option A: Separate Workflows (Recommended)
```yaml
# .github/workflows/ci-fast.yml - Runs on every push
name: Fast CI
on: [push, pull_request]
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - pytest tests/ -m "unit and not slow"

# .github/workflows/ci-integration.yml - Runs on PRs
name: Integration CI
on:
  pull_request:
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - Start services
      - pytest tests/ -m "integration and not slow"

# .github/workflows/ci-comprehensive.yml - Runs on merge
name: Comprehensive CI
on:
  push:
    branches: [main]
jobs:
  full-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - Current full test suite
```

### Option B: Conditional Steps (Simpler)
```yaml
# Single workflow with conditional steps
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # Always run unit tests
      - name: Fast Unit Tests
        run: pytest tests/ -m "unit and not slow"
      
      # Only on PRs or main
      - name: Integration Tests
        if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main'
        run: |
          Start services
          pytest tests/ -m "integration and not slow"
      
      # Only on merge to main
      - name: Comprehensive Tests
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: |
          # Current full test suite
```

## Test Marking Strategy

### Mark Tests Appropriately
```python
# Fast unit test
@pytest.mark.unit
def test_persona_interface():
    pass

# Integration test (requires services)
@pytest.mark.integration
def test_training_data_initialization():
    pass

# Slow test (comprehensive evaluation)
@pytest.mark.slow
@pytest.mark.integration
def test_rag_real_world_evaluation():
    pass
```

### Test Categories
- **`@pytest.mark.unit`**: Fast, isolated, no services
- **`@pytest.mark.integration`**: Requires services, moderate speed
- **`@pytest.mark.slow`**: > 30 seconds, comprehensive
- **`@pytest.mark.critical`**: Must pass for CI (core functionality)

## Benefits

### Development Speed
- ✅ **Fast feedback** (< 2 min) on every commit
- ✅ **No blocking** on full stack startup for simple changes
- ✅ **Parallel development** - don't wait for full suite

### Quality Assurance
- ✅ **Unit tests** catch logic errors immediately
- ✅ **Integration tests** verify service interactions on PRs
- ✅ **Full suite** ensures nothing breaks on merge

### Resource Efficiency
- ✅ **Less CI minutes** consumed
- ✅ **Faster iteration** cycles
- ✅ **Selective testing** based on change scope

## Migration Plan

1. **Phase 1**: Mark all tests appropriately
   - Add `@pytest.mark.unit` to fast isolated tests
   - Add `@pytest.mark.integration` to service-requiring tests
   - Add `@pytest.mark.slow` to comprehensive tests

2. **Phase 2**: Create fast CI workflow
   - New workflow: `ci-fast.yml` for unit tests only
   - Runs on every push
   - < 2 minute target

3. **Phase 3**: Split integration tests
   - Move integration tests to PR-only workflow
   - Keep comprehensive suite for main branch

4. **Phase 4**: Optimize test execution
   - Parallel test execution where possible
   - Cache service startup
   - Optimize slow tests

## Best Practices

### ✅ DO
- Run unit tests on every commit
- Run integration tests on PRs
- Run full suite on merge to main
- Mark tests appropriately
- Keep unit tests fast (< 1 second each)
- Use test markers for selective execution

### ❌ DON'T
- Run full stack on every commit
- Block development on slow tests
- Mix fast and slow tests in same run
- Skip unit tests to save time
- Run comprehensive suite on feature branches

## Current Test Breakdown

### Fast Unit Tests (< 1 min)
- `tests/unit/test_*.py` - All unit tests
- `tests/test_rag_modular.py -m "not integration"` - RAG unit tests
- `tests/test_rag_llm_config.py -m "not integration"` - Config tests
- `tests/test_rag_hybrid_search.py -m "not integration"` - Hybrid search unit

### Integration Tests (5-15 min)
- `tests/test_rag_ci_verification.py` - RAG integration
- `tests/test_training_data_initialization.py` - Training data
- `tests/api/test_core_functionality.py` - Core API
- `tests/test_rag_modular.py -m integration` - RAG integration

### Comprehensive Tests (30-45 min)
- `tests/test_das_integration_comprehensive.py` - Full DAS
- `tests/test_rag_system_stability.py` - RAG stability
- `tests/test_rag_real_world_evaluation.py` - Real-world eval
- All CRUD tests
- All ontology tests
- Complete lifecycle tests

## Recommendation

**Implement Option A (Separate Workflows)**:
1. **Fast CI** (< 2 min) - Every commit
2. **Integration CI** (10-15 min) - PRs only
3. **Comprehensive CI** (30-45 min) - Main branch only

This gives you:
- ✅ Fast feedback for developers
- ✅ Quality assurance on PRs
- ✅ Comprehensive validation on merge
- ✅ Reduced CI costs
- ✅ Faster development cycles
