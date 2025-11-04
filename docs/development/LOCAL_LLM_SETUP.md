# Local LLM Setup for ODRAS Development

This guide helps you configure Cursor to use local LLMs for offline development of ODRAS.

## 🎯 Recommended Models for ODRAS Development

Based on ODRAS's tech stack (Python/FastAPI, multi-database, RAG, ontology processing), here are the best local models:

### **Top Recommendations (Priority Order)**

#### 1. **DeepSeek Coder V2** ⭐ Best Choice
- **Models**: `deepseek-coder-1.3b`, `deepseek-coder-6.7b`, `deepseek-coder-33b`
- **Why**: Excellent Python code understanding, FastAPI patterns, async/await handling
- **Size**: 1.3B (fastest), 6.7B (balanced), 33B (best quality)
- **Speed**: ⚡⚡⚡ (1.3B) / ⚡⚡ (6.7B) / ⚡ (33B)
- **GPU VRAM**: 2GB / 8GB / 24GB
- **Best for**: Python/FastAPI development, service architecture, database code

#### 2. **Qwen2.5 Coder**
- **Models**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`, `Qwen/Qwen2.5-Coder-7B-Instruct`
- **Why**: Strong coding capabilities, good RAG understanding, multi-database support
- **Size**: 1.5B or 7B
- **Speed**: ⚡⚡⚡ (1.5B) / ⚡⚡ (7B)
- **GPU VRAM**: 2GB / 8GB
- **Best for**: Complex system architecture, RAG implementations

#### 3. **CodeLlama 2**
- **Models**: `codellama/CodeLlama-7b-Instruct-hf`, `codellama/CodeLlama-13b-Instruct-hf`
- **Why**: Specifically designed for code generation, understands Python well
- **Size**: 7B or 13B
- **Speed**: ⚡⚡ (7B) / ⚡ (13B)
- **GPU VRAM**: 8GB / 16GB
- **Best for**: Code completion, refactoring, debugging

#### 4. **Llama 3.1**
- **Models**: `meta-llama/Meta-Llama-3.1-8B-Instruct`, `meta-llama/Meta-Llama-3.1-70B-Instruct`
- **Why**: Good general reasoning, handles complex architecture questions
- **Size**: 8B (recommended) or 70B (if you have VRAM)
- **Speed**: ⚡⚡ (8B) / ⚡ (70B)
- **GPU VRAM**: 10GB / 40GB+
- **Best for**: Architecture planning, system design discussions

### **Model Selection Matrix**

| Model | Python Code | FastAPI | Databases | RAG | Speed | VRAM |
|-------|------------|---------|-----------|-----|-------|------|
| DeepSeek Coder 6.7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⚡⚡ | 8GB |
| Qwen2.5 Coder 7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | 8GB |
| CodeLlama 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⚡⚡ | 8GB |
| Llama 3.1 8B | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⚡⚡ | 10GB |

**Recommendation for ODRAS**: Start with **DeepSeek Coder 6.7B** for best balance of speed and quality.

### **High-VRAM Setup (64GB+ VRAM)** 🚀

With 64GB VRAM, you can run **multiple large models simultaneously** for different tasks:

#### **Maximum Quality Models (Recommended for 64GB)**

1. **DeepSeek Coder V2 33B** ⭐⭐⭐⭐⭐
   - **Model**: `deepseek-coder:33b`
   - **VRAM**: ~24GB
   - **Why**: Best code understanding, excellent Python/FastAPI patterns
   - **Use for**: Complex architecture, critical code reviews, system design

2. **Llama 3.1 70B** ⭐⭐⭐⭐⭐
   - **Model**: `llama3.1:70b`
   - **VRAM**: ~40GB
   - **Why**: Outstanding reasoning, handles complex ODRAS architecture questions
   - **Use for**: Architecture planning, system design, complex debugging

3. **Qwen2.5 Coder 32B** (if available)
   - **VRAM**: ~32GB
   - **Why**: Excellent RAG understanding, multi-database expertise
   - **Use for**: RAG implementations, knowledge base work

4. **CodeLlama 34B**
   - **Model**: `codellama:34b` (check availability)
   - **VRAM**: ~28GB
   - **Why**: Maximum code generation quality
   - **Use for**: Large refactoring, code generation

#### **Multi-Model Configuration (Recommended Setup)**

Run **multiple models simultaneously** for different use cases:

```bash
# Primary: Maximum quality for complex tasks
ollama pull deepseek-coder:33b    # ~24GB VRAM
ollama pull llama3.1:70b          # ~40GB VRAM

