#!/bin/bash
# Setup script for installing 'act' - GitHub Actions local runner
# Usage: ./scripts/setup-act.sh

set -e

echo "🔧 Setting up 'act' - GitHub Actions local runner"
echo "============================================================"

# Check if act is already installed
if command -v act &> /dev/null; then
    echo "✅ act is already installed"
    act --version
    exit 0
fi

echo "📦 Installing act..."
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - install via snap or download binary
    if command -v snap &> /dev/null; then
        echo "Installing via snap..."
        sudo snap install act
    else
        echo "Installing via binary download..."
        # Download latest act release
        ACT_VERSION=$(curl -s https://api.github.com/repos/nektos/act/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        echo "Downloading act version: $ACT_VERSION"
        
        curl -sL "https://github.com/nektos/act/releases/download/${ACT_VERSION}/act_Linux_x86_64.tar.gz" -o /tmp/act.tar.gz
        tar -xzf /tmp/act.tar.gz -C /tmp
        sudo mv /tmp/act /usr/local/bin/act
        chmod +x /usr/local/bin/act
        rm /tmp/act.tar.gz
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - install via Homebrew
    if command -v brew &> /dev/null; then
        echo "Installing via Homebrew..."
        brew install act
    else
        echo "❌ Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
    fi
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "Please install act manually: https://github.com/nektos/act#installation"
    exit 1
fi

echo ""
echo "✅ act installed successfully!"
act --version
echo ""
echo "📖 Usage:"
echo "  act -l                    # List all workflows"
echo "  act push                  # Run workflow on push event"
echo "  act pull_request          # Run workflow on PR event"
echo "  act -j complete_odras_test  # Run specific job"
echo ""
echo "⚠️  Note: You may need to set secrets in ~/.secrets file or use --secret flag"
echo "   Example: act --secret OPENAI_API_KEY=\$OPENAI_API_KEY"
