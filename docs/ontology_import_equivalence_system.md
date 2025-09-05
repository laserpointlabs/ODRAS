# Ontology Import Equivalence System - Technical Reference

## Overview

The ODRAS ontology import equivalence system allows users to import ontologies and automatically detect matching classes between the base ontology and imported ontologies. When matches are found, the system displays an equivalence count (e.g., "imported-ontology(2)") and creates visual links between matching classes on the canvas.

## System Architecture

### Data Flow

```
Frontend (Local Storage) ←→ Backend API ←→ Fuseki RDF Store
     ↓
Cytoscape.js Canvas
     ↓
Visual Equivalence Links
```

### Key Components

1. **Import Equivalence Counting** (`importEquivCount` function)
2. **Import Graph Snapshot** (`fetchImportGraphSnapshot` function)  
3. **Visual Linking** (Cytoscape.js overlay system)
4. **Data Persistence** (Local storage + Fuseki)

## Core Functions

### 1. Import Equivalence Counting

**Function**: `importEquivCount(importIri)`

**Purpose**: Counts matching classes between base ontology and imported ontology.

**Data Sources**:
- **Base classes**: From current Cytoscape graph (`ontoState.cy`)
- **Imported classes**: From local storage using consistent key format

**Key Implementation Details**:

```javascript
// Storage key format for imported ontology data
const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);

// Class matching logic
const norm = s => String(s||'').trim().toLowerCase();
const baseByLabel = new Map();
baseClasses.forEach(n => { 
  const label = n.data('label') || n.id();
  const normalized = norm(label);
  baseByLabel.set(normalized, n);
});
```

**Critical Requirements**:
- Both base and imported classes must use the same data source (local storage)
- Class matching is case-insensitive and whitespace-normalized
- Returns count of matching classes for display in import tree

### 2. Import Graph Snapshot

**Function**: `fetchImportGraphSnapshot(importIri)`

**Purpose**: Retrieves and processes imported ontology data for visual display.

**Data Processing Pipeline**:

```javascript
// 1. Get data from local storage
const importData = localStorage.getItem(importKey);
const importOntology = JSON.parse(importData);
const importNodes = importOntology.nodes || [];
const importEdges = importOntology.edges || [];

// 2. Convert Cytoscape nodes to snapshot format
const classes = importNodes
  .filter(node => (node.data && node.data.type === 'class') || !node.data?.type)
  .map(node => ({
    iri: node.data?.iri || node.id,
    label: node.data?.label || node.data?.id || node.id,
    comment: node.data?.comment || '',
    attrs: node.data?.attrs || {}
  }));

// 3. Return processed data
return { classes, edges, importNodes };
```

**Critical Requirements**:
- Must return `importNodes` data for proper node ID resolution
- Class labels must be preserved from original data
- Edge data must be properly converted

### 3. Visual Linking System

**Function**: `overlayImportsRefresh()`

**Purpose**: Creates visual representation of imported classes on canvas.

**Node Creation Process**:

```javascript
snap.classes.forEach((c, index) => {
  // Use original node ID from local storage data
  const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;
  const id = `imp:${imp}#${originalId}`;
  
  // Add to Cytoscape graph
  ontoState.cy.add({ 
    group: 'nodes', 
    data: { 
      id, 
      iri: c.iri || originalId, 
      label: c.label, 
      type: 'class', 
      importSource: imp, 
      attrs: c.attrs || {} 
    }, 
    position: pos, 
    classes: 'imported' 
  });
});
```

**Visual Linking Logic**:

```javascript
// Create equivalence edges between matching classes
const baseClasses = ontoState.cy.nodes().filter(n => !n.hasClass('imported'));
const importedClasses = ontoState.cy.nodes().filter(n => n.hasClass('imported'));

