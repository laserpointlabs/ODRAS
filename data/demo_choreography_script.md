# ODRAS/DAS Demonstration Choreography Script
## SME Peer Review Walkthrough

---

## Introduction and Setup

**Duration**: 2-3 hours for complete demonstration  
**Audience**: Subject Matter Experts (SMEs), stakeholders, technical reviewers  
**Prerequisites**: ODRAS system running, services healthy, demo account (das_service) ready  

### Demonstration Objectives
1. Show core ODRAS capabilities for knowledge management and requirements engineering
2. Demonstrate DAS (Domain Advisor Service) AI assistance throughout the workflow
3. Illustrate ontology-based system modeling and reasoning
4. Highlight project inheritance and knowledge reuse patterns
5. Demonstrate requirements analysis and architecture generation

---

## PHASE 1: CORE PROJECT BUILD

### 1.1 Create Core Project

**Action**: Navigate to Projects panel and create new project

**Steps**:
1. Click "+ New Project" button
2. Enter Project Details:
   - **Name**: `Core`
   - **Key**: `CORE`
   - **Description**: "Foundational systems engineering knowledge and standards"
3. Click "Create Project"
4. Verify project appears in project list

**Talking Points**:
- "The Core project establishes foundational SE knowledge that other projects will inherit"
- "Project keys are used in URI generation for ontologies and semantic data"
- "Core project will contain reusable standards and base ontology classes"

---

### 1.2 Load Knowledge Documents

**Action**: Upload reference documents to Core project knowledge base

**Steps**:
1. Navigate to Knowledge Management panel
2. Click "Upload Documents"
3. Select and upload:
   - `core_requirements.md`
   - `how_to_write_a_requirement.md`
4. Wait for processing confirmation
5. Verify documents appear in knowledge list

**Talking Points**:
- "ODRAS chunks documents and creates vector embeddings for semantic search"
- "We use both small (384-dim) and large (1536-dim) embeddings for different use cases"
- "These documents will be available for DAS to reference when answering questions"
- "The 'how to write a requirement' guide establishes our requirements standards"

---

### 1.3 Publish Requirements Writing Guide

**Action**: Make the requirements guide available to all projects

**Steps**:
1. Locate `how_to_write_a_requirement.md` in knowledge list
2. Click document to view details
3. Click "Publish Document" button
4. Set visibility to "All Projects"
5. Confirm publication

**Talking Points**:
- "Publishing makes knowledge available across project boundaries"
- "Published documents appear in other projects' knowledge bases"
- "This enables standardization across the organization"
- "DAS will reference published standards when assisting in other projects"

**DAS Verification Discussion**:
```
Ask DAS: "What are the key elements of a well-written requirement?"

Expected Response: DAS should reference the guide and explain:
- Use of "shall" language
- Specific and measurable criteria
- Threshold [T] vs Objective [O] designations
- KPP/KPA/KPC classifications
```

---

### 1.4 Import Requirements in Workbench

**Action**: Import core requirements into Requirements Workbench

**Steps**:
1. Navigate to Requirements Workbench
2. Click "Import Requirements"
3. Select "From Document" option
4. Choose `core_requirements.md`
5. Review parsed requirements preview
6. Confirm import
7. Verify requirements appear in workbench with proper structure

**Talking Points**:
- "Requirements Workbench parses requirements from documents"
- "Notice it automatically identifies [KPP], [T], and [O] designations"
- "Each requirement gets a unique identifier for traceability"
- "We can edit, categorize, and manage requirements here"

**Review Imported Requirements**:
- IOC timeline requirement (18 months [T], 12 months [O])
- Interoperability requirement (MIL-STD-6040)
- Cost requirement ($2.5M [T], $2M [O])
- Acceptance testing requirement

---

### 1.5 Add Assumptions via DAS Dock

**Action**: Capture project assumptions using DAS conversation

**Steps**:
1. Open DAS Dock (bottom panel or F12)
2. Start conversation about project assumptions

**DAS Discussion**:
```
You: "I need to capture some assumptions for the Core project. We're establishing 
systems engineering standards that will be used across multiple UAS projects."

DAS: [Acknowledges and asks clarifying questions]

You: "First assumption: All systems engineering requirements will follow the 
threshold/objective format with [T] and [O] designations."

DAS: [Confirms and may ask if you want to formalize this]

You: "Second assumption: We'll use ontology-based modeling for all system 
architectures, building on OWL and RDF standards."

DAS: [Confirms and may suggest related concepts]

You: "Third assumption: Key Performance Parameters will be limited to 3-5 per 
system to maintain focus on critical capabilities."

DAS: [Confirms assumption captured]

You: "Can you summarize the assumptions we've captured?"

DAS: [Provides summary of three assumptions]
```

**Talking Points**:
- "DAS captures conversational context in the thread manager"
- "Assumptions are tracked and can be promoted to formal project artifacts"
- "This natural language interface makes knowledge capture easy"
- "DAS maintains conversation history for future reference"

