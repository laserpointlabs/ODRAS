# ODRAS MVP TODO

- [ ] BPMN execution: wire `bpmn/odras_mvp.bpmn` into runtime by mapping service tasks to Python callables via SpiffWorkflow.
- [ ] Ingestion: Add real PDF/DOCX parsing with metadata anchors; store SourceDocument nodes.
- [ ] Embeddings: Replace hasher with sentence-transformers; add model/version metadata in Qdrant payloads.
- [ ] LLM Team: Add prompt templates, schema validation/correction loop, and persona weighting.
- [ ] Persistence: Strengthen Neo4j schema with labels (Requirement, Entity) and relations; add constraints and indexes.
- [ ] RDF: Use prefixes and named graphs per run; add SHACL shapes; proper SPARQL Update.
- [ ] API: Endpoints to list runs, fetch results, download RDF/CSV; simple impact/traceability queries.
- [ ] UI: Runs list, results viewer, charts for sensitivities and entity counts.
- [ ] Security/RBAC: Token auth, project scoping.
- [ ] Tests/CI: Unit tests for extractors, LLM adapters (mocked), and persistence; docker health checks.
- [ ] DADMS integration: Import BPMN patterns and connect to `/home/jdehart/dadms` workflows, align service contracts.



