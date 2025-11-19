# ODRAS Living Project Lattice Demonstrator Guide

## Overview

This demonstrator showcases ODRAS's core capability: creating a **living project lattice** that self-assembles from requirements, processes data continuously, makes autonomous decisions, and evolves through real-time event flow.

## What You'll See

### 1. **Program Bootstrapping**
- System automatically creates project lattice from requirements text
- Rule-based analysis determines layers, domains, and relationships
- Complete Pre-Milestone A acquisition program structure generated

### 2. **Living System Behavior**
- Projects as computational cells (not passive data stores)
- Continuous processing with state transitions: `draft` → `processing` → `ready` → `published`
- Autonomous decision-making: projects evaluate conditions and decide when to publish
- Real-time event flow with cascading updates

### 3. **Visual Lattice Structure**
- Proper grid layout: Layers (L0-L3) vertical, Domains horizontal
- Project cells positioned at layer/domain intersections
- All relationships visible: parent-child (vertical), cousins (horizontal)
- Live animations showing event flow and processing states

### 4. **Decision-Making Demonstration**
- Projects make decisions based on analysis results
- Decision points clearly displayed: "Requirements complete? → YES → Publish"
- Federated decisions from multiple projects
- Real decision support, not just visualization

### 5. **Gray System Activity**
- Continuous sensitivity analysis (mocked)
- Projects show sensitivity indicators (green/yellow/red)
- Fragile regions and stability assessment
- Proactive warnings before changes occur

### 6. **X-layer Exploration**
- Alternative configurations explored continuously (mocked)
- Suggestions for lattice improvements
- Evolutionary optimization proposals
- Best alternatives highlighted

## Prerequisites

1. **ODRAS Running**: All services must be running
   ```bash
   ./odras.sh status  # Verify ODRAS is running
   ```

2. **Dependencies**: Python packages for demo
   ```bash
   pip install websockets httpx
   ```

3. **Network Ports**: Ensure ports 8080 and 8081 are available
   ```bash
   netstat -an | grep :808  # Check port availability
   ```

## Quick Start

### Complete Automated Demo
```bash
# Run complete demonstration with bootstrapping
python scripts/demo/run_living_lattice_demo.py

# Run with custom requirements
python scripts/demo/run_living_lattice_demo.py --requirements-file my_requirements.txt

# Run with cleanup
python scripts/demo/run_living_lattice_demo.py --cleanup
```

### Manual Mode
```bash
# Use predefined lattice structure
python scripts/demo/run_living_lattice_demo.py --manual-mode
```

## Step-by-Step Demonstration

### 1. Start the Demo
```bash
python scripts/demo/run_living_lattice_demo.py
```

### 2. Review Bootstrapped Structure
- See decision log explaining why each project was created
- Understand rule application: keywords → domains → projects
- Review generated relationships and event subscriptions

### 3. Open Live Visualization
- Browser opens automatically to `http://localhost:8080/lattice_demo.html`
- See project lattice in proper grid layout
- Projects start in `draft` state

### 4. Activate the System
- In demo terminal, choose option 1: "Activate L1 projects"
- Watch L1 projects change to `published` state
- System becomes live and responsive

### 5. Trigger Event Flow
- Choose option 2: "Publish requirements event"
- Watch events cascade through dependent projects
- See processing animations and state transitions

### 6. Demonstrate Change Impact
- Choose option 3: "Change requirement"
- See requirement change cascade through lattice
- Watch dependent projects react automatically

### 7. Observe Living System
- Projects pulse/glow when processing
- Event flow animations show data movement
- State transitions visible in real-time
- System shows continuous activity

### 8. Monitor Systems
- Gray System shows sensitivity analysis
- X-layer displays alternative explorations
- Decision log shows autonomous decisions
- Processing queue shows active work

## Key Demonstrations

### Program Bootstrapping
**What it shows**: DAS capability to self-assemble enterprise from intent

**Example**:
- Input: "Need unmanned surface vehicle for maritime surveillance missions"
- Output: Complete 9-project lattice with proper relationships
- Rules applied: Mission keywords → Mission domain, Cost keywords → Cost domain

### Event-Driven Processing
**What it shows**: Projects as active computational cells

**Example**:
1. Requirements project publishes `capability_gaps_identified`
2. Mission Analysis receives event → processes scenarios → publishes `scenarios_defined`
3. CDD Development receives event → develops requirements → publishes `requirements_approved`
4. Concept projects receive requirements → evaluate designs → publish `design_defined`

### Decision-Making
**What it shows**: Autonomous project decisions based on conditions