---

### 1.6 Conversation About Requirements

**Action**: Have substantive discussion with DAS about requirements

**DAS Discussion**:
```
You: "Looking at our core requirements, what's the relationship between the 
IOC timeline and the cost constraints?"

DAS: [Analyzes requirements and discusses trade-offs between schedule and cost]

You: "The interoperability requirement mentions MIL-STD-6040. What are the 
implications for our architecture?"

DAS: [Discusses C4ISR integration, data formats, security requirements]

You: "How should we approach verification for the acceptance testing requirement?"

DAS: [Suggests verification methods, test planning approach]

You: "What requirements engineering best practices should we emphasize for 
future projects?"

DAS: [References the how-to guide, highlights key principles]
```

**Talking Points**:
- "DAS has access to all project knowledge and uploaded documents"
- "Notice how DAS references the requirements guide we uploaded"
- "DAS provides context-aware responses based on project content"
- "These conversations are preserved and searchable"

---

### 1.7 Create Core Ontology

**Action**: Build foundational ontology with abstract base classes

**Steps**:
1. Navigate to Ontology Workbench
2. Click "New Ontology"
3. Enter ontology details:
   - **Name**: `Core Ontology`
   - **Prefix**: `core`
   - **Namespace**: `http://usn/adt/core/`
4. Click "Create"
5. Add base classes:

**Add Object Class**:
1. Click "Add Class" → "Root Class"
2. Enter:
   - **Class Name**: `Object`
   - **Label**: "Object"
   - **Comment**: "Abstract root class for all entities in the system"
   - **Type**: Abstract (check box)
3. Save class

**Add PhysicalObject Class**:
1. Click "Add Class" → "Subclass of Object"
2. Enter:
   - **Class Name**: `PhysicalObject`
   - **Label**: "Physical Object"
   - **Comment**: "Abstract class for entities with physical manifestation"
   - **Parent**: `Object`
   - **Type**: Abstract (check box)
3. Save class

**Talking Points**:
- "We start with abstract base classes that define fundamental concepts"
- "Abstract classes cannot be instantiated - they're templates for inheritance"
- "Object is the root of our hierarchy - everything is an Object"
- "PhysicalObject captures entities with physical properties"
- "These classes will be inherited by more specific classes in derived projects"

---

### 1.8 Make Core Ontology a Reference

**Action**: Designate Core ontology as reference for other projects

**Steps**:
1. In Ontology Workbench, select Core Ontology
2. Click ontology settings/properties
3. Enable "Reference Ontology" flag
4. Set visibility to "All Projects"
5. Save settings

**Talking Points**:
- "Reference ontologies are read-only for importing projects"
- "This prevents accidental modification of foundational concepts"
- "Other projects will import and extend these base classes"
- "Changes to reference ontologies are version controlled"

---

### 1.9 Test Inheritance Capability (Example)

**Action**: Create a test class to demonstrate inheritance

**Steps**:
1. Still in Core Ontology
2. Add new class:
   - **Class Name**: `System`
   - **Parent**: `PhysicalObject`
   - **Label**: "System"
   - **Comment**: "An organized assembly of components arranged to accomplish specific functions"
   - **Type**: Abstract
3. Add property to System class:
   - **Property Name**: `hasComponent`
   - **Type**: Object Property
   - **Domain**: `System`
   - **Range**: `PhysicalObject`
   - **Label**: "has component"
4. Save

**Talking Points**:
- "System inherits characteristics from PhysicalObject and Object"
- "The hasComponent property establishes composition relationships"
- "This demonstrates how ontologies capture not just entities but relationships"
- "Other projects can create specific system types (UAS, sensor, etc.) that inherit from System"

**Visual Demonstration**:
- Show class hierarchy in ontology browser
- Highlight inheritance chain: System → PhysicalObject → Object
- Show properties inherited at each level

---

### 1.10 Another DAS Conversation - Thread Management

**Action**: Demonstrate conversation continuity and context awareness

**DAS Discussion**:
```
You: "Earlier we discussed assumptions. Can you remind me what we captured?"

DAS: [Retrieves previous conversation context and lists the three assumptions]

You: "Good. Now looking at the ontology we just created, how does the Object 
class hierarchy relate to systems engineering decomposition?"

DAS: [Discusses how ontology models system structure, references SE principles]

You: "Should we add more base classes, or is Object and PhysicalObject sufficient 
for the Core?"

DAS: [Provides recommendation based on best practices and project scope]

You: "What about non-physical things like functions or requirements?"

DAS: [Discusses potential for additional abstract classes like ConceptualObject]

You: "Let's hold on that for now. I want to show how derived projects extend the Core."

DAS: [Acknowledges, notes for future consideration]
```

**Talking Points**:
- "Notice DAS recalled our earlier assumption discussion"
- "DAS maintains thread continuity across the session"
- "Context from knowledge base + conversation history enables intelligent responses"
- "Thread history is stored in Qdrant vector database for semantic retrieval"

