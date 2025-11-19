# Local LLM Quick Reference for ODRAS

## 🚀 Quick Start

### Option 1: Continue.dev (Local-Only, No Proxy!) ⭐

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Install Continue.dev VS Code extension
code --install-extension Continue.continue

# 3. Install model
ollama pull deepseek-coder:6.7b

# 4. Configure Continue.dev:
#    - Model provider: Ollama
#    - Endpoint: http://localhost:11434
#    - Model: deepseek-coder:6.7b
# ✅ Works offline, no proxy needed!
```

### Option 2: Cursor v2 (Requires Proxy)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Try local IP first (may work):
#    - Configure Ollama: export OLLAMA_HOST=0.0.0.0:11434
#    - Use your local IP in Cursor settings

# 3. If that doesn't work, use Cloudflare Tunnel (better than ngrok):
cloudflared tunnel --url http://localhost:11434
# Copy the *.cfargotunnel.com URL

# 4. Or use ngrok:
ngrok http 11434
# Copy the HTTPS URL

# 5. Install model
ollama pull deepseek-coder:6.7b

# 6. Configure Cursor with proxy URL
```

> 💡 **For local-only**: Use **Continue.dev** instead - it works directly with `localhost`!

## 📦 Model Recommendations

### For 64GB+ VRAM (High-End Setup):
| Use Case | Model | Size | VRAM | Speed | Quality |
|----------|-------|------|------|-------|---------|
| **Best for Coding** | `deepseek-coder:33b` | 33B | 24GB | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| **Best for Architecture** | `llama3.1:70b` | 70B | 40GB | ⚡ | ⭐⭐⭐⭐⭐ |
| **Quick Iterations** | `deepseek-coder:6.7b` | 6.7B | 8GB | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| **RAG Focus** | `qwen2.5-coder:7b` | 7B | 8GB | ⚡⚡ | ⭐⭐⭐⭐ |

**Recommended**: Install both 33B + 70B, can run simultaneously (~64GB total)

### For Standard Setup (8-16GB VRAM):
| Use Case | Model | Size | VRAM | Speed |
|----------|-------|------|------|-------|
| **Best Overall** | `deepseek-coder:6.7b` | 6.7B | 8GB | ⚡⚡ |
| Fast Iterations | `deepseek-coder:1.3b` | 1.3B | 2GB | ⚡⚡⚡ |
| RAG Focus | `qwen2.5-coder:7b` | 7B | 8GB | ⚡⚡ |

## ⚙️ Cursor Configuration

> ⚠️ **Use ngrok HTTPS URL**, NOT `localhost`!

### Method 1: UI Settings
1. Start ngrok: `ngrok http 11434` (keep terminal open)
2. Copy HTTPS URL (e.g., `https://abc123.ngrok-free.app`)
3. `Cmd/Ctrl + Shift + P` → "Preferences: Open Settings"
4. Search: "Custom OpenAI API" or "AI Model"
5. Set endpoint: `https://abc123.ngrok-free.app/v1`
6. Set model: `deepseek-coder:6.7b`

### Method 2: Settings JSON
1. `Cmd/Ctrl + Shift + P` → "Preferences: Open User Settings (JSON)"
2. Add:
```json
{
  "cursor.localLLM.enabled": true,
  "cursor.localLLM.endpoint": "http://localhost:11434",
  "cursor.localLLM.model": "deepseek-coder:6.7b"
}
```

## 🧪 Test Commands

```bash
# Check Ollama status
ollama list
ollama ps
curl http://localhost:11434/api/tags

# Test model
ollama run deepseek-coder:6.7b "Explain FastAPI async patterns"

# Test ODRAS-specific
ollama run deepseek-coder:6.7b \
  "Write a FastAPI endpoint using DatabaseService from backend.services.db"
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Cursor v2 requires proxy** | Install ngrok: `ngrok http 11434`, use HTTPS URL in Cursor |
| ngrok URL changed | Free URLs change on restart - update Cursor settings |
| Model slow | Use smaller model (1.3b instead of 6.7b) |
| Out of memory | Use `deepseek-coder:1.3b` or reduce GPU layers |
| Ollama not found | Install: `curl -fsSL https://ollama.com/install.sh \| sh` |
| Connection failed | Test: `curl https://your-ngrok-url.ngrok-free.app/api/tags` |
| Cursor not connecting | Use ngrok HTTPS URL, not `localhost`, restart Cursor |
| ngrok disconnects | Keep ngrok terminal open, or use systemd service |

## 📝 ODRAS-Specific Prompts

### FastAPI Endpoint
```
Write a FastAPI async endpoint for [feature] that:
- Uses DatabaseService from backend.services.db
- Includes error handling and logging
- Follows ODRAS service patterns
```

### Database Service
```
Create a service in backend/services/ that:
- Connects to [PostgreSQL/Neo4j/Qdrant]
- Uses existing patterns from backend/services/db.py
- Includes proper error handling
```

### RAG Implementation
```
Implement RAG using:
- Qdrant collections: knowledge_chunks, knowledge_large
- Sentence transformers for embeddings
- BPMN workflow (not hard-coded)
```

## 📚 Files Created

- **Setup Guide**: `docs/development/LOCAL_LLM_SETUP.md` - Full guide
- **Quick Reference**: `docs/development/LOCAL_LLM_QUICKREF.md` - This file
- **Setup Script**: `scripts/setup_local_llm.sh` - Automated setup

## 🎯 Recommended Workflow

### For 64GB VRAM:
1. **Preload models in morning**: `ollama run deepseek-coder:33b 'ready' && ollama run llama3.1:70b 'ready'`
2. **Use 33B for coding**: Code generation, refactoring, FastAPI endpoints
3. **Use 70B for architecture**: System design, complex debugging, multi-database planning
4. **Switch models in Cursor**: `Cmd/Ctrl + Shift + P` → "Change AI Model"

### For Standard Setup:
1. **Start with local model** for quick iterations
2. **Use cloud model** (GPT-4) for complex architecture decisions
3. **Hybrid approach** works best:
   - Local: Code completion, refactoring, small changes
   - Cloud: System design, architecture, complex debugging

## 💡 Pro Tips

- **For local-only**: Use **Continue.dev** - no proxy needed!
- **Smaller context** = faster responses
- **Point to files**: "See `backend/services/db.py`"
- **Iterative**: Ask for small focused changes
- **Test frequently**: Verify suggestions work
- **Combine models**: Use both local and cloud

## 🆓 Local-Only Alternative: Continue.dev

If you want **true local-only** (no internet, no proxy):

1. Install: `code --install-extension Continue.continue`
2. Configure: Ollama → `http://localhost:11434`
3. Use: Same as Cursor, but works directly with localhost

**Benefits**:
- ✅ No proxy/tunnel needed
- ✅ Works completely offline
- ✅ Better privacy (no routing through servers)
- ✅ Simpler setup
- ✅ **Full CRUD capabilities** (create, edit, delete files)
- ✅ **Multi-agent teams** - multiple LLMs working together
- ✅ **Terminal commands** - can run git, tests, builds

**See**: [Multi-Agent Coding Teams Guide](MULTI_AGENT_CODING_TEAMS.md) for building a team of coding agents offline.

---

**Full Documentation**: See `docs/development/LOCAL_LLM_SETUP.md`
