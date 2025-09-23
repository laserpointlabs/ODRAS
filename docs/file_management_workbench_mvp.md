# File Management Workbench MVP<br>
<br>
> ⚠️ **DOCUMENT STATUS**: This document is being replaced by [`file_management_status_2024.md`](./file_management_status_2024.md) which reflects the actual current implementation as of December 2024.<br>
<br>
## 🎉 **Phase 1 COMPLETE** - File Management Foundation<br>
<br>
**The ODRAS File Management Workbench Phase 1 is fully implemented and production-ready!**<br>
<br>
### ✅ What's Working<br>
- Project-scoped file upload, library, preview, and deletion<br>
- Admin-controlled public/private file visibility system<br>
- Advanced file preview (Markdown, Text, PDF, CSV) with fullscreen<br>
- Configurable processing parameters and embedding model selection<br>
- Multi-backend storage with unified API<br>
- Role-based authentication with admin controls<br>
<br>
**See [`file_management_status_2024.md`](./file_management_status_2024.md) for complete implementation details.**<br>
<br>
---<br>
<br>
## Original MVP Planning Document (Historical)<br>
<br>
## Goals and scope (MVP)<br>
- Manage project-scoped files: upload, import, list, preview, organize.<br>
- BPMN-orchestrated pipelines for ingestion, chunking, embedding, indexing, and extraction.<br>
- Requirements extraction and Knowledge documents preparation as explicit workflows.<br>
- Integrate with LLM Playground by exposing curated, searchable context sets (Requirements and Knowledge) and actions.<br>
- Provide visibility into workflow runs (status, logs, artifacts) with ability to re-run.<br>
<br>
## Principles<br>
- BPMN-first orchestration for all RAG steps; workers are stateless services.<br>
- Idempotent operations and deterministic inputs (content hashing, metadata versioning).<br>
- Separation of concerns: raw file storage vs. derived data (chunks/embeddings/extractions).<br>
- Traceability: every artifact carries lineage to the file version and workflow run.<br>
<br>
## High-level architecture<br>
```mermaid<br>
graph TD<br>
  U["User"] --> UI["Browser: File Management Workbench\n(Library | Details | Workflows)"]<br>
  UI --> API["API Server"]<br>
  API --> BPMN["BPMN Engine\n(Process runtime)"]<br>
  BPMN --> W1["Workers: Parse/Chunk/OCR"]<br>
  BPMN --> W2["Workers: Embed/Index"]<br>
  BPMN --> W3["Workers: Requirements Extraction"]<br>
  BPMN --> W4["Workers: Knowledge Enrichment"]<br>
  API --> OS["Object Store\n(Files)"]<br>
  API --> DB["Metadata DB\n(files, runs, extractions)"]<br>
  API --> VS["Vector Store\n(chunks/embeddings)"]<br>
  UI --> PLY["LLM Playground\n(context selectors)"]<br>
```<br>
<br>
## Current implementation snapshot (now)<br>
- Backend<br>
  - Implemented file API under `/api/files`:<br>
    - POST `/api/files/upload` (auth + project membership, supports `tags` JSON)<br>
    - POST `/api/files/batch/upload` (bulk upload; project-scoped; no per-file tags yet)<br>
    - GET `/api/files` (returns metadata list; optional `project_id` filter)<br>
    - GET `/api/files/{file_id}/download` and GET `/api/files/{file_id}/url`<br>
    - DELETE `/api/files/{file_id}`<br>
    - POST `/api/files/{file_id}/process` (starts Camunda requirements analysis on stored file)<br>
    - GET/PUT `/api/files/keywords` and POST `/api/files/extract/keywords` (keyword-based quick extraction to RDF)<br>
  - Storage backends available via `Settings.storage_backend`: `local`, `minio`, `postgresql` (with metadata JSON persisted for `local`/`minio`).<br>
  - Camunda integration is wired (see `/api/upload`, `/api/files/{id}/process`, status/user-task routes). BPMN deployment auto-handled from `bpmn/odras_requirements_analysis.bpmn` if needed.<br>
- Frontend<br>
  - Files Workbench exists in `frontend/app.html` (`#wb-files`) with UI for: doc type, status, tags, drag-drop, staged list, and a library panel. Current actions are placeholder-only for Upload/Refresh; library list is not yet wired to the backend in this UI.<br>
  - A separate minimal page (root index) contains a Files tab already calling `/api/files` and `/api/files/batch/upload` (useful as reference while wiring the new UI).<br>