---

## PHASE 2: CORE.SE PROJECT BUILD

### 2.1 Create Core.SE Project

**Action**: Create derived project for specific UAS system engineering

**Steps**:
1. Navigate to Projects panel
2. Click "+ New Project"
3. Enter Project Details:
   - **Name**: `Core.SE`
   - **Key**: `CORESE`
   - **Description**: "Systems Engineering for tactical UAS reconnaissance capability"
   - **Parent Project**: Select `Core` (if supported, otherwise note inheritance manually)
4. Click "Create Project"
5. Switch to Core.SE project context

**Talking Points**:
- "Core.SE is a specific system engineering project"
- "It will inherit knowledge from Core project"
- "Notice published documents from Core are now visible here"
- "Ontologies from Core are available for import"

---

### 2.2 Load Project Knowledge

**Action**: Upload project-specific documents

**Steps**:
1. Navigate to Knowledge Management in Core.SE project
2. Verify `how_to_write_a_requirement.md` is visible (published from Core)
3. Upload new documents:
   - `core_se_project_description.md`
   - `core_se_requirements.md`
   - `uas_specifications.md` (optional, for DAS reference)
4. Wait for processing
5. Verify all documents in knowledge base

**Talking Points**:
- "Project description provides mission context for DAS"
- "Requirements are specific to the UAS system"
- "UAS specifications provide technical reference data"
- "Combination of Core standards + project specifics gives DAS full context"

---

### 2.3 Import Requirement from Core

**Action**: Demonstrate cross-project requirements inheritance

**Steps**:
1. Navigate to Requirements Workbench
2. Click "Import from Project"
3. Select `Core` project
4. Browse Core requirements
5. Select one requirement (e.g., "The system shall meet all requirements specified in the System Requirements Document and pass acceptance testing [T]")
6. Import as "Inherited Requirement"
7. Verify it appears in Core.SE requirements with link to Core

**Talking Points**:
- "Requirements can be inherited from parent projects"
- "Inherited requirements maintain traceability to source"
- "Changes in Core propagate (or are flagged) in derived projects"
- "This enables requirements reuse and consistency"

---

### 2.4 Load Project Requirements

**Action**: Import Core.SE specific requirements

**Steps**:
1. Still in Requirements Workbench
2. Click "Import Requirements" → "From Document"
3. Select `core_se_requirements.md`
4. Review parsed requirements
5. Confirm import

**Review Key Requirements Together**:
- Survey coverage: ≥5 km² in ≤2 hours [T], ≥10 km² [O]
- Wind tolerance: ≤25 kt [T]
- Temperature range: -10°C to +45°C [T], -20°C to +50°C [O]
- Setup time: ≤15 min [T]
- Endurance: ≥3 hours [T], ≥4 hours [O]

**Talking Points**:
- "Notice the requirements follow the format from our published guide"
- "KPP designations identify mission-critical parameters"
- "Threshold/Objective structure gives contract minimums and stretch goals"
- "These requirements will drive architecture decisions"

---

### 2.5 Create Ontologies with DAS Assistance

**Action**: Use DAS to help define ontology classes

**DAS Discussion for BSEO (Basic Systems Engineering Ontology)**:
```
You: "I need to create the BSEO ontology for Core.SE. This should extend the Core 
ontology and include systems engineering concepts. What classes should I include?"

DAS: [Suggests classes based on SE principles and project context]
Expected suggestions:
- Component (extends PhysicalObject)
- Interface
- Function
- Requirement
- Subsystem (extends System from Core)

You: "Good. What about the UAS-specific classes?"

DAS: [Suggests domain-specific classes]
Expected suggestions:
- AirVehicle (extends System)
- GroundControlStation (extends System)
- Sensor (extends Component)
- DataLink (extends Component)
- PayloadSubsystem (extends Subsystem)

You: "Should these be abstract or concrete classes?"

DAS: [Discusses abstraction levels]
- Abstract: System, Component, Subsystem
- Concrete: Specific sensor types, specific air vehicle configurations

You: "What properties should I define between these classes?"

DAS: [Suggests relationships]
- hasSubsystem (System → Subsystem)
- interfaces (Component → Interface)
- implements (System → Function)
- satisfies (Component → Requirement)
```

**Action After Discussion**:
1. Navigate to Ontology Workbench
2. Click "New Ontology"
3. Create BSEO:
   - **Name**: `Basic Systems Engineering Ontology`
   - **Prefix**: `bseo`
   - **Namespace**: `http://usn/adt/SE/core/bseo/`
4. Import Core ontology (click "Import Ontology" → Select Core)
5. Add classes based on DAS discussion:
   - Component (subclass of PhysicalObject)
   - Subsystem (subclass of System from Core)
   - AirVehicle (subclass of System)
   - Sensor (subclass of Component)
   - DataLink (subclass of Component)

