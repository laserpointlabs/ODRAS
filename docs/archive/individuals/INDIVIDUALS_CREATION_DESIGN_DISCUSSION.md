# Individuals Creation Design Discussion

## Overview

This document discusses architectural decisions and best practices for implementing individual creation in the ontology workbench, addressing concerns about inheritance handling, editing patterns, and data modeling.

## Key Questions

### 1. Table Editing vs Form-Based Editing

**Question**: Should users edit individuals directly in the table or use a form/modal?

**Analysis**:

**Option A: Inline Table Editing** (Like Excel/Airtable)
- ✅ **Pros**:
  - Faster for bulk data entry
  - Natural spreadsheet-like experience
  - Easy to see relationships between individuals
  - Quick edits without modal interactions
- ❌ **Cons**:
  - Complex property types hard to handle inline (e.g., object properties, multi-values)
  - Difficult to show inheritance indicators inline
  - Validation harder to implement
  - Touch/mobile unfriendly

**Option B: Form-Based Editing** (Traditional CRUD)
- ✅ **Pros**:
  - Better for complex property types
  - Clear property organization (direct vs inherited)
  - Easier validation and error handling
  - Better UX for required fields and tooltips
  - Can show property descriptions/comments
- ❌ **Cons**:
  - Slower for bulk operations
  - More clicks for simple edits
  - Can't easily compare multiple individuals

**Option C: Hybrid Approach** (Recommended)
- ✅ **Best of both worlds**:
  - Table shows all individuals with key properties
  - Simple text properties editable inline
  - Complex properties open form on click
  - "Add Individual" button opens full form
  - Can still implement bulk import/export

**Recommendation**: **Option C (Hybrid)**
- Primary: Form-based creation for all new individuals
- Secondary: Inline editing for simple text/datatype properties
- Complex: Click to edit opens form for object properties, validation, etc.

**Rationale**: 
- Our ontology has complex inheritance hierarchies
- Many properties are object properties (references to other individuals)
- Form provides better UX for showing inheritance and validation
- Can add inline editing later if needed for power users

---

### 2. Handling Inheritance

**Critical Requirement**: Must properly handle inherited properties

**Current Implementation**:
- ✅ Inheritance detection works (`getClassPropertiesWithInheritance`)
- ✅ API returns `inherited: true/false` flag
- ✅ API returns `inheritedFrom: "ParentClass"` metadata
- ✅ Tables show inheritance indicators (↑ symbol)

**Design for Individual Creation**:

**Property Display**:
```
┌─────────────────────────────────────────┐
│  Create Person Individual                │
├─────────────────────────────────────────┤
│  Basic Information                       │
│  ├─ Name * (datatype: xsd:string)      │
│  ├─ Age (datatype: xsd:integer)         │
│  └─ Email (datatype: xsd:string)        │
│                                          │
│  Inherited from Entity ↑                 │
│  ├─ Created Date ↑ (datatype: xsd:date) │
│  └─ Creator ↑ (object: Person)         │
│                                          │
│  Inherited from Agent ↑                 │
│  └─ Status ↑ (datatype: xsd:string)    │
└─────────────────────────────────────────┘
```

**Implementation Strategy**:
1. Fetch all properties using existing API (`/api/ontology/classes/{class}/all-properties`)
2. Group properties by inheritance source
3. Display with visual indicators
4. Form fields show tooltip: "Inherited from {parentClass}"
5. Values submitted to backend include ALL properties

**Form Validation**:
- Inherited properties: Optional unless marked required in parent
- Direct properties: Validate against class constraints
- Object properties: Validate referenced individuals exist

---

### 3. Name Column vs ID/UUID

**Current Issue**: Tables have hardcoded "Name" column, but individuals should use a proper identifier

**Analysis**:

**Current Behavior**:
```javascript
// Line 31541: Individual table display
let displayName = individual.name || individual.instance_name || 'Unnamed';
```

**Problem**: 
- Assumes every individual has a "name" property
- Doesn't respect ontology design (if class wants an ID instead)
- Mixes display name with identifier

**RDF Best Practice**:
- **URI**: True identifier (`<ontology#Person_john>`) - system generated
- **rdfs:label**: Display name (optional, user-defined)
- **Custom properties**: All other attributes (e.g., `hasName`, `personID`)

**Recommended Solution**:

1. **Primary Identifier Column**: Always show URI or UUID
   ```javascript
   <th>ID</th>  // Shows: http://ontology#Person_abc123 or abc-123
   ```

2. **Label Column**: Only if class has `rdfs:label` or `hasName` property
   ```javascript
   // Detect if class has a 'name' property
   const hasNameProperty = properties.some(p => 
     p.name === 'rdfs:label' || p.name === 'hasName' || p.name === 'name'
   );
   
   if (hasNameProperty) {
     html += '<th>Name</th>';
   }
   ```

3. **Dynamic Columns**: Show all other properties as columns
   ```javascript
   properties.forEach(prop => {
     html += `<th>${prop.label}</th>`;
   });
   ```

**Backend Consideration**:
- Store UUID in database (`instance_id`)
- Generate URI in Fuseki based on name + UUID
- Allow user to set label/name as a property value

**Recommended Change**:
```javascript
// Always show ID column
html += '<th style="min-width: 120px;">ID</th>';

// Optionally show Name column if property exists
const nameProp = properties.find(p => 
  ['name', 'hasName', 'rdfs:label'].includes(p.name.toLowerCase())
);
if (nameProp) {
  html += `<th>${nameProp.label}</th>`;
}

// Then properties
properties.forEach(prop => {
  // Skip if this property is displayed as Name
  if (nameProp && prop.name === nameProp.name) return;
  html += `<th>${prop.label}</th>`;
});
```

---

### 4. Individual Identifiers: URI vs UUID

