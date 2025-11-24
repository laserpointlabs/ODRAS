# Quick Start - Intelligent Lattice Demo

## Prerequisites

1. ODRAS running (`./odras.sh start`)
2. OpenAI API key set (`export OPENAI_API_KEY=your_key`)
3. Python 3.8+

## Start Demo

```bash
cd scripts/demo
x
```

Open browser: `http://localhost:8082/intelligent_lattice_demo.html`

## What You'll See

1. **Requirements Input** - Collapsible panel for entering requirements
2. **Projects Generated** - List of generated projects with controls
3. **Cytoscape Canvas** - Visual graph of project lattice
4. **Processing Status** - Horizontal panel showing current processing
5. **Workflow History** - Detailed log of each processing step
6. **LLM Audit Trail** - Complete LLM interaction log

## Using the Demo

1. **Load Example** - Click "Load Example" to populate requirements
2. **Generate Lattice** - Click "Generate Intelligent Lattice" to create projects
3. **Start Processing** - Click "Start Processing" to begin workflow
4. **Review Results** - Click "View Data" on workflow steps to see details
5. **View LLM Trail** - Click "View LLM Audit Trail" to see all LLM interactions

## Clean Up

```bash
# Stop demo services
./demo.sh stop

# Clear demo projects
python3 clear_das_service_projects.py
```

## Demo Features

- ✅ Real LLM-powered lattice generation
- ✅ Actual project creation in ODRAS
- ✅ Proper input blocking (waits for all inputs)
- ✅ Visual state feedback (waiting/processing/complete)
- ✅ Complete LLM audit trail
- ✅ Workflow history with inputs/outputs
