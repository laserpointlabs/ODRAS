# ODRAS MVP Updates - Week 2 Enhancement Plan

This document outlines the proposed enhancements to the ODRAS MVP based on research and architectural considerations for improved project isolation, data management, and workflow controls.

## 🎯 Executive Summary

The proposed enhancements focus on:
1. **Single Ontology per Project** - Enforce project sandbox model with admin-released importable ontologies
2. **Data Manager Workbench** - New component for managing data properties and external data connections  
3. **Project-Scoped Resources** - Strengthen isolation with admin approval workflows
4. **LLM Playground Enhancement** - Consolidate RAG capabilities for better experimentation
5. **Project Approval Workflow** - Streamline global resource sharing through project-level approval

## 📊 Current State Analysis

### Existing Architecture
- **Ontology Management**: Currently allows multiple ontologies per project via `ontologies_registry`
- **Resource Scoping**: Knowledge assets have `is_public` flag, files have project scoping
- **Admin Controls**: Individual resource approval (knowledge assets, files)
- **RAG Interface**: Embedded in knowledge workbench, not optimized for experimentation

### Key Gaps Identified
1. No enforcement of single ontology per project
2. Data properties not actively integrated with external data sources
3. Fragmented approval process for making resources global
4. RAG experimentation limited by current UI placement
5. No formal project approval workflow

## 🏗️ Proposed Enhancements

### 1. Single Ontology per Project Model

#### Rationale
- Creates focused project sandboxes
- Simplifies ontology management and versioning
- Clearer separation between development and released ontologies

#### Implementation Plan

**Database Schema Changes:**
```sql
-- Modify projects table to include base ontology reference
ALTER TABLE public.projects 
ADD COLUMN base_ontology_id UUID REFERENCES public.ontologies(ontology_id),
ADD COLUMN ontology_graph_iri TEXT UNIQUE;

-- Create ontologies table for better management
CREATE TABLE IF NOT EXISTS public.ontologies (
    ontology_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_iri TEXT UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    namespace TEXT NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    status VARCHAR(50) DEFAULT 'draft', -- draft, review, released
    is_importable BOOLEAN DEFAULT FALSE,
    released_at TIMESTAMP WITH TIME ZONE,
    released_by UUID REFERENCES public.users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track imported ontologies per project
CREATE TABLE IF NOT EXISTS public.project_ontology_imports (
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    imported_ontology_id UUID REFERENCES public.ontologies(ontology_id),
    import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, imported_ontology_id)
);
```

**API Changes:**
- `POST /api/projects` - Modified to create default ontology graph
- `GET /api/ontologies/importable` - List admin-released ontologies
- `POST /api/projects/{id}/imports` - Import released ontology
- `POST /api/admin/ontologies/{id}/release` - Admin release workflow

**Workbench UI Updates:**
- Remove multi-ontology selector
- Add "Import Released Ontology" action in tree
- Show imported ontologies as read-only overlays
- Display ontology status badges (draft/review/released)

### 2. Data Manager Workbench

#### Concept
A new workbench for managing the connection between ontology data properties and external data sources, enabling live data integration with semantic models.

#### Core Features

**Data Property Detection:**
- Monitor project ontology for data property additions
- Auto-create data pipe configurations for new properties
- Maintain property-to-source mappings

**Data Pipe Types:**
1. **Database Connections**
   - SQL databases (PostgreSQL, MySQL, SQLite)
   - NoSQL stores (MongoDB, Redis)
   - Time-series databases (InfluxDB, TimescaleDB)

2. **API Integrations**
   - REST APIs with authentication
   - GraphQL endpoints
   - WebSocket streams

3. **File-Based Sources**
   - CSV/Excel files
   - JSON/XML documents
   - CAD model metadata

4. **Ontology Data Sources**
   - Published ontology instances
   - Cross-project data sharing (with permissions)

