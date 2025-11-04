# Multi-Agent Coding Teams for Offline Development

This guide explains how to set up multiple LLM agents working together to code offline, leveraging Continue.dev's file manipulation capabilities and ODRAS's existing team-based architecture.

> **Philosophy**: This guide follows the [amplified developers](https://amplified.dev/) principle: developers should be **amplified, not automated**. We build AI systems that empower developers, not replace them.

## 🎯 Amplified Developers Principles

Based on [amplified.dev](https://amplified.dev/), successful AI software development systems follow five core principles:

1. **Architecture of Participation** - Developers actively improve the system
2. **Right Models for the Job** - Use specialized models for different tasks
3. **Measure and Improve** - Track metrics and iterate on improvements
4. **Standardize Permissions** - Clear data flow and security practices
5. **Open-Source Interfaces** - Avoid vendor lock-in, enable ecosystem growth

This guide aligns with these principles for building effective offline coding teams.

## ✅ Continue.dev CRUD Capabilities

**Yes, Continue.dev can fully manipulate files:**

### Supported Operations

1. **Create Files & Directories**
   - Generate new files from scratch
   - Create directory structures
   - Initialize projects

2. **Read & Analyze Files**
   - Read existing codebases
   - Analyze code patterns
   - Understand project structure

3. **Update/Edit Files**
   - Modify existing code
   - Refactor codebases
   - Implement features across files

4. **Delete Files**
   - Remove unused files
   - Clean up codebases
   - Manage file structure

5. **Terminal Commands**
   - Run git commands
   - Execute build scripts
   - Run tests
   - Manage dependencies

6. **Multi-File Operations**
   - Implement features spanning multiple files
   - Maintain consistency across codebase
   - Coordinate changes

### Example: Continue.dev Agent Mode

```yaml
# Continue.dev config.yaml
name: odras-development
version: 0.0.1
schema: v1

models:
  - name: DeepSeek Coder 33B
    provider: ollama
    model: deepseek-coder:33b
    roles:
      - chat
      - edit
      - apply  # Enables file operations!
    defaultCompletionOptions:
      temperature: 0.7
```

**Agent Mode Features**:
- ✅ Create new files and directories
- ✅ Implement features across multiple files
- ✅ Execute terminal commands
- ✅ Refactor existing code
- ✅ Work through complex, multi-step implementations
- ✅ All operations work **completely offline**

## 👥 Building a Team of Coding Agents

ODRAS already implements a team-based approach with `LLMTeam`. Here's how to extend this for offline development following the **"Right Models for the Job"** principle from [amplified.dev](https://amplified.dev/).

### AI Software Development System Components

According to [amplified.dev](https://amplified.dev/), modern AI dev systems use multiple specialized components:

#### 1. **Autocomplete Model** (1-15B parameters)
- **Purpose**: Code completion suggestions
- **Latency**: < 500ms
- **Models**: CodeGemma, Code Llama, DeepSeek Coder Base, StarCoder 2
- **For ODRAS**: Use `deepseek-coder:1.3b` or `deepseek-coder:6.7b` for fast completions

#### 2. **Chat Model** (30B+ parameters)
- **Purpose**: Question-answer, complex reasoning
- **Latency**: Less critical (seconds acceptable)
- **Models**: GPT-4, DeepSeek Coder 33B, Claude 3, Llama 3 70B
- **For ODRAS**: Use `deepseek-coder:33b` or `llama3.1:70b` for architecture discussions

#### 3. **Local Context Engine**
- **Purpose**: Gather relevant context from codebase
- **Technologies**: Embeddings, full-text search, LSP
- **For ODRAS**: Leverage Qdrant vector search, Neo4j relationships

#### 4. **Remote Context Engine** (for larger orgs)
- **Purpose**: Shared index across all codebases
- **Technologies**: Embeddings, centralized index
- **For ODRAS**: Can extend current RAG system

#### 5. **Filtering Component**
- **Purpose**: Block low-quality, insecure, or licensing-problematic suggestions
- **For ODRAS**: Add validation before accepting suggestions

### ODRAS's Existing LLMTeam Architecture

ODRAS uses **multiple personas** that work together:

```python
# From backend/services/llm_team.py
personas = [
    ("Extractor", "You extract ontology-grounded entities from requirements."),
    ("Reviewer", "You validate and correct extracted JSON to fit the schema strictly.")
]
```

Each persona:
1. Processes the same input with different system prompts
2. Produces independent results
3. Results are merged using voting/consensus

### Extended Multi-Agent Team for Coding

Build a **specialized coding team** for ODRAS development following the **"Right Models for the Job"** principle. Each agent uses the optimal model size and type for its specific role:

#### Team Structure

```python
coding_team_personas = [
    {
        "name": "Architect",
        "role": "system_design",
        "system_prompt": """You are a senior software architect specializing in FastAPI, 
        multi-database systems, and service-oriented architectures. You design 
        high-level system structures and API contracts.""",
        "model": "llama3.1:70b",  # Best for architecture
    },
    {
        "name": "Implementer",
        "role": "code_generation",
        "system_prompt": """You are an expert Python developer specializing in FastAPI, 
        async/await patterns, and ODRAS service architecture. You write clean, 
        production-ready code following ODRAS patterns.""",
        "model": "deepseek-coder:33b",  # Best for coding
    },
    {
        "name": "Reviewer",
        "role": "code_review",
        "system_prompt": """You are a senior code reviewer. You check code quality, 
        identify bugs, ensure proper error handling, verify database connection patterns, 
        and enforce ODRAS coding standards.""",
        "model": "deepseek-coder:33b",
    },
    {
        "name": "Tester",
        "role": "test_generation",
        "system_prompt": """You are a test engineer specializing in integration tests 
        for ODRAS. You write comprehensive tests for FastAPI endpoints, database 
        services, and multi-database interactions.""",
        "model": "deepseek-coder:6.7b",  # Fast for test generation
    },
    {
        "name": "Documenter",
        "role": "documentation",
        "system_prompt": """You create clear, comprehensive documentation following 
        ODRAS documentation standards. You write docstrings, API docs, and architecture 
        explanations.""",
        "model": "qwen2.5-coder:7b",  # Good for documentation
    }
]
```

## 🛠️ Setup: Multi-Agent Team with Continue.dev

### Step 1: Configure Multiple Models

With 64GB VRAM, you can run multiple models simultaneously:

```bash
# Install primary models
ollama pull deepseek-coder:33b    # For coding
ollama pull llama3.1:70b          # For architecture
ollama pull deepseek-coder:6.7b    # For quick tasks
ollama pull qwen2.5-coder:7b      # For RAG/docs
```

### Step 2: Continue.dev Multi-Model Configuration

Create `~/.continue/config.json` or `.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Architect (Llama 3.1 70B)",
      "provider": "ollama",
      "model": "llama3.1:70b",
      "apiBase": "http://localhost:11434",
      "roles": ["chat", "edit", "apply"],
      "systemMessage": "You are a senior software architect specializing in FastAPI and multi-database systems."
    },
    {
      "title": "Implementer (DeepSeek Coder 33B)",
      "provider": "ollama",
      "model": "deepseek-coder:33b",
      "apiBase": "http://localhost:11434",
      "roles": ["chat", "edit", "apply"],
      "systemMessage": "You are an expert Python developer specializing in FastAPI and async patterns."
    },
    {
      "title": "Reviewer (DeepSeek Coder 33B)",
      "provider": "ollama",
      "model": "deepseek-coder:33b",
      "apiBase": "http://localhost:11434",
      "roles": ["chat", "edit", "apply"],
      "systemMessage": "You are a senior code reviewer checking quality, bugs, and ODRAS standards."
    },
    {
      "title": "Tester (DeepSeek Coder 6.7B)",
      "provider": "ollama",
      "model": "deepseek-coder:6.7b",
      "apiBase": "http://localhost:11434",
      "roles": ["chat", "edit", "apply"],
      "systemMessage": "You write comprehensive integration tests for ODRAS FastAPI endpoints."
    }
  ],
  "defaultModel": "deepseek-coder:33b"
}
```

### Step 3: Workflow: Multi-Agent Collaboration

#### Scenario: Implementing a New FastAPI Endpoint

1. **Architect designs the endpoint**:
   ```
   [Switch to Architect model]
   "Design a FastAPI async endpoint for requirement validation that:
   - Uses DatabaseService from backend.services.db
   - Validates against Neo4j ontology
   - Returns structured JSON response
   - Includes proper error handling"
   ```

2. **Implementer writes the code**:
   ```
   [Switch to Implementer model]
   "Implement the endpoint designed by Architect in backend/api/requirements.py"
   ```

3. **Reviewer checks the code**:
   ```
   [Switch to Reviewer model]
   "Review the new endpoint in backend/api/requirements.py for:
   - Error handling
   - Database connection patterns
   - ODRAS coding standards"
   ```

4. **Tester writes tests**:
   ```
   [Switch to Tester model]
   "Write integration tests for the new endpoint in tests/api/test_requirements.py"
   ```

5. **Documenter writes docs**:
   ```
   [Switch to Documenter model]
   "Document the new endpoint following ODRAS documentation standards"
   ```

## 🔄 Automated Team Workflow Script

Create a script to automate multi-agent collaboration:

```python
# scripts/multi_agent_workflow.py
#!/usr/bin/env python3
"""
Automated multi-agent coding workflow for ODRAS development.
Each agent handles a specific task and passes results to the next.
"""

import asyncio
import httpx
from typing import Dict, List, Any

class CodingTeam:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.agents = {
            "architect": {
                "model": "llama3.1:70b",
                "prompt": "You are a senior software architect..."
            },
            "implementer": {
                "model": "deepseek-coder:33b",
                "prompt": "You are an expert Python developer..."
            },
            "reviewer": {
                "model": "deepseek-coder:33b",
                "prompt": "You are a senior code reviewer..."
            },
            "tester": {
                "model": "deepseek-coder:6.7b",
                "prompt": "You write comprehensive integration tests..."
            }
        }
    
    async def architect_design(self, requirement: str) -> Dict[str, Any]:
        """Architect designs the solution."""
        return await self._call_agent("architect", f"""
        Design a solution for: {requirement}
        
        Provide:
        1. High-level architecture
        2. API structure
        3. Database interactions needed
        4. Error handling strategy
        """)
    
    async def implementer_code(self, design: Dict[str, Any], target_file: str) -> str:
        """Implementer writes the code."""
        return await self._call_agent("implementer", f"""
        Based on this design:
        {design}
        
        Implement the code in {target_file} following ODRAS patterns:
        - Use DatabaseService from backend.services.db
        - Include proper async/await patterns
        - Follow FastAPI best practices
        """)
    
    async def reviewer_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Reviewer checks the code."""
        return await self._call_agent("reviewer", f"""
        Review this code in {file_path}:
        {code}
        
        Check for:
        - Code quality issues
        - Bugs or potential errors
        - ODRAS coding standards compliance
        - Error handling completeness
        """)
    
    async def tester_write_tests(self, code: str, file_path: str) -> str:
        """Tester writes tests."""
        return await self._call_agent("tester", f"""
        Write integration tests for this code:
        {code}
        
        Test file: tests/api/test_{file_path.split('/')[-1].replace('.py', '.py')}
        Use das_service credentials for testing.
        """)
    
    async def _call_agent(self, agent_name: str, prompt: str) -> Any:
        """Call a specific agent."""
        agent = self.agents[agent_name]
        url = f"{self.ollama_url}/v1/chat/completions"
        payload = {
            "model": agent["model"],
            "messages": [
                {"role": "system", "content": agent["prompt"]},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            return response.json()["choices"][0]["message"]["content"]

# Usage
async def main():
    team = CodingTeam()
    
    # 1. Architect designs
    design = await team.architect_design(
        "New endpoint to validate requirements against ontology"
    )
    
    # 2. Implementer codes
    code = await team.implementer_code(
        design, 
        "backend/api/requirements.py"
    )
    
    # 3. Reviewer checks
    review = await team.reviewer_check(
        code, 
        "backend/api/requirements.py"
    )
    
    # 4. Tester writes tests
    tests = await team.tester_write_tests(
        code, 
        "backend/api/requirements.py"
    )
    
    print("✅ Multi-agent workflow complete!")
    print(f"Design: {design[:200]}...")
    print(f"Code: {code[:200]}...")
    print(f"Review: {review[:200]}...")
    print(f"Tests: {tests[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🎯 Continue.dev Agent Mode Workflow

### Enable Agent Mode in Continue.dev

1. **Open Continue.dev** in VS Code
2. **Start Agent Mode**: `Cmd/Ctrl + Shift + P` → "Continue: Start Agent"
3. **Give task**:
   ```
   "Create a new FastAPI endpoint for requirement validation:
   1. Design the endpoint structure (as Architect)
   2. Implement the code (as Implementer)
   3. Review the code (as Reviewer)
   4. Write tests (as Tester)
   "
   ```

4. **Continue.dev will**:
   - Create necessary files
   - Write code across multiple files
   - Run terminal commands
   - Execute tests
   - All completely offline!

### Agent Mode Capabilities

**What Continue.dev agents can do**:
- ✅ Navigate codebase
- ✅ Read existing files
- ✅ Create new files and directories
- ✅ Edit multiple files simultaneously
- ✅ Run terminal commands
- ✅ Execute tests
- ✅ Commit to git (if configured)
- ✅ Work through multi-step tasks

**Example Agent Task**:
```
"I need to refactor the DatabaseService to use connection pooling.
1. Analyze current implementation
2. Design pooling strategy
3. Implement changes
4. Update all callers
5. Write tests
6. Update documentation"
```

The agent will:
1. Read `backend/services/db.py`
2. Analyze connection patterns
3. Implement pooling
4. Update all files that use DatabaseService
5. Write tests
6. Update docs

## 📊 Multi-Agent Performance with 64GB VRAM

### Optimal Setup

Run multiple models simultaneously:

```bash
# Preload all models
ollama run llama3.1:70b "ready"        # ~40GB (Architect)
ollama run deepseek-coder:33b "ready"   # ~24GB (Implementer/Reviewer)
ollama ps  # Verify both loaded (~64GB total)
```

**Workflow**:
1. Architect uses 70B model (already loaded)
2. Implementer uses 33B model (already loaded)
3. Reviewer uses same 33B model (instant switch)
4. Tester can use 6.7B (loads quickly if needed)

**Response Times**:
- First request per model: 20-40s (loading)
- Subsequent requests: 5-15s (already in VRAM)
- Model switching: Near-instant (if preloaded)

## 🔒 Privacy & Security Benefits

### Offline Multi-Agent Teams

**Advantages**:
- ✅ **Complete privacy** - All processing local
- ✅ **No data leaks** - Nothing leaves your machine
- ✅ **Secure environments** - Works in air-gapped networks
- ✅ **No API costs** - Run unlimited iterations
- ✅ **Customizable** - Define your own agents

### Team Coordination

**Strategies**:
1. **Sequential** - Agents work in order (Architect → Implementer → Reviewer)
2. **Parallel** - Multiple agents work simultaneously (Reviewer + Tester)
3. **Consensus** - Multiple agents vote on decisions (like ODRAS LLMTeam)
4. **Specialized** - Each agent handles specific domains (FastAPI, Neo4j, Qdrant)

## 🎓 Best Practices (Aligned with Amplified Developers)

Based on [amplified.dev](https://amplified.dev/), here are best practices for building effective multi-agent coding teams:

### 1. Architecture of Participation

**Principle**: Developers actively improve the AI system, not just use it.

**Implementation**:
- ✅ **Define Clear Agent Roles** - Each agent has specific expertise (architecture, coding, testing)
- ✅ **Enable Contribution** - Developers can add new agents, modify prompts, improve workflows
- ✅ **Feedback Loops** - When agents produce bad suggestions, developers can fix and improve
- ✅ **Share Knowledge** - Team members share effective prompts, agent configurations, workflows

**ODRAS Example**:
```python
# Developers can customize personas
custom_personas = [
    {
        "name": "ODRAS Specialist",
        "system_prompt": "You are an ODRAS expert. Follow patterns from backend/services/db.py...",
        "is_active": True
    }
]
```

### 2. Right Models for the Job

**Principle**: Use specialized models optimized for specific tasks.

**Implementation** (from [amplified.dev](https://amplified.dev/)):
- ✅ **Autocomplete Model** (1-15B): `deepseek-coder:1.3b` for < 500ms completions
- ✅ **Chat Model** (30B+): `deepseek-coder:33b` or `llama3.1:70b` for complex reasoning
- ✅ **Specialized Models**: Different agents use different models based on their role
- ✅ **Model Comparison**: Track which models perform best for which tasks

**ODRAS Implementation**:
```python
# Each agent uses optimal model for its task
AGENT_MODELS = {
    "architect": "llama3.1:70b",      # Complex reasoning
    "implementer": "deepseek-coder:33b",  # Code generation
    "reviewer": "deepseek-coder:33b",     # Code analysis
    "tester": "deepseek-coder:6.7b",     # Fast test generation
}
```

### 3. Measure and Improve System Metrics

**Principle**: Collect development data and track KPIs to improve the system over time.

**Implementation**:
- ✅ **Development Data Collection**: Track step-by-step agent actions, context used, reasoning
- ✅ **KPIs to Track**:
  - Agent suggestion acceptance rate
  - Time saved vs. manual coding
  - Code quality metrics (linting, tests)
  - Developer satisfaction
- ✅ **Dashboards**: Visualize system usage and performance
- ✅ **Continuous Improvement**: Use data to refine agents, prompts, workflows

**ODRAS Metrics Example**:
```python
# Track agent performance
agent_metrics = {
    "architect": {
        "suggestions_made": 150,
        "accepted": 120,
        "rejected": 30,
        "acceptance_rate": 0.8,
        "avg_time_to_complete": 45.2
    },
    "implementer": {
        "files_created": 45,
        "files_modified": 120,
        "tests_passing": 0.95,
        "code_quality_score": 8.5
    }
}
```

### 4. Standardize Permissions and Integrations

**Principle**: Clear data flow, security practices, and integration standards.

**Implementation**:
- ✅ **Context Integration**: Allow codebase, docs, Jira tickets as context
- ✅ **Write Actions**: Enable agents to create tickets, update docs (with permissions)
- ✅ **Centralized Tokens**: Manage API keys, model access centrally
- ✅ **Principle of Least Privilege**: Agents only access what they need

**ODRAS Integration Points**:
```python
# Standardized integrations
INTEGRATIONS = {
    "codebase": "Qdrant + Neo4j vector search",
    "documentation": "Local docs/ directory",
    "requirements": "PostgreSQL + Fuseki",
    "issues": "GitHub Issues API (future)",
    "permissions": "ODRAS user roles"
}
```

### 5. Open-Source Interfaces

**Principle**: Use open-source interfaces to avoid vendor lock-in and enable ecosystem growth.

**Implementation**:
- ✅ **Continue.dev**: Open-source IDE extension interface
- ✅ **Ollama**: Open-source model serving
- ✅ **ODRAS Components**: Modular, swappable components
- ✅ **Standard Protocols**: OpenAI-compatible API, LSP

**ODRAS Alignment**:
- Continue.dev (open-source) as IDE interface
- Ollama (open-source) for local models
- Modular architecture allows swapping components
- No vendor lock-in - can switch models, interfaces, components

### 6. Establish Communication Patterns

- **Shared context files** - Agents read/write to shared workspace
- **Explicit handoffs** - One agent completes before next starts
- **Results documentation** - Each agent documents its work

### 7. Version Control Integration

- Agents commit their work
- Clear commit messages indicating agent role
- Easy rollback if agent makes mistakes

### 8. Quality Gates

- Reviewer must approve before proceeding
- Tests must pass before moving forward
- Documentation must be complete

## 🔮 Future Components (From Amplified.dev)

As AI dev systems evolve, expect these components to emerge:

### Async Engines (Reasoning, Planning, Proactive)

**Coming Soon** - Enable agents to handle multi-step tasks:

1. **Reasoning**: Complex problem-solving across multiple steps
   - Projects: SWE-Agent, Devin
   - Research: OpenAI and labs working in this direction

2. **Planning**: Workflow execution in task environments
   - Examples: Code Interpreter, OpenInterpreter, e2b.dev sandboxes
   - Includes: Shell, code editor, browser in sandboxed environment

3. **Proactive**: Agents ask for help when stuck, offer support before asked
   - Reduces developer notifications
   - Balances autonomy with human oversight

**For ODRAS**: Consider integrating reasoning engines for complex ontology-driven analysis tasks.

### Training Engines

**Enable continuous improvement** using your development data:

1. **Fine-tuning** (Near-term):
   - Requires: Domain-specific instruction data, hundreds of GPU hours
   - Benefit: Shape style/format for your organization
   - Examples: smol.ai, Arcee (continuous process)

2. **Domain Adaptive Pre-training** (Medium-term):
   - Requires: Open-source base, billions of tokens, thousands of GPU hours
   - Benefit: More control over model capabilities
   - Examples: ChipNeMo (Nvidia), Code Llama (Meta)

3. **Pre-training from Scratch** (Long-term):
   - Requires: Trillions of tokens, millions of GPU hours
   - Benefit: Complete control over capabilities
   - Vendors: OpenAI custom models ($2-3M), MosaicML, Together

**For ODRAS**: Start collecting development data now for future fine-tuning opportunities.

### Trends: Specialized Models

Vendors are creating models for specific use cases:
- **Cursor**: Predict next edit
- **Phind**: GPT-4 quality, faster
- **Replit**: LSP Code Actions behavior
- **Magic**: Entire codebase as context
- **Poolside**: Real-world use cases

**For ODRAS**: Consider domain-specific models for requirements analysis, ontology processing.

## 📚 Resources

- [Amplified Developers Manifesto](https://amplified.dev/) - Core philosophy and principles
- [Continue.dev Agent Mode Docs](https://docs.continue.dev/guides/agent-mode)
- [ODRAS LLMTeam Implementation](backend/services/llm_team.py)
- [Multi-Agent Workflow Script](scripts/task_llm_processing.py)
- [ODRAS Architecture](docs/architecture/)

---

## 🚀 Quick Start

```bash
# 1. Install Continue.dev
code --install-extension Continue.continue

# 2. Configure multiple models (see config above)

# 3. Preload models
ollama run llama3.1:70b "ready"
ollama run deepseek-coder:33b "ready"

# 4. Start Agent Mode in Continue.dev
# 5. Give it a complex task spanning multiple files
# 6. Watch your coding team work! 🎉
```

**Your offline coding team is ready!**

---

## 🎯 Amplified Developers Philosophy

> "When a new tool enters your workflow, it changes how you think. As software development is increasingly automated, we need to be able to shape AI software development systems, so that we can shape how we think."
>
> — [amplified.dev](https://amplified.dev/)

**Key Takeaways**:
- ✅ **Developers are amplified, not automated** - AI should enhance, not replace
- ✅ **Shape the system** - Actively participate in building and improving AI dev tools
- ✅ **Right foundation** - Set up for long-term success with modular, measurable systems
- ✅ **Open ecosystem** - Avoid vendor lock-in, enable innovation

ODRAS's multi-agent approach aligns with this philosophy: developers control the agents, define the workflows, and continuously improve the system based on their needs and feedback.