**Talking Points**:
- "DAS helped us think through the class hierarchy"
- "Notice we're importing and extending Core ontology classes"
- "We use owl:equivalentClass to link to imported concepts when appropriate"
- "This ontology captures system structure and composition"

---

**DAS Discussion for BSEO-RNM (Requirements and Needs Model)**:
```
You: "Now I need the RNM ontology for requirements traceability. What should this include?"

DAS: [Suggests requirements metamodel classes]
Expected suggestions:
- Requirement (abstract)
- FunctionalRequirement (subclass of Requirement)
- PerformanceRequirement (subclass of Requirement)
- InterfaceRequirement (subclass of Requirement)
- Stakeholder
- Need
- VerificationMethod

You: "What relationships should connect requirements to system elements?"

DAS: [Suggests traceability relationships]
- tracesTo (Requirement → Need)
- satisfiedBy (Requirement → Component/System)
- verifiedBy (Requirement → VerificationMethod)
- derivedFrom (Requirement → Requirement)

You: "How do we handle threshold and objective values?"

DAS: [Suggests data properties]
- hasThresholdValue (Requirement → literal)
- hasObjectiveValue (Requirement → literal)
- hasUnit (Requirement → literal)
- isKPP (Requirement → boolean)
```

**Action After Discussion**:
1. Create new ontology:
   - **Name**: `Requirements and Needs Model`
   - **Prefix**: `bseornm`
   - **Namespace**: `http://usn/adt/SE/core/bseornm/`
2. Import BSEO (to link requirements to system elements)
3. Add classes:
   - Requirement (abstract)
   - PerformanceRequirement
   - FunctionalRequirement
   - Stakeholder
4. Add properties:
   - satisfiedBy (Requirement → System/Component)
   - hasThresholdValue (data property)
   - hasObjectiveValue (data property)
   - isKPP (boolean data property)

**Talking Points**:
- "RNM captures requirements structure and traceability"
- "Links between requirements and design elements enable impact analysis"
- "Threshold/Objective properties formalize requirements structure"
- "This enables automated consistency checking and traceability queries"

---

### 2.6 Explore Ontology Workbench Features

**Action**: Demonstrate key ontology workbench capabilities

**Demonstrate Imports**:
1. Select BSEO ontology
2. Click "Imports" tab
3. Show Core ontology import
4. Show class hierarchy with imported classes highlighted

**Demonstrate Named Views**:
1. Click "Views" → "Create Named View"
2. Create view: "Air Vehicle Subsystem"
3. Add filters: Classes that are subclasses of AirVehicle or Component
4. Save and show filtered view

**Demonstrate Multiplicity**:
1. Select `hasComponent` property (from Core.System)
2. Edit property
3. Add cardinality constraints:
   - **Min**: 1 (System must have at least one component)
   - **Max**: unlimited
4. Show how this appears in class definition

**Demonstrate Enumerations**:
1. Create new class: `LaunchMethod`
2. Add enumeration values:
   - HandLaunch
   - CatapultLaunch
   - VerticalTakeoff
   - RunwayTakeoff
3. Add property to AirVehicle:
   - **Property**: `launchMethod`
   - **Range**: `LaunchMethod` (enumeration)

**Talking Points**:
- "Imports enable ontology reuse and extension"
- "Named views help manage complex ontologies by showing relevant subsets"
- "Multiplicity constraints enforce design rules"
- "Enumerations provide controlled vocabularies"
- "These features enable formal system modeling and validation"

---

### 2.7 Explain Individuals to SMEs

**Action**: Discuss individuals (instances) and their role

**Talking Points**:
- "Individuals are specific instances of classes"
- "In SysML terms, individuals are like instance specifications"
- "Example: AirVehicle is a class; 'SkyEagle X500' is an individual"
- "Individuals have property values: SkyEagle X500 wingspan = 3.5 meters"
- "We can use individuals to represent actual components in our design"

**Demonstration**:
1. In Ontology Workbench, select BSEO ontology
2. Click "Individuals" tab
3. Create new individual:
   - **Name**: `SkyEagle_X500`
   - **Type**: `AirVehicle`
4. Add data property values:
   - weight: 15 (kg)
   - wingspan: 3.5 (meters)
   - maxSpeed: 120 (km/h)
   - endurance: 10 (hours)
5. Add object property values:
   - launchMethod: CatapultLaunch
6. Save individual

**Talking Points**:
- "This individual represents a specific UAS platform"
- "Property values come from the uas_specifications.md document"
- "We can create individuals for candidate platforms and compare them"
- "Reasoners can check if individuals satisfy requirements"

---

### 2.8 Inject Demo Requirements Manager

**Action**: Upload or reference demo_requirements_manager.py script

**Note**: This file needs to be created. It should be a Python script that demonstrates programmatic requirements management via ODRAS API.

