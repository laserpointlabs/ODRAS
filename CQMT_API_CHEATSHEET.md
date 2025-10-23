# CQMT API Cheat Sheet

## Quick Start

### 1. Login and Get Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "das_service", "password": "das_service_2024!"}'
```

Copy the token from response.

### 2. Test Dependencies

**Get MT Dependencies**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/dependencies
```

**Validate Dependencies**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/validation
```

**Find Affected MTs**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/cqmt/ontologies/YOUR_GRAPH_IRI/impact-analysis?element_iri=ELEMENT_IRI"
```

## How to Get IDs

### Get MT ID from UI
1. Open CQMT workbench
2. Find your microtheory
3. Copy the ID from URL or API response

### Get MT ID via API
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/microtheories
```

## What to Expect

### Good Response (All Elements Valid)
```json
{
  "validation_status": "complete",
  "valid_dependencies": 3,
  "invalid_dependencies": 0
}
```

### Bad Response (Some Elements Deleted)
```json
{
  "validation_status": "incomplete",
  "valid_dependencies": 2,
  "invalid_dependencies": 1,
  "broken_references": [
    {
      "element_iri": "...",
      "status": "not_found"
    }
  ]
}
```

## Quick Test Script

```bash
# Setup
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "das_service", "password": "das_service_2024!"}' | jq -r '.token')

# Replace with your MT ID
MT_ID="your-mt-id-here"

# Test dependencies
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/$MT_ID/dependencies | jq .

# Test validation
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/$MT_ID/validation | jq .
```

Copy-paste ready! 🚀
