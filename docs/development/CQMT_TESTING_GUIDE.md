# CQMT Testing Guide

**Version:** 2.0  
**Date:** November 2025  
**Status:** Production Testing Documentation

## Overview

This guide consolidates all CQMT testing documentation, including API testing examples, manual testing workflows, UI testing plans, and coverage analysis. Use this guide for comprehensive testing of CQMT features.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [API Testing](#2-api-testing)
3. [Manual Testing Workflows](#3-manual-testing-workflows)
4. [UI Testing Plan](#4-ui-testing-plan)
5. [Coverage Analysis](#5-coverage-analysis)
6. [Integration Testing](#6-integration-testing)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

### 1.1 Authentication

**Get Authentication Token:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "das_service", "password": "das_service_2024!"}'
```

**Response:**
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "user": {
    "user_id": "...",
    "username": "das_service"
  }
}
```

**Save Token:**
```bash
export TOKEN="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

### 1.2 Test Data Setup

**Required:**
- ODRAS services running (`./odras.sh start`)
- Test project created
- Test ontology with classes and properties
- Test microtheory with triples

**Test Credentials:**
- Username: `das_service`
- Password: `das_service_2024!`

---

## 2. API Testing

### 2.1 Dependency Endpoints

#### Get MT Dependencies

**Endpoint:** `GET /api/cqmt/microtheories/{mt_id}/dependencies`

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/dependencies
```

**Expected Response:**
```json
{
  "microtheory_id": "abc-123-def-456",
  "dependencies": [
    {
      "ontology_graph_iri": "http://odras.local/onto/project123/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/project123/test_ontology#Person",
      "element_type": "Class",
      "is_valid": true,
      "first_detected_at": "2025-10-23T08:30:00Z",
      "last_validated_at": "2025-10-23T08:30:00Z"
    }
  ]
}
```

**Test Cases:**
- ✅ MT with valid dependencies returns all dependencies
- ✅ MT with no dependencies returns empty array
- ✅ Invalid MT ID returns 404
- ✅ Unauthorized request returns 401

#### Validate MT Dependencies

**Endpoint:** `GET /api/cqmt/microtheories/{mt_id}/validation`

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/validation
```

**Expected Response (All Valid):**
```json
{
  "microtheory_id": "abc-123-def-456",
  "validation_status": "complete",
  "total_dependencies": 3,
  "valid_dependencies": 3,
  "invalid_dependencies": 0,
  "broken_references": []
}
```

**Expected Response (With Broken References):**
```json
{
  "microtheory_id": "abc-123-def-456",
  "validation_status": "incomplete",
  "total_dependencies": 3,
  "valid_dependencies": 2,
  "invalid_dependencies": 1,
  "broken_references": [
    {
      "element_iri": "http://odras.local/onto/project123/test_ontology#hasSpeed",
      "element_type": "DatatypeProperty",
      "reason": "Element not found in ontology"
    }
  ]
}
```

**Test Cases:**
- ✅ MT with all valid dependencies returns "complete" status
- ✅ MT with broken references returns "incomplete" status
- ✅ Broken references list includes deleted elements
- ✅ Validation updates last_validated_at timestamp

#### Get Ontology Impact Analysis

**Endpoint:** `GET /api/cqmt/ontologies/{graph_iri}/impact-analysis`

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/ontologies/http%3A%2F%2Fodras.local%2Fonto%2Fproject123%2Ftest_ontology/impact-analysis"
```

**Expected Response:**
```json
{
  "ontology_graph_iri": "http://odras.local/onto/project123/test_ontology",
  "affected_microtheories": [
    {
      "mt_id": "abc-123",
      "mt_name": "Test MT",
      "broken_references": [
        "http://odras.local/onto/project123/test_ontology#DeletedProperty"
      ]
    }
  ]
}
```

**Test Cases:**
- ✅ Ontology with no affected MTs returns empty array
- ✅ Ontology with affected MTs returns all affected MTs
- ✅ Broken references list includes all deleted elements
- ✅ Invalid graph IRI returns 404

### 2.2 Competency Question Endpoints

#### List CQs

**Endpoint:** `GET /api/cqmt/projects/{project_id}/competency-questions`

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/competency-questions
```

**Test Cases:**
- ✅ Returns list of all CQs for project
- ✅ Includes CQ metadata (name, status, contract)
- ✅ Filters by project_id correctly
- ✅ Empty project returns empty array

#### Create CQ

**Endpoint:** `POST /api/cqmt/projects/{project_id}/competency-questions`

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cq_name": "List All Aircraft",
    "problem_text": "What aircraft are defined?",
    "sparql_text": "SELECT ?aircraft WHERE { ?aircraft rdf:type ex:Aircraft . }",
    "contract_json": {
      "require_columns": ["aircraft"],
      "min_rows": 1
    }
  }' \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/competency-questions
```

**Test Cases:**
- ✅ Valid CQ creates successfully
- ✅ Invalid SPARQL returns validation error
- ✅ Missing required fields returns 400
- ✅ Duplicate CQ name returns conflict error

#### Run CQ

**Endpoint:** `POST /api/cqmt/projects/{project_id}/competency-questions/{cq_id}/run`

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "microtheory_id": "mt-123",
    "parameters": {}
  }' \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/competency-questions/CQ_ID/run
```

**Test Cases:**
- ✅ Valid CQ execution returns results
- ✅ Results match contract requirements
- ✅ Invalid MT ID returns 404
- ✅ SPARQL errors return error details

### 2.3 Microtheory Endpoints

#### List MTs

**Endpoint:** `GET /api/cqmt/projects/{project_id}/microtheories`

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/microtheories
```

**Test Cases:**
- ✅ Returns list of all MTs for project
- ✅ Includes MT metadata (name, slug, dependency status)
- ✅ Filters by project_id correctly

#### Create MT

**Endpoint:** `POST /api/cqmt/projects/{project_id}/microtheories`

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test MT",
    "slug": "test-mt",
    "triples": [
      {
        "subject": "http://.../john",
        "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "object": "http://.../Person"
      }
    ]
  }' \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/microtheories
```

**Test Cases:**
- ✅ Valid MT creates successfully
- ✅ Dependencies automatically extracted
- ✅ Invalid triples return validation error
- ✅ Duplicate slug returns conflict error

---

## 3. Manual Testing Workflows

### 3.1 Dependency Tracking Workflow

**Step 1: Create an Ontology**
1. Navigate to Project → Ontologies tab
2. Create new ontology
3. Add classes and properties:
```turtle
@prefix : <http://odras.local/onto/YOUR_PROJECT/test_ontology#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Person a owl:Class ;
    rdfs:label "Person" .

:Vehicle a owl:Class ;
    rdfs:label "Vehicle" .

:hasName a owl:DatatypeProperty ;
    rdfs:label "has name" ;
    rdfs:domain :Person ;
    rdfs:range rdfs:Literal .
```
4. Save the ontology

**Step 2: Create a Microtheory**
1. Navigate to Project → CQ/MT Workbench
2. Create new microtheory: "Test MT"
3. Add triples that reference the ontology:
```json
[
  {
    "subject": "http://odras.local/onto/YOUR_PROJECT/test_ontology#john",
    "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "object": "http://odras.local/onto/YOUR_PROJECT/test_ontology#Person"
  },
  {
    "subject": "http://odras.local/onto/YOUR_PROJECT/test_ontology#john",
    "predicate": "http://odras.local/onto/YOUR_PROJECT/test_ontology#hasName",
    "object": "John Doe"
  }
]
```
4. Save the microtheory
5. **Result**: Dependencies automatically tracked ✅

**Step 3: Check Dependencies**
1. Get the MT ID from the UI
2. Call API: `GET /api/cqmt/microtheories/{mt_id}/dependencies`
3. **Expected**: Returns Person class and hasName property dependencies

**Step 4: Validate Dependencies**
1. Call API: `GET /api/cqmt/microtheories/{mt_id}/validation`
2. **Expected**: Returns "complete" status with all dependencies valid

**Step 5: Delete Ontology Element**
1. Edit ontology and delete `hasName` property
2. Save ontology
3. **Result**: Change detection identifies affected MTs

**Step 6: Re-validate Dependencies**
1. Call API: `GET /api/cqmt/microtheories/{mt_id}/validation`
2. **Expected**: Returns "incomplete" status with broken reference to `hasName`

### 3.2 Change Detection Workflow

**Step 1: Create Baseline**
1. Create ontology with classes and properties
2. Create MTs that reference these elements
3. Verify all dependencies are valid

**Step 2: Make Ontology Changes**
1. Edit ontology:
   - Add new class: `NewClass`
   - Delete property: `OldProperty`
   - Modify class: `UpdatedClass`
2. Save ontology

**Step 3: Review Change Detection**
1. API response includes:
   - `changes.added`: ["NewClass"]
   - `changes.deleted`: ["OldProperty"]
   - `changes.modified`: ["UpdatedClass"]
   - `affected_microtheories`: List of MTs with broken references

**Step 4: Update Affected MTs**
1. Review affected MTs list
2. Update MTs to remove references to deleted elements
3. Re-validate dependencies

---

## 4. UI Testing Plan

### 4.1 CQ/MT Workbench UI

**Test Areas:**
- ✅ CQ list display and filtering
- ✅ CQ creation and editing forms
- ✅ MT list display and filtering
- ✅ MT creation and editing forms
- ✅ CQ execution panel
- ✅ Results display and validation
- ✅ Dependency status indicators
- ✅ Validation status badges

**Test Cases:**

**CQ Management:**
- Create new CQ with valid SPARQL
- Edit existing CQ
- Delete CQ
- Run CQ against MT
- View CQ execution results
- Validate CQ contract requirements

**MT Management:**
- Create new MT with triples
- Edit existing MT
- Clone MT
- Set default MT
- View MT dependencies
- Validate MT dependencies

**Dependency Display:**
- Dependency status badge on MT list
- Dependency panel in MT details
- Broken reference highlighting
- Validation status indicators

### 4.2 Integration Points

**Ontology Workbench:**
- Save ontology triggers change detection
- Affected MTs notification
- Impact analysis display

**Project Navigation:**
- CQ/MT icon in left navigation
- Project context switching
- Workbench access control

---

## 5. Coverage Analysis

### 5.1 Test Coverage Goals

**API Endpoints:**
- ✅ All dependency endpoints tested
- ✅ All CQ endpoints tested
- ✅ All MT endpoints tested
- ✅ Error cases covered
- ✅ Authentication/authorization tested

**Business Logic:**
- ✅ Dependency extraction logic
- ✅ Validation logic
- ✅ Change detection logic
- ✅ Impact analysis logic

**UI Components:**
- ✅ CQ management UI
- ✅ MT management UI
- ✅ Dependency display UI
- ✅ Validation status UI

### 5.2 Coverage Metrics

**Phase 1 (Dependency Tracking):**
- Unit tests: ✅ Complete
- Integration tests: ✅ Complete
- API tests: ✅ Complete
- Manual tests: ✅ Complete

**Phase 2 (Change Detection):**
- Unit tests: ✅ Complete
- Integration tests: ✅ Complete
- API tests: ✅ Complete
- Manual tests: ✅ Complete

**Overall Coverage:**
- API endpoints: 100%
- Core services: 95%+
- UI components: 90%+

---

## 6. Integration Testing

### 6.1 End-to-End Workflow

**Test Scenario: Complete CQMT Workflow**

1. **Setup:**
   - Create test project
   - Create test ontology
   - Create test CQs
   - Create test MTs

2. **Dependency Tracking:**
   - Verify dependencies extracted
   - Verify dependencies valid
   - Verify dependency display

3. **Change Detection:**
   - Modify ontology
   - Verify change detection
   - Verify affected MTs identified

4. **Validation:**
   - Re-validate dependencies
   - Verify broken references detected
   - Verify validation status updated

5. **CQ Execution:**
   - Run CQs against MTs
   - Verify results match contracts
   - Verify execution history recorded

### 6.2 Integration Points

**With Ontology Workbench:**
- Ontology save triggers change detection
- Change detection returns affected MTs
- UI displays impact analysis

**With Authentication:**
- All endpoints require authentication
- Project access control enforced
- User permissions validated

**With Database:**
- Dependencies stored correctly
- Validation queries work
- Impact analysis queries efficient

---

## 7. Troubleshooting

### 7.1 Common Issues

**Issue: Dependencies Not Extracted**
- **Cause**: MT triples don't reference ontology elements
- **Solution**: Verify MT triples use correct IRIs

**Issue: Validation Always Returns Invalid**
- **Cause**: Ontology graph IRI mismatch
- **Solution**: Verify ontology graph IRI matches dependency records

**Issue: Change Detection Not Working**
- **Cause**: Ontology save hook not triggered
- **Solution**: Verify ontology save endpoint calls change detection

**Issue: API Returns 401 Unauthorized**
- **Cause**: Token expired or invalid
- **Solution**: Re-authenticate and get new token

### 7.2 Debug Commands

**Check Dependencies:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/{mt_id}/dependencies | jq
```

**Validate Dependencies:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/{mt_id}/validation | jq
```

**Check Impact Analysis:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/ontologies/{graph_iri}/impact-analysis" | jq
```

---

## Test Data

### Sample Ontology
```turtle
@prefix : <http://odras.local/onto/test/project#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Person a owl:Class ;
    rdfs:label "Person" .

:Vehicle a owl:Class ;
    rdfs:label "Vehicle" .

:hasName a owl:DatatypeProperty ;
    rdfs:domain :Person ;
    rdfs:range rdfs:Literal .
```

### Sample Microtheory
```json
[
  {
    "subject": "http://odras.local/onto/test/project#john",
    "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "object": "http://odras.local/onto/test/project#Person"
  },
  {
    "subject": "http://odras.local/onto/test/project#john",
    "predicate": "http://odras.local/onto/test/project#hasName",
    "object": "John Doe"
  }
]
```

### Sample Competency Question
```json
{
  "cq_name": "List All Persons",
  "problem_text": "What persons are defined in the system?",
  "sparql_text": "SELECT ?person ?name WHERE { ?person rdf:type :Person . ?person :hasName ?name . }",
  "contract_json": {
    "require_columns": ["person", "name"],
    "min_rows": 1
  }
}
```

---

*Last Updated: November 2025*  
*Consolidated from: CQMT_API_TESTING_EXAMPLES.md, CQMT_MANUAL_TESTING_GUIDE.md, CQMT_UI_TEST_PLAN.md, CQMT_COVERAGE_ANALYSIS_PLAN.md, and related testing documentation*