# Secondary: Fast iteration models (can run alongside)
ollama pull deepseek-coder:6.7b   # ~8GB VRAM
ollama pull qwen2.5-coder:7b      # ~8GB VRAM
```

**Total VRAM usage**: 24GB + 40GB = 64GB (both models loaded)

**Multi-Model Strategy**:
- **DeepSeek Coder 33B**: Use for code generation, refactoring, complex features
- **Llama 3.1 70B**: Use for architecture questions, system design, debugging
- **DeepSeek Coder 6.7B**: Keep loaded for quick iterations (fastest response)
- **Qwen2.5 Coder 7B**: Use for RAG-specific tasks

#### **High-End Model Comparison**

| Model | Size | VRAM | Python Code | FastAPI | Architecture | Speed | Best Use |
|-------|------|------|------------|---------|--------------|-------|----------|
| DeepSeek Coder 33B | 33B | 24GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚡⚡ | Code generation, refactoring |
| Llama 3.1 70B | 70B | 40GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚡ | Architecture, design, debugging |
| Qwen2.5 Coder 32B | 32B | 32GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | RAG, knowledge base |
| CodeLlama 34B | 34B | 28GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | Large refactoring |

**Recommended High-VRAM Setup**:
1. **Primary**: DeepSeek Coder 33B (best for ODRAS coding tasks)
2. **Secondary**: Llama 3.1 70B (best for architecture discussions)
3. **Tertiary**: Keep 6.7B models loaded for fast iterations

## 🛠️ Setup Instructions

### Prerequisites

1. **Check GPU Availability**:
```bash
# Check if you have NVIDIA GPU
nvidia-smi

# Check CUDA version
nvcc --version
```

2. **Install Ollama** (Recommended for local LLMs):
```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download
```

3. **Alternative: LM Studio** (GUI option):
   - Download from: https://lmstudio.ai
   - User-friendly interface for managing local models

### Step 1: Install Models via Ollama

#### For 64GB VRAM (High-End Setup):
```bash
# Primary models for maximum quality
ollama pull deepseek-coder:33b    # ~24GB VRAM - Best for coding
ollama pull llama3.1:70b          # ~40GB VRAM - Best for architecture

# Fast iteration models (run alongside)
ollama pull deepseek-coder:6.7b   # ~8GB VRAM - Quick code changes
ollama pull qwen2.5-coder:7b      # ~8GB VRAM - RAG-specific tasks
```

#### For Standard Setup (8-16GB VRAM):
```bash
# Install DeepSeek Coder 6.7B (recommended)
ollama pull deepseek-coder:6.7b

# Or try these alternatives:
ollama pull qwen2.5-coder:7b
ollama pull codellama:7b
ollama pull llama3.1:8b
```

#### Verify Models Installed:
```bash
ollama list
```

### Step 2: Configure Cursor for Local LLMs

> ⚠️ **IMPORTANT: Cursor v2 Connection Requirements**
> 
> **Cursor v2 routes requests through its servers**, which typically requires exposing your local LLM via a public URL. However, there are local-only alternatives you can try:
>
> ### **Try These Local-Only Methods First** (No Internet Required)
> 
> 1. **Local Network IP** - May work if Cursor can reach your network
> 2. **localhost.run** - Simple local tunnel (still requires internet briefly for setup)
> 3. **Cloudflare Tunnel** - More local than ngrok (runs locally, minimal cloud dependency)
>
> ### **If Local-Only is Critical**
> - See **[Open-Source Alternatives](#open-source-alternatives)** section below
> - Consider **Continue.dev**, **Tabby**, or **Cline** for true local-only operation

#### Option A: Direct Local Network Connection (Try First!)

**This may work** depending on your Cursor version and network setup:

1. **Find your local IP address**:
```bash
# Linux/WSL
hostname -I | awk '{print $1}'

# macOS
ipconfig getifaddr en0

