# Local LLM Setup Guide for ODRAS Development

**Version:** 2.0  
**Date:** November 2025  
**Status:** Production Setup Guide

## Overview

This guide helps you configure Cursor to use local LLMs for offline development of ODRAS. It consolidates setup instructions, model recommendations, and GPU configuration.

---

## Table of Contents

1. [Recommended Models](#1-recommended-models)
2. [Quick Reference](#2-quick-reference)
3. [GPU Setup](#3-gpu-setup)
4. [Configuration](#4-configuration)
5. [Usage Tips](#5-usage-tips)

---

## 1. Recommended Models

### Top Recommendations (Priority Order)

#### 1. DeepSeek Coder V2 ⭐ Best Choice
- **Models**: `deepseek-coder-1.3b`, `deepseek-coder-6.7b`, `deepseek-coder-33b`
- **Why**: Excellent Python code understanding, FastAPI patterns, async/await handling
- **Size**: 1.3B (fastest), 6.7B (balanced), 33B (best quality)
- **Speed**: ⚡⚡⚡ (1.3B) / ⚡⚡ (6.7B) / ⚡ (33B)
- **GPU VRAM**: 2GB / 8GB / 24GB
- **Best for**: Python/FastAPI development, service architecture, database code

#### 2. Qwen2.5 Coder
- **Models**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`, `Qwen/Qwen2.5-Coder-7B-Instruct`
- **Why**: Strong coding capabilities, good RAG understanding, multi-database support
- **Size**: 1.5B or 7B
- **Speed**: ⚡⚡⚡ (1.5B) / ⚡⚡ (7B)
- **GPU VRAM**: 2GB / 8GB
- **Best for**: Complex system architecture, RAG implementations

#### 3. CodeLlama 2
- **Models**: `codellama/CodeLlama-7b-Instruct-hf`, `codellama/CodeLlama-13b-Instruct-hf`
- **Why**: Specifically designed for code generation, understands Python well
- **Size**: 7B or 13B
- **Speed**: ⚡⚡ (7B) / ⚡ (13B)
- **GPU VRAM**: 8GB / 16GB
- **Best for**: Code completion, refactoring, debugging

#### 4. Llama 3.1
- **Models**: `meta-llama/Meta-Llama-3.1-8B-Instruct`, `meta-llama/Meta-Llama-3.1-70B-Instruct`
- **Why**: Good general reasoning, handles complex architecture questions
- **Size**: 8B (recommended) or 70B (if you have VRAM)
- **Speed**: ⚡⚡ (8B) / ⚡ (70B)
- **GPU VRAM**: 10GB / 40GB+
- **Best for**: Architecture planning, system design discussions

### Model Selection Matrix

| Model | Python Code | FastAPI | Databases | RAG | Speed | VRAM |
|-------|------------|---------|-----------|-----|-------|------|
| DeepSeek Coder 6.7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⚡⚡ | 8GB |
| Qwen2.5 Coder 7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | 8GB |
| CodeLlama 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⚡⚡ | 8GB |
| Llama 3.1 8B | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⚡⚡ | 10GB |

**Recommendation for ODRAS**: Start with **DeepSeek Coder 6.7B** for best balance of speed and quality.

### High-VRAM Setup (64GB+ VRAM)

With 64GB VRAM, you can run **multiple large models simultaneously**:

**Maximum Quality Models:**
1. **DeepSeek Coder V2 33B** (~24GB VRAM) - Best code understanding
2. **Llama 3.1 70B** (~40GB VRAM) - Outstanding reasoning
3. **Qwen2.5 Coder 32B** (~32GB VRAM) - Excellent RAG understanding

**Multi-Model Strategy:**
- Use DeepSeek Coder 33B for code generation and refactoring
- Use Llama 3.1 70B for architecture planning
- Keep smaller models for fast iteration

---

## 2. Quick Reference

### Installation

**Install Ollama:**
```bash
# Linux/WSL
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download
```

**Pull Models:**
```bash
# Recommended starter model
ollama pull deepseek-coder:6.7b

# Alternative models
ollama pull qwen2.5-coder:7b
ollama pull codellama:7b
ollama pull llama3.1:8b
```

### Basic Usage

**Run Model:**
```bash
ollama run deepseek-coder:6.7b
```

**Test Model:**
```bash
ollama run deepseek-coder:6.7b "Write a Python function to connect to PostgreSQL"
```

### Cursor Configuration

**Add to Cursor Settings:**
1. Open Cursor Settings
2. Navigate to "AI" or "Models"
3. Add local model endpoint: `http://localhost:11434`
4. Select model: `deepseek-coder:6.7b`

---

## 3. GPU Setup

### NVIDIA GPU Setup

**Prerequisites:**
- NVIDIA GPU with CUDA support
- NVIDIA drivers installed
- CUDA toolkit installed

**Verify GPU:**
```bash
nvidia-smi
```

**Ollama GPU Configuration:**
Ollama automatically uses GPU if available. No additional configuration needed.

**Check GPU Usage:**
```bash
# While running Ollama
nvidia-smi
```

### AMD GPU Setup

**Prerequisites:**
- AMD GPU with ROCm support
- ROCm drivers installed

**Ollama Configuration:**
Ollama supports AMD GPUs via ROCm. Check Ollama documentation for latest AMD support.

### CPU-Only Setup

**Limitations:**
- Slower inference (10-100x slower than GPU)
- Limited to smaller models (< 7B)
- Not recommended for development

**If GPU unavailable:**
- Use smallest models (1.3B-3B)
- Accept slower response times
- Consider cloud GPU options

---

## 4. Configuration

### Ollama Configuration

**Default Location:**
- Linux/WSL: `~/.ollama/`
- macOS: `~/.ollama/`
- Windows: `C:\Users\<user>\.ollama\`

**Environment Variables:**
```bash
# Set model directory
export OLLAMA_MODELS=/path/to/models

# Set host/port
export OLLAMA_HOST=0.0.0.0:11434
```

### Cursor Integration

**Local Model Endpoint:**
```
http://localhost:11434
```

**Model Selection:**
- Use model name as shown in `ollama list`
- Format: `model-name:tag` (e.g., `deepseek-coder:6.7b`)

**API Compatibility:**
- Ollama provides OpenAI-compatible API
- Cursor can use it directly
- No additional configuration needed

---

## 5. Usage Tips

### Model Selection

**For Code Generation:**
- Use DeepSeek Coder or CodeLlama
- Best for Python/FastAPI code
- Good for database queries

**For Architecture:**
- Use Llama 3.1 or Qwen2.5
- Better reasoning capabilities
- Good for system design

**For Fast Iteration:**
- Use smaller models (1.3B-7B)
- Faster response times
- Good for simple tasks

### Performance Optimization

**GPU Memory:**
- Monitor VRAM usage with `nvidia-smi`
- Unload unused models: `ollama stop <model>`
- Use quantization for large models

**Response Speed:**
- Use smaller models for faster responses
- Batch requests when possible
- Cache common queries

**Quality vs Speed:**
- Use larger models for complex tasks
- Use smaller models for simple tasks
- Balance based on your needs

---

## Troubleshooting

### Common Issues

**Model Not Loading:**
- Check GPU memory availability
- Try smaller model
- Check Ollama logs: `ollama logs`

**Slow Performance:**
- Verify GPU is being used: `nvidia-smi`
- Check model size vs available VRAM
- Consider CPU-only if GPU unavailable

**Connection Errors:**
- Verify Ollama is running: `ollama list`
- Check port 11434 is accessible
- Restart Ollama service

### Debug Commands

**Check Ollama Status:**
```bash
ollama list
ollama ps
```

**View Logs:**
```bash
ollama logs
```

**Test Model:**
```bash
ollama run <model-name> "test prompt"
```

---

*Last Updated: November 2025*  
*Consolidated from: LOCAL_LLM_SETUP.md, LOCAL_LLM_QUICKREF.md, OLLAMA_GPU_SETUP_GUIDE.md*

