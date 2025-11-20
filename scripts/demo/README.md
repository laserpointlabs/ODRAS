# Intelligent Lattice Demo

## Overview

The Intelligent Lattice Demo showcases ODRAS's ability to generate project lattices using LLM analysis and process them with proper dependency management.

## Features

- **LLM-Powered Lattice Generation** - Uses OpenAI to analyze requirements and generate intelligent project structures
- **Real Project Creation** - Creates actual projects in ODRAS with parent-child relationships
- **Workflow Processing** - Processes projects with proper input blocking (waits for all inputs)
- **Visual Feedback** - Real-time visualization with Cytoscape.js showing project states
- **LLM Audit Trail** - Complete log of all LLM interactions for review

## Quick Start

### Using demo.sh (Recommended)

```bash
cd scripts/demo
./demo.sh start      # Start all services (HTTP, WebSocket, LLM service)
./demo.sh status     # Check service status
./demo.sh logs       # View logs
./demo.sh stop       # Stop all services
```

Then open: `http://localhost:8082/intelligent_lattice_demo.html`

### Manual Start

1. **Start LLM Service:**
   ```bash
   cd scripts/demo
   python3 llm_service.py
   ```

2. **Start HTTP Server:**
   ```bash
   cd scripts/demo
   python3 -m http.server 8082 --directory static
   ```

3. **Open Browser:**
   ```
   http://localhost:8082/intelligent_lattice_demo.html
   ```

## Requirements

- ODRAS API running on `http://localhost:8000`
- OpenAI API key set in environment (`OPENAI_API_KEY`)
- Python 3.8+
- Modern web browser

## Usage

1. **Enter Requirements** - Paste or upload UAV acquisition requirements
2. **Generate Lattice** - Click "Generate Intelligent Lattice" to create project structure
3. **Start Processing** - Click "Start Processing" to process projects with LLM
4. **Review Results** - View workflow history and LLM audit trail

## Files

- `intelligent_lattice_demo.html` - Main demo interface
- `intelligent_lattice.js` - Demo logic and visualization
- `llm_service.py` - LLM service backend (Flask)
- `demo.sh` - Service management script
- `clear_das_service_projects.py` - Utility to clean up demo projects

## Architecture

- **Frontend**: HTML/JavaScript with Cytoscape.js for visualization
- **Backend**: Flask service for LLM interactions
- **ODRAS API**: Creates projects, relationships, and subscriptions
- **Workflow**: JavaScript-based with proper input blocking

## Key Features

### Input Blocking
Projects wait for ALL required inputs before processing:
- Parent project data
- Data flow inputs
- Requirements (for L1 projects)

### Visual States
- **Waiting** - Orange dashed border (inputs not ready)
- **Processing** - Yellow with pulsing overlay
- **Complete** - Green border
- **Error** - Red border

### LLM Integration
- Real OpenAI GPT-4 calls for each project
- Complete audit trail of prompts and responses
- Fallback to mock data if LLM fails

## Troubleshooting

### Demo not starting
- Check ODRAS is running: `./odras.sh status`
- Check ports are available: `lsof -i :8082 -i :8083`
- Check LLM service logs: `./demo.sh logs llm`

### Projects not creating
- Verify authentication: Check browser console for auth errors
- Check ODRAS API: `curl http://localhost:8000/api/projects`
- Clear old projects: `python3 clear_das_service_projects.py`

### LLM not working
- Verify API key: `echo $OPENAI_API_KEY`
- Check LLM service: `curl http://localhost:8083/health`
- Review logs: `./demo.sh logs llm`
