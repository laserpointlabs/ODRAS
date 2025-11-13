<!-- 9ab58978-72c4-4036-98a1-7848b3c9ff3e aa4aa543-7834-4973-a75e-16b7cac7515e -->
# ODRAS MVP Refactoring Plan

## Overview

Refactor ODRAS from monolithic files into a clean, modular architecture that:

- Enables future workbench plugability
- Supports centralized data management
- Maintains existing functionality
- Prepares for MVP development
- **Emphasizes testing and local CI replication**

## Critical Issues to Address

### 1. DAS Consolidation

- **Problem**: Two DAS implementations (DAS1 deprecated, DAS2 active) causing confusion
- **Solution**: Consolidate to single DAS implementation (rename DAS2 to DAS)

### 2. Ontology API Conflicts

- **Problem**: Ontology endpoints scattered in `main.py` conflict with `backend/api/ontology.py`
- **Solution**: Consolidate ALL ontology endpoints into single router

### 3. RAG Modularization

- **Problem**: RAG components scattered, hard to test and swap backends
- **Solution**: Create modular RAG architecture with abstract interfaces

### 4. Testing Infrastructure

- **Problem**: CI runs in GitHub but developers need local testing
- **Solution**: Create local CI replication and comprehensive testing infrastructure

## Phase 0: Testing Infrastructure (DO FIRST)

### 0.1 Local CI Replication

**Create `scripts/ci-local.sh`:**

```bash
#!/bin/bash
# Mirrors .github/workflows/ci.yml exactly for local testing

set -e

echo "🚀 Running local CI workflow (mirrors GitHub Actions)..."

# Step 1: Start ODRAS stack (same as CI)
./odras.sh clean -y
docker-compose up -d
sleep 20

# Step 2: Initialize database (same as CI)
./odras.sh init-db

# Step 3: Start application (same as CI)
./odras.sh start
sleep 30

# Step 4: Run test suite (same as CI)
pytest tests/test_core_functionality.py -v
pytest tests/test_working_ontology_attributes.py -v
# ... all CI test steps ...

# Step 5: Diagnostic report (same as CI)
echo "📊 System diagnostics..."
```

**Usage**: `./scripts/ci-local.sh` before pushing to verify CI will pass.

### 0.2 Test Coverage Reporting

**Enhance CI.yml and create local script:**

```yaml
- name: Run tests with coverage
  run: |
    pytest tests/ \
      --cov=backend \
      --cov-report=html \
      --cov-report=term \
      --cov-report=xml \
      --cov-fail-under=80
```

**Local**: `pytest tests/ --cov=backend --cov-report=html && open htmlcov/index.html`

### 0.3 Code Quality Tools

**Create `scripts/quality-check.sh`:**

```bash
#!/bin/bash
# Comprehensive code quality checks

# 1. Linting (flake8)
flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics

# 2. Formatting (black)
black --check backend/

# 3. Type checking (mypy) - optional
mypy backend/ --ignore-missing-imports

# 4. Security scanning (bandit)
bandit -r backend/ -f json -o bandit-report.json
```

### 0.4 Pre-Commit Hooks

**Create `.pre-commit-config.yaml`:**

```yaml
repos:
 - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
   - id: trailing-whitespace
   - id: end-of-file-fixer
   - id: check-yaml
   - id: check-added-large-files

 - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
   - id: black

 - repo: local
    hooks:
   - id: pytest-fast
        name: pytest-fast
        entry: pytest tests/api/test_core_functionality.py -v
        language: system
        pass_filenames: false
        always_run: true
```

**Installation**: `pre-commit install`

### 0.5 Test Categorization

**Enhance `pytest.ini`:**

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (require services)
    api: API endpoint tests
    slow: Slow tests (>5 seconds)
    das: DAS-related tests
    rag: RAG-related tests

addopts = 
    -n auto
    --dist loadgroup
    --maxfail=5
    --tb=short
