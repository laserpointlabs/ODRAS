# Project Lattice Demonstration Guide

## Overview

This guide demonstrates ODRAS's project lattice capability - how projects can self-assemble into hierarchical structures with parent-child relationships, cousin relationships for cross-domain coordination, and event-driven data flow.

## What is the Project Lattice?

The project lattice is ODRAS's mechanism for organizing projects into a hierarchical structure where:

- **Parent-Child Relationships**: Projects can have parent projects, creating vertical knowledge inheritance chains (L0 → L1 → L2 → L3)
- **Cousin Relationships**: Projects in different domains can coordinate horizontally through cousin relationships
- **Cross-Domain Knowledge Links**: Projects can explicitly link to knowledge in other domains
- **Event-Driven Data Flow**: Projects publish and subscribe to events, enabling artifact flow across the lattice

## Prerequisites

Before running the demonstrations:

1. **ODRAS must be running**: All services (PostgreSQL, Neo4j, Qdrant, Redis, Fuseki, ODRAS API) must be running
2. **Database initialized**: Run `./odras.sh init-db` to ensure all domains are available
3. **Authentication**: Scripts use the `das_service` account (Username: `das_service`, Password: `das_service_2024!`)

## Available Domains

The demonstration uses these domains:

**Default Domains:**
- `avionics` - Aircraft electronics and flight systems
- `mission-planning` - Mission planning and execution systems
- `systems-engineering` - Systems engineering processes and methodologies
- `logistics` - Supply chain and logistics management
- `cybersecurity` - Cybersecurity and information assurance
- `communications` - Communication systems and protocols
- `radar-systems` - Radar and sensor technologies
- `weapons-systems` - Weapons and armament systems

**Additional Domains (for demonstrations):**
- `cost` - Cost analysis and modeling
- `foundation` - Foundational and abstract projects
- `structures` - Structural analysis and engineering
- `analysis` - Analysis and computational modeling

## Example Scenarios

### Scenario 1: Simple 3-Project Bootstrap

**Purpose**: Minimal example showing basic lattice growth

**Project Structure:**
- L1 Parent: `demo-parent` (systems-engineering domain)
- L2 Child: `demo-child` (systems-engineering domain, parent: parent)
- L2 Cousin: `demo-cousin` (cost domain, cousin to child)

**Run:**
```bash
python scripts/demo/create_lattice_example_1.py
```

**What it demonstrates:**
- Parent-child relationship (vertical hierarchy)
- Cousin relationship (horizontal coordination)
- Event subscriptions and publishing
- Basic data flow

### Scenario 2: Aircraft Development Workflow

**Purpose**: Demonstrate vertical parent-child hierarchy with cross-domain cousin coordination

**Project Structure:**
- L0 Foundation: `aircraft-foundation` (foundation domain)
- L1 Requirements: `aircraft-requirements` (systems-engineering domain, parent: foundation)
- L2 Loads Analysis: `aircraft-loads` (structures domain, parent: requirements)
- L3 FEA Analysis: `aircraft-fea` (analysis domain, parent: loads)
- L2 Cost Model: `aircraft-cost` (cost domain, cousin to FEA)

**Run:**
```bash
python scripts/demo/create_lattice_example_2.py
```

**What it demonstrates:**
- Multi-level parent-child chain (L0 → L1 → L2 → L3)
- Cross-domain cousin coordination
- Cross-domain knowledge links
- Event-driven workflow (Requirements → Loads → FEA → Cost)

### Scenario 3: Multi-Domain Program Bootstrap

**Purpose**: Demonstrate how a program can bootstrap from a single foundation project

**Project Structure:**
- L0 Foundation: `program-foundation` (foundation domain)
- L1 SE Strategy: `program-se-strategy` (systems-engineering domain, parent: foundation)
- L1 Cost Strategy: `program-cost-strategy` (cost domain, parent: foundation)
- L1 Logistics Strategy: `program-logistics-strategy` (logistics domain, parent: foundation)
- L2 SE Tactical: `program-se-tactical` (systems-engineering domain, parent: SE Strategy)
- L2 Cost Analysis: `program-cost-analysis` (cost domain, parent: Cost Strategy)
- L3 SE Implementation: `program-se-impl` (systems-engineering domain, parent: SE Tactical)

**Run:**
```bash
python scripts/demo/create_lattice_example_3.py
```

**What it demonstrates:**
- Multiple sibling projects (same parent, different domains)
- Multi-domain coordination
- Cousin relationships across domains
- Event cascade showing system self-assembly

## Visualization

### Interactive Graph Visualization

Generate an interactive HTML visualization of the lattice:

```bash
# Visualize all projects
python scripts/demo/visualize_lattice.py

# Visualize from a specific root project
python scripts/demo/visualize_lattice.py <project_id>

# Specify output file
python scripts/demo/visualize_lattice.py --output my_lattice.html
```

This creates an interactive Cytoscape.js visualization showing:
- Project nodes colored by level (L0-L3)
- Parent-child relationships (solid blue lines)
- Cousin relationships (dashed gray lines)
- Click and drag to explore
- Hover to highlight projects

Open the generated HTML file in a web browser to view the lattice.

### Workflow Execution with Mock Workbenches

Execute a step-by-step workflow demonstration showing data flow:

```bash
# Execute scenario 1 (simple 3-project)
python scripts/demo/execute_workflow.py 1

# Execute scenario 2 (aircraft FEA workflow)
python scripts/demo/execute_workflow.py 2

# Execute scenario 3 (multi-domain bootstrap)
python scripts/demo/execute_workflow.py 3

# Interactive mode (pause between steps)
python scripts/demo/execute_workflow.py 2 --interactive
```