**Data Model:**
```sql
CREATE TABLE IF NOT EXISTS public.data_pipes (
    pipe_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    ontology_property_iri TEXT NOT NULL,
    pipe_name VARCHAR(255) NOT NULL,
    pipe_type VARCHAR(50) NOT NULL, -- database, api, file, ontology
    source_config JSONB NOT NULL, -- connection details, credentials reference
    mapping_config JSONB NOT NULL, -- field mappings, transformations
    refresh_schedule VARCHAR(50), -- cron expression or 'manual'
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_status VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.data_pipe_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipe_id UUID REFERENCES public.data_pipes(pipe_id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL, -- running, success, failed
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    execution_log JSONB
);
```

**MVP Scope (Limited):**
- Basic UI for viewing detected data properties
- Manual data pipe creation for database sources
- Simple field mapping interface
- Test connection functionality
- Manual sync execution
- View sync history and status

**Future Enhancements:**
- Advanced transformation rules
- Real-time data streaming
- Data quality monitoring
- Automated sync scheduling
- Complex JOIN operations

### 3. Project-Scoped Resources & Admin Approval

#### Enhanced Project Isolation

**Principle:** All resources are project-specific by default, becoming global only through explicit admin action.

**Resource Types:**
- Ontologies (base + imported)
- Documents/Files
- Knowledge Assets
- Data Pipes
- LLM Agents/Prompts

**Implementation:**

```sql
-- Add project approval table
CREATE TABLE IF NOT EXISTS public.project_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(project_id),
    requested_by UUID REFERENCES public.users(user_id),
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by UUID REFERENCES public.users(user_id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    approval_type VARCHAR(50) NOT NULL, -- full_project, specific_resources
    resource_list JSONB, -- if specific_resources
    review_notes TEXT,
    approval_metadata JSONB -- quality scores, compliance checks
);

-- Add global resource tracking
ALTER TABLE public.files ADD COLUMN made_global_via_project UUID REFERENCES public.projects(project_id);
ALTER TABLE public.knowledge_assets ADD COLUMN made_global_via_project UUID REFERENCES public.projects(project_id);
```

**Approval Workflows:**

1. **Individual Resource Approval** (Current)
   - Admin manually reviews and approves each resource
   - Suitable for high-value, selective sharing

2. **Project-Level Approval** (New)
   - Submit entire project for review
   - Quality gates and automated checks
   - Batch approval of all project resources
   - Resources tagged with source project

**Quality Gates for Project Approval:**
- Ontology validation (SHACL compliance)
- Documentation completeness (>80% coverage)
- Knowledge asset quality scores (>0.7 average)
- No conflicting global resources
- Passing test cases (if defined)

### 4. LLM Playground Integration

#### Relocate Knowledge RAG Interface

**Current State:** RAG query interface embedded in knowledge detail view

**Proposed State:** Consolidated in LLM Playground for unified experimentation

**Benefits:**
- Test different LLM models (OpenAI, Ollama) in one place
- Compare responses across models
- Experiment with prompt engineering
- Create and test LLM agents
- Access both project and global knowledge

**Implementation:**

```typescript
// LLM Playground Components
interface PlaygroundConfig {
    context: {
        knowledge_scope: 'project' | 'global' | 'both';
        project_ids?: string[];
        document_types?: string[];
        include_ontology: boolean;
    };
    model: {
        provider: 'openai' | 'ollama' | 'anthropic';
        model_name: string;
        temperature: number;
        max_tokens: number;
    };
    agents?: LLMAgent[];
}

interface LLMAgent {
    agent_id: string;
    name: string;
    role: string;
    system_prompt: string;
    tools?: string[]; // available functions
    constraints?: string[];
}
```

**UI Features:**
- Split-panel interface (query + response)
- Model selector with settings
- Context scope controls
- Query history with versioning
- Response comparison view
- Agent builder interface
- Prompt template library
- Export conversations

