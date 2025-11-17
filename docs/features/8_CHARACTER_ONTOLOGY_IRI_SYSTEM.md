# 8-Character Ontology Element IRI System

## Overview

ODRAS now supports human-memorable 8-character codes for ontology elements instead of UUIDs. This makes it easy for users to reference, write down, and remember specific ontology elements.

## Design

### **Format**
- **8 characters total**: `XXXX-XXXX` (4 chars + hyphen + 4 chars)
- **Character set**: Clear alphanumeric excluding confusing characters (`0`, `O`, `I`, `l`)
- **Examples**: `A1B2-C3D4`, `X5Y7-M9N2`, `P3Q6-R8S4`

### **IRI Pattern**
```
Full IRI: {tenant_base}/{namespace}/{project_uuid}/ontologies/{name}#{8char-code}
Example:  https://odras.navy.mil/usn-adt/se/abc123/ontologies/requirements#A1B2-C3D4
```

### **Usage Pattern**
- **Label**: Keep human-readable display names ("Requirement", "Component", etc.)
- **IRI**: Use 8-character codes for technical identification
- **Display**: Show both label and code in UI for easy reference

## Implementation

### **Backend Service** (`backend/services/unified_iri_service.py`)

**Core Methods:**
```python
# Generate random 8-character code
def generate_8char_code(self) -> str:
    """Returns: 'A1B2-C3D4'"""

# Generate unique code within ontology scope  
def generate_unique_8char_code(self, project_id: str, ontology_name: str) -> str:
    """Ensures no collisions within same ontology"""

# Mint complete element IRI
def mint_ontology_element_iri(self, project_id: str, ontology_name: str, element_type: str) -> Dict:
    """Returns: {'code': 'A1B2-C3D4', 'iri': 'https://...#A1B2-C3D4', ...}"""
```

### **API Endpoints** (`/api/tenants/`)

**Mint Element IRI:**
```http
POST /api/tenants/mint-element-iri
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "12345678-1234-1234-1234-123456789abc",
  "ontology_name": "Requirements", 
  "element_type": "class"
}

Response:
{
  "code": "A1B2-C3D4",
  "iri": "https://system.odras.local/projects/.../ontologies/requirements#A1B2-C3D4",
  "element_type": "class",
  "project_id": "12345678-1234-1234-1234-123456789abc",
  "ontology_name": "Requirements"
}
```

**Generate Sample Codes:**
```http
GET /api/tenants/generate-8char-codes/5

Response:
{
  "tenant_code": "system",
  "sample_codes": [
    {"code": "A1B2-C3D4", "example_iri": "https://...#A1B2-C3D4"},
    {"code": "X5Y7-M9N2", "example_iri": "https://...#X5Y7-M9N2"}
  ],
  "format_description": "8-character codes in format XXXX-XXXX using clear alphanumeric characters"
}
```

## Testing

### **Comprehensive Testing** (`scripts/test_8char_iri.py`)
- ✅ Basic code generation (20 unique codes)
- ✅ Format validation (XXXX-XXXX pattern)
- ✅ Character set validation (no confusing characters)
- ✅ Uniqueness within ontology scope
- ✅ Full IRI generation for all element types
- ✅ API endpoint integration testing

### **CI Integration**
- ✅ **Fast CI**: Unit tests without database (5 sample codes + validation)
- ✅ **Comprehensive CI**: Full integration testing with API endpoints

## Frontend Integration Plan

### **Current State** (`frontend/js/workbenches/ontology/ontology-ui.js`)
```javascript
// Current approach - generates sequential IDs
const id = `Class${ontoState.nextId++}`;  // Class1, Class2, Class3...

// API call uses ID as both name and label
body: JSON.stringify({
  name: id,        // "Class1" 
  label: label,    // Human-readable display name
  comment: ''
})
```

### **Proposed Enhancement**
```javascript
// NEW: Request 8-character code from backend
async function addClassNode(label) {
  // 1. Get 8-character code from API
  const codeResponse = await fetch('/api/tenants/mint-element-iri', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
    },
    body: JSON.stringify({
      project_id: currentProjectId,
      ontology_name: currentOntologyName,
      element_type: 'class'
    })
  });
  
  const codeData = await codeResponse.json();
  const elementCode = codeData.code;  // e.g., "A1B2-C3D4"
  const elementIRI = codeData.iri;    // Full IRI
  
  // 2. Use code as technical ID, keep label for display
  const displayId = `Class${ontoState.nextId++}`;  // Keep for backward compatibility
  
  ontoState.cy.add({
    group: 'nodes',
    data: { 
      id: elementCode,           // Use 8-char code as technical ID
      label: label || displayId, // Human-readable label
      iri: elementIRI,           // Store full IRI
      type: 'class',
      attrs: addCreationMetadata({})
    },
    position: { x, y }
  });
  
  // 3. API call uses 8-character code
  await fetch(`/api/ontology/classes?graph=${encodeURIComponent(graphUri)}`, {
    method: 'POST',
    headers: { /* ... */ },
    body: JSON.stringify({
      name: elementCode,  // Use 8-char code
      label: label,       // Human-readable label
      iri: elementIRI,    // Full IRI
      comment: ''
    })
  });
}
```

### **UI Display Enhancement**
```javascript
// Show both label and code in ontology tree/properties
function displayElementInUI(element) {
  return `${element.label} (${element.id})`;  // "Requirement (A1B2-C3D4)"
}
```

## Benefits

✅ **Human-Memorable**: `A1B2-C3D4` is much easier to remember than UUID  
✅ **Easy to Reference**: Users can verbally share codes ("use the A1B2 requirement")  
✅ **Writable**: Easy to write down in documentation or notes  
✅ **Collision-Resistant**: 58^8 ≈ 128 billion combinations  
✅ **Clear**: No confusing characters (0, O, I, l excluded)  
✅ **Tenant-Aware**: Integrated with unified IRI service  

## Migration Strategy

**Phase 1: Backend Ready** ✅ **COMPLETE**
- 8-character generation in UnifiedIRIService
- API endpoints for minting and testing
- Comprehensive testing and CI integration

**Phase 2: Frontend Integration** (Coordinate with ontology workbench refactoring)
- Update `addClassNode()`, `addObjectProperty()`, `addDataProperty()` functions
- Modify Cytoscape node creation to use 8-char codes as IDs
- Update UI to display both label and code
- Modify API calls to send 8-char codes instead of sequential IDs

**Phase 3: Full Deployment**
- Migrate existing ontologies (optional)
- Update documentation and user guides
- User training on new reference system

## Next Steps

**Ready for ontology workbench integration!** The backend is complete and tested. When you're ready to update the frontend, the API endpoints are available and the integration pattern is documented above.
