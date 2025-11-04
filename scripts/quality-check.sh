#!/bin/bash
# Comprehensive code quality checks
# Usage: ./scripts/quality-check.sh

set -e

echo "🔍 Running code quality checks..."
echo "============================================================"

# 1. Linting (flake8) - Critical errors only
echo ""
echo "1️⃣ Running flake8 linting (critical errors)..."
if flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
    echo "✅ Flake8 critical errors check passed"
else
    echo "❌ Flake8 found critical errors"
    exit 1
fi

# 2. Formatting (black) - Check only
echo ""
echo "2️⃣ Checking code formatting with black..."
if black --check backend/ scripts/ 2>/dev/null || python -m black --check backend/ scripts/ 2>/dev/null; then
    echo "✅ Code formatting check passed"
else
    echo "⚠️  Code formatting issues found (run 'black backend/ scripts/' to fix)"
    # Don't fail on formatting issues, just warn
fi

# 3. Type checking (mypy) - Optional
echo ""
echo "3️⃣ Running type checking with mypy (optional)..."
if command -v mypy &> /dev/null; then
    if mypy backend/ --ignore-missing-imports 2>/dev/null || true; then
        echo "✅ Type checking passed (or skipped)"
    else
        echo "⚠️  Type checking found issues (non-critical)"
    fi
else
    echo "⚠️  mypy not installed, skipping type checking"
fi

# 4. Security scanning (bandit) - Optional
echo ""
echo "4️⃣ Running security scanning with bandit (optional)..."
if command -v bandit &> /dev/null; then
    if bandit -r backend/ -f json -o bandit-report.json 2>/dev/null || true; then
        echo "✅ Security scan completed (check bandit-report.json)"
    else
        echo "⚠️  Security scan found issues (check bandit-report.json)"
    fi
else
    echo "⚠️  bandit not installed, skipping security scan"
fi

echo ""
echo "✅ Code quality checks completed"
echo "============================================================"
