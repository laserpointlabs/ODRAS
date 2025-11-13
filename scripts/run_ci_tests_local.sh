#!/bin/bash
# Run CI tests locally before committing
# This mirrors the exact test sequence from .github/workflows/ci.yml

set -e

echo "🧪 Running CI tests locally..."
echo "============================================================"

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Warning: Docker services may not be running"
    echo "   Start with: docker-compose up -d"
fi

# Check if ODRAS API is running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "⚠️  Warning: ODRAS API may not be running"
    echo "   Start with: ./odras.sh start"
fi

echo ""
echo "🏃‍♂️ Step 1: Fast DAS Health Check..."
python scripts/fast_das_validator.py

echo ""
echo "🧪 Step 2: Enhanced Ontology Attributes Test..."
python -m pytest tests/test_working_ontology_attributes.py -v --tb=short

echo ""
echo "🧪 Step 3: Baseline DAS Integration Test..."
python tests/test_das_integration_comprehensive.py

echo ""
echo "🧪 Step 4: RAG System Stability Test..."
python tests/test_rag_system_stability.py

echo ""
echo "🧪 Step 4.5: RAG Modularization Test..."
python -m pytest tests/test_rag_modular.py -v --tb=short -m "not integration"

echo ""
echo "🧪 Step 4.6: RAG LLM Configuration Test..."
python -m pytest tests/test_rag_llm_config.py -v --tb=short -m "not integration"

echo ""
echo "🧪 Step 4.7: RAG Hybrid Search and Reranker Test..."
python -m pytest tests/test_rag_hybrid_search.py -v --tb=short -m "not integration"

echo ""
echo "🧪 Step 4.8: RAG Hybrid Search Evaluation Test..."
python -m pytest tests/test_rag_hybrid_search_evaluation.py -v --tb=short -m "not integration"

echo ""
echo "🧪 Step 4.9: RAG Real-World Performance Evaluation..."
python -m pytest tests/test_rag_real_world_evaluation.py -v --tb=short -s || echo "⚠️ Real-world evaluation requires running services"

echo ""
echo "🧪 Step 4.10: RAG CI Verification Test..."
if [ -f "tests/test_rag_ci_verification.py" ]; then
    python -m pytest tests/test_rag_ci_verification.py -v --tb=short -m integration
else
    echo "⚠️  Warning: tests/test_rag_ci_verification.py not found - skipping"
fi

echo ""
echo "🧪 Step 4.11: DAS Training Data Initialization Test..."
python -m pytest tests/test_training_data_initialization.py -v --tb=short -m integration

echo ""
echo "🧪 Step 5: Ontology Inheritance System Test..."
python -m pytest tests/test_inheritance_system.py -v --tb=short

echo ""
echo "🧪 Step 6: CQ/MT Workbench Test..."
python scripts/cqmt_ui_test.py

echo ""
echo "🧪 Step 7: CQMT Dependency Tracking Test..."
python -m pytest tests/test_cqmt_dependency_tracking.py -v --tb=short

echo ""
echo "🧪 Step 8: CQMT Change Detection Test..."
python -m pytest tests/test_ontology_change_detection.py -v --tb=short

echo ""
echo "🧪 Step 9: Individual Tables CRUD Test..."
python -m pytest tests/test_individuals_crud.py -v --tb=short

echo ""
echo "🧪 Step 10: Class Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_class_migration.py -v --tb=short || true

echo ""
echo "🧪 Step 11: Property Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_property_migration.py -v --tb=short || true

echo ""
echo "🧪 Step 12: CQMT Workbench Complete Test..."
python -m pytest tests/test_cqmt_workbench_complete.py -v --tb=short

echo ""
echo "✅ COMPLETE ODRAS system validation finished"
echo "============================================================"