baseClasses.forEach(baseClass => {
  const baseLabel = baseClass.data('label');
  const matchingImported = importedClasses.filter(impClass => 
    impClass.data('label') === baseLabel
  );
  
  matchingImported.forEach(impClass => {
    // Create dashed equivalence edge
    ontoState.cy.add({
      group: 'edges',
      data: {
        id: `equiv_${baseClass.id()}_${impClass.id()}`,
        source: baseClass.id(),
        target: impClass.id(),
        type: 'equivalentClass',
        style: 'dashed'
      },
      classes: 'imported equivalent'
    });
  });
});
```

## Data Storage Architecture

### Local Storage Keys

```javascript
// Ontology graph data
`onto_graph__${projectId}__${encodeURIComponent(ontologyIri)}`

// Import overlay positions
`onto_import_positions__${encodeURIComponent(baseIri)}__${encodeURIComponent(importIri)}`

// Active ontology state
`active_ontology_iri`
`active_project`
```

### Data Structure

```javascript
// Local storage ontology data
{
  nodes: [
    {
      data: {
        id: "Class1",
        label: "A", 
        type: "class",
        attrs: {}
      },
      position: { x: 100, y: 200 },
      group: "nodes"
    }
  ],
  edges: [
    {
      data: {
        id: "edge1",
        source: "Class1",
        target: "Class2", 
        predicate: "relatedTo",
        type: "objectProperty"
      },
      group: "edges"
    }
  ],
  timestamp: 1757020118362,
  source: "local"
}
```

## Common Issues and Solutions

### Issue 1: Import Classes Show as "Class1", "Class2" Instead of Actual Labels

**Symptoms**:
- Imported classes display generic IDs instead of meaningful labels
- Equivalence counting works but visual display is wrong

**Root Cause**: 
- `c.iri` field is `undefined` in class objects
- Node IDs become malformed: `imp:${imp}#undefined`

**Solution**:
```javascript
// Use original node ID from local storage data
const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;
const id = `imp:${imp}#${originalId}`;
```

### Issue 2: ReferenceError: importNodes is not defined

**Symptoms**:
- JavaScript error when checking import checkbox
- Import classes don't appear on canvas

**Root Cause**:
- `importNodes` variable only defined in `fetchImportGraphSnapshot` scope
- `overlayImportsRefresh` function can't access it

**Solution**:
```javascript
// Return importNodes from fetchImportGraphSnapshot
return { classes, edges, importNodes };

// Access via snapshot data in overlayImportsRefresh
const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;
```

### Issue 3: Equivalence Count Shows 0 Despite Matching Classes

**Symptoms**:
- Import shows no equivalence count (no "(1)" or "(2)")
- Classes exist in both ontologies with same names

**Root Cause**:
- Data source mismatch between base and imported classes
- Base classes from Cytoscape, imported classes from Fuseki

**Solution**:
```javascript
// Use consistent data source (local storage) for both
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);
const importData = localStorage.getItem(importKey);
const importOntology = JSON.parse(importData);
const importClasses = importOntology.nodes || [];
```

### Issue 4: Classes Not Persisted to Fuseki

**Symptoms**:
- Classes exist in frontend but not in Fuseki
- SPARQL queries return empty results

**Root Cause**:
- Frontend only adds to Cytoscape graph, doesn't call backend API
- Classes stored with wrong namespace/URI

**Solution**:
```javascript
// Call backend API when creating classes
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
  },
  body: JSON.stringify({
    name: id,
    label: label,
    comment: ''
  })
});
```

### Issue 5: Reference Ontology Imports Show No Equivalence Count

**Symptoms**:
- Reference ontologies imported but show no equivalence count
- Import classes don't appear on canvas
- Console shows "No local storage data found for import"

**Root Cause**:
- Reference ontologies not loaded into local storage
- `importEquivCount` and `fetchImportGraphSnapshot` can't find data

**Solution**:
```javascript
// Auto-load reference ontology data if not in local storage
if (!importData) {
  console.log('🔍 No local storage data found for import, attempting to load from API:', importIri);
  try {
    const token = localStorage.getItem(tokenKey);
    const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;
    const response = await fetch(apiUrl, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    
    if (response.ok) {
      const ontologyData = await response.json();
      // Use simpler conversion since we don't have rich metadata
      const cytoscapeData = convertOntologyToCytoscape(ontologyData);
      const storageData = {
        nodes: cytoscapeData.nodes || [],
        edges: cytoscapeData.edges || [],
        timestamp: Date.now(),
        source: 'api'
      };
      
      localStorage.setItem(importKey, JSON.stringify(storageData));
      importData = JSON.stringify(storageData);
    }
  } catch (err) {
    console.error('🔍 Error loading imported ontology:', err);
    return 0;
  }
}
```

### Issue 6: TypeError in convertOntologyToCytoscapeWithMetadata

**Symptoms**:
- Reference ontology import fails with "Cannot read properties of undefined (reading 'forEach')"
- Error occurs at line 4663 in convertOntologyToCytoscapeWithMetadata

**Root Cause**:
- `convertOntologyToCytoscapeWithMetadata` expects rich metadata with `classes` and `properties` arrays
- Reference ontology API response doesn't include rich metadata
- Empty object `{}` passed as second parameter causes undefined access

**Solution**:
```javascript
// Use simpler conversion function for reference ontologies
const cytoscapeData = convertOntologyToCytoscape(ontologyData);
// Instead of:
// const cytoscapeData = convertOntologyToCytoscapeWithMetadata(ontologyData, {});
```

## Debugging Techniques

### 1. Console Debugging

Add comprehensive logging to trace data flow:

```javascript
console.log('🔍 Base classes found:', baseClasses.length);
console.log('🔍 Base classes by label:', Array.from(baseByLabel.keys()));
console.log('🔍 Import classes found:', rows.length);
console.log('🔍 Import class details:', rows);
console.log('🔍 Final import classes:', classes);
```

### 2. Data Source Verification

Check what data is actually stored:

```javascript
// Check local storage
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);
const importData = localStorage.getItem(importKey);
console.log('🔍 Import data:', JSON.parse(importData));

