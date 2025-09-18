## ODRAS: Heilmeier Catechism<br>
<br>
This document presents the Heilmeier answers for the Ontology‑Driven Requirements and Architecture System (ODRAS) MVP. It is grounded in the implementation plan described in `ontology_workbench_mvp.md` and complementary docs in `docs/`.<br>
<br>
### 1) What are you trying to do?<br>
<br>
Build a web workbench that turns unstructured program documents into a shared, computable project model using ontologies, then keeps that model actionable across RDF/SPARQL and a property graph.<br>
<br>
Key outcomes for the MVP:<br>
- Visual, direct‑manipulation ontology editing backed by Fuseki named graphs; layout stored separately from triples.<br>
- Project‑scoped RAG (retrieval‑augmented generation) to review requirements with citations.<br>
- Single‑pass conceptualization that grounds LLM suggestions in the active ontology, creating typed individuals and relations with confidences.<br>
- Dual persistence: RDF in Fuseki, plus a Neo4j mirror for interactive graph operations.<br>
- Lightweight BPMN hooks to integrate steps such as review and conceptualization.<br>
<br>
### 2) How is it done today and what are the limits?<br>
<br>
Current practice combines siloed tools: requirements managers, modeling tools, spreadsheets, ad‑hoc scripts and un‑grounded LLM outputs. Ontologies are rarely first‑class in daily workflows and cross‑tool traceability is weak.<br>
<br>
Limits we address:<br>
- Inconsistent semantics across teams; weak linkage from requirements to a computable model.<br>
- Slow, manual concept modeling; fragile handoffs between RDF ecosystems and graph applications.<br>
- LLM outputs without schema grounding, leading to hallucinations and poor auditability.<br>
<br>
### 3) What’s new and why will it succeed?<br>
<br>
What’s new:<br>
- Direct‑manipulation ontology editor with strict separation of layout JSON from RDF triples.<br>
- Schema‑grounded, single‑pass conceptualization loop that produces typed individuals/relations linked to requirements with confidence scores and citations.<br>
- Dual‑store strategy (Fuseki + Neo4j mirror) for both semantics (RDF) and performance/UX (property graph).<br>
- Project‑scoped RAG with explicit document metadata and citations in prompts.<br>
- Process hooks (BPMN/Camunda) and a status bar for live service checks.<br>
<br>
Why now:<br>
- Mature open tooling (FastAPI, Fuseki, Neo4j, Cytoscape) and reliable vector stores.<br>
- LLMs are now strong enough for assisted extraction when strictly schema‑constrained and reviewer‑gated.<br>
<br>
### 4) Who cares? What difference will it make?<br>
<br>
Stakeholders: systems engineers, digital engineering teams, architects, program managers and knowledge managers.<br>
<br>
Impact:<br>
- Faster path from documents to a computable, shared model with consistent semantics.<br>
- Auditable traceability from requirement → individual → relationship → artifact.<br>
- Smoother integration with downstream analytics, query, and decision support across RDF and property‑graph tooling.<br>
<br>
### 5) What are the risks and how will you mitigate them?<br>
<br>
- LLM grounding/hallucination: schema‑constrained prompts, RAG with citations, reviewer‑in‑the‑loop, confidence scoring.<br>
- Ontology/UI complexity: MVP limits to a single base ontology; imports as read‑only overlays later; strict separation of layout vs triples.<br>
- Data integrity/versioning: full graph replacement for MVP; plan diff/versioning next; optional SHACL validation later.<br>
- Performance/scale: acceptance checks at ~500+ elements; Neo4j mirror for responsive views; idempotent upserts by IRI.<br>
- Integration fragility: narrow, documented API contracts; health checks; fallbacks for graph‑store writes.<br>
<br>
### 6) How much will it cost and how long will it take?<br>
<br>
Schedule (MVP): ~10–14 weeks.<br>
- Weeks 1–4: Ontology Workbench load/save, layout persistence, inline editing.<br>
- Weeks 5–8: Files + Embedding Workbenches; Requirements review with RAG.<br>
- Weeks 9–12: Conceptualization loop and Neo4j mirror; acceptance tests; BPMN hooks and status bar.<br>
<br>
Team: 2–3 full‑stack engineers plus 0.25–0.5 PM/SME.<br>
<br>
Budget range: $180k–$320k all‑in (team rates and infra dependent). Infra includes Fuseki, Neo4j and a vector store; cloud costs are modest for MVP.<br>
<br>
### 7) What are the midterm and final “exams”?<br>
<br>
Midterm (Ontology Workbench):<br>
- Load/render from a named graph; edit classes/properties; inline rename; round‑trip save is lossless.<br>
- Layout persists per graph IRI; auto‑layout fallback; keyboard shortcuts and basic undo/redo.<br>
<br>
Midterm (RAG + Requirements):<br>
- Import docs; embed with metadata; retrieve cited context; reviewer approves structured requirements.<br>
<br>
Final (Conceptualization + Mirror + Process):<br>
- Single‑pass conceptualization creates individuals/relations with confidences linked to requirements; idempotent upsert by IRI.<br>
- Neo4j mirror remains consistent with RDF; project‑scoped APIs pass contract tests.<br>
- BPMN hooks emit start/complete events; status bar shows live service checks.<br>
<br>
### 8) How will you measure success (quantitative)?<br>
<br>
- ≥50% reduction in time from document import to first concept model (baseline vs MVP runs).<br>
- ≥90% reviewer acceptance for schema‑valid LLM suggestions on benchmark sets.<br>
- RDF round‑trip fidelity: 100% on test ontologies up to ~1k elements.<br>
- Save/load latency: <3s for ~1k elements; mirror sync <5s.<br>
- RAG citation accuracy: ≥95% of cited chunks resolve to correct sources.<br>
<br>
### 9) What are the deliverables?<br>
<br>
- Running web app with the MVP workbenches: Ontology, Files, Embedding, Requirements, GraphDB and Process.<br>
- API docs for `GET/PUT /ontology?graph=<iri>`, `GET/PUT /layout?graph=<iri>`, ontology discovery and conceptualization.<br>
- Example project with sample ontologies and automated tests; acceptance checklist implemented.<br>
- Minimal deployment guide and service health checks.<br>
<br>
### 10) If it works, what’s next?<br>
<br>
- Read‑only imports overlay; diff/versioning; SHACL validation.<br>
- Multi‑pass conceptualization with SME feedback loops and governance.<br>
- Deeper BPMN orchestration; project thread and artifact generation from curated interactions.<br>
<br>
### References<br>
<br>
- Implementation plan: `ontology_workbench_mvp.md`<br>
- UI restart checklist: `todo-refresh.md`<br>
- Backend/API overview: `backend/main.py`<br>
<br>
<br>

