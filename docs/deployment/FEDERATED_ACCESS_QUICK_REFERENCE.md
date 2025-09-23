# ODRAS Federated Access - Quick Reference<br>
<br>
## 🚀 Quick Start for External Developers<br>
<br>
### 1. Resolve Any ODRAS IRI<br>
<br>
```bash<br>
curl "https://{installation}.{service}.mil/api/iri/public/resolve?iri={IRI}"<br>
```<br>
<br>
**Example:**<br>
```bash<br>
curl "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"<br>
```<br>
<br>
### 2. Download Files<br>
<br>
```bash<br>
curl "https://{installation}.{service}.mil/api/federated/files/{file-id}/download" -o filename.ext<br>
```<br>
<br>
### 3. Get Knowledge Content<br>
<br>
```bash<br>
curl "https://{installation}.{service}.mil/api/federated/knowledge/{asset-id}/content"<br>
```<br>
<br>
---<br>
<br>
## 🌐 Real-World Integration Examples<br>
<br>
### Python One-Liner<br>
```python<br>
import requests<br>
content = requests.get("https://xma-adt.usn.mil/api/iri/public/resolve", params={"iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/analysis"}).json()["access_urls"]["content"]<br>
analysis = requests.get(content).json()<br>
```<br>
<br>
### Bash One-Liner<br>
```bash<br>
curl -s "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/files/report.pdf" | jq -r '.access_urls.download' | xargs curl -o report.pdf<br>
```<br>
<br>
### JavaScript/Browser<br>
```javascript<br>
async function getODRASArtifact(iri) {<br>
    const resolution = await fetch(`https://xma-adt.usn.mil/api/iri/public/resolve?iri=${iri}`).then(r => r.json());<br>
    const content = await fetch(resolution.access_urls.content).then(r => r.json());<br>
    return content;<br>
}<br>
```<br>
<br>
---<br>
<br>
## 📋 Installation Discovery<br>
<br>
### Discover Capabilities<br>
```bash<br>
curl "https://{installation}.{service}.mil/api/federated/installations/discover"<br>
```<br>
<br>
**Response includes:**<br>
- Installation information<br>
- Supported resource types<br>
- Available endpoints<br>
- Contact information<br>
<br>
---<br>
<br>
## 🔒 Access Control Summary<br>
<br>
| Resource Type | Public Access | Private Access | Federated |<br>
|---------------|---------------|----------------|-----------|<br>
| **Public Files** | ✅ Full download | ✅ Full access | ✅ Available |<br>
| **Private Files** | ❌ Contact info only | ✅ Full access | ❌ Protected |<br>
| **Public Knowledge** | ✅ Full content | ✅ Full access | ✅ Available |<br>
| **Private Knowledge** | ❌ Contact info only | ✅ Full access | ❌ Protected |<br>
<br>
---<br>
<br>
## 🛠️ Integration Checklist<br>
<br>
- [ ] Identify target ODRAS installation base URI<br>
- [ ] Test installation discovery endpoint<br>
- [ ] Implement IRI resolution in your system<br>
- [ ] Add error handling for private resources<br>
- [ ] Include proper attribution in your application<br>
- [ ] Test with real IRIs from target installation<br>
- [ ] Implement caching for performance (optional)<br>
<br>
---<br>
<br>
## 📞 Support<br>
<br>
For integration support or access to private resources, contact the installation authority listed in IRI resolution responses:<br>

