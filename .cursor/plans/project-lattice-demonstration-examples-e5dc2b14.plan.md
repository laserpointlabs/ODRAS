<!-- e5dc2b14-c75e-4390-8785-05f545752ef1 cf04c601-539a-4d2b-a6ff-136589ff9349 -->
## Living System Architecture

### Core Principle: Projects as Computational Cells

**Critical Understanding**: Each project in ODRAS is not a folder or document container. It is a **computational cell** with:

- **Defined Inputs**: Allocated requirements, policies, data parameters from parent/cousin cells
- **Internal State**: Models, evidence, derived requirements, satisfaction links, provenance
- **Defined Outputs**: Derived requirements, analysis results, artifacts, **decisions**

Projects are **active participants** in a living system, not passive data stores.

### Living System Characteristics

**1. Continuous Processing**

- Projects process inputs continuously, not just on-demand
- Internal state evolves as new data arrives
- Processing states visible: `draft` → `processing` → `ready` → `published`
- Mock analyses simulate real computational work (gap analysis, scenario evaluation, cost calculation)

**2. Autonomous Decision-Making**

- Projects evaluate conditions and make decisions autonomously
- Decision points: "Is analysis complete?", "Are requirements satisfied?", "Should I publish?"
- Decisions trigger events that propagate through lattice
- Federated decisions emerge when multiple projects contribute

**3. Event-Driven Responsiveness**

- Projects subscribe to events and react automatically
- No manual intervention needed for data flow
- Changes cascade through dependent projects automatically
- System responds to changes in real-time

**4. Coordinated Organism Behavior**

- Projects coordinate through parent-child and cousin relationships
- Knowledge flows downward (parent → child)
- Artifacts flow via events (any → any)
- System operates as unified whole, not isolated components

**5. Proactive Analysis (Gray System)**

- Shadow cells continuously perturb parameters
- Sensitivity analysis happens automatically
- System anticipates consequences before changes occur
- Fragility detection alerts projects to potential issues

**6. Evolutionary Exploration (X-layer)**

- System explores alternative configurations
- Experiments with different project arrangements
- Proposes improvements based on sensitivity analysis
- Best alternatives can be promoted to live system

### Demonstrator Requirements

The demonstrator must show:

**Active Processing**:

- Projects transition through states: `draft` → `processing` → `ready` → `published`
- Visual indicators show projects actively processing (spinning, pulsing)
- Processing time simulated (not instant updates)
- Internal state changes visible (requirements count, analysis progress)

**Decision Points**:

- Show when projects evaluate conditions
- Display decision logic: "CDD project: Requirements complete? → YES → Publish"
- Decisions trigger downstream events automatically
- Federated decisions show multiple projects contributing

**Continuous Data Flow**:

- Events flow continuously, not just one-time
- Projects process events as they arrive
- Queue visualization shows pending events
- Real-time updates show system responding

**Living System Visualization**:

- Projects pulse/glow when processing
- Event flow animations show data moving
- State transitions visible (color changes, animations)
- System "breathing" - continuous activity even when idle

**Real Decision Support**:

- Not just visualization - actual decision-making
- Projects evaluate and decide autonomously
- Decisions influence downstream projects
- System provides actionable insights, not just data display

### Implementation Implications

**Mock Analysis Functions**:

- Must simulate real processing time (not instant)
- Show internal state changes during processing
- Make decisions based on conditions
- Publish results when ready (not automatically)

**Event System**:

- Events trigger processing, not just data updates
- Projects queue events and process sequentially
- Processing state prevents duplicate work
- Events carry decision context, not just data

**Visualization**:

- Show projects as active cells, not static boxes
- Animate processing states
- Display decision points and logic
- Show continuous activity, not static diagram

**State Management**:

- Track project states explicitly
- State transitions trigger visual updates
- Processing states prevent race conditions
- Published state makes outputs available to others