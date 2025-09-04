# ProcOS System Specification

This specification complements the prompt provided for use with Cursor LLMs or similar AI-assisted IDEs. It serves as a detailed guide during the build cycle, ensuring the implementation stays aligned with the core vision of ProcOS: a process-oriented operating system that is simple, usable for generalists (visual BPMN editing), and powerful for advanced users (probabilistic LLM execution with deterministic tools). Use this spec alongside the prompt to iterate on code, BPMN XML, and diagrams—e.g., prompt Cursor: "Implement the nanocernel per the spec, keeping it under 100 lines."

The spec is structured for phased building: start with the nanocernel, then DAS, PDO, TDE, and integrations. Emphasize simplicity—avoid bloat, ensure PDO's BPMN diagram remains unmodified for new tools/tasks (rely on TDE's LLM prompts), and incorporate a while-loop nature in PDO for dynamic task handling. Leverage AWS MCP servers (via Amazon Q CLI in Cursor) for diagrams, docs, and CDK stacks during development and deployment.

## 1. System Overview and Goals

- **System Name**: ProcOS (Process-Oriented Operating System).
- **Vision**: A lean OS where BPMN processes are the core, allowing users (e.g., traders, engineers, supply chain professionals) to extract domain knowledge into visual workflows without coding. Starts blank and evolves via DAS, which generates processes from natural language. Functionality focuses on usability, probabilistic execution (LLM-driven fuzzy decisions), deterministic tools, and knowledge persistence (vector store + graph DB).
- **Build Cycle Guidance**: 
  - Phase 1: Nanocernel (bootstrap).
  - Phase 2: DAS (ambient intelligence and memory).
  - Phase 3: PDO and TDE (process/task execution).
  - Phase 4: Integrations (tools, MCP servers, testing).
  - Use AWS MCP: Prompt Amazon Q for diagrams (e.g., "Generate ProcOS architecture diagram using Diagram MCP") and CDK stacks (e.g., "Create CDK for ECS deployment via CDK MCP").
  - Testing: Log all iterations/errors to vector store/graph DB for DAS learning; ensure no BPMN modifications for new features.
- **Non-Functional Requirements**:
  - Simplicity: Components generic and modular; nanocernel <100 lines.
  - Scalability: Horizontal TDE spawning; AWS-ready (ECS for TDEs, Bedrock for LLMs).
  - Persistence: All logs/interactions to vector store (semantic) and graph DB (relational).
  - Date Context: As of September 03, 2025, use latest libraries (e.g., Python 3.12, Camunda 8.x).

## 2. Architecture

ProcOS uses a nanocernel for bootstrapping, with BPMN for processes (via Camunda or lightweight state machine). DAS is central, monitoring and generating. PDO handles workflow orchestration in a while-loop style (loop until no pending tasks). TDE executes tasks with LLM decisions, ensuring flexibility without BPMN changes.

- **High-Level Flow**:
  1. Nanocernel initializes and listens for process triggers.
  2. User/DAS triggers a BPMN process.
  3. Nanocernel spawns PDO (BPMN instance).
  4. PDO loops: Query state (Camunda/state machine), spawn TDEs for ready tasks (parallel/sequential), update state.
  5. TDE uses LLM to decide/execute task, logs via DAS.
  6. DAS monitors, generates new processes, persists knowledge.

- **Key Constraints**:
  - PDO's BPMN diagram is generic and immutable for new tools/tasks—while-loop gateway checks for tasks; LLM in TDE handles specifics via prompts.
  - No inter-component chatter beyond necessary (e.g., PDO spawns TDEs via API calls).
  - Use AWS MCP servers for build: Diagram MCP for visuals, Documentation MCP for specs, CDK MCP for IaC.

## 3. Components

### 3.1 Nanocernel
- **Description**: Ultra-lean Python script (~50-100 lines max) for system bootstrap. No execution—only init and monitoring.
- **Functionality**:
  - Initialize: Camunda API (or `transitions` state machine), vector store (Milvus/Pinecone), graph DB (Neo4j), DAS.
  - Listen: Monitor Camunda/state machine for new process instances; spawn PDO on trigger.
  - Terminate idle resources; no while-loops here (defer to PDO).
- **Build Guidance**: Start here. Prompt Cursor: "Write Python nanocernel (<100 lines) to init Camunda, Milvus, Neo4j, DAS, and listen for process triggers to spawn PDO."
- **Dependencies**: Python 3.12, camunda-external-client, milvus-client, neo4j-driver.
- **Deployment**: Local/AWS (Lambda or ECS via CDK MCP).

