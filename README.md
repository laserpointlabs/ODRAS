## ODRAS MVP - Camunda BPMN Workflow

Minimal end-to-end prototype that runs requirements analysis as a **BPMN workflow orchestrated by Camunda 7**:

- Upload a document → **BPMN Process Start**
- Extract requirements using keyword patterns → **Script Task 1**
- Run Monte Carlo LLM processing → **Script Task 2** 
- Store results in Qdrant (vector) → **Script Task 3**
- Store results in Neo4j (graph) → **Script Task 4**
- Store results in Fuseki (RDF) → **Script Task 5**
- **BPMN Process Complete**

### Architecture

**BPMN Process Flow:**
```
Document Upload → Extract Requirements → LLM Processing → Vector Store → Graph DB → RDF Store → Complete
```

**Key Benefits:**
- **Visual Workflow**: Modify the process in Camunda Cockpit without code changes
- **Orchestrated Execution**: Each step runs as a script task with proper error handling
- **Real-time Monitoring**: Track process execution in Camunda Cockpit
- **Extensible**: Add new tasks, decision gateways, and parallel branches easily

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Start All Services
```bash
# Start data stores and Camunda
docker compose up -d

# Verify services are running
docker compose ps
```

**Services:**
- **Qdrant**: http://localhost:6333 (Vector Database)
- **Neo4j**: http://localhost:7474 (Graph Database, neo4j/testpassword)
- **Fuseki**: http://localhost:3030 (RDF Database)
- **Ollama**: http://localhost:11434 (Local LLM)
- **Camunda 7**: http://localhost:8080 (BPMN Engine, demo/demo)

### Install & Run Backend
```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn backend.main:app --reload --port 8000
```

**Open UI**: http://localhost:8000

### BPMN Workflow

**Process Definition**: `bpmn/odras_requirements_analysis.bpmn`

**Script Tasks** (executed by Camunda):
1. **Extract Requirements**: Regex-based extraction with keyword patterns
2. **LLM Processing**: Monte Carlo iterations through OpenAI/Ollama
3. **Vector Storage**: Store embeddings and metadata in Qdrant
4. **Graph Storage**: Create nodes/relationships in Neo4j
5. **RDF Storage**: Generate and store RDF triples in Fuseki

**Process Variables**:
- `document_content`: Raw text from uploaded file
- `document_filename`: Original filename
- `llm_provider`: OpenAI or Ollama
- `llm_model`: Specific model to use
- `iterations`: Number of Monte Carlo iterations

### Usage

1. **Start Services**: Ensure Camunda and data stores are running
2. **Upload Document**: Use the web UI to upload a text file
3. **Configure Analysis**: Set LLM provider, model, and iterations
4. **Start Process**: Click "Start BPMN Analysis" to begin
5. **Monitor Execution**: Watch progress in real-time
6. **View Results**: Check Camunda Cockpit for detailed execution logs

### Testing

**Run Integration Tests:**
```bash
# Test Camunda integration
python scripts/test_camunda_integration.py

# Deploy and test BPMN process
python scripts/deploy_to_camunda.py
```

**Manual Testing:**
1. Upload a document with requirements (e.g., "The system shall...")
2. Monitor the BPMN process execution
3. Check data stores for results
4. View process variables and execution history

### LLM Configuration

**OpenAI**: Set `OPENAI_API_KEY` environment variable
**Ollama**: Pull models locally with `docker exec odras_ollama ollama pull llama3:8b-instruct`

### Development

**Modify BPMN Process:**
1. Edit `bpmn/odras_requirements_analysis.bpmn`
2. Update script task logic in `backend/services/camunda_tasks.py`
3. Redeploy to Camunda via UI or script

**Add New Tasks:**
1. Add script task to BPMN file
2. Implement Python function in `camunda_tasks.py`
3. Update task registry
4. Redeploy process

### Next Steps

- [ ] **Real LLM Integration**: Replace simulated LLM calls with actual API calls
- [ ] **Enhanced Extraction**: Add ML-based requirement extraction
- [ ] **Error Handling**: Add retry logic and compensation tasks
- [ ] **Parallel Processing**: Execute tasks in parallel where possible
- [ ] **Decision Gateways**: Add conditional logic based on extraction quality
- [ ] **External Task Workers**: Move heavy processing to external workers
- [ ] **DADMS Integration**: Connect with existing DADMS BPMN patterns

### Troubleshooting

**Camunda Not Starting:**
```bash
# Check logs
docker compose logs camunda7

# Restart service
docker compose restart camunda7
```

**BPMN Deployment Issues:**
- Verify Camunda is running: http://localhost:8080/actuator/health
- Check BPMN file syntax
- Use deployment script: `python scripts/deploy_to_camunda.py`

**Process Execution Errors:**
- Check Camunda Cockpit for detailed error logs
- Verify all data stores are accessible
- Check Python task function implementations