// Check Fuseki directly
curl -X POST http://localhost:8000/api/ontology/sparql \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT ?s ?p ?o WHERE { GRAPH <'$GRAPH_URI'> { ?s ?p ?o } }"}'
```

### 3. Node ID Resolution

Verify node IDs are properly constructed:

```javascript
console.log('🔍 Original node data:', importNodes[index]);
console.log('🔍 Generated ID:', id);
console.log('🔍 Final node data:', nodeData);
```

## Best Practices

### 1. Data Consistency
- Always use the same data source for both base and imported classes
- Prefer local storage over Fuseki for frontend operations
- Ensure proper synchronization between frontend and backend

### 2. Error Handling
- Add try-catch blocks around all async operations
- Provide fallback values for undefined data
- Log errors with sufficient context for debugging

### 3. Performance
- Cache imported ontology data in local storage
- Use efficient data structures (Maps) for class lookups
- Minimize DOM manipulations in Cytoscape

### 4. Maintainability
- Use consistent naming conventions for storage keys
- Document data flow between functions
- Keep debugging code for future troubleshooting

## Testing Checklist

When testing the import equivalence system:

1. **Create Test Ontologies**:
   - Base ontology with classes A, B
   - Import ontology with classes B, C
   - Expected: 1 match (class B)

2. **Verify Equivalence Counting**:
   - Check console for "✅ MATCH FOUND" messages
   - Verify import shows "(1)" in tree view

3. **Check Visual Display**:
   - Imported classes show correct labels (B, C)
   - Matching classes connected with dashed lines
   - No JavaScript errors in console

4. **Test Data Persistence**:
   - Refresh page, verify import still works
   - Check Fuseki contains correct class data
   - Verify local storage has proper data structure

## Related Files

- `/frontend/app.html` - Main frontend implementation
- `/backend/services/ontology_manager.py` - Backend ontology management
- `/backend/api/ontology.py` - API endpoints
- `/scripts/init-postgres.sql` - Database schema
- `/odras.sh` - System management script

## Version History

- **v1.0** - Initial implementation with basic import functionality
- **v1.1** - Added equivalence counting and visual linking
- **v1.2** - Fixed data source consistency issues
- **v1.3** - Resolved node ID and visual display problems
- **v1.4** - Added comprehensive debugging and error handling

---

*This document should be updated whenever significant changes are made to the import equivalence system.*
