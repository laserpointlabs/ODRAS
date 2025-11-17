# Ontology Workbench Refactor Plan

## Overview

This branch will refactor the ontology workbench to integrate with the new **Multi-Tenant Architecture + Unified IRI Service + 8-Character Codes** that was merged to main.

## Current State (Post-Merge)

✅ **Backend Ready:**
- Multi-tenant database schema with tenant_id columns
- UnifiedIRIService with 8-character code generation
- API endpoints: `/api/tenants/mint-element-iri` and `/api/tenants/generate-8char-codes/`
- Enhanced authentication with TenantUser context

✅ **Frontend Current Pattern:**
```javascript
// Current ontology element creation (ontology-ui.js:2481)
const id = `Class${ontoState.nextId++}`;  // Class1, Class2, Class3...

// API call
body: JSON.stringify({
  name: id,        // "Class1"
  label: label,    // Human-readable display
  comment: ''
})
```

## Refactor Goals

### **1. Integrate 8-Character IRI System**
- Replace sequential IDs (`Class1`, `Class2`) with 8-char codes (`A1B2-C3D4`)
- Use 8-char codes as technical identifiers for ontology elements
- Keep human-readable labels for display purposes
- Enable users to reference elements by memorable codes

### **2. Enhance UI for Code Display**
- Show both label and code in ontology tree: `"Requirement (A1B2-C3D4)"`
- Add copy-to-clipboard for 8-char codes
- Display full IRI when needed for technical reference
- Improve element selection/search by code

### **3. Update API Integration**
- Modify `addClassNode()`, `addObjectProperty()`, `addDataProperty()` functions
- Use mint-element-iri API before creating Cytoscape nodes
- Update Fuseki API calls to use 8-char codes
- Handle code generation errors gracefully

### **4. Maintain Backwards Compatibility**
- Existing ontologies continue to work during transition
- Gradual migration path for existing elements
- No breaking changes to saved ontology data

## Implementation Tasks

### **Phase 1: Backend API Integration**
- [ ] Create JavaScript helper for minting 8-char codes
- [ ] Update `addClassNode()` to use API-generated codes
- [ ] Update `addObjectProperty()` and `addDataProperty()` functions
- [ ] Test ontology element creation with new codes

### **Phase 2: UI Enhancement**
- [ ] Update ontology tree display to show codes
- [ ] Add code display in element properties panel
- [ ] Implement copy-to-clipboard for codes
- [ ] Update element search to work with codes

### **Phase 3: Element Management**
- [ ] Update element selection by code
- [ ] Enhance element editing to preserve codes
- [ ] Update relationship creation to use codes
- [ ] Test full ontology creation workflow

### **Phase 4: Testing & Validation**
- [ ] Test ontology element lifecycle with 8-char codes
- [ ] Validate Fuseki storage with new IRI patterns
- [ ] Test export/import with new IRI system
- [ ] User experience testing

## API Integration Pattern

### **New Element Creation Flow:**
```javascript
// 1. Request 8-char code from backend
const codeResponse = await fetch('/api/tenants/mint-element-iri', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
  },
  body: JSON.stringify({
    project_id: currentProjectId,
    ontology_name: currentOntologyName,
    element_type: 'class'  // or 'objectProperty', 'dataProperty', 'individual'
  })
});

const {code, iri} = await codeResponse.json();

// 2. Create Cytoscape node with 8-char code
ontoState.cy.add({
  group: 'nodes',
  data: { 
    id: code,                    // "A1B2-C3D4" - technical ID
    label: label || `Class${ontoState.nextId++}`,  // Display name
    iri: iri,                   // Full IRI for reference
    type: 'class',
    attrs: addCreationMetadata({})
  },
  position: { x, y }
});

// 3. Store in Fuseki with 8-char code
const response = await fetch(`/api/ontology/classes?graph=${encodeURIComponent(graphUri)}`, {
  method: 'POST',
  headers: { /* ... */ },
  body: JSON.stringify({
    name: code,     // Use 8-char code as technical name
    label: label,   // Human-readable label  
    iri: iri,       // Full IRI
    comment: ''
  })
});
```

## Benefits After Refactor

✅ **User Experience:**
- "Go to requirement A1B2-C3D4" ← Easy to communicate
- Codes are writable in documentation  
- Technical discussions more precise

✅ **Technical:**
- Collision-resistant (58^8 combinations)
- Tenant-aware IRI generation
- Consistent with unified IRI architecture
- Future-ready for files, configurations, etc.

## Timeline

**Ready to start tomorrow on `feature/ontology-workbench-refactor` branch.**

Backend APIs are complete and tested. Focus will be on frontend integration and user experience enhancement.

## Dependencies

- ✅ Multi-tenant architecture (merged)
- ✅ UnifiedIRIService (merged)  
- ✅ 8-character code generation APIs (merged)
- ✅ Enhanced authentication (merged)

**All dependencies satisfied - ready for clean implementation.**
