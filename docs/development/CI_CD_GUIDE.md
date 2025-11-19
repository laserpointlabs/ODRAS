# ODRAS CI/CD and Testing Guide

**Version:** 2.0  
**Date:** November 2025  
**Status:** Production Testing Documentation

## Overview

This guide consolidates all CI/CD testing documentation, including GitHub Actions workflows, test strategies, smoke test procedures, and comprehensive testing approaches for ODRAS.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [CI/CD Testing Strategy](#2-cicd-testing-strategy)
3. [Test Structure](#3-test-structure)
4. [Smoke Tests](#4-smoke-tests)
5. [GitHub Actions Workflows](#5-github-actions-workflows)
6. [Testing Best Practices](#6-testing-best-practices)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start

### After Database Changes
```bash
# Quick validation (recommended first step)
python scripts/quick_db_test.py

# Full validation with API tests
python scripts/quick_db_test.py --full

# Run comprehensive test suite
pytest tests/test_comprehensive_suite.py -v
```

### Quick Validation Commands
```bash
# Basic check
python scripts/quick_db_test.py

# Include API tests
python scripts/quick_db_test.py --api

# Full validation
python scripts/quick_db_test.py --full
```

---

## 2. CI/CD Testing Strategy

### Current State
- **Full stack integration tests** on every commit/PR
- **45-minute timeout** - comprehensive but slow
- **12+ test steps** - thorough but blocks development

### Recommended: Tiered Testing Strategy

#### Tier 1: Fast Unit Tests (Every Commit)
**Duration**: < 2 minutes  
**Purpose**: Quick feedback on code changes  
**Runs on**: Every push, every PR

```bash
# Unit tests only - no services required
pytest tests/unit/ -v --tb=short -m "unit and not slow"
pytest tests/ -v --tb=short -m "unit and not integration and not slow"
```

**What to include:**
- All `@pytest.mark.unit` tests
- Fast isolated tests (no database/services)
- Interface/contract tests
- Fast RAG unit tests (mocked)

#### Tier 2: Integration Tests (PRs Only)
**Duration**: 10-15 minutes  
**Purpose**: Verify integration with services  
**Runs on**: Pull requests, not every commit

```bash
# Integration tests - requires services
pytest tests/ -v --tb=short -m "integration and not slow"
pytest tests/api/test_core_functionality.py -v  # Critical path only
```

**What to include:**
- Core API functionality
- Critical integration paths
- RAG integration tests (subset)
- Training data initialization

#### Tier 3: Full Suite (Merge to Main)
**Duration**: 30-45 minutes  
**Purpose**: Comprehensive validation  
**Runs on**: Merge to main, nightly builds

```bash
# Everything - full comprehensive suite
# Current full test suite
```

**What to include:**
- All integration tests
- Slow tests
- Comprehensive DAS tests
- Full RAG evaluation
- All CRUD operations

### Implementation Strategy

**Option A: Separate Workflows (Recommended)**
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

**Option B: Conditional Steps (Simpler)**
- Single workflow with conditional steps
- Use GitHub Actions conditions to skip slow tests on commits
- Run full suite on PRs and merges

---

## 3. Test Structure

### 3.1 Comprehensive Test Suite
**Location**: `tests/test_comprehensive_suite.py`

**Coverage:**
- Database integrity (PostgreSQL, Neo4j, Qdrant, Fuseki)
- All required tables and collections
- Critical API endpoints
- Authentication flow
- DAS service account functionality
- Project CRUD operations

**Usage:**
```bash
# Run all comprehensive tests
pytest tests/test_comprehensive_suite.py -v

# Run specific test class
pytest tests/test_comprehensive_suite.py::TestDatabaseIntegrity -v

# Run tests matching pattern
pytest tests/test_comprehensive_suite.py -k "database" -v
```

### 3.2 Full Stack API Tests
**Location**: `tests/api/test_full_stack_api.py`

**Coverage:**
- Complete project lifecycle (create, read, update, delete)
- File upload and management
- Ontology creation and element management
- Knowledge document processing and search
- Namespace operations
- Multi-user collaboration scenarios
- Performance and concurrency testing

### 3.3 CRUD Operations Tests
**Location**: `tests/api/test_crud_operations.py`

**Coverage:**
- Detailed CRUD tests for all major entities:
  - Projects (with metadata and special characters)
  - Files (various types and sizes)
  - Ontologies (classes, properties, individuals)
  - Knowledge (upload, search, metadata)
  - Namespaces (admin operations)

### 3.4 Edge Cases and Error Handling
**Location**: `tests/api/test_edge_cases.py`

**Coverage:**
- Invalid authentication scenarios
- Malformed requests and data validation
- SQL injection and XSS attempts
- Unicode and special character handling
- Rate limiting and concurrent requests
- Boundary value testing
- Non-existent resource access

### 3.5 Quick Database Test Script
**Location**: `scripts/quick_db_test.py`

**Purpose**: Rapid validation after database changes without full test suite

**Features:**
- Service availability checks
- Database table validation
- Qdrant collection verification
- Migration file checks
- Optional API endpoint testing

**Usage:**
```bash
# Basic check
python scripts/quick_db_test.py

# Include API tests
python scripts/quick_db_test.py --api

# Full validation
python scripts/quick_db_test.py --full
```

---

## 4. Smoke Tests

### 4.1 Smoke Test Overview

Smoke tests provide quick validation that critical functionality works after changes. They are designed to run fast (< 5 minutes) and catch major breakages.

### 4.2 Smoke Test Components

**Database Smoke Tests:**
- PostgreSQL connection and basic queries
- Neo4j connection and graph queries
- Qdrant connection and vector operations
- Fuseki connection and SPARQL queries

**API Smoke Tests:**
- Authentication endpoint
- Project creation endpoint
- Basic CRUD operations
- Health check endpoints

**Service Smoke Tests:**
- All required services running
- Service health checks
- Basic inter-service communication

### 4.3 Running Smoke Tests

```bash
# Run smoke tests
pytest tests/ -m "smoke" -v

# Run specific smoke test
pytest tests/test_smoke_tests.py::TestDatabaseSmoke -v
```

### 4.4 Smoke Test Fixes

**Common Issues:**
- Service startup timing
- Database connection pooling
- Test data initialization
- Environment variable configuration

**Resolution:**
- Add proper wait conditions for services
- Implement connection retry logic
- Ensure test data is properly initialized
- Verify environment variables are set

---

## 5. GitHub Actions Workflows

### 5.1 Current Workflow Structure

**Main CI Workflow** (`.github/workflows/ci.yml`):
- Runs on every push and PR
- Spins up full stack (PostgreSQL, Neo4j, Qdrant, Redis, Fuseki)
- Runs comprehensive test suite
- 45-minute timeout

### 5.2 Workflow Components

**Service Setup:**
- PostgreSQL database initialization
- Neo4j graph database setup
- Qdrant vector database setup
- Redis cache setup
- Fuseki triplestore setup
- ODRAS API startup

**Test Execution:**
- Database integrity tests
- API endpoint tests
- Integration tests
- CRUD operation tests
- Edge case tests

**Artifact Collection:**
- Test results
- Logs
- Coverage reports

### 5.3 Workflow Optimization

**Recommended Improvements:**
- Separate fast unit tests from slow integration tests
- Run unit tests on every commit
- Run integration tests on PRs only
- Run full suite on merge to main
- Cache dependencies and services
- Parallel test execution

---

## 6. Testing Best Practices

### 6.1 Test Organization

**Test Markers:**
- `@pytest.mark.unit` - Unit tests (no services)
- `@pytest.mark.integration` - Integration tests (requires services)
- `@pytest.mark.slow` - Slow tests (> 5 seconds)
- `@pytest.mark.smoke` - Smoke tests (critical path)

**Test Structure:**
```
tests/
├── unit/           # Unit tests (no services)
├── integration/    # Integration tests (requires services)
├── api/            # API endpoint tests
└── test_comprehensive_suite.py  # Full suite
```

### 6.2 Test Credentials

**Standard Test Account:**
- Username: `das_service`
- Password: `das_service_2024!`
- Purpose: Automated testing and validation

### 6.3 Test Data Management

**Test Data Setup:**
- Use `./odras.sh init-db` for test data
- Clean up test data after tests
- Use fixtures for common test data
- Isolate test data by test class

### 6.4 Test Performance

**Optimization Strategies:**
- Use test markers to skip slow tests
- Run tests in parallel when possible
- Cache service startup
- Use test fixtures for expensive setup
- Clean up resources promptly

---

## 7. Troubleshooting

### 7.1 Common Test Failures

**Service Connection Failures:**
- **Cause**: Services not started or not ready
- **Solution**: Add wait conditions, check service health

**Database Connection Issues:**
- **Cause**: Connection pool exhaustion or timeout
- **Solution**: Increase pool size, add retry logic

**Test Data Issues:**
- **Cause**: Test data not initialized or cleaned up
- **Solution**: Ensure proper test data setup/teardown

**Timing Issues:**
- **Cause**: Race conditions or insufficient waits
- **Solution**: Add proper synchronization, increase timeouts

### 7.2 Debug Commands

**Check Service Status:**
```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs postgres
docker-compose logs neo4j
docker-compose logs qdrant
```

**Run Tests with Debug Output:**
```bash
# Verbose output
pytest tests/ -v -s

# Show print statements
pytest tests/ -v -s --capture=no

# Run single test with debug
pytest tests/test_specific.py::test_name -v -s
```

**Check Test Coverage:**
```bash
# Generate coverage report
pytest tests/ --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## Test Execution Summary

### Quick Validation (After Changes)
```bash
python scripts/quick_db_test.py
```

### Unit Tests (Fast Feedback)
```bash
pytest tests/ -m "unit and not slow" -v
```

### Integration Tests (PR Validation)
```bash
pytest tests/ -m "integration and not slow" -v
```

### Full Suite (Comprehensive)
```bash
pytest tests/test_comprehensive_suite.py -v
```

### Smoke Tests (Critical Path)
```bash
pytest tests/ -m "smoke" -v
```

---

*Last Updated: November 2025*  
*Consolidated from: CI_TESTING_STRATEGY.md, CI_CD_TESTING_GUIDE.md, CI_SMOKE_TEST_ANALYSIS.md, CI_SMOKE_TEST_FIX_COMPLETE.md, CI_SMOKE_TEST_FIX_PROPOSAL.md, BOTH_SMOKE_TESTS_FIXED.md, SMOKE_TEST_CLARIFICATION.md*