**Script Purpose** (describe to SMEs):
- "This script shows how to interact with ODRAS programmatically"
- "It can bulk import requirements, run traceability queries, generate reports"
- "Useful for integrating ODRAS with other tools (JIRA, DOORS, etc.)"
- "Demonstrates API-driven workflows for automation"

**If Script Exists**:
1. Upload to Knowledge Management
2. Show script contents
3. Explain key functions

**If Script Doesn't Exist** (note for future):
- "We're developing API scripts for requirements automation"
- "This will enable CI/CD integration for requirements validation"
- "Placeholder for now, will be part of future capabilities"

---

### 2.9 Add Example Assumptions

**Action**: Capture project-specific assumptions

**DAS Discussion**:
```
You: "I need to document assumptions specific to Core.SE. First assumption: 
The UAS will operate in permissive airspace with no active threats."

DAS: [Captures assumption, may note security/safety implications]

You: "Second: We assume existing DoD communication infrastructure is available 
for C4ISR integration."

DAS: [Captures, may ask about fallback if infrastructure unavailable]

You: "Third: Operators will have basic aviation and radio operation knowledge 
before UAS-specific training."

DAS: [Captures, may relate to training duration requirements]

You: "Fourth: We assume commercial-off-the-shelf sensors meet performance needs, 
no custom development required."

DAS: [Captures, may note cost and schedule implications]

You: "Can you summarize all project assumptions now?"

DAS: [Lists all four Core.SE assumptions]
```

**Talking Points**:
- "Project assumptions are critical for risk management"
- "DAS helps identify implications of assumptions"
- "Assumptions should be validated during system development"
- "Violated assumptions trigger risk mitigation plans"

---

### 2.10 Run the Conceptualizer

**Action**: Extract concept graphs from requirements

**Steps**:
1. Navigate to Requirements Workbench
2. Select all requirements (or select specific set)
3. Click "Analyze" → "Extract Concepts"
4. Wait for processing (may take 30-60 seconds)
5. View generated concept graphs

**Review Concept Graphs**:
- **Survey Coverage Concept**:
  - Root node: UAS
  - Properties: coverage area (5-10 km²), time (≤2 hours)
  - Relationships: performs survey operation
  
- **Environmental Operation Concept**:
  - Root node: UAS
  - Properties: wind tolerance (≤25 kt), temperature range (-10 to +45°C)
  - Relationships: operates in environment
  
- **Communication System Concept**:
  - Root node: DataLink
  - Properties: range (≥50 km), encryption (AES-256)
  - Relationships: provides communication

**Talking Points**:
- "Conceptualizer uses NLP to extract semantic concepts from requirements"
- "Root nodes are identified by single output class (no class references them)"
- "Concepts show system structure implied by requirements"
- "Future: Deduplication will merge similar concepts automatically"
- "These concepts inform architecture development"

**DAS Debrief**:
```
You: "Looking at these concept graphs, what architectural patterns do you see?"

DAS: [Analyzes concepts, suggests architectural elements]
- Air vehicle subsystem implied by environmental requirements
- Communication subsystem implied by data link requirements
- Mission management system implied by survey requirements

You: "How do these concepts map to our BSEO ontology?"

DAS: [Discusses concept-to-class mappings, suggests refinements]
```

---

### 2.11 Thoughtful Discussion with DAS

**Action**: Deep dive into system architecture considerations

**DAS Discussion**:
```
You: "Based on the requirements and concepts we've extracted, what are the 
critical trade-offs for the Core.SE UAS system?"

DAS: [Analyzes and discusses]
Expected topics:
- Endurance vs. payload capacity
- Cost vs. capability (threshold vs. objective)
- Fixed-wing vs. VTOL for rapid deployment
- Environmental hardening impact on weight/cost

You: "The setup time requirement is ≤15 minutes. How does that constrain our 
platform choices?"

DAS: [Discusses launch methods]
- Hand launch or VTOL favored over catapult
- Pre-flight check automation
- Battery vs. fuel considerations
- Transportation case design

You: "What about the interoperability requirement? How does MIL-STD-6040 
compliance affect our architecture?"

DAS: [Discusses interface requirements]
- Data format standards
- Network protocol requirements
- Security/encryption needs
- Integration points with C4ISR

You: "Looking at the individuals we created from the UAS specifications, which 
platforms best satisfy our threshold requirements?"

DAS: [Analyzes UAS specs against requirements]
- Compares platforms on key parameters
- Identifies candidates meeting thresholds
- Notes which approach objectives
- Highlights trade-offs

You: "Can you identify any requirements conflicts or gaps?"

DAS: [Performs analysis]
- Checks for contradictions
- Identifies underspecified areas
- Suggests additional requirements that may be needed
```

**Talking Points**:
- "DAS integrates knowledge across documents, requirements, and ontologies"
- "This enables systems thinking - understanding relationships and trade-offs"
- "DAS can't make decisions, but provides analysis to support human judgment"
- "Conversation is preserved for future reference and audit trails"

---

### 2.12 Create UAS Architecture Diagram with DAS

