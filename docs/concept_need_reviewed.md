## Concept Needs — Reviewed Specification (v0.1)<br>
<br>
This document refines the original concept needs by addressing identified gaps and aligning ontology semantics, data governance, and workflows for an implementable system.<br>
<br>
## Scope and Outcomes<br>
<br>
- **Goal**: Ingest documents → extract requirements → conceptualize system elements → persist in RDF and projected Neo4j graphs → enable UI-driven curation, analysis, and reporting with governed LLM assistance.<br>
- **Users**: Requirements engineers, system architects, SMEs, data governors.<br>
<br>
## Data Stores and Canonical Source<br>
<br>
- **Canonical**: RDF (Apache Jena/Fuseki) is the source of truth for ontology, requirements, and conceptual models.<br>
- **Projection**: Neo4j is a derived, query-optimized projection. Use neosemantics (n10s) or a defined ETL to project selected classes/relations.<br>
- **Sync policy**:<br>
  - One-way from RDF → Neo4j by default.<br>
  - Changes in Neo4j are read-only for users; write paths go to RDF then re-project.<br>
  - Include a replayable ETL job and change audit trail.<br>
<br>
## Base Ontology v0.1<br>
<br>
- **Classes**: `Requirement`, `Constraint`, `Component`, `Interface`, `Function`, `Process`, `Condition`, `Stakeholder`, `SourceDocument`, `TestCase`, `Verification`, `RequirementSet`, `Rationale`, `Assumption`, `Risk`.<br>
- **Object properties**:<br>
  - `Requirement → constrained_by → Constraint`<br>
  - `Requirement → satisfied_by → {Component | Function | Process}`<br>
  - `Requirement → verified_by → TestCase`<br>
  - `Requirement → originates_from → SourceDocument`<br>
  - `Requirement → derived_from → Requirement` and `Requirement → refines → Requirement`<br>
  - `Component → has_interface → Interface`<br>
  - `Function → allocated_to → {Component | Process}`<br>
  - `Process → realizes → Function` (keep this direction consistently)<br>
  - `Function → triggered_by → Condition`<br>
  - Trace semantics: `conflicts_with`, `duplicates`, `replaces`, `related_to`<br>