**Agent Management:**
```sql
CREATE TABLE IF NOT EXISTS public.llm_agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(project_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    role VARCHAR(100),
    system_prompt TEXT NOT NULL,
    model_config JSONB NOT NULL,
    tools JSONB DEFAULT '[]',
    is_global BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES public.users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5. Enhanced Project Workflow Controls

#### Project Lifecycle Management

**States:**
1. **Draft** - Active development, all resources private
2. **Review** - Submitted for approval, read-only
3. **Approved** - Resources available globally
4. **Archived** - Historical reference only

**Workflow Implementation:**

```mermaid
stateDiagram-v2
    [*] --> Draft: Create Project
    Draft --> Review: Submit for Approval
    Review --> Draft: Request Changes
    Review --> Approved: Admin Approve
    Approved --> Archived: Archive Project
    Draft --> Archived: Archive Project
```

**API Endpoints:**
- `POST /api/projects/{id}/submit-review` - Submit project for approval
- `POST /api/admin/projects/{id}/review` - Admin review action
- `GET /api/projects/{id}/approval-status` - Check approval status
- `POST /api/projects/{id}/archive` - Archive project

## 🧪 Synthesized Test Data Strategy

### Overview
To validate the Data Manager Workbench and ensure robust testing without external dependencies, we'll create a comprehensive synthesized test dataset covering all supported data source types.

### Test Data Components

#### 1. Database Test Data

**Test Schema (PostgreSQL):**
```sql
-- Test schema for aerospace components
CREATE SCHEMA IF NOT EXISTS odras_test;

-- Aircraft components table
CREATE TABLE IF NOT EXISTS odras_test.aircraft_components (
    component_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_number VARCHAR(50) UNIQUE NOT NULL,
    component_name VARCHAR(255) NOT NULL,
    component_type VARCHAR(100), -- engine, avionics, structure, hydraulics
    manufacturer VARCHAR(255),
    weight_kg DECIMAL(10,2),
    cost_usd DECIMAL(12,2),
    certification_date DATE,
    mtbf_hours INTEGER, -- Mean Time Between Failures
    temperature_rating_min INTEGER, -- Celsius
    temperature_rating_max INTEGER, -- Celsius
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sensor readings table (time-series data)
CREATE TABLE IF NOT EXISTS odras_test.sensor_readings (
    reading_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sensor_id VARCHAR(50) NOT NULL,
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),
    reading_type VARCHAR(50), -- temperature, pressure, vibration, voltage
    value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    quality_score DECIMAL(3,2), -- 0.00 to 1.00
    INDEX idx_sensor_time (sensor_id, timestamp)
);

-- Requirements compliance table
CREATE TABLE IF NOT EXISTS odras_test.compliance_records (
    compliance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),
    requirement_id VARCHAR(50) NOT NULL, -- Links to ontology requirements
    compliance_status VARCHAR(50), -- compliant, non_compliant, partial, pending
    test_date DATE,
    test_results JSONB,
    notes TEXT
);

-- Insert sample data
INSERT INTO odras_test.aircraft_components 
(part_number, component_name, component_type, manufacturer, weight_kg, cost_usd, certification_date, mtbf_hours, temperature_rating_min, temperature_rating_max)
VALUES 
('GPS-NAV-001', 'GPS Navigation Module', 'avionics', 'TechAvionics Corp', 2.5, 15000.00, '2023-06-15', 10000, -40, 85),
('ENG-CTRL-A1', 'Engine Control Unit', 'engine', 'AeroControls Inc', 5.2, 45000.00, '2023-03-20', 8000, -55, 125),
('HYD-PUMP-B2', 'Hydraulic Pump Assembly', 'hydraulics', 'FluidDynamics Ltd', 12.8, 28000.00, '2022-11-10', 5000, -40, 100),
('STR-BEAM-C3', 'Structural Support Beam', 'structure', 'AeroStructures', 45.0, 8500.00, '2023-01-05', 50000, -60, 150);

