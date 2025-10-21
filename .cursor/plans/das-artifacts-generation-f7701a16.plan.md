<!-- f7701a16-2b71-4902-b47e-c3fe192a3215 85598cbd-b518-4af6-b5ab-a308191f5b07 -->
# DAS Artifacts Generation (DAS Actions) - Simple Implementation (Note lets call them DAS Actions)

## Overview

Add five DAS Actions (slash commands) to DAS chat: `/assumption [hint]`, `/white_paper`, `/diagram [description]`, `/help`, and `/summary`. Each command analyzes recent conversation, generates content using OpenAI (similar to conceptualizer pattern), stores artifacts in MinIO and PostgreSQL, and displays them in the main treeview. Includes artifact viewer modal for viewing generated content.

## Architecture

### Command Flow

1. User types slash command in DAS chat
2. DAS2 detects command in message processing
3. Command handler analyzes conversation history + hint/description
4. Generate artifact using OpenAI
5. Store in MinIO + PostgreSQL
6. Add to project artifacts array
7. Return confirmation to user
8. Treeview refreshes to show new artifact

### Option B Flow for `/assumption`

- User provides hint: `/assumption OAuth2 providers will be reliable`
- DAS analyzes hint + last 3-5 messages from conversation
- DAS refines assumption using OpenAI
- DAS presents refined version in chat response with [Edit] [Confirm] [Cancel] options
- User confirms or edits
- Store in database, show in treeview

## Implementation Steps

### 1. Database Schema (New Tables)

Add to `backend/odras_schema.sql`:

```sql
-- Assumptions captured during discussions
CREATE TABLE IF NOT EXISTS project_assumptions (
    assumption_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id),
    conversation_context TEXT,  -- JSON: recent messages
    status VARCHAR(50) DEFAULT 'active',  -- active, validated, invalidated
    notes TEXT
);

CREATE INDEX idx_assumptions_project ON project_assumptions(project_id);
```

### 2. Artifact Generation Service (New File)

Create `backend/services/artifact_generator.py`:

```python
class ArtifactGenerator:
    """Generate artifacts from DAS conversations using OpenAI"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.openai_key = settings.openai_api_key
        
    async def refine_assumption(
        self,
        hint: str,
        conversation_history: List[Dict],
        max_messages: int = 5
    ) -> str:
        """Analyze hint + recent conversation to refine assumption"""
        # Get last N messages
        recent = conversation_history[-max_messages:]
        
        # Build prompt
        prompt = f"""Analyze this discussion and the user's hint to extract a clear, specific assumption.

Recent conversation:
{self._format_conversation(recent)}

User's hint: "{hint}"

Extract a single, clear assumption statement. Be specific and actionable. Return only the assumption text, no explanation."""
        
        # Call OpenAI (use same pattern as llm_team.py _call_openai)
        return await self._call_openai(prompt)
        
    async def generate_white_paper(
        self,
        conversation_history: List[Dict],
        project_metadata: Dict
    ) -> str:
        """Generate white paper markdown from conversation"""
        
        prompt = f"""Generate a professional white paper summarizing this technical discussion.

Project: {project_metadata.get('name', 'Unknown')}
Discussion ({len(conversation_history)} messages):
{self._format_conversation(conversation_history)}

Create a well-structured white paper with:
- Title
- Executive Summary
- Key Topics Discussed (with subsections)
- Technical Details
- Conclusions and Next Steps

Format in clean markdown. Be professional and concise."""
        
        return await self._call_openai(prompt)
        
    async def generate_mermaid_diagram(
        self,
        description: str,
        conversation_history: List[Dict]
    ) -> str:
        """Generate Mermaid diagram from description + conversation context"""
        
        recent = conversation_history[-10:]
        
        prompt = f"""Generate a Mermaid diagram based on this request and discussion context.

User request: "{description}"

Recent discussion:
{self._format_conversation(recent)}

Generate valid Mermaid syntax for an appropriate diagram type (flowchart, sequence, class, etc.).
Return ONLY the mermaid code block, nothing else."""
        
        return await self._call_openai(prompt)
```

### 3. Command Detection in DAS2 (Modify Existing)

