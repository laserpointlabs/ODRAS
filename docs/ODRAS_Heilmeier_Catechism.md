## ODRAS: Heilmeier Catechism

This document presents the Heilmeier answers for the Ontology‑Driven Requirements and Architecture System (ODRAS) MVP. It is grounded in the implementation plan described in `ontology_workbench_mvp.md` and complementary docs in `docs/`.

### 1) What are you trying to do?

Build a web workbench that turns unstructured program documents into a shared, computable project model using ontologies, then keeps that model actionable across RDF/SPARQL and a property graph.

Key outcomes for the MVP:
- Visual, direct‑manipulation ontology editing backed by Fuseki named graphs; layout stored separately from triples.
- Project‑scoped RAG (retrieval‑augmented generation) to review requirements with citations.
- Single‑pass conceptualization that grounds LLM suggestions in the active ontology, creating typed individuals and relations with confidences.
- Dual persistence: RDF in Fuseki, plus a Neo4j mirror for interactive graph operations.
- Lightweight BPMN hooks to integrate steps such as review and conceptualization.

### 2) How is it done today and what are the limits?

Current practice combines siloed tools: requirements managers, modeling tools, spreadsheets, ad‑hoc scripts and un‑grounded LLM outputs. Ontologies are rarely first‑class in daily workflows and cross‑tool traceability is weak.

Limits we address:
- Inconsistent semantics across teams; weak linkage from requirements to a computable model.
- Slow, manual concept modeling; fragile handoffs between RDF ecosystems and graph applications.
- LLM outputs without schema grounding, leading to hallucinations and poor auditability.

### 3) What’s new and why will it succeed?

What’s new:
- Direct‑manipulation ontology editor with strict separation of layout JSON from RDF triples.
- Schema‑grounded, single‑pass conceptualization loop that produces typed individuals/relations linked to requirements with confidence scores and citations.
- Dual‑store strategy (Fuseki + Neo4j mirror) for both semantics (RDF) and performance/UX (property graph).
- Project‑scoped RAG with explicit document metadata and citations in prompts.
- Process hooks (BPMN/Camunda) and a status bar for live service checks.

Why now:
- Mature open tooling (FastAPI, Fuseki, Neo4j, Cytoscape) and reliable vector stores.
- LLMs are now strong enough for assisted extraction when strictly schema‑constrained and reviewer‑gated.

### 4) Who cares? What difference will it make?

Stakeholders: systems engineers, digital engineering teams, architects, program managers and knowledge managers.

Impact:
- Faster path from documents to a computable, shared model with consistent semantics.
- Auditable traceability from requirement → individual → relationship → artifact.
- Smoother integration with downstream analytics, query, and decision support across RDF and property‑graph tooling.

### 5) What are the risks and how will you mitigate them?

- LLM grounding/hallucination: schema‑constrained prompts, RAG with citations, reviewer‑in‑the‑loop, confidence scoring.
- Ontology/UI complexity: MVP limits to a single base ontology; imports as read‑only overlays later; strict separation of layout vs triples.
- Data integrity/versioning: full graph replacement for MVP; plan diff/versioning next; optional SHACL validation later.
- Performance/scale: acceptance checks at ~500+ elements; Neo4j mirror for responsive views; idempotent upserts by IRI.
- Integration fragility: narrow, documented API contracts; health checks; fallbacks for graph‑store writes.

### 6) How much will it cost and how long will it take?

Schedule (MVP): ~10–14 weeks.
- Weeks 1–4: Ontology Workbench load/save, layout persistence, inline editing.
- Weeks 5–8: Files + Embedding Workbenches; Requirements review with RAG.
- Weeks 9–12: Conceptualization loop and Neo4j mirror; acceptance tests; BPMN hooks and status bar.

Team: 2–3 full‑stack engineers plus 0.25–0.5 PM/SME.

Budget range: $180k–$320k all‑in (team rates and infra dependent). Infra includes Fuseki, Neo4j and a vector store; cloud costs are modest for MVP.

### 7) What are the midterm and final “exams”?

Midterm (Ontology Workbench):
- Load/render from a named graph; edit classes/properties; inline rename; round‑trip save is lossless.
- Layout persists per graph IRI; auto‑layout fallback; keyboard shortcuts and basic undo/redo.

Midterm (RAG + Requirements):
- Import docs; embed with metadata; retrieve cited context; reviewer approves structured requirements.

Final (Conceptualization + Mirror + Process):
- Single‑pass conceptualization creates individuals/relations with confidences linked to requirements; idempotent upsert by IRI.
- Neo4j mirror remains consistent with RDF; project‑scoped APIs pass contract tests.
- BPMN hooks emit start/complete events; status bar shows live service checks.

### 8) How will you measure success (quantitative)?

- ≥50% reduction in time from document import to first concept model (baseline vs MVP runs).
- ≥90% reviewer acceptance for schema‑valid LLM suggestions on benchmark sets.
- RDF round‑trip fidelity: 100% on test ontologies up to ~1k elements.
- Save/load latency: <3s for ~1k elements; mirror sync <5s.
- RAG citation accuracy: ≥95% of cited chunks resolve to correct sources.

### 9) What are the deliverables?

- Running web app with the MVP workbenches: Ontology, Files, Embedding, Requirements, GraphDB and Process.
- API docs for `GET/PUT /ontology?graph=<iri>`, `GET/PUT /layout?graph=<iri>`, ontology discovery and conceptualization.
- Example project with sample ontologies and automated tests; acceptance checklist implemented.
- Minimal deployment guide and service health checks.

### 10) If it works, what’s next?

- Read‑only imports overlay; diff/versioning; SHACL validation.
- Multi‑pass conceptualization with SME feedback loops and governance.
- Deeper BPMN orchestration; project thread and artifact generation from curated interactions.

### References

- Implementation plan: `ontology_workbench_mvp.md`
- UI restart checklist: `todo-refresh.md`
- Backend/API overview: `backend/main.py`


