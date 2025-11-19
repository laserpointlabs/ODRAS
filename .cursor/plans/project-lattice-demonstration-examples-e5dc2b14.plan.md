<!-- e5dc2b14-c75e-4390-8785-05f545752ef1 363a7417-58ce-41ea-8e99-a672fbeb7a98 -->
# Project Lattice Demonstration Examples

## Overview

Create example project lattice setups that demonstrate how ODRAS can self-grow a bootstrapped system through parent/child/cousin project relationships and data flow. These examples will showcase the lattice architecture for customer demonstrations, working within current limitations (requirements and ontology management are in refactoring).

## Domain Setup

**Current Default Domains** (from `backend/odras_schema.sql`):

- `avionics`, `mission-planning`, `systems-engineering`, `logistics`, `cybersecurity`, `communications`, `radar-systems`, `weapons-systems`

**Additional Domains Needed for Examples**:

- `cost` - Cost analysis and modeling (needed for scenarios)
- `foundation` - Foundational/abstract projects (needed for L0 examples)
- `structures` - Structural analysis (needed for Scenario 1)
- `analysis` - Analysis domain (needed for Scenario 1)

**Action**: Add these 4 domains to `backend/odras_schema.sql` in the default domains INSERT statement (lines 1207-1216). Insert them after the existing 8 domains with appropriate descriptions.

## Example Scenarios

### Scenario 1: Aircraft Development Workflow (FEA Example)

**Purpose**: Demonstrate vertical parent-child hierarchy with cross-domain cousin coordination

**Project Structure**:

- **L0 Foundation**: `aircraft-foundation` (foundation domain)
- **L1 Requirements**: `aircraft-requirements` (systems-engineering domain, parent: foundation)
- **L2 Loads Analysis**: `aircraft-loads` (structures domain, parent: requirements)
- **L3 FEA Analysis**: `aircraft-fea` (analysis domain, parent: loads)
- **L2 Cost Model**: `aircraft-cost` (cost domain, cousin to FEA)

**Relationships**:

- Parent-child chain: Foundation → Requirements → Loads → FEA
- Cousin: FEA coordinates_with Cost Model
- Cross-domain knowledge link: FEA → Requirements (for requirement reference)

**Data Flow Demonstration**:

1. Requirements project publishes `requirements.approved` event with max_weight, range data
2. Loads project subscribes and publishes `loads.calculated` event with wing_load, fuselage_load
3. FEA subscribes to both, performs analysis, publishes `fea.analysis_complete` with margin_of_safety, material, mass
4. Cost Model subscribes to FEA, receives mass/material data for cost calculation

### Scenario 2: Multi-Domain Program Bootstrap

**Purpose**: Demonstrate how a program can bootstrap from a single foundation project

**Project Structure**:

- **L0 Foundation**: `program-foundation` (foundation domain)
- **L1 SE Strategy**: `program-se-strategy` (systems-engineering domain, parent: foundation)
- **L1 Cost Strategy**: `program-cost-strategy` (cost domain, parent: foundation)
- **L1 Logistics Strategy**: `program-logistics-strategy` (logistics domain, parent: foundation)
- **L2 SE Tactical**: `program-se-tactical` (systems-engineering domain, parent: SE Strategy)
- **L2 Cost Analysis**: `program-cost-analysis` (cost domain, parent: Cost Strategy)
- **L3 SE Implementation**: `program-se-impl` (systems-engineering domain, parent: SE Tactical)

**Relationships**:

- All L1 projects are siblings (same parent, different domains)
- Cousin relationships: SE Tactical ↔ Cost Analysis, SE Implementation ↔ Cost Analysis
- Cross-domain knowledge links as needed

**Data Flow Demonstration**:

1. Foundation publishes foundational knowledge events
2. L1 strategies coordinate via cousin relationships
3. L2/L3 projects inherit from parents and coordinate across domains
4. Event cascade shows how system self-assembles

### Scenario 3: Simple 3-Project Bootstrap

