# Ontology API Design

## Overview

ODRAS uses a **two-router design** for ontology management, separating registry operations from ontology operations. This is an intentional architectural decision.

## Router Structure

### 1. Ontology Registry Router (`/api/ontologies`)
**File**: `backend/api/ontology_registry.py`  
**Prefix**: `/api/ontologies` (plural)  
**Purpose**: Manage ontology registry (which ontologies exist in projects)

**Endpoints**:
- `GET /api/ontologies` - List ontologies in project
- `POST /api/ontologies` - Create new ontology
- `DELETE /api/ontologies` - Delete ontology
- `PUT /api/ontologies/label` - Update ontology label
- `GET /api/ontologies/reference` - List reference ontologies
- `PUT /api/ontologies/reference` - Toggle reference status
- `POST /api/ontologies/import-url` - Import ontology from URL

**Use Case**: Project-level ontology lifecycle management

### 2. Ontology Operations Router (`/api/ontology/`)
**File**: `backend/api/ontology.py`  
**Prefix**: `/api/ontology/` (singular)  
**Purpose**: Operations on a single ontology (classes, properties, content)

**Key Endpoints**:
- `GET /api/ontology/` - Get ontology details (JSON format)
- `POST /api/ontology/classes` - Add class to ontology
- `POST /api/ontology/properties` - Add property to ontology
- `POST /api/ontology/save` - Save turtle content
- `POST /api/ontology/sparql` - Execute SPARQL query
- `GET /api/ontology/statistics` - Get ontology statistics
- `GET /api/ontology/layout` - Get visualization layout
- And 19 more endpoints for detailed operations

**Use Case**: Content management and operations on ontology structure

## Design Rationale

**Separation of Concerns**:
- Registry operations = Project management (CRUD on ontology entities)
- Ontology operations = Content management (classes, properties, queries)

**Benefits**:
- Clear API boundaries
- Easier to understand and maintain
- Supports different authentication/authorization needs
- Better organization of code

## Status

✅ **Consolidation Complete**: All endpoints moved from `main.py` to routers  
✅ **No Conflicts**: No duplicate endpoints  
✅ **Registered**: Both routers registered in `backend/startup/routers.py`

## Migration Notes

- Previously, some endpoints were in `main.py` (lines 893-1910)
- All endpoints now consolidated into appropriate routers
- No breaking changes - endpoints maintain same paths

---

*Last Updated: 2025-01-XX*  
*Status: Design Documented and Verified*