- **Data/annotation properties**: `id`, `title`, `text`, `state` (Draft/Reviewed/Approved), `priority`, `risk_level`, `rationale`, `created_at`, `updated_at`, `version`, `provenance`.<br>
<br>
## Pipelines<br>
<br>
### Document Ingestion<br>
<br>
- **File types**: PDF, DOCX, Markdown, TXT; OCR for scanned PDFs; language detection.<br>
- **Structure extraction**: Headings, tables, figures, references; maintain page/section anchors in metadata.<br>
- **Metadata**: `project_id`, `source_uri`, `mime_type`, `hash`, `ingested_at`, `parser_version`.<br>
<br>
### Chunking and Embeddings<br>
<br>
- **Chunking**: Sliding window with overlap; configurable `chunk_size` (e.g., 800–1,200 tokens) and `chunk_overlap` (e.g., 10–20%).<br>
- **Vector store**: Pluggable (pgvector/Milvus/Qdrant). Store `embedding_model`, `dim`, `doc_id`, `chunk_idx`, `page_ref`, `lang`, `version`.<br>
- **Re-embedding policy**: On parser/model change or content change; keep historical versions for reproducibility.<br>
<br>
### Requirement Extraction<br>
<br>
- **Patterns**: Detect “shall/should/will/must”, modal verbs, passive voice, and domain patterns; support multi-sentence scope.<br>
- **Quality checks**: Ambiguity, testability, atomicity, duplicates; propose edits and rationale.<br>
- **Evaluation**: Precision/recall targets per domain; maintain labeled sets per project; regular regression runs.<br>
- **Workflow**: Extracted → Draft → Reviewed (SME) → Approved; track reviewer, comments, diffs.<br>
- **Linking**: `Requirement.originates_from → SourceDocument` with offsets and citations; auto-suggest `constrained_by`, `satisfied_by` candidates.<br>
<br>
### Conceptualization (Probabilistic)<br>
<br>
- **Goal**: Estimate Components/Interfaces, Processes, Functions, Conditions from approved requirements.<br>
- **Clustering**: Similarity over requirement embeddings and extracted concepts; synonym squashing (e.g., airplane/aircraft/air-vehicle).<br>
- **Convergence criteria**: Stability across resamples, silhouette score, entropy reduction; stop when metrics plateau or thresholds met.<br>
- **Outputs**: Candidate concepts with probabilities; alternative clustered conceptual systems (e.g., 80% configuration A, 20% B).<br>
- **Persistence**: Store conceptual models in RDF; project to Neo4j for visualization.<br>
<br>
## LLM Team, Models, and Governance<br>
<br>
- **Providers**: OpenAI (remote) and Ollama (local) behind a routing layer.<br>
- **Routing**: Task-aware selection, cost/latency budgets, retries, rate limiting, caching, and fallbacks.<br>
- **Output contracts**: For constrained tasks, responses must be JSON validated against per-task JSON Schemas (requirement, concept, query).<br>
- **Prompt governance**: Only tested prompts may be used in production. Maintain prompt versions, evaluation results, and approvals.<br>
<br>
## Natural Language → Query (SPARQL/Cypher)<br>
<br>
- **Schema-aware generation**: Grounded on RDF/Neo4j schema; auto-include prefixes and label/property constraints.<br>
- **Safety**: Read-only by default; preview query + estimated impact; user approval required to execute.<br>
- **Recovery**: On errors, propose fixes; include explanations and sample results.<br>
- **Testing**: Example-based unit tests for common intents.<br>
<br>
## UI<br>
<br>
- **Ontology Workbench**: React Flow graph + hierarchical tree for classes/properties; CRUD over Classes, Object/Data/Annotation properties; manage URIs and datatypes.<br>
- **Requirements Console**: Review/approve workflow with diffs, comments, and quality checks; trace links visualization.<br>
- **Concept Model View**: Clustered alternatives with probabilities; merge/split concepts; link to requirements.<br>
- **Query Studio**: NL → SPARQL/Cypher preview → execute read-only; saved queries per project.<br>
- **Reports**: Requirements and conceptualization reports with citations and export options.<br>
- **SME Co-editing**: LLM-assisted edits with explicit acceptance.<br>
- **Project/User Management**: RBAC roles and audit trail.<br>
- **RAG Knowledge Management (new)**:<br>
  - Upload a priori knowledge documents (e.g., requirement-writing techniques, domain guides) to create managed RAG knowledge sets.<br>
  - Supported formats: PDF/DOCX/MD/TXT; per-project or global scope; versioned with provenance.<br>
  - UI flows: Upload → parse → chunk/embed → validation report → enable/disable per task/persona.<br>
  - Link knowledge sets to extraction and conceptualization tasks; show citations for any retrieved context.<br>
  - Governance: Review/approve knowledge sets; redaction and PII scanning before activation.<br>
<br>
## Security and Tenancy<br>
<br>
- **RBAC**: Roles (Admin, Architect, SME, Viewer) at org/project level.<br>
- **Multi-tenancy**: Project isolation; per-tenant keys and storage; data residency options.<br>
- **Audit**: Immutable logs for changes, approvals, and query executions.<br>
- **Secrets**: Managed via vault; no secrets in source control.<br>
<br>
## Observability and QA<br>
<br>
- **Telemetry**: Structured logs, metrics, tracing; prompt/output logs with redaction.<br>
- **Eval harness**: Periodic regression for extractors, NL→query, and conceptualization; track scores over time.<br>
- **Dashboards**: Extraction quality, approval throughput, LLM costs/latency, vector recall.<br>
<br>
## Versioning, Baselines, and IDs<br>
<br>
- **Versioning**: Requirements, ontology, conceptual models, documents, embeddings, prompts, and knowledge sets are versioned.<br>
- **Baselines**: Project-level snapshots for releases; diff across baselines.<br>
- **IDs**: Stable human-friendly IDs plus immutable UUIDs for cross-store linking.<br>
<br>
## Export and Interoperability<br>
<br>
- **Formats**: ReqIF/OSLC, CSV/JSON/TTL, PDF/DOCX reports.<br>
- **MBSE**: Teamwork Cloud mapping (IDs, stereotypes) for SysML concept definitions.<br>
- **Process**: BPMN models exportable to Camunda runtime where applicable.<br>
<br>
## Implementation Notes<br>
<br>
- Prefer RDF-first modeling; keep Neo4j synchronized via controlled projection.<br>
- Provide JSON Schemas for all LLM-constrained outputs and validate server-side.<br>
- Ensure read-only defaults for generated queries; require explicit opt-in for any write operation.<br>
<br>
<br>