```

## Phase 1: Backend Refactoring (Core Infrastructure)

### 1.1 DAS Consolidation (CRITICAL FIX)

**Problem**: Two DAS implementations exist (DAS1 deprecated, DAS2 active) causing confusion and duplicate initialization.

**Solution**: Consolidate to single DAS implementation

**Steps**:

1. **Remove DAS1 references**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Archive `backend/api/das.py` (keep as reference only)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Remove `backend/services/das_core_engine.py` (or archive)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Remove DAS1 initialization from startup

2. **Rename DAS2 to DAS**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Rename `backend/api/das2.py` → `backend/api/das.py`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Rename `backend/services/das2_core_engine.py` → `backend/services/das_core_engine.py`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update all imports from `das2` to `das`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update API prefix from `/api/das2/` to `/api/das/`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update frontend to use `/api/das/` endpoints

3. **Update startup initialization**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Remove `initialize_das_engine()` call (DAS1)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Keep only `initialize_das2_engine()` (renamed to `initialize_das_engine()`)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update event routing to use single DAS system

### 1.2 Ontology API Consolidation (CRITICAL FIX)

**Problem**: Ontology endpoints scattered across `main.py` and `backend/api/ontology.py`, causing conflicts.

**Solution**: Consolidate ALL ontology endpoints into `backend/api/ontology.py` router.

**Endpoints to move from `main.py`**:

1. **Registry endpoints** (`/api/ontologies`):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `GET /api/ontologies` (line 934)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `POST /api/ontologies` (line 1024)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `GET /api/ontologies/reference` (line 1151)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `PUT /api/ontologies/reference` (line 1521)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `POST /api/ontologies/import-url` (line 1545)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `DELETE /api/ontologies` (line 1669)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `PUT /api/ontologies/label` (line 1710)

2. **Operation endpoints** (`/api/ontology/`):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `POST /api/ontology/push-turtle` (line 893) → Move to router
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `POST /api/ontology/save` (line 1744) → Keep in router (consolidate)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `GET /api/ontology/summary` (line 1877) → Move to router
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `POST /api/ontology/sparql` (line 1910) → Move to router

**Implementation**: Add all endpoints to `backend/api/ontology.py` router, remove from `main.py`.

### 1.3 Extract Application Factory

**Create `backend/app_factory.py`:**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.middleware.session_capture import SessionCaptureMiddleware

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(title="ODRAS API", version="0.1.0")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Add middleware
    app.add_middleware(SessionCaptureMiddleware, redis_client=None)
    
    return app
```

### 1.4 Extract Startup Logic

**Create `backend/startup/` modules:**

- `database.py` - Database initialization
- `services.py` - Service initialization (RAG, Redis, Qdrant)
- `das.py` - Single DAS initialization (consolidated)
- `events.py` - Event system initialization
- `middleware.py` - Middleware configuration
- `routers.py` - Router registration

**Create `backend/startup/initialize.py`:**

```python
async def initialize_application(app: FastAPI) -> None:
    """Centralized application initialization"""
    from .database import initialize_database
    from .services import initialize_services
    from .das import initialize_das  # Single DAS system
    from .events import initialize_event_system
    from .middleware import configure_middleware
    
    settings = Settings()
    
    # Initialize in dependency order
    db = await initialize_database(settings)
    services = await initialize_services(settings, db)
    await initialize_das(settings, services, db)
    await initialize_event_system(app, services, db)
    configure_middleware(app, services)
```

### 1.5 Extract Core Endpoints

**Create `backend/api/core.py`:**

Move these endpoints from `main.py`:

- `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/health`, `/api/sync/health`, `/api/sync/emergency-recovery`
- `/api/projects/*` (project CRUD operations)
- `/app` (UI route)

### 1.6 Slim Down main.py

**Target `backend/main.py` structure (~200 lines):**

```python
from backend.app_factory import create_app
from backend.startup.initialize import initialize_application
from backend.startup.routers import register_routers
from backend.api.core import router as core_router

app = create_app()

# Register routers (includes consolidated ontology router)
register_routers(app)
app.include_router(core_router)

@app.on_event("startup")
async def startup():
    await initialize_application(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Phase 2: RAG Modularization (CRITICAL FOR ENHANCEMENT & TESTING)

### 2.1 RAG Module Structure

**Create `backend/rag/` module:**

```
backend/rag/
├── __init__.py
├── core/
│   ├── rag_service.py          # Main RAG orchestrator
│   ├── query_processor.py      # Query understanding
│   └── response_generator.py   # LLM response generation
├── retrieval/
│   ├── retriever.py            # Abstract retriever interface
│   └── vector_retriever.py     # Vector similarity retrieval
├── storage/
│   ├── vector_store.py         # Abstract vector store interface
│   ├── qdrant_store.py         # Qdrant implementation (current)
│   └── opensearch_store.py    # OpenSearch implementation (stretch)
├── chunking/
│   ├── chunker.py              # Abstract chunker interface
│   └── semantic_chunker.py     # Semantic chunking
└── embedding/
    ├── embedding_service.py    # Abstract embedding interface
    └── local_embedding.py      # Local embedding
```

### 2.2 Abstract Vector Store Interface

**Create `backend/rag/storage/vector_store.py`:**

```python
from abc import ABC, abstractmethod

class VectorStore(ABC):
    """Abstract interface for vector storage backends"""
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def store(self, collection: str, vectors: List[Dict]) -> List[str]:
        pass
