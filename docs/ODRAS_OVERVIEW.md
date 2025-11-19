# ODRAS Overview

**ODRAS** (Ontology-Driven Requirements Analysis System) is a problem-agnostic knowledge platform that assembles project-specific environments from a shared architectural core.

## Core Principles

- **Problem agnosticism**: Reuse the same software fabric across diverse missions
- **Composable capability delivery**: Pluggable workbenches expose new functionality without code rewrites
- **Continuous alignment**: Governance rules cascade from parent to child projects with local overrides

## System Architecture

ODRAS operates through a hierarchical project structure:
- **L0 projects**: Enterprise programs with mission narrative, policy canon, funding guardrails
- **L1 projects**: Campaign plans, capability roadmaps, milestone schedules
- **L2 projects**: Day-to-day execution, work orders, sprint plans, supplier coordination

**Project Cells**: Cross-functional team enclaves with dedicated workbench instances, tracked via "batting average" performance metrics.

## Key Workbenches

- **Knowledge Workbench**: Document ingestion, enrichment, ontology alignment, validation
- **Requirements Workbench**: Structured authoring, traceability, publishing pipelines
- **Ontology Workbench**: Author/edit domain vocabularies, manage imports/versioning
- **CQMT Workbench**: Competency questions and microtheories for test-driven ontology development
- **DAS Workbench**: Decision Assistance System with LLM-powered Q&A and suggestions

## Use Cases

1. Ontology management: author/edit domain vocabularies; validate; manage imports/versioning
2. Requirements management: extract, review, approve, trace requirements to model elements
3. System conceptualization: propose components/functions with traceability
4. SysML/SysML v2 export: generate concept definitions/model skeletons for MBSE tools
5. ReqIF export: exchange approved requirements with external RM tools
6. LLM-assisted SE expert: grounded Q&A, suggestions, critiques that improve with project history
7. Traceability and impact analysis: visualize links, assess ripple effects from changes
8. Interface definition and ICD generation: derive and publish interface views
9. Compliance mapping: link requirements/model elements to standards, produce coverage reports
10. Trade studies and decision support: graph-based analyses on dependencies and alternatives
11. Knowledge ingestion and glossary: build controlled glossary from ingested knowledge
12. Risk/assumptions/uncertainty tracking: attach confidences/assumptions, surface hotspots
13. Test planning and V&V: derive verification methods, export test case stubs
14. Program communications: generate model-backed briefs/white papers and status summaries
15. Integration and automation: BPMN-driven tasks, webhooks, connectors to enterprise toolchains
16. Reliability and sustainment: treat RAM and sustainment as first-class (MTBF/MTTR, logistics constraints)

## Origin

ODRAS emerged from supporting Navy ADT and WIRR efforts, where meetings lacked synthesis between vendor pitches and Navy outcomes. The system uses a systems-engineering ontology to guide probabilistic requirement extraction from CDDs, ICDs, and AoAs, producing traceable conceptual system estimates with confidence weighting.

**Early Results**: The reqFlow prototype (10/2023) extracted 435 requirement candidates from the FLRAA CDD in ~5 minutes, bootstrapping a conceptual architecture with components, processes, functions, and interfaces.

## Technical Foundation

- **BPMN Workflows**: All capabilities orchestrated through visual BPMN process definitions
- **Event Bus**: Connective tissue for workbench coordination and DAS actions
- **Containerization**: Workbench isolation with attribute-based access control
- **Multi-Database**: PostgreSQL, Neo4j, Qdrant, Redis, Fuseki for different data types
- **RAG System**: Hybrid search combining vector similarity and keyword matching

## DAS Integration

The Decision Assistance System (DAS) provides:
- Reactive prompts and suggested actions based on analyst behavior
- Project context awareness with conversation memory
- RAG-powered knowledge retrieval from project documents
- Proactive capabilities (roadmap): initiate investigations, recommend acquisitions, schedule tasks

