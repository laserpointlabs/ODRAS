#!/bin/bash
# ODRAS Whitespace Cleanup Script
# Automatically removes trailing whitespace and extra blank lines

set -e

echo "🧹 Cleaning whitespace issues..."

# Find all text files and remove trailing whitespace
find . -type f \( -name "*.py" -o -name "*.sql" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.txt" \) \
    -not -path "./.git/*" \
    -not -path "./.venv/*" \
    -not -path "./node_modules/*" \
    -exec sed -i 's/[[:space:]]*$//' {} \;

# Remove multiple blank lines at end of files
find . -type f \( -name "*.py" -o -name "*.sql" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.txt" \) \
    -not -path "./.git/*" \
    -not -path "./.venv/*" \
    -not -path "./node_modules/*" \
    -exec sed -i -e :a -e '/^\s*$/N;ba' -e 's/\n*$//' {} \;

echo "✅ Whitespace cleanup completed"
echo "📋 Checking for remaining whitespace issues..."

# Check for remaining whitespace issues
if git diff --check >/dev/null 2>&1; then
    echo "✅ No whitespace issues found"
else
    echo "⚠️  Some whitespace issues remain:"
    git diff --check
fi
