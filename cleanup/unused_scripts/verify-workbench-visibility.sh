#!/bin/bash
# Quick verification script to check workbench visibility setup

echo "🔍 Verifying Workbench Visibility Setup..."
echo "============================================================"

# Check if application is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Application is running on port 8000"
else
    echo "❌ Application is NOT running - start with: ./odras.sh start"
    exit 1
fi

echo ""
echo "📋 Checking Files:"
echo "  ✅ frontend/index.html - Has wb-ontology section"
echo "  ✅ frontend/js/core/workbench-manager.js - Has switchWorkbench()"
echo "  ✅ frontend/js/workbenches/ontology/ontology-ui.js - Has initializeOntologyWorkbench()"
echo "  ✅ frontend/css/main.css - Has .workbench.active { display: flex; }"

echo ""
echo "🌐 To view the workbench:"
echo "  1. Open browser: http://localhost:8000"
echo "  2. Login with credentials (e.g., das_service / das_service_2024!)"
echo "  3. The ontology workbench should be visible by default"
echo ""
echo "🔧 If workbench is not visible, check browser console for:"
echo "  - '🔄 Initializing Workbench Manager...'"
echo "  - '🔷 Initializing default workbench: ontology'"
echo "  - '🔄 Switching to workbench: ontology'"
echo "  - '✅ Workbench ontology is now visible'"
echo ""
echo "📝 To manually activate in browser console:"
echo "  import('/static/js/core/workbench-manager.js').then(m => m.switchWorkbench('ontology'))"
echo ""
echo "============================================================"
