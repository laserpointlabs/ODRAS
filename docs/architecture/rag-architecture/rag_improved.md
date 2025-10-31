ODRAS - RAG Update Prompts
========================

**Cursor Task: Add SQL-first storage to ODRAS RAG with minimal changes**

**Goal**

* Keep current vector behavior.
* Add SQL as source of truth for docs/chunks and chats.
* Dual-write: SQL + vectors.
* Read-through: vectors find IDs → fetch full text from SQL.

---

## Deliverables

1. DB init that **creates tables if missing** (no migrations).
2. Store/retrieve functions.
3. Wrapper functions to **dual-write** SQL + vector.
4. Update ingest (file upload) and ask/answer (DAS) flows to use SQL-first.
5. Env flags to roll out safely.
6. Basic test.

---

## 1) DB Init (run on app startup)

Create `backend/db/init.py` and call from app boot:

```python
# backend/db/init.py
DDL = """
create table if not exists doc (
  doc_id text primary key,
  project_id text not null,
  filename text not null,
  version int not null default 1,
  sha256 text not null,
  created_at timestamptz default now()
);
create table if not exists doc_chunk (
  chunk_id text primary key,
  doc_id text not null references doc(doc_id) on delete cascade,
  chunk_index int not null,
  text text not null,
  page int,
  start_char int,
  end_char int,
  created_at timestamptz default now()
);
create table if not exists chat_message (
  message_id text primary key,
  session_id text not null,
  project_id text not null,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz default now()
);
create index if not exists idx_doc_chunk_doc on doc_chunk(doc_id, chunk_index);
"""

def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(DDL)
        conn.commit()
```

Call `ensure_schema(conn)` during app startup.

---

## 2) SQL helpers

Create `backend/db/queries.py`:

```python
import uuid, datetime

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def insert_doc(conn, project_id, filename, version, sha256):
    doc_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""insert into doc(doc_id, project_id, filename, version, sha256, created_at)
                       values (%s,%s,%s,%s,%s,%s)""",
                    (doc_id, project_id, filename, version, sha256, now_utc()))
    conn.commit()
    return doc_id

def insert_chunk(conn, doc_id, idx, text, page=None, start=None, end=None):
    chunk_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""insert into doc_chunk(chunk_id, doc_id, chunk_index, text, page, start_char, end_char, created_at)
                       values (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (chunk_id, doc_id, idx, text, page, start, end, now_utc()))
    conn.commit()
    return chunk_id

def insert_chat(conn, session_id, project_id, role, content):
    message_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""insert into chat_message(message_id, session_id, project_id, role, content, created_at)
                       values (%s,%s,%s,%s,%s,%s)""",
                    (message_id, session_id, project_id, role, content, now_utc()))
    conn.commit()
    return message_id

def get_chunks_by_ids(conn, chunk_ids):
    with conn.cursor() as cur:
        cur.execute("""select chunk_id, text, page, start_char, end_char
                       from doc_chunk where chunk_id = any(%s)""", (chunk_ids,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
```

---

## 3) Dual-write wrappers (SQL + vectors)

Create `backend/services/store.py`:

```python
from .embeddings import embed  # your existing embed
from .vectors import qdrant_upsert  # your existing Qdrant client
from backend.db.queries import insert_chunk, insert_chat, now_utc

def store_chunk_and_vector(conn, project_id, doc_id, idx, text, version=1, page=None, start=None, end=None):
    chunk_id = insert_chunk(conn, doc_id, idx, text, page, start, end)
    qdrant_upsert(
        collection="docs_idx",
        id=chunk_id,
        vector=embed(text),
        payload={"project_id": project_id, "doc_id": doc_id, "chunk_id": chunk_id, "version": version},
    )
    return chunk_id

def store_message_and_vector(conn, project_id, session_id, role, content):
    message_id = insert_chat(conn, session_id, project_id, role, content)
    qdrant_upsert(
        collection="project_threads",
        id=message_id,
        vector=embed(content),
        payload={"project_id": project_id, "item_id": message_id, "kind": "message", "role": role,
                 "created_at": now_utc().isoformat()},
    )
    return message_id
```

---

## 4) Env flags (safe rollout)

Add to config:

