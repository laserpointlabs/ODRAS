## Concept Tool — Comprehensive Specification (v1.0)<br>
<br>
This specification defines the architecture, data models, APIs, workflows, and governance for the Concept Tool. It builds on `docs/concept_need_reviewed.md` and turns it into an implementable plan.<br>
<br>
## 1. Overview<br>
<br>
- **Purpose**: Manage projects and documents; extract requirements; conceptualize systems; govern ontology-backed knowledge; and enable safe, auditable LLM-assisted workflows.<br>
- **Audience**: Product, engineering, ontology, data governance, QA, and devops teams.<br>
- **References**: `docs/concept_need_reviewed.md` (Reviewed Needs v0.1).<br>
<br>
## 2. Goals and Non-goals<br>
<br>
- **Goals**:<br>
  - End-to-end pipeline: ingest → parse → chunk/embed → extract requirements → review/approve → conceptualize → persist → query/report.<br>
  - RDF as canonical source; Neo4j as a projection.<br>
  - Schema-constrained LLM outputs (JSON) with prompt governance and evaluation.<br>
  - UI for ontology workbench, requirements console, conceptual model view, query studio, and RAG knowledge management.<br>
- **Non-goals** (v1.0):<br>
  - Full auto-ontology extraction (roadmap).<br>
  - Multi-cloud vendor-specific managed services integration beyond standard OSS components.<br>
<br>
## 3. User Roles and Permissions (RBAC)<br>
<br>
- **Admin**: Org/project admin, settings, user management, secrets, approvals override.<br>
- **Architect**: Ontology editing, conceptualization operations, projections.<br>
- **SME**: Requirement review/approval, RAG knowledge curation.<br>
- **Viewer**: Read-only across approved items, run read-only queries.<br>
<br>
## 4. Functional Requirements<br>
<br>
- **Project/User Management**: CRUD projects, invite users, assign roles; audit log of changes.<br>
- **Document Ingestion**: Upload PDF/DOCX/MD/TXT; OCR; capture metadata; version documents; delta re-ingest.<br>
- **Chunking/Embeddings**: Configurable chunk size/overlap; embeddings stored with metadata; re-embed on model/parser change.<br>
- **Requirement Extraction**: Detect patterns (shall/should/will/must; passive voice); quality checks; dedup; link to source spans; version and review workflow.<br>
- **Ontology Workbench**: CRUD Classes, Object/Data/Annotation properties; manage URIs/datatypes; React Flow graph and tree views.<br>
- **Conceptualization**: Generate candidate Components, Interfaces, Processes, Functions, Conditions; cluster with probabilities; convergence criteria; persistence.<br>
- **Traceability**: `Requirement → constrained_by/satisfied_by/verified_by/derived_from/refines/...` and links to concepts/tests.<br>
- **RAG Knowledge Management**: Upload a priori knowledge (e.g., requirement-writing guides); parse, embed, validate; enable per task/persona; citations.<br>
- **NL → Query**: Generate SPARQL/Cypher with preview and read-only execution by default; schema-aware validation.<br>
- **Reporting/Export**: Requirements and conceptualization reports; ReqIF/OSLC, CSV/JSON/TTL, PDF/DOCX; MBSE export to Teamwork Cloud (SysML); BPMN to Camunda.<br>
<br>
## 5. Non-functional Requirements<br>
<br>
- **Performance**:<br>
  - Ingestion parse throughput: ≥ 30 pages/minute per worker.<br>
  - Requirement extraction latency: p95 ≤ 5s per 10 pages with cached embeddings.<br>
  - NL→query generation: p95 ≤ 2s (local) / ≤ 4s (remote LLM).<br>
