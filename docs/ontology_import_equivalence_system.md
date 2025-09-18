# Ontology Import Equivalence System - Technical Reference<br>
<br>
## Overview<br>
<br>
The ODRAS ontology import equivalence system allows users to import ontologies and automatically detect matching classes between the base ontology and imported ontologies. When matches are found, the system displays an equivalence count (e.g., "imported-ontology(2)") and creates visual links between matching classes on the canvas.<br>
<br>
## System Architecture<br>
<br>
### Data Flow<br>
<br>
```<br>
Frontend (Local Storage) ←→ Backend API ←→ Fuseki RDF Store<br>
     ↓<br>
Cytoscape.js Canvas<br>
     ↓<br>
Visual Equivalence Links<br>
```<br>
<br>
### Key Components<br>
<br>
1. **Import Equivalence Counting** (`importEquivCount` function)<br>
2. **Import Graph Snapshot** (`fetchImportGraphSnapshot` function)<br>
3. **Visual Linking** (Cytoscape.js overlay system)<br>
4. **Data Persistence** (Local storage + Fuseki)<br>
<br>
## Core Functions<br>
<br>
### 1. Import Equivalence Counting<br>
<br>
**Function**: `importEquivCount(importIri)`<br>
<br>
**Purpose**: Counts matching classes between base ontology and imported ontology.<br>
<br>
**Data Sources**:<br>
- **Base classes**: From current Cytoscape graph (`ontoState.cy`)<br>
- **Imported classes**: From local storage using consistent key format<br>
<br>
**Key Implementation Details**:<br>
<br>
```javascript<br>
// Storage key format for imported ontology data<br>
const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';<br>
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);<br>
<br>
// Class matching logic<br>
const norm = s => String(s||'').trim().toLowerCase();<br>
const baseByLabel = new Map();<br>
baseClasses.forEach(n => {<br>
  const label = n.data('label') || n.id();<br>
  const normalized = norm(label);<br>
  baseByLabel.set(normalized, n);<br>
});<br>
```<br>
<br>
**Critical Requirements**:<br>
- Both base and imported classes must use the same data source (local storage)<br>
- Class matching is case-insensitive and whitespace-normalized<br>
- Returns count of matching classes for display in import tree<br>
<br>
### 2. Import Graph Snapshot<br>
<br>
**Function**: `fetchImportGraphSnapshot(importIri)`<br>
<br>
**Purpose**: Retrieves and processes imported ontology data for visual display.<br>
<br>
**Data Processing Pipeline**:<br>
<br>
```javascript<br>
// 1. Get data from local storage<br>
const importData = localStorage.getItem(importKey);<br>
const importOntology = JSON.parse(importData);<br>
const importNodes = importOntology.nodes || [];<br>
const importEdges = importOntology.edges || [];<br>
<br>
// 2. Convert Cytoscape nodes to snapshot format<br>
const classes = importNodes<br>
  .filter(node => (node.data && node.data.type === 'class') || !node.data?.type)<br>
  .map(node => ({<br>
    iri: node.data?.iri || node.id,<br>
    label: node.data?.label || node.data?.id || node.id,<br>
    comment: node.data?.comment || '',<br>
    attrs: node.data?.attrs || {}<br>
  }));<br>
<br>
// 3. Return processed data<br>
return { classes, edges, importNodes };<br>
```<br>
<br>
**Critical Requirements**:<br>
- Must return `importNodes` data for proper node ID resolution<br>
- Class labels must be preserved from original data<br>
- Edge data must be properly converted<br>
<br>
### 3. Visual Linking System<br>
<br>
**Function**: `overlayImportsRefresh()`<br>
<br>
**Purpose**: Creates visual representation of imported classes on canvas.<br>
<br>
**Node Creation Process**:<br>
<br>
```javascript<br>
snap.classes.forEach((c, index) => {<br>
  // Use original node ID from local storage data<br>
  const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;<br>
  const id = `imp:${imp}#${originalId}`;<br>