The workflow executor:
- Shows each step of the workflow
- Performs mock calculations at each project (e.g., FEA adds 2+2)
- Demonstrates data flow between projects
- Shows event publishing and subscription notifications
- Displays final results

**Mock Workbenches:**
- **Requirements Workbench**: Validates and approves requirements
- **Loads Workbench**: Calculates structural loads (60% wings, 40% fuselage)
- **FEA Workbench**: Performs finite element analysis (mock: adds loads together)
- **Cost Workbench**: Estimates cost based on mass and material
- **Strategy/Tactical/Implementation Workbenches**: Process workflow stages

## Validation

After creating a lattice, validate its structure:

```bash
# Validate a specific project
python scripts/demo/validate_lattice.py <project_id>

# Validate all projects
python scripts/demo/validate_lattice.py --all
```

The validator checks:
- Project structure and hierarchy
- Parent-child relationships
- Cousin relationships
- Event subscriptions
- Knowledge links

## Cleanup

All demonstration scripts support cleanup:

```bash
python scripts/demo/create_lattice_example_1.py --cleanup
python scripts/demo/create_lattice_example_2.py --cleanup
python scripts/demo/create_lattice_example_3.py --cleanup
```

This removes all created projects after the demonstration.

## Complete Demonstration Workflow

### Quick Start (All-in-One)

For a complete automated demonstration:

```bash
# Run complete demo (creates, visualizes, executes, cleans up)
python scripts/demo/run_complete_demo.py 2

# Keep projects for further exploration
python scripts/demo/run_complete_demo.py 2 --keep-projects
```

This single command:
1. Creates the project lattice
2. Validates the structure
3. Generates interactive visualization HTML
4. Executes workflow with mock workbenches
5. Cleans up (unless --keep-projects specified)

### Manual Step-by-Step

For a manual demonstration with more control:

1. **Create the Lattice**:
   ```bash
   python scripts/demo/create_lattice_example_2.py
   ```

2. **Visualize the Structure**:
   ```bash
   python scripts/demo/visualize_lattice.py
   # Open lattice_visualization.html in browser
   ```

3. **Execute the Workflow**:
   ```bash
   python scripts/demo/execute_workflow.py 2
   ```

4. **Show the Results**:
   - Point to the visualization showing the lattice structure
   - Walk through each step of the workflow execution
   - Highlight how data flows from Requirements → Loads → FEA → Cost
   - Show how cousin relationships enable cross-domain coordination

## Customer Demonstration Talking Points

### Self-Growing System

ODRAS demonstrates how a bootstrapped system can self-assemble:

1. **Start with Foundation**: Create a single L0 foundation project
2. **Grow Vertically**: Add L1, L2, L3 projects as needed
3. **Grow Horizontally**: Add cousin projects for cross-domain coordination
4. **Connect Knowledge**: Create knowledge links for explicit knowledge access
5. **Enable Data Flow**: Set up event subscriptions for artifact flow

### Key Capabilities Demonstrated

- **Hierarchical Organization**: Projects naturally organize into layers (L0-L3)
- **Domain Separation**: Each project belongs to a domain, maintaining domain boundaries
- **Cross-Domain Coordination**: Cousin relationships enable coordination without violating domain boundaries
- **Event-Driven Architecture**: Projects communicate through events, enabling loose coupling
- **Knowledge Inheritance**: Child projects inherit knowledge from parent projects
- **Explicit Knowledge Access**: Cross-domain knowledge links provide controlled access to knowledge

### Use Cases

- **Acquisition Programs**: Bootstrap from foundation to strategy to tactical to implementation
- **Engineering Workflows**: Requirements → Analysis → Design → Implementation
- **Multi-Domain Programs**: Coordinate across systems engineering, cost, logistics, etc.
- **Knowledge Management**: Organize and share knowledge across domains

## Troubleshooting

### Authentication Failed

- Verify `das_service` account exists: `./odras.sh init-db`
- Check ODRAS API is running: `./odras.sh status`
- Verify credentials: Username: `das_service`, Password: `das_service_2024!`

### Domain Not Found

- Ensure domains are added to schema: Check `backend/odras_schema.sql`
- Run database initialization: `./odras.sh init-db`
- Verify domain exists: Check domain_registry table

### Project Creation Failed

- Verify namespace exists: Check `/api/namespace/simple`
- Check project level validation: Parent level must be < child level
- Verify parent project exists: Check project_id is valid

### Event Publishing Failed

- Verify subscriptions exist: Check `/api/projects/{id}/subscriptions`
- Verify publisher project exists: Check project_id is valid
- Check event type format: Should be `domain.event_name` format

## Next Steps

After running the demonstrations:

1. **Explore the UI**: View projects in the ODRAS frontend
2. **Query Relationships**: Use API endpoints to explore relationships
3. **Create Custom Lattices**: Modify scripts to create your own structures
4. **Integrate with Workflows**: Connect lattice to BPMN workflows
5. **Add Knowledge**: Populate projects with requirements and ontologies

## Related Documentation

- [Project Lattice Architecture](../architecture/PROJECT_LATTICE_AND_KNOWLEDGE_FLOW.md)
- [Domain-Centric Project Hierarchy](../features/DOMAIN_CENTRIC_PROJECT_HIERARCHY.md)
- [Publishing Architecture](../architecture/PUBLISHING_ARCHITECTURE.md)
