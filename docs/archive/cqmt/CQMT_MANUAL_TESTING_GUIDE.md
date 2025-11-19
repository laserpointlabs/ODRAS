# CQMT Manual Testing Guide - UI Workflow

## Overview

This guide walks you through manually testing the CQMT synchronization features we just implemented.

## What Was Implemented

### Phase 1: Dependency Tracking ✅
- Tracks which MTs reference which ontology elements
- Stores dependencies automatically when MTs are created/updated
- Provides endpoints to query dependencies

### Phase 2: Change Detection ✅
- Detects ontology changes when saving
- Returns affected MTs
- Returns change summary (added/deleted/modified)

## Manual Testing Workflow

### Step 1: Create an Ontology

1. **Navigate to**: Project → Ontologies tab
2. **Create new ontology**: Click "Create Ontology"
3. **Add classes and properties**:

```turtle
@prefix : <http://odras.local/onto/YOUR_PROJECT/test_ontology#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:TestOntology a owl:Ontology ;
    rdfs:label "Test Ontology" .

:Person a owl:Class ;
    rdfs:label "Person" .

:Vehicle a owl:Class ;
    rdfs:label "Vehicle" .

:hasName a owl:DatatypeProperty ;
    rdfs:label "has name" ;
    rdfs:domain :Person ;
    rdfs:range rdfs:Literal .

:hasSpeed a owl:DatatypeProperty ;
    rdfs:label "has speed" ;
    rdfs:domain :Vehicle ;
    rdfs:range rdfs:Literal .
```

4. **Save the ontology** via UI
5. **Result**: Ontology saved successfully

### Step 2: Create a Microtheory

1. **Navigate to**: Project → CQ/MT Workbench
2. **Create new microtheory**: Click "Create Microtheory"
3. **Name**: "Test MT"
4. **Add triples that reference the ontology**:

When you update the microtheory, add triples like:
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
  },
  {
    "subject": "http://odras.local/onto/YOUR_PROJECT/test_ontology#car1",
    "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "object": "http://odras.local/onto/YOUR_PROJECT/test_ontology#Vehicle"
  },
  {
    "subject": "http://odras.local/onto/YOUR_PROJECT/test_ontology#car1",
    "predicate": "http://odras.local/onto/YOUR_PROJECT/test_ontology#hasSpeed",
    "object": "120"
  }
]
```

5. **Save the microtheory**
6. **Result**: Microtheory created, dependencies automatically tracked ✅

### Step 3: Check Dependencies (API)

1. **Get the MT ID** from the UI
2. **Call API**: 
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/MT_ID/dependencies
```

3. **Expected Response**:
```json
{
  "microtheory_id": "...",
  "dependencies": [
    {
      "ontology_graph_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology#Person",
      "element_type": "Class",
      "is_valid": true
    },
    {
      "ontology_graph_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology#hasName",
      "element_type": "DatatypeProperty",
      "is_valid": true
    },
    {
      "ontology_graph_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology#Vehicle",
      "element_type": "Class",
      "is_valid": true
    },
    {
      "ontology_graph_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology#hasSpeed",
      "element_type": "DatatypeProperty",
      "is_valid": true
    }
  ]
}
```

### Step 4: Modify the Ontology

1. **Go back to**: Project → Ontologies tab
2. **Edit the ontology** - Make some changes:

**Scenario A: Add an element**
```turtle
# Add this to the ontology
:Animal a owl:Class ;
    rdfs:label "Animal" .
```

**Scenario B: Delete an element**
```turtle
# Remove :hasSpeed property entirely
```

**Scenario C: Rename an element**
```turtle
# Change :hasName to :hasFullName
:hasFullName a owl:DatatypeProperty ;
    rdfs:label "has full name" ;
    rdfs:domain :Person ;
    rdfs:range rdfs:Literal .
```

3. **Save the ontology** via UI

### Step 5: Observe Change Detection

**When you save**, check the browser's Network tab:

1. **Find the save request**: `POST /api/ontology/save`
2. **Look at the response**:

**If you added :Animal**:
```json
{
  "success": true,
  "graphIri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
  "message": "Saved to Fuseki",
  "changes": {
    "total": 1,
    "added": 1,
    "deleted": 0,
    "renamed": 0,
    "modified": 0,
    "affected_mts": []
  }
}
```

**If you deleted :hasSpeed**:
```json
{
  "success": true,
  "graphIri": "http://odras.local/onto/YOUR_PROJECT/test_ontology",
  "message": "Saved to Fuseki",
  "changes": {
    "total": 1,
    "added": 0,
    "deleted": 1,
    "renamed": 0,
    "modified": 0,
    "affected_mts": ["YOUR_MT_ID"]
  }
}
```

### Step 6: Validate Dependencies

1. **Call validation endpoint**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/MT_ID/validation
```

2. **After deleting hasSpeed**, expect:
```json
{
  "microtheory_id": "...",
  "validation_status": "incomplete",
  "total_dependencies": 4,
  "valid_dependencies": 3,
  "invalid_dependencies": 1,
  "broken_references": [
    {
      "element_iri": "http://odras.local/onto/YOUR_PROJECT/test_ontology#hasSpeed",
      "element_type": "DatatypeProperty",
      "status": "not_found"
    }
  ]
}
```

## What Happens Behind the Scenes

### When You Create/Update an MT
1. MT triples stored in Fuseki
2. Dependencies extracted automatically
3. Stored in `mt_ontology_dependencies` table

### When You Save an Ontology
1. Current elements queried from Fuseki
2. New content parsed
3. Changes detected (additions/deletions/modifications)
4. Dependency table queried for affected MTs
5. Change summary returned in API response

## Current Limitations

### What Works ✅
- Automatic dependency tracking
- Change detection on save
- Affected MT identification
- Validation endpoints

### What Doesn't Work Yet ⚠️
- **UI notifications** - API returns data but UI doesn't show it
- **Change history** - Only current changes, no history
- **Auto-update** - MTs don't auto-update when ontology changes

## UI Testing Checklist

- [ ] Create ontology with classes and properties
- [ ] Create microtheory referencing those elements
- [ ] Verify dependencies API returns correct elements
- [ ] Modify ontology (add element)
- [ ] Check save response shows addition
- [ ] Modify ontology (delete element)
- [ ] Check save response shows deletion + affected MT
- [ ] Call validation endpoint
- [ ] Verify validation shows broken references

## Expected API Responses

### Save Ontology (No Changes)
```json
{
  "success": true,
  "changes": {
    "total": 0,
    "added": 0,
    "deleted": 0,
    "renamed": 0,
    "modified": 0,
    "affected_mts": []
  }
}
```

### Save Ontology (With Changes)
```json
{
  "success": true,
  "changes": {
    "total": 2,
    "added": 1,
    "deleted": 1,
    "renamed": 0,
    "modified": 0,
    "affected_mts": ["mt-id-1", "mt-id-2"]
  }
}
```

## Future UI Enhancements

When UI is updated, you'll see:
1. **Toast notification** after save: "2 changes detected, affects 1 microtheory"
2. **Affected MTs list** in notification
3. **Details button** to see what changed
4. **Update button** to update MTs automatically

## Key Takeaways

**What's Working Now**:
- Backend detects changes automatically
- Backend tracks dependencies automatically
- Backend returns change information
- API endpoints available for UI

**What Needs UI Work**:
- Display change notifications
- Show affected MTs list
- Provide update workflow

**To Test**:
- Use browser Network tab to see API responses
- Call API endpoints directly
- Verify backend behavior

Ready to test! 🚀