- Auth and project context<br>
  - Auth token stored as `odras_token`; active project id persisted as `active_project_id`. Upload API enforces membership; list/download/delete currently do not enforce auth in MVP.<br>
<br>
<br>
## Data model (MVP)<br>
- Project: id, name, settings.<br>
- File: id, projectId, name, bytesHash, mimeType, size, storageKey, createdAt, tags[].<br>
- FileVersion: fileId, version, bytesHash, ocrApplied?, textExtracted?, createdAt.<br>
- IngestionRun: id, projectId, fileId(s), processKey, status, startedAt, finishedAt, logsRef.<br>
- Chunk: id, fileId/version, order, text, tokenCount, section/page metadata.<br>
- Embedding: chunkId, vector, modelId, createdAt.<br>
- Requirement: id, projectId, sourceFileId/version, text, citations[], confidence.<br>
- KnowledgeItem: id, projectId, sourceFileId/version, text/snippet, citations[], tags[].<br>
<br>
## BPMN processes (no hard-coded pipelines)<br>
- ingestion_pipeline<br>
  - Detect type → optional OCR → parse → normalize → chunk → embed → upsert vector store → persist metadata → complete.<br>
- requirements_extraction<br>
  - Select doc set → retrieve relevant chunks → LLM extract requirements → persist items with citations → summary.<br>
- knowledge_enrichment<br>
  - Select doc set → retrieve → LLM synthesize knowledge items (with attributions) → persist → summary.<br>
- rag_playground_session (ephemeral)<br>
  - Given selected context sets → retrieval → LLM response → optional actions (save snippet, link, create requirement).<br>
<br>
Represent process definitions as BPMN (XML) files under `bpmn/` and reference them by `processKey` at runtime.<br>
<br>
## User flows (MVP)<br>
- Library<br>
  - Upload/import files (drag-drop, URL import).<br>
  - View list with filters (docType: requirements|knowledge|unknown, tags, status).<br>
  - Select files and start a workflow: ingestion_pipeline, requirements_extraction, knowledge_enrichment.<br>
  - Monitor run status; view logs; re-run failed steps.<br>
- Document details<br>
  - Preview text (post-parse), metadata, and derived artifacts (chunks, embeddings count, extracted items).<br>
  - Actions: re-ingest, re-embed (model change), open in Playground context.<br>
- Playground integration<br>
  - Choose context from Requirements and Knowledge sets; run chat with citations; actions to persist back.<br>
<br>
## Sequence: ingestion pipeline<br>
```mermaid<br>
sequenceDiagram<br>
  participant U as User<br>
  participant UI as Workbench UI<br>
  participant API as API<br>
  participant BPMN as BPMN Engine<br>
  participant W as Workers<br>
  participant OS as Object Store<br>
  participant VS as Vector Store<br>
  participant DB as Metadata DB<br>
<br>
  U->>UI: Upload/import files<br>
  UI->>API: POST /files (multipart or URL)<br>
  API->>OS: Store bytes<br>
  API->>DB: Upsert File + FileVersion<br>
  UI->>API: POST /workflows/start { processKey: ingestion_pipeline, fileIds }<br>
  API->>BPMN: Start process<br>
  BPMN->>W: Detect/Parse/OCR/Chunk<br>
  W-->>DB: Persist Chunk metadata<br>
  W->>VS: Embed + upsert vectors<br>
  BPMN-->>DB: Mark IngestionRun complete<br>
  API-->>UI: Run status and artifacts<br>
```<br>
<br>
## API sketch (MVP)<br>
- POST /files (multipart or { url }) → 201 { fileId }<br>
- GET /files?project=<id>&q=&docType=&status= → 200 [ files ]<br>
- GET /files/:id → 200 { file, versions, latestArtifacts }<br>
- POST /workflows/start { processKey, projectId, params } → 202 { runId }<br>
- GET /workflows/:runId → 200 { status, steps[], logsRef, outputs }<br>
- GET /chunks?fileId=&version= → 200 [ chunks ]<br>
- GET /requirements?project=<id> → 200 [ items ]<br>
- GET /knowledge?project=<id> → 200 [ items ]<br>
- POST /playground/sessions → 201 { sessionId }<br>
- POST /playground/sessions/:id/message → 200 { reply, citations[] }<br>
<br>
Notes:<br>
- All long-running operations are started via `POST /workflows/start` referencing a BPMN `processKey`.<br>
- Workers are triggered via the BPMN engine; API remains thin and stateless.<br>
<br>
## Implemented API (current)<br>
- Files<br>
  - POST `/api/files/upload` — multipart, fields: `file`, `project_id`, optional `tags` (JSON); auth required<br>
  - POST `/api/files/batch/upload` — multipart, fields: `files[]`, optional `project_id`<br>
  - GET `/api/files?project_id=` — returns `files[]` with metadata (includes `tags` if provided)<br>
  - GET `/api/files/{file_id}/download`, GET `/api/files/{file_id}/url`<br>
  - DELETE `/api/files/{file_id}`<br>
  - POST `/api/files/{file_id}/process` — start Camunda process for this file<br>
  - GET `/api/files/keywords`, PUT `/api/files/keywords`, POST `/api/files/extract/keywords`<br>
