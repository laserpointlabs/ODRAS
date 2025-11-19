# Individuals Architecture Analysis & Planning

## Overview

This document addresses architectural concerns about individuals creation, conceptualizer integration, data management, and units handling in ODRAS.

## 1. Conceptualizer Impact Analysis

### Current Conceptualizer Flow

**Process**:
1. User selects a root individual (e.g., a Requirement)
2. DAS analyzes the individual and ontology
3. Generates concepts (individuals) for related classes
4. Stores concepts in `individual_instances` table
5. Creates configuration with nested structure

**Code Flow**:
```
backend/api/configurations.py (line 870)
├─ GET individual from database (line 886-894)
├─ Fetch ontology structure from Fuseki (line 911)
├─ Call DAS to generate concepts (line 924)
├─ For each concept:
│  ├─ Generate instance_id = UUID() (line 957)
│  ├─ Generate instance_uri = f"{graph_iri}#{concept_id}" (line 958)
│  ├─ Insert into individual_instances (line 960-970)
│  └─ Set source_type = "das_generated" (line 968)
└─ Create configuration from concepts (line 984)
```

**Database Schema**:
```sql
individual_instances (
    instance_id UUID PRIMARY KEY,
    table_id UUID REFERENCES individual_tables_config,
    class_name VARCHAR(100),
    instance_name VARCHAR(255),  -- ODRAS ID
    instance_uri TEXT,
    properties JSONB,
    source_type VARCHAR(50),  -- 'das_generated', 'manual', etc.
    ...
)
```

### Impact of Manual Individual Creation

**What Changes**:
- Adding form-based individual creation in ontology workbench
- Users can manually create individuals
- Stored in same `individual_instances` table

**What Doesn't Change**:
- Database schema stays the same ✅
- API endpoints stay the same ✅
- Conceptualizer code stays the same ✅
- Data flow stays the same ✅

**Risk Assessment**: **LOW RISK** ✅

**Why Safe**:
1. **Separate source types**: 
   - Conceptualizer uses `source_type = "das_generated"`
   - Manual creation uses `source_type = "manual"`
   - No conflict between them

2. **Same storage mechanism**:
   - Both use `individual_instances` table
   - Both use `instance_id` (UUID) as primary key
   - Both store properties as JSONB

3. **No coupling**:
   - Conceptualizer doesn't read/write individuals differently
   - Just inserts rows into same table

**Potential Issues**:
- **Name Collision**: If manual create uses same `instance_name` as DAS
  - **Mitigation**: UUID-based `instance_id` prevents conflicts
  - **Recommendation**: Use UUID-based identifiers (as discussed in design doc)

**Verification Needed**:
- ✅ Conceptualizer uses UUID for `instance_id`
- ✅ Conceptualizer sets `source_type = "das_generated"`
- ✅ Our manual creation will set `source_type = "manual"`
- ✅ Both use same table structure

**Conclusion**: 
- **NO IMPACT** on conceptualizer functionality
- Conceptualizer will continue to work exactly as before
- Users can manually create individuals without breaking DAS

---

## 2. Configurator for Manual Table Configuration

### Requirement

**Current State**:
- Conceptualizer creates nested ontology-based tables automatically
- User wants manual way to create same structure

**Desired Feature**:
A "configurator" that allows users to manually create ontology/constraint-based nested tables (like conceptualizer output but without DAS).

### Analysis

**What Conceptualizer Does**:
1. Takes a root individual (e.g., Requirement)
2. Analyzes ontology structure
3. Creates individuals for related classes
4. Builds nested configuration structure
5. Links individuals via object properties

**Manual Configurator Would Do**:
1. User selects a class to configure
2. Configurator shows all related classes (from ontology)
3. User manually creates individuals for each class
4. User links individuals via object properties
5. Builds same nested structure

### Best Practice: Where Should This Live?

**Option A: Conceptualizer Workbench** ✅ **RECOMMENDED**
- **Pros**:
  - Conceptualizer already handles configuration
  - Same UI patterns (ontology selection, individual selection)
  - Same data structures (individuals, configurations)
  - Natural workflow: "Generate with DAS" or "Configure Manually"
- **Cons**:
  - Adds complexity to conceptualizer workbench
  - Could confuse users about DAS vs manual

**Option B: Ontology Workbench** ❌ **NOT RECOMMENDED**
- **Pros**:
  - Already has individuals tables
- **Cons**:
  - Doesn't handle configurations
  - Doesn't understand nested structures
  - Would duplicate functionality

