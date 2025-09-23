# ODRAS MVP Updates - Week 2 Enhancement Plan<br>
<br>
This document outlines the proposed enhancements to the ODRAS MVP based on research and architectural considerations for improved project isolation, data management, and workflow controls.<br>
<br>
## 🎯 Executive Summary<br>
<br>
The proposed enhancements focus on:<br>
1. **Single Ontology per Project** - Enforce project sandbox model with admin-released importable ontologies<br>
2. **Data Manager Workbench** - New component for managing data properties and external data connections<br>
3. **Project-Scoped Resources** - Strengthen isolation with admin approval workflows<br>
4. **LLM Playground Enhancement** - Consolidate RAG capabilities for better experimentation<br>
5. **Project Approval Workflow** - Streamline global resource sharing through project-level approval<br>
<br>
## 📊 Current State Analysis<br>
<br>
### Existing Architecture<br>
- **Ontology Management**: Currently allows multiple ontologies per project via `ontologies_registry`<br>
- **Resource Scoping**: Knowledge assets have `is_public` flag, files have project scoping<br>
- **Admin Controls**: Individual resource approval (knowledge assets, files)<br>
- **RAG Interface**: Embedded in knowledge workbench, not optimized for experimentation<br>
<br>
### Key Gaps Identified<br>
1. No enforcement of single ontology per project<br>
2. Data properties not actively integrated with external data sources<br>
3. Fragmented approval process for making resources global<br>
4. RAG experimentation limited by current UI placement<br>
5. No formal project approval workflow<br>
<br>
## 🏗️ Proposed Enhancements<br>
<br>
### 1. Single Ontology per Project Model<br>
<br>
#### Rationale<br>
- Creates focused project sandboxes<br>
- Simplifies ontology management and versioning<br>
- Clearer separation between development and released ontologies<br>
<br>
#### Implementation Plan<br>
<br>
**Database Schema Changes:**<br>
```sql<br>
-- Modify projects table to include base ontology reference<br>
ALTER TABLE public.projects<br>
ADD COLUMN base_ontology_id UUID REFERENCES public.ontologies(ontology_id),<br>
ADD COLUMN ontology_graph_iri TEXT UNIQUE;<br>
<br>
-- Create ontologies table for better management<br>
CREATE TABLE IF NOT EXISTS public.ontologies (<br>
    ontology_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    graph_iri TEXT UNIQUE NOT NULL,<br>
    name VARCHAR(255) NOT NULL,<br>
    namespace TEXT NOT NULL,<br>
    version VARCHAR(50) DEFAULT '1.0.0',<br>
    status VARCHAR(50) DEFAULT 'draft', -- draft, review, released<br>
    is_importable BOOLEAN DEFAULT FALSE,<br>
    released_at TIMESTAMP WITH TIME ZONE,<br>
    released_by UUID REFERENCES public.users(user_id),<br>
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()<br>
);<br>
<br>
-- Track imported ontologies per project<br>
CREATE TABLE IF NOT EXISTS public.project_ontology_imports (<br>
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,<br>
    imported_ontology_id UUID REFERENCES public.ontologies(ontology_id),<br>
    import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    PRIMARY KEY (project_id, imported_ontology_id)<br>
);<br>
```<br>
<br>
**API Changes:**<br>
- `POST /api/projects` - Modified to create default ontology graph<br>
- `GET /api/ontologies/importable` - List admin-released ontologies<br>
- `POST /api/projects/{id}/imports` - Import released ontology<br>
- `POST /api/admin/ontologies/{id}/release` - Admin release workflow<br>
<br>
**Workbench UI Updates:**<br>
- Remove multi-ontology selector<br>
- Add "Import Released Ontology" action in tree<br>
- Show imported ontologies as read-only overlays<br>
- Display ontology status badges (draft/review/released)<br>
<br>
### 2. Data Manager Workbench<br>
<br>
#### Concept<br>
A new workbench for managing the connection between ontology data properties and external data sources, enabling live data integration with semantic models.<br>
<br>
#### Core Features<br>
<br>
**Data Property Detection:**<br>
- Monitor project ontology for data property additions<br>
- Auto-create data pipe configurations for new properties<br>
- Maintain property-to-source mappings<br>
<br>
**Data Pipe Types:**<br>
1. **Database Connections**<br>
   - SQL databases (PostgreSQL, MySQL, SQLite)<br>
   - NoSQL stores (MongoDB, Redis)<br>
   - Time-series databases (InfluxDB, TimescaleDB)<br>
