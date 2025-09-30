# ODRAS Testing Workflow Guide

## Overview

ODRAS uses **integration tests** that run against the **REAL API** and full database stack. This ensures complete system validation after database changes and code modifications.

## Test Architecture

### **Integration Tests (Not Mocked)**
- Tests connect to `http://localhost:8000` (real running API)
- Uses real databases: PostgreSQL, Neo4j, Qdrant, Redis, Fuseki
- Requires the complete ODRAS stack running
- Test credentials: `das_service` / `das_service_2024!`

### **Test Categories**

| Test File | Purpose | Duration | Use Case |
|-----------|---------|----------|----------|
| `test_full_use_case.py` | Complete workflow validation | ~30s | After any changes |
| `test_schema_validation.py` | Full rebuild + validation | ~5min | After DB schema changes |
| `test_project_crud.py` | Project operations only | ~10s | Project development |
| `test_*_crud.py` | Component-specific tests | ~10s each | Component development |

## Daily Testing Workflow

### **Quick Validation (Most Common)**
```bash
# After code changes - validates complete workflow
pytest tests/api/test_full_use_case.py -v -s
```
**What it tests:**
- ✅ Project creation and management
- ✅ Ontology creation with entities and properties
- ✅ File uploads and management
- ✅ Knowledge assets and search
- ✅ System verification and cleanup
- ✅ Real database integration

### **Schema Change Validation**
```bash
# After database schema changes - full rebuild
pytest tests/api/test_schema_validation.py -v -s
```
**What it does:**
1. 🔄 Stops ODRAS API
2. 🧹 Cleans entire database (`./odras.sh clean -y`)
3. 🏗️ Rebuilds from scratch (`./odras.sh init-db`)
4. 🚀 Starts ODRAS API
5. ✅ Runs complete workflow validation

### **Component Testing**
```bash
# Test specific components during development
pytest tests/api/test_project_crud.py -v        # Projects only
pytest tests/api/test_ontology_crud.py -v       # Ontology only
pytest tests/api/test_file_crud.py -v           # Files only
```

## Pytest Command Reference

### **Essential Flags**
```bash
-v, --verbose      # Show detailed test output
-s, --no-capture   # Show print() statements in real-time
--tb=short         # Shorter error tracebacks
--tb=long          # Full error tracebacks
-x                 # Stop on first failure
```

### **Common Combinations**
```bash
# Development workflow
pytest tests/api/test_full_use_case.py -v -s --tb=short

# Debugging failures
pytest tests/api/test_project_crud.py -v -s --tb=long -x

# Quick status check
pytest tests/api/test_full_use_case.py --tb=short

# Run specific test method
pytest tests/api/test_full_use_case.py::TestFullODRASUseCase::test_complete_odras_workflow -v

# All CRUD tests
pytest tests/api/test_*_crud.py -v
```

### **Advanced Options**
```bash
# Parallel execution (requires: pip install pytest-xdist)
pytest tests/api/test_*_crud.py -v -n 4         # 4 parallel workers
pytest tests/api/ -v -n auto                    # Auto-detect CPUs

# Timeout handling
pytest tests/api/test_full_use_case.py --timeout=600

# Filter by test name
pytest -k "project" -v                         # Tests with "project" in name
pytest -k "not admin" -v                       # Exclude admin tests

# Debug mode
pytest tests/api/test_project_crud.py --pdb    # Drop into debugger on failure

# Show local variables
pytest tests/api/test_project_crud.py -l       # Show locals in traceback
```

## Prerequisites

### **Services Must Be Running**
```bash
# Check service status
docker ps

# Ensure all services are up
docker-compose up -d

# Check ODRAS API status
./odras.sh status

# Start if needed
./odras.sh start
```

**Required Services:**
- ✅ PostgreSQL (port 5432)
- ✅ Neo4j (ports 7474, 7687)
- ✅ Qdrant (port 6333)
- ✅ Redis (port 6379)
- ✅ Fuseki (port 3030)
- ✅ ODRAS API (port 8000)

### **Database Initialization**
```bash
# If database is corrupted or missing data
./odras.sh clean -y && ./odras.sh init-db

# Quick verification
curl http://localhost:8000/api/health
```

## Test Results Interpretation

### **✅ Success Indicators**
```bash
# Full workflow success
🎉 WORKFLOW COMPLETE!
✓ Admin functions (prefixes, domains, namespaces)
✓ Project creation and management
✓ Ontology and entity creation
✓ File upload and management
✓ Knowledge asset processing
✓ Search and retrieval
```