**Action**: Generate architecture diagram using extracted concepts

**DAS Discussion**:
```
You: "I need you to create a UAS system architecture diagram for Core.SE. Use 
the concepts we extracted from requirements. Focus on the physical architecture 
showing major subsystems and their relationships."

DAS: [Asks clarifying questions]
- Level of detail?
- Specific notation (boxes and lines, formal language)?
- Include data flows or just structural composition?

You: "Show major subsystems as blocks, with composition relationships. Include 
interfaces between subsystems. Use the BSEO ontology classes."

DAS: [Generates architecture description/diagram]

Expected output format (text-based description that can be visualized):
```text
UAS_System [System]
├── AirVehicle_Subsystem [Subsystem]
│   ├── Propulsion [Component]
│   ├── FlightControl [Component]
│   └── Airframe [Component]
├── PayloadSubsystem [Subsystem]
│   ├── Sensor [Component]
│   ├── Gimbal [Component]
│   └── DataProcessor [Component]
├── CommunicationSubsystem [Subsystem]
│   ├── DataLink [Component]
│   ├── Encryption [Component]
│   └── Antenna [Component]
├── GroundControlStation [Subsystem]
│   ├── Display [Component]
│   ├── OperatorInterface [Component]
│   └── MissionPlanner [Component]
└── SupportEquipment [Subsystem]
    ├── LaunchRecovery [Component]
    ├── Transport [Component]
    └── Maintenance [Component]

Interfaces:
- AirVehicle ↔ PayloadSubsystem: Power, data, mounting
- PayloadSubsystem ↔ CommunicationSubsystem: Sensor data
- CommunicationSubsystem ↔ GroundControlStation: Telemetry, commands
- AirVehicle ↔ SupportEquipment: Launch, recovery, charging
```

You: "Can you map the requirements to this architecture? Which subsystems 
address which requirements?"

DAS: [Creates traceability mapping]
- Survey coverage → PayloadSubsystem + AirVehicle (endurance)
- Wind tolerance → AirVehicle (flight control)
- Setup time → SupportEquipment (launch method)
- Data link range → CommunicationSubsystem
- Interoperability → GroundControlStation (C4ISR interface)
```

**Talking Points**:
- "DAS generated this architecture based on requirements analysis"
- "Architecture uses ontology classes ensuring semantic consistency"
- "Traceability links requirements to architectural elements"
- "This can be exported to SysML or other modeling tools"
- "Human review and refinement is still essential"

---

### 2.13 Create Communication Architecture with DAS

**Action**: Develop communication architecture after discussion

**DAS Discussion**:
```
You: "Now I need a communication architecture. Show all data flows between 
subsystems and external systems."

DAS: [Asks clarifying questions]
- Include data rates/bandwidths?
- Show protocol layers?
- Include external interfaces (C4ISR)?

You: "Yes to all. Show the complete communication picture including security."

DAS: [Generates communication architecture]

Expected output:
```text
Communication Architecture:

Data Flows:
1. Air-to-Ground (AirVehicle → GroundControlStation)
   - Telemetry: Position, altitude, velocity, system health (10 Hz, 10 kbps)
   - Video: Real-time sensor feed (4K @ 30fps, 25 Mbps)
   - Protocol: Encrypted UDP over custom radio link
   - Security: AES-256 encryption, authentication

2. Ground-to-Air (GroundControlStation → AirVehicle)
   - Commands: Waypoint updates, mode changes, sensor control (1 Hz, 1 kbps)
   - Protocol: Encrypted TCP/IP over radio link
   - Security: AES-256 encryption, command authentication

3. Ground-to-C4ISR (GroundControlStation → External C4ISR)
   - Situational awareness data: Imagery, metadata, mission status
   - Protocol: MIL-STD-6040 compliant (Link 16 compatible)
   - Security: Type 1 encryption compatible
   - Interface: Ethernet, military connectors

4. Internal Subsystem Communication (onboard UAS)
   - AirVehicle ↔ PayloadSubsystem: CAN bus, 1 Mbps
   - PayloadSubsystem → CommunicationSubsystem: Ethernet, 100 Mbps
   - FlightControl ↔ Sensors: I2C, SPI buses

Network Topology:
- Star topology: GroundControlStation is central hub
- Air Vehicle is leaf node (single radio link)
- C4ISR integration via dedicated network interface

Fallback/Redundancy:
- Lost link: AirVehicle autonomous return-to-home
- Backup frequency for primary data link
- Emergency beacon for location
```

You: "How does this architecture satisfy the data link range and encryption requirements?"

DAS: [Maps communication architecture to requirements]
- ≥50 km range: Achieved via radio link specification
- AES-256 encryption: Applied to all air-ground communication
- MIL-STD-6040: Implemented in C4ISR interface layer
```

**Talking Points**:
- "Communication architecture shows information flow, not just structure"
- "Security requirements are embedded throughout the architecture"
- "Interoperability requirement drives C4ISR interface design"
- "Bandwidth analysis ensures sensor requirements can be met"
- "Fallback modes address lost link scenarios"