# Output: e.g., 192.168.1.100
```

2. **Configure Ollama to listen on all interfaces**:
```bash
# Set environment variable before starting Ollama
export OLLAMA_HOST=0.0.0.0:11434

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export OLLAMA_HOST=0.0.0.0:11434' >> ~/.bashrc
```

3. **Configure Cursor** with local network IP:
   - Settings → Custom OpenAI API
   - Endpoint: `http://192.168.1.100:11434/v1` (replace with your IP)
   - Model: `deepseek-coder:6.7b`

4. **Test if it works**:
   - Try using Cursor's AI features
   - If connection errors occur, Cursor requires public exposure (see Option B)

**Note**: This may not work if Cursor v2 strictly routes through its servers. If it fails, proceed to Option B.

#### Option B: Using Cloudflare Tunnel (More Local Than ngrok)

**Cloudflare Tunnel runs locally** and feels more "local-only" than ngrok:

1. **Install Cloudflare Tunnel (cloudflared)**:
```bash
# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# macOS
brew install cloudflare/cloudflare/cloudflared
```

2. **Create tunnel** (one-time setup):
```bash
# Authenticate (opens browser)
cloudflared tunnel login

# Create tunnel (no need for Cloudflare dashboard)
cloudflared tunnel create ollama-tunnel

# Get tunnel UUID (save it)
cloudflared tunnel list
```

3. **Start tunnel**:
```bash
# Run tunnel (replace TUNNEL_UUID with your UUID)
cloudflared tunnel run ollama-tunnel

# Or use quick tunnel (no login required, but URL changes)
cloudflared tunnel --url http://localhost:11434
```

4. **Configure Cursor** with Cloudflare Tunnel URL:
   - Use the `*.cfargotunnel.com` URL shown
   - Format: `https://abc123.cfargotunnel.com/v1`

**Advantages over ngrok**:
- ✅ Runs locally on your machine
- ✅ Free persistent URLs (after one-time setup)
- ✅ No account required for quick tunnels
- ✅ Better privacy (data stays closer to you)

#### Option C: Using localhost.run (Simple Alternative)

**No account required**, works similarly to ngrok:

```bash
# Install (if not available)
# Usually pre-installed or: gem install localtunnel

# Start tunnel
ssh -R 80:localhost:11434 serveo.net

# Or use localhost.run directly
ssh -R ollama:80:localhost:11434 localhost.run
```

**Note**: Still requires internet, but simpler than ngrok.

#### Option D: Using ngrok (Most Reliable)

1. **Install ngrok**:
```bash
# Linux/macOS
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

# Or download from: https://ngrok.com/download
# Or via package manager: brew install ngrok (macOS)
```

2. **Create ngrok account** (free tier works):
   - Sign up at: https://dashboard.ngrok.com/signup
   - Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken

3. **Configure ngrok**:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

4. **Start ngrok tunnel to Ollama**:
```bash
# Expose Ollama's port 11434
ngrok http 11434

# You'll see output like:
# Forwarding   https://abc123.ngrok-free.app -> http://localhost:11434
# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
```

5. **Keep ngrok running** - Leave the terminal open with ngrok running.

6. **Configure Cursor**:
   - Open Cursor Settings: `Cmd/Ctrl + Shift + P` → "Preferences: Open Settings"
   - Search for "AI Model" or "Custom OpenAI API"
   - Set **Custom API Endpoint** to your ngrok URL: `https://abc123.ngrok-free.app/v1`
   - Or use: `https://abc123.ngrok-free.app/v1/chat/completions`

7. **Test Connection**:
```bash
# Test via ngrok URL (replace with your ngrok URL)
curl https://abc123.ngrok-free.app/api/tags
```

#### Option B: Using llm-router (Alternative Proxy)

1. **Install llm-router**:
```bash
# Clone the repository
git clone https://github.com/kcolemangt/llm-router.git
cd llm-router

# Install and configure
npm install
```

2. **Configure llm-router** to point to local Ollama:
   - Edit config to use `http://localhost:11434`
   - Start the router

3. **Use llm-router URL** in Cursor settings instead of direct Ollama URL

#### Switching Between Models in Cursor

**For 64GB VRAM Setup - Multiple Model Strategy**:

1. **Use Cursor's Model Selector**:
   - `Cmd/Ctrl + Shift + P` → "Change AI Model"
   - Select from installed models:
     - `deepseek-coder:33b` - Code generation, refactoring
     - `llama3.1:70b` - Architecture, system design
     - `deepseek-coder:6.7b` - Quick iterations

2. **Or Configure Model Per Task**:
   - Create separate Cursor workspaces with different model configs
   - Use chat commands to specify model preferences

#### Option C: Using LM Studio with ngrok

1. **Launch LM Studio**
2. **Download a model** (DeepSeek Coder recommended)
3. **Start Local Server** (usually `http://localhost:1234`)
4. **Expose via ngrok**:
```bash
ngrok http 1234
# Copy the HTTPS URL (e.g., https://xyz789.ngrok-free.app)
```
5. **Configure Cursor** to use: `https://xyz789.ngrok-free.app/v1`

### Step 3: Create Cursor Configuration File

> ⚠️ **Important**: Use your **ngrok HTTPS URL**, not `localhost`!

Create or update `.cursor/config.json` in your ODRAS project:

```json
{
  "localLLM": {
    "enabled": true,
    "provider": "openai",  // Cursor uses OpenAI-compatible API
    "endpoint": "https://abc123.ngrok-free.app/v1",  // Your ngrok URL
    "apiKey": "not-needed-for-ollama",  // Ollama doesn't need API key
    "model": "deepseek-coder:6.7b",
    "fallbackToCloud": false
  },
  "context": {
    "maxTokens": 8192,
    "includePatterns": [
      "backend/**/*.py",
      "frontend/**/*.{ts,tsx}",
      "tests/**/*.py",
      "scripts/**/*.py",
      "*.md"
    ]
  }
}
```

**Note**: Replace `https://abc123.ngrok-free.app` with your actual ngrok URL.

### Step 4: Test Local LLM Setup

Create a test file to verify:

```bash
# Create test prompt
cat > test_local_llm.py << 'EOF'
# Test: Ask the local LLM about FastAPI async patterns
# Expected: Should understand FastAPI and async/await

from fastapi import FastAPI, Depends
from backend.services.db import DatabaseService

# Write an async endpoint that queries Neo4j
EOF
```

## 🔧 Advanced Configuration

### GPU Acceleration (NVIDIA)

1. **Install CUDA-enabled Ollama**:
```bash
# Check if CUDA is available
ollama show deepseek-coder:6.7b --modelfile

# Verify GPU usage
nvidia-smi  # Should show Ollama process using GPU
```

2. **Force GPU Usage**:
```bash
# Set environment variable
export OLLAMA_GPU_LAYERS=35  # Use all GPU layers
export CUDA_VISIBLE_DEVICES=0  # Use first GPU
```

### Running Multiple Models Simultaneously (64GB VRAM)

With 64GB VRAM, you can run **multiple large models at once**:

#### Strategy 1: Keep Models Loaded in Memory

Ollama will automatically manage model loading. When you request a model, it loads into VRAM. You can:

```bash
# Preload your primary models (keeps them in VRAM)
ollama run deepseek-coder:33b "Hello"  # Loads 33B model (~24GB)
ollama run llama3.1:70b "Hello"        # Loads 70B model (~40GB)

# Check loaded models
ollama ps
```

**Note**: Both models will stay in VRAM until memory pressure requires unloading.

#### Strategy 2: Multi-Ollama Instances (Advanced)

Run separate Ollama instances for different models on different ports:

```bash
# Terminal 1: Primary coding model
OLLAMA_HOST=127.0.0.1:11434 ollama serve

# Terminal 2: Architecture model (different port)
OLLAMA_HOST=127.0.0.1:11435 OLLAMA_MODELS=/path/to/models2 ollama serve

# Configure Cursor to use port 11434 for coding, 11435 for architecture
```

#### Strategy 3: Single Instance with Model Switching

Most practical approach - let Ollama manage loading/unloading automatically:

```bash
# Ollama will load models on-demand
# First request: loads model into VRAM
# Subsequent requests: uses loaded model (fast)
# If VRAM full: unloads least recently used model
```