<br>
  // Add to Cytoscape graph<br>
  ontoState.cy.add({<br>
    group: 'nodes',<br>
    data: {<br>
      id,<br>
      iri: c.iri || originalId,<br>
      label: c.label,<br>
      type: 'class',<br>
      importSource: imp,<br>
      attrs: c.attrs || {}<br>
    },<br>
    position: pos,<br>
    classes: 'imported'<br>
  });<br>
});<br>
```<br>
<br>
**Visual Linking Logic**:<br>
<br>
```javascript<br>
// Create equivalence edges between matching classes<br>
const baseClasses = ontoState.cy.nodes().filter(n => !n.hasClass('imported'));<br>
const importedClasses = ontoState.cy.nodes().filter(n => n.hasClass('imported'));<br>
<br>
baseClasses.forEach(baseClass => {<br>
  const baseLabel = baseClass.data('label');<br>
  const matchingImported = importedClasses.filter(impClass =><br>
    impClass.data('label') === baseLabel<br>
  );<br>
<br>
  matchingImported.forEach(impClass => {<br>
    // Create dashed equivalence edge<br>
    ontoState.cy.add({<br>
      group: 'edges',<br>
      data: {<br>
        id: `equiv_${baseClass.id()}_${impClass.id()}`,<br>
        source: baseClass.id(),<br>
        target: impClass.id(),<br>
        type: 'equivalentClass',<br>
        style: 'dashed'<br>
      },<br>
      classes: 'imported equivalent'<br>
    });<br>
  });<br>
});<br>
```<br>
<br>
## Data Storage Architecture<br>
<br>
### Local Storage Keys<br>
<br>
```javascript<br>
// Ontology graph data<br>
`onto_graph__${projectId}__${encodeURIComponent(ontologyIri)}`<br>
<br>
// Import overlay positions<br>
`onto_import_positions__${encodeURIComponent(baseIri)}__${encodeURIComponent(importIri)}`<br>
<br>
// Active ontology state<br>
`active_ontology_iri`<br>
`active_project`<br>
```<br>
<br>
### Data Structure<br>
<br>
```javascript<br>
// Local storage ontology data<br>
{<br>
  nodes: [<br>
    {<br>
      data: {<br>
        id: "Class1",<br>
        label: "A",<br>
        type: "class",<br>
        attrs: {}<br>
      },<br>
      position: { x: 100, y: 200 },<br>
      group: "nodes"<br>
    }<br>
  ],<br>
  edges: [<br>
    {<br>
      data: {<br>
        id: "edge1",<br>
        source: "Class1",<br>
        target: "Class2",<br>
        predicate: "relatedTo",<br>
        type: "objectProperty"<br>
      },<br>
      group: "edges"<br>
    }<br>
  ],<br>
  timestamp: 1757020118362,<br>
  source: "local"<br>
}<br>
```<br>
<br>
## Common Issues and Solutions<br>
<br>
### Issue 1: Import Classes Show as "Class1", "Class2" Instead of Actual Labels<br>
<br>
**Symptoms**:<br>
- Imported classes display generic IDs instead of meaningful labels<br>
- Equivalence counting works but visual display is wrong<br>
<br>
**Root Cause**:<br>
- `c.iri` field is `undefined` in class objects<br>
- Node IDs become malformed: `imp:${imp}#undefined`<br>
<br>
**Solution**:<br>
```javascript<br>
// Use original node ID from local storage data<br>
const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;<br>
const id = `imp:${imp}#${originalId}`;<br>
```<br>
<br>
### Issue 2: ReferenceError: importNodes is not defined<br>
<br>
**Symptoms**:<br>
- JavaScript error when checking import checkbox<br>
- Import classes don't appear on canvas<br>
<br>
**Root Cause**:<br>
- `importNodes` variable only defined in `fetchImportGraphSnapshot` scope<br>
- `overlayImportsRefresh` function can't access it<br>
<br>
**Solution**:<br>
```javascript<br>
// Return importNodes from fetchImportGraphSnapshot<br>
return { classes, edges, importNodes };<br>
<br>
// Access via snapshot data in overlayImportsRefresh<br>
const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;<br>
```<br>
<br>
### Issue 3: Equivalence Count Shows 0 Despite Matching Classes<br>
<br>
**Symptoms**:<br>
- Import shows no equivalence count (no "(1)" or "(2)")<br>
- Classes exist in both ontologies with same names<br>
<br>
**Root Cause**:<br>
- Data source mismatch between base and imported classes<br>
- Base classes from Cytoscape, imported classes from Fuseki<br>
<br>
**Solution**:<br>
```javascript<br>
// Use consistent data source (local storage) for both<br>
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);<br>
const importData = localStorage.getItem(importKey);<br>
const importOntology = JSON.parse(importData);<br>
const importClasses = importOntology.nodes || [];<br>
```<br>
<br>
### Issue 4: Classes Not Persisted to Fuseki<br>
<br>
**Symptoms**:<br>
- Classes exist in frontend but not in Fuseki<br>
- SPARQL queries return empty results<br>
<br>
**Root Cause**:<br>
- Frontend only adds to Cytoscape graph, doesn't call backend API<br>
- Classes stored with wrong namespace/URI<br>
<br>
**Solution**:<br>
```javascript<br>
// Call backend API when creating classes<br>
const response = await fetch(url, {<br>
  method: 'POST',<br>
  headers: {<br>
    'Content-Type': 'application/json',<br>
    'Authorization': `Bearer ${localStorage.getItem('odras_token')}`<br>
  },<br>
  body: JSON.stringify({<br>
    name: id,<br>
    label: label,<br>
    comment: ''<br>
  })<br>
});<br>
```<br>
<br>
### Issue 5: Reference Ontology Imports Show No Equivalence Count<br>
<br>
**Symptoms**:<br>
- Reference ontologies imported but show no equivalence count<br>
- Import classes don't appear on canvas<br>
- Console shows "No local storage data found for import"<br>
<br>
**Root Cause**:<br>
- Reference ontologies not loaded into local storage<br>
- `importEquivCount` and `fetchImportGraphSnapshot` can't find data<br>
<br>
**Solution**:<br>
```javascript<br>
// Auto-load reference ontology data if not in local storage<br>
if (!importData) {<br>
  console.log('🔍 No local storage data found for import, attempting to load from API:', importIri);<br>
  try {<br>
    const token = localStorage.getItem(tokenKey);<br>
    const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;<br>
    const response = await fetch(apiUrl, {<br>
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}<br>
    });<br>
<br>
    if (response.ok) {<br>
      const ontologyData = await response.json();<br>
      // Use simpler conversion since we don't have rich metadata<br>
      const cytoscapeData = convertOntologyToCytoscape(ontologyData);<br>
      const storageData = {<br>
        nodes: cytoscapeData.nodes || [],<br>
        edges: cytoscapeData.edges || [],<br>
        timestamp: Date.now(),<br>
        source: 'api'<br>
      };<br>
<br>
      localStorage.setItem(importKey, JSON.stringify(storageData));<br>
      importData = JSON.stringify(storageData);<br>
    }<br>
  } catch (err) {<br>
    console.error('🔍 Error loading imported ontology:', err);<br>
    return 0;<br>
  }<br>
}<br>
```<br>
<br>
### Issue 6: TypeError in convertOntologyToCytoscapeWithMetadata<br>
<br>
**Symptoms**:<br>
- Reference ontology import fails with "Cannot read properties of undefined (reading 'forEach')"<br>
- Error occurs at line 4663 in convertOntologyToCytoscapeWithMetadata<br>
<br>
**Root Cause**:<br>
- `convertOntologyToCytoscapeWithMetadata` expects rich metadata with `classes` and `properties` arrays<br>
- Reference ontology API response doesn't include rich metadata<br>
- Empty object `{}` passed as second parameter causes undefined access<br>
<br>
**Solution**:<br>
```javascript<br>
// Use simpler conversion function for reference ontologies<br>
const cytoscapeData = convertOntologyToCytoscape(ontologyData);<br>
// Instead of:<br>
// const cytoscapeData = convertOntologyToCytoscapeWithMetadata(ontologyData, {});<br>
```<br>
<br>
## Debugging Techniques<br>
<br>
### 1. Console Debugging<br>
<br>
Add comprehensive logging to trace data flow:<br>
<br>
```javascript<br>
console.log('🔍 Base classes found:', baseClasses.length);<br>
console.log('🔍 Base classes by label:', Array.from(baseByLabel.keys()));<br>
console.log('🔍 Import classes found:', rows.length);<br>
console.log('🔍 Import class details:', rows);<br>
console.log('🔍 Final import classes:', classes);<br>
```<br>
<br>
### 2. Data Source Verification<br>
<br>
Check what data is actually stored:<br>
<br>
```javascript<br>
// Check local storage<br>
const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);<br>
const importData = localStorage.getItem(importKey);<br>
console.log('🔍 Import data:', JSON.parse(importData));<br>
<br>
// Check Fuseki directly<br>
curl -X POST http://localhost:8000/api/ontology/sparql \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"query": "SELECT ?s ?p ?o WHERE { GRAPH <'$GRAPH_URI'> { ?s ?p ?o } }"}'<br>
```<br>
<br>
### 3. Node ID Resolution<br>
<br>
Verify node IDs are properly constructed:<br>
<br>
```javascript<br>
console.log('🔍 Original node data:', importNodes[index]);<br>
console.log('🔍 Generated ID:', id);<br>
console.log('🔍 Final node data:', nodeData);<br>
```<br>
<br>
## Best Practices<br>
<br>
### 1. Data Consistency<br>
- Always use the same data source for both base and imported classes<br>
- Prefer local storage over Fuseki for frontend operations<br>
- Ensure proper synchronization between frontend and backend<br>
<br>
### 2. Error Handling<br>
- Add try-catch blocks around all async operations<br>
- Provide fallback values for undefined data<br>
- Log errors with sufficient context for debugging<br>
<br>
### 3. Performance<br>
- Cache imported ontology data in local storage<br>
- Use efficient data structures (Maps) for class lookups<br>
- Minimize DOM manipulations in Cytoscape<br>
<br>
### 4. Maintainability<br>
- Use consistent naming conventions for storage keys<br>
- Document data flow between functions<br>
- Keep debugging code for future troubleshooting<br>
<br>
## Testing Checklist<br>
<br>
When testing the import equivalence system:<br>
<br>
1. **Create Test Ontologies**:<br>
   - Base ontology with classes A, B<br>
   - Import ontology with classes B, C<br>
   - Expected: 1 match (class B)<br>
<br>
2. **Verify Equivalence Counting**:<br>
   - Check console for "✅ MATCH FOUND" messages<br>
   - Verify import shows "(1)" in tree view<br>
<br>
3. **Check Visual Display**:<br>
   - Imported classes show correct labels (B, C)<br>
   - Matching classes connected with dashed lines<br>
   - No JavaScript errors in console<br>
<br>
4. **Test Data Persistence**:<br>
   - Refresh page, verify import still works<br>
   - Check Fuseki contains correct class data<br>
   - Verify local storage has proper data structure<br>
<br>
## Related Files<br>
<br>
- `/frontend/app.html` - Main frontend implementation<br>
- `/backend/services/ontology_manager.py` - Backend ontology management<br>
- `/backend/api/ontology.py` - API endpoints<br>
- `/scripts/init-postgres.sql` - Database schema<br>
- `/odras.sh` - System management script<br>
<br>
## Version History<br>
<br>
- **v1.0** - Initial implementation with basic import functionality<br>
- **v1.1** - Added equivalence counting and visual linking<br>
- **v1.2** - Fixed data source consistency issues<br>
- **v1.3** - Resolved node ID and visual display problems<br>
- **v1.4** - Added comprehensive debugging and error handling<br>
<br>
---<br>
<br>
*This document should be updated whenever significant changes are made to the import equivalence system.*<br>