### **⚠️ Partial Success (Expected)**
Some admin endpoints may not be implemented:
```bash
⚠️ Prefix creation not available (status: 404)
⚠️ Domain creation not available (status: 404)
⚠️ Namespace creation not available (status: 404)
```
This is **normal** - not all admin features are implemented yet.

### **❌ Failure Scenarios**

**API Connection Issues:**
```bash
# Symptoms
httpx.ConnectError: Connection refused
ReadTimeout

# Solutions
./odras.sh start
# Wait 10 seconds, retry test
```

**Authentication Failures:**
```bash
# Symptoms
assert 500 == 200 (login failed)
Login error: 'NoneType' object has no attribute 'cursor'

# Solutions
./odras.sh clean -y && ./odras.sh init-db
# This recreates test users
```

**Database Issues:**
```bash
# Symptoms
Connection failed, Table doesn't exist

# Solutions
./odras.sh clean -y && ./odras.sh init-db
./odras.sh start
```

## CI/CD Integration

The GitHub Actions workflow runs:

```yaml
1. Service Setup (PostgreSQL, Neo4j, Qdrant, Redis, Fuseki)
2. Database Initialization (schema + collections + users)
3. Comprehensive Test Suite
4. Categorized CRUD Tests
5. Full Workflow Test ← KEY VALIDATION
6. Integration Tests
7. Edge Case Tests
```

**Key Test in CI/CD:**
```bash
pytest tests/api/test_full_use_case.py -v --tb=short --timeout=900
```

## Troubleshooting

### **Tests Running Slowly (8+ seconds per operation)**
This is **expected behavior**. ODRAS operations involve:
- Database writes to PostgreSQL
- Graph updates in Neo4j
- Vector operations in Qdrant
- Cache updates in Redis
- RDF operations in Fuseki

**Performance expectations:**
- Project creation: 6-10 seconds
- File upload: 2-5 seconds
- Ontology operations: 3-8 seconds
- Full workflow test: 25-35 seconds

### **Individual CRUD Test Failures**
Some individual `test_*_crud.py` files may need fixture updates. The **main workflow test** covers all functionality and is the primary validation.

**Priority:**
1. ✅ `test_full_use_case.py` - MUST PASS
2. ✅ `test_project_crud.py` - Core functionality
3. ⚠️ Other CRUD files - Nice to have, covered by workflow test

### **Memory/Resource Issues**
```bash
# If tests fail due to resource constraints
docker-compose restart
./odras.sh restart
pytest tests/api/test_full_use_case.py -v -s
```

## Development Workflow

### **Recommended Testing Sequence**

1. **Daily Development:**
   ```bash
   pytest tests/api/test_full_use_case.py -v -s
   ```

2. **Before Committing:**
   ```bash
   pytest tests/api/test_full_use_case.py -v --tb=short
   pytest tests/api/test_project_crud.py -v
   ```

3. **After Database Changes:**
   ```bash
   pytest tests/api/test_schema_validation.py -v -s
   ```

4. **Component Development:**
   ```bash
   pytest tests/api/test_project_crud.py -v      # Working on projects
   pytest tests/api/test_ontology_crud.py -v     # Working on ontology
   ```

### **Integration with Development**
```bash
# Standard development cycle
git pull origin main
docker-compose up -d
./odras.sh restart
pytest tests/api/test_full_use_case.py -v -s    # Validate system
# Make changes...
pytest tests/api/test_full_use_case.py -v -s    # Validate changes
git add . && git commit -m "feature: description"
git push origin feature/branch-name
# GitHub Actions runs full test suite
```

## Test Maintenance

### **Adding New Tests**
Follow the pattern in `test_full_use_case.py`:
```python
@pytest.fixture
async def client(self):
    async with AsyncClient(base_url="http://localhost:8000", timeout=60.0) as client:
        yield client

@pytest.fixture
async def auth_headers(self, client):
    response = await client.post("/api/auth/login",
        json={"username": "das_service", "password": "das_service_2024!"})
    return {"Authorization": f"Bearer {response.json()['token']}"}
```

### **Test Data Cleanup**
All tests should clean up after themselves:
```python
try:
    # Test operations
    created_resources["projects"].append(project_id)
finally:
    # Cleanup
    await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
```

---

## Quick Reference

**Most Important Command:**
```bash
pytest tests/api/test_full_use_case.py -v -s
```

**After Database Changes:**
```bash
pytest tests/api/test_schema_validation.py -v -s
```

**System Status Check:**
```bash
./odras.sh status
docker ps
curl http://localhost:8000/api/health
```

This testing approach ensures **confidence after database changes** and validates the complete ODRAS system integration.
