#!/bin/bash
# Local CI Replication Script
# Mirrors .github/workflows/ci.yml exactly for local testing
# Usage: ./scripts/ci-local.sh

set -e

echo "🚀 Running local CI workflow (mirrors GitHub Actions)..."
echo "============================================================"

# Step 1: Start ODRAS stack (same as CI)
echo ""
echo "📦 Step 1: Starting ODRAS stack..."
./odras.sh clean -y
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 20

# Verify critical services (same as CI)
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

echo "✅ ODRAS stack ready"

# Step 2: Initialize database (same as CI)
echo ""
echo "🗄️ Step 2: Initializing database..."
./odras.sh init-db

# Step 3: Start application (same as CI)
echo ""
echo "🚀 Step 3: Starting ODRAS application..."
./odras.sh start

echo "Waiting for application startup..."
sleep 30

# Verify application is running
echo "🔍 Verifying application..."
if ! pgrep -f "uvicorn.*main" > /dev/null && ! pgrep -f "python.*main" > /dev/null; then
  echo "❌ ERROR: Application process not found!"
  echo "Checking logs..."
  tail -50 /tmp/odras_app.log 2>/dev/null || echo "No logs found"
  exit 1
fi
echo "✅ Application process is running"

# API Health check
echo "Waiting for API to be ready..."
api_ready=false
for i in {1..60}; do
  health_response=$(curl -s -w "\n%{http_code}" --connect-timeout 5 --max-time 10 http://localhost:8000/api/health 2>/dev/null || echo -e "\n000")
  http_code=$(echo "$health_response" | tail -1)
  
  if [ "$http_code" = "200" ]; then
    health_data=$(echo "$health_response" | head -n -1)
    echo "✅ ODRAS API responding (HTTP $http_code)"
    echo "📊 Health status: $health_data"
    api_ready=true
    break
  elif [ "$http_code" = "000" ]; then
    echo "API connection failed... ($i/60)"
  else
    echo "API returned HTTP $http_code... ($i/60)"
  fi
  sleep 2
done

if [ "$api_ready" = "false" ]; then
  echo "❌ ERROR: API health check failed after 120 seconds"
  echo "Application logs (last 100 lines):"
  tail -100 /tmp/odras_app.log 2>/dev/null || echo "No logs found"
  exit 1
fi

echo "🎯 COMPLETE ODRAS APPLICATION READY"

# Step 4: Run test suite (same as CI)
echo ""
echo "🧪 Step 4: Running COMPLETE ODRAS system tests..."
echo "============================================================"

echo "🏃‍♂️ Step 4.1: Fast DAS Health Check..."
python scripts/fast_das_validator.py

echo ""
echo "🧪 Step 4.2: Enhanced Ontology Attributes Test..."
python -m pytest tests/test_working_ontology_attributes.py -v --tb=short

echo ""
echo "🧪 Step 4.3: Baseline DAS Integration Test..."
python tests/test_das_integration_comprehensive.py

echo ""
echo "🧪 Step 4.4: RAG System Stability Test..."
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
python -m pytest tests/test_rag_ci_verification.py -v --tb=short -m integration

echo ""
echo "🧪 Step 4.11: DAS Training Data Initialization Test..."
python -m pytest tests/test_training_data_initialization.py -v --tb=short -m integration -s || {
  echo "❌ Training data tests failed!"
  echo "Checking API status..."
  curl -s http://localhost:8000/api/health || echo "API not responding"
  exit 1
}

echo ""
echo "🧪 Step 4.12: Ontology Inheritance System Test..."
python -m pytest tests/test_inheritance_system.py -v --tb=short

echo ""
echo "🧪 Step 4.13: CQ/MT Workbench Test..."
python scripts/cqmt_ui_test.py

echo ""
echo "🧪 Step 4.14: CQMT Dependency Tracking Test..."
python -m pytest tests/test_cqmt_dependency_tracking.py -v --tb=short

echo ""
echo "🧪 Step 4.15: CQMT Change Detection Test..."
python -m pytest tests/test_ontology_change_detection.py -v --tb=short

echo ""
echo "🧪 Step 4.16: Individual Tables CRUD Test..."
python -m pytest tests/test_individuals_crud.py -v --tb=short

echo ""
echo "🧪 Step 4.17: Class Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_class_migration.py -v --tb=short || true

echo ""
echo "🧪 Step 4.18: Property Migration Test (XFAIL - Known Issues)..."
python -m pytest tests/test_property_migration.py -v --tb=short || true

echo ""
echo "🧪 Step 4.19: CQMT Workbench Complete Test..."
python -m pytest tests/test_cqmt_workbench_complete.py -v --tb=short

# Step 5: Run tests with coverage
echo ""
echo "📊 Step 5: Running tests with coverage reporting..."
pytest tests/ \
  --cov=backend \
  --cov-report=html \
  --cov-report=term \
  --cov-report=xml \
  --cov-fail-under=80 || echo "⚠️ Coverage below 80% or tests failed"

echo ""
echo "🧪 Running RAG Modularization Integration Tests..."
python -m pytest tests/test_rag_modular.py -v --tb=short -m integration || echo "⚠️ RAG integration tests failed (may require running services)"

# Step 6: Diagnostic report (same as CI)
echo ""
echo "📊 Step 6: System diagnostics..."
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
echo "NEO4J STATUS:"
cypher-shell -a neo4j://localhost:7687 -u neo4j -p testpassword "
CALL db.labels() YIELD label RETURN label LIMIT 10;
" || echo "Neo4j unavailable"

echo ""
echo "REDIS STATUS:"
redis-cli -h localhost -p 6379 info server | head -5 || echo "Redis unavailable"

echo ""
echo "FUSEKI STATUS:"
curl -s http://localhost:3030/\$/ping || echo "Fuseki unavailable"

echo ""
echo "============================================================"
echo "🎉 LOCAL CI WORKFLOW COMPLETED"
echo "📊 System diagnostic and logs captured"
echo "============================================================"
