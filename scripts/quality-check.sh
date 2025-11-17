#!/bin/bash
# Comprehensive Code Quality Checks
# Usage: ./scripts/quality-check.sh

set -e

echo "🔍 Running comprehensive code quality checks..."
echo "============================================================"

# 1. Linting (flake8)
echo ""
echo "📝 Step 1: Running flake8 linting..."
if command -v flake8 &> /dev/null; then
    flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics || {
        echo "⚠️ Flake8 found issues (continuing with other checks)..."
    }
else
    echo "⚠️ flake8 not installed, skipping..."
    echo "   Install with: pip install flake8"
fi

# 2. Formatting (black)
echo ""
echo "🎨 Step 2: Checking code formatting with black..."
if command -v black &> /dev/null; then
    black --check backend/ --line-length=100 || {
        echo "⚠️ Black found formatting issues"
        echo "   Run 'black backend/' to auto-format"
    }
else
    echo "⚠️ black not installed, skipping..."
    echo "   Install with: pip install black"
fi

# 3. Type checking (mypy) - optional
echo ""
echo "🔎 Step 3: Running type checking with mypy..."
if command -v mypy &> /dev/null; then
    mypy backend/ --ignore-missing-imports || {
        echo "⚠️ Mypy found type issues (non-blocking)"
    }
else
    echo "ℹ️ mypy not installed, skipping (optional)..."
    echo "   Install with: pip install mypy"
fi

# 4. Security scanning (bandit)
echo ""
echo "🔒 Step 4: Running security scan with bandit..."
if command -v bandit &> /dev/null; then
    bandit -r backend/ -f json -o bandit-report.json || {
        echo "⚠️ Bandit found security issues"
        echo "   Check bandit-report.json for details"
    }
else
    echo "⚠️ bandit not installed, skipping..."
    echo "   Install with: pip install bandit"
fi

# 5. Import sorting (isort) - optional
echo ""
echo "📦 Step 5: Checking import sorting with isort..."
if command -v isort &> /dev/null; then
    isort --check-only backend/ || {
        echo "⚠️ isort found import ordering issues"
        echo "   Run 'isort backend/' to auto-fix"
    }
else
    echo "ℹ️ isort not installed, skipping (optional)..."
    echo "   Install with: pip install isort"
fi

echo ""
echo "============================================================"
echo "✅ Code quality checks completed"
echo "============================================================"