- Camunda helpers (selected)<br>
  - POST `/api/upload` — start analysis directly from uploaded content (requires `project_id`)<br>
  - GET `/api/user-tasks`, task-by-instance routes; GET `/api/camunda/status`<br>
<br>
Planned additions (to support docType/status UX):<br>
- POST `/api/files/import-url` — server-side fetch by URL with `project_id`, `tags` (including `docType`)<br>
- GET `/api/files/{file_id}` — return metadata (and tags) for a single file<br>
- PUT `/api/files/{file_id}/tags` — update tags (to carry `status` changes like `ingested`, `embedded`)<br>
- Extend GET `/api/files` to accept optional filters: `docType`, `status`, `tags` (server-side), or filter client-side in MVP<br>
<br>
## Storage strategy (MVP)<br>
- Object Store: local FS or S3-compatible for file bytes.<br>
- Metadata DB: relational (e.g., Postgres) for files, runs, extractions.<br>
- Vector Store: pgvector/Qdrant/Weaviate; store embedding model id with vectors.<br>
<br>
## LLM Playground planning<br>
- Context selectors: choose Requirements and Knowledge subsets; filter by project/tags.<br>
- Chat with citations; every citation resolves to file/version/chunk.<br>
- Actions (persisted via API):<br>
  - "Create requirement" → adds Requirement with citation to source chunk.<br>
  - "Save snippet to Knowledge" → creates KnowledgeItem with lineage.<br>
  - "Link to requirement" → associates snippet to an existing Requirement.<br>
- Sessions may optionally be driven by a BPMN `rag_playground_session` for parity and audit.<br>
<br>
## Validation & safety (MVP)<br>
- Deduplicate files by bytesHash per project; allow reprocessing of the same file.<br>
- Enforce model/version consistency in embeddings; re-embed on model change via workflow.<br>
- Ensure each derived artifact carries provenance (fileId, version, runId, stepId).<br>
<br>
## Versioning (later)<br>
- Maintain FileVersion chain with immutable derived artifacts; soft-delete support.<br>
- Add process versioning and migration for BPMN definitions.<br>
<br>
## MVP TODO checklist (File Management Workbench)<br>
<br>
- [ ] FM-0: Route and Library<br>
  - [x] Create `File Management` route/page; mount under existing layout (exists in `frontend/app.html`)<br>
  - [ ] Project-scoped library view with filters (docType/tags/status) wired to `/api/files`<br>
  - [ ] Upload/import (drag-drop + URL) wired to `/api/files/upload` (per-file) or `/api/files/batch/upload`<br>
<br>
- [ ] FM-1: BPMN engine and definitions<br>
  - [x] Add BPMN engine wiring in backend (runtime + REST start/status)<br>
  - [ ] Define `ingestion_pipeline.bpmn` (detect → ocr? → parse → chunk → embed → index)<br>
  - [ ] Define `requirements_extraction.bpmn`<br>
  - [ ] Define `knowledge_enrichment.bpmn`<br>
  - [ ] Define `rag_playground_session.bpmn` (ephemeral, optional)<br>
<br>
- [ ] FM-2: Workers (services)<br>
  - [ ] Parser/OCR/Chunker worker with text normalization<br>
  - [ ] Embedder/Indexer worker (configurable model)<br>
  - [ ] Requirements extractor worker (LLM + citations)<br>
  - [ ] Knowledge synthesizer worker (LLM + citations)<br>
<br>
- [ ] FM-3: API contracts<br>
  - [x] POST /api/files/upload, GET /api/files<br>
  - [ ] GET /api/files/:id (metadata), filters on `docType/status/tags`, tags update route<br>
  - [ ] POST /workflows/start (or reuse `/api/files/{id}/process`), GET /workflows/:runId<br>
  - [ ] GET /chunks, GET /requirements, GET /knowledge<br>