-- Generate time-series sensor data
INSERT INTO odras_test.sensor_readings (sensor_id, component_id, reading_type, value, unit, timestamp, quality_score)
SELECT 
    'TEMP-' || comp.part_number,
    comp.component_id,
    'temperature',
    20 + (RANDOM() * 40), -- 20-60°C
    'celsius',
    NOW() - (interval '1 hour' * generate_series(1, 168)), -- Last 7 days hourly
    0.85 + (RANDOM() * 0.15) -- 0.85-1.00 quality
FROM odras_test.aircraft_components comp
WHERE comp.component_type IN ('avionics', 'engine');
```

#### 2. Mock API Endpoints

**Test API Server (FastAPI):**
```python
# test_api_server.py
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import random
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="ODRAS Test Data API")

class MaintenanceRecord(BaseModel):
    record_id: str
    component_id: str
    maintenance_type: str
    performed_date: datetime
    next_due_date: datetime
    technician: str
    status: str
    cost: float

class WeatherData(BaseModel):
    location: str
    timestamp: datetime
    temperature: float
    pressure: float
    humidity: float
    visibility: float
    conditions: str

@app.get("/api/v1/maintenance/{component_id}")
async def get_maintenance_history(component_id: str, limit: int = 10) -> List[MaintenanceRecord]:
    """Mock maintenance history for a component"""
    records = []
    for i in range(limit):
        performed = datetime.now() - timedelta(days=30*i)
        records.append(MaintenanceRecord(
            record_id=f"MNT-{component_id}-{i:03d}",
            component_id=component_id,
            maintenance_type=random.choice(["inspection", "repair", "replacement", "calibration"]),
            performed_date=performed,
            next_due_date=performed + timedelta(days=90),
            technician=f"Tech-{random.randint(100, 999)}",
            status=random.choice(["completed", "pending_parts", "scheduled"]),
            cost=random.uniform(500, 5000)
        ))
    return records

@app.get("/api/v1/weather/conditions")
async def get_weather_conditions(lat: float, lon: float) -> WeatherData:
    """Mock weather data for flight conditions"""
    return WeatherData(
        location=f"{lat},{lon}",
        timestamp=datetime.now(),
        temperature=15 + random.uniform(-10, 25),
        pressure=1013 + random.uniform(-20, 20),
        humidity=random.uniform(30, 90),
        visibility=random.uniform(1, 10),
        conditions=random.choice(["clear", "cloudy", "rain", "fog", "snow"])
    )

@app.get("/api/v1/supply-chain/{part_number}")
async def get_supply_chain_data(part_number: str):
    """Mock supply chain data"""
    return {
        "part_number": part_number,
        "suppliers": [
            {
                "supplier_id": f"SUP-{i:03d}",
                "name": f"Supplier {chr(65+i)}",
                "lead_time_days": random.randint(7, 60),
                "price": random.uniform(100, 10000),
                "availability": random.choice(["in_stock", "low_stock", "out_of_stock"]),
                "quality_rating": round(random.uniform(3.5, 5.0), 1)
            }
            for i in range(3)
        ],
        "last_updated": datetime.now().isoformat()
    }
```

#### 3. Sample CAD/STL Files

**Generate Test STL Files:**
```python
# generate_test_stl.py
import numpy as np
from stl import mesh