- **Reliability**: 99.5% monthly availability for APIs; idempotent pipelines with retries/backoff.<br>
- **Security**: RBAC, project isolation, PII scanning in RAG uploads, secrets via vault, TLS in transit.<br>
- **Auditability**: Immutable logs for approvals, ontology edits, prompt usage, query executions.<br>
- **Portability**: Dockerized; single-node compose for dev; scalable services for prod.<br>
<br>
## 6. System Architecture<br>
<br>
```mermaid<br>
graph TD<br>
  subgraph UI[Web UI]<br>
    A[Ontology Workbench]<br>
    B[Requirements Console]<br>
    C[Concept Model View]<br>
    D[Query Studio]<br>
    E[RAG Knowledge Mgmt]<br>
    F[Admin/Projects]<br>
  end<br>
<br>
  UI --> G[API Gateway]<br>
<br>
  subgraph S[Backend Services]<br>
    S1[Ingestion Service]<br>
    S2[Embedding Service]<br>
    S3[Extraction Service]<br>
    S4[Conceptualization Service]<br>
    S5[Ontology Service]<br>
    S6[Query Service]<br>
    S7[RAG Knowledge Service]<br>
    S8[Export/Report Service]<br>
  end<br>
<br>
  G --> S1<br>
  G --> S5<br>
  G --> S6<br>
  G --> S7<br>
  G --> S8<br>
  S1 --> S2 --> S3 --> S4 --> S5<br>
<br>
  subgraph Data[Data Layer]<br>
    R[(Fuseki RDF)]<br>
    N[(Neo4j)]<br>
    V[(Vector Store)]<br>
    O[(Object Storage)]<br>
    Q[(Queue)]<br>
  end<br>
<br>
  S5 --> R<br>
  S5 --> N<br>
  S2 --> V<br>
  S1 --> O<br>
  S1 --> Q<br>
  S3 --> Q<br>
  S4 --> Q<br>
<br>
  subgraph LLM[LLM Providers]<br>
    L1[OpenAI]<br>
    L2[Ollama]<br>
  end<br>
  S3 --> LLM<br>
  S4 --> LLM<br>
  S6 --> LLM<br>
```<br>
<br>
### 6.1 Services<br>
<br>
- **API Gateway**: Auth, rate limit, request routing; error normalization.<br>
- **Ingestion**: File upload, parsing, OCR; writes to object storage and metadata; enqueues chunking/embedding.<br>
- **Embedding**: Chunking; embeddings; vector upsert; metadata tagging/versioning.<br>
- **Extraction**: Requirement extraction; quality checks; linking to source; enqueue for review.<br>
- **Conceptualization**: Concept proposals, clustering, convergence; persistence to RDF; projection to Neo4j.<br>
- **Ontology**: CRUD ontology objects; SHACL validation; projection jobs to Neo4j.<br>
- **Query**: NL→SPARQL/Cypher; schema validation; safe execution; result caching.<br>
- **RAG Knowledge**: Managed knowledge sets; pipeline mirroring document ingestion; enablement per task/persona.<br>
- **Export/Report**: ReqIF/OSLC/CSV/JSON/TTL and PDF/DOCX generation; MBSE and BPMN export.<br>
<br>
## 7. Data Model<br>
<br>
### 7.1 Ontology (RDF canonical)<br>
<br>
- **Classes**: `Requirement`, `Constraint`, `Component`, `Interface`, `Function`, `Process`, `Condition`, `Stakeholder`, `SourceDocument`, `TestCase`, `Verification`, `RequirementSet`, `Rationale`, `Assumption`, `Risk`.<br>
- **Object properties**: `constrained_by`, `satisfied_by`, `verified_by`, `originates_from`, `derived_from`, `refines`, `has_interface`, `allocated_to`, `realizes`, `triggered_by`, `conflicts_with`, `duplicates`, `replaces`, `related_to`.<br>
- **Data/annotation**: `id`, `title`, `text`, `state`, `priority`, `risk_level`, `rationale`, `created_at`, `updated_at`, `version`, `provenance`.<br>
- **Validation**: SHACL shapes for each class; enforce required properties and value sets.<br>
<br>
### 7.2 Vector Store Schema<br>
<br>
- **Fields**: `embedding` (array<float>), `doc_id`, `chunk_id`, `chunk_idx`, `project_id`, `source`, `page_ref`, `section_ref`, `lang`, `embedding_model`, `parser_version`, `content_hash`, `version`, `created_at`.<br>
<br>
### 7.3 Neo4j Projection<br>
<br>
- **Projection**: Via n10s or ETL of selected classes/properties.<br>
- **Naming**: Labels mirror class names; relationships mirror object properties; include `iri` and `uuid` as identifiers.<br>
<br>
## 8. APIs (High-level)<br>
<br>
- **Auth**: OAuth2 or token-based; project scoping via headers.<br>
- **Content-type**: JSON; binary upload via multipart/form-data.<br>
<br>
### 8.1 Documents<br>
<br>
- `POST /api/projects/{pid}/documents` (multipart) → { `document_id`, metadata }<br>
- `GET /api/projects/{pid}/documents/{id}` → metadata + status<br>
- `POST /api/projects/{pid}/documents/{id}/reingest` → re-parse/version<br>
<br>
### 8.2 Requirements<br>
<br>
- `POST /api/projects/{pid}/requirements/extract` → starts extraction for a document/version<br>
- `GET /api/projects/{pid}/requirements` → list with states<br>
- `POST /api/projects/{pid}/requirements/{rid}/review` → { decision: approve|reject, comments }<br>
<br>
### 8.3 Ontology<br>
<br>
- CRUD for classes and properties; SHACL validation endpoint.<br>
- `POST /api/ontology/projection` → project canonical RDF to Neo4j.<br>
<br>
### 8.4 Conceptualization<br>
<br>
- `POST /api/projects/{pid}/concepts/propose` → generate candidate concepts<br>
- `GET /api/projects/{pid}/concepts` → list clusters, probabilities<br>
- `POST /api/projects/{pid}/concepts/{cid}/accept` → persist to RDF<br>
<br>
### 8.5 RAG Knowledge<br>
<br>
- `POST /api/projects/{pid}/knowledge` (multipart) → create knowledge set and ingest content<br>
- `GET /api/projects/{pid}/knowledge` → list sets and versions<br>
- `POST /api/projects/{pid}/knowledge/{kid}/enable` → enable for tasks/personas<br>
<br>
### 8.6 NL → Query<br>
<br>
- `POST /api/query/generate` { intent, modality: sparql|cypher, constraints } → { query, rationale }<br>
- `POST /api/query/execute` { query, modality } → { rows, stats } (read-only by default)<br>
<br>
### 8.7 Export<br>
<br>
- `POST /api/projects/{pid}/export` { format } → downloadable artifact<br>
<br>
## 9. LLM Output Contracts (JSON Schemas)<br>
<br>
### 9.1 Requirement Schema<br>
<br>
```json<br>
{<br>
  "$schema": "https://json-schema.org/draft/2020-12/schema",<br>
  "$id": "https://example.com/schemas/requirement.schema.json",<br>
  "type": "object",<br>
  "required": ["id", "text", "state", "originates_from"],<br>
  "properties": {<br>
    "id": {"type": "string"},<br>
    "text": {"type": "string"},<br>
    "state": {"enum": ["Draft", "Reviewed", "Approved"]},<br>
    "priority": {"type": "string"},<br>
    "risk_level": {"type": "string"},<br>
    "originates_from": {"type": "string"},<br>
    "constrained_by": {"type": "array", "items": {"type": "string"}},<br>
    "satisfied_by": {"type": "array", "items": {"type": "string"}},<br>
    "verified_by": {"type": "array", "items": {"type": "string"}}<br>
  }<br>
}<br>
```<br>
<br>
### 9.2 Concept Proposal Schema<br>
<br>
```json<br>
{<br>
  "$schema": "https://json-schema.org/draft/2020-12/schema",<br>
  "$id": "https://example.com/schemas/concept_proposal.schema.json",<br>
  "type": "object",<br>
  "required": ["concepts", "clusters"],<br>
  "properties": {<br>
    "concepts": {<br>
      "type": "array",<br>
      "items": {<br>
        "type": "object",<br>
        "required": ["id", "type", "label", "probability"],<br>
        "properties": {<br>
          "id": {"type": "string"},<br>
          "type": {"enum": ["Component", "Interface", "Process", "Function", "Condition"]},<br>
          "label": {"type": "string"},<br>
          "probability": {"type": "number", "minimum": 0, "maximum": 1}<br>
        }<br>
      }<br>
    },<br>
    "clusters": {<br>
      "type": "array",<br>
      "items": {<br>
        "type": "object",<br>
        "required": ["id", "members", "probability"],<br>
        "properties": {<br>
          "id": {"type": "string"},<br>
          "members": {"type": "array", "items": {"type": "string"}},<br>
          "probability": {"type": "number", "minimum": 0, "maximum": 1}<br>
        }<br>
      }<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
### 9.3 NL→Query Generation Schema<br>
<br>
```json<br>
{<br>
  "$schema": "https://json-schema.org/draft/2020-12/schema",<br>
  "$id": "https://example.com/schemas/query_generation.schema.json",<br>
  "type": "object",<br>
  "required": ["modality", "query", "explanations"],<br>
  "properties": {<br>
    "modality": {"enum": ["sparql", "cypher"]},<br>
    "query": {"type": "string"},<br>
    "explanations": {"type": "array", "items": {"type": "string"}},<br>
    "safety": {"type": "object", "properties": {"estimated_read_rows": {"type": "integer"}}}<br>
  }<br>
}<br>
```<br>
<br>
## 10. Pipelines and Jobs<br>
<br>
- **Queues**: Use a durable queue for long-running or retryable tasks (e.g., chunking, embeddings, extraction, conceptualization, projection, export).<br>
- **Idempotency**: Content-hash keys and version tags; safe re-runs.<br>
- **Backoff**: Exponential backoff on provider/API failures; circuit breakers for LLMs.<br>
- **Scheduling**: Cron for re-projection and evaluation runs.<br>
<br>
## 11. UI Specification<br>
<br>
- **Ontology Workbench**: React Flow graph and hierarchical tree; CRUD over ontology; SHACL validation feedback; URI/datatype management.<br>
- **Requirements Console**: Side-by-side source text with highlighted spans; quality warnings; review actions; trace link suggestions.<br>
- **Concept Model View**: Clusters with probabilities; merge/split; accept/reject; view traceability to requirements.<br>
- **Query Studio**: NL intent input → generated SPARQL/Cypher preview → run read-only; saved queries; result table and graph view.<br>
- **RAG Knowledge Management**: Upload a priori knowledge; show parsing/embedding status; validation report; enable/disable per task/persona; citation previews.<br>
- **Admin**: Projects, roles, audit log, prompt versions, model routing policies.<br>
<br>
## 12. LLM Team and Governance<br>
<br>
- **Providers**: OpenAI and Ollama via a routing layer; model capability registry per task.<br>
- **Prompt lifecycle**: Draft → Tested → Approved; store with versions and metrics; only Approved prompts in production.<br>
- **Contracts**: All constrained tasks must produce JSON validated against schemas in Section 9.<br>
- **Observability**: Prompt and output logging with PII redaction; per-task latency and cost budgets.<br>
<br>
## 13. Security and Compliance<br>
<br>
- **AuthZ**: RBAC at org/project levels; endpoint guards per role.<br>
- **Data**: Tenant isolation; encrypted at rest/in transit; content hashing; redaction on exports when configured.<br>
- **Audit**: Append-only logs for sensitive actions (approvals, ontology changes, query executes).<br>
<br>
## 14. Observability and QA<br>
<br>
- **Telemetry**: Structured logs, metrics, tracing; dashboards for extraction quality, approvals throughput, LLM latency/costs, vector recall.<br>
- **Evaluation**: Regression suites for extraction, NL→query, conceptualization; tracked over time.<br>
<br>
## 15. Versioning, Baselines, and IDs<br>
<br>
- **Versioning**: Documents, embeddings, requirements, ontology, concepts, prompts, and knowledge sets are versioned.<br>
- **Baselines**: Project-wide snapshots; immutable; diff support.<br>
- **IDs**: Human-friendly IDs + immutable UUIDs across stores.<br>
<br>
## 16. Deployment and Environments<br>
<br>
- **Dev (local)**: Docker compose; services for API, workers, Fuseki, Neo4j, vector store, object store, queue, UI.<br>
- **Dev helpers**: Use `./blueforce-start.sh` to manage the dev UI server and local LLM; UI on port 4000, Ollama on 11434; check status to avoid port hangs.<br>
- **Staging/Prod**: Containerized; externalized secrets; backups for RDF/Neo4j/vector/object stores; health probes and autoscaling.<br>
<br>
## 17. Performance Targets (SLOs)<br>
<br>
- **API availability**: 99.5% monthly.<br>
- **NL→Query latency**: p95 ≤ 2–4s depending on provider.<br>
- **Extraction throughput**: ≥ 10 documents/hour/worker (50–100 pages each), excluding OCR-heavy docs.<br>
<br>
## 18. Risks and Mitigations<br>
<br>
- **Model drift**: Regular evaluation with alerts; prompt and model version pinning.<br>
- **Hallucinations**: Strict schema validation; citations required for RAG-augmented outputs.<br>
- **Cost overrun**: Caching, budgets, and rate limiting; local model fallbacks for heavy tasks.<br>
- **Data leakage**: Redaction, PII scanning for RAG uploads, and tenant isolation enforcement.<br>
<br>
## 19. Roadmap<br>
<br>
- **Phase 1 (MVP)**: Ingestion, embeddings, extraction with review, RDF canonical store, basic ontology workbench, NL→SPARQL/Cypher preview, RAG knowledge upload, basic reports.<br>
- **Phase 2**: Probabilistic conceptualization with convergence, Neo4j projection, dashboards, export to ReqIF/OSLC and MBSE, BPMN→Camunda.<br>
- **Phase 3**: Semi-automatic ontology extraction by agent team; active learning loops.<br>
<br>
## 20. Appendices<br>
<br>
- **Example SPARQL (Requirements by State)**:<br>
<br>
```sparql<br>
PREFIX ex: <http://example.com/ontology/><br>
SELECT ?req ?title ?state WHERE {<br>
  ?req a ex:Requirement ;<br>
       ex:title ?title ;<br>
       ex:state ?state .<br>
}<br>
```<br>
<br>
- **Example Cypher (Concepts satisfied by Components)**:<br>
<br>
```cypher<br>
MATCH (r:Requirement)-[:SATISFIED_BY]->(c:Component)<br>
RETURN r.id, c.id<br>
LIMIT 50<br>
```<br>
<br>
- **SHACL Sketch (Requirement)**:<br>
<br>
```turtle<br>
@prefix sh: <http://www.w3.org/ns/shacl#> .<br>
@prefix ex: <http://example.com/ontology/> .<br>
<br>
ex:RequirementShape a sh:NodeShape ;<br>
  sh:targetClass ex:Requirement ;<br>
  sh:property [ sh:path ex:title ; sh:minCount 1 ; sh:datatype xsd:string ] ;<br>
  sh:property [ sh:path ex:state ; sh:minCount 1 ; sh:in ("Draft" "Reviewed" "Approved") ] .<br>
```<br>

