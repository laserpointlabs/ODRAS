# 🚀 Ollama GPU Setup Guide for ODRAS<br>
<br>
This guide helps you set up Ollama with GPU acceleration for optimal local LLM performance in ODRAS.<br>
<br>
## 🎯 Benefits of GPU-Accelerated Ollama<br>
<br>
- **⚡ 10-50x Faster**: GPU inference vs CPU-only<br>
- **🔒 Complete Privacy**: All AI processing stays local<br>
- **💰 Zero API Costs**: No OpenAI or external API charges<br>
- **🌐 Offline Ready**: Works without internet connection<br>
- **🎛️ Full Control**: Choose your own models and configurations<br>
<br>
## 📋 Prerequisites<br>
<br>
### **System Requirements**<br>
- **NVIDIA GPU**: GTX 1060 (6GB) or newer recommended<br>
- **GPU Memory**: Minimum 4GB VRAM (8GB+ for larger models)<br>
- **Docker**: Version 20.10+ with Docker Compose<br>
- **NVIDIA Driver**: Version 470+ installed on host<br>
<br>
### **Check Your GPU**<br>
```bash<br>
# Verify NVIDIA GPU is available<br>
nvidia-smi<br>
<br>
# Should show something like:<br>
# +-----------------------------------------------------------------------------+<br>
# | NVIDIA-SMI 525.xx       Driver Version: 525.xx       CUDA Version: 12.x  |<br>
# |-------------------------------+----------------------+----------------------+<br>
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |<br>
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |<br>
# |===============================+======================+======================|<br>
# |   0  GeForce RTX 3080    Off  | 00000000:01:00.0  On |                  N/A |<br>
# | 30%   45C    P8    25W / 320W |   1234MiB / 10240MiB |      5%      Default |<br>
# +-------------------------------+----------------------+----------------------+<br>
```<br>
<br>
## 🛠️ Installation Steps<br>
<br>
### **1. Install NVIDIA Container Toolkit**<br>
<br>
#### **Ubuntu/Debian**<br>
```bash<br>
# Configure the repository<br>
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \<br>
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \<br>
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \<br>
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \<br>
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list<br>
<br>
# Install the toolkit<br>
sudo apt-get update<br>
sudo apt-get install -y nvidia-container-toolkit<br>
<br>
# Configure Docker<br>
sudo nvidia-ctk runtime configure --runtime=docker<br>
sudo systemctl restart docker<br>
```<br>
<br>
#### **RHEL/CentOS/Fedora**<br>
```bash<br>
# Configure the repository<br>
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)<br>
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.repo | \<br>
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo<br>
<br>
# Install the toolkit<br>
sudo dnf install -y nvidia-container-toolkit  # Fedora<br>
# sudo yum install -y nvidia-container-toolkit  # RHEL/CentOS<br>
<br>
# Configure Docker<br>
sudo nvidia-ctk runtime configure --runtime=docker<br>
sudo systemctl restart docker<br>
```<br>
<br>
### **2. Test GPU Access in Docker**<br>
```bash<br>
# Test NVIDIA runtime<br>
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi<br>
<br>
# Should show the same GPU info as the host system<br>
```<br>
<br>
### **3. Start ODRAS with GPU-Enabled Ollama**<br>
```bash<br>
cd /path/to/ODRAS<br>
./odras.sh restart-docker<br>
```<br>
<br>
### **4. Verify Ollama GPU Detection**<br>
```bash<br>
# Check Ollama container logs<br>
docker logs odras_ollama<br>
<br>
# Should show GPU detection messages like:<br>
# time=2024-xx-xx level=INFO source=gpu.go:xx msg="Initializing GPU"<br>
# time=2024-xx-xx level=INFO source=gpu.go:xx msg="Found 1 NVIDIA GPU(s)"<br>
```<br>
<br>
## 🤖 Model Setup<br>
<br>
### **Download Recommended Models**<br>
```bash<br>
# Access Ollama container<br>
docker exec -it odras_ollama bash<br>
<br>
# Inside container - download models (choose based on your GPU memory)<br>
ollama pull llama3.1:8b-instruct      # Requires ~5GB VRAM (Recommended)<br>
ollama pull llama3.1:7b-instruct      # Requires ~4GB VRAM (Minimum)<br>
ollama pull codellama:13b-instruct    # Requires ~8GB VRAM (Code tasks)<br>
ollama pull mistral:7b-instruct       # Requires ~4GB VRAM (Alternative)<br>
<br>
# List available models<br>
ollama list<br>
```<br>
<br>
### **Configure ODRAS to Use Ollama**<br>
<br>
Create/update `.env` file in your ODRAS root:<br>
```bash<br>
# Local Ollama Configuration<br>
LLM_PROVIDER=ollama<br>
LLM_MODEL=llama3.1:8b-instruct<br>
OLLAMA_URL=http://localhost:11434<br>
```<br>
<br>
### **Test Your Setup**<br>
```bash<br>
# Test model directly<br>
curl -X POST http://localhost:11434/v1/chat/completions \<br>
  -H "Content-Type: application/json" \<br>
  -d '{<br>
    "model": "llama3.1:8b-instruct",<br>
    "messages": [{"role": "user", "content": "Hello! Are you running on GPU?"}],<br>
    "stream": false<br>
  }'<br>
<br>
# Restart ODRAS application to pick up new config<br>
./odras.sh restart<br>
```<br>
<br>
## 🔧 Performance Optimization<br>
<br>
### **Model Selection by GPU Memory**<br>
- **4GB VRAM**: `llama3.1:7b-instruct`, `mistral:7b-instruct`<br>
- **6GB VRAM**: `llama3.1:8b-instruct` (recommended)<br>
- **8GB+ VRAM**: `llama3.1:13b-instruct`, `codellama:13b-instruct`<br>
- **16GB+ VRAM**: `llama3.1:70b-instruct` (best quality)<br>
<br>
### **Environment Variables for Performance**<br>
Add to docker-compose.yml Ollama environment:<br>
```yaml<br>
environment:<br>
  - OLLAMA_KEEP_ALIVE=1h<br>
  - OLLAMA_HOST=0.0.0.0:11434<br>
  - OLLAMA_ORIGINS=*<br>
  - OLLAMA_NUM_PARALLEL=4      # Parallel requests<br>
  - OLLAMA_MAX_LOADED_MODELS=2 # Models in memory<br>
```<br>
<br>
## ❌ Troubleshooting<br>
<br>
### **GPU Not Detected**<br>
```bash<br>
# Check container can see GPU<br>
docker exec odras_ollama nvidia-smi<br>
<br>
# If command fails, GPU access isn't working<br>
# Verify: nvidia-container-toolkit installation<br>
# Restart: Docker daemon after toolkit installation<br>
```<br>
<br>
### **Out of Memory Errors**<br>
- Use smaller model (7b instead of 13b)<br>
- Reduce `OLLAMA_NUM_PARALLEL`<br>
- Check GPU memory: `nvidia-smi`<br>
<br>
### **Slow Performance**<br>
- Verify GPU is actually being used: `nvidia-smi` during inference<br>
- Check model is fully loaded in VRAM<br>
- Consider larger model if you have memory available<br>
<br>
### **Fallback to CPU Mode**<br>
If GPU setup fails, comment out the `deploy` section in docker-compose.yml:<br>
```yaml<br>
# deploy:<br>
#   resources:<br>
#     reservations:<br>
#       devices:<br>
#         - driver: nvidia<br>
#           count: 1<br>
#           capabilities: [gpu]<br>
```<br>
<br>
## 🎯 Testing RAG Performance<br>
<br>
### **Before (CPU or OpenAI API)**<br>
```bash<br>
time curl -X POST http://localhost:8000/api/knowledge/query \<br>
  -H "Authorization: Bearer YOUR_TOKEN" \<br>
  -H 'Content-Type: application/json' \<br>
  -d '{"question": "What are the navigation system requirements?"}'<br>
```<br>
<br>
### **After (GPU-Accelerated Ollama)**<br>
- **Faster responses**: 2-10x speed improvement<br>
- **No API costs**: Completely free inference<br>
- **Private processing**: All data stays local<br>
- **Consistent availability**: No rate limits or outages<br>
<br>
## 🚀 Next Steps<br>
<br>
1. **Configure ODRAS**: Update `.env` with Ollama settings<br>
2. **Download Models**: Choose models based on your GPU capacity<br>
3. **Test RAG**: Try knowledge queries in the ODRAS UI<br>
4. **Monitor Performance**: Use `nvidia-smi` to verify GPU usage<br>
5. **Experiment**: Try different models for different use cases<br>
<br>
---<br>
<br>
## 📊 Model Comparison<br>
<br>
| Model | Size | VRAM | Speed | Quality | Use Case |<br>
|-------|------|------|-------|---------|----------|<br>
| llama3.1:7b | ~4GB | 4GB+ | Fast | Good | General chat, quick responses |<br>
| llama3.1:8b | ~5GB | 6GB+ | Fast | Better | **Recommended for ODRAS** |<br>
| llama3.1:13b | ~8GB | 8GB+ | Medium | Great | Complex reasoning |<br>
| codellama:13b | ~8GB | 8GB+ | Medium | Great | Code analysis, technical docs |<br>
| llama3.1:70b | ~40GB | 48GB+ | Slow | Excellent | Best quality (enterprise) |<br>
<br>
**💡 Tip**: Start with `llama3.1:8b-instruct` - it offers the best balance of performance, quality, and resource usage for most ODRAS knowledge management tasks.<br>
<br>

