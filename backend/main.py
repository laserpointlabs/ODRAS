from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
import uvicorn
import asyncio
import orjson
import requests
import json

from .services.config import Settings
import httpx


app = FastAPI(title="ODRAS API", version="0.1.0")

# Camunda configuration
CAMUNDA_BASE_URL = "http://localhost:8080"
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

# Simple in-memory run registry (MVP). Replace with Redis/DB later.
RUNS: Dict[str, Dict] = {}


@app.on_event("startup")
async def on_startup():
    # Ensure services are initialized lazily via Settings
    Settings()  # loads env


@app.post("/api/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    iterations: int = Form(10),
    llm_provider: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
):
    """Upload document and start Camunda BPMN process."""
    try:
        content = await file.read()
        document_text = content.decode('utf-8', errors='ignore')
        
        # Ensure filename is never None
        document_filename = file.filename or "unknown_document.txt"
        
        # Start Camunda BPMN process
        process_id = await start_camunda_process(
            document_content=document_text,
            document_filename=document_filename,
            llm_provider=llm_provider or "openai",
            llm_model=llm_model or "gpt-4o-mini",
            iterations=iterations
        )
        
        if not process_id:
            raise HTTPException(status_code=500, detail="Failed to start Camunda process")
        
        # Store run info
        run_id = str(process_id)
        RUNS[run_id] = {
            "status": "started",
            "process_id": process_id,
            "filename": document_filename,
            "iterations": iterations,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "camunda_url": f"{CAMUNDA_BASE_URL}/cockpit/default/#/process-instance/{process_id}"
        }
        
        return {"run_id": run_id, "status": "started", "process_id": process_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def start_camunda_process(document_content: str, document_filename: str, 
                               llm_provider: str, llm_model: str, iterations: int) -> Optional[str]:
    """Start a new Camunda BPMN process instance."""
    
    # First, ensure the BPMN is deployed
    deployment_id = await deploy_bpmn_if_needed()
    if not deployment_id:
        return None
    
    # Start process instance
    start_url = f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis/start"
    
    variables = {
        "document_content": {
            "value": document_content,
            "type": "String"
        },
        "document_filename": {
            "value": document_filename,
            "type": "String"
        },
        "llm_provider": {
            "value": llm_provider,
            "type": "String"
        },
        "llm_model": {
            "value": llm_model,
            "type": "String"
        },
        "iterations": {
            "value": iterations,
            "type": "Integer"
        }
    }
    
    payload = {
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(start_url, json=payload)
            response.raise_for_status()
            
            process_info = response.json()
            return process_info['id']
            
    except Exception as e:
        print(f"Failed to start Camunda process: {e}")
        return None


async def deploy_bpmn_if_needed() -> Optional[str]:
    """Deploy the BPMN file to Camunda if not already deployed."""
    
    # Check if already deployed
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis")
            if response.status_code == 200:
                # Already deployed
                return "already_deployed"
    except:
        pass
    
    # Deploy BPMN
    deploy_url = f"{CAMUNDA_REST_API}/deployment/create"
    
    try:
        # Read BPMN file
        bpmn_path = "bpmn/odras_requirements_analysis.bpmn"
        with open(bpmn_path, 'rb') as f:
            bpmn_content = f.read()
        
        files = {
            'file': ('odras_requirements_analysis.bpmn', bpmn_content, 'application/xml')
        }
        
        data = {
            'deployment-name': 'odras-requirements-analysis',
            'enable-duplicate-filtering': 'true'
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(deploy_url, files=files, data=data)
            response.raise_for_status()
            
            deployment_info = response.json()
            return deployment_info['id']
            
    except Exception as e:
        print(f"Failed to deploy BPMN: {e}")
        return None


@app.get("/api/runs/{run_id}", response_model=dict)
async def get_run_status(run_id: str):
    """Get the status of a run from Camunda."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run not found")
    
    run_info = RUNS[run_id]
    process_id = run_info.get("process_id")
    
    if not process_id or process_id == "already_deployed":
        return run_info
    
    # Get status from Camunda
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get process instance status
            status_response = await client.get(f"{CAMUNDA_REST_API}/process-instance/{process_id}")
            if status_response.status_code == 200:
                status_info = status_response.json()
                
                # Get process variables
                variables_response = await client.get(f"{CAMUNDA_REST_API}/process-instance/{process_id}/variables")
                variables = {}
                if variables_response.status_code == 200:
                    variables = variables_response.json()
                
                # Update run info
                run_info.update({
                    "camunda_status": status_info.get("state", "unknown"),
                    "variables": variables
                })
                
                # Check if completed
                if status_info.get("state") == "completed":
                    run_info["status"] = "completed"
                
    except Exception as e:
        run_info["camunda_error"] = str(e)
    
    return run_info


@app.get("/api/camunda/status")
async def get_camunda_status():
    """Get Camunda engine status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CAMUNDA_BASE_URL}/actuator/health")
            if response.status_code == 200:
                return {"status": "running", "url": CAMUNDA_BASE_URL}
            else:
                return {"status": "error", "url": CAMUNDA_BASE_URL}
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "url": CAMUNDA_BASE_URL}


@app.get("/api/camunda/deployments")
async def get_camunda_deployments():
    """Get list of deployed BPMN processes."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CAMUNDA_REST_API}/deployment")
            if response.status_code == 200:
                return {"deployments": response.json()}
            else:
                return {"deployments": [], "error": "Failed to fetch deployments"}
    except Exception as e:
        return {"deployments": [], "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index():
    # Minimal HTML UI
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>ODRAS MVP - Camunda BPMN</title>
      <style>
        body { font-family: system-ui, Arial, sans-serif; margin: 2rem; }
        .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; max-width: 640px; margin-bottom: 1rem; }
        label { display: block; margin: 0.5rem 0 0.25rem; }
        input[type=file], input[type=number], select, input[name="llm_model"] { width: 100%; padding: 0.5rem; box-sizing: border-box; }
        button { margin-top: 1rem; padding: 0.5rem 1rem; margin-right: 0.5rem; }
        pre { background: #f9fafb; padding: 1rem; border-radius: 6px; overflow-x: auto; }
        .status { padding: 0.5rem; border-radius: 4px; margin: 0.5rem 0; }
        .status.running { background: #dbeafe; color: #1e40af; }
        .status.completed { background: #dcfce7; color: #166534; }
        .status.error { background: #fee2e2; color: #dc2626; }
      </style>
    </head>
    <body>
      <h1>ODRAS MVP - Camunda BPMN</h1>
      
      <div class="card">
        <h3>Camunda Status</h3>
        <div id="camunda-status">Checking...</div>
        <button onclick="checkCamundaStatus()">Refresh Status</button>
      </div>
      
      <div class="card">
        <h3>Document Analysis</h3>
        <form id="upload-form">
          <label>Document</label>
          <input type="file" name="file" required />
          <label>Monte Carlo Iterations</label>
          <input type="number" name="iterations" value="10" min="1" />
          <label>LLM Provider</label>
          <select name="llm_provider">
            <option value="">(default)</option>
            <option value="openai">OpenAI</option>
            <option value="ollama">Ollama (local)</option>
          </select>
          <label>LLM Model</label>
          <input name="llm_model" list="models-list" placeholder="gpt-4o-mini / llama3:8b-instruct" />
          <datalist id="models-list"></datalist>
          <button type="submit">Start BPMN Analysis</button>
        </form>
        <div id="result"></div>
      </div>
      
      <div class="card">
        <h3>Active Runs</h3>
        <div id="runs-list">Loading...</div>
        <button onclick="refreshRuns()">Refresh Runs</button>
      </div>
      
      <script>
        const form = document.getElementById('upload-form');
        const result = document.getElementById('result');
        const providerSelect = document.querySelector('select[name="llm_provider"]');
        const modelInput = document.querySelector('input[name="llm_model"]');
        const modelsList = document.getElementById('models-list');
        
        // Check Camunda status on page load
        checkCamundaStatus();
        refreshRuns();
        
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const data = new FormData(form);
          result.innerHTML = '<div class="status running">Starting BPMN process...</div>';
          
          const res = await fetch('/api/upload', { method: 'POST', body: data });
          const json = await res.json();
          
          if (!res.ok) { 
            result.innerHTML = `<div class="status error">Error: ${JSON.stringify(json)}</div>`; 
            return; 
          }
          
          result.innerHTML = `<div class="status running">BPMN process started: ${json.process_id}</div>`;
          refreshRuns();
          
          // Poll for completion
          const interval = setInterval(async () => {
            const sres = await fetch(`/api/runs/${json.run_id}`);
            const sjson = await sres.json();
            
            if (sjson.status === 'completed') {
              result.innerHTML = `<div class="status completed">Process completed! <a href="${sjson.camunda_url}" target="_blank">View in Camunda</a></div>`;
              clearInterval(interval);
              refreshRuns();
            } else if (sjson.camunda_error) {
              result.innerHTML = `<div class="status error">Camunda error: ${sjson.camunda_error}</div>`;
              clearInterval(interval);
            }
          }, 2000);
        });

        providerSelect.addEventListener('change', async () => {
          const provider = providerSelect.value;
          modelsList.innerHTML = '';
          modelInput.value = '';
          if (!provider) return;
          try {
            const res = await fetch(`/api/models/${provider}`);
            const json = await res.json();
            const names = (function normalize() {
              const arr = Array.isArray(json.models) ? json.models : [];
              if (provider === 'openai') {
                return arr.map(m => (typeof m === 'string' ? m : (m.id || ''))).filter(Boolean);
              }
              return arr.map(m => (m.model || m.name || '')).filter(Boolean);
            })();
            modelsList.innerHTML = names.map(n => `<option value="${n}"></option>`).join('');
            if (names.length) modelInput.value = names[0];
          } catch (e) {
            console.error(e);
          }
        });

        async function checkCamundaStatus() {
          const statusDiv = document.getElementById('camunda-status');
          try {
            const res = await fetch('/api/camunda/status');
            const json = await res.json();
            if (json.status === 'running') {
              statusDiv.innerHTML = '<div class="status running">✅ Camunda is running</div>';
            } else {
              statusDiv.innerHTML = `<div class="status error">❌ Camunda: ${json.status}</div>`;
            }
          } catch (e) {
            statusDiv.innerHTML = '<div class="status error">❌ Cannot connect to Camunda</div>';
          }
        }

        async function refreshRuns() {
          const runsDiv = document.getElementById('runs-list');
          try {
            const res = await fetch('/api/runs');
            const json = await res.json();
            if (json.runs && json.runs.length > 0) {
              runsDiv.innerHTML = json.runs.map(run => 
                `<div class="status ${run.status}">${run.filename} - ${run.status} <a href="${run.camunda_url}" target="_blank">View</a></div>`
              ).join('');
            } else {
              runsDiv.innerHTML = '<div>No active runs</div>';
            }
          } catch (e) {
            runsDiv.innerHTML = '<div class="status error">Error loading runs</div>';
          }
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/models/ollama", response_model=dict)
async def list_ollama_models():
    settings = Settings()
    base = settings.ollama_url.rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/api/tags")
            r.raise_for_status()
            data = r.json()
            # Normalize shape
            return {"provider": "ollama", "models": data.get("models", data)}
    except Exception as e:
        return {"provider": "ollama", "error": str(e)}


@app.get("/api/models/openai", response_model=dict)
async def list_openai_models():
    api_key = Settings().openai_api_key
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = "https://api.openai.com/v1/models"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 401:
                return {"provider": "openai", "error": "Unauthorized (set OPENAI_API_KEY)"}
            r.raise_for_status()
            data = r.json()
            return {"provider": "openai", "models": data.get("data", [])}
    except Exception as e:
        return {"provider": "openai", "error": str(e)}


@app.get("/api/runs")
async def list_runs():
    """List all runs."""
    return {"runs": list(RUNS.values())}


def run():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()



