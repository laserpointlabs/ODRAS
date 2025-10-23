# CQMT API Testing Examples

## Prerequisites

### 1. Get Authentication Token

**Via curl**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "das_service", "password": "das_service_2024!"}'
```

**Response**:
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "user": {
    "user_id": "...",
    "username": "das_service"
  }
}
```

**Save the token**:
```bash
export TOKEN="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

### 2. Find Your MT ID

From the UI, or via API:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/projects/YOUR_PROJECT_ID/microtheories
```

## Dependency Endpoints

### Get MT Dependencies

**Endpoint**: `GET /api/cqmt/microtheories/{mt_id}/dependencies`

**curl command**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/dependencies
```

**Expected response**:
```json
{
  "microtheory_id": "abc-123-def-456",
  "dependencies": [
    {
      "ontology_graph_iri": "http://odras.local/onto/project123/test_ontology",
      "referenced_element_iri": "http://odras.local/onto/project123/test_ontology#Person",
      "element_type": "Class",
      "is_valid": true,
      "first_detected_at": "2025-10-23T08:30:00Z",
      "last_validated_at": "2025-10-23T08:30:00Z"
    }
  ]
}
```

### Validate MT Dependencies

**Endpoint**: `GET /api/cqmt/microtheories/{mt_id}/validation`

**curl command**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/cqmt/microtheories/YOUR_MT_ID/validation
```

**Expected response**:
```json
{
  "microtheory_id": "abc-123-def-456",
  "validation_status": "complete",
  "total_dependencies": 3,
  "valid_dependencies": 3,
  "invalid_dependencies": 0,
  "broken_references": []
}
```

**If elements deleted**:
```json
{
  "microtheory_id": "abc-123-def-456",
  "validation_status": "incomplete",
  "total_dependencies": 3,
  "valid_dependencies": 2,
  "invalid_dependencies": 1,
  "broken_references": [
    {
      "element_iri": "http://odras.local/onto/project123/test_ontology#hasSpeed",
      "element_type": "DatatypeProperty",
      "status": "not_found"
    }
  ]
}
```

### Get Impact Analysis

**Endpoint**: `GET /api/cqmt/ontologies/{graph_iri}/impact-analysis`

**curl command**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/cqmt/ontologies/YOUR_GRAPH_IRI/impact-analysis?element_iri=http://odras.local/onto/project123/test_ontology#Person"
```

**Expected response**:
```json
{
  "ontology_graph_iri": "http://odras.local/onto/project123/test_ontology",
  "element_iri": "http://odras.local/onto/project123/test_ontology#Person",
  "affected_microtheories": [
    "mt-id-1",
    "mt-id-2"
  ]
}
```

## Change Detection

### Save Ontology (Returns Changes)

**Endpoint**: `POST /api/ontology/save`

**Via curl**:
```bash
curl -X POST "http://localhost:8000/api/ontology/save?graph=YOUR_GRAPH_IRI" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  --data-binary @ontology.ttl
```

**Via browser Network tab**:
1. Edit ontology in UI
2. Click Save
3. Open Network tab (F12)
4. Find `POST /api/ontology/save`
5. Click to see response

**Expected response**:
```json
{
  "success": true,
  "graphIri": "http://odras.local/onto/project123/test_ontology",
  "message": "Saved to Fuseki",
  "changes": {
    "total": 2,
    "added": 1,
    "deleted": 1,
    "renamed": 0,
    "modified": 0,
    "affected_mts": ["mt-id-1"]
  }
}
```

## Complete Testing Script

Save this as `test_cqmt_api.sh`:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
USERNAME="das_service"
PASSWORD="das_service_2024!"

echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.token')
echo "✅ Token: ${TOKEN:0:20}..."

# Get project ID (first project)
echo "📋 Getting projects..."
PROJECTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/projects")
PROJECT_ID=$(echo $PROJECTS | jq -r '.projects[0].project_id')
echo "✅ Project ID: $PROJECT_ID"

# Get MTs
echo "📋 Getting microtheories..."
MTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/cqmt/projects/$PROJECT_ID/microtheories")
MT_ID=$(echo $MTS | jq -r '.[0].id')
echo "✅ MT ID: $MT_ID"

# Get dependencies
echo "🔗 Getting dependencies..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/cqmt/microtheories/$MT_ID/dependencies" | jq .

# Validate dependencies
echo "✔️  Validating dependencies..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/cqmt/microtheories/$MT_ID/validation" | jq .

echo "✅ Done!"
```

**Run it**:
```bash
chmod +x test_cqmt_api.sh
./test_cqmt_api.sh
```

## Using Postman/Insomnia

### Setup
1. **Base URL**: `http://localhost:8000`
2. **Headers**: 
   - `Authorization: Bearer YOUR_TOKEN`
   - `Content-Type: application/json`

### Endpoints to Test

1. **Login**:
   - Method: POST
   - URL: `/api/auth/login`
   - Body: `{"username": "das_service", "password": "das_service_2024!"}`

2. **Get Dependencies**:
   - Method: GET
   - URL: `/api/cqmt/microtheories/{mt_id}/dependencies`
   - Headers: `Authorization: Bearer {token}`

3. **Validate**:
   - Method: GET
   - URL: `/api/cqmt/microtheories/{mt_id}/validation`
   - Headers: `Authorization: Bearer {token}`

4. **Impact Analysis**:
   - Method: GET
   - URL: `/api/cqmt/ontologies/{graph_iri}/impact-analysis?element_iri={element_iri}`
   - Headers: `Authorization: Bearer {token}`

## Using Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Login
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "das_service", "password": "das_service_2024!"}
)
token = response.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get MT dependencies
mt_id = "your-mt-id"
response = requests.get(
    f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/dependencies",
    headers=headers
)
print(response.json())

# Validate dependencies
response = requests.get(
    f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/validation",
    headers=headers
)
print(response.json())
```

## Browser Testing

### Check Network Tab

1. **Open browser**: Navigate to CQMT workbench
2. **Open DevTools**: Press F12
3. **Go to Network tab**
4. **Create/update MT**: Trigger dependency tracking
5. **Look for**: `GET /api/cqmt/microtheories/{id}/dependencies`

### Check Save Response

1. **Edit ontology**: Make a change
2. **Save**: Click save button
3. **In Network tab**: Find `POST /api/ontology/save`
4. **Click it**: See response with `changes` field

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Get token |
| `/api/cqmt/microtheories/{id}/dependencies` | GET | List dependencies |
| `/api/cqmt/microtheories/{id}/validation` | GET | Validate references |
| `/api/cqmt/ontologies/{graph}/impact-analysis` | GET | Find affected MTs |
| `/api/ontology/save` | POST | Save (returns changes) |

## Troubleshooting

### "Unauthorized" Error
- Token expired or invalid
- Re-login to get new token

### "Microtheory not found"
- Check MT ID is correct
- MT might have been deleted

### "No dependencies found"
- MT has no triples referencing ontology
- Try adding triples first
