#!/bin/bash
# Quick test script for CQMT dependency endpoints

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Logging in...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "das_service", "password": "das_service_2024!"}' | jq -r '.token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo -e "${GREEN}✅ Logged in${NC}"

# Get first project
echo -e "${BLUE}📋 Getting projects...${NC}"
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/projects | jq -r '.projects[0].project_id')

if [ "$PROJECT_ID" == "null" ] || [ -z "$PROJECT_ID" ]; then
  echo "❌ No projects found"
  exit 1
fi

echo -e "${GREEN}✅ Found project: $PROJECT_ID${NC}"

# Get first MT
echo -e "${BLUE}📋 Getting microtheories...${NC}"
MT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/projects/$PROJECT_ID/microtheories" | jq -r '.[0].id')

if [ "$MT_ID" == "null" ] || [ -z "$MT_ID" ]; then
  echo "❌ No microtheories found"
  exit 1
fi

echo -e "${GREEN}✅ Found MT: $MT_ID${NC}"

# Get dependencies
echo -e "${BLUE}🔗 Getting dependencies...${NC}"
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/microtheories/$MT_ID/dependencies" | jq .

# Validate
echo -e "${BLUE}✔️  Validating dependencies...${NC}"
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/microtheories/$MT_ID/validation" | jq .

echo -e "${GREEN}✅ Done!${NC}"
