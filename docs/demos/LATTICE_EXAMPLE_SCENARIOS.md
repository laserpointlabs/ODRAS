# Project Lattice Example Scenarios

Detailed descriptions of each demonstration scenario.

## Scenario 1: Simple 3-Project Bootstrap

### Overview

The simplest demonstration of ODRAS's project lattice capability. Shows how three projects can form a basic lattice with parent-child and cousin relationships.

### Project Structure

```
L1: demo-parent (systems-engineering)
  └─ L2: demo-child (systems-engineering)
       ↔ L2: demo-cousin (cost)
```

### Relationships

- **Parent-Child**: `demo-parent` → `demo-child` (vertical hierarchy)
- **Cousin**: `demo-child` ↔ `demo-cousin` (horizontal coordination)

### Event Flow

1. **Parent publishes**: `parent.data_ready` event with initial data
2. **Child subscribes**: Receives `parent.data_ready` event
3. **Child processes**: Performs processing on received data
4. **Child publishes**: `child.processed` event with processed data
5. **Cousin subscribes**: Receives `child.processed` event

### Data Flow Example

```json
// Parent publishes
{
  "event_type": "parent.data_ready",
  "data": {
    "status": "ready",
    "data_points": 100,
    "timestamp": "2025-01-15T10:00:00Z"
  }
}

// Child publishes
{
  "event_type": "child.processed",
  "data": {
    "processed_items": 100,
    "processing_time_ms": 250,
    "status": "complete"
  }
}
```

### Use Case

Demonstrates basic lattice concepts:
- Vertical hierarchy (parent-child)
- Horizontal coordination (cousin)
- Event-driven communication
- Data flow across projects

## Scenario 2: Aircraft Development Workflow

### Overview

Demonstrates a realistic engineering workflow where requirements flow through analysis stages to implementation, with cost modeling coordination.

### Project Structure

```
L0: aircraft-foundation (foundation)
  └─ L1: aircraft-requirements (systems-engineering)
       └─ L2: aircraft-loads (structures)
            └─ L3: aircraft-fea (analysis)
                 ↔ L2: aircraft-cost (cost) [cousin]
```

### Relationships

- **Parent-Child Chain**: Foundation → Requirements → Loads → FEA (vertical)
- **Cousin**: FEA ↔ Cost Model (horizontal coordination)
- **Knowledge Link**: FEA → Requirements (cross-domain knowledge access)

### Event Flow

1. **Requirements publishes**: `requirements.approved` with max_weight, range data
2. **Loads subscribes**: Receives requirements data
3. **Loads calculates**: Performs structural loads analysis
4. **Loads publishes**: `loads.calculated` with wing_load, fuselage_load
5. **FEA subscribes**: Receives both requirements and loads data
6. **FEA analyzes**: Performs finite element analysis
7. **FEA publishes**: `fea.analysis_complete` with margin_of_safety, material, mass
8. **Cost subscribes**: Receives FEA results
9. **Cost calculates**: Performs cost estimation based on mass/material

### Data Flow Example

```json
// Requirements publishes
{
  "event_type": "requirements.approved",
  "data": {
    "max_weight": 25000,
    "range": 3000,
    "requirement_count": 15,
    "status": "approved"
  }
}

// Loads publishes
{
  "event_type": "loads.calculated",
  "data": {
    "wing_load": 15000,
    "fuselage_load": 8000,
    "max_load": 23000,
    "analysis_id": "loads-001"
  }
}

// FEA publishes
{
  "event_type": "fea.analysis_complete",
  "data": {
    "margin_of_safety": 0.86,
    "factor_of_safety_yield": 1.15,
    "factor_of_safety_ultimate": 1.50,
    "material": "17-4PH",
    "mass": 25.4,
    "analysis_id": "fea-001"
  }
}
```

### Use Case

Real-world engineering workflow:
- Requirements definition
- Structural analysis
- Finite element analysis
- Cost estimation
- Cross-domain coordination

## Scenario 3: Multi-Domain Program Bootstrap

### Overview

Demonstrates how a program can bootstrap from a single foundation project, growing into multiple domains with coordination across domains.

### Project Structure

```
L0: program-foundation (foundation)
  ├─ L1: program-se-strategy (systems-engineering)
  │    └─ L2: program-se-tactical (systems-engineering)
  │         └─ L3: program-se-impl (systems-engineering)
  ├─ L1: program-cost-strategy (cost)
  │    └─ L2: program-cost-analysis (cost)
  └─ L1: program-logistics-strategy (logistics)

Cousin Relationships:
  program-se-tactical ↔ program-cost-analysis
  program-se-impl ↔ program-cost-analysis
```

