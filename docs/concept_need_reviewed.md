## Concept Needs — Reviewed Specification (v0.1)

This document refines the original concept needs by addressing identified gaps and aligning ontology semantics, data governance, and workflows for an implementable system.

## Scope and Outcomes

- **Goal**: Ingest documents → extract requirements → conceptualize system elements → persist in RDF and projected Neo4j graphs → enable UI-driven curation, analysis, and reporting with governed LLM assistance.
- **Users**: Requirements engineers, system architects, SMEs, data governors.

## Data Stores and Canonical Source

- **Canonical**: RDF (Apache Jena/Fuseki) is the source of truth for ontology, requirements, and conceptual models.
- **Projection**: Neo4j is a derived, query-optimized projection. Use neosemantics (n10s) or a defined ETL to project selected classes/relations.
- **Sync policy**:
  - One-way from RDF → Neo4j by default.
  - Changes in Neo4j are read-only for users; write paths go to RDF then re-project.
  - Include a replayable ETL job and change audit trail.

## Base Ontology v0.1

- **Classes**: `Requirement`, `Constraint`, `Component`, `Interface`, `Function`, `Process`, `Condition`, `Stakeholder`, `SourceDocument`, `TestCase`, `Verification`, `RequirementSet`, `Rationale`, `Assumption`, `Risk`.
- **Object properties**:
  - `Requirement → constrained_by → Constraint`
  - `Requirement → satisfied_by → {Component | Function | Process}`
  - `Requirement → verified_by → TestCase`
  - `Requirement → originates_from → SourceDocument`
  - `Requirement → derived_from → Requirement` and `Requirement → refines → Requirement`
  - `Component → has_interface → Interface`
  - `Function → allocated_to → {Component | Process}`
  - `Process → realizes → Function` (keep this direction consistently)
  - `Function → triggered_by → Condition`
  - Trace semantics: `conflicts_with`, `duplicates`, `replaces`, `related_to`
- **Data/annotation properties**: `id`, `title`, `text`, `state` (Draft/Reviewed/Approved), `priority`, `risk_level`, `rationale`, `created_at`, `updated_at`, `version`, `provenance`.

## Pipelines

### Document Ingestion

- **File types**: PDF, DOCX, Markdown, TXT; OCR for scanned PDFs; language detection.
- **Structure extraction**: Headings, tables, figures, references; maintain page/section anchors in metadata.
- **Metadata**: `project_id`, `source_uri`, `mime_type`, `hash`, `ingested_at`, `parser_version`.

### Chunking and Embeddings

- **Chunking**: Sliding window with overlap; configurable `chunk_size` (e.g., 800–1,200 tokens) and `chunk_overlap` (e.g., 10–20%).
- **Vector store**: Pluggable (pgvector/Milvus/Qdrant). Store `embedding_model`, `dim`, `doc_id`, `chunk_idx`, `page_ref`, `lang`, `version`.
- **Re-embedding policy**: On parser/model change or content change; keep historical versions for reproducibility.

### Requirement Extraction

- **Patterns**: Detect “shall/should/will/must”, modal verbs, passive voice, and domain patterns; support multi-sentence scope.
- **Quality checks**: Ambiguity, testability, atomicity, duplicates; propose edits and rationale.
- **Evaluation**: Precision/recall targets per domain; maintain labeled sets per project; regular regression runs.
- **Workflow**: Extracted → Draft → Reviewed (SME) → Approved; track reviewer, comments, diffs.
- **Linking**: `Requirement.originates_from → SourceDocument` with offsets and citations; auto-suggest `constrained_by`, `satisfied_by` candidates.

### Conceptualization (Probabilistic)

