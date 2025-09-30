# ODRAS API Test Structure Summary

## Overview

The ODRAS API tests have been reorganized into categorized CRUD test files for better maintainability, focused testing, and easier debugging. Each major entity type now has its own comprehensive test file.

## Test Categories

### 1. **Project CRUD Tests** (`test_project_crud.py`)
Tests all project-related operations:
- ✅ Create projects (basic, with metadata, validation)
- ✅ Read projects (by ID, list with filters, pagination)
- ✅ Update projects (name, metadata, partial updates)
- ✅ Delete projects (archive, restore, permanent delete)
- ✅ Access control and member management
- ✅ Project permissions

**Run:** `pytest tests/api/test_project_crud.py -v`

### 2. **Ontology CRUD Tests** (`test_ontology_crud.py`)
Tests all ontology-related operations:
- ✅ Create ontologies (basic, with metadata)
- ✅ Class management (creation, hierarchy, updates)
- ✅ Property management (object/data properties, characteristics)
- ✅ Individual/instance management
- ✅ Ontology structure retrieval
- ✅ Import/export functionality
- ✅ Reasoning capabilities

**Run:** `pytest tests/api/test_ontology_crud.py -v`

### 3. **File CRUD Tests** (`test_file_crud.py`)
Tests all file-related operations:
- ✅ Upload files (various types, sizes, metadata)
- ✅ Download files
- ✅ File metadata management
- ✅ File listing and filtering
- ✅ File updates and renaming
- ✅ File deletion (single and bulk)
- ✅ File versioning
- ✅ File permissions
- ✅ Batch operations

**Run:** `pytest tests/api/test_file_crud.py -v`

### 4. **Knowledge CRUD Tests** (`test_knowledge_crud.py`)
Tests all knowledge management operations:
- ✅ Upload knowledge documents
- ✅ Process files for knowledge extraction
- ✅ Basic and advanced search
- ✅ Semantic search capabilities
- ✅ Knowledge statistics
- ✅ Document management
- ✅ Knowledge graph operations
- ✅ Chunking and embeddings
- ✅ Batch operations

**Run:** `pytest tests/api/test_knowledge_crud.py -v`

### 5. **Event CRUD Tests** (`test_event_crud.py`)
Tests all event capture and tracking:
- ✅ Automatic event capture
- ✅ Manual event creation
- ✅ Session event tracking
- ✅ Event retrieval and filtering
- ✅ Event analytics and statistics
- ✅ DAS interaction events
- ✅ Semantic event enrichment
- ✅ Event updates and retention
- ✅ Real-time event streaming
- ✅ Event search

**Run:** `pytest tests/api/test_event_crud.py -v`

### 6. **Admin CRUD Tests** (`test_admin_crud.py`)
Tests all administrative operations:
- ✅ Prefix management (create, read, update, delete)
- ✅ Domain management
- ✅ Namespace management and members
- ✅ User management (CRUD, roles)
- ✅ System configuration
- ✅ System statistics and resource usage
- ✅ Audit logs
- ✅ Backup and restore
- ✅ Maintenance mode
- ✅ Cache management
- ✅ Permission enforcement

**Run:** `pytest tests/api/test_admin_crud.py -v`

## Test Organization Benefits

### 1. **Focused Testing**
- Each file focuses on a specific entity type
- Easy to run tests for just the area you're working on
- Clear separation of concerns

### 2. **Better Debugging**
- When a test fails, you know exactly which component is affected
- Smaller test files are easier to navigate
- Related tests are grouped together

### 3. **Parallel Execution**
- Different test files can run in parallel in CI/CD
- Faster overall test execution
- Better resource utilization

### 4. **Maintainability**
- New tests for a component go in the appropriate file
- Easy to find and update tests
- Consistent structure across all test files

## Running Tests

### Run All CRUD Tests
```bash
pytest tests/api/test_*_crud.py -v
```

### Run Specific Category
```bash
# Just project tests
pytest tests/api/test_project_crud.py -v

# Just admin tests
pytest tests/api/test_admin_crud.py -v
```

### Run Specific Test
```bash
# Run a specific test method
pytest tests/api/test_project_crud.py::TestProjectCRUD::test_create_basic_project -v
```

### Run Tests in Parallel
```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run with 4 workers
pytest tests/api/test_*_crud.py -v -n 4
```

## CI/CD Integration

The GitHub Actions workflow has been updated to run these categorized tests:

1. **Comprehensive Test Suite** - Overall system validation
2. **Categorized CRUD Tests** - Each category runs separately for better visibility
3. **Integration Tests** - Full stack testing
4. **Edge Case Tests** - Security and error handling

### CI Test Order
1. Database setup and validation
2. Service health checks
3. Comprehensive test suite
4. Unit tests
5. Categorized CRUD tests (with individual status reporting)
6. Full stack integration tests
7. Other API tests
8. Database schema tests

## Test Standards

Each test file follows these standards:

1. **Fixtures**
   - `client` - HTTP client for API calls
   - `auth_headers` - Authentication headers
   - `test_project` - Test project for operations
   - `admin_headers` - Admin authentication (where needed)

2. **Test Structure**
   - Tests grouped by operation type (CREATE, READ, UPDATE, DELETE)
   - Clear test names describing what's being tested
   - Proper cleanup after tests
   - Status messages for unimplemented endpoints

3. **Error Handling**
   - Tests handle both success and not-implemented cases
   - Graceful degradation for missing features
   - Clear reporting of test results

## Adding New Tests

When adding new tests:

1. **Identify the Category** - Which CRUD file should it go in?
2. **Follow the Pattern** - Use existing tests as templates
3. **Add Cleanup** - Ensure tests clean up after themselves
4. **Document Coverage** - Update this summary if adding new test categories

## Coverage Goals

Each test file aims to cover:
- ✅ Happy path scenarios
- ✅ Error cases and validation
- ✅ Edge cases and boundaries
- ✅ Permission and access control
- ✅ Performance considerations (timeouts)
- ✅ Integration with other components

## Continuous Improvement

These tests should grow over time:
- Add tests for new features
- Improve coverage of edge cases
- Add performance benchmarks
- Add data validation tests
- Add workflow/scenario tests

---

*Last Updated: December 2024*
