#!/usr/bin/env python3
"""
Check current LLM configuration and availability
"""
import os
import sys
import requests
sys.path.append('.')

from backend.services.config import Settings

def check_llm_config():
    settings = Settings()
    
    print("🤖 ODRAS LLM Configuration Status")
    print("=" * 50)
    
    # Basic configuration
    print(f"🔧 Provider: {settings.llm_provider}")
    print(f"🔧 Model: {settings.llm_model}")
    print(f"🔧 Ollama URL: {settings.ollama_url}")
    
    # Check OpenAI configuration
    print(f"\n📡 OpenAI Configuration:")
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"   ✅ API Key: Set (ends with: ...{openai_key[-4:]})")
    else:
        print(f"   ❌ API Key: Not set")
    
    # Check Ollama availability
    print(f"\n🖥️  Local Ollama Status:")
    try:
        response = requests.get(f"{settings.ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"   ✅ Ollama: Running")
            print(f"   📊 Available models: {len(models)}")
            for model in models[:3]:  # Show first 3 models
                name = model.get('name', 'unknown')
                size = model.get('size', 0) / (1024**3)  # Convert to GB
                print(f"      • {name} ({size:.1f}GB)")
            if len(models) > 3:
                print(f"      • ... and {len(models) - 3} more")
        else:
            print(f"   ⚠️  Ollama: Responding but error {response.status_code}")
    except Exception as e:
        print(f"   ❌ Ollama: Not accessible ({str(e)})")
    
    # Determine what's actually being used
    print(f"\n🎯 Current Usage:")
    if settings.llm_provider == "openai":
        if openai_key:
            print(f"   🌐 Using: OpenAI {settings.llm_model}")
        else:
            print(f"   ⚠️  Configured for OpenAI but no API key → Using development fallback")
    elif settings.llm_provider == "ollama":
        print(f"   🖥️  Using: Local Ollama {settings.llm_model}")
    
    print(f"\n💡 To switch to local Ollama:")
    print(f"   1. Ensure Ollama has a model installed")
    print(f"   2. Set LLM_PROVIDER=ollama in environment")
    print(f"   3. Set LLM_MODEL=llama3:8b-instruct (or other model)")

if __name__ == "__main__":
    check_llm_config()
