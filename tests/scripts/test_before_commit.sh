#!/bin/bash
# Quick test script - run before committing
# Tests the most common failure points

set -e

echo "🔍 Quick Pre-Commit Test Suite"
echo "============================================================"

# Test 1: Hybrid search tests (recent failures)
echo ""
echo "🧪 Test 1: RAG Hybrid Search Tests..."
python -m pytest tests/test_rag_hybrid_search.py -v --tb=short -m "not integration" || {
    echo "❌ Hybrid search tests failed!"
    exit 1
}

# Test 2: Training data initialization
echo ""
echo "🧪 Test 2: DAS Training Data Initialization..."
if [ -f "tests/test_training_data_initialization.py" ]; then
    python -m pytest tests/test_training_data_initialization.py -v --tb=short -m integration || {
        echo "❌ Training data tests failed!"
        exit 1
    }
else
    echo "⚠️  tests/test_training_data_initialization.py not found"
fi

# Test 3: RAG CI verification
echo ""
echo "🧪 Test 3: RAG CI Verification..."
if [ -f "tests/test_rag_ci_verification.py" ]; then
    python -m pytest tests/test_rag_ci_verification.py -v --tb=short -m integration || {
        echo "❌ RAG CI verification tests failed!"
        exit 1
    }
else
    echo "⚠️  tests/test_rag_ci_verification.py not found"
fi

echo ""
echo "✅ Quick pre-commit tests passed!"
echo "============================================================"
echo ""
echo "💡 To run full CI test suite: ./scripts/run_ci_tests_local.sh"
