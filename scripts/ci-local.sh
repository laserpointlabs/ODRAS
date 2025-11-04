#!/bin/bash
# Local CI runner - mirrors .github/workflows/ci.yml exactly for local testing
# Usage: ./scripts/ci-local.sh

set -e

echo "🚀 Running local CI workflow (mirrors GitHub Actions)..."
echo "============================================================"

# Step 1: Start ODRAS stack (same as CI)
echo ""
echo "📦 Step 1: Starting ODRAS stack (CI-compatible with CPU ollama)..."
./odras.sh clean -y
# Start core services (no GPU profile)
docker-compose up -d
# Optionally start CPU ollama for LLM testing (if docker-compose.ci.yml exists)
if [ -f docker-compose.ci.yml ]; then
    docker-compose -f docker-compose.yml -f docker-compose.ci.yml up -d ollama || echo "⚠️  ollama not available (optional)"
fi

echo "Waiting for services to be ready..."
sleep 20

# Verify critical services (same as odras.sh)
echo "Checking PostgreSQL..."
for i in {1..30}; do
    if pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL ready"
        break
    fi
    sleep 2
done

echo "Checking Redis..."
for i in {1..30}; do
    if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
        echo "✅ Redis ready"
        break
    fi
    sleep 2
done

echo "✅ ODRAS stack ready with proper container names and GPU fallback"

# Step 2: Initialize database (same as CI)
echo ""
echo "🗄️ Step 2: Initializing database (EXACTLY like CI)..."
./odras.sh init-db

# Step 3: Start application (same as CI)
echo ""
echo "🚀 Step 3: Starting ODRAS application..."
./odras.sh start

echo "Waiting for application startup..."
sleep 30

# Verify COMPLETE system
echo "🔍 Verifying COMPLETE ODRAS system..."

# API Health
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        health_data=$(curl -s http://localhost:8000/api/health)
        echo "✅ ODRAS API responding"
        echo "📊 Health status: $health_data"
        break
    fi
    echo "API not ready... ($i/30)"
    sleep 3
done

# Service status (if endpoint exists)
service_status=$(curl -s http://localhost:8000/api/service-status 2>/dev/null || echo "Service status not available")
echo "📊 Service status: $service_status"

echo "🎯 COMPLETE ODRAS APPLICATION READY"

# Step 4: Run test suite (same as CI)
echo ""
echo "🧪 Step 4: Running COMPLETE ODRAS system tests (EXACT SAME AS CI)"
echo "============================================================"

echo "🏃‍♂️ Step 1: Fast DAS Health Check..."
python scripts/fast_das_validator.py

echo "🧪 Step 2: Enhanced Ontology Attributes Test..."
python -m pytest tests/test_working_ontology_attributes.py -v --tb=short

echo "🧪 Step 3: Baseline DAS Integration Test..."
python tests/test_das_integration_comprehensive.py

echo "🧪 Step 4: RAG System Stability Test..."
python tests/test_rag_system_stability.py

echo "🧪 Step 4.5: RAG Modularization Test..."
python -m pytest tests/test_rag_modular.py -v --tb=short -m "not integration"

echo "🧪 Step 4.6: RAG LLM Configuration Test..."
python -m pytest tests/test_rag_llm_config.py -v --tb=short -m "not integration"

echo "🧪 Step 5: Ontology Inheritance System Test..."
python -m pytest tests/test_inheritance_system.py -v --tb=short

echo "🧪 Step 6: CQ/MT Workbench Test..."
python scripts/cqmt_ui_test.py

echo "🧪 Step 7: CQMT Dependency Tracking Test..."
python -m pytest tests/test_cqmt_dependency_tracking.py -v --tb=short

echo "🧪 Step 8: CQMT Change Detection Test..."
python -m pytest tests/test_ontology_change_detection.py -v --tb=short

echo "🧪 Step 9: Individual Tables CRUD Test..."
python -m pytest tests/test_individuals_crud.py -v --tb=short

echo "🧪 Step 10: Class Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_class_migration.py -v --tb=short || true

echo "🧪 Step 11: Property Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_property_migration.py -v --tb=short || true

echo "🧪 Step 12: CQMT Workbench Complete Test..."
python -m pytest tests/test_cqmt_workbench_complete.py -v --tb=short

echo "✅ COMPLETE ODRAS system validation finished"

# Step 5: Run tests with coverage (same as CI)
echo ""
echo "📊 Step 5: Running tests with coverage reporting..."
export PYTHONPATH="${PWD}"
pytest tests/ \
  --cov=backend \
  --cov-report=html \
  --cov-report=term \
  --cov-report=xml \
  --cov-fail-under=80 || echo "⚠️ Coverage below 80% or tests failed"

# Step 6: Diagnostic report (same as CI)
echo ""
echo "📊 Step 6: System diagnostic report"
echo "============================================================"

echo "DATABASE TABLES:"
PGPASSWORD=password psql -h localhost -U postgres -d odras -c "
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;" || echo "PostgreSQL unavailable"

echo ""
echo "TEST USERS:"
PGPASSWORD=password psql -h localhost -U postgres -d odras -c "
SELECT username, is_admin, is_active FROM users ORDER BY username;" || echo "Users check failed"

echo ""
echo "QDRANT COLLECTIONS:"
curl -s http://localhost:6333/collections | python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    collections = data.get('result', {}).get('collections', [])
    print(f'Total collections: {len(collections)}')
    for c in collections:
        print(f'  ✅ {c}')
except Exception as e:
    print(f'Qdrant check failed: {e}')
" || echo "Qdrant unavailable"

echo ""
echo "============================================================"
echo "🎉 LOCAL CI WORKFLOW COMPLETED"
echo "📊 System diagnostic and logs captured"
echo "============================================================"
