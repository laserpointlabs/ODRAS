from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
import uvicorn
import asyncio
import requests
import json
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.config import Settings
import httpx


app = FastAPI(title="ODRAS API", version="0.1.0")

# Camunda configuration
CAMUNDA_BASE_URL = "http://localhost:8080"
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

# Simple in-memory run registry (MVP). Replace with Redis/DB later.
RUNS: Dict[str, Dict] = {}

# In-memory storage for personas and prompts (MVP). Replace with Redis/DB later.
PERSONAS: List[Dict] = [
    {
        "id": "extractor",
        "name": "Extractor",
        "description": "You extract ontology-grounded entities from requirements.",
        "system_prompt": "You are an expert requirements analyst. Your role is to extract ontology-grounded entities from requirements text. Return ONLY JSON conforming to the provided schema.",
        "is_active": True
    },
    {
        "id": "reviewer",
        "name": "Reviewer", 
        "description": "You validate and correct extracted JSON to fit the schema strictly.",
        "system_prompt": "You are a quality assurance specialist. Your role is to validate and correct extracted JSON to ensure it strictly conforms to the provided schema. Return ONLY JSON conforming to the schema.",
        "is_active": True
    }
]

PROMPTS: List[Dict] = [
    {
        "id": "default_analysis",
        "name": "Default Analysis",
        "description": "Default prompt for requirement analysis",
        "prompt_template": "Analyze the following requirement and extract key information:\n\nRequirement: {requirement_text}\nCategory: {category}\nSource: {source_file}\nIteration: {iteration}\n\nPlease provide:\n1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)\n2. Constraints and dependencies\n3. Performance requirements\n4. Quality attributes\n5. Confidence level (0.0-1.0)\n\nFormat your response as JSON.",
        "variables": ["requirement_text", "category", "source_file", "iteration"],
        "is_active": True
    }
]


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
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(start_url, json={"variables": variables})
            response.raise_for_status()
            data = response.json()
            return data.get("id")
    except Exception as e:
        print(f"Error starting Camunda process: {e}")
        return None


async def deploy_bpmn_if_needed() -> Optional[str]:
    """Deploy BPMN if not already deployed."""
    try:
        # Check if already deployed
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis")
            if response.status_code == 200:
                data = response.json()
                return data[0]["id"] if data else None
    except Exception:
        pass
    
    # Deploy BPMN
    try:
        bpmn_file_path = "../bpmn/odras_requirements_analysis.bpmn"
        with open(bpmn_file_path, "rb") as f:
            files = {"file": ("odras_requirements_analysis.bpmn", f, "application/xml")}
            data = {"deployment-name": "odras-requirements-analysis"}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{CAMUNDA_REST_API}/deployment/create",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                data = response.json()
                return data.get("id")
    except Exception as e:
        print(f"Error deploying BPMN: {e}")
        return None