**Purpose**: Minimal example showing basic lattice growth

**Project Structure**:

- **L1 Parent**: `parent-project` (systems-engineering domain)
- **L2 Child**: `child-project` (systems-engineering domain, parent: parent)
- **L2 Cousin**: `cousin-project` (cost domain, cousin to child)

**Relationships**:

- Parent → Child (vertical)
- Child ↔ Cousin (horizontal)

**Data Flow Demonstration**:

1. Parent publishes `parent.data_ready` event
2. Child subscribes, processes, publishes `child.processed` event
3. Cousin subscribes to child, receives processed data

## Implementation Approach

### Phase 1: Script-Based Setup

Create Python scripts in `scripts/demo/` that:

1. Create projects with proper hierarchy
2. Establish relationships (parent-child, cousin, knowledge links)
3. Set up event subscriptions
4. Publish initial events to demonstrate flow

### Phase 2: Documentation

Create demonstration guide in `docs/demos/` that:

1. Explains each scenario
2. Shows expected lattice structure
3. Documents data flow patterns
4. Provides talking points for customer demos

### Phase 3: Validation Scripts

Create test scripts that:

1. Verify project structure
2. Validate relationships
3. Test event flow
4. Check knowledge visibility

## Technical Details

### Script Structure

- `scripts/demo/create_lattice_example_1.py` - Simple 3-project bootstrap (START HERE)
- `scripts/demo/create_lattice_example_2.py` - Aircraft development workflow
- `scripts/demo/create_lattice_example_3.py` - Multi-domain program bootstrap
- `scripts/demo/validate_lattice.py` - Validation utility

### API Endpoints Used

- `POST /api/projects` - Create projects
- `POST /api/projects/{id}/relationships` - Create cousin relationships
- `POST /api/projects/{id}/knowledge-links` - Create cross-domain knowledge links
- `POST /api/projects/{id}/subscriptions` - Set up event subscriptions
- `POST /api/projects/{id}/publish-event` - Publish events
- `GET /api/projects/{id}/visible-knowledge` - Query knowledge visibility
- `GET /api/projects/{id}/lineage` - Get parent chain
- `GET /api/projects/{id}/cousins` - Get cousin projects

### Data Limitations

Since requirements and ontology management are in refactoring:

- Focus on project structure and relationships
- Use event-driven data flow (artifacts)
- Demonstrate knowledge visibility queries
- Show lattice growth patterns
- Avoid complex ontology/requirement operations

## Files to Create

1. **Scripts** (`scripts/demo/`):

- `create_lattice_example_1.py`
- `create_lattice_example_2.py`
- `create_lattice_example_3.py`
- `validate_lattice.py`
- `__init__.py`

2. **Documentation** (`docs/demos/`):

- `PROJECT_LATTICE_DEMONSTRATION_GUIDE.md`
- `LATTICE_EXAMPLE_SCENARIOS.md`

3. **Test Scripts** (optional, in `scripts/demo/`):

- `test_lattice_examples.py` - Run all examples and validate

## Success Criteria

1. ✅ Can create complete project hierarchies programmatically
2. ✅ Relationships (parent-child, cousin, knowledge links) work correctly
3. ✅ Event subscriptions and publishing demonstrate data flow
4. ✅ Knowledge visibility queries return expected results
5. ✅ Examples are documented and ready for customer demonstration
6. ✅ Scripts are reusable and can bootstrap fresh systems

## Notes

- Scripts should use `das_service` account for consistency
- Include cleanup options to remove demo projects
- Make scripts idempotent (can run multiple times safely)
- Add verbose logging for demonstration purposes
- Include visual output (print statements) showing lattice structure

### To-dos

- [ ] Create Python scripts in scripts/demo/ for each example scenario (aircraft FEA, multi-domain bootstrap, simple 3-project)
- [ ] Create validate_lattice.py utility to verify project structure, relationships, and data flow
- [ ] Create demonstration guide and scenario documentation in docs/demos/
- [ ] Test all example scripts end-to-end and verify they work correctly