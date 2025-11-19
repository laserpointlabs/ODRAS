# CQMT Ontology Synchronization Issue

> **Architectural Assessment**: This is NOT an architectural flaw—it's a missing implementation feature. See `CQMT_ARCHITECTURAL_ASSESSMENT.md` for detailed analysis comparing our architecture to industry standards.

## Problem Statement

The CQMT Workbench has a synchronization problem where test data stored in Microtheories (MTs) references ontology elements by their IRIs (e.g., `hasCapacity` property). When ontology elements are renamed or modified in the ontology graph, the MT test data continues to reference the old IRIs, causing CQ tests to fail.

### Example Scenario

1. **Initial State**:
   - Ontology defines property: `http://example.org/ontology#hasCapacity`
   - Microtheory stores test data: `:C130 :hasCapacity "92 passengers" .`
   - CQ queries: `SELECT ?capacity WHERE { ?aircraft :hasCapacity ?capacity }`

2. **User Changes Ontology**:
   - Renames property from `hasCapacity` to `hasCapacity1`
   - Saves ontology (updates ontology graph)

3. **Result**:
   - Microtheory still has: `:C130 :hasCapacity "92 passengers" .`
   - CQ now queries: `SELECT ?capacity WHERE { ?aircraft :hasCapacity1 ?capacity }`
   - **Test fails**: No results because old property name still referenced in MT

## Root Cause Analysis

### Architecture Overview

```
┌─────────────────────┐         ┌──────────────────────┐
│   Ontology Graph    │         │   Microtheory (MT)   │
│   (in Fuseki)       │         │   (Named Graph)      │
├─────────────────────┤         ├──────────────────────┤
│ Class: Aircraft     │         │ :C130 rdf:type       │
│ Prop: hasCapacity   │───X───→│   :TransportPlane .  │
│ Prop: hasCapacity1  │         │ :C130 :hasCapacity   │
│                     │         │   "92 passengers" .  │
└─────────────────────┘         └──────────────────────┘
      ↑ Changed                      ↑ Stale Reference
```

### Why This Happens

1. **Decoupled Storage**: Ontology definitions and MT test data are stored separately:
   - Ontology: Original definition graph (e.g., `http://example.org/ontology`)
   - Microtheory: Named graph containing test instances (e.g., `http://localhost:8000/mt/project123/baseline`)

2. **No Referential Integrity**: MT triples reference ontology IRIs via strings/literal patterns:
   - `:hasCapacity` expands to `<http://example.org/ontology#hasCapacity>`
   - MT has no tracking of which IRIs it references

3. **No Change Propagation**: When ontology saves occur:
   - Only the ontology graph is updated
   - No mechanism exists to update dependent MTs
   - No validation checks for broken references

### Current Code Evidence

From `scripts/test_cqmt_setup.py` (lines 213-219):
```python
:C130 a :TransportPlane ;
    rdfs:label "C-130 Hercules" ;
    :hasCapacity "92 passengers" .
```

From `scripts/cqmt_ui_test.py` (lines 146-149):
```python
<{graph_iri}#hasCapacity> a owl:DatatypeProperty ;
    rdfs:label "has Capacity" ;
    rdfs:domain <{graph_iri}#TransportPlane> ;
    rdfs:range rdfs:Literal .
```

## Impact Assessment

### Is This Actually a Problem?

**YES** - This is a legitimate problem because:

1. **Test-Driven Development Fails**: The core purpose of CQMT is to validate ontology changes through tests. If tests become stale due to broken references, the validation cycle breaks.

2. **Maintenance Burden**: Users must manually:
   - Track which MTs use which properties
   - Manually update all MT references after ontology changes
   - Potentially recreate test data if references become unclear

3. **User Experience**: Silent failures are confusing:
   - CQ fails with "no results" but no explanation why
   - User might think ontology is wrong, not realizing MT has stale data

4. **Data Integrity**: MT test data can become orphaned:
   - References to deleted properties remain
   - No way to validate MT triples against current ontology

### When Is This NOT a Problem?

- When ontology elements are never renamed (static ontologies)
- When MTs are recreated after every ontology change
- When CQs are updated manually to match ontology changes

### Real-World Frequency

Based on typical ontology development workflows:
- **Common**: Property renaming during refinement (e.g., `hasCapacity` → `passengerCapacity`)
- **Common**: Class renaming for clarity (e.g., `Aircraft` → `AirVehicle`)
- **Less Common**: Deleting properties (usually deprecated instead)
- **Rare**: Complete ontology restructure

## Solution Approaches

### Option 1: Track Ontology Dependencies (RECOMMENDED)

**Concept**: Maintain a mapping of which MTs reference which ontology elements.

**Implementation**:
1. Parse MT triples to extract referenced IRIs
2. Store dependency mapping in PostgreSQL
3. On ontology save, detect changes
4. Notify user of affected MTs
5. Provide one-click update option

**Pros**:
- Non-invasive: Doesn't break existing workflow
- User-controlled: User decides when to update
- Auditable: Can see what depends on what
- Efficient: Only updates affected MTs

**Cons**:
- Requires dependency tracking infrastructure
- Doesn't auto-fix (requires user action)

### Option 2: Auto-Sync on Save

**Concept**: Automatically update MT triples when ontology changes.

**Implementation**:
1. Track MT content in PostgreSQL (not just Fuseki)
2. On ontology save, detect element changes
3. Automatically update all affected MTs
4. Report changes to user

**Pros**:
- Automatic: No user intervention needed
- Always up-to-date: MTs always match ontology

**Cons**:
- Can lose test data if not careful
- Expensive: Requires parsing/updating all MTs
- May break intentional test scenarios
- Risk of data loss