- **Goal**: Estimate Components/Interfaces, Processes, Functions, Conditions from approved requirements.
- **Clustering**: Similarity over requirement embeddings and extracted concepts; synonym squashing (e.g., airplane/aircraft/air-vehicle).
- **Convergence criteria**: Stability across resamples, silhouette score, entropy reduction; stop when metrics plateau or thresholds met.
- **Outputs**: Candidate concepts with probabilities; alternative clustered conceptual systems (e.g., 80% configuration A, 20% B).
- **Persistence**: Store conceptual models in RDF; project to Neo4j for visualization.

## LLM Team, Models, and Governance

- **Providers**: OpenAI (remote) and Ollama (local) behind a routing layer.
- **Routing**: Task-aware selection, cost/latency budgets, retries, rate limiting, caching, and fallbacks.
- **Output contracts**: For constrained tasks, responses must be JSON validated against per-task JSON Schemas (requirement, concept, query).
- **Prompt governance**: Only tested prompts may be used in production. Maintain prompt versions, evaluation results, and approvals.

## Natural Language → Query (SPARQL/Cypher)

- **Schema-aware generation**: Grounded on RDF/Neo4j schema; auto-include prefixes and label/property constraints.
- **Safety**: Read-only by default; preview query + estimated impact; user approval required to execute.
- **Recovery**: On errors, propose fixes; include explanations and sample results.
- **Testing**: Example-based unit tests for common intents.

## UI

- **Ontology Workbench**: React Flow graph + hierarchical tree for classes/properties; CRUD over Classes, Object/Data/Annotation properties; manage URIs and datatypes.
- **Requirements Console**: Review/approve workflow with diffs, comments, and quality checks; trace links visualization.
- **Concept Model View**: Clustered alternatives with probabilities; merge/split concepts; link to requirements.
- **Query Studio**: NL → SPARQL/Cypher preview → execute read-only; saved queries per project.
- **Reports**: Requirements and conceptualization reports with citations and export options.
- **SME Co-editing**: LLM-assisted edits with explicit acceptance.
- **Project/User Management**: RBAC roles and audit trail.
- **RAG Knowledge Management (new)**:
  - Upload a priori knowledge documents (e.g., requirement-writing techniques, domain guides) to create managed RAG knowledge sets.
  - Supported formats: PDF/DOCX/MD/TXT; per-project or global scope; versioned with provenance.
  - UI flows: Upload → parse → chunk/embed → validation report → enable/disable per task/persona.
  - Link knowledge sets to extraction and conceptualization tasks; show citations for any retrieved context.
  - Governance: Review/approve knowledge sets; redaction and PII scanning before activation.

## Security and Tenancy

- **RBAC**: Roles (Admin, Architect, SME, Viewer) at org/project level.
- **Multi-tenancy**: Project isolation; per-tenant keys and storage; data residency options.
- **Audit**: Immutable logs for changes, approvals, and query executions.
- **Secrets**: Managed via vault; no secrets in source control.

## Observability and QA

- **Telemetry**: Structured logs, metrics, tracing; prompt/output logs with redaction.
- **Eval harness**: Periodic regression for extractors, NL→query, and conceptualization; track scores over time.
- **Dashboards**: Extraction quality, approval throughput, LLM costs/latency, vector recall.

## Versioning, Baselines, and IDs

- **Versioning**: Requirements, ontology, conceptual models, documents, embeddings, prompts, and knowledge sets are versioned.
- **Baselines**: Project-level snapshots for releases; diff across baselines.
- **IDs**: Stable human-friendly IDs plus immutable UUIDs for cross-store linking.

## Export and Interoperability

- **Formats**: ReqIF/OSLC, CSV/JSON/TTL, PDF/DOCX reports.
- **MBSE**: Teamwork Cloud mapping (IDs, stereotypes) for SysML concept definitions.
- **Process**: BPMN models exportable to Camunda runtime where applicable.

## Implementation Notes

- Prefer RDF-first modeling; keep Neo4j synchronized via controlled projection.
- Provide JSON Schemas for all LLM-constrained outputs and validate server-side.
- Ensure read-only defaults for generated queries; require explicit opt-in for any write operation.


