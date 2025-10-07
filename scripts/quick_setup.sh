#!/bin/bash
# ODRAS Quick Setup Script (Shell Version)
# 
# This script automates the complete ODRAS rebuild and setup process:
# 1. Clean all databases and services
# 2. Start Docker services
# 3. Initialize database
# 4. Start ODRAS application
# 5. Run Python setup script
# 6. Validate the setup
#
# Usage: ./scripts/quick_setup.sh

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 ODRAS Complete Rebuild & Setup"
echo "=================================="

# Check if we're in the right directory
if [[ ! -f "$PROJECT_ROOT/odras.sh" ]]; then
    echo "❌ Error: Not in ODRAS project directory"
    echo "   Please run from ODRAS root directory"
    exit 1
fi

cd "$PROJECT_ROOT"

# Step 1: Clean all databases and services
echo "🧹 Step 1: Cleaning all databases and services..."
./odras.sh clean-all -y
echo "✅ System cleaned"

# Step 2: Start Docker services
echo "🐳 Step 2: Starting Docker services..."
docker-compose up -d
echo "✅ Docker services started"

# Step 3: Wait for services to be ready
echo "⏳ Step 3: Waiting for services to be ready..."
sleep 15
echo "✅ Services should be ready"

# Step 4: Initialize database
echo "🗄️ Step 4: Initializing database..."
./odras.sh init-db
echo "✅ Database initialized"

# Step 5: Start ODRAS application
echo "🚀 Step 5: Starting ODRAS application..."
./odras.sh start
echo "✅ ODRAS application started"

# Step 6: Wait for application to be ready
echo "⏳ Step 6: Waiting for application to be ready..."
sleep 10

# Check if ODRAS is responding
echo "🔍 Checking ODRAS status..."
max_attempts=6
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ ODRAS is responding"
        break
    else
        echo "⏳ Attempt $attempt/$max_attempts - waiting for ODRAS..."
        sleep 5
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ ODRAS failed to start properly"
    echo "   Check logs: tail /tmp/odras_app.log"
    exit 1
fi

# Check if required data files exist
echo "🔍 Checking data files..."
required_files=(
    "data/bseo_v1a.json"
    "data/uas_specifications.md"
    "data/disaster_response_requirements.md"
    "data/decision_matrix_template.md"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
        echo "⚠️  Warning: $file not found"
        ((missing_files++))
    else
        echo "✅ Found $file"
    fi
done

if [[ $missing_files -gt 0 ]]; then
    echo "⚠️  $missing_files required files missing - setup will continue with available files"
fi

# Run the Python setup script
echo ""
echo "🐍 Running Python setup script..."
cd "$PROJECT_ROOT"

if python3 scripts/quick_setup.py; then
    echo ""
    echo "🎉 Quick Setup Complete!"
    echo "======================="
    echo "Your ODRAS system is ready to use:"
    echo "• Open: http://localhost:8000/app"
    echo "• Login as: jdehart / jdehart123!"
    echo "• Project: core.se"
    echo ""
    echo "🧪 Testing both embedding models..."
    if python3 scripts/test_embedders.py; then
        echo "✅ Both embedding models tested successfully!"
    else
        echo "⚠️  Embedding model tests had issues - check output above"
    fi
    echo ""
    echo "💡 Try asking DAS: 'How many UAS are in the specifications?'"
else
    echo ""
    echo "❌ Quick Setup Failed"
    echo "==================="
    echo "Check the output above for errors."
    echo ""
    echo "Common fixes:"
    echo "• Restart ODRAS: ./odras.sh restart"
    echo "• Rebuild database: ./odras.sh clean -y && ./odras.sh init-db"
    echo "• Check services: ./odras.sh status"
    exit 1
fi