**Option C: New Configuration Workbench** ⚠️ **FUTURE**
- **Pros**:
  - Clear separation of concerns
  - Focused on configuration
- **Cons**:
  - Adds another workbench
  - More complex to navigate
  - Duplicates ontology navigation

### Recommendation: **Option A**

**Implementation Approach**:
```
Conceptualizer Workbench
├─ Generate Configuration (existing)
│  └─ Conceptualize and Store (DAS-driven)
└─ Configure Manually (new)
   ├─ Select Root Class
   ├─ Create Individuals Wizard
   │  ├─ Step 1: Create root individual
   │  ├─ Step 2: Create related individuals
   │  └─ Step 3: Link individuals
   └─ Generate Configuration
```

**Benefits**:
- Users can choose: DAS-generated or manually-configured
- Same output format (configurations)
- No new workbench needed
- Natural addition to existing workflow

**User Flow**:
1. Open Conceptualizer Workbench
2. Select ontology
3. Choose mode:
   - "Generate with DAS" (existing button)
   - "Configure Manually" (new button)
4. If manual:
   - Select root class (e.g., "System")
   - Wizard guides through creating related individuals
   - Link individuals via object properties
   - Generate configuration

---

## 3. Data Manager Workbench

### Requirement

**Concern**: Don't want to directly couple workbenches. Need a data manager that allows users to connect data flows between projects, workbenches, etc.

### Analysis

**Current State**:
- Workbenches are loosely coupled
- Each workbench manages its own data
- No centralized data flow management

**Your Concern**:
- Workbenches shouldn't directly depend on each other
- Need a layer for data flow between them
- Need cross-project data management

### Architectural Pattern: **Data Pipeline Manager**

**Concept**:
A workbench-agnostic data flow manager that handles:
- Data export from workbenches
- Data import to workbenches
- Data transformation
- Cross-project data sharing
- Workbench-to-workbench pipelines

**Architecture**:
```
Data Manager Workbench
├─ Data Sources
│  ├─ Requirements Workbench → Export requirements
│  ├─ Ontology Workbench → Export individuals
│  ├─ CQMT Workbench → Export CQs/MTs
│  └─ Conceptualizer → Export configurations
├─ Data Destinations
│  ├─ Requirements Workbench ← Import requirements
│  ├─ Ontology Workbench ← Import individuals
│  ├─ CQMT Workbench ← Import CQs/MTs
│  └─ Conceptualizer ← Import configurations
└─ Pipelines
   ├─ Requirements → Individuals
   ├─ Individuals → Microtheories
   ├─ Ontology → CQMT
   └─ Configurations → Export/Import
```

**Benefits**:
- **No coupling**: Workbenches don't know about each other
- **Flexible**: Easy to add new workbenches
- **Transparent**: Clear data flow visibility
- **Reusable**: Same pipeline for multiple projects

**Implementation**:
1. **Data Manager Workbench** (new workbench)
   - List of available data sources
   - List of available data destinations
   - Pipeline builder (drag-and-drop)
   - Pipeline execution and monitoring

2. **Export/Import Adapters** (one per workbench)
   - Requirements Workbench adapter
   - Ontology Workbench adapter
   - CQMT Workbench adapter
   - Conceptualizer adapter

3. **Pipeline Engine** (backend service)
   - Execute pipelines
   - Transform data between formats
   - Handle errors and retries
   - Log execution history

**Example Pipeline**:
```
Requirements Workbench → Export Requirements as JSON
                     ↓
Data Manager → Transform to Individuals format
                     ↓
Ontology Workbench → Import Individuals
```

**Best Practice**: **Service-Oriented Architecture**
- Each workbench exposes standardized export/import APIs
- Data Manager orchestrates data flow
- No direct workbench-to-workbench communication

---

## 4. Units Management

### Requirement

How should we plan for managing units?

### Current State

**Units Storage**:
```python
# backend/api/ontology.py line 43
units: Optional[str] = Field(None, description="Units of measure (e.g., 'm', 'kg', 'ft')")
```

**Units Display**:
```javascript
// frontend/app.html line 31508
const unitsText = prop.units ? ` (${prop.units})` : '';
```

**Units Storage in Fuseki**:
```python
# backend/services/ontology_manager.py line 358-360
if property_data.get("units"):
    units_uri = URIRef(f"{self.base_uri}/units")
    triples.append((prop_uri, units_uri, Literal(property_data["units"])))
```

