# File Management Workbench MVP

> ⚠️ **DOCUMENT STATUS**: This document is being replaced by [`file_management_status_2024.md`](./file_management_status_2024.md) which reflects the actual current implementation as of December 2024.

## 🎉 **Phase 1 COMPLETE** - File Management Foundation

**The ODRAS File Management Workbench Phase 1 is fully implemented and production-ready!**

### ✅ What's Working
- Project-scoped file upload, library, preview, and deletion
- Admin-controlled public/private file visibility system  
- Advanced file preview (Markdown, Text, PDF, CSV) with fullscreen
- Configurable processing parameters and embedding model selection
- Multi-backend storage with unified API
- Role-based authentication with admin controls

**See [`file_management_status_2024.md`](./file_management_status_2024.md) for complete implementation details.**

---

## Original MVP Planning Document (Historical)

## Goals and scope (MVP)
- Manage project-scoped files: upload, import, list, preview, organize.
- BPMN-orchestrated pipelines for ingestion, chunking, embedding, indexing, and extraction.
- Requirements extraction and Knowledge documents preparation as explicit workflows.
- Integrate with LLM Playground by exposing curated, searchable context sets (Requirements and Knowledge) and actions.
- Provide visibility into workflow runs (status, logs, artifacts) with ability to re-run.

## Principles
- BPMN-first orchestration for all RAG steps; workers are stateless services.
- Idempotent operations and deterministic inputs (content hashing, metadata versioning).
- Separation of concerns: raw file storage vs. derived data (chunks/embeddings/extractions).
- Traceability: every artifact carries lineage to the file version and workflow run.

## High-level architecture
```mermaid
graph TD
  U["User"] --> UI["Browser: File Management Workbench\n(Library | Details | Workflows)"]
  UI --> API["API Server"]
  API --> BPMN["BPMN Engine\n(Process runtime)"]
  BPMN --> W1["Workers: Parse/Chunk/OCR"]
  BPMN --> W2["Workers: Embed/Index"]
  BPMN --> W3["Workers: Requirements Extraction"]
  BPMN --> W4["Workers: Knowledge Enrichment"]
  API --> OS["Object Store\n(Files)"]
  API --> DB["Metadata DB\n(files, runs, extractions)"]
  API --> VS["Vector Store\n(chunks/embeddings)"]
  UI --> PLY["LLM Playground\n(context selectors)"]
```

## Current implementation snapshot (now)
- Backend
  - Implemented file API under `/api/files`:
    - POST `/api/files/upload` (auth + project membership, supports `tags` JSON)
    - POST `/api/files/batch/upload` (bulk upload; project-scoped; no per-file tags yet)
    - GET `/api/files` (returns metadata list; optional `project_id` filter)
    - GET `/api/files/{file_id}/download` and GET `/api/files/{file_id}/url`
    - DELETE `/api/files/{file_id}`
    - POST `/api/files/{file_id}/process` (starts Camunda requirements analysis on stored file)
    - GET/PUT `/api/files/keywords` and POST `/api/files/extract/keywords` (keyword-based quick extraction to RDF)
  - Storage backends available via `Settings.storage_backend`: `local`, `minio`, `postgresql` (with metadata JSON persisted for `local`/`minio`).
  - Camunda integration is wired (see `/api/upload`, `/api/files/{id}/process`, status/user-task routes). BPMN deployment auto-handled from `bpmn/odras_requirements_analysis.bpmn` if needed.
- Frontend
  - Files Workbench exists in `frontend/app.html` (`#wb-files`) with UI for: doc type, status, tags, drag-drop, staged list, and a library panel. Current actions are placeholder-only for Upload/Refresh; library list is not yet wired to the backend in this UI.
  - A separate minimal page (root index) contains a Files tab already calling `/api/files` and `/api/files/batch/upload` (useful as reference while wiring the new UI).