**VRAM Management Tips**:
- **Keep 33B + 70B loaded**: ~64GB total (perfect for your setup)
- **Add 6.7B for quick tasks**: Only loads when needed, swaps out if needed
- **Monitor VRAM**: `watch -n 1 nvidia-smi` to see usage
- **Preload frequently used**: Start Ollama and make a quick request to each model

#### Recommended Multi-Model Workflow

1. **Morning Setup**:
```bash
# Preload primary models
ollama run deepseek-coder:33b "ready"
ollama run llama3.1:70b "ready"
ollama ps  # Verify both loaded (~64GB VRAM)
```

2. **During Development**:
   - Use `deepseek-coder:33b` for code changes (keep loaded)
   - Switch to `llama3.1:70b` for architecture questions (already loaded)
   - Use `deepseek-coder:6.7b` for quick iterations (loads/unloads as needed)

3. **Monitor Usage**:
```bash
# Watch VRAM in real-time
watch -n 1 nvidia-smi

# Check which models are loaded
ollama ps
```

#### Cursor Configuration for Multiple Models

Update `.cursor/config.json` with multiple model options:

```json
{
  "localLLM": {
    "enabled": true,
    "provider": "ollama",
    "endpoint": "http://localhost:11434",
    "primaryModel": "deepseek-coder:33b",
    "secondaryModel": "llama3.1:70b",
    "quickModel": "deepseek-coder:6.7b",
    "autoSwitch": true
  }
}
```

Or use Cursor's built-in model switcher (Cmd/Ctrl + Shift + P → "Change AI Model").

### CPU-Only Setup

If you don't have a GPU, models will run on CPU (slower but functional):

```bash
# Use smaller models
ollama pull deepseek-coder:1.3b  # Runs well on CPU
ollama pull qwen2.5-coder:1.5b   # CPU-friendly option
```

### Memory Optimization

For systems with limited RAM:

```bash
# Use quantization (smaller, faster models)
ollama pull deepseek-coder:6.7b-q4_0  # 4-bit quantization
ollama pull deepseek-coder:6.7b-q8_0  # 8-bit quantization (better quality)
```

## 📝 ODRAS-Specific Prompt Templates

Create prompts optimized for ODRAS development:

### Template 1: FastAPI Endpoint Development
```
You are helping develop ODRAS, an ontology-driven requirements analysis system.

Tech Stack:
- FastAPI with async/await
- Multi-database: PostgreSQL, Neo4j, Qdrant, Redis, Fuseki
- Services pattern: backend/services/
- Authentication: backend/services/auth.py

Task: [Describe the endpoint you need]
```

### Template 2: Database Service Development
```
ODRAS uses multiple databases:
- PostgreSQL: backend/services/db.py (DatabaseService)
- Neo4j: For graph relationships
- Qdrant: Vector embeddings (384/1536 dim)
- Redis: Caching
- Fuseki: SPARQL/OWL ontologies

Create a service that: [Your requirement]
```

### Template 3: RAG Implementation
```
ODRAS implements RAG using:
- Qdrant collections: knowledge_chunks, knowledge_large, odras_requirements
- Sentence transformers for embeddings
- BPMN workflows (not hard-coded pipelines)

Help implement: [Your RAG feature]
```

## 🚀 Usage Tips

### 1. Start with Smaller Context
- Local models handle smaller contexts better
- Break large files into smaller chunks
- Focus on specific functions/classes

### 2. Use Code References
- Point to specific files: "See `backend/services/db.py`"
- Reference existing patterns: "Similar to `backend/api/files.py`"

### 3. Iterative Development
- Ask for small, focused changes
- Build up complex features incrementally
- Test after each suggestion

### 4. Combine with Cloud Models
- Use local for quick iterations
- Use cloud (GPT-4) for complex architecture decisions
- Hybrid approach works best

## 🔍 Troubleshooting

### Model Not Responding
```bash
# Check Ollama status
ollama list
ollama ps

# Restart Ollama
pkill ollama
ollama serve
```

### Slow Performance
1. **Use smaller model** (1.3B or 7B instead of 33B)
2. **Enable GPU** (check `nvidia-smi`)
3. **Reduce context size** (shorter prompts)
4. **Use quantization** (q4_0 or q8_0)

### Out of Memory
```bash
# Use smaller model
ollama pull deepseek-coder:1.3b

# Or reduce GPU layers
export OLLAMA_GPU_LAYERS=20
```