<br>
- [ ] FM-4: Library UI<br>
  - [ ] Upload/import UI with progress<br>
  - [ ] File list with status badges and actions (start workflows)<br>
  - [ ] Run status panel and logs link<br>
<br>
- [ ] FM-5: Document details UI<br>
  - [ ] Text preview, metadata, derived artifacts (chunks/embeddings counts)<br>
  - [ ] Actions: re-ingest, re-embed, open in Playground<br>
<br>
- [ ] FM-6: Playground integration<br>
  - [ ] Context selectors for Requirements/Knowledge subsets<br>
  - [ ] Chat with citations and actions (save snippet/link/create requirement)<br>
<br>
- [ ] FM-7: Validation, idempotency, and provenance<br>
  - [ ] Content hashing and deduplication<br>
  - [ ] Provenance capture (file/version/run/step) on all artifacts<br>
<br>
- [ ] FM-8: Tests and acceptance<br>
  - [ ] Unit tests for parsing/chunking/embedding<br>
  - [ ] Contract tests for workflow start/status and artifact creation<br>
  - [ ] UI smoke test: upload → ingest → view artifacts → run extraction → view items<br>
<br>
## Acceptance criteria (MVP)<br>
- Upload/import files; list and filter in Library.<br>
- Start ingestion via BPMN; chunks/embeddings appear with provenance.<br>
- Start requirements extraction and knowledge enrichment via BPMN; items created with citations.<br>
- Playground consumes selected context sets and supports actions that persist artifacts.<br>
- No RAG steps are hard-coded in app logic; all run through BPMN by `processKey`.<br>
<br>
## Next step plan (to ship File Manager for Requirements & Knowledge)<br>
- Wire Files Workbench UI (`frontend/app.html`, `#wb-files`) to the backend:<br>
  - Use `odras_token` in `Authorization: Bearer` and `active_project_id` for all writes.<br>
  - Replace placeholder Upload-All with real uploads:<br>
    - For per-file tags (to capture `docType`), call POST `/api/files/upload` per file with `tags={ docType }` and `project_id`.<br>
    - Optionally keep batch upload for speed; add per-file tags later.<br>
  - Implement Refresh to call GET `/api/files?project_id=...`; filter client-side by docType/status/tags for now.<br>
  - In Library rows, add actions: Delete (DELETE `/api/files/{id}`), Get URL (GET `/api/files/{id}/url`), Process (POST `/api/files/{id}/process`).<br>
  - Stage URL import in UI and POST to a new backend route `/api/files/import-url` (server downloads) — quick follow-up.<br>
- Tag model for doc type and status:<br>
  - On upload, include `tags = { docType: "requirements"|"knowledge"|"unknown", status: "new" }`.<br>
  - After ingestion, workers (or a small callback) update `status` to `ingested`/`embedded` via a `PUT /api/files/{id}/tags` endpoint.<br>
- Add a “Quick extract by keywords” button that calls POST `/api/files/extract/keywords` and displays the result summary in the UI.<br>
<br>
Deliverables for this step:<br>
- Files Workbench shows real library from `/api/files`, supports upload, delete, presigned URL, and “Process” per file.<br>
- Doc type visible as a badge; filter chip(s) work client-side.<br>
- Optional: simple toast/logs for process starts and keyword extraction runs.<br>
<br>
## Adopted best practices for document management (RAG-focused)<br>
<br>
- Metadata and tags as first-class: capture `docType`, `status`, source, authorship, confidentiality, and domain tags. Enable multi-facet filtering and deterministic lineage via content hashing and versioning.<br>
- Versioning and provenance: immutable `FileVersion` chain; every derived artifact includes `fileId`, `version`, `runId`, and a `pipelineConfigHash` (fingerprint of chunking/embedding params) for replayability and safe reprocessing.<br>
- Chunking strategy: semantic-first segmentation (headings, sections, sentences), then token-window fallback. Defaults: `sizeTokens=350`, `overlapTokens=50`, `respectHeadings=true`, `joinShortParagraphs=true`.<br>
- Embedding discipline: model registry with versioning; re-embed triggered on model/default change or chunking parameter change. Store embedding model id with each vector and record normalization.<br>
- OCR and layout: detect scanned PDFs; use OCR pipeline when needed, preserving page numbers and text coordinates where feasible for better citation UX.<br>
- Previews: safe, in-browser previews for Markdown, text, PDF, and CSV without requiring download; limit row/page counts for large files.<br>
- Security: project-scoped RBAC and token-based access on all write operations; download/preview URLs can be short-lived presigned links.<br>
- Observability: workflow runs expose step-level logs, inputs/outputs, and artifacts with links; surface errors and re-run affordances in UI.<br>
<br>
## Design updates for File Management Workbench<br>
<br>
### File previews (UI + API)<br>
- UI: in `#wb-files`, add a right-side preview panel for selected file. Renderers:<br>
  - Markdown/Text: client-side render (sanitize HTML), line numbers toggle for `.txt`.<br>
  - PDF: embed PDF.js viewer using file URL or a proxied preview route.<br>
  - CSV: stream first N rows with client table (virtualized for large files), download full.<br>