@app.get("/api/runs/{run_id}")
async def get_run_status(run_id: str):
    """Get status of a specific run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_info = RUNS[run_id].copy()
    
    try:
        # Get Camunda process instance status
        process_id = run_info["process_id"]
        status_url = f"{CAMUNDA_REST_API}/process-instance/{process_id}"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(status_url)
            if response.status_code == 200:
                status_info = response.json()
                
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
        input[type=file], input[type=number], select, input[name="llm_model"], textarea { width: 100%; padding: 0.5rem; box-sizing: border-box; }
        button { margin-top: 1rem; padding: 0.5rem 1rem; margin-right: 0.5rem; }
        pre { background: #f9fafb; padding: 1rem; border-radius: 6px; overflow-x: auto; }
        .status { padding: 0.5rem; border-radius: 4px; margin: 0.5rem 0; }
        .status.running { background: #dbeafe; color: #1e40af; }
        .status.completed { background: #dcfce7; color: #166534; }
        .status.error { background: #fee2e2; color: #dc2626; }
        
        /* Tab Styles */
        .tabs { display: flex; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem; }
        .tab-button { 
          background: none; border: none; padding: 0.75rem 1.5rem; cursor: pointer; 
          border-bottom: 2px solid transparent; margin-right: 0.5rem;
        }
        .tab-button.active { 
          border-bottom-color: #3b82f6; color: #3b82f6; font-weight: 600;
        }
        .tab-button:hover { background: #f3f4f6; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .persona-item, .prompt-item { 
          border: 1px solid #e5e7eb; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;
          background: #f9fafb;
        }
        .persona-item h4, .prompt-item h4 { margin-top: 0; }
        .persona-controls, .prompt-controls { margin-bottom: 1rem; }
        .test-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }
        .test-input { margin-bottom: 0.5rem; }
        .test-result { background: #f1f5f9; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; }
      </style>
    </head>
    <body>
      <h1>ODRAS MVP - Camunda BPMN</h1>
      
      <div class="card">
        <h3>System Status</h3>
        <div id="camunda-status">Checking...</div>
        <button onclick="checkCamundaStatus()">Refresh Status</button>
        <button onclick="debugFunctions()">Debug Functions</button>
        <button onclick="showTab('personas')">Test Personas Tab</button>
        <button onclick="showTab('prompts')">Test Prompts Tab</button>
      </div>
      
      <!-- Tab Navigation -->
      <div class="tabs">
        <button class="tab-button active" onclick="showTab('upload')">Upload & Process</button>
        <button class="tab-button" onclick="showTab('personas')">Personas</button>
        <button class="tab-button" onclick="showTab('prompts')">Prompts</button>
        <button class="tab-button" onclick="showTab('runs')">Active Runs</button>
      </div>
      
      <!-- Upload Tab -->
      <div id="upload-tab" class="tab-content active">
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
      </div>
      
      <!-- Personas Tab -->
      <div id="personas-tab" class="tab-content">
        <div class="card">
          <h3>LLM Personas</h3>
          <div class="persona-controls">
            <button onclick="addPersona()">Add New Persona</button>
            <button onclick="savePersonas()">Save All Personas</button>
            <button onclick="loadPersonas()">Load Personas</button>
          </div>
          <div id="personas-list">
            <!-- Personas will be loaded here -->
          </div>
        </div>
      </div>
      
      <!-- Prompts Tab -->
      <div id="prompts-tab" class="tab-content">
        <div class="card">
          <h3>Prompt Management</h3>
          <div class="prompt-controls">
            <button onclick="addPrompt()">Add New Prompt</button>
            <button onclick="savePrompts()">Save All Prompts</button>
            <button onclick="loadPrompts()">Load Prompts</button>
          </div>
          <div id="prompts-list">
            <!-- Prompts will be loaded here -->
          </div>
        </div>
      </div>
      
      <!-- Runs Tab -->
      <div id="runs-tab" class="tab-content">
        <div class="card">
          <h3>Active Runs</h3>
          <div id="runs-list">Loading...</div>
          <button onclick="refreshRuns()">Refresh Runs</button>
        </div>
      </div>
      
      <script>
        const form = document.getElementById('upload-form');
        const result = document.getElementById('result');
        const providerSelect = document.querySelector('select[name="llm_provider"]');
        const modelInput = document.querySelector('input[name="llm_model"]');
        const modelsList = document.getElementById('models-list');
        
        // Check Camunda status on page load
        console.log('Page loaded, checking status...');
        setTimeout(() => {
          console.log('Checking Camunda status...');
          checkCamundaStatus();
        }, 100);
        setTimeout(() => {
          console.log('Refreshing runs...');
          refreshRuns();
        }, 200);
        
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
          console.log('Provider changed to:', providerSelect.value);
          const provider = providerSelect.value;
          modelsList.innerHTML = '';
          modelInput.value = '';
          if (!provider) return;
          try {
            console.log('Fetching models for provider:', provider);
            const res = await fetch(`/api/models/${provider}`);
            const json = await res.json();
            console.log('Models response:', json);
            
            const names = (function normalize() {
              const arr = Array.isArray(json.models) ? json.models : [];
              if (provider === 'openai') {
                return arr.map(m => (typeof m === 'string' ? m : (m.id || ''))).filter(Boolean);
              }
              return arr.map(m => (m.model || m.name || '')).filter(Boolean);
            })();
            
            console.log('Normalized names:', names);
            modelsList.innerHTML = names.map(n => `<option value="${n}"></option>`).join('');
            if (names.length) {
              modelInput.value = names[0];
              console.log('Set default model to:', names[0]);
            }
          } catch (e) {
            console.error('Error fetching models:', e);
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

        // Tab Management
        function showTab(tabName) {
          console.log('showTab called with:', tabName);
          
          try {
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Remove active class from all tab buttons
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => button.classList.remove('active'));
            
            // Show selected tab content
            const targetTab = document.getElementById(tabName + '-tab');
            if (targetTab) {
              targetTab.classList.add('active');
              console.log('Tab content shown:', tabName);
            } else {
              console.error('Tab content not found:', tabName + '-tab');
            }
            
            // Add active class to selected tab button
            const activeButton = document.querySelector(`[onclick="showTab('${tabName}')"]`);
            if (activeButton) {
              activeButton.classList.add('active');
              console.log('Tab button activated:', tabName);
            } else {
              console.error('Tab button not found for:', tabName);
            }
            
            // Load content for specific tabs
            if (tabName === 'personas') {
              console.log('Loading personas...');
              loadPersonas();
            } else if (tabName === 'prompts') {
              console.log('Loading prompts...');
              loadPrompts();
            }
          } catch (e) {
            console.error('Error in showTab:', e);
          }
        }

        // Persona Management
        let personas = [
          {
            id: 'extractor',
            name: 'Extractor',
            description: 'You extract ontology-grounded entities from requirements.',
            system_prompt: 'You are an expert requirements analyst. Your role is to extract ontology-grounded entities from requirements text. Return ONLY JSON conforming to the provided schema.',
            is_active: true
          },
          {
            id: 'reviewer',
            name: 'Reviewer', 
            description: 'You validate and correct extracted JSON to fit the schema strictly.',
            system_prompt: 'You are a quality assurance specialist. Your role is to validate and correct extracted JSON to ensure it strictly conforms to the provided schema. Return ONLY JSON conforming to the schema.',
            is_active: true
          }
        ];

        function addPersona() {
          const newPersona = {
            id: 'persona_' + Date.now(),
            name: 'New Persona',
            description: 'Enter persona description',
            system_prompt: 'Enter system prompt for this persona',
            is_active: true
          };
          personas.push(newPersona);
          renderPersonas();
        }

        function deletePersona(personaId) {
          personas = personas.filter(p => p.id !== personaId);
          renderPersonas();
        }

        function togglePersona(personaId) {
          const persona = personas.find(p => p.id === personaId);
          if (persona) {
            persona.is_active = !persona.is_active;
            renderPersonas();
          }
        }

        function renderPersonas() {
          const container = document.getElementById('personas-list');
          container.innerHTML = personas.map(persona => 
            '<div class="persona-item">' +
              '<h4>' + persona.name + '</h4>' +
              '<div class="form-group">' +
                '<label>Name:</label>' +
                '<input type="text" value="' + persona.name + '" onchange="updatePersona(\'' + persona.id + '\', \'name\', this.value)">' +
              '</div>' +
              '<div class="form-group">' +
                '<label>Description:</label>' +
                '<input type="text" value="' + persona.description + '" onchange="updatePersona(\'' + persona.id + '\', \'description\', this.value)">' +
              '</div>' +
              '<div class="form-group">' +
                '<label>System Prompt:</label>' +
                '<textarea rows="4" onchange="updatePersona(\'' + persona.id + '\', \'system_prompt\', this.value)">' + persona.system_prompt + '</textarea>' +
              '</div>' +
              '<div class="form-group">' +
                '<label>' +
                  '<input type="checkbox" ' + (persona.is_active ? 'checked' : '') + ' onchange="togglePersona(\'' + persona.id + '\')">' +
                  'Active' +
                '</label>' +
              '</div>' +
              '<button onclick="deletePersona(\'' + persona.id + '\')">Delete</button>' +
            '</div>'
          ).join('');
        }

        function updatePersona(personaId, field, value) {
          const persona = personas.find(p => p.id === personaId);
          if (persona) {
            persona[field] = value;
          }
        }

        async function savePersonas() {
          try {
            // Save each persona to the API
            for (const persona of personas) {
              if (persona.id.startsWith('persona_')) {
                // New persona - create it
                await fetch('/api/personas', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(persona)
                });
              } else {
                // Existing persona - update it
                await fetch(`/api/personas/${persona.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(persona)
                });
              }
            }
            alert('Personas saved successfully!');
          } catch (e) {
            alert('Error saving personas: ' + e.message);
          }
        }

        async function loadPersonas() {
          try {
            const response = await fetch('/api/personas');
            const data = await response.json();
            personas = data.personas || personas;
            renderPersonas();
          } catch (e) {
            console.error('Error loading personas:', e);
            // Fallback to default personas
            renderPersonas();
          }
        }

        // Prompt Management
        let prompts = [
          {
            id: 'default_analysis',
            name: 'Default Analysis',
            description: 'Default prompt for requirement analysis',
            prompt_template: 'Analyze the following requirement and extract key information:\\n\\nRequirement: {requirement_text}\\nCategory: {category}\\nSource: {source_file}\\nIteration: {iteration}\\n\\nPlease provide:\\n1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)\\n2. Constraints and dependencies\\n3. Performance requirements\\n4. Quality attributes\\n5. Confidence level (0.0-1.0)\\n\\nFormat your response as JSON.',
            variables: ['requirement_text', 'category', 'source_file', 'iteration'],
            is_active: true
          }
        ];

        function addPrompt() {
          const newPrompt = {
            id: 'prompt_' + Date.now(),
            name: 'New Prompt',
            description: 'Enter prompt description',
            prompt_template: 'Enter prompt template with {variables}',
            variables: ['variable1', 'variable2'],
            is_active: true
          };
          prompts.push(newPrompt);
          renderPrompts();
        }

        function deletePrompt(promptId) {
          prompts = prompts.filter(p => p.id !== promptId);
          renderPrompts();
        }

        function togglePrompt(promptId) {
          const prompt = prompts.find(p => p.id === promptId);
          if (prompt) {
            prompt.is_active = !prompt.is_active;
            renderPrompts();
          }
        }

        function renderPrompts() {
          const container = document.getElementById('prompts-list');
          container.innerHTML = prompts.map(prompt => 
            '<div class="prompt-item">' +
              '<h4>' + prompt.name + '</h4>' +
              '<div class="form-group">' +
                '<label>Name:</label>' +
                '<input type="text" value="' + prompt.name + '" onchange="updatePrompt(\'' + prompt.id + '\', \'name\', this.value)">' +
              '</div>' +
              '<div class="form-group">' +
                '<label>Description:</label>' +
                '<input type="text" value="' + prompt.description + '" onchange="updatePrompt(\'' + prompt.id + '\', \'description\', this.value)">' +
              '</div>' +
              '<div class="form-group">' +
                '<label>Prompt Template:</label>' +
                '<textarea rows="6" onchange="updatePrompt(\'' + prompt.id + '\', \'prompt_template\', this.value)">' + prompt.prompt_template + '</textarea>' +
              '</div>' +
              '<div class="form-group">' +
                '<label>Variables (comma-separated):</label>' +
                '<input type="text" value="' + prompt.variables.join(', ') + '" onchange="updatePrompt(\'' + prompt.id + '\', \'variables\', this.value.split(\',\').map(v => v.trim()))">' +
              '</div>' +
              '<div class="form-group">' +
                '<label>' +
                  '<input type="checkbox" ' + (prompt.is_active ? 'checked' : '') + ' onchange="togglePrompt(\'' + prompt.id + '\')">' +
                  'Active' +
                '</label>' +
              '</div>' +
              '<div class="test-section">' +
                '<h5>Test Prompt</h5>' +
                '<div class="test-input">' +
                  '<label>Test Variables (JSON):</label>' +
                  '<textarea rows="3" placeholder=\'{"requirement_text": "Test requirement", "category": "Test", "source_file": "test.txt", "iteration": 1}\'>' + JSON.stringify({requirement_text: "Test requirement", category: "Test", source_file: "test.txt", iteration: 1}, null, 2) + '</textarea>' +
                '</div>' +
                '<button onclick="testPrompt(\'' + prompt.id + '\', this.previousElementSibling.querySelector(\'textarea\').value)">Test Prompt</button>' +
                '<div class="test-result" id="test-result-' + prompt.id + '"></div>' +
              '</div>' +
              '<button onclick="deletePrompt(\'' + prompt.id + '\')">Delete</button>' +
            '</div>'
          ).join('');
        }

        function updatePrompt(promptId, field, value) {
          const prompt = prompts.find(p => p.id === promptId);
          if (prompt) {
            prompt[field] = value;
          }
        }

        async function savePrompts() {
          try {
            // Save each prompt to the API
            for (const prompt of prompts) {
              if (prompt.id.startsWith('prompt_')) {
                // New prompt - create it
                await fetch('/api/prompts', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(prompt)
                });
              } else {
                // Existing prompt - update it
                await fetch(`/api/prompts/${prompt.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(prompt)
                });
              }
            }
            alert('Prompts saved successfully!');
          } catch (e) {
            alert('Error saving prompts: ' + e.message);
          }
        }

        async function loadPrompts() {
          try {
            const response = await fetch('/api/prompts');
            const data = await response.json();
            prompts = data.prompts || prompts;
            renderPrompts();
          } catch (e) {
            console.error('Error loading prompts:', e);
            // Fallback to default prompts
            renderPrompts();
          }
        }

        async function testPrompt(promptId, testVariablesJson) {
          try {
            const testVariables = JSON.parse(testVariablesJson);
            const prompt = prompts.find(p => p.id === promptId);
            if (!prompt) return;

            const resultDiv = document.getElementById(`test-result-${promptId}`);
            resultDiv.innerHTML = '<div class="status running">Testing prompt...</div>';

            // Test with the API
            const response = await fetch(`/api/prompts/${promptId}/test`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(testVariables)
            });

            if (response.ok) {
              const result = await response.json();
              resultDiv.innerHTML = `
                <div class="status completed">
                  <strong>Filled Prompt:</strong><br>
                  <pre>${result.filled_prompt}</pre>
                  <br><strong>Test Variables:</strong><br>
                  <pre>${JSON.stringify(result.test_variables, null, 2)}</pre>
                </div>
              `;
            } else {
              const error = await response.json();
              resultDiv.innerHTML = `<div class="status error">Error: ${error.detail}</div>`;
            }
          } catch (e) {
            const resultDiv = document.getElementById(`test-result-${promptId}`);
            resultDiv.innerHTML = `<div class="status error">Error: ${e.message}</div>`;
          }
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
          console.log('DOM loaded, initializing...');
          try {
            loadPersonas();
            loadPrompts();
            console.log('Initialization complete');
          } catch (e) {
            console.error('Error during initialization:', e);
          }
        });

        // Debug function to check if functions are available
        window.debugFunctions = function() {
          console.log('Available functions:', {
            showTab: typeof showTab,
            loadPersonas: typeof loadPersonas,
            loadPrompts: typeof loadPrompts,
            checkCamundaStatus: typeof checkCamundaStatus
          });
        };
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


# Persona Management API
@app.get("/api/personas")
async def list_personas():
    """List all personas."""
    return {"personas": PERSONAS}


@app.post("/api/personas")
async def create_persona(persona: Dict):
    """Create a new persona."""
    new_persona = {
        "id": persona.get("id", f"persona_{int(time.time() * 1000)}"),
        "name": persona.get("name", "New Persona"),
        "description": persona.get("description", ""),
        "system_prompt": persona.get("system_prompt", ""),
        "is_active": persona.get("is_active", True)
    }
    PERSONAS.append(new_persona)
    return {"persona": new_persona, "message": "Persona created successfully"}


@app.put("/api/personas/{persona_id}")
async def update_persona(persona_id: str, persona: Dict):
    """Update an existing persona."""
    for i, existing_persona in enumerate(PERSONAS):
        if existing_persona["id"] == persona_id:
            PERSONAS[i].update(persona)
            return {"persona": PERSONAS[i], "message": "Persona updated successfully"}
    raise HTTPException(status_code=404, detail="Persona not found")


@app.delete("/api/personas/{persona_id}")
async def delete_persona(persona_id: str):
    """Delete a persona."""
    global PERSONAS
    PERSONAS = [p for p in PERSONAS if p["id"] != persona_id]
    return {"message": "Persona deleted successfully"}


# Prompt Management API
@app.get("/api/prompts")
async def list_prompts():
    """List all prompts."""
    return {"prompts": PROMPTS}


@app.post("/api/prompts")
async def create_prompt(prompt: Dict):
    """Create a new prompt."""
    new_prompt = {
        "id": prompt.get("id", f"prompt_{int(time.time() * 1000)}"),
        "name": prompt.get("name", "New Prompt"),
        "description": prompt.get("description", ""),
        "prompt_template": prompt.get("prompt_template", ""),
        "variables": prompt.get("variables", []),
        "is_active": prompt.get("is_active", True)
    }
    PROMPTS.append(new_prompt)
    return {"prompt": new_prompt, "message": "Prompt created successfully"}


@app.put("/api/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, prompt: Dict):
    """Update an existing prompt."""
    for i, existing_prompt in enumerate(PROMPTS):
        if existing_prompt["id"] == prompt_id:
            PROMPTS[i].update(prompt)
            return {"prompt": PROMPTS[i], "message": "Prompt updated successfully"}
    raise HTTPException(status_code=404, detail="Prompt not found")


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    global PROMPTS
    PROMPTS = [p for p in PROMPTS if p["id"] != prompt_id]
    return {"message": "Prompt deleted successfully"}


@app.post("/api/prompts/{prompt_id}/test")
async def test_prompt(prompt_id: str, test_data: Dict):
    """Test a prompt with sample variables."""
    prompt = next((p for p in PROMPTS if p["id"] == prompt_id), None)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    try:
        # Fill the prompt template with test variables
        filled_prompt = prompt["prompt_template"]
        for variable in prompt.get("variables", []):
            if variable in test_data:
                filled_prompt = filled_prompt.replace(f"{{{variable}}}", str(test_data[variable]))
        
        return {
            "prompt_id": prompt_id,
            "filled_prompt": filled_prompt,
            "test_variables": test_data,
            "message": "Prompt filled successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing prompt: {str(e)}")


def run():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()



