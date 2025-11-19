# Individuals Creation Guide

**Version:** 2.0  
**Date:** November 2025  
**Status:** Implementation Guide

## Overview

This guide consolidates all documentation related to individuals creation in the ODRAS ontology workbench, including requirements analysis, architectural decisions, design discussions, and implementation planning.

---

## Table of Contents

1. [Requirements Summary](#1-requirements-summary)
2. [Architecture Analysis](#2-architecture-analysis)
3. [Design Decisions](#3-design-decisions)
4. [Implementation Plan](#4-implementation-plan)
5. [Impact Analysis](#5-impact-analysis)

---

## 1. Requirements Summary

### Core Requirements

**1. Manual Individual Creation ✅**
- **User Need**: Create individuals in ontology workbench for CQMT testing
- **Solution**: Form-based creation with dynamic form generation
- **Status**: Ready to implement

**2. Conceptualizer Impact ✅**
- **User Concern**: Will manual creation break conceptualizer?
- **Analysis**: **NO IMPACT** - Different `source_type` values
- **Status**: Safe to proceed

**3. Configurator ✅**
- **User Need**: Manual way to create nested tables like conceptualizer output
- **Solution**: Add to Conceptualizer Workbench
- **Status**: Phase 2 implementation

**4. Data Manager Workbench ✅**
- **User Concern**: Don't couple workbenches directly
- **Solution**: Future Data Manager Workbench with standardized APIs
- **Status**: Phase 3 architecture

**5. Units Management ✅**
- **User Question**: How to handle units?
- **Answer**: Current implementation sufficient (string-based)
- **Status**: No changes needed

---

## 2. Architecture Analysis

### Current Architecture

**Storage:**
- Individuals stored in Fuseki as RDF triples
- Metadata stored in PostgreSQL
- `source_type` field distinguishes creation method

**Workbench Integration:**
- Ontology Workbench: Class and property management
- Conceptualizer Workbench: AI-generated individuals
- CQMT Workbench: Test data creation

### Architectural Concerns

**1. Source Type Distinction**
- **Manual**: `source_type = "manual"`
- **DAS Generated**: `source_type = "das_generated"`
- **Impact**: No code changes needed in conceptualizer

**2. Storage Mechanism**
- Same storage mechanism for all individuals
- No coupling between creation methods
- Safe to add manual creation

**3. Workbench Coupling**
- Avoid direct workbench coupling
- Use standardized APIs
- Future Data Manager Workbench for integration

---

## 3. Design Decisions

### Form-Based Creation (vs Inline Editing)

**Decision**: Form-based with future inline option

**Rationale:**
- Better for complex inheritance
- Easier validation
- Clearer UX for object properties
- Can add inline editing later

**Implementation:**
- Dynamic form generation from class properties
- Inheritance-aware property display
- Support for all property types

### UUID-Based Identifiers

**Decision**: UUID primary key, UUID-based URI

**Rationale:**
- Globally unique
- Stable across name changes
- Database-friendly
- Prevents collisions

**Implementation:**
- Generate UUID on creation
- Use UUID in RDF URI
- Display UUID in UI

### Dynamic Name Column

**Decision**: Show Name column only if class has name property

**Rationale:**
- Respects ontology design
- Flexible for different classes
- Always show ID column

**Implementation:**
- Check class properties for name property
- Conditionally display Name column
- Always display ID column

### Inheritance Display

**Decision**: Group properties by inheritance source

**Rationale:**
- Clear visual hierarchy
- Shows inheritance relationships
- Easier to understand structure

**Implementation:**
- Group properties by class
- Show inheritance chain
- Highlight inherited properties

---

## 4. Implementation Plan

### Phase 1: Basic Individual Creation

**Components:**
1. **Backend API**
   - `POST /api/ontology/{project_id}/{ontology_id}/individuals`
   - Create individual with properties
   - Validate against class definition

2. **Frontend Form**
   - Dynamic form generation
   - Property type handling
   - Validation and error display

3. **Database Integration**
   - Store in Fuseki
   - Store metadata in PostgreSQL
   - Set `source_type = "manual"`

**Timeline**: 2-3 weeks

### Phase 2: Advanced Features

**Components:**
1. **Inheritance Support**
   - Display inherited properties
   - Group by inheritance source
   - Handle multiple inheritance

2. **Property Types**
   - Datatype properties (string, int, float, boolean)
   - Object properties (individual references)
   - List properties (multiple values)

3. **Validation**
   - Property type validation
   - Required property checking
   - Range validation

**Timeline**: 2-3 weeks

### Phase 3: Integration Features

**Components:**
1. **Configurator Integration**
   - Manual creation in Conceptualizer Workbench
   - Wizard-based creation
   - Same output format

2. **Data Manager Integration**
   - Standardized export/import
   - Pipeline builder
   - Workbench decoupling

**Timeline**: 3-4 weeks

---

## 5. Impact Analysis

### Conceptualizer Impact

**Analysis**: **NO IMPACT**

**Reasons:**
- Different `source_type` values
- Same storage mechanism
- No code changes needed
- Conceptualizer queries by `source_type`

**Conclusion**: Safe to proceed with manual creation

### CQMT Workbench Impact

**Positive Impact:**
- Enables manual test data creation
- Supports CQMT testing workflow
- Reduces dependency on conceptualizer

**No Negative Impact:**
- Separate creation method
- No interference with existing functionality

### Configurator Impact

**Future Enhancement:**
- Add manual creation mode
- Wizard-based interface
- Generate same configuration format

**No Current Impact:**
- Configurator not yet implemented
- Can design with manual creation in mind

---

## Database Schema

### Individuals Table

```sql
CREATE TABLE individuals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    ontology_id UUID NOT NULL,
    class_iri TEXT NOT NULL,
    individual_iri TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL DEFAULT 'manual',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Individual Properties Table

```sql
CREATE TABLE individual_properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    individual_id UUID NOT NULL REFERENCES individuals(id) ON DELETE CASCADE,
    property_iri TEXT NOT NULL,
    property_type TEXT NOT NULL, -- 'datatype' or 'object'
    value_text TEXT,
    value_iri TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Design

### Create Individual

**Endpoint**: `POST /api/ontology/{project_id}/{ontology_id}/individuals`

**Request:**
```json
{
  "class_iri": "http://.../Person",
  "properties": [
    {
      "property_iri": "http://.../hasName",
      "property_type": "datatype",
      "value": "John Doe"
    },
    {
      "property_iri": "http://.../hasAge",
      "property_type": "datatype",
      "value": "30"
    }
  ]
}
```

**Response:**
```json
{
  "individual_id": "uuid",
  "individual_iri": "http://.../individuals/uuid",
  "status": "created"
}
```

### Get Individual

**Endpoint**: `GET /api/ontology/{project_id}/{ontology_id}/individuals/{individual_id}`

**Response:**
```json
{
  "individual_id": "uuid",
  "individual_iri": "http://.../individuals/uuid",
  "class_iri": "http://.../Person",
  "properties": [
    {
      "property_iri": "http://.../hasName",
      "value": "John Doe"
    }
  ]
}
```

---

## UI Design

### Individual Creation Form

**Components:**
1. **Class Selection**
   - Dropdown of available classes
   - Shows class hierarchy
   - Validates selection

2. **Property Form**
   - Dynamic fields based on class
   - Grouped by inheritance
   - Type-specific inputs

3. **Validation**
   - Real-time validation
   - Error messages
   - Required field indicators

### Individual List View

**Components:**
1. **Table Display**
   - ID column (always shown)
   - Name column (if class has name property)
   - Class column
   - Actions column

2. **Filtering**
   - Filter by class
   - Filter by source type
   - Search by name/ID

3. **Actions**
   - Edit individual
   - Delete individual
   - View details

---

## Testing Strategy

### Unit Tests

**Coverage:**
- Form generation logic
- Property validation
- UUID generation
- URI construction

### Integration Tests

**Coverage:**
- API endpoint tests
- Database storage
- Fuseki integration
- Property type handling

### UI Tests

**Coverage:**
- Form rendering
- Property display
- Validation feedback
- Error handling

---

## Future Enhancements

### Inline Editing
- Edit individuals directly in table
- Quick property updates
- Batch editing

### Import/Export
- CSV import
- RDF export
- Bulk operations

### Advanced Features
- Property templates
- Individual cloning
- Relationship visualization

---

*Last Updated: November 2025*  
*Consolidated from: INDIVIDUALS_SUMMARY.md, INDIVIDUALS_CREATION_PLAN.md, INDIVIDUALS_CREATION_DESIGN_DISCUSSION.md, INDIVIDUALS_ARCHITECTURE_ANALYSIS.md*