- API additions:<br>
  - GET `/api/files/{file_id}/preview?mode=text|markdown|pdf|csv&maxRows=...` → 200 stream/text or redirects to presigned URL for PDF.<br>
  - Existing `GET /api/files/{file_id}/url` remains for direct viewer sources (PDF.js, CSV fetch).<br>
<br>
### Chunking and embedding from File Manager<br>
- Replace separate Embedding workspace: ingestion and embedding are triggered from the Files Workbench.<br>
- Ingest/Embed action opens a drawer with parameters:<br>
  - Chunking: `strategy=semantic|fixed`, `sizeTokens` (default 350), `overlapTokens` (default 50), `respectHeadings`, `joinShortParagraphs`, `splitCodeBlocks`.<br>
  - Embedding: `modelId` (from registry), `normalize=true|false` (default true), optional `batchSize`.<br>
- Persist selected params in `IngestionRun.params` and compute a `pipelineConfigHash` used for idempotency and provenance.<br>
- Re-embed flow: choose a different model or parameters; pipeline reads latest parsed text and regenerates vectors only.<br>
<br>
### Embedding model management<br>
- Model registry (system-level):<br>
  - `EmbeddingModel`: `id`, `provider`, `name`, `version`, `dimensions`, `maxInputTokens`, `normalizeDefault`, `status{active|deprecated}`, `createdAt`.<br>
  - API:<br>
    - GET `/api/embedding-models` — list registry<br>
    - POST `/api/embedding-models` — register model<br>
    - PUT `/api/embedding-models/{id}` — update metadata/status<br>
    - DELETE `/api/embedding-models/{id}` — soft-delete/deprecate<br>
- Project defaults and overrides:<br>
  - GET `/api/projects/{project_id}/embedding-model` — resolve default<br>
  - PUT `/api/projects/{project_id}/embedding-model` — set default<br>
  - Optional: GET/PUT `/api/projects/{project_id}/chunking-config`<br>
<br>
### API additions/changes<br>
- Files (additions):<br>
  - GET `/api/files/{file_id}` — single-file metadata with tags and latest artifacts<br>
  - PUT `/api/files/{file_id}/tags` — update tags (status transitions `new → ingested → embedded`)<br>
  - POST `/api/files/import-url` — server-side import by URL with `project_id`, `tags`<br>
  - GET `/api/files/{file_id}/preview` — see above<br>
- Workflows:<br>
  - POST `/api/workflows/start` payload sample:<br>
    ```json<br>
    {<br>
      "processKey": "ingestion_pipeline",<br>
      "projectId": "...",<br>
      "fileIds": ["..."],<br>
      "params": {<br>
        "chunking": {<br>
          "strategy": "semantic",<br>
          "sizeTokens": 350,<br>
          "overlapTokens": 50,<br>
          "respectHeadings": true,<br>
          "joinShortParagraphs": true,<br>
          "splitCodeBlocks": true<br>
        },<br>
        "embedding": {<br>
          "modelId": "e5-large-v2",<br>
          "normalize": true,<br>
          "batchSize": 64<br>
        }<br>
      }<br>
    }<br>
    ```<br>
  - Re-embed: reuse `ingestion_pipeline` with `params.mode = "reembed"` or introduce `reembed_pipeline` with `fileIds`, `modelId`.<br>
