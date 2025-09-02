#!/bin/bash
#
# ODRAS Test Data Setup Script
# Sets up complete test environment for Data Manager Workbench
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DATA_DIR="$PROJECT_ROOT/test_data"

# Default values (can be overridden by environment variables)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-odras_db}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
API_PORT="${API_PORT:-8888}"

echo -e "${GREEN}=== ODRAS Test Data Setup ===${NC}"
echo "Setting up test environment in: $PROJECT_ROOT"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if PostgreSQL is running
check_postgres() {
    echo -n "Checking PostgreSQL connection... "
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
        return 1
    fi
}

# Function to check if Fuseki is running
check_fuseki() {
    echo -n "Checking Fuseki connection... "
    if curl -s -f "$FUSEKI_URL/$/ping" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${YELLOW}WARNING${NC}"
        echo "Fuseki not available at $FUSEKI_URL - skipping ontology setup"
        return 1
    fi
}

# Create test data directory structure
create_directories() {
    echo "Creating test data directories..."
    mkdir -p "$TEST_DATA_DIR"/{sql,api,cad,ontology,configs}
    echo -e "${GREEN}✓${NC} Directory structure created"
}

# Generate SQL scripts
generate_sql_scripts() {
    echo "Generating SQL scripts..."
    
    # Create schema script
    cat > "$TEST_DATA_DIR/sql/create_test_schema.sql" << 'EOF'
-- ODRAS Test Schema for Data Manager Workbench
-- Aerospace components test data

-- Create test schema
CREATE SCHEMA IF NOT EXISTS odras_test;

-- Aircraft components table
CREATE TABLE IF NOT EXISTS odras_test.aircraft_components (
    component_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_number VARCHAR(50) UNIQUE NOT NULL,
    component_name VARCHAR(255) NOT NULL,
    component_type VARCHAR(100),
    manufacturer VARCHAR(255),
    weight_kg DECIMAL(10,2),
    cost_usd DECIMAL(12,2),
    certification_date DATE,
    mtbf_hours INTEGER,
    temperature_rating_min INTEGER,
    temperature_rating_max INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sensor readings table
CREATE TABLE IF NOT EXISTS odras_test.sensor_readings (
    reading_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_id VARCHAR(50) NOT NULL,
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),
    reading_type VARCHAR(50),
    value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    quality_score DECIMAL(3,2)
);

-- Create index for time-series queries
CREATE INDEX IF NOT EXISTS idx_sensor_time 
ON odras_test.sensor_readings(sensor_id, timestamp);

-- Compliance records table
CREATE TABLE IF NOT EXISTS odras_test.compliance_records (
    compliance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id UUID REFERENCES odras_test.aircraft_components(component_id),
    requirement_id VARCHAR(50) NOT NULL,
    compliance_status VARCHAR(50),
    test_date DATE,
    test_results JSONB,
    notes TEXT
);
EOF

    # Create data insertion script
    cat > "$TEST_DATA_DIR/sql/insert_test_data.sql" << 'EOF'
-- Insert sample aerospace components
INSERT INTO odras_test.aircraft_components 
(part_number, component_name, component_type, manufacturer, weight_kg, cost_usd, 
 certification_date, mtbf_hours, temperature_rating_min, temperature_rating_max)
VALUES 
('GPS-NAV-001', 'GPS Navigation Module', 'avionics', 'TechAvionics Corp', 2.5, 15000.00, 
 '2023-06-15', 10000, -40, 85),
('ENG-CTRL-A1', 'Engine Control Unit', 'engine', 'AeroControls Inc', 5.2, 45000.00, 
 '2023-03-20', 8000, -55, 125),
('HYD-PUMP-B2', 'Hydraulic Pump Assembly', 'hydraulics', 'FluidDynamics Ltd', 12.8, 28000.00, 
 '2022-11-10', 5000, -40, 100),
('STR-BEAM-C3', 'Structural Support Beam', 'structure', 'AeroStructures', 45.0, 8500.00, 
 '2023-01-05', 50000, -60, 150)
ON CONFLICT (part_number) DO NOTHING;

-- Generate time-series sensor data
INSERT INTO odras_test.sensor_readings (sensor_id, component_id, reading_type, value, unit, timestamp, quality_score)
SELECT 
    'TEMP-' || comp.part_number,
    comp.component_id,
    'temperature',
    20 + (RANDOM() * 40),
    'celsius',
    NOW() - (INTERVAL '1 hour' * s.hour_offset),
    0.85 + (RANDOM() * 0.15)
FROM odras_test.aircraft_components comp
CROSS JOIN generate_series(1, 168) AS s(hour_offset)
WHERE comp.component_type IN ('avionics', 'engine')
ON CONFLICT DO NOTHING;

-- Insert compliance records
INSERT INTO odras_test.compliance_records 
(component_id, requirement_id, compliance_status, test_date, test_results)
SELECT 
    component_id,
    'REQ-NAV-' || LPAD(s.req_num::TEXT, 3, '0'),
    CASE WHEN RANDOM() > 0.1 THEN 'compliant' ELSE 'partial' END,
    CURRENT_DATE - INTERVAL '30 days' * (s.req_num % 12),
    jsonb_build_object(
        'test_id', 'TEST-' || LPAD((RANDOM() * 9999)::INT::TEXT, 4, '0'),
        'score', ROUND((0.7 + RANDOM() * 0.3)::NUMERIC, 2)
    )
FROM odras_test.aircraft_components
CROSS JOIN generate_series(1, 5) AS s(req_num)
WHERE component_type = 'avionics'
ON CONFLICT DO NOTHING;
EOF

    echo -e "${GREEN}✓${NC} SQL scripts generated"
}

