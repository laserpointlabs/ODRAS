# CQMT (Competency Question and Microtheory) Guide

**Version:** 2.0  
**Date:** November 2025  
**Status:** Production Implementation

## Executive Summary

The Competency Question and Microtheory (CQ/MT) Workbench is a Test-Driven Ontology Development (TDOD) tool that enables users to evaluate ontology effectiveness through executable competency questions and isolated microtheory contexts. This guide consolidates all CQMT implementation documentation, architecture decisions, and usage instructions.

**Key Concepts:**
- **Competency Questions (CQs)**: Executable specifications that define what questions the ontology should answer
- **Microtheories (MTs)**: Isolated named graph contexts containing test data for validating CQs
- **Test-Driven Development**: Define requirements (CQs) before building ontology, iterate until CQs pass
- **Dependency Tracking**: Track which MTs reference which ontology elements
- **Change Detection**: Detect when ontology changes affect MTs

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Concepts](#2-core-concepts)
3. [Implementation Phases](#3-implementation-phases)
4. [API Reference](#4-api-reference)
5. [Synchronization and Dependency Management](#5-synchronization-and-dependency-management)
6. [Versioning Strategy](#6-versioning-strategy)
7. [Usage Guide](#7-usage-guide)
8. [Architecture Assessment](#8-architecture-assessment)

---

## 1. Architecture Overview

### 1.1 System Architecture

The CQMT system follows Semantic Web best practices:

**Components:**
- **Frontend**: `frontend/cqmt-workbench.html` - Full-featured UI
- **Backend Services**:
  - `backend/services/sparql_runner.py` - SPARQL execution
  - `backend/services/cqmt_service.py` - Business logic
  - `backend/services/cqmt_dependency_tracker.py` - Dependency tracking
  - `backend/api/cqmt.py` - REST API endpoints

**Data Storage:**
- **PostgreSQL**: CQ metadata, run history, MT metadata, dependency tracking
- **Fuseki**: Microtheories as named graphs, shared ontology in TBox graphs

### 1.2 Named Graph Architecture

**Shared TBox Graphs:**
- `<http://localhost:8000/ontology/{project_id}/base>` - Read-only ontology classes

**MT ABox Graphs:**
- `<http://localhost:8000/mt/{project_id}/{slug}>` - Per-MT instance data

This architecture provides:
- Isolation between microtheories
- Shared ontology definitions
- Precise query targeting
- Test reproducibility

---

## 2. Core Concepts

### 2.1 Competency Questions (CQs)

A **Competency Question** is an executable specification with three components:

1. **Natural Language Question**: What information should be retrievable
2. **SPARQL Query**: Executable form of the question
3. **Validation Contract**: Success criteria (columns, row counts, performance)

**Example:**
```json
{
  "cq_name": "List All Aircraft",
  "problem_text": "What aircraft are defined in the system?",
  "sparql_text": "SELECT ?aircraft ?label WHERE { ?aircraft rdf:type ex:Aircraft . ?aircraft rdfs:label ?label . }",
  "contract_json": {
    "require_columns": ["aircraft", "label"],
    "min_rows": 1,
    "max_latency_ms": 1000
  },
  "status": "active"
}
```

**Key Characteristics:**
- Executable: Must be runnable against an ontology
- Validatable: Clear success/failure criteria
- Parameterizable: Can accept parameters for flexible testing
- Traceable: Linked to specific ontology requirements

### 2.2 Microtheories (MTs)

A **Microtheory** is an isolated named graph context containing test data:

**Example:**
```turtle
@prefix : <http://odras.local/onto/project123/test_ontology#> .

:aircraft1 rdf:type :Aircraft .
:aircraft1 :hasRole :Transport .
:aircraft1 :hasType "C-130" .
:aircraft1 :hasCapacity 92 .
```

**Key Characteristics:**
- Isolated: Each MT is independent
- Named: Unique IRI for precise targeting
- Clonable: Can be created by copying existing MTs
- Defaultable: One MT per project can be set as default

### 2.3 Test-Driven Workflow

**Traditional Approach (Bottom-Up):**
```
Build Ontology → Hope it meets needs → Discover gaps later → Fix
```

**CQ/MT Approach (Test-Driven):**
```
1. Define Competency Questions (requirements)
2. Create Microtheory (test environment)
3. Run CQs → They FAIL (ontology incomplete)
4. Build ontology classes/properties
5. Re-run CQs → Track progress toward PASS
6. Iterate until all CQs pass
```

---

## 3. Implementation Phases

### 3.1 Phase 1: Dependency Tracking ✅ COMPLETE

**Goal**: Track which MTs reference which ontology elements

**Database Schema:**
```sql
CREATE TABLE mt_ontology_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mt_id UUID REFERENCES microtheories(id) ON DELETE CASCADE,
    ontology_graph_iri TEXT NOT NULL,
    referenced_element_iri TEXT NOT NULL,
    element_type VARCHAR(50), -- 'Class', 'ObjectProperty', 'DatatypeProperty'
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated_at TIMESTAMPTZ,
    is_valid BOOLEAN DEFAULT TRUE,
    UNIQUE(mt_id, referenced_element_iri)
);
```

**Service Layer:**
- `CQMTDependencyTracker.extract_dependencies()` - Parse MT triples and extract referenced IRIs
- `CQMTDependencyTracker.validate_dependencies()` - Check if all dependencies still exist
- `CQMTDependencyTracker.get_affected_mts()` - Find MTs that reference changed elements

**API Endpoints:**
- `GET /api/cqmt/microtheories/{mt_id}/dependencies` - Get MT dependencies
- `GET /api/cqmt/microtheories/{mt_id}/validation` - Validate MT dependencies
- `GET /api/cqmt/ontologies/{graph_iri}/impact-analysis` - Get affected MTs

**Status**: ✅ Complete and tested

### 3.2 Phase 2: Change Detection ✅ COMPLETE

**Goal**: Detect when ontology changes affect MTs

**Implementation:**
- Hook into ontology save operation
- Detect changes (added/deleted/modified elements)
- Find affected MTs using dependency tracker
- Return change summary and affected MTs

**API Response:**
```json
{
  "success": true,
  "changes": {
    "added": ["http://.../NewClass"],
    "deleted": ["http://.../OldProperty"],
    "modified": ["http://.../UpdatedClass"]
  },
  "affected_microtheories": [
    {
      "mt_id": "abc-123",
      "mt_name": "Test MT",
      "broken_references": ["http://.../OldProperty"]
    }
  ]
}
```

**Status**: ✅ Complete and tested

### 3.3 Phase 3: Version Management (Future)

**Goal**: Track ontology versions and MT compatibility

**Planned Features:**
- Ontology versioning system
- MT version compatibility tracking
- Migration utilities
- Version rollback capabilities

**Status**: 📋 Planned

---

## 4. API Reference

### 4.1 Authentication

**Login:**
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

### 4.2 Competency Questions

**List CQs:**
```bash
GET /api/cqmt/projects/{project_id}/competency-questions
```

**Create CQ:**
```bash
POST /api/cqmt/projects/{project_id}/competency-questions
Content-Type: application/json

{
  "cq_name": "List All Aircraft",
  "problem_text": "What aircraft are defined?",
  "sparql_text": "SELECT ?aircraft WHERE { ?aircraft rdf:type ex:Aircraft . }",
  "contract_json": {
    "require_columns": ["aircraft"],
    "min_rows": 1
  }
}
```

**Run CQ:**
```bash
POST /api/cqmt/projects/{project_id}/competency-questions/{cq_id}/run
Content-Type: application/json

{
  "microtheory_id": "mt-123",
  "parameters": {}
}
```

### 4.3 Microtheories

**List MTs:**
```bash
GET /api/cqmt/projects/{project_id}/microtheories
```

**Create MT:**
```bash
POST /api/cqmt/projects/{project_id}/microtheories
Content-Type: application/json

{
  "name": "Test MT",
  "slug": "test-mt",
  "triples": [
    {
      "subject": "http://.../john",
      "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
      "object": "http://.../Person"
    }
  ]
}
```

**Get MT Dependencies:**
```bash
GET /api/cqmt/microtheories/{mt_id}/dependencies
Authorization: Bearer {token}
```

**Response:**
```json
{
  "microtheory_id": "abc-123",
  "dependencies": [
    {
      "ontology_graph_iri": "http://.../test_ontology",
      "referenced_element_iri": "http://.../Person",
      "element_type": "Class",
      "is_valid": true,
      "first_detected_at": "2025-10-23T08:30:00Z",
      "last_validated_at": "2025-10-23T08:30:00Z"
    }
  ]
}
```

**Validate MT Dependencies:**
```bash
GET /api/cqmt/microtheories/{mt_id}/validation
Authorization: Bearer {token}
```

**Response:**
```json
{
  "microtheory_id": "abc-123",
  "validation_status": "complete",
  "total_dependencies": 3,
  "valid_dependencies": 3,
  "invalid_dependencies": 0,
  "broken_references": []
}
```

### 4.4 Ontology Impact Analysis

**Get Affected MTs:**
```bash
GET /api/cqmt/ontologies/{graph_iri}/impact-analysis
Authorization: Bearer {token}
```

**Response:**
```json
{
  "ontology_graph_iri": "http://.../test_ontology",
  "affected_microtheories": [
    {
      "mt_id": "abc-123",
      "mt_name": "Test MT",
      "broken_references": ["http://.../DeletedProperty"]
    }
  ]
}
```

---

## 5. Synchronization and Dependency Management

### 5.1 The Synchronization Problem

**Problem**: When ontology elements are deleted or modified, MTs that reference them become invalid.

**Example Scenario:**
1. Create ontology with `Person` class and `hasName` property
2. Create MT that references `Person` and `hasName`
3. Delete `hasName` property from ontology
4. MT now has broken references

### 5.2 Solution: Dependency Tracking + Change Detection

**Architecture Assessment:**
- ✅ Architecture is solid (follows Semantic Web best practices)
- ✅ Named graphs for isolation
- ✅ SPARQL for queries
- ✅ Triple-based references
- ✅ Proper separation of concerns

**Missing Infrastructure:**
- ❌ Dependency tracking system (now implemented)
- ❌ Change detection mechanism (now implemented)
- ❌ Version management tooling (planned)

**Conclusion**: The architecture is correct; we needed to add standard supporting infrastructure.

### 5.3 Dependency Tracking Implementation

**Automatic Extraction:**
- Dependencies extracted when MTs are created/updated
- Parses MT triples to find referenced ontology elements
- Stores in `mt_ontology_dependencies` table

**Validation:**
- Validates dependencies against current ontology state
- Identifies broken references
- Provides validation status and broken reference list

**Impact Analysis:**
- Finds all MTs affected by ontology changes
- Returns affected MTs with broken references
- Enables proactive notification and updates

---

## 6. Versioning Strategy

### 6.1 Versioning vs Dependency Tracking

**Dependency Tracking** (Implemented):
- Tracks current state dependencies
- Validates against current ontology
- Detects when changes break references
- **Use Case**: Day-to-day development and validation

**Versioning** (Planned):
- Tracks historical ontology versions
- Enables rollback and migration
- Supports compatibility analysis
- **Use Case**: Long-term maintenance and evolution

### 6.2 Layered Approach

**Layer 1: Dependency Tracking** ✅
- Current state validation
- Change detection
- Impact analysis

**Layer 2: Version Management** 📋
- Version snapshots
- Compatibility tracking
- Migration utilities

**Layer 3: Advanced Features** 📋
- Semantic versioning
- Automated migration
- Version comparison tools

---

## 7. Usage Guide

### 7.1 Getting Started

**Access the Workbench:**
- Main ODRAS Interface: Click CQ/MT icon in left navigation
- Direct URL: `http://localhost:8000/cqmt-workbench`
- Credentials: Use ODRAS login (e.g., `das_service/das_service_2024!`)

### 7.2 Basic Workflow

**1. Create an Ontology:**
- Navigate to Project → Ontologies tab
- Create new ontology
- Add classes and properties

**2. Define Competency Questions:**
- Navigate to CQ/MT Workbench
- Create CQs that define what the ontology should answer
- Write SPARQL queries and validation contracts

**3. Create Microtheories:**
- Create MTs with test data
- Reference ontology elements in MT triples
- Dependencies automatically tracked

**4. Run CQs Against MTs:**
- Execute CQs against MTs
- Review results and validation status
- Iterate until CQs pass

**5. Monitor Dependencies:**
- Check MT dependency status
- Validate dependencies when ontology changes
- Review affected MTs from impact analysis

### 7.3 Best Practices

**Competency Questions:**
- Start with high-level questions
- Make questions specific and measurable
- Include validation contracts
- Parameterize queries for flexibility

**Microtheories:**
- Create focused MTs for specific scenarios
- Use meaningful names and slugs
- Clone MTs for variations
- Set default MT for convenience

**Dependency Management:**
- Regularly validate MT dependencies
- Review impact analysis before ontology changes
- Update MTs when ontology changes
- Use dependency tracking to prevent broken references

---

## 8. Architecture Assessment

### 8.1 Industry Standards Comparison

**Our Architecture:**
- ✅ Named graphs for isolation
- ✅ SPARQL for queries
- ✅ Triple-based references
- ✅ Proper separation of concerns

**Industry Standards** (Protege, Pellet, Enterprise Knowledge Graphs):
- ✅ Named graphs for isolation
- ✅ SPARQL for queries
- ✅ Triple-based references
- ✅ Proper separation of concerns

**Conclusion**: Our architecture matches industry standards.

### 8.2 Supporting Infrastructure

**Standard Features in Enterprise Systems:**
- Dependency tracking ✅ (Implemented)
- Change detection ✅ (Implemented)
- Version management 📋 (Planned)
- Migration tooling 📋 (Planned)

**Conclusion**: We're implementing standard infrastructure, not bandaids.

### 8.3 Key Insights

**Architecture vs Infrastructure:**
- **Architecture** (What we built): ✅ Correct
- **Infrastructure** (Supporting systems): ✅ Being added

**Solution Quality:**
- Solutions are standard industry practice
- Not bandaids or workarounds
- Completes the architecture properly

---

## Key Files

### Backend
- `backend/services/cqmt_service.py` - Core CQMT business logic
- `backend/services/sparql_runner.py` - SPARQL execution
- `backend/services/cqmt_dependency_tracker.py` - Dependency tracking
- `backend/api/cqmt.py` - REST API endpoints

### Frontend
- `frontend/cqmt-workbench.html` - Main UI

### Database
- `mt_ontology_dependencies` table - Dependency tracking
- `microtheories` table - MT metadata
- `competency_questions` table - CQ metadata

---

## Success Metrics

✅ **Phase 1 Complete**: Dependency tracking implemented and tested  
✅ **Phase 2 Complete**: Change detection implemented and tested  
📋 **Phase 3 Planned**: Version management roadmap defined  

**Architecture**: ✅ Matches industry standards  
**Implementation**: ✅ Standard infrastructure, not bandaids  
**Status**: ✅ Production-ready for Phases 1 and 2  

---

*Last Updated: November 2025*  
*Consolidated from: CQMT_IMPLEMENTATION_ROADMAP.md, CQMT_SYNC_MASTER_SUMMARY.md, CQMT_PHASE1_COMPLETE.md, CQMT_PHASE2_COMPLETE.md, CQMT_VERSIONING_STRATEGY_DISCUSSION.md, CQMT_ARCHITECTURAL_ASSESSMENT.md, and related phase documentation*

