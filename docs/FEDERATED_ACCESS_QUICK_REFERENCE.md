# ODRAS Federated Access - Quick Reference

## 🚀 Quick Start for External Developers

### 1. Resolve Any ODRAS IRI

```bash
curl "https://{installation}.{service}.mil/api/iri/public/resolve?iri={IRI}"
```

**Example:**
```bash
curl "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"
```

### 2. Download Files

```bash
curl "https://{installation}.{service}.mil/api/federated/files/{file-id}/download" -o filename.ext
```

### 3. Get Knowledge Content

```bash
curl "https://{installation}.{service}.mil/api/federated/knowledge/{asset-id}/content"
```

---

## 🌐 Real-World Integration Examples

### Python One-Liner
```python
import requests
content = requests.get("https://xma-adt.usn.mil/api/iri/public/resolve", params={"iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/analysis"}).json()["access_urls"]["content"]
analysis = requests.get(content).json()
```

### Bash One-Liner  
```bash
curl -s "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/files/report.pdf" | jq -r '.access_urls.download' | xargs curl -o report.pdf
```

### JavaScript/Browser
```javascript
async function getODRASArtifact(iri) {
    const resolution = await fetch(`https://xma-adt.usn.mil/api/iri/public/resolve?iri=${iri}`).then(r => r.json());
    const content = await fetch(resolution.access_urls.content).then(r => r.json());
    return content;
}
```

---

## 📋 Installation Discovery

### Discover Capabilities
```bash
curl "https://{installation}.{service}.mil/api/federated/installations/discover"
```

**Response includes:**
- Installation information
- Supported resource types
- Available endpoints
- Contact information

---

## 🔒 Access Control Summary

| Resource Type | Public Access | Private Access | Federated |
|---------------|---------------|----------------|-----------|
| **Public Files** | ✅ Full download | ✅ Full access | ✅ Available |
| **Private Files** | ❌ Contact info only | ✅ Full access | ❌ Protected |
| **Public Knowledge** | ✅ Full content | ✅ Full access | ✅ Available |
| **Private Knowledge** | ❌ Contact info only | ✅ Full access | ❌ Protected |

---

## 🛠️ Integration Checklist

- [ ] Identify target ODRAS installation base URI
- [ ] Test installation discovery endpoint
- [ ] Implement IRI resolution in your system
- [ ] Add error handling for private resources
- [ ] Include proper attribution in your application
- [ ] Test with real IRIs from target installation
- [ ] Implement caching for performance (optional)

---

## 📞 Support

For integration support or access to private resources, contact the installation authority listed in IRI resolution responses:

- **XMA-ADT**: admin@xma-adt.usn.mil
- **AFIT**: admin@afit-research.usaf.mil  
- **TRADOC**: admin@tradoc-sim.usa.mil

---

## 🎯 Common Use Cases

1. **Cross-Installation Analysis**: Norfolk Naval Base uses XMA-ADT's mission analysis
2. **Academic Research**: AFIT references Navy requirements for research
3. **Industry Integration**: Boeing accesses Navy specifications for design
4. **Tool Integration**: External analysis tools process ODRAS artifacts
5. **Knowledge Sharing**: Share lessons learned across installations