### 3.2 DAS (Digital Assistance System)
- **Description**: Ambient intelligence, always-on Python process started by nanocernel. Captures interactions, generates BPMN, learns via memory.
- **Functionality**:
  - Input: Text/voice (CLI/Flask API) for commands like "save to memory" (generates BPMN for file write).
  - Monitoring: Tracks user actions, process states, logs to vector store (embeddings) and graph DB (nodes/edges, e.g., process-task relations).
  - Generation: Creates BPMN XML from inputs using BPMN.io lib; pre-loads a priori memory (5-10 samples).
  - Memory: Short-term (in-memory cache); long-term (persist to stores); "save to memory" writes to both.
  - Suggestions: Contextual (e.g., refine task based on logs); learns from errors/iterations.
- **Build Guidance**: Build after nanocernel. Prompt Cursor: "Implement DAS Python script with text input, BPMN generation, and logging to Milvus/Neo4j."
- **Dependencies**: openai/ollama, bpmn-io, flask (for API), speech_recognition (voice optional).
- **Deployment**: Persistent service (e.g., AWS ECS via CDK MCP).

### 3.3 PDO (Process Definition Orchestrator)
- **Description**: Generic BPMN process (XML template via BPMN.io) for workflow management. While-loop nature: Loop gateway queries state until no tasks remain.
- **Functionality**:
  - Query: Camunda API/state machine for active tasks, states (previous/next), parallel splits.
  - Spawn: Dynamically create TDEs for ready tasks (one per task, parallel if needed).
  - Update: Report outcomes to Camunda/state machine; handle feedback loops.
  - While-Loop: BPMN loop gateway: "Pending tasks?" → Fetch/spawn → Update → Loop.
  - Immutability: No BPMN changes for new tools/tasks—routes to TDE's LLM for decisions.
- **Build Guidance**: BPMN XML first. Prompt Cursor: "Generate BPMN XML for generic PDO with loop gateway for task handling, querying Camunda, spawning TDEs."
- **Dependencies**: Integrated with Camunda; fallback to `transitions` if bloated.
- **Deployment**: Run as Camunda instance; scale via AWS EKS.

### 3.4 TDE (Task Definition Executor)
- **Description**: Generic BPMN process (XML template) for task execution. LLM at front for decisions; spawned by PDO.
- **Functionality**:
  - Receive: Task input from PDO.
  - Decide: LLM prompt evaluates input, chooses action (e.g., "write file" or "run MATLAB") without BPMN changes—prompts stored in vector store.
  - Execute: Probabilistic (loop until convergence, e.g., Monte Carlo for weights); deterministic (call tools/Docker).
  - Log: Outcomes/errors to DAS (vector store/graph DB).
  - Terminate: After task; isolated.
- **Build Guidance**: BPMN XML with LLM integration. Prompt Cursor: "Generate BPMN XML for TDE with LLM decision gateway, executing actions via prompts, logging to DAS stores."
- **Dependencies**: openai/ollama, docker-py.
- **Deployment**: Ephemeral ECS tasks via CDK MCP.

## 4. Integrations and Tools

- **State Management**: Prefer Camunda for features (user tasks/scripts); fallback to `transitions` if bloated—state machine tracks/publishes process states simply.
- **Memory Stores**: Milvus (vector embeddings for semantic search); Neo4j (graphs for relations).
- **AWS MCP Servers**: Use Amazon Q CLI: Diagram MCP for arch visuals; Documentation MCP for specs; CDK MCP for IaC (e.g., ECS, Bedrock, Neptune).
- **Other Tools**: BPMN.io for XML; React Flow for ontologies; Docker for containers.

## 5. Functional Requirements

- Process Generation: DAS creates BPMN from inputs.
- Execution: Probabilistic/deterministic; parallel handling in PDO.
- Learning: DAS logs everything for refinement.
- Usability: No code for new features—update LLM prompts only.

## 6. Build Cycle Phases

1. Nanocernel: Init and deploy.
2. DAS: Input/generation/logging.
3. PDO/TDE: BPMN XML and testing.
4. Full Test: Sample process (e.g., "save to memory").
5. AWS: CDK stack via MCP.

Use this spec to guide prompts—e.g., "Build per spec section 3.1." Iterate with logs to DAS for self-improvement.