# Smoke Test Clarification

## Two Different Smoke Tests

### 1. CI Smoke Test (`ci.yml` Step 1)
**File**: `scripts/fast_das_validator.py`
**Runs**: As part of main CI workflow
**Status**: ✅ Fixed with namespace schema change

**What it does**:
- Tests ODRAS connectivity
- Tests authentication
- Creates test project (needs namespaces) ← Fixed
- Tests DAS responses
- Tests ontology context

### 2. Smoke Tests Workflow (`smoke-tests.yml`)
**File**: `tests/test_comprehensive_suite.py::run_quick_validation()`
**Runs**: After CI completes (separate workflow)
**Status**: ⚠️ This one is failing

**What it does**:
- Checks if services are running (PostgreSQL, Neo4j, Qdrant, Fuseki)
- Checks API health endpoint
- Tests DAS login
- Validates project structure

## The Failing One

The `smoke-tests.yml` workflow **doesn't start services** - it expects them to already be running!

**Line 484-489**: Tries to connect to localhost services
**Problem**: Services not running in this workflow
**Solution**: Need to either:
1. Start services in this workflow
2. Skip service checks if services not available
3. Make it optional/graceful

## Fix Needed

The smoke-tests.yml workflow tries to connect to services that aren't running.

**Current behavior**:
```python
services = {
    "PostgreSQL": ("localhost", 5432),
    "Neo4j": ("localhost", 7687),
    ...
}
for service, (host, port) in services.items():
    sock.connect_ex((host, port))  # ← FAILS if service not running
```

**Fix options**:
1. Start services before validation
2. Make checks optional/graceful
3. Skip this workflow if services unavailable

## Recommendation

This workflow should be **optional** or **graceful** since it runs AFTER CI (where services may not be running).

Want me to fix this?