### Option 3: Validation Without Auto-Fix

**Concept**: Detect broken references but don't fix them automatically.

**Implementation**:
1. Parse MT triples periodically
2. Validate references against current ontology
3. Report broken references to user
4. Mark CQs as "likely broken"

**Pros**:
- Safe: No risk of data loss
- Informative: User knows what's wrong
- Simple: Minimal infrastructure needed

**Cons**:
- Doesn't solve the problem
- Manual fixes still required
- Doesn't prevent the issue

### Option 4: Immutable Test Data

**Concept**: Store test data with fully-qualified IRIs and never update it.

**Implementation**:
1. Always use full IRIs in MT triples
2. When ontology changes, create new version
3. Keep old MTs as historical snapshots
4. CQs reference specific ontology versions

**Pros**:
- Preserves test history
- No synchronization needed
- Clear versioning

**Cons**:
- Proliferates MTs over time
- Complex version management
- Not intuitive for users

## Recommended Solution: Hybrid Approach

Combine **Option 1** (Track Dependencies) with **Option 3** (Validation):

### Phase 1: Dependency Tracking (MVP)

**Database Schema Addition**:
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

CREATE INDEX idx_mt_deps_element ON mt_ontology_dependencies(referenced_element_iri);
CREATE INDEX idx_mt_deps_valid ON mt_ontology_dependencies(is_valid);
```

**Implementation Steps**:

1. **Extract Dependencies**: When MT is created/updated, parse triples and extract referenced IRIs
2. **Store Mapping**: Insert into `mt_ontology_dependencies` table
3. **Validate Periodically**: Query Fuseki to check if IRIs still exist
4. **Report Issues**: UI shows warning badges on MTs with broken references

**API Enhancement**:
```python
# New endpoint
@router.get("/microtheories/{mt_id}/dependencies")
async def get_mt_dependencies(mt_id: str):
    """Get list of ontology elements this MT depends on"""
    
# New endpoint  
@router.get("/microtheories/{mt_id}/validation")
async def validate_mt_references(mt_id: str):
    """Check if all referenced ontology elements still exist"""
```

### Phase 2: Change Detection and Notification

**On Ontology Save**:
1. Detect changed elements (new/renamed/deleted properties/classes)
2. Query `mt_ontology_dependencies` to find affected MTs
3. Return warning to user: "3 MTs reference changed elements"
4. Provide UI option to "Update affected MTs"

**Suggested User Flow**:
```
User saves ontology with renamed property
  ↓
System: "This change affects 2 microtheories. Update them?"
  [Yes] [Later] [Cancel]
  ↓
User clicks "Yes"
  ↓
System updates MT triples automatically
  ↓
System: "Updated 2 microtheories successfully"
```

### Phase 3: Smart Update (Future)

**Auto-Update Logic**:
1. Parse both old and new ontology
2. Build mapping: `old_iri → new_iri`
3. For each affected MT:
   - Parse all triples
   - Replace old IRIs with new IRIs
   - Validate against new ontology
   - Commit updates

**Edge Cases**:
- Element deleted: Mark MT as "needs review"
- Element renamed: Update automatically
- Property type changed: Warn user
- Domain/range changed: Validate existing data

## Implementation Plan

### Step 1: Database Migration
- [ ] Add `mt_ontology_dependencies` table
- [ ] Add indexes for performance
- [ ] Migration script to populate from existing MTs

### Step 2: Dependency Extraction Service
- [ ] Parse MT triples to extract IRIs
- [ ] Classify by element type (Class/Property)
- [ ] Store in dependency table
- [ ] Update on MT create/update

### Step 3: Validation Service
- [ ] Query Fuseki for element existence
- [ ] Mark dependencies as valid/invalid
- [ ] Batch validation for performance

### Step 4: Change Detection
- [ ] Hook into ontology save workflow
- [ ] Detect element changes
- [ ] Query dependency table
- [ ] Generate notification

### Step 5: UI Updates
- [ ] Badge on MT list showing broken references
- [ ] Dependency list in MT details
- [ ] Update confirmation dialog
- [ ] Success/error feedback

### Step 6: Testing
- [ ] Unit tests for dependency extraction
- [ ] Integration tests for change detection
- [ ] End-to-end tests for update workflow
- [ ] Manual testing with real ontology changes

## Alternative: Defer Implementation

If this is not urgent, consider:

1. **Document Best Practices**: Guide users to recreate MTs after major ontology changes
2. **Warning Messages**: Show warnings in UI about ontology-MT sync
3. **Validation Tool**: Manual tool to check MT integrity
4. **Monitor Issue**: Track how often this problem occurs in practice

## Architectural Context

**Important**: The proposed solutions are NOT bandaids—they're **standard industry infrastructure**:

- Dependency tracking is a **standard feature** in enterprise ontology systems
- Change detection is **common practice** in knowledge graph management
- Version management aligns with our existing versioning strategy doc
- Migration tooling is **expected** in professional ontology platforms

Our architecture is **sound**—we follow Semantic Web best practices with named graphs, SPARQL, and proper separation. What we're adding is the **supporting infrastructure** that professional systems provide.

See `CQMT_ARCHITECTURAL_ASSESSMENT.md` for detailed comparison to industry standards.

## Conclusion

**The issue is real and should be addressed**, but it can be phased:

- **Short-term**: Add validation and warnings (Phase 1)
- **Medium-term**: Add change detection (Phase 2)  
- **Long-term**: Add smart updates (Phase 3)

The recommended approach balances user needs with implementation complexity, providing value incrementally while avoiding risky automatic updates.