```

### 2.3 OpenSearch Text Search Store (COMPLETED ✅)

**Created `backend/rag/storage/opensearch_store.py`:**

- OpenSearch/Elasticsearch is used as a **complementary text search store**** (not a vector store replacement)
- Provides full-text/keyword search (BM25) to complement Qdrant vector similarity search
- Supports hybrid search combining vector (semantic) + keyword (exact match) results
- Added to `docker-compose.yml` as optional service (disabled by default)
- Configured via `OPENSEARCH_ENABLED=true` and `RAG_HYBRID_SEARCH=true`

### 2.4 Reranker Implementation (COMPLETED ✅)

**Created `backend/rag/retrieval/reranker.py`:**

- `ReciprocalRankFusionReranker`: Combines results from multiple sources (RRF algorithm)
- `CrossEncoderReranker`: More accurate reranking using sentence-transformers (optional)
- `HybridReranker`: Combines RRF + cross-encoder for best results
- Configured via `RAG_RERANKER` setting (rrf, cross_encoder, hybrid, none)

### 2.5 Hybrid Retriever (COMPLETED ✅)

**Created `backend/rag/retrieval/hybrid_retriever.py`:**

- Combines vector search (Qdrant) + keyword search (OpenSearch) in parallel
- Deduplicates results by chunk_id
- Uses reranker to combine and rank results from both sources
- Falls back to vector-only if OpenSearch unavailable

### 2.4 Factory Pattern

**Create `backend/rag/storage/factory.py`:**

```python
def create_vector_store(settings: Settings) -> VectorStore:
    """Factory to create vector store based on configuration"""
    backend = getattr(settings, 'vector_store_backend', 'qdrant').lower()
    
    if backend == 'qdrant':
        return QdrantVectorStore(settings)
    elif backend == 'opensearch':
        return OpenSearchVectorStore(settings)  # Stretch goal
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

## Phase 3: Frontend Refactoring

### 3.1 Extract Core Infrastructure

**Create `frontend/js/core/`:**

- `app-init.js` - Application initialization
- `state-manager.js` - Global state management
- `api-client.js` - Centralized API client
- `event-bus.js` - Frontend event system

**Create `frontend/js/components/`:**

- `toolbar.js` - Main toolbar
- `panel-manager.js` - Panel/workbench management
- `modal-dialogs.js` - Shared dialogs

### 3.2 Extract Workbench Modules

**Create `frontend/js/workbenches/`:**

- `requirements/requirements-ui.js`
- `ontology/ontology-ui.js`
- `knowledge/knowledge-ui.js`
- `configurations/configurations-ui.js`
- `cqmt/cqmt-ui.js`

### 3.3 Create Slim index.html

**Create `frontend/index.html` (~300 lines)** that loads modular JavaScript.

## Phase 4: Data Management Foundation

### 4.1 Create Data Access Layer

**Create `backend/services/data_manager.py`** for centralized workbench data access.

### 4.2 Create Workbench Data Contracts

**Create `backend/schemas/workbench_data.py`** with Pydantic models.

## Implementation Order

1. **Testing Infrastructure First** (Phase 0):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create `scripts/ci-local.sh`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Set up pre-commit hooks
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Add test coverage reporting
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create quality check scripts

2. **Backend Refactoring** (Phase 1):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - DAS consolidation
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Ontology API consolidation
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Extract startup modules
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Slim down main.py

3. **RAG Modularization** (Phase 2):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create modular structure
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Implement abstract interfaces
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Refactor RAGService

4. **Frontend Refactoring** (Phase 3):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Extract core modules
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Extract workbenches

5. **Data Management** (Phase 4):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create DataManager
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Define data contracts

## Database Schema Management

### Important: Direct Schema Editing

**No Migration Files**: Work directly in `backend/odras_schema.sql`

- **Primary approach**: Edit `backend/odras_schema.sql` directly
- **Initialization**: `odras.sh init-db` applies `backend/odras_schema.sql` via PostgreSQL
- **Testing**: After schema changes, run `./odras.sh clean -y && ./odras.sh init-db`
- **No migration system**: Do not create migration files during refactoring

**If schema changes are needed during refactoring:**

1. Edit `backend/odras_schema.sql` directly
2. Run `./odras.sh clean -y && ./odras.sh init-db` to test
3. Verify all tests pass
4. Commit schema changes with refactoring code

## Success Criteria

- Backend main.py reduced to ~200 lines
- Frontend app.html reduced to ~300 lines
- Single DAS implementation (DAS2 renamed to DAS)
- All ontology endpoints in single router
- Modular RAG architecture with abstract interfaces
- Local CI replication working (`./scripts/ci-local.sh`)
- Test coverage reporting enabled
- Pre-commit hooks installed
- Database schema changes made directly in `odras_schema.sql` (no migrations)
- All tests pass
- No breaking changes

### To-dos

- [ ] Create backend/app_factory.py with FastAPI app creation and middleware setup
- [ ] Create backend/startup/ modules: initialize.py, database.py, services.py, das.py, events.py, middleware.py, routers.py
- [ ] Create backend/api/core.py and move auth, health, sync, and project endpoints from main.py
- [ ] Refactor backend/main.py to ~200 lines using app_factory and startup modules
- [ ] Create frontend/js/core/ with app-init.js, state-manager.js, api-client.js, event-bus.js
- [ ] Create frontend/js/components/ with toolbar.js, panel-manager.js, modal-dialogs.js
- [ ] Extract workbench modules from app.html to frontend/js/workbenches/ (one at a time, starting with requirements)
- [ ] Extract DAS UI to frontend/js/das/ modules (das-ui.js, das-api.js)
- [ ] Create frontend/index.html (~300 lines) that loads modular JavaScript and replaces app.html
- [ ] Create backend/services/data_manager.py for centralized workbench data access
- [ ] Create backend/schemas/workbench_data.py with Pydantic models for workbench data exchange
- [ ] Test all functionality after each phase: run clean/init-db, start services, test workbenches, verify logs