```
RAG_SQL_READ_THROUGH=true   # if true, fetch chunk text from SQL after vector search
RAG_DUAL_WRITE=true         # if true, write SQL + vectors; else SQL-only for tests
```

Use these flags in handlers to branch behavior.

---

## 5) Update ingest (file upload) flow

Where you currently chunk → embed → write to vectors, change to:

```python
from backend.db.queries import insert_doc
from backend.services.store import store_chunk_and_vector

doc_id = insert_doc(conn, project_id, filename, version, sha256)
for idx, chunk in enumerate(chunks):
    store_chunk_and_vector(conn, project_id, doc_id, idx, chunk.text, version, chunk.page, chunk.start, chunk.end)
```

Vectors remain populated; now you also keep chunk text in SQL.

---

## 6) Update ask/answer (DAS) flow

Replace “read text from vector payload” with SQL read-through:

```python
from uuid import uuid4
from backend.db.queries import insert_chat, get_chunks_by_ids
from backend.services.embeddings import embed
from backend.services.vectors import qdrant_search

session_id = str(uuid4())
insert_chat(conn, session_id, project_id, "user", question)

hits = qdrant_search("docs_idx", vector=embed(question), top_k=40,
                     filter={"must":[{"key":"project_id","match":{"value":project_id}}]})
chunk_ids = [h.payload["chunk_id"] for h in hits]

rows = get_chunks_by_ids(conn, chunk_ids)  # real text from SQL
context = build_context(rows, max_tokens=4000)  # your existing utility

answer = llm.ask(SYSTEM_PROMPT, question, context)
insert_chat(conn, session_id, project_id, "assistant", answer)

# optional: also mirror Q/A into project_threads
if RAG_DUAL_WRITE:
    store_message_and_vector(conn, project_id, session_id, "user", question)
    store_message_and_vector(conn, project_id, session_id, "assistant", answer)
```

---

## 7) Acceptance Criteria

* Upload file: rows created in `doc` and `doc_chunk`; points created in `docs_idx`.
* Ask question: two `chat_message` rows exist; answer built from **SQL** chunk texts.
* If Qdrant is down: chats still listable from SQL; answering may fall back or error by design.
* If SQL is down: do **not** answer from vectors alone.

---

## 8) Quick test (happy path)

Create `tests/test_rag_sql_first.py`:

* Ingest tiny text with two chunks → assert `doc_chunk` rows > 0.
* Ask → assert two `chat_message` rows, and that retrieved chunk texts came from SQL (mock vector client to ensure payload text isn’t used).

---

**Implement exactly as above. Keep vector behavior. SQL becomes authoritative.**






# Small Prompts


## Introduction Prompt

Use this **intro prompt** before each small Cursor task. It sets the rules and context once so each follow-up prompt can stay short.

---

**Intro Prompt — ODRAS RAG (SQL-first) Context**

**Repo:** `laserpointlabs/ODRAS`
**Objective:** Implement RAG with **SQL as source of truth** and **Qdrant for semantic search**.
**Non-Goals (for now):** requirements extraction, ontology linking, fancy re-ranking. RAG first.

**Core rules**

* **Store** all full text (docs/chunks) and all chat messages in **SQL**.
* **Vectors** contain **embeddings + IDs only** (no full text).
* Retrieval = **vector search → get IDs → fetch real text from SQL**.
* Always scope by `project_id`. No raw text in vector payloads.

**Collections**

* `docs_idx`: chunk embeddings; payload `{project_id, doc_id, chunk_id, version}`.
* `project_threads`: chat/event embeddings; payload `{project_id, item_id, kind, role, created_at}`.

**Tables (create if missing; no migrations right now)**

* `doc(doc_id, project_id, filename, version, sha256, created_at)`
* `doc_chunk(chunk_id, doc_id, chunk_index, text, page, start_char, end_char, created_at)`
* `chat_message(message_id, session_id, project_id, role, content, created_at)`

**Feature flags (env)**

* `RAG_DUAL_WRITE` (default `true`): write SQL + vectors; if `false`, SQL-only.
* `RAG_SQL_READ_THROUGH` (default `true`): after vector search, load text from SQL; if `false`, legacy behavior.
* (Optional) `RAG_FTS_PREFILTER` (default `false`): use Postgres FTS to prefilter chunk IDs before vector search.

