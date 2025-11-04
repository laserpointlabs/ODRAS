#!/bin/bash
# Setup script for local LLM development with ODRAS

set -e

echo "🚀 ODRAS Local LLM Setup"
echo "========================"
echo ""

# Check for GPU
echo "📊 Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    
    # Check VRAM amount
    VRAM_GB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | awk '{print int($1/1024)}')
    echo "   VRAM: ${VRAM_GB}GB"
    
    HAS_GPU=true
    
    if [ "$VRAM_GB" -ge 64 ]; then
        HIGH_VRAM=true
        echo "🚀 High-VRAM setup detected (64GB+) - can run multiple large models!"
    elif [ "$VRAM_GB" -ge 24 ]; then
        HIGH_VRAM=false
        MEDIUM_VRAM=true
        echo "💪 Medium-VRAM setup (24GB+) - can run 33B models"
    else
        HIGH_VRAM=false
        MEDIUM_VRAM=false
    fi
else
    echo "⚠️  No NVIDIA GPU detected - will use CPU (slower)"
    HAS_GPU=false
    HIGH_VRAM=false
    MEDIUM_VRAM=false
fi

# Check for Ollama
echo ""
echo "🔍 Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed: $(ollama --version)"
else
    echo "❌ Ollama not found. Installing..."
    echo ""
    echo "Please install Ollama from: https://ollama.com/download"
    echo "Or run: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# Check if Ollama is running
echo ""
echo "🔍 Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama is not running. Starting..."
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama started successfully"
    else
        echo "❌ Failed to start Ollama. Please start it manually: ollama serve"
        exit 1
    fi
fi

# Recommend model based on GPU and VRAM
echo ""
echo "💾 Recommended models for ODRAS:"
echo ""
if [ "$HIGH_VRAM" = true ]; then
    echo "🚀 High-VRAM Setup (64GB+):"
    echo "  Primary models (install both):"
    echo "    ⭐ deepseek-coder:33b - Best for coding (~24GB VRAM)"
    echo "       Download: ollama pull deepseek-coder:33b"
    echo "    ⭐ llama3.1:70b - Best for architecture (~40GB VRAM)"
    echo "       Download: ollama pull llama3.1:70b"
    echo ""
    echo "  Secondary models (optional, for quick iterations):"
    echo "    • deepseek-coder:6.7b - Fast iterations (~8GB VRAM)"
    echo "    • qwen2.5-coder:7b - RAG-specific tasks (~8GB VRAM)"
    echo ""
    echo "  💡 You can run 33B + 70B simultaneously (~64GB total)"
elif [ "$MEDIUM_VRAM" = true ]; then
    echo "💪 Medium-VRAM Setup (24GB+):"
    echo "  ⭐ deepseek-coder:33b - Maximum quality (~24GB VRAM)"
    echo "     Download: ollama pull deepseek-coder:33b"
    echo ""
    echo "  Alternative: deepseek-coder:6.7b for faster responses"
elif [ "$HAS_GPU" = true ]; then
    echo "Standard GPU (8-16GB VRAM):"
    echo "  ⭐ deepseek-coder:6.7b - Best balance (8GB VRAM)"
    echo "     Download: ollama pull deepseek-coder:6.7b"
    echo ""
    echo "  Alternative options:"
    echo "    • deepseek-coder:1.3b - Fastest (2GB VRAM)"
    echo "    • qwen2.5-coder:7b - Good RAG understanding (8GB VRAM)"
    echo "    • codellama:7b - Code-focused (8GB VRAM)"
else
    echo "CPU-only setup (slower but works):"
    echo "  ⭐ deepseek-coder:1.3b - Fastest on CPU"
    echo "     Download: ollama pull deepseek-coder:1.3b"
    echo ""
    echo "  Alternative: qwen2.5-coder:1.5b"
fi