**Question**: Should individuals use URIs (`<ontology#Person_john>`) or UUIDs?

**Current Implementation**:
```python
# backend/api/individuals.py line 827
individual_uri = f"{graph_iri}#{individual.name}_{uuid.uuid4().hex[:8]}"
```

**Analysis**:

**Option A: URI-Based** (Current)
- ✅ Semantic and human-readable
- ✅ RDF standard
- ✅ Good for references in MTs
- ❌ Can have collisions if names repeat
- ❌ Harder to track if name changes

**Option B: UUID-Based**
- ✅ Globally unique
- ✅ Name changes don't affect ID
- ✅ Database-friendly
- ❌ Not human-readable
- ❌ Less semantic

**Option C: Hybrid** (Recommended)
- **Database**: Store UUID as primary key
- **Fuseki URI**: Use UUID in URI: `<ontology#Person_abc123def>`
- **Display**: Show UUID in table, optionally show label property
- **User Input**: Collect label/name as a property value

**Recommendation**: **Option C**

```python
# Generate URI from UUID
instance_id = str(uuid.uuid4())
individual_uri = f"{graph_iri}#{instance_id[:12]}"  # abc123def456

# Store in Fuseki
triples = [
    f"<{individual_uri}> rdf:type ?class .",
    f"<{individual_uri}> rdfs:label \"{individual.name}\" ."  # User-friendly name
]
```

---

### 5. Form Implementation Strategy

**Dynamic Form Generation**:

```javascript
async function generateAddIndividualForm(className, classData, properties) {
  // Group properties by inheritance
  const directProps = properties.filter(p => !p.inherited);
  const inheritedProps = properties.filter(p => p.inherited);
  
  // Group inherited by parent
  const inheritedByParent = {};
  inheritedProps.forEach(prop => {
    const parent = prop.inheritedFrom;
    if (!inheritedByParent[parent]) {
      inheritedByParent[parent] = [];
    }
    inheritedByParent[parent].push(prop);
  });
  
  let html = `
    <div class="modal-form">
      <h2>Create ${className}</h2>
      
      <!-- Direct Properties -->
      <div class="form-section">
        <h3>Properties</h3>
        ${directProps.map(prop => generateFieldHTML(prop)).join('')}
      </div>
      
      <!-- Inherited Properties, grouped by parent -->
      ${Object.entries(inheritedByParent).map(([parent, props]) => `
        <div class="form-section inherited">
          <h3>Inherited from ${parent} <span class="inherited-icon">↑</span></h3>
          ${props.map(prop => generateFieldHTML(prop, true)).join('')}
        </div>
      `).join('')}
      
      <div class="form-actions">
        <button onclick="cancelForm()">Cancel</button>
        <button onclick="createIndividual('${className}')">Create</button>
      </div>
    </div>
  `;
  
  return html;
}

function generateFieldHTML(prop, inherited = false) {
  const inputType = getInputType(prop);
  const required = prop.required ? '*' : '';
  const tooltip = inherited ? `title="Inherited from ${prop.inheritedFrom}"` : '';
  
  return `
    <div class="form-field" ${tooltip}>
      <label>
        ${prop.label} ${required}
        ${inherited ? '<span class="inherited-badge">↑</span>' : ''}
      </label>
      ${generateInputForType(prop, inputType)}
      ${prop.comment ? `<small>${prop.comment}</small>` : ''}
    </div>
  `;
}

function getInputType(prop) {
  // Map property range to input type
  if (prop.type === 'object') return 'select';  // Dropdown of individuals
  if (prop.enumeration_values) return 'select';  // Enum
  if (prop.range === 'xsd:integer' || prop.range === 'xsd:decimal') return 'number';
  if (prop.range === 'xsd:date' || prop.range === 'xsd:dateTime') return 'date';
  if (prop.range === 'xsd:boolean') return 'checkbox';
  return 'text';
}
```

---

## Implementation Recommendations

### Phase 1: Form-Based Creation (Recommended Start)
1. ✅ Use dynamic form generation
2. ✅ Group properties by inheritance
3. ✅ Show visual inheritance indicators
4. ✅ Handle all property types (datatype, object, inherited)
5. ✅ Use UUID-based identifiers
6. ✅ Store label as `rdfs:label` property

### Phase 2: Table Display Enhancement
1. Fix "Name" column to be dynamic based on properties
2. Add ID column showing UUID
3. Show name property only if it exists
4. Make simple properties editable inline

### Phase 3: Advanced Features
1. Bulk import from CSV
2. Template-based creation
3. Duplicate individual
4. Inline editing for power users

---

## Migration Path

**Current State**:
- Table shows "Name" column hardcoded
- No way to create individuals

**Step 1**: Implement form-based creation with UUID IDs
**Step 2**: Update table to show ID column + conditional Name column
**Step 3**: Add inline editing for simple properties
**Step 4**: Add bulk operations

---

## Summary of Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Editing Pattern** | Form-based (with future inline option) | Better for complex inheritance and validation |
| **Property Display** | Grouped by inheritance source | Clear visual hierarchy |
| **Identifiers** | UUID-based URIs | Globally unique, stable |
| **Name Column** | Dynamic based on properties | Respects ontology design |
| **Form Fields** | Dynamic based on property type | Handles all property types |

---

## Open Questions

1. Should we support owl:sameAs for linking individuals?
2. How to handle multi-value properties in form?
3. Should object properties allow creating new individuals inline?
4. Do we need fuzzy search for object property references?
5. Should validation happen client-side or server-side?

---

## References

- Current implementation: `frontend/app.html` lines 29851-31598
- Backend API: `backend/api/individuals.py`
- Inheritance system: `backend/api/ontology.py` line 736
- Property detection: `frontend/app.html` line 29960
