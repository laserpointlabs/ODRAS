# Cursor Chat History Integration Plan

## Overview

Extract, parse, and integrate Cursor chat histories into ODRAS knowledge base to inform future development decisions and provide searchable development context.

## Architecture

### 1. **Chat History Extraction**
- **Source**: Windows AppData paths via WSL: `/mnt/c/Users/JohnDeHart/AppData/Roaming/Cursor/User/workspaceStorage/*/chatSessions/*.json`
- **Parser**: Extract conversations, metadata, code snippets, decisions
- **Output**: Structured conversation objects with context preservation

### 2. **Intelligent Chunking Strategy**
- **Conversation Grouping**: Group related exchanges (Q&A pairs, multi-turn discussions)
- **Context Preservation**: Maintain code context, file references, decision rationale
- **Semantic Boundaries**: Chunk at natural conversation breaks, not fixed sizes
- **Metadata Extraction**: Code patterns, architectural decisions, bug fixes, feature implementations

### 3. **Knowledge Extraction**
- **Key Decisions**: Architectural choices, design patterns, implementation approaches
- **Code Patterns**: Reusable solutions, best practices, anti-patterns to avoid
- **Lessons Learned**: What worked, what didn't, why changes were made
- **Project Context**: ODRAS-specific knowledge, domain insights

### 4. **Storage Integration**
- **SQL-First Pattern**: Store in `doc` and `doc_chunk` tables (aligned with existing RAG)
- **Collection**: Use `knowledge_chunks` collection (384 dim) or create `cursor_chat_history` collection
- **Metadata**: Tag with `document_type: "cursor_chat_history"`, include workspace hash, session IDs, timestamps
- **Dual-Write**: SQL + Qdrant vectors (IDs-only payloads)

### 5. **Query/Retrieval Interface**
- **Search**: "How did we implement X?" "What was the decision on Y?"
- **Context Retrieval**: Find relevant conversations during development
- **Pattern Matching**: Identify similar past solutions to current problems

## Implementation Plan

### Phase 1: Parser & Extraction (Current)
1. ✅ Create chat history parser to read Cursor JSON files
2. ✅ Extract conversation structure (messages, code blocks, context)
3. ✅ Identify workspace mappings (hash to project directory)

### Phase 2: Chunking & Knowledge Extraction
1. Build conversation-aware chunking service
2. Extract key information (decisions, patterns, code)
3. Generate metadata tags (topic, decision_type, code_language, etc.)

### Phase 3: Storage Integration
1. Store chunks in SQL (`doc_chunk` table)
2. Create embeddings and store in Qdrant
3. Tag with appropriate metadata for retrieval

### Phase 4: Backup & Export
1. Export to markdown format (human-readable backup)
2. Archive original JSON files
3. Create restoration utility

### Phase 5: Query Interface
1. Build search/retrieval API endpoint
2. Integration with DAS for "How did we..." queries
3. Context-aware suggestions during development

## File Structure

```
scripts/
  cursor_chat_extractor.py      # Main extraction script
  cursor_chat_chunker.py         # Conversation-aware chunking
  cursor_chat_importer.py        # Import into ODRAS knowledge base
  cursor_chat_backup.py          # Backup/export utility
  
docs/development/
  CURSOR_CHAT_HISTORY_INTEGRATION.md  # This document
  CURSOR_CHAT_METADATA_SCHEMA.md        # Metadata schema

data/
  cursor_chat_backups/           # Exported markdown backups
```

## Metadata Schema

```python
{
  "document_type": "cursor_chat_history",
  "workspace_hash": "0163e297d3d23022880a54c19dce58e9",
  "session_id": "0d66fd17-3561-4ac5-af81-d3da9a42b591",
  "workspace_path": "/home/jdehart/working/ODRAS",
  "conversation_date": "2024-06-09",
  "topics": ["database", "rag", "chunking"],
  "code_languages": ["python", "sql"],
  "decision_type": "architecture",  # or "implementation", "bug_fix", "feature"
  "files_referenced": ["backend/services/rag_service.py"],
  "key_insights": ["SQL-first pattern", "chunking strategy"]
}
```

## Usage Examples

### Extraction
```bash
python scripts/cursor_chat_extractor.py \
  --source "/mnt/c/Users/JohnDeHart/AppData/Roaming/Cursor/User/workspaceStorage" \
  --workspace-map "0163e297d3d23022880a54c19dce58e9:/home/jdehart/working/ODRAS" \
  --output data/cursor_chat_backups/
```

### Import into Knowledge Base
```bash
python scripts/cursor_chat_importer.py \
  --project-id <odras-project-id> \
  --source data/cursor_chat_backups/ \
  --chunk-strategy conversation-aware
```

### Query
```python
# In development
"How did we implement SQL-first RAG storage?"
"What was the decision on chunking strategy?"
"Show me conversations about Qdrant collections"
```

## Benefits

1. **Knowledge Preservation**: Capture development decisions and rationale
2. **Pattern Recognition**: Identify reusable solutions and anti-patterns
3. **Context Recovery**: Understand why decisions were made
4. **Future Development**: Learn from past experiences
5. **Onboarding**: Help new developers understand system evolution