**Example**:
- CDD project evaluates: "Requirements complete? Confidence > 80%? → YES → Publish"
- Trade Study project: "All concepts evaluated? → YES → Recommend Concept A"
- Cost project: "Budget constraints achievable? → NO → Request optimization"

### Requirement Change Cascade
**What it shows**: How changes propagate through enterprise

**Example**:
1. User changes surveillance range requirement (50 NM → 75 NM)
2. Mission Analysis updates scenarios for extended range
3. CONOPS adjusts operational concept
4. Concept projects re-evaluate performance against new requirement
5. Cost project updates estimates for extended range capability

## Project Structure Created

The demonstrator creates a Pre-Milestone A acquisition program:

```
L0: foundation-ontology (foundation)
├─ L1: icd-development (systems-engineering)
│   └─ L2: cdd-development (systems-engineering)
│       ├─ L3: solution-concept-a (analysis)
│       ├─ L3: solution-concept-b (analysis)
│       └─ L3: trade-study (analysis)
├─ L1: mission-analysis (mission-planning)
│   └─ L2: conops-development (mission-planning)
└─ L1: cost-strategy (cost)
    └─ L2: affordability-analysis (cost)

Cousin Relationships:
  icd-development ↔ mission-analysis ↔ cost-strategy
  cdd-development ↔ conops-development ↔ affordability-analysis
```

## Understanding the Living System

### Projects as Computational Cells
- **Inputs**: Requirements, policies, data from parent/cousin cells
- **Processing**: Gap analysis, scenario evaluation, cost calculation
- **Outputs**: Derived requirements, analysis results, **decisions**
- **State**: Draft → Processing → Ready → Published

### Event-Driven Architecture
- Events trigger processing (not just data updates)
- Projects queue events and process sequentially
- Processing state prevents race conditions
- Events carry decision context

### Coordinated Organism Behavior
- Knowledge flows downward (parent → child)
- Artifacts flow via events (any → any)
- System operates as unified whole
- Autonomous coordination through relationships

### Continuous Analysis
- **Gray System**: Shadow cells perturb parameters continuously
- **X-layer**: Explores alternative configurations
- **Decision Support**: System provides actionable insights

## Troubleshooting

### Connection Issues
```bash
# Check ODRAS status
./odras.sh status

# Check port availability
netstat -an | grep :8080
netstat -an | grep :8081

# Restart ODRAS if needed
./odras.sh restart
```

### Visualization Issues
```bash
# Check if static files exist
ls scripts/demo/static/

# Check browser console for errors (F12)
# Ensure WebSocket connection established

# Manual server start
python scripts/demo/visualization_server.py
```

### Project Creation Issues
```bash
# Check authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"das_service","password":"das_service_2024!"}'

# Check namespace availability
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/namespaces/released
```

## Next Steps

### For Learning
1. **Modify Requirements**: Try different requirement texts to see how bootstrapping changes
2. **Adjust Rules**: Modify `bootstrap_rules.py` to improve lattice generation
3. **Add Domains**: Test with requirements that trigger new domains
4. **Study Patterns**: Identify which rules work best for different program types

### For Integration into ODRAS
1. **Rule Refinement**: Improve rule accuracy based on demonstration results
2. **DAS Integration**: Move bootstrapping logic into DAS service
3. **Real Event System**: Replace mocked events with actual ODRAS pub/sub
4. **Workbench Integration**: Integrate lattice visualization into main ODRAS UI

## Architecture Insights

This demonstrator proves several key ODRAS concepts:

1. **Self-Assembly**: Systems can bootstrap themselves from requirements
2. **Living Systems**: Projects actively process and decide, not just store data
3. **Event-Driven**: Real-time responsiveness through pub/sub architecture
4. **Decision-Centric**: Explicit decisions drive enterprise evolution
5. **Proactive Analysis**: Continuous monitoring prevents issues
6. **Evolutionary**: System explores improvements automatically

## Files Created

### Core Components
- `scripts/demo/program_bootstrapper.py` - Bootstrapping engine
- `backend/services/event_bus.py` - Real-time event bus
- `scripts/demo/mock_analyses.py` - Computational cell simulations

### Visualization
- `scripts/demo/visualization_server.py` - WebSocket server
- `scripts/demo/static/lattice_demo.html` - Frontend interface
- `scripts/demo/static/lattice_demo.js` - Grid layout and animations
- `scripts/demo/static/lattice_demo.css` - Styling

### Mock Systems
- `scripts/demo/mock_gray_system.py` - Continuous sensitivity analysis
- `scripts/demo/mock_x_layer.py` - Alternative exploration

### Orchestration
- `scripts/demo/run_living_lattice_demo.py` - Master demonstration script

This demonstrator represents a significant step toward implementing the SDD vision of self-assembling, self-executing digital enterprises.
