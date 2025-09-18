# ProcOS System Specification<br>
<br>
This specification complements the prompt provided for use with Cursor LLMs or similar AI-assisted IDEs. It serves as a detailed guide during the build cycle, ensuring the implementation stays aligned with the core vision of ProcOS: a process-oriented operating system that is simple, usable for generalists (visual BPMN editing), and powerful for advanced users (probabilistic LLM execution with deterministic tools). Use this spec alongside the prompt to iterate on code, BPMN XML, and diagrams—e.g., prompt Cursor: "Implement the nanocernel per the spec, keeping it under 100 lines."<br>
<br>
The spec is structured for phased building: start with the nanocernel, then DAS, PDO, TDE, and integrations. Emphasize simplicity—avoid bloat, ensure PDO's BPMN diagram remains unmodified for new tools/tasks (rely on TDE's LLM prompts), and incorporate a while-loop nature in PDO for dynamic task handling. Leverage AWS MCP servers (via Amazon Q CLI in Cursor) for diagrams, docs, and CDK stacks during development and deployment.<br>
<br>
## 1. System Overview and Goals<br>
<br>
- **System Name**: ProcOS (Process-Oriented Operating System).<br>
- **Vision**: A lean OS where BPMN processes are the core, allowing users (e.g., traders, engineers, supply chain professionals) to extract domain knowledge into visual workflows without coding. Starts blank and evolves via DAS, which generates processes from natural language. Functionality focuses on usability, probabilistic execution (LLM-driven fuzzy decisions), deterministic tools, and knowledge persistence (vector store + graph DB).<br>
- **Build Cycle Guidance**:<br>
  - Phase 1: Nanocernel (bootstrap).<br>
  - Phase 2: DAS (ambient intelligence and memory).<br>
  - Phase 3: PDO and TDE (process/task execution).<br>
  - Phase 4: Integrations (tools, MCP servers, testing).<br>
  - Use AWS MCP: Prompt Amazon Q for diagrams (e.g., "Generate ProcOS architecture diagram using Diagram MCP") and CDK stacks (e.g., "Create CDK for ECS deployment via CDK MCP").<br>
  - Testing: Log all iterations/errors to vector store/graph DB for DAS learning; ensure no BPMN modifications for new features.<br>
- **Non-Functional Requirements**:<br>
  - Simplicity: Components generic and modular; nanocernel <100 lines.<br>
  - Scalability: Horizontal TDE spawning; AWS-ready (ECS for TDEs, Bedrock for LLMs).<br>
  - Persistence: All logs/interactions to vector store (semantic) and graph DB (relational).<br>
  - Date Context: As of September 03, 2025, use latest libraries (e.g., Python 3.12, Camunda 8.x).<br>
<br>
## 2. Architecture<br>
<br>
ProcOS uses a nanocernel for bootstrapping, with BPMN for processes (via Camunda or lightweight state machine). DAS is central, monitoring and generating. PDO handles workflow orchestration in a while-loop style (loop until no pending tasks). TDE executes tasks with LLM decisions, ensuring flexibility without BPMN changes.<br>
<br>
- **High-Level Flow**:<br>
  1. Nanocernel initializes and listens for process triggers.<br>
  2. User/DAS triggers a BPMN process.<br>
  3. Nanocernel spawns PDO (BPMN instance).<br>
  4. PDO loops: Query state (Camunda/state machine), spawn TDEs for ready tasks (parallel/sequential), update state.<br>
  5. TDE uses LLM to decide/execute task, logs via DAS.<br>
  6. DAS monitors, generates new processes, persists knowledge.<br>
<br>
- **Key Constraints**:<br>
  - PDO's BPMN diagram is generic and immutable for new tools/tasks—while-loop gateway checks for tasks; LLM in TDE handles specifics via prompts.<br>
  - No inter-component chatter beyond necessary (e.g., PDO spawns TDEs via API calls).<br>
  - Use AWS MCP servers for build: Diagram MCP for visuals, Documentation MCP for specs, CDK MCP for IaC.<br>
<br>
## 3. Components<br>
<br>
### 3.1 Nanocernel<br>
- **Description**: Ultra-lean Python script (~50-100 lines max) for system bootstrap. No execution—only init and monitoring.<br>
- **Functionality**:<br>
  - Initialize: Camunda API (or `transitions` state machine), vector store (Milvus/Pinecone), graph DB (Neo4j), DAS.<br>
  - Listen: Monitor Camunda/state machine for new process instances; spawn PDO on trigger.<br>
  - Terminate idle resources; no while-loops here (defer to PDO).<br>
