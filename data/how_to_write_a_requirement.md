# How to Write a Requirement

## Introduction
This guide provides standards and best practices for writing clear, testable, and verifiable requirements for systems engineering projects. Requirements form the foundation of system design and are critical for successful project execution.

## Requirement Anatomy

A well-written requirement consists of:
1. **Designation** - [KPP], [KPA], [KPC], or standard requirement
2. **Subject** - The system, component, or entity being specified
3. **Action** - "shall" for mandatory requirements
4. **Object** - What the subject must do or be
5. **Condition** - Context or circumstances when applicable
6. **Threshold [T]** - Minimum acceptable performance
7. **Objective [O]** - Desired performance level (when applicable)

### Example:
```
[KPP] The UAS shall survey ≥ 5 km² within ≤ 2 hours [T] and survey ≥ 10 km² within ≤ 2 hours [O].
```

## Key Performance Parameters (KPP)

**KPP** (Key Performance Parameter) requirements are mission-critical. System cannot proceed without meeting these:
- Must be measurable and testable
- Failure to meet KPPs results in system rejection
- Limited to 3-5 per system (too many dilutes importance)
- Examples: Coverage area, endurance, operational range

## Supporting Performance Parameters

### KPA (Key Performance Attribute)
Attributes that enable effective system operation but are not mission-critical:
- Example: Training time, crew size, setup time

### KPC (Key Performance Capability)
Specific operational capabilities that enhance mission effectiveness:
- Example: Operational radius, communication range

## Writing Guidelines

### 1. Use "Shall" Language
- **Correct**: "The system shall operate at -20°C"
- **Incorrect**: "The system should/will/must operate at -20°C"

### 2. Be Specific and Measurable
- **Correct**: "The UAS shall achieve ≤ 15 min setup time"
- **Incorrect**: "The UAS shall be quick to deploy"

### 3. Include Units and Tolerances
- Always specify units: km, hours, kg, °C, knots
- Use standard symbols: ≥ (greater than or equal), ≤ (less than or equal)
- Include ranges when appropriate: -10°C to +45°C

### 4. Separate Threshold [T] and Objective [O]
- **[T]** = Minimum acceptable performance (contract requirement)
- **[O]** = Desired performance (stretch goal)
- Not all requirements need objectives

### 5. One Requirement Per Statement
- **Correct**: 
  - "The UAS shall operate in winds ≤ 25 kt [T]"
  - "The UAS shall operate from -10°C to +45°C [T]"
- **Incorrect**: "The UAS shall operate in winds ≤ 25 kt and from -10°C to +45°C"

### 6. Use Active Voice
- **Correct**: "The system shall encrypt data using AES-256"
- **Incorrect**: "Data shall be encrypted by the system using AES-256"

### 7. Avoid Ambiguity
- **Correct**: "The camera shall provide ≥ 4K resolution (3840×2160 pixels)"
- **Incorrect**: "The camera shall provide high resolution"

## Common Requirements Categories

### Performance Requirements
Quantifiable system capabilities:
- Speed, range, endurance
- Coverage area, altitude
- Processing time, response time

### Environmental Requirements
Operating conditions:
- Temperature range
- Wind tolerance
- Precipitation limits
- Altitude range

### Functional Requirements
What the system must do:
- Autonomous navigation
- Data transmission
- Sensor capabilities
- Control modes

### Interface Requirements
How system connects with external entities:
- Communication protocols (MIL-STD-6040)
- Data link specifications
- Interoperability standards
- Physical interfaces

### Reliability/Maintainability Requirements
System support characteristics:
- Mean time between failures (MTBF)
- Maintenance intervals
- Repair time
- Operational availability

### Safety Requirements
Risk mitigation and safe operation:
- Fail-safe modes
- Emergency procedures
- Collision avoidance
- Geofencing

## Requirements Traceability

Each requirement should be:
1. **Uniquely Identifiable** - Assign requirement IDs (REQ-001, REQ-002)
2. **Traceable Upward** - Links to higher-level requirements or needs
3. **Traceable Downward** - Links to design elements or lower-level requirements
4. **Verifiable** - Define how requirement will be tested/verified

## Verification Methods

Specify how each requirement will be verified:
- **Test** - Physical testing/measurement
- **Analysis** - Mathematical modeling/simulation
- **Inspection** - Visual examination
- **Demonstration** - Observable operation

## Common Pitfalls to Avoid

### 1. Vague Language
❌ "The system shall be user-friendly"
✓ "The system shall require ≤ 40 hours operator training [T]"

### 2. Implementation Specification
❌ "The system shall use a Raspberry Pi 4"
✓ "The system shall process imagery at ≥ 10 frames per second"

### 3. Mixing Requirements and Rationale
❌ "The UAS shall fly for ≥ 3 hours because missions are long"
✓ "The UAS shall sustain continuous flight ≥ 3 hours [T]"

### 4. Unverifiable Requirements
❌ "The system shall be easy to maintain"
✓ "The system shall support component replacement within ≤ 30 minutes using standard tools [T]"

### 5. Compound Requirements
❌ "The UAS shall have 4K camera and thermal sensor and fly 100 km"
✓ Split into separate requirements

## Requirements Review Checklist

Before finalizing requirements, verify:
- [ ] Uses "shall" language
- [ ] Includes specific, measurable criteria
- [ ] Specifies units and tolerances
- [ ] Distinguishes [T] threshold from [O] objective
- [ ] Contains one requirement per statement
- [ ] Uses active voice
- [ ] Avoids ambiguous terms
- [ ] Includes verification method
- [ ] Is uniquely identifiable
- [ ] Is traceable to higher-level needs

## Example Requirements Set

```markdown
[KPP] The UAS shall survey ≥ 5 km² within ≤ 2 hours [T] and survey ≥ 10 km² within ≤ 2 hours [O].

The system shall fly grid patterns with cross-track error ≤ 10 m [T] and ≤ 5 m [O].

[KPP] The UAS shall operate safely in steady wind ≤ 25 kt [T].

The UAS shall remain fully operational from −10 °C to +45 °C [T] and from −20 °C to +50 °C [O].

The UAS shall be mission-ready ≤ 15 min from arrival on scene [T].

[KPP] The UAS shall sustain continuous flight ≥ 3 hours without refuel or battery change [T] and ≥ 4 hours [O].

[KPC] The UAS shall maintain a minimum operational radius of 50 km from the ground control station [O].

The system shall provide line-of-sight data link ≥ 50 km with AES-256 encryption [T].

The UAS shall include a 4K visible camera with optical zoom on a 3-axis gimbal [T] and shall include an 8K camera [O].

[KPA] The system shall be deployable and operable by ≤ 2 personnel [T] and operator training shall be ≤ 40 hours [T] and ≤ 30 hours [O].
```

## Summary

Good requirements are:
- **Clear** - No ambiguity in interpretation
- **Concise** - One requirement per statement
- **Feasible** - Technically achievable
- **Necessary** - Must support system objectives
- **Verifiable** - Can be tested/measured
- **Unambiguous** - Only one interpretation possible

Following these guidelines ensures requirements effectively communicate stakeholder needs and provide a solid foundation for system design and development.