def create_test_bracket_stl():
    """Create a simple bracket STL for testing"""
    # Define vertices for a simple L-shaped bracket
    vertices = np.array([
        [0, 0, 0], [100, 0, 0], [100, 20, 0], [0, 20, 0],  # Base
        [0, 0, 10], [100, 0, 10], [100, 20, 10], [0, 20, 10],  # Base top
        [0, 0, 10], [20, 0, 10], [20, 0, 80], [0, 0, 80],  # Vertical
        [0, 20, 10], [20, 20, 10], [20, 20, 80], [0, 20, 80]  # Vertical other side
    ])
    
    # Define faces
    faces = np.array([
        [0,3,1], [1,3,2],  # Bottom
        [4,5,7], [5,6,7],  # Top base
        [0,1,5], [0,5,4],  # Front base
        [2,3,7], [2,7,6],  # Back base
        [8,11,9], [9,11,10],  # Vertical front
        [12,13,15], [13,14,15]  # Vertical back
    ])
    
    # Create mesh
    bracket = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            bracket.vectors[i][j] = vertices[f[j],:]
    
    # Add metadata as comments
    bracket.save('test_data/cad/bracket_GPS-NAV-001.stl')
    
    # Create metadata file
    metadata = {
        "file": "bracket_GPS-NAV-001.stl",
        "part_number": "GPS-NAV-001",
        "material": "Aluminum 6061-T6",
        "volume_cm3": 24.5,
        "surface_area_cm2": 156.8,
        "weight_g": 66.15,
        "bounding_box": {
            "x": 100, "y": 20, "z": 80
        },
        "tolerance": "+/- 0.1mm",
        "finish": "Anodized"
    }
    
    import json
    with open('test_data/cad/bracket_GPS-NAV-001.json', 'w') as f:
        json.dump(metadata, f, indent=2)

# Generate multiple test CAD files
components = [
    ("GPS-NAV-001", "GPS Mount Bracket"),
    ("ENG-CTRL-A1", "Engine Controller Housing"),
    ("HYD-PUMP-B2", "Pump Mounting Plate"),
    ("STR-BEAM-C3", "Structural Connector")
]

for part_number, description in components:
    create_test_bracket_stl()  # Simplified - would create different geometries
```

#### 4. Test Ontology with Data Properties

**Extend Test Ontology:**
```turtle
@prefix odras: <http://odras.local/onto/aerospace#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Data Properties for testing Data Manager
odras:partNumber a owl:DatatypeProperty ;
    rdfs:label "Part Number" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:string .

odras:weight a owl:DatatypeProperty ;
    rdfs:label "Weight" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:decimal ;
    odras:unit "kilogram" .

odras:operatingTemperature a owl:DatatypeProperty ;
    rdfs:label "Operating Temperature" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:decimal ;
    odras:unit "celsius" .

odras:certificationDate a owl:DatatypeProperty ;
    rdfs:label "Certification Date" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:date .

odras:mtbfHours a owl:DatatypeProperty ;
    rdfs:label "Mean Time Between Failures" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:integer ;
    odras:unit "hours" .

odras:supplierLeadTime a owl:DatatypeProperty ;
    rdfs:label "Supplier Lead Time" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:integer ;
    odras:unit "days" .

odras:complianceStatus a owl:DatatypeProperty ;
    rdfs:label "Compliance Status" ;
    rdfs:domain odras:Component ;
    rdfs:range xsd:string ;
    odras:allowedValues "compliant,non_compliant,partial,pending" .
```

### Test Data Initialization Scripts

**Master Test Data Setup:**
```bash
#!/bin/bash
# setup_test_data.sh

echo "Setting up ODRAS test data environment..."

# 1. Create test database schema and data
echo "Creating test database..."
psql -U $POSTGRES_USER -d $POSTGRES_DB -f test_data/sql/create_test_schema.sql
psql -U $POSTGRES_USER -d $POSTGRES_DB -f test_data/sql/insert_test_data.sql

# 2. Start mock API server
echo "Starting mock API server..."
cd test_data/api && uvicorn test_api_server:app --host 0.0.0.0 --port 8888 --reload &

# 3. Generate CAD test files
echo "Generating CAD test files..."
python test_data/cad/generate_test_stl.py

# 4. Load test ontology
echo "Loading test ontology with data properties..."
curl -X POST http://localhost:3030/test/data \
     -H "Content-Type: text/turtle" \
     -d @test_data/ontology/test_data_properties.ttl

# 5. Create test data pipes configuration
echo "Creating default data pipe configurations..."
python test_data/create_test_pipes.py

echo "Test data setup complete!"
```

### Integration Test Scenarios

**Data Manager Test Cases:**
```python
# test_data_manager_integration.py
import pytest
from datetime import datetime