### ngrok Issues (Cursor v2 Requirement)

**ngrok tunnel disconnects**:
```bash
# Check if ngrok is still running
ps aux | grep ngrok

# Restart ngrok
ngrok http 11434

# Note: Free ngrok URLs change on restart - update Cursor settings!
```

**ngrok URL changed**:
- Free ngrok URLs change every restart
- **Solution**: Use ngrok config file with static domain (paid feature) OR update Cursor settings each time

**ngrok "too many connections" error**:
- Free tier has connection limits
- **Solution**: Upgrade to paid tier OR use Cloudflare Tunnel (free alternative)

**Test ngrok connection**:
```bash
# Replace with your ngrok URL
curl https://abc123.ngrok-free.app/api/tags

# Should return Ollama model list
```

**Keep ngrok running**:
- Leave ngrok terminal open
- Or run in background: `nohup ngrok http 11434 > ngrok.log 2>&1 &`
- Or use systemd service (Linux) for auto-start

### Cursor Not Connecting
1. **Verify Ollama is running**: `curl http://localhost:11434/api/tags`
2. **Verify ngrok is running**: Check ngrok web interface at http://localhost:4040
3. **Test ngrok URL**: `curl https://your-ngrok-url.ngrok-free.app/api/tags`
4. **Check Cursor settings**: Use **ngrok HTTPS URL**, not `localhost`
5. **Check firewall**: Port 11434 should be open locally
6. **Restart Cursor** after changing settings

## 📊 Performance Benchmarks

Typical response times on modern hardware:

### Standard Models (8-16GB VRAM)

| Model | Size | GPU | Speed | Quality |
|-------|------|-----|-------|---------|
| DeepSeek Coder | 1.3B | RTX 3060 | 2-5s | ⭐⭐⭐ |
| DeepSeek Coder | 6.7B | RTX 3080 | 5-10s | ⭐⭐⭐⭐⭐ |
| Qwen2.5 Coder | 7B | RTX 3080 | 5-12s | ⭐⭐⭐⭐ |
| CodeLlama | 7B | RTX 3060 | 8-15s | ⭐⭐⭐⭐ |

### High-End Models (64GB+ VRAM)

| Model | Size | GPU | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| DeepSeek Coder | 33B | RTX 4090/A100 | 15-30s | ⭐⭐⭐⭐⭐ | Code generation, refactoring |
| Llama 3.1 | 70B | A100 (80GB) | 20-40s | ⭐⭐⭐⭐⭐ | Architecture, system design |
| Qwen2.5 Coder | 32B* | RTX 6000 Ada | 18-35s | ⭐⭐⭐⭐⭐ | RAG, knowledge base |
| CodeLlama | 34B* | RTX 4090 | 20-35s | ⭐⭐⭐⭐⭐ | Large refactoring |

*If available via Ollama

### Multi-Model Setup (64GB VRAM)

When running multiple models simultaneously:
- **33B + 70B loaded**: ~64GB VRAM usage
- **First response**: 20-40s (model loading)
- **Subsequent responses**: 5-15s (model already in VRAM)
- **Model switching**: Near-instant (if both loaded)

**Recommendation**: Preload both models in the morning for best performance.

## 🎯 Next Steps

### For 64GB VRAM Setup:

1. **Install Primary Models**:
```bash
ollama pull deepseek-coder:33b    # Best for ODRAS coding
ollama pull llama3.1:70b          # Best for architecture
```

2. **Preload Models**:
```bash
ollama run deepseek-coder:33b "ready"
ollama run llama3.1:70b "ready"
ollama ps  # Verify both loaded (~64GB VRAM)
```

3. **Configure Cursor**: Set primary model to `deepseek-coder:33b`

4. **Test ODRAS-Specific Prompts**:
   - Code generation: "Write FastAPI endpoint using DatabaseService"
   - Architecture: "Design service for multi-database RAG system"
   - RAG: "Implement Qdrant collection with sentence transformers"

5. **Set Up Multi-Model Workflow**: Use 33B for coding, 70B for architecture questions

### For Standard Setup (8-16GB VRAM):