- **Build Guidance**: Start here. Prompt Cursor: "Write Python nanocernel (<100 lines) to init Camunda, Milvus, Neo4j, DAS, and listen for process triggers to spawn PDO."<br>
- **Dependencies**: Python 3.12, camunda-external-client, milvus-client, neo4j-driver.<br>
- **Deployment**: Local/AWS (Lambda or ECS via CDK MCP).<br>
<br>
### 3.2 DAS (Digital Assistance System)<br>
- **Description**: Ambient intelligence, always-on Python process started by nanocernel. Captures interactions, generates BPMN, learns via memory.<br>
- **Functionality**:<br>
  - Input: Text/voice (CLI/Flask API) for commands like "save to memory" (generates BPMN for file write).<br>
  - Monitoring: Tracks user actions, process states, logs to vector store (embeddings) and graph DB (nodes/edges, e.g., process-task relations).<br>
  - Generation: Creates BPMN XML from inputs using BPMN.io lib; pre-loads a priori memory (5-10 samples).<br>
  - Memory: Short-term (in-memory cache); long-term (persist to stores); "save to memory" writes to both.<br>
  - Suggestions: Contextual (e.g., refine task based on logs); learns from errors/iterations.<br>
- **Build Guidance**: Build after nanocernel. Prompt Cursor: "Implement DAS Python script with text input, BPMN generation, and logging to Milvus/Neo4j."<br>
- **Dependencies**: openai/ollama, bpmn-io, flask (for API), speech_recognition (voice optional).<br>
- **Deployment**: Persistent service (e.g., AWS ECS via CDK MCP).<br>
<br>
### 3.3 PDO (Process Definition Orchestrator)<br>
- **Description**: Generic BPMN process (XML template via BPMN.io) for workflow management. While-loop nature: Loop gateway queries state until no tasks remain.<br>
- **Functionality**:<br>
  - Query: Camunda API/state machine for active tasks, states (previous/next), parallel splits.<br>
  - Spawn: Dynamically create TDEs for ready tasks (one per task, parallel if needed).<br>
  - Update: Report outcomes to Camunda/state machine; handle feedback loops.<br>
  - While-Loop: BPMN loop gateway: "Pending tasks?" → Fetch/spawn → Update → Loop.<br>
  - Immutability: No BPMN changes for new tools/tasks—routes to TDE's LLM for decisions.<br>
- **Build Guidance**: BPMN XML first. Prompt Cursor: "Generate BPMN XML for generic PDO with loop gateway for task handling, querying Camunda, spawning TDEs."<br>
- **Dependencies**: Integrated with Camunda; fallback to `transitions` if bloated.<br>
- **Deployment**: Run as Camunda instance; scale via AWS EKS.<br>
<br>
### 3.4 TDE (Task Definition Executor)<br>
- **Description**: Generic BPMN process (XML template) for task execution. LLM at front for decisions; spawned by PDO.<br>
- **Functionality**:<br>
  - Receive: Task input from PDO.<br>
  - Decide: LLM prompt evaluates input, chooses action (e.g., "write file" or "run MATLAB") without BPMN changes—prompts stored in vector store.<br>
  - Execute: Probabilistic (loop until convergence, e.g., Monte Carlo for weights); deterministic (call tools/Docker).<br>
  - Log: Outcomes/errors to DAS (vector store/graph DB).<br>
  - Terminate: After task; isolated.<br>
- **Build Guidance**: BPMN XML with LLM integration. Prompt Cursor: "Generate BPMN XML for TDE with LLM decision gateway, executing actions via prompts, logging to DAS stores."<br>
- **Dependencies**: openai/ollama, docker-py.<br>
- **Deployment**: Ephemeral ECS tasks via CDK MCP.<br>
<br>
## 4. Integrations and Tools<br>
<br>
- **State Management**: Prefer Camunda for features (user tasks/scripts); fallback to `transitions` if bloated—state machine tracks/publishes process states simply.<br>
- **Memory Stores**: Milvus (vector embeddings for semantic search); Neo4j (graphs for relations).<br>
- **AWS MCP Servers**: Use Amazon Q CLI: Diagram MCP for arch visuals; Documentation MCP for specs; CDK MCP for IaC (e.g., ECS, Bedrock, Neptune).<br>
- **Other Tools**: BPMN.io for XML; React Flow for ontologies; Docker for containers.<br>
<br>
## 5. Functional Requirements<br>
<br>
- Process Generation: DAS creates BPMN from inputs.<br>
- Execution: Probabilistic/deterministic; parallel handling in PDO.<br>
- Learning: DAS logs everything for refinement.<br>
- Usability: No code for new features—update LLM prompts only.<br>
<br>
## 6. Build Cycle Phases<br>
<br>
1. Nanocernel: Init and deploy.<br>
2. DAS: Input/generation/logging.<br>
3. PDO/TDE: BPMN XML and testing.<br>
4. Full Test: Sample process (e.g., "save to memory").<br>
5. AWS: CDK stack via MCP.<br>
<br>
Use this spec to guide prompts—e.g., "Build per spec section 3.1." Iterate with logs to DAS for self-improvement.<br>