class TestDataManagerIntegration:
    
    @pytest.fixture
    def test_project(self):
        """Create test project with ontology"""
        # Setup code
        return project_id
    
    def test_database_pipe_sync(self, test_project):
        """Test syncing component data from PostgreSQL"""
        # Create pipe configuration
        pipe_config = {
            "pipe_type": "database",
            "source_config": {
                "driver": "postgresql",
                "connection_string": "postgresql://test:test@localhost/odras_test"
            },
            "mapping": {
                "query": "SELECT * FROM aircraft_components",
                "bindings": {
                    "odras:partNumber": "part_number",
                    "odras:weight": "weight_kg",
                    "odras:certificationDate": "certification_date"
                }
            }
        }
        
        # Execute sync
        result = data_manager.sync_pipe(pipe_config)
        
        # Verify RDF triples created
        assert result.records_processed == 4
        assert result.status == "success"
    
    def test_api_pipe_realtime(self, test_project):
        """Test API integration for maintenance data"""
        pipe_config = {
            "pipe_type": "api",
            "source_config": {
                "endpoint": "http://localhost:8888/api/v1/maintenance/{component_id}",
                "method": "GET",
                "auth": None
            },
            "mapping": {
                "response_path": "$",
                "bindings": {
                    "odras:maintenanceDate": "$.performed_date",
                    "odras:maintenanceCost": "$.cost"
                }
            }
        }
        
        # Test with specific component
        result = data_manager.sync_pipe(pipe_config, {"component_id": "GPS-NAV-001"})
        assert len(result.data) > 0
    
    def test_cad_metadata_extraction(self, test_project):
        """Test CAD file metadata extraction"""
        pipe_config = {
            "pipe_type": "file",
            "source_config": {
                "path": "test_data/cad/",
                "pattern": "*.json",
                "format": "json"
            },
            "mapping": {
                "bindings": {
                    "odras:cadVolume": "$.volume_cm3",
                    "odras:cadWeight": "$.weight_g",
                    "odras:cadMaterial": "$.material"
                }
            }
        }
        
        result = data_manager.sync_pipe(pipe_config)
        assert result.records_processed == 4
```

### Performance Test Data

**Load Testing Dataset:**
```python
# generate_load_test_data.py
def generate_large_dataset():
    """Generate larger dataset for performance testing"""
    
    # 10,000 components
    components = []
    for i in range(10000):
        components.append({
            "part_number": f"COMP-{i:06d}",
            "name": f"Component {i}",
            "type": random.choice(["engine", "avionics", "structure", "hydraulics"]),
            "weight": random.uniform(0.1, 100),
            "cost": random.uniform(10, 50000)
        })
    
    # 1 million sensor readings
    readings = []
    for comp in components[:1000]:  # First 1000 components
        for hour in range(1000):  # Last 1000 hours
            readings.append({
                "component_id": comp["part_number"],
                "timestamp": datetime.now() - timedelta(hours=hour),
                "temperature": random.uniform(20, 80),
                "pressure": random.uniform(0.8, 1.2)
            })
    
    return components, readings