- Auth and project context
  - Auth token stored as `odras_token`; active project id persisted as `active_project_id`. Upload API enforces membership; list/download/delete currently do not enforce auth in MVP.


## Data model (MVP)
- Project: id, name, settings.
- File: id, projectId, name, bytesHash, mimeType, size, storageKey, createdAt, tags[].
- FileVersion: fileId, version, bytesHash, ocrApplied?, textExtracted?, createdAt.
- IngestionRun: id, projectId, fileId(s), processKey, status, startedAt, finishedAt, logsRef.
- Chunk: id, fileId/version, order, text, tokenCount, section/page metadata.
- Embedding: chunkId, vector, modelId, createdAt.
- Requirement: id, projectId, sourceFileId/version, text, citations[], confidence.
- KnowledgeItem: id, projectId, sourceFileId/version, text/snippet, citations[], tags[].

## BPMN processes (no hard-coded pipelines)
- ingestion_pipeline
  - Detect type → optional OCR → parse → normalize → chunk → embed → upsert vector store → persist metadata → complete.
- requirements_extraction
  - Select doc set → retrieve relevant chunks → LLM extract requirements → persist items with citations → summary.
- knowledge_enrichment
  - Select doc set → retrieve → LLM synthesize knowledge items (with attributions) → persist → summary.
- rag_playground_session (ephemeral)
  - Given selected context sets → retrieval → LLM response → optional actions (save snippet, link, create requirement).

Represent process definitions as BPMN (XML) files under `bpmn/` and reference them by `processKey` at runtime.

## User flows (MVP)
- Library
  - Upload/import files (drag-drop, URL import).
  - View list with filters (docType: requirements|knowledge|unknown, tags, status).
  - Select files and start a workflow: ingestion_pipeline, requirements_extraction, knowledge_enrichment.
  - Monitor run status; view logs; re-run failed steps.
- Document details
  - Preview text (post-parse), metadata, and derived artifacts (chunks, embeddings count, extracted items).
  - Actions: re-ingest, re-embed (model change), open in Playground context.
- Playground integration
  - Choose context from Requirements and Knowledge sets; run chat with citations; actions to persist back.

## Sequence: ingestion pipeline
```mermaid
sequenceDiagram
  participant U as User
  participant UI as Workbench UI
  participant API as API
  participant BPMN as BPMN Engine
  participant W as Workers
  participant OS as Object Store
  participant VS as Vector Store
  participant DB as Metadata DB

  U->>UI: Upload/import files
  UI->>API: POST /files (multipart or URL)
  API->>OS: Store bytes
  API->>DB: Upsert File + FileVersion
  UI->>API: POST /workflows/start { processKey: ingestion_pipeline, fileIds }
  API->>BPMN: Start process
  BPMN->>W: Detect/Parse/OCR/Chunk
  W-->>DB: Persist Chunk metadata
  W->>VS: Embed + upsert vectors
  BPMN-->>DB: Mark IngestionRun complete
  API-->>UI: Run status and artifacts
```

## API sketch (MVP)
- POST /files (multipart or { url }) → 201 { fileId }
- GET /files?project=<id>&q=&docType=&status= → 200 [ files ]
- GET /files/:id → 200 { file, versions, latestArtifacts }
- POST /workflows/start { processKey, projectId, params } → 202 { runId }
- GET /workflows/:runId → 200 { status, steps[], logsRef, outputs }
- GET /chunks?fileId=&version= → 200 [ chunks ]
- GET /requirements?project=<id> → 200 [ items ]
- GET /knowledge?project=<id> → 200 [ items ]
- POST /playground/sessions → 201 { sessionId }
- POST /playground/sessions/:id/message → 200 { reply, citations[] }

Notes:
- All long-running operations are started via `POST /workflows/start` referencing a BPMN `processKey`.
- Workers are triggered via the BPMN engine; API remains thin and stateless.

