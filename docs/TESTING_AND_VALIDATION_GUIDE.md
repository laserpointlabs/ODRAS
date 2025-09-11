# ODRAS Testing and Validation Guide

## 🎯 Overview

This document provides comprehensive testing and validation strategies for the ODRAS (Ontology-Driven Requirements Analysis System) tool. It covers all API endpoints, integration testing, and pre-merge validation procedures to ensure system reliability and functionality.

## 📋 Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [API Testing Strategy](#api-testing-strategy)
3. [Module-Specific Testing](#module-specific-testing)
4. [Integration Testing](#integration-testing)
5. [Pre-Merge Validation](#pre-merge-validation)
6. [Automated Testing Pipeline](#automated-testing-pipeline)
7. [Manual Testing Procedures](#manual-testing-procedures)
8. [Performance Testing](#performance-testing)
9. [Security Testing](#security-testing)
10. [Test Data Management](#test-data-management)

## 🧪 Testing Philosophy

### Core Principles
- **API-First Testing**: Every API endpoint must have comprehensive test coverage
- **Integration Validation**: End-to-end workflow testing for critical paths
- **Regression Prevention**: Automated tests prevent breaking changes
- **Performance Monitoring**: Response time and resource usage validation
- **Security Verification**: Authentication, authorization, and data protection testing

### Testing Levels
1. **Unit Tests**: Individual function and class testing
2. **Integration Tests**: API endpoint and service interaction testing
3. **End-to-End Tests**: Complete workflow validation
4. **Performance Tests**: Load and stress testing
5. **Security Tests**: Vulnerability and access control testing

## 🔌 API Testing Strategy

### Current API Coverage Analysis

Based on the codebase analysis, ODRAS has **131 API endpoints** across 8 major modules:

#### Core Modules and Endpoint Counts:
- **Authentication & Projects**: 15 endpoints
- **File Management**: 15 endpoints  
- **Ontology Management**: 12 endpoints
- **Knowledge Management**: 12 endpoints
- **Workflow Management**: 3 endpoints
- **Namespace Management**: 8 endpoints (simple) + 12 endpoints (advanced)
- **Domain Management**: 5 endpoints
- **Prefix Management**: 4 endpoints
- **Embedding Models**: 7 endpoints
- **Persona & Prompt Management**: 8 endpoints
- **User Tasks & Review**: 6 endpoints

### Testing Framework Setup

```python
# Recommended testing stack
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0  # For async API testing
pytest-mock>=3.10.0
```

## 📊 Module-Specific Testing

### 1. Authentication & Project Management

**Endpoints to Test:**
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `PUT /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`

**Test Scenarios:**
```python
# Authentication Tests
async def test_login_success():
    """Test successful user login with valid credentials"""
    
async def test_login_invalid_credentials():
    """Test login failure with invalid credentials"""
    
async def test_token_expiration():
    """Test token expiration and refresh mechanism"""
    
async def test_logout():
    """Test user logout and token invalidation"""

# Project Management Tests
async def test_create_project():
    """Test project creation with valid data"""
    
async def test_project_access_control():
    """Test user can only access their own projects"""
    
async def test_project_archival():
    """Test project archival and restoration"""
```

### 2. File Management

**Endpoints to Test:**
- `POST /api/files/upload`
- `GET /api/files/`
- `GET /api/files/{file_id}/download`
- `GET /api/files/{file_id}/url`
- `DELETE /api/files/{file_id}`
- `PUT /api/files/{file_id}/tags`
- `POST /api/files/batch/upload`
- `POST /api/files/{file_id}/process`

**Test Scenarios:**
```python
# File Upload Tests
async def test_single_file_upload():
    """Test uploading a single file with metadata"""
    
async def test_batch_file_upload():
    """Test uploading multiple files simultaneously"""
    
async def test_file_type_validation():
    """Test file type restrictions and validation"""
    
async def test_large_file_handling():
    """Test handling of large files (>100MB)"""

# File Management Tests
async def test_file_download():
    """Test file download with proper authentication"""
    
async def test_file_deletion():
    """Test file deletion and cleanup"""
    
async def test_file_visibility_controls():
    """Test admin-controlled file visibility"""
```

### 3. Ontology Management

**Endpoints to Test:**
- `GET /api/ontology/`
- `PUT /api/ontology/`
- `POST /api/ontology/classes`
- `POST /api/ontology/properties`
- `DELETE /api/ontology/classes/{class_name}`
- `DELETE /api/ontology/properties/{property_name}`
- `POST /api/ontology/validate`
- `POST /api/ontology/import`
- `GET /api/ontology/export/{format}`

**Test Scenarios:**
```python
# Ontology CRUD Tests
async def test_ontology_retrieval():
    """Test ontology data retrieval"""
    
async def test_class_creation():
    """Test adding new ontology classes"""
    
async def test_property_creation():
    """Test adding new ontology properties"""
    
async def test_ontology_validation():
    """Test ontology structure validation"""

# Import/Export Tests
async def test_ontology_import():
    """Test importing ontology from various formats"""
    
async def test_ontology_export():
    """Test exporting ontology to different formats"""
```

### 4. Knowledge Management

**Endpoints to Test:**
- `GET /api/knowledge/assets`
- `POST /api/knowledge/assets`
- `GET /api/knowledge/assets/{asset_id}`
- `PUT /api/knowledge/assets/{asset_id}`
- `DELETE /api/knowledge/assets/{asset_id}`
- `POST /api/knowledge/search`
- `POST /api/knowledge/query`
- `POST /api/knowledge/search/semantic`

**Test Scenarios:**
```python
# Knowledge Asset Tests
async def test_knowledge_asset_creation():
    """Test creating knowledge assets"""
    
async def test_semantic_search():
    """Test semantic search functionality"""
    
async def test_rag_query():
    """Test RAG (Retrieval-Augmented Generation) queries"""
    
async def test_knowledge_asset_processing():
    """Test asset processing and embedding generation"""
```

### 5. Workflow Management

**Endpoints to Test:**
- `POST /api/workflows/start`
- `POST /api/workflows/rag-query`
- `GET /api/workflows/rag-query/{process_instance_id}/status`

**Test Scenarios:**
```python
# Workflow Tests
async def test_workflow_start():
    """Test starting BPMN workflows"""
    
async def test_workflow_status():
    """Test workflow status monitoring"""
    
async def test_rag_workflow():
    """Test RAG query workflow execution"""
```

## 🔗 Integration Testing

### End-to-End Workflow Tests

```python
async def test_complete_document_processing_workflow():
    """Test complete workflow: upload → process → extract → review"""
    
    # 1. Create project
    project = await create_test_project()
    
    # 2. Upload document
    file_id = await upload_test_document(project["id"])
    
    # 3. Start processing workflow
    workflow_id = await start_processing_workflow(project["id"], [file_id])
    
    # 4. Monitor workflow status
    status = await monitor_workflow_completion(workflow_id)
    
    # 5. Verify results
    assert status == "completed"
    requirements = await get_extracted_requirements(workflow_id)
    assert len(requirements) > 0

async def test_ontology_workflow_integration():
    """Test ontology creation and knowledge asset integration"""
    
    # 1. Create ontology classes
    await create_ontology_classes()
    
    # 2. Create knowledge assets
    asset_id = await create_knowledge_asset()
    
    # 3. Verify ontology integration
    integration_status = await verify_ontology_integration(asset_id)
    assert integration_status == "success"
```

### Cross-Module Integration Tests

```python
async def test_file_to_knowledge_pipeline():
    """Test file upload → processing → knowledge asset creation"""
    
async def test_ontology_to_workflow_integration():
    """Test ontology changes affecting workflow behavior"""
    
async def test_namespace_to_ontology_consistency():
    """Test namespace changes maintaining ontology consistency"""
```

## ✅ Pre-Merge Validation

### Mandatory Pre-Merge Checklist

#### 1. Code Quality Checks
- [ ] **Linting**: All code passes `flake8` and `black` formatting
- [ ] **Type Hints**: All functions have proper type annotations
- [ ] **Documentation**: All new functions have docstrings
- [ ] **Security**: No hardcoded secrets or credentials

#### 2. Test Coverage Requirements
- [ ] **Unit Tests**: 90%+ code coverage for new/modified code
- [ ] **API Tests**: All new endpoints have comprehensive tests
- [ ] **Integration Tests**: Critical workflows have end-to-end tests
- [ ] **Regression Tests**: Existing functionality still works

#### 3. API Validation
- [ ] **Response Formats**: All endpoints return expected JSON schemas
- [ ] **Error Handling**: Proper HTTP status codes and error messages
- [ ] **Authentication**: All protected endpoints require valid tokens
- [ ] **Input Validation**: All inputs are properly validated

#### 4. Database Integrity
- [ ] **Schema Changes**: Database migrations are tested
- [ ] **Data Consistency**: Foreign key constraints are maintained
- [ ] **Performance**: No N+1 queries or performance regressions

#### 5. Frontend Integration
- [ ] **UI Components**: New UI elements render correctly
- [ ] **API Integration**: Frontend correctly calls backend APIs
- [ ] **Error States**: Error handling displays user-friendly messages
- [ ] **Responsive Design**: UI works on different screen sizes

### Automated Pre-Merge Script

```bash
#!/bin/bash
# pre-merge-validation.sh

echo "🔍 Starting ODRAS Pre-Merge Validation..."

# 1. Code Quality
echo "📝 Running code quality checks..."
flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics
black --check backend/ scripts/

# 2. Test Execution
echo "🧪 Running test suite..."
pytest tests/ -v --cov=backend --cov-report=html --cov-report=term

# 3. API Validation
echo "🔌 Validating API endpoints..."
python scripts/validate_all_endpoints.py

# 4. Integration Tests
echo "🔗 Running integration tests..."
pytest tests/integration/ -v

# 5. Performance Tests
echo "⚡ Running performance tests..."
pytest tests/performance/ -v

# 6. Security Tests
echo "🔒 Running security tests..."
bandit -r backend/ -ll

echo "✅ Pre-merge validation complete!"
```

## 🤖 Automated Testing Pipeline

### CI/CD Pipeline Configuration

```yaml
# .github/workflows/comprehensive-testing.yml
name: Comprehensive Testing Pipeline

on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  api-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run API tests
        run: pytest tests/api/ -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, api-tests]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: pytest tests/integration/ -v

  performance-tests:
    runs-on: ubuntu-latest
    needs: [integration-tests]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run performance tests
        run: pytest tests/performance/ -v
```

### Test Organization Structure

```
tests/
├── unit/
│   ├── test_auth.py
│   ├── test_file_management.py
│   ├── test_ontology.py
│   ├── test_knowledge.py
│   └── test_workflows.py
├── api/
│   ├── test_auth_endpoints.py
│   ├── test_file_endpoints.py
│   ├── test_ontology_endpoints.py
│   ├── test_knowledge_endpoints.py
│   └── test_workflow_endpoints.py
├── integration/
│   ├── test_document_processing_workflow.py
│   ├── test_ontology_knowledge_integration.py
│   └── test_cross_module_integration.py
├── performance/
│   ├── test_api_response_times.py
│   ├── test_large_file_handling.py
│   └── test_concurrent_users.py
├── security/
│   ├── test_authentication.py
│   ├── test_authorization.py
│   └── test_input_validation.py
└── fixtures/
    ├── test_data.json
    ├── sample_ontologies/
    └── sample_documents/
```

## 🧪 Manual Testing Procedures

### 1. User Interface Testing

#### File Management Workbench
```bash
# Test file upload functionality
1. Navigate to Files workbench
2. Upload various file types (PDF, DOCX, TXT, CSV)
3. Verify file appears in library
4. Test file preview functionality
5. Test file deletion
6. Test batch upload
```

#### Ontology Editor
```bash
# Test ontology editing
1. Navigate to Ontology Editor
2. Create new classes and properties
3. Test JSON editing interface
4. Verify Fuseki synchronization
5. Test import/export functionality
```

#### Knowledge Management
```bash
# Test knowledge asset management
1. Navigate to Knowledge workbench
2. Create knowledge assets
3. Test semantic search
4. Test RAG queries
5. Verify asset processing
```

### 2. Workflow Testing

#### Document Processing Workflow
```bash
# Test complete document processing
1. Upload a requirements document
2. Start ingestion workflow
3. Monitor workflow progress
4. Review extracted requirements
5. Approve or rerun extraction
6. Verify knowledge asset creation
```

### 3. Cross-Browser Testing

Test on multiple browsers:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## ⚡ Performance Testing

### Response Time Requirements

| Endpoint Category | Max Response Time |
|------------------|-------------------|
| Authentication | 200ms |
| File Upload | 5s (per MB) |
| File Download | 1s (per MB) |
| Ontology Operations | 500ms |
| Knowledge Search | 2s |
| RAG Queries | 10s |

### Load Testing Scenarios

```python
# Performance test example
async def test_concurrent_file_uploads():
    """Test system under concurrent file upload load"""
    
    async def upload_file(client, file_data):
        return await client.post("/api/files/upload", files=file_data)
    
    # Simulate 10 concurrent uploads
    tasks = [upload_file(client, test_file) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Verify all uploads succeeded
    for result in results:
        assert result.status_code == 200
        assert result.json()["success"] is True
```

## 🔒 Security Testing

### Authentication & Authorization Tests

```python
async def test_unauthorized_access():
    """Test that protected endpoints reject unauthorized requests"""
    
    # Test without token
    response = await client.get("/api/projects")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = await client.get("/api/projects", headers=headers)
    assert response.status_code == 401

async def test_user_isolation():
    """Test that users can only access their own data"""
    
    # Create two users
    user1_token = await login_user("user1")
    user2_token = await login_user("user2")
    
    # User1 creates a project
    project = await create_project(user1_token, "User1 Project")
    
    # User2 tries to access User1's project
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = await client.get(f"/api/projects/{project['id']}", headers=headers)
    assert response.status_code == 403
```

### Input Validation Tests

```python
async def test_sql_injection_prevention():
    """Test that SQL injection attempts are blocked"""
    
    malicious_input = "'; DROP TABLE projects; --"
    response = await client.post("/api/projects", 
                                json={"name": malicious_input})
    # Should not cause database error
    assert response.status_code in [400, 422]

async def test_xss_prevention():
    """Test that XSS attempts are sanitized"""
    
    xss_payload = "<script>alert('xss')</script>"
    response = await client.post("/api/projects",
                                json={"name": xss_payload})
    # Should sanitize the input
    assert "<script>" not in response.json()["project"]["name"]
```

## 📊 Test Data Management

### Test Data Strategy

```python
# test_data/fixtures.py
class TestDataManager:
    def __init__(self):
        self.sample_documents = {
            "requirements_doc": "test_data/sample_requirements.pdf",
            "technical_spec": "test_data/sample_spec.docx",
            "csv_data": "test_data/sample_data.csv"
        }
        
        self.sample_ontologies = {
            "base_ontology": "test_data/base_ontology.ttl",
            "extended_ontology": "test_data/extended_ontology.ttl"
        }
        
        self.test_users = {
            "admin": {"username": "admin", "is_admin": True},
            "user": {"username": "testuser", "is_admin": False}
        }
    
    async def setup_test_environment(self):
        """Set up clean test environment"""
        await self.clean_database()
        await self.create_test_users()
        await self.load_sample_data()
    
    async def cleanup_test_environment(self):
        """Clean up after tests"""
        await self.clean_database()
        await self.remove_test_files()
```

### Database Testing

```python
# tests/database/test_database_integrity.py
async def test_foreign_key_constraints():
    """Test that foreign key constraints are enforced"""
    
    # Try to create a project with invalid user_id
    response = await client.post("/api/projects",
                                json={"name": "Test Project", "user_id": "invalid"})
    assert response.status_code == 400

async def test_cascade_deletion():
    """Test that cascade deletions work correctly"""
    
    # Create project with files
    project = await create_test_project()
    file_id = await upload_test_file(project["id"])
    
    # Delete project
    await client.delete(f"/api/projects/{project['id']}")
    
    # Verify file is also deleted
    response = await client.get(f"/api/files/{file_id}")
    assert response.status_code == 404
```

## 📈 Monitoring and Metrics

### Test Metrics to Track

1. **Test Coverage**: Maintain 90%+ code coverage
2. **Test Execution Time**: Keep full test suite under 10 minutes
3. **API Response Times**: Monitor 95th percentile response times
4. **Error Rates**: Track test failure rates and flaky tests
5. **Performance Regression**: Monitor for performance degradation

### Continuous Monitoring

```python
# monitoring/test_metrics.py
class TestMetrics:
    def __init__(self):
        self.metrics = {
            "test_coverage": 0,
            "execution_time": 0,
            "api_response_times": {},
            "error_rate": 0
        }
    
    def record_test_execution(self, test_name, duration, status):
        """Record individual test execution metrics"""
        pass
    
    def record_api_response_time(self, endpoint, response_time):
        """Record API response time metrics"""
        pass
    
    def generate_report(self):
        """Generate comprehensive test metrics report"""
        pass
```

## 🚀 Best Practices for Testing

### 1. Test Naming Conventions
```python
# Good test names
def test_user_login_with_valid_credentials_returns_success():
def test_file_upload_with_invalid_type_returns_error():
def test_ontology_class_creation_updates_fuseki_server():

# Bad test names
def test_login():
def test_upload():
def test_ontology():
```

### 2. Test Organization
```python
# Group related tests in classes
class TestFileManagement:
    async def test_file_upload_success(self):
        pass
    
    async def test_file_upload_failure(self):
        pass
    
    async def test_file_download(self):
        pass
```

### 3. Test Data Management
```python
# Use fixtures for reusable test data
@pytest.fixture
async def test_project():
    """Create a test project for use in multiple tests"""
    return await create_test_project()

@pytest.fixture
async def authenticated_client():
    """Create an authenticated HTTP client"""
    client = AsyncClient(app=app, base_url="http://test")
    token = await login_test_user(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

### 4. Error Testing
```python
# Test both success and failure scenarios
async def test_file_upload_success():
    """Test successful file upload"""
    response = await client.post("/api/files/upload", files=test_file)
    assert response.status_code == 200
    assert response.json()["success"] is True

async def test_file_upload_invalid_type():
    """Test file upload with invalid file type"""
    response = await client.post("/api/files/upload", files=invalid_file)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["error"]
```

## 📋 Testing Checklist Template

### Before Each Feature Branch Merge

- [ ] **Code Quality**
  - [ ] All code passes linting (flake8, black)
  - [ ] Type hints are complete and accurate
  - [ ] Documentation is updated
  - [ ] No hardcoded secrets or credentials

- [ ] **Unit Tests**
  - [ ] New functions have unit tests
  - [ ] Test coverage is 90%+ for new code
  - [ ] All tests pass locally
  - [ ] Edge cases are covered

- [ ] **API Tests**
  - [ ] All new endpoints have comprehensive tests
  - [ ] Request/response schemas are validated
  - [ ] Error cases are tested
  - [ ] Authentication/authorization is tested

- [ ] **Integration Tests**
  - [ ] End-to-end workflows are tested
  - [ ] Cross-module interactions work
  - [ ] Database integrity is maintained
  - [ ] External service integrations work

- [ ] **Performance Tests**
  - [ ] Response times meet requirements
  - [ ] No performance regressions
  - [ ] Memory usage is reasonable
  - [ ] Concurrent operations work correctly

- [ ] **Security Tests**
  - [ ] Authentication is properly enforced
  - [ ] Authorization works correctly
  - [ ] Input validation prevents attacks
  - [ ] No sensitive data is exposed

- [ ] **Manual Testing**
  - [ ] UI components work correctly
  - [ ] User workflows are intuitive
  - [ ] Error messages are helpful
  - [ ] Cross-browser compatibility

## 🎯 Conclusion

This comprehensive testing and validation guide ensures that ODRAS maintains high quality and reliability. By following these procedures, we can:

1. **Prevent Regressions**: Catch breaking changes before they reach production
2. **Ensure Quality**: Maintain high code quality and user experience
3. **Validate Integration**: Ensure all components work together correctly
4. **Monitor Performance**: Track and maintain system performance
5. **Secure the System**: Protect against common security vulnerabilities

The key to successful testing is **automation** and **consistency**. Every feature branch should go through the same rigorous testing process before being merged into the main branch.

Remember: **"If it's not tested, it's broken."** - Every line of code should have corresponding tests to ensure the system works as expected.

