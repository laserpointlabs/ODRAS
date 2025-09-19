# Voice Mode MCP Server Setup Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration Options](#configuration-options)
5. [Local Kokoro TTS Service Setup](#local-kokoro-tts-service-setup)
6. [Voice Mode Configuration](#voice-mode-configuration)
7. [Service Management](#service-management)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)
10. [Security Considerations](#security-considerations)

## Overview

This guide provides comprehensive instructions for setting up Voice Mode MCP server in Cursor with both cloud-based (OpenAI) and local GPU-accelerated (Kokoro) TTS services. The setup supports both CUI-compliant local processing and cloud-based voice synthesis.

### Features
- **Auto-start voice mode** in new Cursor threads
- **Persistent voice sessions** for continuous conversation
- **GPU-accelerated local TTS** using Kokoro (CUI compliant)
- **Cloud-based TTS** using OpenAI (requires internet)
- **Easy service management** for GPU resource control

## Prerequisites

### System Requirements
- **Operating System**: Linux (WSL2 supported)
- **GPU**: NVIDIA GPU with CUDA support (for local TTS)
- **Memory**: Minimum 8GB RAM, 16GB recommended
- **Storage**: 10GB free space for models and dependencies

### Software Dependencies
- **Docker**: For containerized Kokoro service
- **NVIDIA Container Toolkit**: For GPU access in containers
- **Python 3.10+**: For voice mode dependencies
- **Git**: For cloning repositories

### Verify GPU Support
```bash
nvidia-smi
```
Should show your GPU and CUDA version (e.g., RTX 5000 Ada, CUDA 12.8).

## Installation

### 1. Install Voice Mode MCP Server

```bash
# Install voice mode globally
pip install voice-mode

# Or install in a virtual environment
python -m venv ~/.voicemode
source ~/.voicemode/bin/activate
pip install voice-mode
```

### 2. Verify Installation

```bash
voice-mode --version
```

### 3. Configure Cursor MCP Settings

Add to your Cursor MCP configuration (`~/.cursor/mcp.json` or workspace settings):

```json
{
  "mcpServers": {
    "voice-mode": {
      "command": "uvx",
      "args": ["voice-mode"],
      "env": {
        "VOICEMODE_AUTO_START": "true",
        "VOICEMODE_PERSISTENT": "true",
        "VOICEMODE_SESSION_TIMEOUT": "0"
      }
    }
  }
}
```

## Configuration Options

### Environment Variables

Add these to your `~/.bashrc` or `~/.profile`:

```bash
# Auto-start voice mode in new threads
export VOICEMODE_AUTO_START=true

# Keep voice sessions persistent
export VOICEMODE_PERSISTENT=true

# Disable session timeout (infinite sessions)
export VOICEMODE_SESSION_TIMEOUT=0

# Keep voice mode alive between interactions
export VOICEMODE_KEEP_ALIVE=true

# Prefer local services when available
export VOICEMODE_PREFER_LOCAL=true

# Always try local services first
export VOICEMODE_ALWAYS_TRY_LOCAL=true
```

### Voice Mode Configuration File

The configuration is stored in `~/.voicemode/voicemode.env`:

```bash
# Example configuration
VOICEMODE_AUTO_START=true
VOICEMODE_PERSISTENT=true
VOICEMODE_SESSION_TIMEOUT=0
VOICEMODE_KEEP_ALIVE=true
VOICEMODE_PREFER_LOCAL=true
VOICEMODE_TTS_BASE_URL=http://127.0.0.1:8880
VOICEMODE_TTS_PROVIDER=kokoro
```

## Local Kokoro TTS Service Setup

### 1. Install Kokoro Service

```bash
# Install Kokoro TTS service with GPU support
uvx voice-mode kokoro-install --auto-enable=true
```

### 2. Alternative: Manual Docker Setup

```bash
# Navigate to voice mode services directory
cd ~/.voicemode/services/kokoro

# Start GPU-accelerated Docker service
docker compose -f docker/gpu/docker-compose.yml up -d
```

### 3. Verify Service Status

```bash
# Check if service is running
curl -s http://127.0.0.1:8880/health

# Check available voices
curl -s http://127.0.0.1:8880/v1/audio/voices

# Check Docker container status
docker ps | grep kokoro
```

### 4. Service Configuration

The Docker service automatically:
- Downloads Kokoro models (~327MB)
- Downloads voice packs (65+ voices)
- Configures GPU acceleration
- Sets up proper file permissions

## Voice Mode Configuration

### For Local TTS Only (CUI Compliant)

```bash
# Configure for local-only processing
export VOICEMODE_PREFER_LOCAL=true
export VOICEMODE_ALWAYS_TRY_LOCAL=true
export VOICEMODE_TTS_BASE_URL=http://127.0.0.1:8880
export VOICEMODE_TTS_PROVIDER=kokoro

# Disable cloud services
export VOICEMODE_USE_LOCAL_TTS=true
export VOICEMODE_USE_LOCAL_STT=false  # Keep STT cloud for now
```

### For Cloud TTS Only (Requires Internet)

```bash
# Configure for cloud services
export VOICEMODE_PREFER_LOCAL=false
export VOICEMODE_ALWAYS_TRY_LOCAL=false

# Use OpenAI services
export VOICEMODE_TTS_PROVIDER=openai
export VOICEMODE_STT_PROVIDER=openai
```

### For Hybrid Mode (Local + Cloud Fallback)

```bash
# Try local first, fallback to cloud
export VOICEMODE_PREFER_LOCAL=true
export VOICEMODE_ALWAYS_TRY_LOCAL=false
export VOICEMODE_TTS_BASE_URL=http://127.0.0.1:8880
```

## Service Management

### Starting Services

#### Local Kokoro Service
```bash
# Start Docker-based Kokoro service
cd ~/.voicemode/services/kokoro
docker compose -f docker/gpu/docker-compose.yml up -d

# Or use voice mode commands
uvx voice-mode service kokoro start
```

#### Voice Mode MCP Server
```bash
# Start voice mode (if not auto-started)
uvx voice-mode
```

### Stopping Services

#### Stop Kokoro Service (Free GPU for other tasks)
```bash
# Stop Docker service
cd ~/.voicemode/services/kokoro
docker compose -f docker/gpu/docker-compose.yml down

# Or use voice mode commands
uvx voice-mode service kokoro stop
```

#### Stop Voice Mode
```bash
# Stop voice mode service
pkill -f "voice-mode"
```

### Service Status Checking

```bash
# Check Kokoro service health
curl -s http://127.0.0.1:8880/health

# Check Docker container status
docker ps | grep kokoro

# Check voice mode status
uvx voice-mode service kokoro status
uvx voice-mode service whisper status
```

### Convenience Aliases

Add to your `~/.bashrc`:

```bash
# Kokoro service management
alias kokoro-start="cd ~/.voicemode/services/kokoro && docker compose -f docker/gpu/docker-compose.yml up -d"
alias kokoro-stop="cd ~/.voicemode/services/kokoro && docker compose -f docker/gpu/docker-compose.yml down"
alias kokoro-status="curl -s http://127.0.0.1:8880/health && echo ' - Kokoro healthy' || echo ' - Kokoro not responding'"

# Voice mode management
alias voice-start="uvx voice-mode"
alias voice-status="uvx voice-mode voice-status"
alias voice-stats="uvx voice-mode voice-statistics"
```

## Troubleshooting

### Common Issues

#### 1. Kokoro Service Won't Start

**Problem**: Service fails to start or health check fails
```bash
# Check Docker logs
docker logs kokoro-tts-gpu-kokoro-tts-1

# Check if port 8880 is in use
netstat -tlnp | grep 8880

# Restart service
docker compose -f docker/gpu/docker-compose.yml restart
```

#### 2. GPU Not Detected

**Problem**: CUDA/GPU not available in container
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi

# Install NVIDIA Container Toolkit (if needed)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

#### 3. Voice Mode Not Auto-Starting

**Problem**: Voice mode doesn't start automatically in Cursor
```bash
# Check environment variables
env | grep VOICEMODE

# Verify MCP configuration
cat ~/.cursor/mcp.json

# Test voice mode manually
uvx voice-mode
```

#### 4. Poor Voice Quality

**Problem**: Voice sounds choppy or unclear
```bash
# Check service performance
uvx voice-mode voice-statistics

# Optimize settings
export VOICEMODE_AUDIO_FORMAT=wav
export VOICEMODE_TTS_SPEED=1.0

# Test with different voice
uvx voice-mode list-tts-voices
```

### Performance Issues

#### High GPU Memory Usage
```bash
# Monitor GPU usage
nvidia-smi

# Stop Kokoro when not needed
kokoro-stop

# Restart with memory optimization
docker compose -f docker/gpu/docker-compose.yml down
docker compose -f docker/gpu/docker-compose.yml up -d
```

#### Slow Response Times
```bash
# Check service logs
docker logs kokoro-tts-gpu-kokoro-tts-1

# Optimize voice mode settings
export VOICEMODE_LISTEN_DURATION=30
export VOICEMODE_MIN_LISTEN_DURATION=2
```

## Performance Optimization

### Voice Mode Performance Testing Results

#### Test Protocol
We conducted systematic performance testing using a consistent test sentence:
**"This is our performance test sentence for optimizing voice mode speed and quality with the local Kokoro service running on GPU."**

#### Performance Test Results

| Test Configuration | Settings | Total Time | Improvement | Notes |
|-------------------|----------|------------|-------------|-------|
| **Baseline** | Default settings | 41.0s | - | Original configuration |
| **Optimization 1** | MP3 format + 1.2x speed | 28.4s | **31% faster** | High quality, good speed |
| **Optimization 2** | 16kHz sample rate + 1.4x speed | 33.8s | 18% faster | Good quality/speed balance |
| **Optimization 3** | WAV format + 22kHz + 1.5x speed | 34.6s | 16% faster | Higher quality, slightly slower |
| **Optimization 4** | MP3 format + 1.8x speed | 32.4s | **31% faster** | Balanced quality/speed |
| **Optimization 5** | MP3 format + 2.0x speed | 32.0s | **32% faster** | **Maximum performance** |

#### Recommended Performance Settings

For optimal performance with local Kokoro TTS:

```bash
# BEST PERFORMANCE: Maximum speed optimization (32% faster)
export VOICEMODE_AUDIO_FORMAT=mp3
export VOICEMODE_TTS_SPEED=2.0

# Alternative: Balanced quality/speed (31% faster)
export VOICEMODE_AUDIO_FORMAT=mp3
export VOICEMODE_TTS_SPEED=1.8

# Conservative: High quality with good speed (31% faster)
export VOICEMODE_AUDIO_FORMAT=mp3
export VOICEMODE_TTS_SPEED=1.2
```

#### Performance Breakdown Analysis

**Optimization 5 (Maximum Performance - 2.0x speed):**
- TTFA (Time to First Audio): 6.2s
- Generation Time: 6.2s
- Playback Time: 14.8s (34% faster than baseline)
- Recording Time: 8.5s (42% faster than baseline)
- STT Time: 2.4s
- **Total: 32.0s (32% improvement)**

**Optimization 4 (Balanced - 1.8x speed):**
- TTFA: 5.5s
- Generation Time: 5.5s
- Playback Time: 15.1s (33% faster than baseline)
- Recording Time: 9.3s (37% faster than baseline)
- STT Time: 2.4s
- **Total: 32.4s (31% improvement)**

**Key Insights:**
- MP3 format provides best compression/speed balance
- 2.0x speech speed delivers maximum performance while maintaining comprehension
- GPU processing time (TTFA + Generation) is consistent at ~6s
- Playback time scales inversely with speech speed (2.0x = 50% faster playback)
- Recording time improves as conversations become more concise and efficient

### GPU Optimization

#### Memory Management
```bash
# Monitor GPU memory
watch -n 1 nvidia-smi

# Optimize Docker memory limits
# Edit docker-compose.yml to add:
# deploy:
#   resources:
#     limits:
#       memory: 8G
```

#### Model Optimization
```bash
# Use smaller models for faster processing
export VOICEMODE_TTS_MODEL=base
export VOICEMODE_STT_MODEL=tiny

# Optimize audio settings
export VOICEMODE_AUDIO_FORMAT=mp3
export VOICEMODE_SAMPLE_RATE=22050
```

### Voice Mode Optimization

#### Session Management
```bash
# Optimize session settings
export VOICEMODE_SESSION_TIMEOUT=300  # 5 minutes
export VOICEMODE_KEEP_ALIVE=true
export VOICEMODE_AUTO_START=true
```

#### Audio Settings
```bash
# Optimize audio processing
export VOICEMODE_LISTEN_DURATION=30
export VOICEMODE_MIN_LISTEN_DURATION=2
export VOICEMODE_DISABLE_SILENCE_DETECTION=false
```

## Security Considerations

### CUI Compliance

For Classified Unclassified Information (CUI) work:

#### Local-Only Configuration
```bash
# Disable all cloud services
export VOICEMODE_PREFER_LOCAL=true
export VOICEMODE_ALWAYS_TRY_LOCAL=true
export VOICEMODE_USE_LOCAL_TTS=true
export VOICEMODE_USE_LOCAL_STT=false  # Consider local Whisper for full compliance

# Verify no internet transmission
netstat -tulpn | grep :8880  # Should only show local connections
```

#### Network Isolation
```bash
# Block internet access for voice mode (if needed)
sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP  # Block HTTPS
sudo iptables -A OUTPUT -p tcp --dport 80 -j DROP   # Block HTTP
```

#### Data Persistence
```bash
# Clear voice mode cache
rm -rf ~/.voicemode/cache/*
rm -rf ~/.voicemode/logs/*

# Secure model storage
chmod 600 ~/.voicemode/services/kokoro/api/src/models/*
```

### General Security

#### Service Isolation
```bash
# Run services in isolated network
docker network create voice-mode-network
docker compose -f docker/gpu/docker-compose.yml --network voice-mode-network up -d
```

#### Access Control
```bash
# Restrict service access
sudo ufw allow from 127.0.0.1 to any port 8880
sudo ufw deny 8880
```

## Usage Examples

### Basic Voice Conversation

1. **Start Services**:
   ```bash
   kokoro-start
   ```

2. **Open Cursor**: Voice mode auto-starts

3. **Speak**: "Hello, can you help me with my project?"

4. **Response**: AI responds with voice synthesis

### CUI Work Session

1. **Configure for CUI**:
   ```bash
   export VOICEMODE_PREFER_LOCAL=true
   export VOICEMODE_ALWAYS_TRY_LOCAL=true
   kokoro-start
   ```

2. **Verify Local Processing**:
   ```bash
   kokoro-status
   ```

3. **Work Securely**: All voice processing happens locally

### GPU Resource Management

1. **Stop for Olam**:
   ```bash
   kokoro-stop
   # Use Olam or other GPU-intensive tasks
   ```

2. **Resume Voice Mode**:
   ```bash
   kokoro-start
   # Voice mode resumes with local processing
   ```

## Maintenance

### Regular Tasks

#### Weekly
```bash
# Update voice mode
pip install --upgrade voice-mode

# Check service health
kokoro-status
voice-status
```

#### Monthly
```bash
# Clean up Docker images
docker system prune -f

# Update Kokoro service
cd ~/.voicemode/services/kokoro
git pull
docker compose -f docker/gpu/docker-compose.yml up -d --build
```

#### As Needed
```bash
# Clear voice mode cache
rm -rf ~/.voicemode/cache/*

# Reset voice mode configuration
rm ~/.voicemode/voicemode.env
uvx voice-mode  # Recreates default config
```

## Support and Resources

### Documentation
- [Voice Mode GitHub](https://github.com/voice-mode/voice-mode)
- [Kokoro TTS Documentation](https://github.com/remsky/Kokoro-FastAPI)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/)

### Troubleshooting Resources
- Check service logs: `docker logs kokoro-tts-gpu-kokoro-tts-1`
- Voice mode statistics: `uvx voice-mode voice-statistics`
- GPU monitoring: `nvidia-smi`

### Configuration Files
- Voice Mode Config: `~/.voicemode/voicemode.env`
- Docker Compose: `~/.voicemode/services/kokoro/docker/gpu/docker-compose.yml`
- Cursor MCP: `~/.cursor/mcp.json`

---

**Last Updated**: September 18, 2025
**Version**: 1.0
**Author**: ODRAS Development Team