<br>
2. **API Integrations**<br>
   - REST APIs with authentication<br>
   - GraphQL endpoints<br>
   - WebSocket streams<br>
<br>
3. **File-Based Sources**<br>
   - CSV/Excel files<br>
   - JSON/XML documents<br>
   - CAD model metadata<br>
<br>
4. **Ontology Data Sources**<br>
   - Published ontology instances<br>
   - Cross-project data sharing (with permissions)<br>
<br>
**Data Model:**<br>
```sql<br>
CREATE TABLE IF NOT EXISTS public.data_pipes (<br>
    pipe_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,<br>
    ontology_property_iri TEXT NOT NULL,<br>
    pipe_name VARCHAR(255) NOT NULL,<br>
    pipe_type VARCHAR(50) NOT NULL, -- database, api, file, ontology<br>
    source_config JSONB NOT NULL, -- connection details, credentials reference<br>
    mapping_config JSONB NOT NULL, -- field mappings, transformations<br>
    refresh_schedule VARCHAR(50), -- cron expression or 'manual'<br>
    last_sync_at TIMESTAMP WITH TIME ZONE,<br>
    last_sync_status VARCHAR(50),<br>
    is_active BOOLEAN DEFAULT TRUE,<br>
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()<br>
);<br>
<br>
CREATE TABLE IF NOT EXISTS public.data_pipe_executions (<br>
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    pipe_id UUID REFERENCES public.data_pipes(pipe_id) ON DELETE CASCADE,<br>
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    completed_at TIMESTAMP WITH TIME ZONE,<br>
    status VARCHAR(50) NOT NULL, -- running, success, failed<br>
    records_processed INTEGER DEFAULT 0,<br>
    error_message TEXT,<br>
    execution_log JSONB<br>
);<br>
```<br>
<br>
**MVP Scope (Limited):**<br>
- Basic UI for viewing detected data properties<br>
- Manual data pipe creation for database sources<br>
- Simple field mapping interface<br>
- Test connection functionality<br>
- Manual sync execution<br>
- View sync history and status<br>
<br>
**Future Enhancements:**<br>
- Advanced transformation rules<br>
- Real-time data streaming<br>
- Data quality monitoring<br>
- Automated sync scheduling<br>
- Complex JOIN operations<br>
<br>
### 3. Project-Scoped Resources & Admin Approval<br>
<br>
#### Enhanced Project Isolation<br>
<br>
**Principle:** All resources are project-specific by default, becoming global only through explicit admin action.<br>
<br>
**Resource Types:**<br>
- Ontologies (base + imported)<br>
- Documents/Files<br>
- Knowledge Assets<br>
- Data Pipes<br>
- LLM Agents/Prompts<br>
<br>
**Implementation:**<br>
<br>
```sql<br>
-- Add project approval table<br>
CREATE TABLE IF NOT EXISTS public.project_approvals (<br>
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    project_id UUID REFERENCES public.projects(project_id),<br>
    requested_by UUID REFERENCES public.users(user_id),<br>
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    reviewed_by UUID REFERENCES public.users(user_id),<br>
    reviewed_at TIMESTAMP WITH TIME ZONE,<br>
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected<br>
    approval_type VARCHAR(50) NOT NULL, -- full_project, specific_resources<br>
    resource_list JSONB, -- if specific_resources<br>
    review_notes TEXT,<br>
    approval_metadata JSONB -- quality scores, compliance checks<br>
);<br>
<br>
-- Add global resource tracking<br>
ALTER TABLE public.files ADD COLUMN made_global_via_project UUID REFERENCES public.projects(project_id);<br>
ALTER TABLE public.knowledge_assets ADD COLUMN made_global_via_project UUID REFERENCES public.projects(project_id);<br>
```<br>
<br>
**Approval Workflows:**<br>
<br>
1. **Individual Resource Approval** (Current)<br>
   - Admin manually reviews and approves each resource<br>
   - Suitable for high-value, selective sharing<br>
<br>
2. **Project-Level Approval** (New)<br>
   - Submit entire project for review<br>
   - Quality gates and automated checks<br>
   - Batch approval of all project resources<br>
   - Resources tagged with source project<br>