## Implemented API (current)
- Files
  - POST `/api/files/upload` — multipart, fields: `file`, `project_id`, optional `tags` (JSON); auth required
  - POST `/api/files/batch/upload` — multipart, fields: `files[]`, optional `project_id`
  - GET `/api/files?project_id=` — returns `files[]` with metadata (includes `tags` if provided)
  - GET `/api/files/{file_id}/download`, GET `/api/files/{file_id}/url`
  - DELETE `/api/files/{file_id}`
  - POST `/api/files/{file_id}/process` — start Camunda process for this file
  - GET `/api/files/keywords`, PUT `/api/files/keywords`, POST `/api/files/extract/keywords`
- Camunda helpers (selected)
  - POST `/api/upload` — start analysis directly from uploaded content (requires `project_id`)
  - GET `/api/user-tasks`, task-by-instance routes; GET `/api/camunda/status`

Planned additions (to support docType/status UX):
- POST `/api/files/import-url` — server-side fetch by URL with `project_id`, `tags` (including `docType`)
- GET `/api/files/{file_id}` — return metadata (and tags) for a single file
- PUT `/api/files/{file_id}/tags` — update tags (to carry `status` changes like `ingested`, `embedded`)
- Extend GET `/api/files` to accept optional filters: `docType`, `status`, `tags` (server-side), or filter client-side in MVP

## Storage strategy (MVP)
- Object Store: local FS or S3-compatible for file bytes.
- Metadata DB: relational (e.g., Postgres) for files, runs, extractions.
- Vector Store: pgvector/Qdrant/Weaviate; store embedding model id with vectors.

## LLM Playground planning
- Context selectors: choose Requirements and Knowledge subsets; filter by project/tags.
- Chat with citations; every citation resolves to file/version/chunk.
- Actions (persisted via API):
  - "Create requirement" → adds Requirement with citation to source chunk.
  - "Save snippet to Knowledge" → creates KnowledgeItem with lineage.
  - "Link to requirement" → associates snippet to an existing Requirement.
- Sessions may optionally be driven by a BPMN `rag_playground_session` for parity and audit.

## Validation & safety (MVP)
- Deduplicate files by bytesHash per project; allow reprocessing of the same file.
- Enforce model/version consistency in embeddings; re-embed on model change via workflow.
- Ensure each derived artifact carries provenance (fileId, version, runId, stepId).

## Versioning (later)
- Maintain FileVersion chain with immutable derived artifacts; soft-delete support.
- Add process versioning and migration for BPMN definitions.

## MVP TODO checklist (File Management Workbench)

- [ ] FM-0: Route and Library
  - [x] Create `File Management` route/page; mount under existing layout (exists in `frontend/app.html`)
  - [ ] Project-scoped library view with filters (docType/tags/status) wired to `/api/files`
  - [ ] Upload/import (drag-drop + URL) wired to `/api/files/upload` (per-file) or `/api/files/batch/upload`

- [ ] FM-1: BPMN engine and definitions
  - [x] Add BPMN engine wiring in backend (runtime + REST start/status)
  - [ ] Define `ingestion_pipeline.bpmn` (detect → ocr? → parse → chunk → embed → index)
  - [ ] Define `requirements_extraction.bpmn`
  - [ ] Define `knowledge_enrichment.bpmn`
  - [ ] Define `rag_playground_session.bpmn` (ephemeral, optional)

- [ ] FM-2: Workers (services)
  - [ ] Parser/OCR/Chunker worker with text normalization
  - [ ] Embedder/Indexer worker (configurable model)
  - [ ] Requirements extractor worker (LLM + citations)
  - [ ] Knowledge synthesizer worker (LLM + citations)

- [ ] FM-3: API contracts
  - [x] POST /api/files/upload, GET /api/files
  - [ ] GET /api/files/:id (metadata), filters on `docType/status/tags`, tags update route
  - [ ] POST /workflows/start (or reuse `/api/files/{id}/process`), GET /workflows/:runId
  - [ ] GET /chunks, GET /requirements, GET /knowledge