Update `backend/services/das2_core_engine.py` in `process_message_stream`:

```python
async def process_message_stream(self, project_id: str, message: str, user_id: str, ...):
    """Process message with streaming response"""
    
    # DETECT SLASH COMMANDS
    if message.strip().startswith('/'):
        async for chunk in self._handle_command(message, project_id, user_id, ...):
            yield chunk
        return
    
    # ... existing normal message processing ...

async def _handle_command(self, message: str, project_id: str, user_id: str, ...):
    """Handle slash commands"""
    parts = message.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    if command == '/assumption':
        async for chunk in self._handle_assumption_command(arg, project_id, user_id, ...):
            yield chunk
    elif command == '/white_paper':
        async for chunk in self._handle_whitepaper_command(project_id, user_id, ...):
            yield chunk
    elif command == '/diagram':
        async for chunk in self._handle_diagram_command(arg, project_id, user_id, ...):
            yield chunk
    else:
        yield {"type": "error", "message": f"Unknown command: {command}"}
```

### 4. Command Handlers (Add to DAS2CoreEngine)

```python
async def _handle_assumption_command(self, hint: str, project_id: str, user_id: str, ...):
    """Handle /assumption command - Option B flow"""
    
    # Get conversation history
    project_context = await self.project_manager.get_project_context(project_id)
    conversation_history = project_context.get("conversation_history", [])
    
    if not hint:
        yield {"type": "error", "message": "Please provide an assumption hint: /assumption [text]"}
        return
    
    # Generate refined assumption
    generator = ArtifactGenerator(self.settings)
    refined = await generator.refine_assumption(hint, conversation_history)
    
    # Store temporarily for confirmation
    temp_id = str(uuid.uuid4())
    # Store in Redis with short TTL for confirmation flow
    
    # Present to user with options
    yield {"type": "content", "content": f"I refined this to:\n\n**{refined}**\n\nReply with:\n- `confirm` to save\n- `edit: [new text]` to modify\n- `cancel` to discard"}
    yield {"type": "done", "metadata": {"pending_assumption": temp_id, "content": refined}}

async def _handle_whitepaper_command(self, project_id: str, user_id: str, ...):
    """Handle /white_paper command"""
    
    yield {"type": "content", "content": "Generating white paper from conversation..."}
    
    # Get full conversation history
    project_context = await self.project_manager.get_project_context(project_id)
    conversation = project_context.get("conversation_history", [])
    project_metadata = project_context.get("project_metadata", {})
    
    # Generate white paper
    generator = ArtifactGenerator(self.settings)
    markdown_content = await generator.generate_white_paper(conversation, project_metadata)
    
    # Store in MinIO + PostgreSQL
    filename = f"whitepaper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    file_id = await self._store_artifact(
        content=markdown_content.encode('utf-8'),
        filename=filename,
        project_id=project_id,
        user_id=user_id,
        artifact_type='whitepaper'
    )
    
    yield {"type": "content", "content": f"\n\n✅ White paper created: **{filename}**"}
    yield {"type": "done", "metadata": {"artifact_id": file_id, "filename": filename}}

async def _handle_diagram_command(self, description: str, project_id: str, user_id: str, ...):
    """Handle /diagram command"""
    
    if not description:
        yield {"type": "error", "message": "Please provide a diagram description: /diagram [description]"}
        return
    
    yield {"type": "content", "content": f"Generating Mermaid diagram for: {description}..."}
    
    # Get conversation context
    project_context = await self.project_manager.get_project_context(project_id)
    conversation = project_context.get("conversation_history", [])
    
    # Generate Mermaid diagram
    generator = ArtifactGenerator(self.settings)
    mermaid_content = await generator.generate_mermaid_diagram(description, conversation)
    
    # Store as .mmd file
    filename = f"diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mmd"
    file_id = await self._store_artifact(
        content=mermaid_content.encode('utf-8'),
        filename=filename,
        project_id=project_id,
        user_id=user_id,
        artifact_type='diagram'
    )
    
    yield {"type": "content", "content": f"\n\n✅ Diagram created: **{filename}**"}
    yield {"type": "done", "metadata": {"artifact_id": file_id, "filename": filename}}

async def _handle_help_command(self):
    """Handle /help command"""
    
    help_text = """**Available DAS Actions:**

• `/assumption [hint]` - Capture and refine an assumption from the discussion
• `/white_paper` - Generate a professional white paper from the conversation
• `/diagram [description]` - Create a Mermaid diagram based on the discussion
• `/summary` - Get a quick summary of recent messages
• `/help` - Show this help message

**Examples:**
- `/assumption OAuth2 providers will be reliable`
- `/white_paper`
- `/diagram authentication flow`
- `/summary`
"""
    
    yield {"type": "content", "content": help_text}
    yield {"type": "done", "metadata": {}}

async def _handle_summary_command(self, project_id: str, user_id: str, ...):
    """Handle /summary command - Quick summary of recent messages"""
    
    yield {"type": "content", "content": "Summarizing recent discussion..."}
    
    # Get last 10 messages
    project_context = await self.project_manager.get_project_context(project_id)
    conversation = project_context.get("conversation_history", [])
    recent = conversation[-10:] if len(conversation) > 10 else conversation
    
    if not recent:
        yield {"type": "content", "content": "\n\nNo recent messages to summarize."}
        yield {"type": "done", "metadata": {}}
        return
    
    # Generate quick summary
    generator = ArtifactGenerator(self.settings)
    
    prompt = f"""Provide a concise 2-3 sentence summary of this recent discussion:

{generator._format_conversation(recent)}

Summary:"""
    
    summary = await generator._call_openai(prompt, max_tokens=150)
    
    yield {"type": "content", "content": f"\n\n**Summary:** {summary}"}
    yield {"type": "done", "metadata": {"summary": summary}}
```