### Analysis

**Current Implementation**:
- ✅ Units stored as property metadata
- ✅ Units displayed in tables
- ✅ Units passed to individuals creation

**What's Missing**:
- Unit validation
- Unit conversion
- Unit standards (SI, Imperial, etc.)
- Unit parsing from strings (e.g., "100 kg" → value=100, unit="kg")

### Best Practice: **Units as Property Constraints**

**RDF Approach**:
Use QUDT (Quantities, Units, Dimensions, and Data Types) ontology:
```turtle
ex:hasMass rdf:type owl:DatatypeProperty ;
    rdfs:range qudt:Mass ;
    qudt:unit qudt:Kilogram .
```

**ODRAS Approach** (Simpler for MVP):
1. **Store units as property metadata** (current)
2. **Display units in UI** (current)
3. **Validate units match** (future)
4. **Support unit conversion** (future)

**Recommendation**:

**Phase 1 (Current MVP)**:
- Keep simple string-based units
- Display units: `(kg)`, `(m)`, `(ft)`
- Store in property metadata
- ✅ **This is sufficient for now**

**Phase 2 (Future Enhancement)**:
- Integrate QUDT ontology
- Unit validation
- Unit conversion
- Unit parsing

**Phase 3 (Advanced)**:
- Dimensional analysis
- Automatic unit conversion
- Unit-aware calculations

**For Now**:
- ✅ Current implementation is acceptable
- ✅ No changes needed for units management
- ✅ Document as "simple units" in architecture
- ⚠️ Plan for QUDT integration later

---

## Summary & Recommendations

### 1. Conceptualizer Impact: **NO IMPACT** ✅
- Safe to add manual individual creation
- Same storage mechanism
- Different source types prevent conflicts

### 2. Configurator: **Add to Conceptualizer Workbench** ✅
- Keep in Conceptualizer
- Add "Configure Manually" mode
- Wizard-based individual creation
- Generates same configuration format

### 3. Data Manager: **New Workbench Needed** ✅
- Create Data Manager Workbench
- Standardized export/import APIs
- Pipeline builder for data flow
- Prevents workbench coupling

### 4. Units Management: **Current Implementation Sufficient** ✅
- Keep simple string-based units
- Document as MVP approach
- Plan QUDT integration for future

---

## Implementation Priority

### Phase 1: Manual Individual Creation (Immediate)
- **Priority**: HIGH
- **Risk**: LOW
- **Effort**: 13-19 hours
- **Dependencies**: None

### Phase 2: Configurator in Conceptualizer (Next)
- **Priority**: MEDIUM
- **Risk**: LOW
- **Effort**: 20-30 hours
- **Dependencies**: Manual individual creation

### Phase 3: Data Manager Workbench (Future)
- **Priority**: LOW
- **Risk**: MEDIUM
- **Effort**: 40-60 hours
- **Dependencies**: Stable export/import APIs

### Phase 4: Enhanced Units Management (Future)
- **Priority**: LOW
- **Risk**: LOW
- **Effort**: 20-30 hours
- **Dependencies**: QUDT ontology integration

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ODRAS Workbenches                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Requirements │  │   Ontology   │  │     CQMT     │      │
│  │  Workbench   │  │   Workbench  │  │   Workbench  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                   ┌────────▼─────────┐                       │
│                   │ Conceptualizer   │                       │
│                   │   Workbench      │                       │
│                   │  ┌────────────┐  │                       │
│                   │  │ Generate   │  │                       │
│                   │  │ with DAS   │  │                       │
│                   │  ├────────────┤  │                       │
│                   │  │ Configure  │  │                       │
│                   │  │ Manually   │  │                       │
│                   │  └────────────┘  │                       │
│                   └────────┬─────────┘                       │
│                            │                                  │
│                   ┌────────▼─────────┐                       │
│                   │   Data Manager   │  ← Future              │
│                   │    Workbench     │                       │
│                   │                  │                       │
│                   │  • Export APIs   │                       │
│                   │  • Import APIs   │                       │
│                   │  • Pipelines    │                       │
│                   └──────────────────┘                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. ✅ **Proceed with manual individual creation** (no conceptualizer impact)
2. ✅ **Add configurator to conceptualizer** (Phase 2)
3. ⚠️ **Plan Data Manager Workbench** (Phase 3)
4. ✅ **Keep simple units** (document approach)

All concerns addressed. Safe to proceed with implementation.