- [ ] FM-4: Library UI
  - [ ] Upload/import UI with progress
  - [ ] File list with status badges and actions (start workflows)
  - [ ] Run status panel and logs link

- [ ] FM-5: Document details UI
  - [ ] Text preview, metadata, derived artifacts (chunks/embeddings counts)
  - [ ] Actions: re-ingest, re-embed, open in Playground

- [ ] FM-6: Playground integration
  - [ ] Context selectors for Requirements/Knowledge subsets
  - [ ] Chat with citations and actions (save snippet/link/create requirement)

- [ ] FM-7: Validation, idempotency, and provenance
  - [ ] Content hashing and deduplication
  - [ ] Provenance capture (file/version/run/step) on all artifacts

- [ ] FM-8: Tests and acceptance
  - [ ] Unit tests for parsing/chunking/embedding
  - [ ] Contract tests for workflow start/status and artifact creation
  - [ ] UI smoke test: upload → ingest → view artifacts → run extraction → view items

## Acceptance criteria (MVP)
- Upload/import files; list and filter in Library.
- Start ingestion via BPMN; chunks/embeddings appear with provenance.
- Start requirements extraction and knowledge enrichment via BPMN; items created with citations.
- Playground consumes selected context sets and supports actions that persist artifacts.
- No RAG steps are hard-coded in app logic; all run through BPMN by `processKey`.

## Next step plan (to ship File Manager for Requirements & Knowledge)
- Wire Files Workbench UI (`frontend/app.html`, `#wb-files`) to the backend:
  - Use `odras_token` in `Authorization: Bearer` and `active_project_id` for all writes.
  - Replace placeholder Upload-All with real uploads:
    - For per-file tags (to capture `docType`), call POST `/api/files/upload` per file with `tags={ docType }` and `project_id`.
    - Optionally keep batch upload for speed; add per-file tags later.
  - Implement Refresh to call GET `/api/files?project_id=...`; filter client-side by docType/status/tags for now.
  - In Library rows, add actions: Delete (DELETE `/api/files/{id}`), Get URL (GET `/api/files/{id}/url`), Process (POST `/api/files/{id}/process`).
  - Stage URL import in UI and POST to a new backend route `/api/files/import-url` (server downloads) — quick follow-up.
- Tag model for doc type and status:
  - On upload, include `tags = { docType: "requirements"|"knowledge"|"unknown", status: "new" }`.
  - After ingestion, workers (or a small callback) update `status` to `ingested`/`embedded` via a `PUT /api/files/{id}/tags` endpoint.
- Add a “Quick extract by keywords” button that calls POST `/api/files/extract/keywords` and displays the result summary in the UI.

Deliverables for this step:
- Files Workbench shows real library from `/api/files`, supports upload, delete, presigned URL, and “Process” per file.
- Doc type visible as a badge; filter chip(s) work client-side.
- Optional: simple toast/logs for process starts and keyword extraction runs.

## Adopted best practices for document management (RAG-focused)

- Metadata and tags as first-class: capture `docType`, `status`, source, authorship, confidentiality, and domain tags. Enable multi-facet filtering and deterministic lineage via content hashing and versioning.
- Versioning and provenance: immutable `FileVersion` chain; every derived artifact includes `fileId`, `version`, `runId`, and a `pipelineConfigHash` (fingerprint of chunking/embedding params) for replayability and safe reprocessing.
- Chunking strategy: semantic-first segmentation (headings, sections, sentences), then token-window fallback. Defaults: `sizeTokens=350`, `overlapTokens=50`, `respectHeadings=true`, `joinShortParagraphs=true`.
- Embedding discipline: model registry with versioning; re-embed triggered on model/default change or chunking parameter change. Store embedding model id with each vector and record normalization.
- OCR and layout: detect scanned PDFs; use OCR pipeline when needed, preserving page numbers and text coordinates where feasible for better citation UX.
- Previews: safe, in-browser previews for Markdown, text, PDF, and CSV without requiring download; limit row/page counts for large files.
- Security: project-scoped RBAC and token-based access on all write operations; download/preview URLs can be short-lived presigned links.
- Observability: workflow runs expose step-level logs, inputs/outputs, and artifacts with links; surface errors and re-run affordances in UI.