echo ""
if [ "$HIGH_VRAM" = true ]; then
    echo "For 64GB VRAM, we recommend installing both primary models."
    read -p "Install deepseek-coder:33b? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Downloading deepseek-coder:33b (this may take 10-20 minutes)..."
        ollama pull deepseek-coder:33b
        echo "✅ deepseek-coder:33b installed!"
    fi
    read -p "Install llama3.1:70b? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Downloading llama3.1:70b (this may take 15-30 minutes)..."
        ollama pull llama3.1:70b
        echo "✅ llama3.1:70b installed!"
    fi
else
    read -p "Would you like to install a recommended model now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$MEDIUM_VRAM" = true ]; then
            MODEL="deepseek-coder:33b"
        elif [ "$HAS_GPU" = false ]; then
            MODEL="deepseek-coder:1.3b"
        else
            MODEL="deepseek-coder:6.7b"
        fi
        echo "Downloading $MODEL (this may take a few minutes)..."
        ollama pull "$MODEL"
        echo "✅ Model installed successfully!"
    fi
fi

# Test the model
echo ""
read -p "Would you like to test a model with an ODRAS-related prompt? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$HIGH_VRAM" = true ]; then
        read -p "Which model? (1) deepseek-coder:33b (2) llama3.1:70b (3) deepseek-coder:6.7b: " choice
        case $choice in
            1) TEST_MODEL="deepseek-coder:33b" ;;
            2) TEST_MODEL="llama3.1:70b" ;;
            3) TEST_MODEL="deepseek-coder:6.7b" ;;
            *) TEST_MODEL="deepseek-coder:33b" ;;
        esac
    elif [ "$MEDIUM_VRAM" = true ]; then
        TEST_MODEL="deepseek-coder:33b"
    elif [ "$HAS_GPU" = false ]; then
        TEST_MODEL="deepseek-coder:1.3b"
    else
        TEST_MODEL="deepseek-coder:6.7b"
    fi
    echo ""
    echo "🧪 Testing model: $TEST_MODEL"
    echo "Prompt: 'Write a FastAPI async endpoint that queries PostgreSQL using DatabaseService'"
    echo ""
    ollama run "$TEST_MODEL" "Write a FastAPI async endpoint that queries PostgreSQL using DatabaseService from backend.services.db. Include error handling and logging."
fi

# Cursor configuration instructions
echo ""
echo "📝 Cursor Configuration:"
echo "========================"
echo ""
echo "To use local LLMs in Cursor:"
echo ""
echo "1. Open Cursor Settings (Cmd/Ctrl + ,)"
echo "2. Search for 'AI Model' or 'Local Models'"
echo "3. Set endpoint to: http://localhost:11434"
if [ "$HIGH_VRAM" = true ]; then
    echo "4. Select primary model: deepseek-coder:33b (or llama3.1:70b for architecture)"
    echo "5. Use Cmd/Ctrl + Shift + P → 'Change AI Model' to switch between models"
else
    echo "4. Select your installed model"
fi
echo ""
echo "Or manually edit Cursor settings JSON and add:"
echo ""
if [ "$HIGH_VRAM" = true ]; then
    cat << 'EOF'
{
  "localLLM": {
    "enabled": true,
    "provider": "ollama",
    "endpoint": "http://localhost:11434",
    "primaryModel": "deepseek-coder:33b",
    "secondaryModel": "llama3.1:70b"
  }
}
EOF
else
    cat << 'EOF'
{
  "localLLM": {
    "enabled": true,
    "provider": "ollama",
    "endpoint": "http://localhost:11434",
    "model": "deepseek-coder:6.7b"
  }
}
EOF
fi

if [ "$HIGH_VRAM" = true ]; then
    echo ""
    echo "💡 Tip: Preload both models for best performance:"
    echo "   ollama run deepseek-coder:33b 'ready'"
    echo "   ollama run llama3.1:70b 'ready'"
    echo "   ollama ps  # Verify both loaded"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 For detailed instructions, see: docs/development/LOCAL_LLM_SETUP.md"
echo ""