**Constraints**

* Parameterized SQL only.
* Don’t modify unrelated files.
* Keep payloads small (IDs/timestamps only).
* Enforce token caps when building context.
* If SQL fails → fail the request (don’t answer from vectors alone).
* If Qdrant fails → degrade gracefully (SQL still holds content), but OK to return “degraded retrieval”.

**Deliverable pattern for each task**

* Minimal code changes.
* Clear, checkable **Acceptance Criteria**.
* File list you edited.
* Short verification steps (how to run/test).

**Testing**

* Add/keep a simple E2E test: ingest small text → ask question → verify two `chat_message` rows and citations referencing `(doc_id, chunk_id)`.
* Mock Qdrant if needed; do not depend on network in unit tests.

**Style**

* Prefer small functions in `backend/db/` and `backend/services/`.
* Keep collection names and env flags as above.
* No full text in vector payloads, ever.

**Ready signal for each step**

* Return: “Done + files changed + acceptance checks passed/notes.”

---

Paste this intro first, then follow with each of your small prompts (Prompts 1–7).


Below are **copy-paste prompts** for Cursor. Run them **one at a time** in order.

---

## Prompt 1 — DB init (create tables on startup)

**Task:** Add SQL tables for docs, chunks, and chat. Create if missing at app startup. No migrations.

**Scope:**

* Add `doc`, `doc_chunk`, `chat_message` tables.
* Add index on `(doc_id, chunk_index)` for `doc_chunk`.
* Provide an `ensure_schema(conn)` function and call it on app boot.

**Acceptance:**

* App boots cleanly.
* Tables exist after boot (verified via psql or a quick query).
* No data loss paths introduced.

**Files to edit:**

* `backend/db/init.py` (new)
* App startup module (where DB conn is established) to call `ensure_schema(conn)`.

**Notes:**

* Use `CREATE TABLE IF NOT EXISTS`.
* Timestamps in UTC.
* Keys are `text` or `uuid`—your choice; be consistent.

---

## Prompt 2 — SQL helper functions

**Task:** Implement minimal repository functions for inserts and reads.

**Scope:**

* `insert_doc(conn, project_id, filename, version, sha256) -> doc_id`
* `insert_chunk(conn, doc_id, idx, text, page=None, start=None, end=None) -> chunk_id`
* `insert_chat(conn, session_id, project_id, role, content) -> message_id`
* `get_chunks_by_ids(conn, chunk_ids: list[str]) -> list[dict]`

**Acceptance:**

* Unit test can insert/read rows without errors.
* All statements parameterized (no string concatenation).

**Files to edit:**

* `backend/db/queries.py` (new)

**Notes:**

* Commit after each write; or manage transaction per request (your current pattern).
* Roles restricted to `'user'|'assistant'`.

---

## Prompt 3 — Vector dual-write wrappers (IDs-only payloads)

**Task:** Wrap current vector writes so we **always** write SQL first, then mirror to vectors with IDs-only payloads.

**Scope:**

* `store_chunk_and_vector(conn, project_id, doc_id, idx, text, version=1, page=None, start=None, end=None) -> chunk_id`
* `store_message_and_vector(conn, project_id, session_id, role, content) -> message_id`
* Vector payloads must **not** include full text; only `{project_id, doc_id|item_id, chunk_id, version, role, created_at}`.

**Acceptance:**

* After calling wrappers, SQL rows exist and Qdrant points exist.
* Payloads contain IDs only; no raw text.

**Files to edit:**

* `backend/services/store.py` (new or update)
* Reuse your existing `embed()` and Qdrant client.

**Notes:**

* Keep collection names: `docs_idx` (chunks) and `project_threads` (messages/events).
* Use ISO timestamp for `created_at`.

---

## Prompt 4 — Update ingest (file upload) to SQL-first

**Task:** Replace direct vector writes during upload with SQL-first + mirror.

**Scope:**

* On upload: `doc_id = insert_doc(...)`.
* For each chunk: call `store_chunk_and_vector(...)`.
* Return `{doc_id, version, chunk_count}`.

**Acceptance:**