1. **Start Simple**: Pull `deepseek-coder:6.7b` first to test setup
2. **Upgrade if Needed**: Move to 13B models if you have 16GB+ VRAM
3. **Test on ODRAS Code**: Try asking about FastAPI endpoints, database services
4. **Iterate**: Refine prompts and configuration based on results

## 🆓 Open-Source Alternatives (True Local-Only)

If you **absolutely need local-only** operation without any internet/proxy requirements, consider these open-source alternatives to Cursor:

### 1. **Continue.dev** ⭐ Recommended
- **VS Code Extension** - Works as extension, not separate app
- **True local-only** - Direct connection to Ollama, no proxies needed
- **Full-featured** - Code completion, chat, Composer-like features
- **Install**: `code --install-extension Continue.continue`
- **Website**: https://continue.dev
- **Perfect for**: ODRAS development with local models

**Quick Setup**:
```bash
# Install Continue extension in VS Code
code --install-extension Continue.continue

# Configure in Continue settings:
# - Model provider: Ollama
# - API endpoint: http://localhost:11434
# - Model: deepseek-coder:6.7b
```

### 2. **Tabby**
- **Self-hosted** - Complete control over deployment
- **Enterprise-ready** - Built for teams and organizations
- **Local-first** - Can run completely offline
- **Website**: https://tabby.sh
- **GitHub**: https://github.com/TabbyML/tabby

### 3. **Cline**
- **Autonomous coding** - Handles complex multi-step tasks
- **Local operation** - Works entirely offline
- **VS Code Extension** - Similar to Continue
- **GitHub**: https://github.com/FullHuman/cline

### 4. **Continue.dev vs Cursor for ODRAS**

| Feature | Continue.dev | Cursor v2 |
|---------|--------------|-----------|
| **Local-only** | ✅ Yes, direct localhost | ❌ Requires proxy |
| **Setup complexity** | ⭐ Easy | ⭐⭐⭐ Complex (needs ngrok) |
| **Privacy** | ✅ Complete (no cloud) | ⚠️ Routes through servers |
| **Features** | ✅ Most features | ✅✅ More features |
| **ODRAS compatibility** | ✅ Excellent | ✅✅ Excellent |
| **Offline development** | ✅ Full support | ❌ Requires internet for proxy |

**Recommendation**: If local-only is critical, **Continue.dev is your best bet**. It's a VS Code extension that works directly with Ollama on `localhost` with no proxies needed.

**Multi-Agent Teams**: Continue.dev supports **multiple agents working together** and can **fully manipulate files** (create, read, update, delete). See **[Multi-Agent Coding Teams Guide](MULTI_AGENT_CODING_TEAMS.md)** for details on building a team of coding agents offline.

**Philosophy**: This setup follows the [amplified developers](https://amplified.dev/) principles: developers are **amplified, not automated**. AI should enhance development, not replace developers. The multi-agent approach aligns with using the right models for the job, establishing an architecture of participation, and maintaining open-source interfaces.

## 📚 Additional Resources

- [Ollama Documentation](https://ollama.com/docs)
- [LM Studio Guide](https://lmstudio.ai/docs)
- [DeepSeek Coder Models](https://huggingface.co/deepseek-ai)
- [Cursor Local LLM Docs](https://cursor.sh/docs)
- [Continue.dev Documentation](https://docs.continue.dev)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Multi-Agent Coding Teams Guide](MULTI_AGENT_CODING_TEAMS.md) - Building teams of coding agents offline
- [Amplified Developers Manifesto](https://amplified.dev/) - Philosophy: Developers amplified, not automated

---

**Quick Start Commands**:

### For 64GB VRAM:
```bash
# Install primary models
ollama pull deepseek-coder:33b
ollama pull llama3.1:70b

# Preload both models
ollama run deepseek-coder:33b "ready" && ollama run llama3.1:70b "ready"

# Verify loaded
ollama ps
```

### For Standard Setup:
```bash
# Install and test in one go
ollama pull deepseek-coder:6.7b && \
ollama run deepseek-coder:6.7b "Explain FastAPI async endpoints"
```

Then configure your chosen editor:
- **Cursor**: Use ngrok/Cloudflare Tunnel URL (see setup instructions above)
- **Continue.dev**: Use `http://localhost:11434` directly (no proxy needed!)
