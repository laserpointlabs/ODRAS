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

## 🧪 RAG System Testing

### **RAG Testing Framework**

**Test Script:** `scripts/single_query_test.py`
**Purpose:** Comprehensive RAG functionality validation with manual evaluation

**Features:**
- Creates project and uploads test documents automatically
- Tests multiple query types including UAS specifications
- Shows actual outputs for manual quality assessment
- Validates chunk counts and source attribution
- Provides detailed debugging information

**Test Queries:**
1. "What are the UAS requirements for disaster response?"
2. "Please list the names only of the UAS we can select from in the specification"
3. "What are the different types of UAS platforms available?"
4. "Which UAS has the longest endurance?"
5. "What is the cost range for UAS platforms?"

**Usage:**
```bash
cd /home/jdehart/working/ODRAS
python scripts/single_query_test.py
```

### **RAG Validation Criteria**

**Success Indicators:**
- ✅ All 9 UAS platforms returned for names query
- ✅ Correct source titles (not "Unknown Document")
- ✅ Comprehensive responses with specific details
- ✅ Multiple chunks retrieved (9+ instead of 3)
- ✅ Relevance scores above 0.3

**Failure Indicators:**
- ❌ Only 2-3 UAS platforms returned
- ❌ "Unknown Document" in sources
- ❌ Generic "I don't have that information" responses
- ❌ Low chunk counts (3 or fewer)

### **RAG Performance Metrics**

**Key Metrics to Monitor:**
- Chunk retrieval count per query
- Source attribution accuracy
- Response quality (manual evaluation)
- Query response time
- LLM context utilization

**Expected Performance:**
- UAS names query: 8-9 platforms returned
- Chunk count: 9+ chunks per query
- Source attribution: 100% correct titles
- Response time: < 10 seconds per query

### **RAG Troubleshooting**

**Common Issues:**
1. **Low chunk counts**: Check similarity thresholds and chunk limits
2. **Missing sources**: Verify asset_id and document_type in chunk payloads
3. **Incomplete responses**: Check deduplication logic and context limits
4. **Poor relevance**: Adjust similarity thresholds and embedding models

**Debug Information:**
- Application logs: `/tmp/odras_app.log`
- RAG debug messages: Look for `VECTOR_QUERY_DEBUG`, `RAG_FILTER_DEBUG`
- Chunk content: Use Qdrant API to inspect chunk payloads

**Related Documentation:**
- **RAG Stabilization Guide:** `docs/development/RAG_STABILIZATION_GUIDE.md`
- **SQL-First RAG:** `docs/sql_first_rag_implementation.md`

## 📋 Daily Testing Workflow

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

### **Pytest Command Reference**

**Essential Flags:**
```bash
-v, --verbose      # Show detailed test output
-s, --no-capture   # Show print() statements in real-time
--tb=short         # Shorter error tracebacks
--tb=long          # Full error tracebacks
-x                 # Stop on first failure
```

**Common Combinations:**
```bash
# Development workflow
pytest tests/api/test_full_use_case.py -v -s --tb=short

# Debugging failures
pytest tests/api/test_project_crud.py -v -s --tb=long -x

# Quick status check
pytest tests/api/test_full_use_case.py --tb=short

# Run specific test method
pytest tests/api/test_full_use_case.py::TestFullODRASUseCase::test_complete_odras_workflow -v
```

### **Prerequisites**

**Services Must Be Running:**
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

### **Test Results Interpretation**

**✅ Success Indicators:**
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

**⚠️ Partial Success (Expected):**
Some admin endpoints may not be implemented:
```bash
⚠️ Prefix creation not available (status: 404)
⚠️ Domain creation not available (status: 404)
⚠️ Namespace creation not available (status: 404)
```
This is **normal** - not all admin features are implemented yet.

**❌ Failure Scenarios:**

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

### **Development Workflow**

**Recommended Testing Sequence:**

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

**Integration with Development:**
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

---

*This consolidated guide replaces multiple testing documents and serves as the single source of truth for ODRAS testing practices.*