```

### Benefits of Test Data Strategy

1. **Isolation**: No external dependencies during development/testing
2. **Repeatability**: Consistent test results across environments
3. **Coverage**: Tests all data source types (DB, API, Files)
4. **Performance**: Can generate scaled datasets for load testing
5. **Validation**: Ensures Data Manager handles various data formats
6. **Documentation**: Test data serves as usage examples

## 📋 Implementation Plan

### Week 2 Sprint Plan

#### Sprint 1: Single Ontology per Project (Days 1-2)
- [ ] **SO-1**: Database schema updates for single ontology enforcement
- [ ] **SO-2**: Modify project creation to include base ontology
- [ ] **SO-3**: Update ontology workbench to work with single project ontology
- [ ] **SO-4**: Implement ontology release workflow (API)
- [ ] **SO-5**: Add import functionality for released ontologies
- [ ] **SO-6**: Update UI to show ontology status and imports

#### Sprint 2: Data Manager Workbench Foundation (Days 2-3)
- [ ] **DM-1**: Create database schema for data pipes
- [ ] **DM-2**: Implement data property detection service
- [ ] **DM-3**: Basic Data Manager UI route and layout
- [ ] **DM-4**: Database connection configuration UI
- [ ] **DM-5**: Simple mapping interface (property to column)
- [ ] **DM-6**: Test connection and manual sync functionality

#### Sprint 3: Project Approval Workflow (Days 3-4)
- [ ] **PA-1**: Create project approval database schema
- [ ] **PA-2**: Implement quality gate checks (automated)
- [ ] **PA-3**: Project submission API endpoints
- [ ] **PA-4**: Admin review interface
- [ ] **PA-5**: Batch resource promotion logic
- [ ] **PA-6**: Project state management and transitions

#### Sprint 4: LLM Playground Enhancement (Days 4-5)
- [ ] **LP-1**: Move RAG query interface to LLM Playground
- [ ] **LP-2**: Implement model selection and comparison
- [ ] **LP-3**: Add context scope controls (project/global)
- [ ] **LP-4**: Create agent builder interface
- [ ] **LP-5**: Implement prompt template management
- [ ] **LP-6**: Add conversation export functionality

#### Sprint 5: Integration and Testing (Day 5)
- [ ] **IT-1**: Integration testing across all new components
- [ ] **IT-2**: Update documentation and user guides
- [ ] **IT-3**: Migration scripts for existing data
- [ ] **IT-4**: Performance optimization
- [ ] **IT-5**: Security audit of new features

## 🎯 Acceptance Criteria

### Single Ontology per Project
- [ ] Each project has exactly one base ontology
- [ ] Imported ontologies are read-only and properly overlaid
- [ ] Admin can release ontologies for import by other projects
- [ ] Clear visual distinction between base and imported ontologies

### Data Manager Workbench
- [ ] Data properties automatically detected from ontology
- [ ] Can create database connections and test them
- [ ] Simple mapping interface functional
- [ ] Manual sync executes successfully
- [ ] Sync history and status visible

### Project Approval
- [ ] Projects can be submitted for approval
- [ ] Quality gates run automatically
- [ ] Admin can approve/reject with notes
- [ ] Approved resources become globally accessible
- [ ] Clear audit trail of approvals

### LLM Playground
- [ ] RAG queries work in playground
- [ ] Can switch between models
- [ ] Context scope controls functional
- [ ] Query history maintained
- [ ] Agents can be created and tested

## 🚧 Risk Mitigation

### Technical Risks
1. **Data Pipeline Complexity** - Start with simple database sources only
2. **Performance Impact** - Implement caching and lazy loading
3. **Migration Complexity** - Provide backwards compatibility mode

### Process Risks
1. **User Adoption** - Provide clear migration guides
2. **Approval Bottlenecks** - Implement automated quality checks
3. **Data Security** - Encrypt credentials, audit all access

## 📚 References and Best Practices

### Ontology Data Management
- **Semantic Web Best Practices**: Separation of TBox (schema) and ABox (instances)
- **Data Property Patterns**: Use rdfs:range for data types, maintain cardinality constraints
- **External Data Integration**: Maintain provenance, versioning, and update timestamps

### Project Isolation Patterns
- **Multi-tenancy**: Logical isolation with shared infrastructure
- **Resource Namespacing**: Use project IDs in all resource identifiers
- **Cross-project Sharing**: Explicit permissions and audit trails

### LLM Integration
- **Context Windows**: Optimize chunk selection for token limits
- **Model Comparison**: Standardize prompts for fair comparison
- **Agent Design**: Clear roles, constrained actions, testable outcomes

---

*This enhancement plan builds upon the successful ODRAS Phase 1 implementation to create a more structured, governed system for ontology-driven requirements analysis and knowledge management.*