## Design updates for File Management Workbench

### File previews (UI + API)
- UI: in `#wb-files`, add a right-side preview panel for selected file. Renderers:
  - Markdown/Text: client-side render (sanitize HTML), line numbers toggle for `.txt`.
  - PDF: embed PDF.js viewer using file URL or a proxied preview route.
  - CSV: stream first N rows with client table (virtualized for large files), download full.
- API additions:
  - GET `/api/files/{file_id}/preview?mode=text|markdown|pdf|csv&maxRows=...` → 200 stream/text or redirects to presigned URL for PDF.
  - Existing `GET /api/files/{file_id}/url` remains for direct viewer sources (PDF.js, CSV fetch).

### Chunking and embedding from File Manager
- Replace separate Embedding workspace: ingestion and embedding are triggered from the Files Workbench.
- Ingest/Embed action opens a drawer with parameters:
  - Chunking: `strategy=semantic|fixed`, `sizeTokens` (default 350), `overlapTokens` (default 50), `respectHeadings`, `joinShortParagraphs`, `splitCodeBlocks`.
  - Embedding: `modelId` (from registry), `normalize=true|false` (default true), optional `batchSize`.
- Persist selected params in `IngestionRun.params` and compute a `pipelineConfigHash` used for idempotency and provenance.
- Re-embed flow: choose a different model or parameters; pipeline reads latest parsed text and regenerates vectors only.

### Embedding model management
- Model registry (system-level):
  - `EmbeddingModel`: `id`, `provider`, `name`, `version`, `dimensions`, `maxInputTokens`, `normalizeDefault`, `status{active|deprecated}`, `createdAt`.
  - API:
    - GET `/api/embedding-models` — list registry
    - POST `/api/embedding-models` — register model
    - PUT `/api/embedding-models/{id}` — update metadata/status
    - DELETE `/api/embedding-models/{id}` — soft-delete/deprecate
- Project defaults and overrides:
  - GET `/api/projects/{project_id}/embedding-model` — resolve default
  - PUT `/api/projects/{project_id}/embedding-model` — set default
  - Optional: GET/PUT `/api/projects/{project_id}/chunking-config`

### API additions/changes
- Files (additions):
  - GET `/api/files/{file_id}` — single-file metadata with tags and latest artifacts
  - PUT `/api/files/{file_id}/tags` — update tags (status transitions `new → ingested → embedded`)
  - POST `/api/files/import-url` — server-side import by URL with `project_id`, `tags`
  - GET `/api/files/{file_id}/preview` — see above
- Workflows:
  - POST `/api/workflows/start` payload sample:
    ```json
    {
      "processKey": "ingestion_pipeline",
      "projectId": "...",
      "fileIds": ["..."],
      "params": {
        "chunking": {
          "strategy": "semantic",
          "sizeTokens": 350,
          "overlapTokens": 50,
          "respectHeadings": true,
          "joinShortParagraphs": true,
          "splitCodeBlocks": true
        },
        "embedding": {
          "modelId": "e5-large-v2",
          "normalize": true,
          "batchSize": 64
        }
      }
    }
    ```
  - Re-embed: reuse `ingestion_pipeline` with `params.mode = "reembed"` or introduce `reembed_pipeline` with `fileIds`, `modelId`.

### Data model updates
- Add `EmbeddingModel` (registry as above).
- Extend `Project` settings: `defaultEmbeddingModelId`, `defaultChunkingConfig`.
- `IngestionRun`: add `params` JSON and `pipelineConfigHash` (hash of params + worker versions).
- `Chunk`: ensure `sectionPath`, `pageNumber`, and `tokenCount` present; `Embedding` continues to carry `modelId` and vector.