# Setup PostgreSQL test data
setup_postgres_data() {
    echo "Setting up PostgreSQL test data..."
    
    if ! check_postgres; then
        return 1
    fi
    
    echo "Creating test schema..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -f "$TEST_DATA_DIR/sql/create_test_schema.sql" 2>/dev/null
    
    echo "Inserting test data..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -f "$TEST_DATA_DIR/sql/insert_test_data.sql" 2>/dev/null
    
    echo -e "${GREEN}✓${NC} PostgreSQL test data loaded"
}

# Generate Python mock API server
generate_mock_api() {
    echo "Generating mock API server..."
    
    cat > "$TEST_DATA_DIR/api/test_api_server.py" << 'EOF'
"""
ODRAS Mock API Server for Data Manager Testing
Provides sample endpoints for maintenance, weather, and supply chain data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import random
from typing import List, Optional
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="ODRAS Test Data API", version="1.0.0")

# Enable CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class SupplierInfo(BaseModel):
    supplier_id: str
    name: str
    lead_time_days: int
    price: float
    availability: str
    quality_rating: float

@app.get("/")
async def root():
    return {"message": "ODRAS Mock API Server", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/maintenance/{component_id}", response_model=List[MaintenanceRecord])
async def get_maintenance_history(component_id: str, limit: int = 10):
    """Get maintenance history for a component"""
    records = []
    for i in range(min(limit, 20)):
        performed = datetime.now() - timedelta(days=30*i)
        records.append(MaintenanceRecord(
            record_id=f"MNT-{component_id}-{i:03d}",
            component_id=component_id,
            maintenance_type=random.choice(["inspection", "repair", "replacement", "calibration"]),
            performed_date=performed,
            next_due_date=performed + timedelta(days=90),
            technician=f"Tech-{random.randint(100, 999)}",
            status=random.choice(["completed", "pending_parts", "scheduled"]),
            cost=round(random.uniform(500, 5000), 2)
        ))
    return records

@app.get("/api/v1/weather/conditions", response_model=WeatherData)
async def get_weather_conditions(lat: float, lon: float):
    """Get current weather conditions for location"""
    return WeatherData(
        location=f"{lat},{lon}",
        timestamp=datetime.now(),
        temperature=round(15 + random.uniform(-10, 25), 1),
        pressure=round(1013 + random.uniform(-20, 20), 1),
        humidity=round(random.uniform(30, 90), 1),
        visibility=round(random.uniform(1, 10), 1),
        conditions=random.choice(["clear", "cloudy", "rain", "fog", "snow"])
    )

@app.get("/api/v1/supply-chain/{part_number}")
async def get_supply_chain_data(part_number: str):
    """Get supply chain information for a part"""
    suppliers = []
    for i in range(3):
        suppliers.append(SupplierInfo(
            supplier_id=f"SUP-{i:03d}",
            name=f"Supplier {chr(65+i)}",
            lead_time_days=random.randint(7, 60),
            price=round(random.uniform(100, 10000), 2),
            availability=random.choice(["in_stock", "low_stock", "out_of_stock"]),
            quality_rating=round(random.uniform(3.5, 5.0), 1)
        ))
    
    return {
        "part_number": part_number,
        "suppliers": [s.dict() for s in suppliers],
        "last_updated": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
EOF

    # Create requirements file
    cat > "$TEST_DATA_DIR/api/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
EOF

    echo -e "${GREEN}✓${NC} Mock API server generated"
}

# Start mock API server
start_mock_api() {
    echo "Starting mock API server..."
    
    if ! command_exists python3; then
        echo -e "${YELLOW}WARNING${NC}: Python not found - skipping API server"
        return 1
    fi
    
    # Check if port is already in use
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}WARNING${NC}: Port $API_PORT already in use - API server may be running"
        return 0
    fi
    
    # Install dependencies if needed
    cd "$TEST_DATA_DIR/api"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt >/dev/null 2>&1
    else
        source venv/bin/activate
    fi
    
    # Start server in background
    nohup python test_api_server.py > api_server.log 2>&1 &
    echo $! > api_server.pid
    
    # Wait for server to start
    sleep 3
    
    # Test if server is running
    if curl -s -f "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Mock API server started on port $API_PORT"
    else
        echo -e "${RED}✗${NC} Failed to start mock API server"
        return 1
    fi
}

# Generate CAD test files
generate_cad_files() {
    echo "Generating CAD test files..."
    
    if ! command_exists python3; then
        echo -e "${YELLOW}WARNING${NC}: Python not found - skipping CAD file generation"
        return 1
    fi
    
    # Create CAD generator script
    cat > "$TEST_DATA_DIR/cad/generate_metadata.py" << 'EOF'
#!/usr/bin/env python3
"""Generate mock CAD metadata files for testing"""

import json
import os

components = [
    {
        "file": "bracket_GPS-NAV-001.stl",
        "part_number": "GPS-NAV-001",
        "material": "Aluminum 6061-T6",
        "volume_cm3": 24.5,
        "surface_area_cm2": 156.8,
        "weight_g": 66.15,
        "bounding_box": {"x": 100, "y": 20, "z": 80},
        "tolerance": "+/- 0.1mm",
        "finish": "Anodized"
    },
    {
        "file": "housing_ENG-CTRL-A1.stl",
        "part_number": "ENG-CTRL-A1",
        "material": "Magnesium AZ91D",
        "volume_cm3": 85.2,
        "surface_area_cm2": 234.5,
        "weight_g": 148.3,
        "bounding_box": {"x": 150, "y": 100, "z": 50},
        "tolerance": "+/- 0.15mm",
        "finish": "Powder Coated"
    },
    {
        "file": "plate_HYD-PUMP-B2.stl",
        "part_number": "HYD-PUMP-B2",
        "material": "Steel 316L",
        "volume_cm3": 156.8,
        "surface_area_cm2": 312.4,
        "weight_g": 1255.2,
        "bounding_box": {"x": 200, "y": 150, "z": 20},
        "tolerance": "+/- 0.2mm",
        "finish": "Machined"
    },
    {
        "file": "connector_STR-BEAM-C3.stl",
        "part_number": "STR-BEAM-C3",
        "material": "Titanium Ti-6Al-4V",
        "volume_cm3": 320.5,
        "surface_area_cm2": 485.2,
        "weight_g": 1442.3,
        "bounding_box": {"x": 300, "y": 50, "z": 100},
        "tolerance": "+/- 0.1mm",
        "finish": "As Machined"
    }
]

# Create metadata files
for comp in components:
    json_file = comp["file"].replace('.stl', '.json')
    with open(json_file, 'w') as f:
        json.dump(comp, f, indent=2)
    
    # Create dummy STL file (just for testing existence)
    stl_file = comp["file"]
    with open(stl_file, 'w') as f:
        f.write("solid " + comp["part_number"] + "\n")
        f.write("endsolid\n")

print(f"Generated {len(components)} CAD metadata files")
EOF

    # Generate files
    cd "$TEST_DATA_DIR/cad"
    python3 generate_metadata.py
    
    echo -e "${GREEN}✓${NC} CAD test files generated"
}

# Generate test ontology
generate_test_ontology() {
    echo "Generating test ontology..."
    
    cat > "$TEST_DATA_DIR/ontology/aerospace_data_properties.ttl" << 'EOF'
@prefix odras: <http://odras.local/onto/aerospace#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Ontology declaration
odras: a owl:Ontology ;
    rdfs:label "ODRAS Aerospace Test Ontology" ;
    rdfs:comment "Test ontology with data properties for Data Manager Workbench" .

# Classes
odras:Component a owl:Class ;
    rdfs:label "Component" ;
    rdfs:comment "An aerospace component" .

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
EOF

    echo -e "${GREEN}✓${NC} Test ontology generated"
}

# Load ontology to Fuseki
load_ontology() {
    echo "Loading test ontology to Fuseki..."
    
    if ! check_fuseki; then
        return 1
    fi
    
    # Create dataset if it doesn't exist
    curl -s -X POST "$FUSEKI_URL/$/datasets" \
         -H "Content-Type: application/x-www-form-urlencoded" \
         -d "dbName=test&dbType=tdb2" >/dev/null 2>&1 || true
    
    # Load ontology
    curl -s -X POST "$FUSEKI_URL/test/data" \
         -H "Content-Type: text/turtle" \
         -T "$TEST_DATA_DIR/ontology/aerospace_data_properties.ttl"
    
    echo -e "${GREEN}✓${NC} Test ontology loaded to Fuseki"
}

# Generate sample pipe configurations
generate_pipe_configs() {
    echo "Generating sample pipe configurations..."
    
    # Database pipe config
    cat > "$TEST_DATA_DIR/configs/db_components_pipe.json" << EOF
{
  "pipe_name": "Component Master Data",
  "pipe_type": "database",
  "ontology_property_iri": "http://odras.local/onto/aerospace#partNumber",
  "source_config": {
    "driver": "postgresql",
    "host": "$POSTGRES_HOST",
    "port": $POSTGRES_PORT,
    "database": "$POSTGRES_DB",
    "schema": "odras_test",
    "table": "aircraft_components"
  },
  "mapping_config": {
    "query": "SELECT * FROM odras_test.aircraft_components",
    "bindings": {
      "odras:partNumber": "part_number",
      "odras:weight": "weight_kg",
      "odras:certificationDate": "certification_date",
      "odras:mtbfHours": "mtbf_hours"
    }
  },
  "refresh_schedule": "manual"
}
EOF

    # API pipe config
    cat > "$TEST_DATA_DIR/configs/api_maintenance_pipe.json" << 'EOF'
{
  "pipe_name": "Maintenance History",
  "pipe_type": "api",
  "ontology_property_iri": "http://odras.local/onto/aerospace#maintenanceDate",
  "source_config": {
    "base_url": "http://localhost:8888",
    "endpoint": "/api/v1/maintenance/{component_id}",
    "method": "GET",
    "headers": {
      "Accept": "application/json"
    }
  },
  "mapping_config": {
    "response_path": "$[*]",
    "bindings": {
      "odras:maintenanceDate": "performed_date",
      "odras:maintenanceCost": "cost",
      "odras:maintenanceType": "maintenance_type"
    }
  },
  "refresh_schedule": "0 */6 * * *"
}
EOF

    # File pipe config
    cat > "$TEST_DATA_DIR/configs/file_cad_pipe.json" << EOF
{
  "pipe_name": "CAD Metadata Import",
  "pipe_type": "file",
  "ontology_property_iri": "http://odras.local/onto/aerospace#cadVolume",
  "source_config": {
    "directory": "$TEST_DATA_DIR/cad",
    "pattern": "*.json",
    "format": "json",
    "watch": false
  },
  "mapping_config": {
    "bindings": {
      "odras:partNumber": "part_number",
      "odras:cadVolume": "volume_cm3",
      "odras:cadWeight": "weight_g",
      "odras:cadMaterial": "material"
    }
  },
  "refresh_schedule": "manual"
}
EOF

    echo -e "${GREEN}✓${NC} Sample pipe configurations generated"
}

# Verify setup
verify_setup() {
    echo ""
    echo "Verifying test data setup..."
    echo ""
    
    # Check PostgreSQL data
    if check_postgres; then
        COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                -U $POSTGRES_USER -d $POSTGRES_DB -t \
                -c "SELECT COUNT(*) FROM odras_test.aircraft_components" 2>/dev/null || echo "0")
        echo "PostgreSQL components: $COUNT"
        
        COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                -U $POSTGRES_USER -d $POSTGRES_DB -t \
                -c "SELECT COUNT(*) FROM odras_test.sensor_readings" 2>/dev/null || echo "0")
        echo "PostgreSQL sensor readings: $COUNT"
    fi
    
    # Check API server
    if curl -s -f "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
        echo "Mock API server: Running on port $API_PORT"
    else
        echo "Mock API server: Not running"
    fi
    
    # Check CAD files
    if [ -d "$TEST_DATA_DIR/cad" ]; then
        STL_COUNT=$(find "$TEST_DATA_DIR/cad" -name "*.stl" | wc -l)
        JSON_COUNT=$(find "$TEST_DATA_DIR/cad" -name "*.json" | wc -l)
        echo "CAD files: $STL_COUNT STL files, $JSON_COUNT metadata files"
    fi
    
    echo ""
}

# Main execution
main() {
    # Check prerequisites
    echo "Checking prerequisites..."
    
    if ! command_exists psql; then
        echo -e "${YELLOW}WARNING${NC}: psql not found - PostgreSQL setup will be skipped"
    fi
    
    if ! command_exists python3; then
        echo -e "${YELLOW}WARNING${NC}: Python 3 not found - API and CAD generation will be skipped"
    fi
    
    if ! command_exists curl; then
        echo -e "${RED}ERROR${NC}: curl is required but not found"
        exit 1
    fi
    
    # Create directories
    create_directories
    
    # Generate all assets
    generate_sql_scripts
    generate_mock_api
    generate_cad_files
    generate_test_ontology
    generate_pipe_configs
    
    # Setup services
    setup_postgres_data
    start_mock_api
    load_ontology
    
    # Verify
    verify_setup
    
    echo ""
    echo -e "${GREEN}=== Test Data Setup Complete ===${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Access mock API at http://localhost:$API_PORT"
    echo "2. View test data in PostgreSQL schema 'odras_test'"
    echo "3. Use pipe configurations in $TEST_DATA_DIR/configs/"
    echo ""
    echo "To stop the mock API server:"
    echo "  kill \$(cat $TEST_DATA_DIR/api/api_server.pid)"
    echo ""
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--clean]"
        echo ""
        echo "Options:"
        echo "  --clean    Remove all test data before setup"
        echo "  --help     Show this help message"
        exit 0
        ;;
    --clean)
        echo "Cleaning existing test data..."
        if check_postgres; then
            PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                -U $POSTGRES_USER -d $POSTGRES_DB \
                -c "DROP SCHEMA IF EXISTS odras_test CASCADE" 2>/dev/null
        fi
        if [ -f "$TEST_DATA_DIR/api/api_server.pid" ]; then
            kill $(cat "$TEST_DATA_DIR/api/api_server.pid") 2>/dev/null || true
        fi
        rm -rf "$TEST_DATA_DIR"
        echo -e "${GREEN}✓${NC} Test data cleaned"
        ;;
esac

# Run main setup
main