<br>
### Data model updates<br>
- Add `EmbeddingModel` (registry as above).<br>
- Extend `Project` settings: `defaultEmbeddingModelId`, `defaultChunkingConfig`.<br>
- `IngestionRun`: add `params` JSON and `pipelineConfigHash` (hash of params + worker versions).<br>
- `Chunk`: ensure `sectionPath`, `pageNumber`, and `tokenCount` present; `Embedding` continues to carry `modelId` and vector.<br>
<br>
### Workflow updates<br>
- `ingestion_pipeline` steps:<br>
  1) Detect type → 2) Optional OCR → 3) Parse/normalize → 4) Semantic segmentation → 5) Token windowing (fallback) → 6) Embed → 7) Upsert vectors → 8) Persist artifacts/metadata.<br>
- Idempotency: skip recompute if `pipelineConfigHash` + `fileVersion.bytesHash` matches an existing successful run for the same outputs.<br>
- Provenance: every artifact references `runId` and includes the config snapshot.<br>
<br>
### UI/UX updates in `frontend/app.html`<br>
- Library table: show `docType` and `status` badges; action menu: `Preview`, `Download`, `Get URL`, `Delete`, `Ingest/Embed`, `Re-embed`, `Start Requirements Extraction`.<br>
- Filters: client-side chips for `docType`, `status`, `tags`, with server-side query support when available.<br>
- Model selector: dropdown bound to `/api/embedding-models` and project default; allow per-run override.<br>
- Project tree integration: newly uploaded files appear under the active project's node; selecting a node focuses the file in the Workbench and opens the preview panel.<br>
- Remove Embedding workspace: routes/menus consolidated under File Management Workbench.<br>
<br>
## Chunking and embedding strategy (defaults and rationale)<br>
<br>
- Defaults aim to balance recall/precision and context fit for common LLMs:<br>
  - `sizeTokens=350`, `overlapTokens=50` (~14% overlap) for general prose.<br>
  - For highly structured content (requirements lists, specs), keep `respectHeadings=true` and enable `joinShortParagraphs` to avoid over-fragmentation.<br>
  - For code or config blobs, enable `splitCodeBlocks` to keep logical units intact.<br>
- Sentence-aware segmentation reduces mid-sentence splits; fallback token windows ensure coverage when structure is poor.<br>
- Overlap ensures cross-boundary recall during retrieval; tune between 10%–20% based on document style and retriever behavior.<br>
- Re-embedding is required when either the model or chunking parameters change; use registry status to deprecate models and surface re-embed prompts in UI.<br>
<br>
## Updated MVP TODO checklist (delta)<br>
<br>
- [ ] FM-0: Route and Library (expand)<br>
  - [ ] Project-scoped library wired to `/api/files` with filters (`docType/status/tags`)<br>
  - [ ] Show uploads in main project tree view (focus file on select)<br>
- [ ] FM-2: Workers (services)<br>
  - [ ] Implement semantic-first chunker with token window fallback<br>
  - [ ] Add OCR pipeline for scanned PDFs (toggleable)<br>
- [ ] FM-3: API contracts (expand)<br>
  - [ ] GET `/api/files/{id}` and PUT `/api/files/{id}/tags`<br>
  - [ ] GET `/api/files/{id}/preview` (md/txt/pdf/csv)<br>
  - [ ] POST `/api/files/import-url`<br>
  - [ ] POST `/api/workflows/start` with chunking/embedding params<br>
- [ ] FM-4: Library UI (expand)<br>
  - [ ] Preview panel for md/txt/pdf/csv with virtualization for CSV<br>
  - [ ] Ingest/Embed drawer with chunking + model selection<br>
  - [ ] Re-embed action<br>
- [ ] FM-9: Embedding Model Registry<br>
  - [ ] Registry CRUD APIs and persistence<br>
  - [ ] Project default model endpoints and UI selector<br>
  - [ ] Deprecation flow and re-embed prompts<br>
- [ ] FM-10: Remove Embedding workspace<br>
  - [ ] Consolidate routes/menus into Files Workbench<br>
  - [ ] Migrate any remaining actions to Files Workbench<br>
<br>
## Acceptance criteria (augmented)<br>
<br>
- Users can preview Markdown, text, PDF, and CSV within the Workbench.<br>
- Users can start ingestion with configurable chunking and selected embedding model; vectors appear in the vector store with correct provenance.<br>
- Changing the default embedding model triggers a re-embed prompt; completed runs show lineage (`runId`, `pipelineConfigHash`).<br>
- Uploaded files appear under the active project's tree node and can be acted on from the Workbench.<br>
- The separate Embedding workspace is removed; all related actions live in File Management.<br>
<br>
<br>

