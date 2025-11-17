#!/bin/bash
# Quick UI Structure Test
# Verifies that UI modules exist and can be loaded (without browser)

set -e

echo "🔍 Testing UI Structure..."
echo "============================================================"

# Check core modules
echo ""
echo "📦 Checking core modules..."
for module in app-init.js state-manager.js api-client.js event-bus.js; do
  if [ -f "frontend/js/core/$module" ]; then
    echo "  ✅ frontend/js/core/$module"
  else
    echo "  ❌ frontend/js/core/$module MISSING"
    exit 1
  fi
done

# Check components
echo ""
echo "🧩 Checking components..."
for component in toolbar.js panel-manager.js modal-dialogs.js; do
  if [ -f "frontend/js/components/$component" ]; then
    echo "  ✅ frontend/js/components/$component"
  else
    echo "  ❌ frontend/js/components/$component MISSING"
    exit 1
  fi
done

# Check workbenches
echo ""
echo "🛠️ Checking workbenches..."
if [ -f "frontend/js/workbenches/requirements/requirements-ui.js" ]; then
  echo "  ✅ Requirements workbench"
else
  echo "  ❌ Requirements workbench MISSING"
  exit 1
fi

if [ -f "frontend/js/workbenches/ontology/ontology-ui.js" ]; then
  echo "  ✅ Ontology workbench"
else
  echo "  ❌ Ontology workbench MISSING"
  exit 1
fi

# Check DAS modules
echo ""
echo "🤖 Checking DAS modules..."
if [ -d "frontend/js/das" ]; then
  echo "  ✅ DAS modules directory exists"
  ls frontend/js/das/*.js 2>/dev/null | while read file; do
    echo "    ✅ $(basename $file)"
  done
else
  echo "  ❌ DAS modules MISSING"
  exit 1
fi

# Check index.html
echo ""
echo "📄 Checking index.html..."
if [ -f "frontend/index.html" ]; then
  echo "  ✅ frontend/index.html exists"
  
  # Check for workbench imports
  if grep -q "initializeRequirementsWorkbench" frontend/index.html; then
    echo "    ✅ Requirements workbench imported"
  else
    echo "    ⚠️ Requirements workbench not imported"
  fi
  
  if grep -q "initializeOntologyWorkbench" frontend/index.html; then
    echo "    ✅ Ontology workbench imported"
  else
    echo "    ⚠️ Ontology workbench not imported"
  fi
else
  echo "  ❌ frontend/index.html MISSING"
  exit 1
fi

# Check UI tests
echo ""
echo "🧪 Checking UI tests..."
if [ -d "tests/ui" ]; then
  echo "  ✅ UI tests directory exists"
  ls tests/ui/*.py 2>/dev/null | while read file; do
    echo "    ✅ $(basename $file)"
  done
else
  echo "  ⚠️ UI tests directory not found"
fi

echo ""
echo "============================================================"
echo "✅ UI Structure Test Complete"
echo "============================================================"