---

### 2.14 Ask DAS to Write a White Paper

**Action**: Generate comprehensive technical white paper

**DAS Discussion**:
```
You: "I need a white paper for Core.SE that we can review with stakeholders. 
It should cover the mission need, requirements analysis, architecture decisions, 
and trade-offs. Target audience is program management and senior engineers."

DAS: [Confirms scope and begins generation]

You: "Include sections on:
- Executive summary
- Mission context and operational need
- Requirements overview with KPP discussion
- System architecture
- Trade study results
- Risk areas
- Path forward"

DAS: [Generates white paper]
```

**Expected White Paper Structure**:
```markdown
# Core.SE UAS System White Paper

## Executive Summary
[Brief overview of capability, requirements, and recommended approach]

## Mission Context
[Discusses operational scenarios, user needs, why this system is needed]

## Requirements Analysis
[Reviews key requirements, discusses KPPs, notes thresholds vs objectives]

## System Architecture
[Describes physical, logical, and communication architectures]
[References diagrams generated earlier]

## Candidate Platforms
[Analyzes UAS options against requirements]
[Trade tables showing performance vs. requirements]

## Trade Study Summary
[Key trade-offs: endurance vs payload, cost vs performance, etc.]
[Rationale for architectural choices]

## Risk Assessment
[Technical risks: environmental hardening, interoperability, cost]
[Mitigation strategies]

## Development Path Forward
[Phases: requirements finalization, design, prototyping, test, fielding]
[Schedule milestones aligned to IOC requirement]

## Recommendations
[Platform selection, architecture approach, next steps]
```

**Review White Paper with Team**:
1. DAS presents generated white paper
2. Scroll through sections
3. Discuss key points:
   - "Notice how requirements drive architecture decisions"
   - "Trade study captures decision rationale"
   - "Risk section identifies areas needing attention"
   - "Path forward connects to IOC timeline requirement"

**DAS Follow-up**:
```
You: "Can you add a comparison table of the three UAS platforms from the 
specifications against our threshold requirements?"

DAS: [Generates comparison table]

You: "Add a cost-benefit analysis section discussing threshold vs objective trade-offs."

DAS: [Adds section with analysis]

You: "This is good. Export this white paper as a document."

DAS: [Provides download or saves to knowledge base]
```

**Talking Points**:
- "DAS synthesizes all project knowledge into coherent documentation"
- "White paper is based on actual requirements, architecture, and specifications"
- "Human review ensures accuracy and adds judgment/experience"
- "Document serves as baseline for stakeholder reviews and design activities"
- "DAS can iterate on the document based on feedback"

---

## Demonstration Wrap-Up

### Key Capabilities Demonstrated

**Review with SMEs**:

1. **Knowledge Management**
   - Document upload and chunking
   - Cross-project knowledge sharing via publishing
   - Semantic search and retrieval

2. **Requirements Engineering**
   - Requirements import and parsing
   - Threshold/Objective tracking
   - KPP identification
   - Cross-project requirements inheritance

3. **Ontology-Based Modeling**
   - Abstract class definition
   - Inheritance and extension
   - Reference ontologies
   - Individuals (instances)
   - Properties and relationships
   - Multiplicity and enumerations

4. **DAS AI Assistance**
   - Natural language interaction
   - Context-aware responses
   - Conversation continuity (thread management)
   - Concept extraction and analysis
   - Architecture generation
   - Documentation synthesis

5. **Project Inheritance**
   - Core → Core.SE knowledge flow
   - Published standards reuse
   - Ontology imports and extension
   - Requirements inheritance

6. **Requirements Analysis**
   - Conceptualizer (semantic extraction)
   - Concept graphs
   - Requirements-to-architecture traceability

7. **Architecture Development**
   - Physical architecture
   - Communication architecture
   - Requirements mapping

8. **Documentation Generation**
   - White paper synthesis
   - Trade study documentation
   - Decision rationale capture

---

## Questions to Pose to SMEs

1. **Requirements Process**:
   - "How does this compare to your current requirements management process?"
   - "Would the threshold/objective structure work for your projects?"
   - "How would you integrate this with existing tools (JIRA, DOORS, etc.)?"

2. **Ontology Value**:
   - "Do you see value in formal ontology modeling vs. traditional SysML?"
   - "How would ontology reasoning help in your system development?"
   - "What domain-specific ontologies would you need?"

3. **DAS Utility**:
   - "Where would DAS assistance be most valuable in your workflow?"
   - "What concerns do you have about AI-generated content?"
   - "How would you validate DAS recommendations?"

4. **Integration**:
   - "What external systems would you need ODRAS to integrate with?"
   - "How would you handle security/classification in ODRAS?"
   - "What export formats do you need (SysML, OSLC, etc.)?"