* Upload returns IDs and counts.
* Chunks present in `doc_chunk`.
* Points present in `docs_idx` with IDs-only payloads.

**Files to edit:**

* Your file ingest handler (e.g., `backend/main.py` or service called by it).

**Notes:**

* Chunk target ~1000 tokens, overlap ~180 (reuse your current chunker).
* Keep `page/start/end` if available.

---

## Prompt 5 — Ask/Answer path: vector search → SQL read-through

**Task:** Change RAG read path to fetch **real text from SQL** using IDs returned by vectors.

**Scope:**

* On question: create `session_id`; `insert_chat(..., role='user', ...)`.
* Vector search `docs_idx` (filter by `project_id`) → get `chunk_id`s.
* `get_chunks_by_ids(conn, chunk_ids)` → build context from SQL texts.
* Call LLM with system prompt + context.
* `insert_chat(..., role='assistant', ...)`.
* (Optional) mirror both messages to `project_threads` via `store_message_and_vector`.

**Acceptance:**

* Answers are produced.
* No text is read from vector payloads.
* Two `chat_message` rows per question.

**Files to edit:**

* RAG query handler (e.g., `backend/main.py` endpoint or `services/rag.py`).

**Notes:**

* System prompt: “Use only the provided context. If not present, say ‘Not in the docs.’ Cite `(filename/page/offsets)`.”
* Enforce a max token window for context.

---

## Prompt 6 — Feature flags for safe rollout

**Task:** Add env flags and wire them.

**Scope:**

* `RAG_DUAL_WRITE` (default `true`): if `false`, skip vector mirror (SQL-only; for tests).
* `RAG_SQL_READ_THROUGH` (default `true`): if `false`, previous behavior is used (legacy).

**Acceptance:**

* Toggling flags affects behavior without code edits.
* Defaults maintain new SQL-first behavior.

**Files to edit:**

* Config module and places where wrappers/read-through are called.

**Notes:**

* Use `os.getenv(..., "true").lower() == "true"` pattern.

---

## Prompt 7 — Basic end-to-end test

**Task:** Add a minimal E2E test for ingest and ask.

**Scope:**

* Ingest small text with 2–3 chunks.
* Assert: `doc_chunk` row count > 0 and Qdrant points exist (mock if needed).
* Ask a question that matches one chunk.
* Assert: two `chat_message` rows exist; returned citations map to valid `(doc_id, chunk_id)`; context built from SQL rows (not vector payload).

**Acceptance:**

* Test passes locally.
* If Qdrant client is mocked, ensure code paths still run.

**Files to edit:**

* `tests/test_rag_sql_first.py` (new)
* Testing utilities/mocks if needed.

**Notes:**

* Keep tests deterministic; avoid network if possible by mocking Qdrant.

---

## Prompt 8 — (Optional) Backfill job from `project_threads` to SQL

**Task:** One-time job to insert any legacy items from vectors into SQL if payload contained text historically.

**Scope:**

* Scroll `project_threads` by `project_id`.
* If `item_id` missing in SQL and payload has `text`/`content`, insert into `chat_message` as historical item (role based on payload if available).

**Acceptance:**

* After run, SQL contains previously missing items.
* Idempotent: re-running doesn’t duplicate.

**Files to edit:**

* `scripts/backfill_threads_to_sql.py` (new)

**Notes:**

* If you never stored text in payloads before, you can skip this prompt.

---

## Prompt 9 — (Optional) SQL FTS prefilter

**Task:** Add Postgres full-text column + index; use it to prefilter by keywords before vector search.

**Scope:**

* `ALTER TABLE doc_chunk ADD COLUMN tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;`
* GIN index on `tsv`.
* Update ask path: preselect top N chunk_ids via FTS; pass as allowed IDs to vector filter.

**Acceptance:**

* Ask path still returns answers.
* When FTS prefilter enabled, vector search is restricted to those IDs.

**Files to edit:**

* Schema init (add `ALTER` and `INDEX`).
* Ask handler (optional prefilter step).

**Notes:**

* Keep this behind a flag `RAG_FTS_PREFILTER=true`.

---

These prompts map exactly to the “What to add (simple)” plan. Run 1→7 to ship; 8–9 are optional improvements.