### Workflow updates
- `ingestion_pipeline` steps:
  1) Detect type → 2) Optional OCR → 3) Parse/normalize → 4) Semantic segmentation → 5) Token windowing (fallback) → 6) Embed → 7) Upsert vectors → 8) Persist artifacts/metadata.
- Idempotency: skip recompute if `pipelineConfigHash` + `fileVersion.bytesHash` matches an existing successful run for the same outputs.
- Provenance: every artifact references `runId` and includes the config snapshot.

### UI/UX updates in `frontend/app.html`
- Library table: show `docType` and `status` badges; action menu: `Preview`, `Download`, `Get URL`, `Delete`, `Ingest/Embed`, `Re-embed`, `Start Requirements Extraction`.
- Filters: client-side chips for `docType`, `status`, `tags`, with server-side query support when available.
- Model selector: dropdown bound to `/api/embedding-models` and project default; allow per-run override.
- Project tree integration: newly uploaded files appear under the active project's node; selecting a node focuses the file in the Workbench and opens the preview panel.
- Remove Embedding workspace: routes/menus consolidated under File Management Workbench.

## Chunking and embedding strategy (defaults and rationale)

- Defaults aim to balance recall/precision and context fit for common LLMs:
  - `sizeTokens=350`, `overlapTokens=50` (~14% overlap) for general prose.
  - For highly structured content (requirements lists, specs), keep `respectHeadings=true` and enable `joinShortParagraphs` to avoid over-fragmentation.
  - For code or config blobs, enable `splitCodeBlocks` to keep logical units intact.
- Sentence-aware segmentation reduces mid-sentence splits; fallback token windows ensure coverage when structure is poor.
- Overlap ensures cross-boundary recall during retrieval; tune between 10%–20% based on document style and retriever behavior.
- Re-embedding is required when either the model or chunking parameters change; use registry status to deprecate models and surface re-embed prompts in UI.

## Updated MVP TODO checklist (delta)

- [ ] FM-0: Route and Library (expand)
  - [ ] Project-scoped library wired to `/api/files` with filters (`docType/status/tags`)
  - [ ] Show uploads in main project tree view (focus file on select)
- [ ] FM-2: Workers (services)
  - [ ] Implement semantic-first chunker with token window fallback
  - [ ] Add OCR pipeline for scanned PDFs (toggleable)
- [ ] FM-3: API contracts (expand)
  - [ ] GET `/api/files/{id}` and PUT `/api/files/{id}/tags`
  - [ ] GET `/api/files/{id}/preview` (md/txt/pdf/csv)
  - [ ] POST `/api/files/import-url`
  - [ ] POST `/api/workflows/start` with chunking/embedding params
- [ ] FM-4: Library UI (expand)
  - [ ] Preview panel for md/txt/pdf/csv with virtualization for CSV
  - [ ] Ingest/Embed drawer with chunking + model selection
  - [ ] Re-embed action
- [ ] FM-9: Embedding Model Registry
  - [ ] Registry CRUD APIs and persistence
  - [ ] Project default model endpoints and UI selector
  - [ ] Deprecation flow and re-embed prompts
- [ ] FM-10: Remove Embedding workspace
  - [ ] Consolidate routes/menus into Files Workbench
  - [ ] Migrate any remaining actions to Files Workbench

## Acceptance criteria (augmented)

- Users can preview Markdown, text, PDF, and CSV within the Workbench.
- Users can start ingestion with configurable chunking and selected embedding model; vectors appear in the vector store with correct provenance.
- Changing the default embedding model triggers a re-embed prompt; completed runs show lineage (`runId`, `pipelineConfigHash`).
- Uploaded files appear under the active project's tree node and can be acted on from the Workbench.
- The separate Embedding workspace is removed; all related actions live in File Management.


