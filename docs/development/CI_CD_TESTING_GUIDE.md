# ODRAS CI/CD and Testing Guide

## Overview

This guide covers the comprehensive testing infrastructure for ODRAS, including GitHub Actions workflows, test suites, and quick validation tools.

## 🚀 Quick Start

### After Database Changes
```bash
# Quick validation (recommended first step)
python scripts/quick_db_test.py

# Full validation with API tests
python scripts/quick_db_test.py --full

# Run comprehensive test suite
pytest tests/test_comprehensive_suite.py -v
```

## 📋 Test Structure

### 1. Comprehensive Test Suite
**Location**: `tests/test_comprehensive_suite.py`

**Coverage**:
- Database integrity (PostgreSQL, Neo4j, Qdrant, Fuseki)
- All required tables and collections
- Critical API endpoints
- Authentication flow
- DAS service account functionality
- Project CRUD operations

### 2. Full Stack API Tests
**Location**: `tests/api/test_full_stack_api.py`

**Coverage**:
- Complete project lifecycle (create, read, update, delete)
- File upload and management
- Ontology creation and element management
- Knowledge document processing and search
- Namespace operations
- Multi-user collaboration scenarios
- Performance and concurrency testing

### 3. CRUD Operations Tests
**Location**: `tests/api/test_crud_operations.py`

**Coverage**:
- Detailed CRUD tests for all major entities:
  - Projects (with metadata and special characters)
  - Files (various types and sizes)
  - Ontologies (classes, properties, individuals)
  - Knowledge (upload, search, metadata)
  - Namespaces (admin operations)

### 4. Edge Cases and Error Handling
**Location**: `tests/api/test_edge_cases.py`

**Coverage**:
- Invalid authentication scenarios
- Malformed requests and data validation
- SQL injection and XSS attempts
- Unicode and special character handling
- Rate limiting and concurrent requests
- Boundary value testing
- Non-existent resource access

**Usage**:
```bash
# Run all comprehensive tests
pytest tests/test_comprehensive_suite.py -v

# Run specific test class
pytest tests/test_comprehensive_suite.py::TestDatabaseIntegrity -v

# Run tests matching pattern
pytest tests/test_comprehensive_suite.py -k "database" -v
```

### 2. Quick Database Test Script
**Location**: `scripts/quick_db_test.py`

**Purpose**: Rapid validation after database changes without full test suite

**Features**:
- Service availability checks
- Database table validation
- Qdrant collection verification
- Migration file checks
- Optional API endpoint testing

**Usage**:
```bash
# Basic check
python scripts/quick_db_test.py

# Include API tests
python scripts/quick_db_test.py --api

# Full validation
python scripts/quick_db_test.py --full
```

## 🔄 GitHub Actions Workflows

### 1. Comprehensive CI (`ci.yml`)
**Triggers**:
- Push to main, develop, feature/* branches
- Pull requests
- Manual dispatch

**What it does**:
- Sets up all services (PostgreSQL, Neo4j, Qdrant, Fuseki)
- Runs database migrations
- Creates required Qdrant collections
- Runs all test suites
- Code quality checks (Black, Flake8, isort)
- Security scanning

### 2. Database Tests (`database-tests.yml`)
**Triggers**:
- Changes to migrations, database code, or odras.sh
- Manual dispatch

**What it does**:
- Validates migration files
- Tests database build from scratch
- Verifies all tables and collections
- Creates test users

### 3. Smoke Tests (`smoke-tests.yml`)
**Triggers**:
- Manual dispatch
- After successful CI runs

**What it does**:
- Quick validation checks
- Verifies project structure
- Basic endpoint testing

## 🧪 Test Categories

### Unit Tests
```bash
pytest tests/unit/ -v
```

### API Tests
```bash
# All API tests
pytest tests/api/ -v

# Specific test suites
pytest tests/api/test_full_stack_api.py -v        # Full stack scenarios
pytest tests/api/test_crud_operations.py -v       # CRUD operations
pytest tests/api/test_edge_cases.py -v           # Edge cases
pytest tests/api/test_auth_endpoints.py -v       # Authentication
pytest tests/api/test_file_endpoints.py -v       # File management
pytest tests/api/test_ontology_endpoints.py -v   # Ontology operations
pytest tests/api/test_knowledge_management_endpoints.py -v  # Knowledge
```

### Database Tests
```bash
pytest tests/database/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Running Specific Test Functions
```bash
# Test a specific function
pytest tests/api/test_full_stack_api.py::TestFullStackAPI::test_complete_project_lifecycle -v

# Test all CRUD operations for projects
pytest tests/api/test_crud_operations.py::TestProjectCRUD -v

# Test edge cases only
pytest tests/api/test_edge_cases.py::TestEdgeCases::test_malformed_json_requests -v
```

## 🔐 Test Credentials

Always use the DAS service account for testing:
- **Username**: `das_service`
- **Password**: `das_service_2024!`

## 📊 Critical Validations

### Required PostgreSQL Tables
- users, projects, project_members
- files, knowledge_documents, knowledge_chunks
- auth_tokens, namespaces, namespace_members
- das_projects, das_threads, das_messages
- das_instructions, project_threads

### Required Qdrant Collections
- `knowledge_chunks` (384 dimensions)
- `knowledge_large` (1536 dimensions)
- `odras_requirements` (384 dimensions)
- `das_instructions` (384 dimensions)
- `project_threads` (384 dimensions) - Critical for DAS

## 🛠️ Troubleshooting

### Service Not Running
```bash
# Start all services
./odras.sh start

# Check service status
./odras.sh status

# View logs
./odras.sh logs [service_name]
```

### Database Issues
```bash
# Clean and rebuild database
./odras.sh clean -y && ./odras.sh init-db

# Check migration status
python scripts/database_schema_manager.py status
```

### Test Failures
1. Check service availability first
2. Verify database migrations completed
3. Ensure test users exist
4. Check Qdrant collections are created

## 📝 Best Practices

1. **Before Committing Database Changes**:
   - Run `python scripts/quick_db_test.py --full`
   - Ensure all migrations are in `migration_order.txt`
   - Test with `./odras.sh clean -y && ./odras.sh init-db`

2. **Adding New Tests**:
   - Add to appropriate test category
   - Include in `test_comprehensive_suite.py` if critical
   - Use DAS service account for authenticated tests
   - Test both success and failure scenarios
   - Include edge cases and error handling

3. **CI/CD Pipeline**:
   - All tests run automatically on push
   - Database tests run on migration changes
   - Manual smoke tests available for quick checks
   - Full stack API tests ensure end-to-end functionality

4. **Writing API Tests**:
   - Always clean up created resources (projects, files, etc.)
   - Use unique names with timestamps to avoid conflicts
   - Test concurrent operations when relevant
   - Validate both response status codes and response data
   - Handle various success codes (200, 201, 204)

5. **Testing Strategy**:
   - Start with happy path tests
   - Add edge cases and error scenarios
   - Test authorization and access control
   - Verify data validation and sanitization
   - Check performance under load

## 🚨 Important Notes

- Never use webhooks for CI/CD (as requested)
- All workflows trigger on commits or manual dispatch
- Database tests are isolated using Docker services
- Test data is ephemeral and recreated each run

## 📚 Related Documentation

- [Testing Guide](./TESTING_GUIDE.md) - General testing practices
- [Database Schema Manager](./DATABASE_SCHEMA_MANAGER_GUIDE.md) - Migration management
- [Development Guide](./DEVELOPMENT_GUIDE.md) - Development practices
