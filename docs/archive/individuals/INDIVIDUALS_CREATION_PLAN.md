# Individuals Creation Implementation Plan

## Problem Statement

The ontology workbench has an "Individuals" tab that displays individuals for each class, but there's no way to manually create individuals through the UI. Currently, the `showAddIndividualDialog` function just shows an alert saying "Coming soon!".

**Current State:**
- ✅ Backend API exists (`POST /api/individuals/{project_id}/individuals/{class_name}`)
- ✅ UI displays individuals in tables
- ✅ Tables show all properties (including inherited ones)
- ❌ No form to create new individuals
- ❌ No ability to set property values

**Goal:**
Enable users to create individuals with all their properties (data properties, object properties, and inherited properties) through a dynamic form UI.

## Current Architecture

### Backend API
- **Endpoint**: `POST /api/individuals/{project_id}/individuals/{class_name}`
- **Request Body**: 
  ```json
  {
    "name": "individual_name",
    "class_type": "ClassName",
    "properties": {
      "property1": "value1",
      "property2": "value2"
    }
  }
  ```
- **Implementation**: `backend/api/individuals.py` line 294-325
- Creates individual in Fuseki using SPARQL INSERT

### Frontend UI
- **Location**: `frontend/app.html` line 29851-29853
- **Current Implementation**: Placeholder alert
- **Table Rendering**: `generateClassTableWithIndividuals` (line 31474)
- **Property Display**: Shows all properties including inherited ones

## Implementation Plan

### Phase 1: Dynamic Form Generation

**Goal**: Generate a form based on class properties

**Tasks:**

1. **Modify `showAddIndividualDialog` function** (line 29851)
   - Accept `className` and optionally `classData` and `properties`
   - Generate dynamic form HTML based on properties
   - Include all direct and inherited properties
   - Add property type information (datatype vs object)

2. **Create `generateAddIndividualForm` function**
   - Input: `className`, `classData`, `properties`
   - Output: HTML string for modal form
   - For each property:
     - Label with inheritance indicator
     - Input field (text, number, date, select, etc.)
     - Validation rules based on property type
     - Units display if available
     - Required indicator

3. **Property Input Types**:
   - **Datatype properties**: Text, number, date based on range
   - **Object properties**: Dropdown of existing individuals of that class
   - **Boolean**: Checkbox
   - **Enumeration**: Select dropdown
   - **Multi-value**: Allow multiple selections

4. **Form Features**:
   - Modal dialog (reuse existing modal system)
   - Cancel/Save buttons
   - Client-side validation
   - Loading state during submission
   - Error handling

### Phase 2: API Integration

**Goal**: Connect form to backend API

**Tasks:**

1. **Create `createIndividual` function**
   - Collect form data
   - Validate required fields
   - Map form inputs to API request format
   - Call `POST /api/individuals/{project_id}/individuals/{class_name}`
   - Handle success/error responses
   - Refresh table on success

2. **Handle different property types**:
   - String values: Direct assignment
   - IRI values: Full IRI form
   - Numbers: Proper formatting
   - Dates: ISO format

3. **Error Handling**:
   - Display validation errors
   - Show API error messages
   - Handle network failures

### Phase 3: Edit and Delete

**Goal**: Enable editing and deleting existing individuals

**Tasks:**

1. **Modify `editIndividual` function** (currently placeholder at line 31580)
   - Fetch individual data
   - Populate form with existing values
   - Reuse add form with different mode
   - Call update API

2. **Modify `deleteIndividual` function** (currently placeholder at line 31581)
   - Show confirmation dialog
   - Call delete API
   - Refresh table

3. **Update APIs**:
   - `PUT /api/individuals/{project_id}/individuals/{class_name}/{individual_id}` (line 327)
   - `DELETE /api/individuals/{project_id}/individuals/{class_name}/{individual_id}` (line 356)

### Phase 4: Enhanced Features

**Goal**: Polish the user experience

**Tasks:**

1. **Inheritance Display**:
   - Show inheritance hierarchy in form
   - Visually distinguish inherited properties
   - Tooltips for inherited properties

2. **Property Information**:
   - Show property descriptions/comments
   - Display cardinality constraints
   - Indicate required vs optional

3. **Data Validation**:
   - Validate against ontology constraints
   - Check cardinality limits
   - Verify data types

4. **Bulk Operations**:
   - Import from CSV
   - Duplicate individual
   - Template-based creation

## Technical Details

### Data Structures

**Property Format** (from `getClassProperties`):
```javascript
{
  name: "propertyName",
  label: "Property Label",
  type: "datatype" | "object",
  domain: "ClassName",
  range: "xsd:string" | "ClassName",
  inherited: true | false,
  inheritedFrom: "ParentClass",
  units: "kg",
  cardinality: { min: 0, max: 1 }
}
```