<br>
**Quality Gates for Project Approval:**<br>
- Ontology validation (SHACL compliance)<br>
- Documentation completeness (>80% coverage)<br>
- Knowledge asset quality scores (>0.7 average)<br>
- No conflicting global resources<br>
- Passing test cases (if defined)<br>
<br>
### 4. LLM Playground Integration<br>
<br>
#### Relocate Knowledge RAG Interface<br>
<br>
**Current State:** RAG query interface embedded in knowledge detail view<br>
<br>
**Proposed State:** Consolidated in LLM Playground for unified experimentation<br>
<br>
**Benefits:**<br>
- Test different LLM models (OpenAI, Ollama) in one place<br>
- Compare responses across models<br>
- Experiment with prompt engineering<br>
- Create and test LLM agents<br>
- Access both project and global knowledge<br>
<br>
**Implementation:**<br>
<br>
```typescript<br>
// LLM Playground Components<br>
interface PlaygroundConfig {<br>
    context: {<br>
        knowledge_scope: 'project' | 'global' | 'both';<br>
        project_ids?: string[];<br>
        document_types?: string[];<br>
        include_ontology: boolean;<br>
    };<br>
    model: {<br>
        provider: 'openai' | 'ollama' | 'anthropic';<br>
        model_name: string;<br>
        temperature: number;<br>
        max_tokens: number;<br>
    };<br>
    agents?: LLMAgent[];<br>
}<br>
<br>
interface LLMAgent {<br>
    agent_id: string;<br>
    name: string;<br>
    role: string;<br>
    system_prompt: string;<br>
    tools?: string[]; // available functions<br>
    constraints?: string[];<br>
}<br>
```<br>
<br>
**UI Features:**<br>
- Split-panel interface (query + response)<br>
- Model selector with settings<br>
- Context scope controls<br>
- Query history with versioning<br>
- Response comparison view<br>
- Agent builder interface<br>
- Prompt template library<br>
- Export conversations<br>
<br>
**Agent Management:**<br>
```sql<br>
CREATE TABLE IF NOT EXISTS public.llm_agents (<br>
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    project_id UUID REFERENCES public.projects(project_id),<br>
    name VARCHAR(255) NOT NULL,<br>
    description TEXT,<br>
    role VARCHAR(100),<br>
    system_prompt TEXT NOT NULL,<br>
    model_config JSONB NOT NULL,<br>
    tools JSONB DEFAULT '[]',<br>
    is_global BOOLEAN DEFAULT FALSE,<br>
    created_by UUID REFERENCES public.users(user_id),<br>
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),<br>
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()<br>
);<br>
```<br>
<br>
### 5. Enhanced Project Workflow Controls<br>
<br>
#### Project Lifecycle Management<br>
<br>
**States:**<br>
1. **Draft** - Active development, all resources private<br>
2. **Review** - Submitted for approval, read-only<br>
3. **Approved** - Resources available globally<br>
4. **Archived** - Historical reference only<br>
<br>
**Workflow Implementation:**<br>
<br>
```mermaid<br>
stateDiagram-v2<br>
    [*] --> Draft: Create Project<br>
    Draft --> Review: Submit for Approval<br>
    Review --> Draft: Request Changes<br>
    Review --> Approved: Admin Approve<br>
    Approved --> Archived: Archive Project<br>
    Draft --> Archived: Archive Project<br>
```<br>
<br>
**API Endpoints:**<br>
- `POST /api/projects/{id}/submit-review` - Submit project for approval<br>
- `POST /api/admin/projects/{id}/review` - Admin review action<br>
- `GET /api/projects/{id}/approval-status` - Check approval status<br>
- `POST /api/projects/{id}/archive` - Archive project<br>
<br>
## 🧪 Synthesized Test Data Strategy<br>
<br>
### Overview<br>
To validate the Data Manager Workbench and ensure robust testing without external dependencies, we'll create a comprehensive synthesized test dataset covering all supported data source types.<br>
<br>
### Test Data Components<br>
<br>
#### 1. Database Test Data<br>
<br>
**Test Schema (PostgreSQL):**<br>
```sql<br>
-- Test schema for aerospace components<br>
CREATE SCHEMA IF NOT EXISTS odras_test;<br>
<br>
-- Aircraft components table<br>
CREATE TABLE IF NOT EXISTS odras_test.aircraft_components (<br>
    component_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    part_number VARCHAR(50) UNIQUE NOT NULL,<br>
    component_name VARCHAR(255) NOT NULL,<br>
    component_type VARCHAR(100), -- engine, avionics, structure, hydraulics<br>
    manufacturer VARCHAR(255),<br>
    weight_kg DECIMAL(10,2),<br>
    cost_usd DECIMAL(12,2),<br>
    certification_date DATE,<br>
    mtbf_hours INTEGER, -- Mean Time Between Failures<br>
    temperature_rating_min INTEGER, -- Celsius<br>
    temperature_rating_max INTEGER, -- Celsius<br>
    created_at TIMESTAMP DEFAULT NOW(),<br>
    updated_at TIMESTAMP DEFAULT NOW()<br>
);<br>
<br>
-- Sensor readings table (time-series data)<br>
CREATE TABLE IF NOT EXISTS odras_test.sensor_readings (<br>
    reading_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    sensor_id VARCHAR(50) NOT NULL,<br>
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),<br>
    reading_type VARCHAR(50), -- temperature, pressure, vibration, voltage<br>
    value DECIMAL(10,4) NOT NULL,<br>
    unit VARCHAR(20) NOT NULL,<br>
    timestamp TIMESTAMP NOT NULL,<br>
    quality_score DECIMAL(3,2), -- 0.00 to 1.00<br>
    INDEX idx_sensor_time (sensor_id, timestamp)<br>
);<br>
<br>
-- Requirements compliance table<br>
CREATE TABLE IF NOT EXISTS odras_test.compliance_records (<br>
    compliance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),<br>
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),<br>
    requirement_id VARCHAR(50) NOT NULL, -- Links to ontology requirements<br>
    compliance_status VARCHAR(50), -- compliant, non_compliant, partial, pending<br>
    test_date DATE,<br>
    test_results JSONB,<br>
    notes TEXT<br>
);<br>
<br>
-- Insert sample data<br>
INSERT INTO odras_test.aircraft_components<br>
(part_number, component_name, component_type, manufacturer, weight_kg, cost_usd, certification_date, mtbf_hours, temperature_rating_min, temperature_rating_max)<br>
VALUES<br>
('GPS-NAV-001', 'GPS Navigation Module', 'avionics', 'TechAvionics Corp', 2.5, 15000.00, '2023-06-15', 10000, -40, 85),<br>
('ENG-CTRL-A1', 'Engine Control Unit', 'engine', 'AeroControls Inc', 5.2, 45000.00, '2023-03-20', 8000, -55, 125),<br>
('HYD-PUMP-B2', 'Hydraulic Pump Assembly', 'hydraulics', 'FluidDynamics Ltd', 12.8, 28000.00, '2022-11-10', 5000, -40, 100),<br>
('STR-BEAM-C3', 'Structural Support Beam', 'structure', 'AeroStructures', 45.0, 8500.00, '2023-01-05', 50000, -60, 150);<br>
<br>
-- Generate time-series sensor data<br>
INSERT INTO odras_test.sensor_readings (sensor_id, component_id, reading_type, value, unit, timestamp, quality_score)<br>
SELECT<br>
    'TEMP-' || comp.part_number,<br>
    comp.component_id,<br>
    'temperature',<br>
    20 + (RANDOM() * 40), -- 20-60°C<br>
    'celsius',<br>
    NOW() - (interval '1 hour' * generate_series(1, 168)), -- Last 7 days hourly<br>
    0.85 + (RANDOM() * 0.15) -- 0.85-1.00 quality<br>
FROM odras_test.aircraft_components comp<br>
WHERE comp.component_type IN ('avionics', 'engine');<br>
```<br>
<br>
#### 2. Mock API Endpoints<br>
<br>
**Test API Server (FastAPI):**<br>
```python<br>
# test_api_server.py<br>
from fastapi import FastAPI, HTTPException<br>
from datetime import datetime, timedelta<br>
import random<br>
from typing import List, Optional<br>
from pydantic import BaseModel<br>
<br>
app = FastAPI(title="ODRAS Test Data API")<br>
<br>
class MaintenanceRecord(BaseModel):<br>
    record_id: str<br>
    component_id: str<br>
    maintenance_type: str<br>
    performed_date: datetime<br>
    next_due_date: datetime<br>
    technician: str<br>
    status: str<br>
    cost: float<br>
<br>
class WeatherData(BaseModel):<br>
    location: str<br>
    timestamp: datetime<br>
    temperature: float<br>
    pressure: float<br>
    humidity: float<br>
    visibility: float<br>
    conditions: str<br>
<br>
@app.get("/api/v1/maintenance/{component_id}")<br>
async def get_maintenance_history(component_id: str, limit: int = 10) -> List[MaintenanceRecord]:<br>
    """Mock maintenance history for a component"""<br>
    records = []<br>
    for i in range(limit):<br>
        performed = datetime.now() - timedelta(days=30*i)<br>
        records.append(MaintenanceRecord(<br>
            record_id=f"MNT-{component_id}-{i:03d}",<br>
            component_id=component_id,<br>
            maintenance_type=random.choice(["inspection", "repair", "replacement", "calibration"]),<br>
            performed_date=performed,<br>
            next_due_date=performed + timedelta(days=90),<br>
            technician=f"Tech-{random.randint(100, 999)}",<br>
            status=random.choice(["completed", "pending_parts", "scheduled"]),<br>
            cost=random.uniform(500, 5000)<br>
        ))<br>
    return records<br>
<br>
@app.get("/api/v1/weather/conditions")<br>
async def get_weather_conditions(lat: float, lon: float) -> WeatherData:<br>
    """Mock weather data for flight conditions"""<br>
    return WeatherData(<br>
        location=f"{lat},{lon}",<br>
        timestamp=datetime.now(),<br>
        temperature=15 + random.uniform(-10, 25),<br>
        pressure=1013 + random.uniform(-20, 20),<br>
        humidity=random.uniform(30, 90),<br>
        visibility=random.uniform(1, 10),<br>
        conditions=random.choice(["clear", "cloudy", "rain", "fog", "snow"])<br>
    )<br>
<br>
@app.get("/api/v1/supply-chain/{part_number}")<br>
async def get_supply_chain_data(part_number: str):<br>
    """Mock supply chain data"""<br>
    return {<br>
        "part_number": part_number,<br>
        "suppliers": [<br>
            {<br>
                "supplier_id": f"SUP-{i:03d}",<br>
                "name": f"Supplier {chr(65+i)}",<br>
                "lead_time_days": random.randint(7, 60),<br>
                "price": random.uniform(100, 10000),<br>
                "availability": random.choice(["in_stock", "low_stock", "out_of_stock"]),<br>
                "quality_rating": round(random.uniform(3.5, 5.0), 1)<br>
            }<br>
            for i in range(3)<br>
        ],<br>
        "last_updated": datetime.now().isoformat()<br>
    }<br>
```<br>
<br>
#### 3. Sample CAD/STL Files<br>
<br>
**Generate Test STL Files:**<br>
```python<br>
# generate_test_stl.py<br>
import numpy as np<br>
from stl import mesh<br>
<br>
def create_test_bracket_stl():<br>
    """Create a simple bracket STL for testing"""<br>
    # Define vertices for a simple L-shaped bracket<br>
    vertices = np.array([<br>
        [0, 0, 0], [100, 0, 0], [100, 20, 0], [0, 20, 0],  # Base<br>
        [0, 0, 10], [100, 0, 10], [100, 20, 10], [0, 20, 10],  # Base top<br>
        [0, 0, 10], [20, 0, 10], [20, 0, 80], [0, 0, 80],  # Vertical<br>
        [0, 20, 10], [20, 20, 10], [20, 20, 80], [0, 20, 80]  # Vertical other side<br>
    ])<br>
<br>
    # Define faces<br>
    faces = np.array([<br>
        [0,3,1], [1,3,2],  # Bottom<br>
        [4,5,7], [5,6,7],  # Top base<br>
        [0,1,5], [0,5,4],  # Front base<br>
        [2,3,7], [2,7,6],  # Back base<br>
        [8,11,9], [9,11,10],  # Vertical front<br>
        [12,13,15], [13,14,15]  # Vertical back<br>
    ])<br>
<br>
    # Create mesh<br>
    bracket = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))<br>
    for i, f in enumerate(faces):<br>
        for j in range(3):<br>
            bracket.vectors[i][j] = vertices[f[j],:]<br>
<br>
    # Add metadata as comments<br>
    bracket.save('test_data/cad/bracket_GPS-NAV-001.stl')<br>
<br>
    # Create metadata file<br>
    metadata = {<br>
        "file": "bracket_GPS-NAV-001.stl",<br>
        "part_number": "GPS-NAV-001",<br>
        "material": "Aluminum 6061-T6",<br>
        "volume_cm3": 24.5,<br>
        "surface_area_cm2": 156.8,<br>
        "weight_g": 66.15,<br>
        "bounding_box": {<br>
            "x": 100, "y": 20, "z": 80<br>
        },<br>
        "tolerance": "+/- 0.1mm",<br>
        "finish": "Anodized"<br>
    }<br>
<br>
    import json<br>
    with open('test_data/cad/bracket_GPS-NAV-001.json', 'w') as f:<br>
        json.dump(metadata, f, indent=2)<br>
<br>
# Generate multiple test CAD files<br>
components = [<br>
    ("GPS-NAV-001", "GPS Mount Bracket"),<br>
    ("ENG-CTRL-A1", "Engine Controller Housing"),<br>
    ("HYD-PUMP-B2", "Pump Mounting Plate"),<br>
    ("STR-BEAM-C3", "Structural Connector")<br>
]<br>
<br>
for part_number, description in components:<br>
    create_test_bracket_stl()  # Simplified - would create different geometries<br>
```<br>
<br>
#### 4. Test Ontology with Data Properties<br>
<br>
**Extend Test Ontology:**<br>
```turtle<br>
@prefix odras: <http://odras.local/onto/aerospace#> .<br>
@prefix owl: <http://www.w3.org/2002/07/owl#> .<br>
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .<br>
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .<br>
<br>
# Data Properties for testing Data Manager<br>
odras:partNumber a owl:DatatypeProperty ;<br>
    rdfs:label "Part Number" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:string .<br>
<br>
odras:weight a owl:DatatypeProperty ;<br>
    rdfs:label "Weight" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:decimal ;<br>
    odras:unit "kilogram" .<br>
<br>
odras:operatingTemperature a owl:DatatypeProperty ;<br>
    rdfs:label "Operating Temperature" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:decimal ;<br>
    odras:unit "celsius" .<br>
<br>
odras:certificationDate a owl:DatatypeProperty ;<br>
    rdfs:label "Certification Date" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:date .<br>
<br>
odras:mtbfHours a owl:DatatypeProperty ;<br>
    rdfs:label "Mean Time Between Failures" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:integer ;<br>
    odras:unit "hours" .<br>
<br>
odras:supplierLeadTime a owl:DatatypeProperty ;<br>
    rdfs:label "Supplier Lead Time" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:integer ;<br>
    odras:unit "days" .<br>
<br>
odras:complianceStatus a owl:DatatypeProperty ;<br>
    rdfs:label "Compliance Status" ;<br>
    rdfs:domain odras:Component ;<br>
    rdfs:range xsd:string ;<br>
    odras:allowedValues "compliant,non_compliant,partial,pending" .<br>
```<br>
<br>
### Test Data Initialization Scripts<br>
<br>
**Master Test Data Setup:**<br>
```bash<br>
#!/bin/bash<br>
# setup_test_data.sh<br>
<br>
echo "Setting up ODRAS test data environment..."<br>
<br>
# 1. Create test database schema and data<br>
echo "Creating test database..."<br>
psql -U $POSTGRES_USER -d $POSTGRES_DB -f test_data/sql/create_test_schema.sql<br>
psql -U $POSTGRES_USER -d $POSTGRES_DB -f test_data/sql/insert_test_data.sql<br>
<br>
# 2. Start mock API server<br>
echo "Starting mock API server..."<br>
cd test_data/api && uvicorn test_api_server:app --host 0.0.0.0 --port 8888 --reload &<br>
<br>
# 3. Generate CAD test files<br>
echo "Generating CAD test files..."<br>
python test_data/cad/generate_test_stl.py<br>
<br>
# 4. Load test ontology<br>
echo "Loading test ontology with data properties..."<br>
curl -X POST http://localhost:3030/test/data \<br>
     -H "Content-Type: text/turtle" \<br>
     -d @test_data/ontology/test_data_properties.ttl<br>
<br>
# 5. Create test data pipes configuration<br>
echo "Creating default data pipe configurations..."<br>
python test_data/create_test_pipes.py<br>
<br>
echo "Test data setup complete!"<br>
```<br>
<br>
### Integration Test Scenarios<br>
<br>
**Data Manager Test Cases:**<br>
```python<br>
# test_data_manager_integration.py<br>
import pytest<br>
from datetime import datetime<br>
<br>
class TestDataManagerIntegration:<br>
<br>
    @pytest.fixture<br>
    def test_project(self):<br>
        """Create test project with ontology"""<br>
        # Setup code<br>
        return project_id<br>
<br>
    def test_database_pipe_sync(self, test_project):<br>
        """Test syncing component data from PostgreSQL"""<br>
        # Create pipe configuration<br>
        pipe_config = {<br>
            "pipe_type": "database",<br>
            "source_config": {<br>
                "driver": "postgresql",<br>
                "connection_string": "postgresql://test:test@localhost/odras_test"<br>
            },<br>
            "mapping": {<br>
                "query": "SELECT * FROM aircraft_components",<br>
                "bindings": {<br>
                    "odras:partNumber": "part_number",<br>
                    "odras:weight": "weight_kg",<br>
                    "odras:certificationDate": "certification_date"<br>
                }<br>
            }<br>
        }<br>
<br>
        # Execute sync<br>
        result = data_manager.sync_pipe(pipe_config)<br>
<br>
        # Verify RDF triples created<br>
        assert result.records_processed == 4<br>
        assert result.status == "success"<br>
<br>
    def test_api_pipe_realtime(self, test_project):<br>
        """Test API integration for maintenance data"""<br>
        pipe_config = {<br>
            "pipe_type": "api",<br>
            "source_config": {<br>
                "endpoint": "http://localhost:8888/api/v1/maintenance/{component_id}",<br>
                "method": "GET",<br>
                "auth": None<br>
            },<br>
            "mapping": {<br>
                "response_path": "$",<br>
                "bindings": {<br>
                    "odras:maintenanceDate": "$.performed_date",<br>
                    "odras:maintenanceCost": "$.cost"<br>
                }<br>
            }<br>
        }<br>
<br>
        # Test with specific component<br>
        result = data_manager.sync_pipe(pipe_config, {"component_id": "GPS-NAV-001"})<br>
        assert len(result.data) > 0<br>
<br>
    def test_cad_metadata_extraction(self, test_project):<br>
        """Test CAD file metadata extraction"""<br>
        pipe_config = {<br>
            "pipe_type": "file",<br>
            "source_config": {<br>
                "path": "test_data/cad/",<br>
                "pattern": "*.json",<br>
                "format": "json"<br>
            },<br>
            "mapping": {<br>
                "bindings": {<br>
                    "odras:cadVolume": "$.volume_cm3",<br>
                    "odras:cadWeight": "$.weight_g",<br>
                    "odras:cadMaterial": "$.material"<br>
                }<br>
            }<br>
        }<br>
<br>
        result = data_manager.sync_pipe(pipe_config)<br>
        assert result.records_processed == 4<br>
```<br>
<br>
### Performance Test Data<br>
<br>
**Load Testing Dataset:**<br>
```python<br>
# generate_load_test_data.py<br>
def generate_large_dataset():<br>
    """Generate larger dataset for performance testing"""<br>
<br>
    # 10,000 components<br>
    components = []<br>
    for i in range(10000):<br>
        components.append({<br>
            "part_number": f"COMP-{i:06d}",<br>
            "name": f"Component {i}",<br>
            "type": random.choice(["engine", "avionics", "structure", "hydraulics"]),<br>
            "weight": random.uniform(0.1, 100),<br>
            "cost": random.uniform(10, 50000)<br>
        })<br>
<br>
    # 1 million sensor readings<br>
    readings = []<br>
    for comp in components[:1000]:  # First 1000 components<br>
        for hour in range(1000):  # Last 1000 hours<br>
            readings.append({<br>
                "component_id": comp["part_number"],<br>
                "timestamp": datetime.now() - timedelta(hours=hour),<br>
                "temperature": random.uniform(20, 80),<br>
                "pressure": random.uniform(0.8, 1.2)<br>
            })<br>
<br>
    return components, readings<br>
```<br>
<br>
### Benefits of Test Data Strategy<br>
<br>
1. **Isolation**: No external dependencies during development/testing<br>
2. **Repeatability**: Consistent test results across environments<br>
3. **Coverage**: Tests all data source types (DB, API, Files)<br>
4. **Performance**: Can generate scaled datasets for load testing<br>
5. **Validation**: Ensures Data Manager handles various data formats<br>
6. **Documentation**: Test data serves as usage examples<br>
<br>
## 📋 Implementation Plan<br>
<br>
### Week 2 Sprint Plan<br>
<br>
#### Sprint 1: Single Ontology per Project (Days 1-2)<br>
- [ ] **SO-1**: Database schema updates for single ontology enforcement<br>
- [ ] **SO-2**: Modify project creation to include base ontology<br>
- [ ] **SO-3**: Update ontology workbench to work with single project ontology<br>
- [ ] **SO-4**: Implement ontology release workflow (API)<br>
- [ ] **SO-5**: Add import functionality for released ontologies<br>
- [ ] **SO-6**: Update UI to show ontology status and imports<br>
<br>
#### Sprint 2: Data Manager Workbench Foundation (Days 2-3)<br>
- [ ] **DM-1**: Create database schema for data pipes<br>
- [ ] **DM-2**: Implement data property detection service<br>
- [ ] **DM-3**: Basic Data Manager UI route and layout<br>
- [ ] **DM-4**: Database connection configuration UI<br>
- [ ] **DM-5**: Simple mapping interface (property to column)<br>
- [ ] **DM-6**: Test connection and manual sync functionality<br>
<br>
#### Sprint 3: Project Approval Workflow (Days 3-4)<br>
- [ ] **PA-1**: Create project approval database schema<br>
- [ ] **PA-2**: Implement quality gate checks (automated)<br>
- [ ] **PA-3**: Project submission API endpoints<br>
- [ ] **PA-4**: Admin review interface<br>
- [ ] **PA-5**: Batch resource promotion logic<br>
- [ ] **PA-6**: Project state management and transitions<br>
<br>
#### Sprint 4: LLM Playground Enhancement (Days 4-5)<br>
- [ ] **LP-1**: Move RAG query interface to LLM Playground<br>
- [ ] **LP-2**: Implement model selection and comparison<br>
- [ ] **LP-3**: Add context scope controls (project/global)<br>
- [ ] **LP-4**: Create agent builder interface<br>
- [ ] **LP-5**: Implement prompt template management<br>
- [ ] **LP-6**: Add conversation export functionality<br>
<br>
#### Sprint 5: Integration and Testing (Day 5)<br>
- [ ] **IT-1**: Integration testing across all new components<br>
- [ ] **IT-2**: Update documentation and user guides<br>
- [ ] **IT-3**: Migration scripts for existing data<br>
- [ ] **IT-4**: Performance optimization<br>
- [ ] **IT-5**: Security audit of new features<br>
<br>
## 🎯 Acceptance Criteria<br>
<br>
### Single Ontology per Project<br>
- [ ] Each project has exactly one base ontology<br>
- [ ] Imported ontologies are read-only and properly overlaid<br>
- [ ] Admin can release ontologies for import by other projects<br>
- [ ] Clear visual distinction between base and imported ontologies<br>
<br>
### Data Manager Workbench<br>
- [ ] Data properties automatically detected from ontology<br>
- [ ] Can create database connections and test them<br>
- [ ] Simple mapping interface functional<br>
- [ ] Manual sync executes successfully<br>
- [ ] Sync history and status visible<br>
<br>
### Project Approval<br>
- [ ] Projects can be submitted for approval<br>
- [ ] Quality gates run automatically<br>
- [ ] Admin can approve/reject with notes<br>
- [ ] Approved resources become globally accessible<br>
- [ ] Clear audit trail of approvals<br>
<br>
### LLM Playground<br>
- [ ] RAG queries work in playground<br>
- [ ] Can switch between models<br>
- [ ] Context scope controls functional<br>
- [ ] Query history maintained<br>
- [ ] Agents can be created and tested<br>
<br>
## 🚧 Risk Mitigation<br>
<br>
### Technical Risks<br>
1. **Data Pipeline Complexity** - Start with simple database sources only<br>
2. **Performance Impact** - Implement caching and lazy loading<br>
3. **Migration Complexity** - Provide backwards compatibility mode<br>
<br>
### Process Risks<br>
1. **User Adoption** - Provide clear migration guides<br>
2. **Approval Bottlenecks** - Implement automated quality checks<br>
3. **Data Security** - Encrypt credentials, audit all access<br>
<br>
## 📚 References and Best Practices<br>
<br>
### Ontology Data Management<br>
- **Semantic Web Best Practices**: Separation of TBox (schema) and ABox (instances)<br>
- **Data Property Patterns**: Use rdfs:range for data types, maintain cardinality constraints<br>
- **External Data Integration**: Maintain provenance, versioning, and update timestamps<br>
<br>
### Project Isolation Patterns<br>
- **Multi-tenancy**: Logical isolation with shared infrastructure<br>
- **Resource Namespacing**: Use project IDs in all resource identifiers<br>
- **Cross-project Sharing**: Explicit permissions and audit trails<br>
<br>
### LLM Integration<br>
- **Context Windows**: Optimize chunk selection for token limits<br>
- **Model Comparison**: Standardize prompts for fair comparison<br>
- **Agent Design**: Clear roles, constrained actions, testable outcomes<br>
<br>
---<br>
<br>
*This enhancement plan builds upon the successful ODRAS Phase 1 implementation to create a more structured, governed system for ontology-driven requirements analysis and knowledge management.*<br>

