# ODRAS Testing Guide
*Comprehensive Testing and Validation Framework*

## 🎯 Overview

This guide provides the complete testing strategy for ODRAS, covering API testing, integration testing, database validation, and CI/CD procedures. All testing approaches are consolidated here for consistency and maintainability.

## 📋 Testing Philosophy

### Core Principles
- **Test-Driven Development**: Write tests before implementation when possible
- **Comprehensive Coverage**: API, unit, integration, and performance testing
- **Automated Validation**: CI/CD pipeline ensures quality gates
- **Real-world Testing**: Use actual user scenarios and data patterns

### Testing Pyramid
```
     /\     E2E Tests (Few, High-Value)
    /  \    
   /____\   Integration Tests (Some, Key Flows)
  /      \  
 /________\  Unit Tests (Many, Fast, Isolated)
```

## 🧪 Test Categories

### **1. API Testing**

#### Authentication Endpoints
```python
# Test user login/logout
def test_auth_login_success()
def test_auth_login_invalid_credentials()
def test_auth_logout()
def test_token_validation()
```

#### Ontology Management
```python
# Test ontology CRUD operations
def test_create_ontology()
def test_get_ontology_list()
def test_update_ontology()
def test_delete_ontology()
def test_ontology_import_export()
```

#### File Management
```python
# Test file operations
def test_file_upload()
def test_file_download()
def test_file_processing()
def test_batch_operations()
```

#### Project Management
```python
# Test project lifecycle
def test_project_creation()
def test_project_permissions()
def test_project_collaboration()
```

### **2. Database Testing**

#### Schema Validation
- **Migration Testing**: Ensure all migrations apply cleanly
- **Constraint Testing**: Verify foreign key and unique constraints
- **Index Performance**: Validate query performance with indexes
- **Data Integrity**: Test referential integrity across tables

#### Test Database Setup
```bash
# Database test initialization
./odras.sh init-test-db
python scripts/setup_test_knowledge_data.py
```

### **3. Integration Testing**

#### Service Integration
- **Camunda Integration**: BPMN workflow execution
- **Vector Store Integration**: Qdrant operations
- **Graph Database**: Neo4j connectivity
- **External APIs**: OpenAI, Ollama integration

#### End-to-End Workflows
- **Document Ingestion**: Upload → Process → Extract → Store
- **Ontology Editing**: Create → Edit → Save → Export
- **User Workflows**: Login → Create Project → Upload Files → Analyze

### **4. Performance Testing**

#### Load Testing
```python
# Concurrent user simulation
def test_concurrent_ontology_editing()
def test_bulk_file_processing()
def test_large_dataset_queries()
```

#### Response Time Targets
- **API Responses**: < 2 seconds for most endpoints
- **File Upload**: < 30 seconds for files up to 100MB
- **Search Queries**: < 1 second for vector searches
- **Ontology Rendering**: < 5 seconds for complex ontologies

### **5. Security Testing**

#### Authentication & Authorization
- **Token Security**: JWT validation and expiration
- **Role-Based Access**: Project permissions and admin rights
- **API Security**: Endpoint protection and input validation
- **Data Privacy**: User data isolation and encryption

#### Security Test Cases
```python
def test_unauthorized_access_blocked()
def test_sql_injection_prevention()
def test_xss_protection()
def test_file_upload_security()
```

## 🚀 Test Execution

### **Manual Testing Procedures**

#### Pre-Merge Checklist
1. **API Validation**: Run comprehensive endpoint tests
2. **UI Testing**: Verify frontend functionality
3. **Database Integrity**: Check schema and data consistency
4. **Service Health**: Confirm all services are operational
5. **Performance Check**: Validate response times

#### Test Credentials
```
Username: das_service
Password: das_service_2024!
```

### **Automated Testing Pipeline**

#### CI/CD Integration
```yaml
# GitHub Actions workflow
- name: Run Tests
  run: |
    pytest tests/api/
    pytest tests/unit/
    pytest tests/integration/
    python scripts/validate_database_schema.py
```

#### Test Commands
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/api/          # API endpoint tests
pytest tests/unit/         # Unit tests
pytest tests/integration/  # Integration tests
pytest tests/database/     # Database tests

# Run with coverage
pytest --cov=backend --cov-report=html

# Run performance tests
pytest tests/performance/ -m slow
```

### **Test Data Management**

#### Test Database
- **Isolated Environment**: Separate test database
- **Sample Data**: Representative test datasets
- **Clean State**: Reset between test runs
- **Realistic Scenarios**: Real-world data patterns

#### Test Data Setup
```python
# Setup test knowledge data
python setup_test_knowledge_data.py

# Load sample ontologies
python scripts/load_sample_ontologies.py --test

# Create test projects
python scripts/create_test_projects.py
```

## 📊 Test Monitoring

### **Coverage Metrics**
- **API Coverage**: 100% of endpoints tested
- **Code Coverage**: >80% line coverage target
- **Integration Coverage**: All service integrations tested
- **User Flow Coverage**: All major workflows tested

### **Quality Gates**
- **All Tests Pass**: No failing tests allowed in main
- **Performance Thresholds**: Response time limits enforced
- **Security Scans**: No high-severity vulnerabilities
- **Code Quality**: Linting and formatting checks

### **Test Reporting**
```bash
# Generate test reports
pytest --html=reports/test_results.html
pytest --cov-report=html:reports/coverage/

# Performance benchmarks
python scripts/run_performance_benchmarks.py
```

## 🔧 Test Configuration

### **Environment Variables**
```bash
# Test configuration
TESTING=true
TEST_DATABASE_URL=postgresql://test:test@localhost:5433/odras_test
TEST_QDRANT_URL=http://localhost:6334
TEST_NEO4J_URL=bolt://localhost:7688

# Test credentials
TEST_ADMIN_USERNAME=test_admin
TEST_ADMIN_PASSWORD=test_password_2024!
```

### **Test Settings**
```python
# pytest.ini configuration
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers = 
    slow: marks tests as slow
    integration: marks tests as integration tests
    api: marks tests as API tests
```

## 🛠️ Testing Tools

### **Primary Tools**
- **pytest**: Python testing framework
- **FastAPI TestClient**: API endpoint testing
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-html**: HTML test reports

### **Database Testing**
- **pytest-postgresql**: Test database management
- **alembic**: Migration testing
- **SQLAlchemy**: ORM testing utilities

### **Integration Testing**
- **requests**: HTTP client testing
- **docker-compose**: Service orchestration
- **testcontainers**: Isolated service testing

## 🚦 Test Enforcement

### **Pre-Commit Hooks**
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### **Branch Protection**
- **Required Tests**: All tests must pass before merge
- **Code Review**: Peer review required
- **Status Checks**: CI pipeline must succeed
- **Up-to-date Branch**: Must be current with main

### **Quality Standards**
- **Test Coverage**: Minimum 80% line coverage
- **Performance**: No regression in response times
- **Security**: No new vulnerabilities introduced
- **Documentation**: Tests must be documented

---

*This consolidated guide replaces multiple testing documents and serves as the single source of truth for ODRAS testing practices.*