### 5. Artifact Storage Helper (Add to DAS2CoreEngine)

```python
async def _store_artifact(
    self,
    content: bytes,
    filename: str,
    project_id: str,
    user_id: str,
    artifact_type: str
) -> str:
    """Store artifact in MinIO and PostgreSQL"""
    
    from backend.services.file_storage import FileStorageService
    
    storage = FileStorageService(self.settings)
    result = await storage.store_file(
        content=content,
        filename=filename,
        content_type='text/markdown' if filename.endswith('.md') else 'text/plain',
        project_id=project_id,
        tags={'artifact_type': artifact_type, 'generated_by': 'das'},
        created_by=user_id
    )
    
    return result['file_id']
```

### 6. Assumptions Storage (New API Endpoints)

Add to `backend/api/das2.py`:

```python
@router.post("/project/{project_id}/assumption")
async def save_assumption(
    project_id: str,
    request: AssumptionRequest,
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(get_db_service)
):
    """Save confirmed assumption"""
    conn = db._conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO project_assumptions 
            (project_id, content, created_by, conversation_context)
            VALUES (%s, %s, %s, %s)
            RETURNING assumption_id
        """, (project_id, request.content, user['user_id'], request.context))
        assumption_id = cursor.fetchone()[0]
        conn.commit()
        return {"success": True, "assumption_id": assumption_id}
    finally:
        db._return(conn)

@router.get("/project/{project_id}/assumptions")
async def get_assumptions(project_id: str, user: dict = Depends(get_user), db: DatabaseService = Depends(get_db_service)):
    """Get all assumptions for treeview"""
    conn = db._conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT assumption_id, content, created_at, status
            FROM project_assumptions
            WHERE project_id = %s
            ORDER BY created_at DESC
        """, (project_id,))
        rows = cursor.fetchall()
        return {
            "assumptions": [
                {"id": r[0], "content": r[1], "created_at": r[2].isoformat(), "status": r[3]}
                for r in rows
            ]
        }
    finally:
        db._return(conn)
```

### 7. Frontend Treeview Integration (Modify Existing)

Update `frontend/app.html` in the `refreshTree()` function around line 11718:

```javascript
// Fetch assumptions
const assumptionsRes = await fetch(`/api/das2/project/${pid}/assumptions`);
const assumptionsData = await assumptionsRes.json();
const assumptionItems = (assumptionsData.assumptions || []).map(a => 
    makeItem(a.id, a.content.substring(0, 50) + '...', 'assumption')
);

// Fetch artifacts (white papers, diagrams)
const artifactsRes = await fetch(`/api/files/project/${pid}/artifacts`);
const artifactsData = await artifactsRes.json();
const artifactItems = (artifactsData.artifacts || []).map(a =>
    makeItem(a.file_id, a.filename, 'artifact')
);

// Add nodes to tree
const assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', assumptionItems);
const artifactsNode = makeItem('artifacts', 'Artifacts', 'folder', artifactItems);

// Insert after Events, before separator (around line 12078)
[projectInfo, ontologyNode, knowledgeNode, analysisNode, eventsNode, 
 assumptionsNode, separator, artifactsNode].filter(Boolean).forEach(n => root.appendChild(n));
```

### 8. Migration Script

Create `scripts/add_assumptions_table.py`:

```python
#!/usr/bin/env python3
"""Add project_assumptions table to database"""

import psycopg2
from backend.services.config import Settings

settings = Settings()

conn = psycopg2.connect(
    host=settings.postgresql_host,
    port=settings.postgresql_port,
    database=settings.postgresql_database,
    user=settings.postgresql_user,
    password=settings.postgresql_password
)

cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_assumptions (
        assumption_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        created_by UUID REFERENCES users(user_id),
        conversation_context TEXT,
        status VARCHAR(50) DEFAULT 'active',
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_assumptions_project ON project_assumptions(project_id);
""")
conn.commit()
print("✅ project_assumptions table created")
```

## Testing Plan

1. Start ODRAS stack
2. Login as das_service
3. Create test project
4. Have conversation with DAS about a technical topic
5. Test commands:

   - `/assumption OAuth2 providers will be reliable` → should refine and ask for confirmation
   - `/white_paper` → should generate markdown white paper
   - `/diagram this authentication flow` → should generate Mermaid diagram

6. Verify artifacts appear in treeview under Assumptions and Artifacts nodes
7. Click artifacts to view content

## Success Criteria

- Slash commands detected in DAS chat
- OpenAI generates refined assumptions, white papers, and diagrams
- Artifacts stored in MinIO + PostgreSQL
- Treeview displays Assumptions and Artifacts nodes
- Click assumption shows content (hover or modal)
- Click artifact opens/downloads file
- Demo-ready by Thursday

## Future Enhancements

Potential DAS Actions for future implementation (to be tracked in GitHub issues):

### High Priority

- **`/summarize`** - Thread compression: Summarize old messages to reduce context size and API costs. Compresses N older messages into a summary while keeping recent messages in full. [Issue #43](https://github.com/laserpointlabs/ODRAS/issues/43)
- **`/decision [text]`** - Decision capture: Similar to assumptions but for key decisions made during discussions
- **`/requirements`** - Extract formal requirements in MIL-STD format (SP-001, SP-002, etc.)

### Medium Priority

- **`/risks`** - Extract and categorize risks mentioned in discussions
- **`/action_items`** - Extract action items with owners and due dates
- **`/planning`** - Generate interactive todo list in DAS dock (like Cursor's todo system)
- **`/ontology_proposal`** - Suggest OWL classes and properties from technical discussions

### Nice to Have

- **`/bpmn_workflow`** - Generate BPMN process diagrams from workflow discussions
- **`/test_plan`** - Generate test cases from requirements discussions
- **`/timeline`** - Generate project timeline/Gantt chart
- **`/export`** - Export conversation as PDF report

### To-dos

- [ ] Add project_assumptions table to backend/odras_schema.sql and create migration script
- [ ] Create backend/services/artifact_generator.py with OpenAI integration for assumptions, white papers, and diagrams
- [ ] Modify backend/services/das2_core_engine.py to detect slash commands and route to handlers
- [ ] Implement command handlers in das2_core_engine.py for /assumption, /white_paper, and /diagram
- [ ] Add assumptions endpoints to backend/api/das2.py for save and retrieval
- [ ] Update frontend/app.html refreshTree() to fetch and display Assumptions and Artifacts nodes
- [ ] Test end-to-end with das_service account: conversation → commands → artifacts in tree