### Relationships

- **Sibling Projects**: All L1 projects share the same parent (foundation)
- **Parent-Child Chains**: 
  - Foundation → SE Strategy → SE Tactical → SE Implementation
  - Foundation → Cost Strategy → Cost Analysis
- **Cousin Relationships**: 
  - SE Tactical ↔ Cost Analysis
  - SE Implementation ↔ Cost Analysis

### Event Flow

1. **Foundation publishes**: `foundation.established` with program information
2. **L1 Strategies publish**: Each strategy publishes `strategy.approved`
3. **L2 Tactical subscribes**: Receives strategy approval
4. **L2 Tactical publishes**: `tactical.ready` when ready
5. **L3 Implementation subscribes**: Receives tactical ready signal
6. **L3 Implementation publishes**: `implementation.complete` when done
7. **Cost Analysis subscribes**: Receives both tactical and implementation events
8. **Cost Analysis coordinates**: Provides cost estimates based on SE progress

### Data Flow Example

```json
// Foundation publishes
{
  "event_type": "foundation.established",
  "data": {
    "program_name": "Multi-Domain Program",
    "established_date": "2025-01-15",
    "domains": ["systems-engineering", "cost", "logistics"]
  }
}

// SE Strategy publishes
{
  "event_type": "strategy.approved",
  "data": {
    "strategy_type": "systems-engineering",
    "approval_date": "2025-01-20",
    "objectives": ["design", "development", "integration"]
  }
}

// SE Tactical publishes
{
  "event_type": "tactical.ready",
  "data": {
    "tactical_plan": "ready",
    "resources_allocated": true,
    "timeline": "2025-Q1"
  }
}

// SE Implementation publishes
{
  "event_type": "implementation.complete",
  "data": {
    "implementation_status": "complete",
    "components_delivered": 5,
    "completion_date": "2025-02-15"
  }
}
```

### Use Case

Program-level bootstrap:
- Multi-domain coordination
- Strategy → Tactical → Implementation flow
- Cross-domain cost tracking
- Event-driven program management

## Key Concepts Demonstrated

### Parent-Child Relationships

- **Vertical Hierarchy**: Projects inherit knowledge from parents
- **Level Validation**: Parent level must be < child level
- **Knowledge Flow**: Knowledge flows downward (L0 → L1 → L2 → L3)

### Cousin Relationships

- **Horizontal Coordination**: Projects in different domains coordinate
- **Bidirectional**: Cousin relationships can be bidirectional
- **Cross-Domain**: Enables coordination without violating domain boundaries

### Cross-Domain Knowledge Links

- **Explicit Access**: Projects can explicitly link to knowledge in other domains
- **Controlled**: Knowledge links require approval/identification
- **Selective**: Not all knowledge is accessible, only linked knowledge

### Event-Driven Data Flow

- **Publish-Subscribe**: Projects publish events, others subscribe
- **Decoupled**: Publishers don't need to know subscribers
- **Flexible**: Any project can subscribe to any event type
- **Artifact Flow**: Events carry data/artifacts, not knowledge

## Customization

All scripts can be customized:

1. **Modify Project Names**: Change project names to match your use case
2. **Add Projects**: Add more projects to the lattice
3. **Change Domains**: Use different domains for your scenario
4. **Custom Events**: Define custom event types and data structures
5. **Add Relationships**: Create additional cousin relationships or knowledge links

## Integration with ODRAS Features

The lattice examples integrate with:

- **Requirements Management**: Projects can contain requirements
- **Ontology Management**: Projects can have ontologies
- **BPMN Workflows**: Lattice can trigger BPMN workflows
- **Knowledge Assets**: Projects can publish knowledge assets
- **DAS Integration**: DAS can operate across the lattice

## Best Practices

1. **Start Simple**: Begin with Scenario 1 to understand basics
2. **Grow Incrementally**: Add projects and relationships gradually
3. **Validate Often**: Use validation script to check structure
4. **Document Relationships**: Document why relationships exist
5. **Use Descriptive Names**: Project names should indicate purpose
6. **Domain Alignment**: Keep projects aligned with their domains
7. **Event Naming**: Use consistent event type naming (`domain.action`)
