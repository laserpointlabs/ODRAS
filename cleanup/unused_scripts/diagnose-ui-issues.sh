#!/bin/bash
# UI Diagnostic Script
# Helps identify why workbench or project creation isn't visible

echo "🔍 ODRAS UI Diagnostic"
echo "============================================================"
echo ""

# Check if app is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Application is NOT running"
    echo "   Start with: ./odras.sh start"
    exit 1
fi

echo "✅ Application is running"
echo ""

echo "📋 Browser Console Checks:"
echo "   Run these in your browser console (F12):"
echo ""
echo "1. Check mainView visibility:"
echo "   document.getElementById('mainView').style.display"
echo "   Expected: 'grid'"
echo ""
echo "2. Check workbench active class:"
echo "   document.getElementById('wb-ontology').classList.contains('active')"
echo "   Expected: true"
echo ""
echo "3. Check project button exists:"
echo "   document.getElementById('addNodeBtn')"
echo "   Expected: <button> element"
echo ""
echo "4. Test project creation:"
echo "   import('/static/js/core/project-manager.js').then(m => m.showCreateProjectModal())"
echo ""
echo "5. Check namespace API:"
echo "   fetch('/api/namespaces/released', {headers: {Authorization: 'Bearer ' + localStorage.getItem('odras_token')}}).then(r => r.json()).then(console.log)"
echo ""
echo "============================================================"
echo ""
echo "🔧 Quick Fixes:"
echo ""
echo "If mainView is not visible:"
echo "  - Check if you're logged in"
echo "  - Check browser console for auth errors"
echo ""
echo "If workbench is not visible:"
echo "  - Check CSS: .workbench.active should have display: flex"
echo "  - Try: import('/static/js/core/workbench-manager.js').then(m => m.switchWorkbench('ontology'))"
echo ""
echo "If project button doesn't work:"
echo "  - Check console for JavaScript errors"
echo "  - Verify project-manager.js is loaded"
echo ""