**Individual Data Format**:
```javascript
{
  instance_id: "uuid",
  name: "individual_name",
  properties: {
    "property1": "value1",
    "property2": "value2"
  }
}
```

### API Calls Needed

1. **Get class properties** (already exists):
   - Function: `getClassProperties(className, ontologyData)`
   - Returns: Array of property objects

2. **Create individual**:
   ```javascript
   fetch(`/api/individuals/${projectId}/individuals/${className}`, {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       name: formData.name,
       class_type: className,
       properties: formData.properties
     })
   })
   ```

3. **Update individual**:
   ```javascript
   fetch(`/api/individuals/${projectId}/individuals/${className}/${individualId}`, {
     method: 'PUT',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       name: formData.name,
       properties: formData.properties
     })
   })
   ```

4. **Delete individual**:
   ```javascript
   fetch(`/api/individuals/${projectId}/individuals/${className}/${individualId}`, {
     method: 'DELETE',
     headers: {
       'Authorization': `Bearer ${token}`
     }
   })
   ```

### Modal System

Reuse existing modal infrastructure in `app.html`:
- Search for "showModal" or "modal" functions
- Use existing modal HTML/CSS
- Create modal container dynamically

## Implementation Steps

### Step 1: Form Generation (Frontend)
1. Update `showAddIndividualDialog` (line 29851)
2. Create `generateAddIndividualForm` function
3. Add modal HTML generation
4. Style form appropriately

### Step 2: Form Submission (Frontend)
1. Create `createIndividual` function
2. Add form validation
3. Handle API response
4. Refresh table on success

### Step 3: Edit Functionality (Frontend)
1. Update `editIndividual` function
2. Create edit mode for form
3. Handle update API call

### Step 4: Delete Functionality (Frontend)
1. Update `deleteIndividual` function
2. Add confirmation dialog
3. Handle delete API call

### Step 5: Backend Updates (if needed)
1. Review `create_fuseki_individual` implementation
2. Implement `update_fuseki_individual` (currently placeholder)
3. Implement `delete_fuseki_individual` (currently placeholder)
4. Test all endpoints

### Step 6: Testing
1. Test creating individuals with data properties
2. Test creating individuals with object properties
3. Test creating individuals with inherited properties
4. Test editing existing individuals
5. Test deleting individuals
6. Test validation

## Dependencies

- Existing modal system
- `getClassProperties` function (for inheritance-aware properties)
- Backend API endpoints (mostly implemented)
- Authentication token system

## Risk Assessment

**Low Risk:**
- Form generation (pure UI)
- Client-side validation
- Conceptualizer integration (separate source types)
- Units management (simple string-based approach sufficient)

**Medium Risk:**
- Property type handling (datatype vs object)
- IRI resolution for object properties
- Backend UPDATE/DELETE implementations (may need work)

**High Risk:**
- None identified

## Impact Analysis

### Conceptualizer Integration
**Impact**: **NO IMPACT** ✅

**Why Safe**:
- Conceptualizer uses `source_type = "das_generated"`
- Manual creation uses `source_type = "manual"`
- Both use same `individual_instances` table
- Same storage mechanism, no conflicts

**Verification**:
- ✅ UUID-based identifiers prevent name collisions
- ✅ Different source types distinguish origins
- ✅ Same table structure supports both

### Data Flow Architecture
**Recommendation**: Add Data Manager Workbench (Phase 3)

**Current State**: Workbenches loosely coupled
**Future State**: Standardized export/import APIs with pipeline manager
**Benefits**: Clear data flow, no direct coupling

See `INDIVIDUALS_ARCHITECTURE_ANALYSIS.md` for detailed analysis.

## Estimated Effort

- **Phase 1**: 4-6 hours
- **Phase 2**: 2-3 hours
- **Phase 3**: 3-4 hours
- **Phase 4**: 4-6 hours
- **Total**: 13-19 hours

## Priority

**High** - Required for CQMT testing functionality. Users need to create individuals to populate microtheories.

## Open Questions

1. Should we validate against ontology constraints in real-time or on submit?
2. How should we handle multi-value properties (arrays)?
3. Should object properties be IRI references or names?
4. Do we need fuzzy search for object property selection?
5. Should we persist the form state if user navigates away?

## References

- Backend API: `backend/api/individuals.py`
- Frontend Table Rendering: `frontend/app.html` line 31474
- Property System: `getClassProperties` function
- CQMT Integration: Need individuals to test competency questions
