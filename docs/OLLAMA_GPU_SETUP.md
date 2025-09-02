# 🚀 Ollama GPU Setup Guide for ODRAS

This guide helps you set up Ollama with GPU acceleration for optimal local LLM performance in ODRAS.

## 🎯 Benefits of GPU-Accelerated Ollama

- **⚡ 10-50x Faster**: GPU inference vs CPU-only
- **🔒 Complete Privacy**: All AI processing stays local
- **💰 Zero API Costs**: No OpenAI or external API charges
- **🌐 Offline Ready**: Works without internet connection
- **🎛️ Full Control**: Choose your own models and configurations

## 📋 Prerequisites

### **System Requirements**
- **NVIDIA GPU**: GTX 1060 (6GB) or newer recommended
- **GPU Memory**: Minimum 4GB VRAM (8GB+ for larger models)
- **Docker**: Version 20.10+ with Docker Compose
- **NVIDIA Driver**: Version 470+ installed on host

### **Check Your GPU**
```bash
# Verify NVIDIA GPU is available
nvidia-smi

# Should show something like:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 525.xx       Driver Version: 525.xx       CUDA Version: 12.x  |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  GeForce RTX 3080    Off  | 00000000:01:00.0  On |                  N/A |
# | 30%   45C    P8    25W / 320W |   1234MiB / 10240MiB |      5%      Default |
# +-------------------------------+----------------------+----------------------+
```

## 🛠️ Installation Steps

### **1. Install NVIDIA Container Toolkit**

#### **Ubuntu/Debian**
```bash
# Configure the repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install the toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### **RHEL/CentOS/Fedora**
```bash
# Configure the repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install the toolkit
sudo dnf install -y nvidia-container-toolkit  # Fedora
# sudo yum install -y nvidia-container-toolkit  # RHEL/CentOS

# Configure Docker  
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### **2. Test GPU Access in Docker**
```bash
# Test NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi

# Should show the same GPU info as the host system
```

### **3. Start ODRAS with GPU-Enabled Ollama**
```bash
cd /path/to/ODRAS
./odras.sh restart-docker
```

### **4. Verify Ollama GPU Detection**
```bash
# Check Ollama container logs
docker logs odras_ollama

# Should show GPU detection messages like:
# time=2024-xx-xx level=INFO source=gpu.go:xx msg="Initializing GPU"
# time=2024-xx-xx level=INFO source=gpu.go:xx msg="Found 1 NVIDIA GPU(s)"
```

## 🤖 Model Setup

### **Download Recommended Models**
```bash
# Access Ollama container
docker exec -it odras_ollama bash

# Inside container - download models (choose based on your GPU memory)
ollama pull llama3.1:8b-instruct      # Requires ~5GB VRAM (Recommended)
ollama pull llama3.1:7b-instruct      # Requires ~4GB VRAM (Minimum)
ollama pull codellama:13b-instruct    # Requires ~8GB VRAM (Code tasks)
ollama pull mistral:7b-instruct       # Requires ~4GB VRAM (Alternative)

# List available models
ollama list
```

### **Configure ODRAS to Use Ollama**

Create/update `.env` file in your ODRAS root:
```bash
# Local Ollama Configuration
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b-instruct
OLLAMA_URL=http://localhost:11434
```

### **Test Your Setup**
```bash
# Test model directly
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b-instruct",
    "messages": [{"role": "user", "content": "Hello! Are you running on GPU?"}],
    "stream": false
  }'

# Restart ODRAS application to pick up new config
./odras.sh restart
```

## 🔧 Performance Optimization

### **Model Selection by GPU Memory**
- **4GB VRAM**: `llama3.1:7b-instruct`, `mistral:7b-instruct`
- **6GB VRAM**: `llama3.1:8b-instruct` (recommended)
- **8GB+ VRAM**: `llama3.1:13b-instruct`, `codellama:13b-instruct`
- **16GB+ VRAM**: `llama3.1:70b-instruct` (best quality)

### **Environment Variables for Performance**
Add to docker-compose.yml Ollama environment:
```yaml
environment:
  - OLLAMA_KEEP_ALIVE=1h
  - OLLAMA_HOST=0.0.0.0:11434
  - OLLAMA_ORIGINS=*
  - OLLAMA_NUM_PARALLEL=4      # Parallel requests
  - OLLAMA_MAX_LOADED_MODELS=2 # Models in memory
```

## ❌ Troubleshooting

### **GPU Not Detected**
```bash
# Check container can see GPU
docker exec odras_ollama nvidia-smi

# If command fails, GPU access isn't working
# Verify: nvidia-container-toolkit installation
# Restart: Docker daemon after toolkit installation
```

### **Out of Memory Errors**
- Use smaller model (7b instead of 13b)
- Reduce `OLLAMA_NUM_PARALLEL` 
- Check GPU memory: `nvidia-smi`

### **Slow Performance** 
- Verify GPU is actually being used: `nvidia-smi` during inference
- Check model is fully loaded in VRAM
- Consider larger model if you have memory available

### **Fallback to CPU Mode**
If GPU setup fails, comment out the `deploy` section in docker-compose.yml:
```yaml
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: 1
#           capabilities: [gpu]
```

## 🎯 Testing RAG Performance

### **Before (CPU or OpenAI API)**
```bash
time curl -X POST http://localhost:8000/api/knowledge/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question": "What are the navigation system requirements?"}'
```

### **After (GPU-Accelerated Ollama)**
- **Faster responses**: 2-10x speed improvement
- **No API costs**: Completely free inference
- **Private processing**: All data stays local
- **Consistent availability**: No rate limits or outages

## 🚀 Next Steps

1. **Configure ODRAS**: Update `.env` with Ollama settings
2. **Download Models**: Choose models based on your GPU capacity  
3. **Test RAG**: Try knowledge queries in the ODRAS UI
4. **Monitor Performance**: Use `nvidia-smi` to verify GPU usage
5. **Experiment**: Try different models for different use cases

---

## 📊 Model Comparison

| Model | Size | VRAM | Speed | Quality | Use Case |
|-------|------|------|-------|---------|----------|
| llama3.1:7b | ~4GB | 4GB+ | Fast | Good | General chat, quick responses |
| llama3.1:8b | ~5GB | 6GB+ | Fast | Better | **Recommended for ODRAS** |
| llama3.1:13b | ~8GB | 8GB+ | Medium | Great | Complex reasoning |
| codellama:13b | ~8GB | 8GB+ | Medium | Great | Code analysis, technical docs |
| llama3.1:70b | ~40GB | 48GB+ | Slow | Excellent | Best quality (enterprise) |

**💡 Tip**: Start with `llama3.1:8b-instruct` - it offers the best balance of performance, quality, and resource usage for most ODRAS knowledge management tasks.

