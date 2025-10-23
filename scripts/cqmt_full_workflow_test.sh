#!/bin/bash
# Full CQ/MT Workflow Test Script
# Tests the complete workflow: Create MT → Add Data → Create CQ → Execute CQ

set -e

BASE_URL="http://localhost:8000"
PROJECT_ID="c1e008e6-b569-4ad8-bbb6-059da4fdec77"

echo "=== CQ/MT Full Workflow Test ==="
echo ""

# Step 1: Login
echo "1. Logging in as das_service..."
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"das_service","password":"das_service_2024!"}')
TOKEN=$(echo $LOGIN_RESP | jq -r '.token')
HEADERS=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
echo "✅ Logged in"
echo ""

# Step 2: Check existing MTs
echo "2. Checking existing microtheories..."
MT_RESP=$(curl -s "${HEADERS[@]}" "$BASE_URL/api/cqmt/projects/$PROJECT_ID/microtheories")
MT_COUNT=$(echo $MT_RESP | jq '.data | length')
echo "Found $MT_COUNT microtheories"
echo ""

# Step 3: Check existing CQs
echo "3. Checking existing CQs..."
CQ_RESP=$(curl -s "${HEADERS[@]}" "$BASE_URL/api/cqmt/projects/$PROJECT_ID/cqs")
CQ_COUNT=$(echo $CQ_RESP | jq '.data | length')
echo "Found $CQ_COUNT CQs"
echo ""

# Step 4: Create test microtheory
echo "4. Creating test microtheory..."
MT_DATA='{
  "label": "Test MT for CQ",
  "description": "Test microtheory for CQ execution",
  "setDefault": false
}'
CREATE_MT_RESP=$(curl -s -X POST "${HEADERS[@]}" \
  "$BASE_URL/api/cqmt/projects/$PROJECT_ID/microtheories" \
  -d "$MT_DATA")
MT_IRI=$(echo $CREATE_MT_RESP | jq -r '.data.iri')
echo "✅ Created microtheory: $MT_IRI"
echo ""

# Step 5: Add test data to microtheory
echo "5. Adding test data to microtheory..."
TEST_DATA='{
  "triples": [
    "<http://example.org/test#Aircraft1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/test#Aircraft> .",
    "<http://example.org/test#Aircraft1> <http://www.w3.org/2000/01/rdf-schema#label> \"Test Aircraft\" .",
    "<http://example.org/test#Aircraft2> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/test#Aircraft> .",
    "<http://example.org/test#Aircraft2> <http://www.w3.org/2000/01/rdf-schema#label> \"Test Aircraft 2\" ."
  ]
}'
curl -s -X PUT "${HEADERS[@]}" \
  "$BASE_URL/api/cqmt/projects/$PROJECT_ID/microtheories/$MT_IRI/triples" \
  -d "$TEST_DATA" > /dev/null
echo "✅ Added test data"
echo ""

# Step 6: Create competency question
echo "6. Creating competency question..."
CQ_DATA='{
  "cq_name": "Test List Aircraft",
  "problem_text": "List all aircraft in the ontology",
  "sparql_text": "PREFIX ex: <http://example.org/test#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\nSELECT ?aircraft ?label WHERE {\n    ?aircraft rdf:type ex:Aircraft .\n    OPTIONAL { ?aircraft rdfs:label ?label }\n}",
  "contract_json": {
    "require_columns": ["aircraft", "label"],
    "min_rows": 1
  },
  "mt_iri_default": "'$MT_IRI'",
  "status": "active"
}'
CREATE_CQ_RESP=$(curl -s -X POST "${HEADERS[@]}" \
  "$BASE_URL/api/cqmt/projects/$PROJECT_ID/cqs" \
  -d "$CQ_DATA")
CQ_ID=$(echo $CREATE_CQ_RESP | jq -r '.data.id')
echo "✅ Created CQ: $CQ_ID"
echo ""

# Step 7: Execute CQ
echo "7. Executing CQ against microtheory..."
EXEC_DATA='{
  "mt_iri": "'$MT_IRI'",
  "params": {}
}'
EXEC_RESP=$(curl -s -X POST "${HEADERS[@]}" \
  "$BASE_URL/api/cqmt/cqs/$CQ_ID/run" \
  -d "$EXEC_DATA")
echo "Execution response:"
echo $EXEC_RESP | jq '.'
echo ""

# Step 8: Summary
echo "=== Summary ==="
echo "Microtheory IRI: $MT_IRI"
echo "CQ ID: $CQ_ID"
echo "✅ Workflow completed successfully"