5. **Workflow**:
   - "How does ODRAS fit into your systems engineering V-model?"
   - "What roles would use ODRAS (requirements engineers, architects, etc.)?"
   - "What training would your team need?"

---

## Additional Information and Gaps

### Identified Gaps in Current Demo Plan

1. **Missing Artifacts**:
   - `demo_requirements_manager.py` script (needs creation)
   - Example BPMN workflow diagrams
   - Verification and validation workflow demo

2. **Features Not Demonstrated**:
   - Requirements traceability queries
   - Ontology reasoning (consistency checking)
   - Version control and change management
   - Multi-user collaboration
   - Access control and permissions
   - Export to external formats (SysML XMI, OSLC, etc.)

3. **Advanced Capabilities to Consider**:
   - Automated requirements validation against ontology
   - Impact analysis (what if requirement changes?)
   - Design alternative comparison
   - Requirement conflict detection
   - Completeness analysis (are all needs covered?)

4. **Workflow Integration**:
   - Show BPMN process for requirements review
   - Demonstrate approval workflows
   - Show notification system
   - Demonstrate audit trail

5. **Performance/Scale**:
   - Demonstrate with larger requirements sets (50+)
   - Show response time for complex queries
   - Test with multiple simultaneous users

### Recommendations for Enhancement

1. **Create Missing Scripts**:
   - `demo_requirements_manager.py` - API interaction examples
   - `validate_requirements.py` - Automated validation
   - `generate_traceability_matrix.py` - Requirements tracing

2. **Prepare Backup Content**:
   - Have alternative DAS discussion prompts if conversations don't flow
   - Prepare canned responses for common questions
   - Have troubleshooting steps ready

3. **Recording/Playback**:
   - Consider recording successful demo run
   - Create video tutorials for self-paced learning
   - Prepare presentation slides as backup

4. **Timing Management**:
   - Phase 1 (Core Project): ~45-60 minutes
   - Phase 2 (Core.SE Project): ~60-90 minutes
   - Q&A: ~30 minutes
   - Total: 2.5-3 hours

5. **Contingency Planning**:
   - What if DAS is slow/unavailable? (Use pre-generated responses)
   - What if imports fail? (Have pre-loaded backup)
   - What if ontology visualization doesn't work? (Show JSON/RDF)

---

## Pre-Demo Checklist

### System Preparation
- [ ] All ODRAS services running and healthy
- [ ] Database initialized with clean state
- [ ] `das_service` account verified (Username: das_service, Password: das_service_2024!)
- [ ] All demo documents uploaded to accessible location
- [ ] Network connectivity verified
- [ ] Backup database snapshot taken

### Content Preparation
- [ ] `how_to_write_a_requirement.md` created and reviewed
- [ ] `core_se_project_description.md` created and reviewed
- [ ] `core_requirements.md` available
- [ ] `core_se_requirements.md` available
- [ ] `uas_specifications.md` available
- [ ] All documents follow requirements format standards

### Dry Run
- [ ] Complete walkthrough performed
- [ ] Timing verified
- [ ] DAS responses reviewed for appropriateness
- [ ] Screenshots/recordings captured as backup
- [ ] Contingency plans prepared

### Audience Preparation
- [ ] SME invitations sent with agenda
- [ ] Background materials distributed (optional reading)
- [ ] Expectations set (interactive demo, not lecture)
- [ ] Technical level confirmed (how deep to go?)
- [ ] Q&A time allocated

---

## Post-Demo Follow-Up

1. **Gather Feedback**:
   - Survey or feedback form
   - Specific questions about usability, value, concerns
   - Feature requests and priorities

2. **Document Issues**:
   - Any bugs or problems encountered
   - Performance concerns
   - Usability problems
   - Missing features identified

3. **Next Steps**:
   - Schedule follow-up sessions if needed
   - Plan pilot project with SMEs
   - Define training program
   - Establish support process

4. **Iterate**:
   - Update demo script based on lessons learned
   - Refine DAS prompts for better responses
   - Enhance documentation
   - Address technical gaps

---

## Appendix: Quick Reference

### Key User Accounts
- **Admin**: admin / [set password]
- **Demo User**: das_service / das_service_2024!
- **Test User**: jdehart / [set password]

### Key Documents
- Core: `core_requirements.md`, `how_to_write_a_requirement.md`
- Core.SE: `core_se_requirements.md`, `core_se_project_description.md`, `uas_specifications.md`

### Key Ontology Prefixes
- Core: `core` → `http://usn/adt/core/`
- BSEO: `bseo` → `http://usn/adt/SE/core/bseo/`
- RNM: `bseornm` → `http://usn/adt/SE/core/bseornm/`

### Useful DAS Prompts
- "Summarize the key requirements for [topic]"
- "What are the trade-offs between [option A] and [option B]?"
- "How does [requirement] impact the architecture?"
- "What are the risks associated with [approach]?"
- "Generate a [document type] for [purpose]"

---

**End of Demonstration Script**










