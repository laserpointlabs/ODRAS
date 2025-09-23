# ODRAS Installation Setup and IRI System<br>
<br>
## Overview<br>
<br>
This document describes how to set up an ODRAS installation with proper installation-specific IRIs and federated access capabilities. This enables cross-installation artifact sharing and external system integration.<br>
<br>
## Table of Contents<br>
<br>
1. [Installation Configuration](#installation-configuration)<br>
2. [IRI System Setup](#iri-system-setup)<br>
3. [Federated Access](#federated-access)<br>
4. [External System Integration](#external-system-integration)<br>
5. [Security and Access Control](#security-and-access-control)<br>
6. [Troubleshooting](#troubleshooting)<br>
<br>
---<br>
<br>
## Installation Configuration<br>
<br>
### 1. Environment Setup<br>
<br>
Copy the configuration template and customize for your installation:<br>
<br>
```bash<br>
cd /path/to/odras<br>
cp config/installation-specific.env.template .env<br>
```<br>
<br>
### 2. Installation-Specific Configuration<br>
<br>
Edit your `.env` file with installation-specific values:<br>
<br>
```bash<br>
# =============================================================================<br>
# INSTALLATION-SPECIFIC IRI CONFIGURATION<br>
# =============================================================================<br>
<br>
# XMA-ADT (Navy) Installation Example<br>
INSTALLATION_NAME=XMA-ADT<br>
INSTALLATION_TYPE=usn<br>
TOP_LEVEL_DOMAIN=mil<br>
INSTALLATION_BASE_URI=https://xma-adt.usn.mil<br>
INSTALLATION_ORGANIZATION=U.S. Navy XMA-ADT<br>
INSTALLATION_PROGRAM_OFFICE=Naval Air Systems Command<br>
AUTHORITY_CONTACT=admin@xma-adt.usn.mil<br>
```<br>
<br>
### 3. Service Branch Configurations<br>
<br>
#### Navy Installation<br>
```bash<br>
INSTALLATION_NAME=XMA-ADT<br>
INSTALLATION_TYPE=usn<br>
TOP_LEVEL_DOMAIN=mil<br>
INSTALLATION_BASE_URI=https://xma-adt.usn.mil<br>
```<br>
<br>
#### Air Force Installation<br>
```bash<br>
INSTALLATION_NAME=AFIT-RESEARCH<br>
INSTALLATION_TYPE=usaf<br>
TOP_LEVEL_DOMAIN=mil<br>
INSTALLATION_BASE_URI=https://afit-research.usaf.mil<br>
```<br>
<br>
#### Army Installation<br>
```bash<br>
INSTALLATION_NAME=TRADOC-SIM<br>
INSTALLATION_TYPE=usa<br>
TOP_LEVEL_DOMAIN=mil<br>
INSTALLATION_BASE_URI=https://tradoc-sim.usa.mil<br>
```<br>
<br>
#### Industry Partner<br>
```bash<br>
INSTALLATION_NAME=BOEING-DEFENSE<br>
INSTALLATION_TYPE=industry<br>
TOP_LEVEL_DOMAIN=com<br>
INSTALLATION_BASE_URI=https://boeing-defense.boeing.com<br>
```<br>
<br>
### 4. Database Migration<br>
<br>
Run the IRI system migration:<br>
<br>
```bash<br>
cd /path/to/odras<br>
python -c "<br>
import psycopg2<br>
from backend.services.config import Settings<br>
<br>
settings = Settings()<br>
conn = psycopg2.connect(<br>
    host=settings.postgres_host,<br>
    database=settings.postgres_database,<br>
    user=settings.postgres_user,<br>
    password=settings.postgres_password,<br>
    port=settings.postgres_port<br>
)<br>
<br>
with open('backend/migrations/015_installation_specific_iris.sql', 'r') as f:<br>
    migration_sql = f.read()<br>
<br>
with conn.cursor() as cur:<br>
    cur.execute(migration_sql)<br>
    conn.commit()<br>
<br>
print('✅ IRI system migration completed')<br>
conn.close()<br>
"<br>
```<br>
<br>
---<br>
<br>
## IRI System Setup<br>
<br>
### 1. IRI Structure<br>
<br>
ODRAS uses hierarchical, installation-specific IRIs:<br>
<br>
```<br>
Base Pattern:<br>
https://{installation}.{service}.{tld}/program/{program}/project/{project}/{resource_type}/{resource_id}<br>
<br>
Examples:<br>
├── Files: https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf<br>
├── Knowledge: https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis<br>
├── Ontologies: https://xma-adt.usn.mil/program/abc/project/xyz/ontologies/requirements<br>
└── Core: https://xma-adt.usn.mil/core/ontologies/odras-base<br>
```<br>
<br>
### 2. Automatic IRI Generation<br>
<br>
IRIs are automatically generated when resources are created:<br>
<br>
- **Files**: Get IRIs on upload<br>
- **Knowledge Assets**: Get IRIs during processing<br>
- **Projects**: Get IRIs on creation<br>
- **Users**: Get IRIs on account creation<br>
<br>
### 3. IRI Components<br>
<br>
Each IRI contains:<br>
- **Installation Identity**: `xma-adt.usn.mil`<br>
- **Hierarchical Path**: `program/abc/project/xyz`<br>
- **Resource Type**: `files`, `knowledge`, `ontologies`<br>
- **Unique Identifier**: UUID or sanitized name<br>
<br>
### 4. Validation<br>
<br>
Check your IRI configuration:<br>
<br>
```bash<br>
curl -X GET "http://localhost:8000/api/iri/installation-config"<br>
```<br>
<br>
---<br>
<br>
## Federated Access<br>
<br>
### 1. Public IRI Resolution<br>
<br>
External systems can resolve any IRI from your installation:<br>
<br>
```bash<br>
# Resolve IRI to get access information<br>
curl -X GET "https://xma-adt.usn.mil/api/iri/public/resolve?iri={IRI}" \<br>
  -H "Accept: application/json"<br>
```<br>
<br>
**Response:**<br>
```json<br>
{<br>
  "iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis",<br>
  "resource_type": "knowledge_asset",<br>
  "status": "public",<br>
  "access_urls": {<br>
    "content": "https://xma-adt.usn.mil/api/federated/knowledge/{id}/content",<br>
    "metadata": "https://xma-adt.usn.mil/api/federated/knowledge/{id}/metadata"<br>
  },<br>
  "authority": {<br>
    "organization": "U.S. Navy XMA-ADT",<br>
    "contact": "admin@xma-adt.usn.mil",<br>
    "installation": "XMA-ADT"<br>
  }<br>
}<br>
```<br>
<br>
### 2. Direct Artifact Access<br>
<br>
Once you have the access URLs, get the actual artifacts:<br>
<br>
```bash<br>
# Download file content<br>
curl -X GET "https://xma-adt.usn.mil/api/federated/files/{file-id}/download" \<br>
  -o downloaded-file.pdf<br>
<br>
# Get knowledge asset content and analysis results<br>
curl -X GET "https://xma-adt.usn.mil/api/federated/knowledge/{asset-id}/content" \<br>
  -H "Accept: application/json"<br>
```<br>
<br>
### 3. Installation Discovery<br>
<br>
Discover an installation's capabilities:<br>
<br>
```bash<br>
curl -X GET "https://xma-adt.usn.mil/api/federated/installations/discover"<br>
```<br>
<br>
**Response:**<br>
```json<br>
{<br>
  "installation": {<br>
    "name": "XMA-ADT",<br>
    "type": "usn",<br>
    "organization": "U.S. Navy XMA-ADT",<br>
    "base_uri": "https://xma-adt.usn.mil",<br>
    "contact": "admin@xma-adt.usn.mil"<br>
  },<br>
  "capabilities": {<br>
    "supported_resource_types": ["files", "knowledge", "ontologies", "projects"],<br>
    "supported_formats": ["json", "rdf", "turtle"],<br>
    "federated_access": true,<br>
    "public_resolution": true<br>
  },<br>
  "endpoints": {<br>
    "iri_resolution": "https://xma-adt.usn.mil/api/iri/public/resolve",<br>
    "file_download": "https://xma-adt.usn.mil/api/federated/files/{file_id}/download",<br>
    "knowledge_content": "https://xma-adt.usn.mil/api/federated/knowledge/{asset_id}/content"<br>
  }<br>
}<br>
```<br>
<br>
---<br>
<br>
## External System Integration<br>
<br>
### 1. Python Integration Example<br>
<br>
```python<br>
import requests<br>
<br>
class ODRASFederatedClient:<br>
    def __init__(self, installation_base_uri):<br>
        self.base_uri = installation_base_uri.rstrip('/')<br>
<br>
    def resolve_iri(self, iri):<br>
        """Resolve an ODRAS IRI to get access information."""<br>
        response = requests.get(<br>
            f"{self.base_uri}/api/iri/public/resolve",<br>
            params={"iri": iri, "include_content_url": True}<br>
        )<br>
        response.raise_for_status()<br>
        return response.json()<br>
<br>
    def get_file_content(self, iri):<br>
        """Download file content using IRI."""<br>
        resolution = self.resolve_iri(iri)<br>
        if resolution["resource_type"] != "file":<br>
            raise ValueError("IRI does not point to a file")<br>
<br>
        download_url = resolution["access_urls"]["download"]<br>
        response = requests.get(download_url)<br>
        response.raise_for_status()<br>
        return response.content<br>
<br>
    def get_knowledge_content(self, iri):<br>
        """Get knowledge asset content and analysis results."""<br>
        resolution = self.resolve_iri(iri)<br>
        if resolution["resource_type"] != "knowledge_asset":<br>
            raise ValueError("IRI does not point to a knowledge asset")<br>
<br>
        content_url = resolution["access_urls"]["content"]<br>
        response = requests.get(content_url)<br>
        response.raise_for_status()<br>
        return response.json()<br>
<br>
# Usage Example<br>
client = ODRASFederatedClient("https://xma-adt.usn.mil")<br>
<br>
# Get mission analysis from XMA-ADT<br>
analysis_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"<br>
analysis_data = client.get_knowledge_content(analysis_iri)<br>
<br>
# Get requirements document<br>
requirements_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf"<br>
requirements_pdf = client.get_file_content(requirements_iri)<br>
```<br>
<br>
### 2. Curl Script Example<br>
<br>
```bash<br>
#!/bin/bash<br>
# Federated ODRAS Access Script<br>
<br>
INSTALLATION_BASE="https://xma-adt.usn.mil"<br>
IRI="$1"<br>
<br>
if [ -z "$IRI" ]; then<br>
    echo "Usage: $0 <IRI>"<br>
    echo "Example: $0 https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"<br>
    exit 1<br>
fi<br>
<br>
echo "🔍 Resolving IRI: $IRI"<br>
<br>
# Step 1: Resolve IRI<br>
RESOLUTION=$(curl -s "$INSTALLATION_BASE/api/iri/public/resolve?iri=$IRI")<br>
echo "📋 Resolution response:"<br>
echo "$RESOLUTION" | jq .<br>
<br>
# Step 2: Extract content URL and fetch content<br>
CONTENT_URL=$(echo "$RESOLUTION" | jq -r '.access_urls.content // .access_urls.download')<br>
<br>
if [ "$CONTENT_URL" != "null" ]; then<br>
    echo "📄 Fetching content from: $CONTENT_URL"<br>
    curl -s "$CONTENT_URL" | jq . || curl -s "$CONTENT_URL"<br>
else<br>
    echo "❌ No content URL available"<br>
fi<br>
```<br>
<br>
### 3. JavaScript/Node.js Integration<br>
<br>
```javascript<br>
class ODRASFederatedClient {<br>
    constructor(installationBaseUri) {<br>
        this.baseUri = installationBaseUri.replace(/\/$/, '');<br>
    }<br>
<br>
    async resolveIRI(iri) {<br>
        const response = await fetch(<br>
            `${this.baseUri}/api/iri/public/resolve?iri=${encodeURIComponent(iri)}&include_content_url=true`<br>
        );<br>
<br>
        if (!response.ok) {<br>
            throw new Error(`IRI resolution failed: ${response.status}`);<br>
        }<br>
<br>
        return await response.json();<br>
    }<br>
<br>
    async getKnowledgeContent(iri) {<br>
        const resolution = await this.resolveIRI(iri);<br>
<br>
        if (resolution.resource_type !== 'knowledge_asset') {<br>
            throw new Error('IRI does not point to a knowledge asset');<br>
        }<br>
<br>
        const contentResponse = await fetch(resolution.access_urls.content);<br>
        if (!contentResponse.ok) {<br>
            throw new Error(`Content access failed: ${contentResponse.status}`);<br>
        }<br>
<br>
        return await contentResponse.json();<br>
    }<br>
}<br>
<br>
// Usage<br>
const client = new ODRASFederatedClient('https://xma-adt.usn.mil');<br>
const analysisData = await client.getKnowledgeContent(<br>
    'https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis'<br>
);<br>
```<br>
<br>
---<br>
<br>
## Security and Access Control<br>
<br>
### 1. Public vs Private Resources<br>
<br>
**Public Resources:**<br>
- ✅ Accessible via federated endpoints<br>
- ✅ No authentication required<br>
- ✅ Full content and metadata available<br>
<br>
**Private Resources:**<br>
- ❌ Not accessible via federated endpoints<br>
- ❌ Returns contact information for access requests<br>
- ❌ Metadata only (no content)<br>
<br>
### 2. Making Resources Public<br>
<br>
**For Files:**<br>
```bash<br>
# Admin can make files public via API<br>
curl -X PUT "http://localhost:8000/api/files/{file-id}/visibility" \<br>
  -H "Authorization: Bearer {admin-token}" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"visibility": "public"}'<br>
```<br>
<br>
**For Knowledge Assets:**<br>
```bash<br>
# Admin can make knowledge assets public<br>
curl -X PUT "http://localhost:8000/api/knowledge/assets/{asset-id}/public" \<br>
  -H "Authorization: Bearer {admin-token}" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"is_public": true}'<br>
```<br>
<br>
### 3. Access Logging<br>
<br>
All federated access is logged with:<br>
- Source IP address<br>
- Requested IRI<br>
- Access timestamp<br>
- Resource type accessed<br>
- Success/failure status<br>
<br>
---<br>
<br>
## External System Integration<br>
<br>
### 1. Integration Patterns<br>
<br>
**Pattern 1: Direct IRI Resolution**<br>
```python<br>
# External system has an IRI and wants the artifact<br>
iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"<br>
content = resolve_and_fetch_content(iri)<br>
```<br>
<br>
**Pattern 2: Resource Discovery**<br>
```python<br>
# External system discovers available resources<br>
discovery = discover_installation("https://xma-adt.usn.mil")<br>
available_endpoints = discovery["endpoints"]<br>
```<br>
<br>
**Pattern 3: Artifact Citation**<br>
```python<br>
# External system cites ODRAS artifacts in reports<br>
citation = {<br>
    "source": "U.S. Navy XMA-ADT ODRAS",<br>
    "iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis",<br>
    "title": "Mission Analysis Results",<br>
    "accessed_at": "2025-09-16T15:30:00Z",<br>
    "authority": "admin@xma-adt.usn.mil"<br>
}<br>
```<br>
<br>
### 2. Use Cases<br>
<br>
**Cross-Installation Collaboration:**<br>
- Norfolk Naval Base references XMA-ADT's mission analysis<br>
- AFIT Research uses Navy requirements for academic study<br>
- Boeing Defense integrates Navy specifications into design<br>
<br>
**External Tool Integration:**<br>
- Analysis tools pull ODRAS artifacts for processing<br>
- Reporting systems cite ODRAS knowledge assets<br>
- Simulation tools use ODRAS ontologies and data<br>
<br>
**Knowledge Sharing:**<br>
- Share analysis results between installations<br>
- Reference requirements across programs<br>
- Distribute best practices and lessons learned<br>
<br>
### 3. Authentication for Internal Access<br>
<br>
For authenticated access (internal users), use standard API endpoints:<br>
<br>
```bash<br>
# Internal access with authentication<br>
curl -X GET "http://localhost:8000/api/knowledge/assets/{asset-id}/content" \<br>
  -H "Authorization: Bearer {user-token}"<br>
```<br>
<br>
---<br>
<br>
## API Endpoints Reference<br>
<br>
### 1. IRI Resolution Endpoints<br>
<br>
| Endpoint | Purpose | Authentication |<br>
|----------|---------|----------------|<br>
| `GET /api/iri/resolve` | Resolve IRI (internal) | Required |<br>
| `GET /api/iri/public/resolve` | Resolve IRI (federated) | None |<br>
| `GET /api/iri/validate` | Validate IRI format | Required |<br>
| `GET /api/iri/installation-config` | Get installation config | Required |<br>
<br>
### 2. Federated Access Endpoints<br>
<br>
| Endpoint | Purpose | Authentication |<br>
|----------|---------|----------------|<br>
| `GET /api/federated/files/{id}/download` | Download public file | None |<br>
| `GET /api/federated/files/{id}/metadata` | Get file metadata | None |<br>
| `GET /api/federated/knowledge/{id}/content` | Get knowledge content | None |<br>
| `GET /api/federated/knowledge/{id}/metadata` | Get knowledge metadata | None |<br>
| `GET /api/federated/installations/discover` | Installation discovery | None |<br>
<br>
### 3. Example API Calls<br>
<br>
**Resolve IRI:**<br>
```bash<br>
curl "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/files/analysis.pdf"<br>
```<br>
<br>
**Download File:**<br>
```bash<br>
curl "https://xma-adt.usn.mil/api/federated/files/12345678-1234-1234-1234-123456789abc/download" -o analysis.pdf<br>
```<br>
<br>
**Get Knowledge Content:**<br>
```bash<br>
curl "https://xma-adt.usn.mil/api/federated/knowledge/87654321-4321-4321-4321-210987654321/content"<br>
```<br>
<br>
---<br>
<br>
## Frontend IRI Features<br>
<br>
### 1. IRI Display<br>
<br>
**Files Page:**<br>
- **IRI Column**: Compact buttons instead of long text<br>
- **🔗 Copy Button**: Instantly copy IRI to clipboard<br>
- **ℹ️ Details Button**: View full IRI breakdown<br>
<br>
**Knowledge Management Page:**<br>
- **IRI Display**: Clickable IRI under asset title<br>
- **Component Breakdown**: Shows installation, program, project, resource type<br>
<br>
### 2. IRI Details Modal<br>
<br>
Click the ℹ️ button to see:<br>
- **Full IRI**: Complete installation-specific IRI<br>
- **Component Breakdown**: Domain, program, project, resource type<br>
- **Installation Info**: Authority and contact information<br>
- **Copy Functionality**: Easy IRI copying<br>
<br>
---<br>
<br>
## Security and Access Control<br>
<br>
### 1. Access Levels<br>
<br>
**Public Access (Federated):**<br>
- ✅ No authentication required<br>
- ✅ Public resources only<br>
- ✅ Full content and metadata<br>
- ✅ Cross-installation sharing<br>
<br>
**Private Access (Internal):**<br>
- 🔐 Authentication required<br>
- 🔐 All resources (public and private)<br>
- 🔐 Full ODRAS functionality<br>
- 🔐 Project-based permissions<br>
<br>
### 2. Making Resources Public<br>
<br>
**Admin Controls:**<br>
- Files can be made public via admin interface<br>
- Knowledge assets can be made public via admin interface<br>
- Public resources are accessible via federated endpoints<br>
<br>
**Security Considerations:**<br>
- Only admins can make resources public<br>
- Public resources are accessible to anyone<br>
- Private resources return contact info for access requests<br>
<br>
---<br>
<br>
## Troubleshooting<br>
<br>
### 1. Common Issues<br>
<br>
**"No IRI" in Frontend:**<br>
```bash<br>
# Check if backend includes IRI in response<br>
curl "http://localhost:8000/api/files?project_id={project-id}" | jq '.[0].iri'<br>
<br>
# If null, check database:<br>
psql -d odras -c "SELECT filename, iri FROM files WHERE iri IS NOT NULL LIMIT 5;"<br>
```<br>
<br>
**IRI Resolution Fails:**<br>
```bash<br>
# Validate IRI format<br>
curl "http://localhost:8000/api/iri/validate?iri={your-iri}"<br>
<br>
# Check installation config<br>
curl "http://localhost:8000/api/iri/installation-config"<br>
```<br>
<br>
**Federated Access Denied:**<br>
- Ensure resource is marked as public<br>
- Check if installation base URI is correct<br>
- Verify network connectivity between installations<br>
<br>
### 2. Validation Commands<br>
<br>
**Check Installation Configuration:**<br>
```bash<br>
python -c "<br>
from backend.services.config import Settings<br>
from backend.services.installation_iri_service import get_installation_iri_service<br>
<br>
settings = Settings()<br>
iri_service = get_installation_iri_service(settings)<br>
<br>
print('Installation Config:')<br>
print(f'  Base URI: {iri_service.installation_base_uri}')<br>
print(f'  Type: {settings.installation_type}')<br>
print(f'  Organization: {settings.installation_organization}')<br>
<br>
issues = iri_service.validate_installation_config()<br>
if issues:<br>
    print('⚠️  Configuration Issues:')<br>
    for issue in issues:<br>
        print(f'  - {issue}')<br>
else:<br>
    print('✅ Configuration is valid')<br>
"<br>
```<br>
<br>
**Test IRI Generation:**<br>
```bash<br>
python -c "<br>
from backend.services.installation_iri_service import get_installation_iri_service<br>
<br>
iri_service = get_installation_iri_service()<br>
test_iri = iri_service.generate_file_iri(<br>
    'caee53ce-4b7a-4da0-937b-8f4664eb3462',<br>
    'test.pdf',<br>
    '12345678-1234-1234-1234-123456789abc'<br>
)<br>
print(f'Generated IRI: {test_iri}')<br>
"<br>
```<br>
<br>
### 3. Migration Issues<br>
<br>
**If migration fails:**<br>
```bash<br>
# Check migration status<br>
psql -d odras -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'files' AND column_name = 'iri';"<br>
<br>
# Re-run migration if needed<br>
python -c "exec(open('backend/migrations/015_installation_specific_iris.sql').read())"<br>
```<br>
<br>
---<br>
<br>
## Best Practices<br>
<br>
### 1. IRI Design<br>
- ✅ Use installation-specific domains<br>
- ✅ Follow hierarchical structure<br>
- ✅ Include authority information<br>
- ✅ Make IRIs dereferenceable<br>
<br>
### 2. Federated Sharing<br>
- ✅ Only make necessary resources public<br>
- ✅ Include proper attribution and contact info<br>
- ✅ Log all federated access<br>
- ✅ Provide clear access policies<br>

