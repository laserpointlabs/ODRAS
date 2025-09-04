# ODRAS Test Data Setup Guide

## Overview

This guide provides comprehensive instructions for setting up and using the ODRAS synthesized test data environment. The test data covers all supported data source types for the Data Manager Workbench, enabling thorough testing without external dependencies.

## Prerequisites

- PostgreSQL 13+ with superuser access
- Python 3.9+ with pip
- Docker (for running test services)
- Node.js 16+ (for mock API server alternative)
- Basic knowledge of SQL and REST APIs

## Quick Start

```bash
# Clone the ODRAS repository
git clone https://github.com/your-org/odras.git
cd odras

# Run the complete test data setup
./scripts/setup_test_data.sh

# Verify test data is loaded
./scripts/verify_test_data.sh
```

## Component Setup

### 1. Database Test Data

#### Create Test Schema
```bash
# Connect to PostgreSQL
psql -U postgres -d odras_db

# Run schema creation script
\i test_data/sql/create_test_schema.sql
```

#### Load Sample Data
```sql
-- Insert aerospace components
\i test_data/sql/insert_aerospace_components.sql

-- Generate time-series sensor data
\i test_data/sql/generate_sensor_data.sql

-- Create compliance records
\i test_data/sql/create_compliance_records.sql
```

#### Verify Data
```sql
-- Check component count
SELECT COUNT(*) FROM odras_test.aircraft_components;
-- Expected: 4 base components + any additional test data

-- Check sensor readings
SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
FROM odras_test.sensor_readings;
-- Expected: ~1,344 readings (4 components × 2 sensors × 168 hours)
```

### 2. Mock API Server

#### Option A: Python FastAPI
```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# Start mock API server
cd test_data/api
uvicorn test_api_server:app --host 0.0.0.0 --port 8888 --reload
```

#### Option B: Docker Container
```bash
# Build and run mock API container
docker build -t odras-mock-api test_data/api/
docker run -p 8888:8888 odras-mock-api
```

#### Test API Endpoints
```bash
# Test maintenance history endpoint
curl http://localhost:8888/api/v1/maintenance/GPS-NAV-001

# Test weather conditions
curl "http://localhost:8888/api/v1/weather/conditions?lat=37.7749&lon=-122.4194"

# Test supply chain data
curl http://localhost:8888/api/v1/supply-chain/GPS-NAV-001
```

### 3. CAD Test Files

#### Generate STL Files
```bash
# Install Python STL library
pip install numpy-stl

# Generate test CAD files
python test_data/cad/generate_test_stl.py

# Verify files created
ls -la test_data/cad/
# Expected: 4 STL files + 4 JSON metadata files
```

#### CAD File Structure
Each component has:
- `.stl` file - 3D geometry data
- `.json` file - Metadata (material, weight, dimensions)

Example metadata:
```json
{
  "file": "bracket_GPS-NAV-001.stl",
  "part_number": "GPS-NAV-001",
  "material": "Aluminum 6061-T6",
  "volume_cm3": 24.5,
  "weight_g": 66.15,
  "bounding_box": {
    "x": 100, "y": 20, "z": 80
  }
}
```

### 4. Test Ontology Setup

#### Load Data Properties
```bash
# Load test ontology with data properties
curl -X POST http://localhost:3030/odras/data \
     -H "Content-Type: text/turtle" \
     -d @test_data/ontology/aerospace_data_properties.ttl

# Verify properties loaded
curl -X POST http://localhost:3030/odras/query \
     -H "Content-Type: application/sparql-query" \
     -d "SELECT ?prop WHERE { ?prop a owl:DatatypeProperty }"
```

## Data Manager Test Scenarios

### Scenario 1: Database Integration

1. **Configure Database Pipe**
```json
{
  "pipe_name": "Component Master Data",
  "pipe_type": "database",
  "source_config": {
    "driver": "postgresql",
    "host": "localhost",
    "database": "odras_db",
    "schema": "odras_test",
    "credentials_ref": "test_db_creds"
  },
  "mapping": {
    "query": "SELECT * FROM aircraft_components WHERE component_type = :type",
    "parameters": {
      "type": "avionics"
    },
    "bindings": {
      "odras:partNumber": "part_number",
      "odras:weight": {
        "column": "weight_kg",
        "transform": "kg_to_g"
      },
      "odras:certificationDate": "certification_date"
    }
  }
}
```

2. **Execute Sync**
```bash
# Via API
curl -X POST http://localhost:8000/api/data-pipes/execute \
     -H "Authorization: Bearer $TOKEN" \
     -d @pipe_configs/component_master.json

# Via UI
# Navigate to Data Manager Workbench
# Select "Component Master Data" pipe
# Click "Run Sync"
```

### Scenario 2: API Integration

1. **Configure API Pipe**
```json
{
  "pipe_name": "Maintenance History",
  "pipe_type": "api",
  "source_config": {
    "base_url": "http://localhost:8888",
    "endpoints": {
      "maintenance": "/api/v1/maintenance/{component_id}"
    }
  },
  "mapping": {
    "iterate_over": "components",
    "response_path": "$[*]",
    "bindings": {
      "odras:maintenanceDate": "performed_date",
      "odras:maintenanceCost": "cost",
      "odras:maintenanceType": "maintenance_type"
    }
  }
}
```

### Scenario 3: File-Based Integration

1. **Configure File Pipe**
```json
{
  "pipe_name": "CAD Metadata Import",
  "pipe_type": "file",
  "source_config": {
    "directory": "test_data/cad",
    "pattern": "*.json",
    "watch": false
  },
  "mapping": {
    "format": "json",
    "bindings": {
      "odras:cadVolume": "volume_cm3",
      "odras:cadWeight": "weight_g",
      "odras:cadMaterial": "material",
      "odras:cadTolerance": "tolerance"
    }
  }
}
```

## Performance Testing

### Generate Large Dataset
```python
# Run performance data generator
python test_data/generate_performance_data.py \
    --components 10000 \
    --sensors-per-component 10 \
    --readings-per-sensor 1000
```

### Load Test Configuration
```yaml
# load_test_config.yaml
scenarios:
  - name: "Bulk Component Sync"
    pipe_type: "database"
    records: 10000
    batch_size: 1000
    
  - name: "High-Frequency Sensor Data"
    pipe_type: "database"
    records: 1000000
    batch_size: 5000
    
  - name: "Concurrent API Calls"
    pipe_type: "api"
    concurrent_requests: 50
    duration_seconds: 300
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify test schema exists
psql -U postgres -d odras_db -c "\dn odras_test.*"
```

2. **Mock API Not Responding**
```bash
# Check if port 8888 is in use
lsof -i :8888

# View API logs
docker logs odras-mock-api
```

3. **STL Generation Errors**
```bash
# Ensure numpy-stl is installed
pip show numpy-stl

# Check Python version (requires 3.9+)
python --version
```

## Cleanup

```bash
# Remove all test data
./scripts/cleanup_test_data.sh

# Or manually:
# Drop test schema
psql -U postgres -d odras_db -c "DROP SCHEMA odras_test CASCADE;"

# Stop mock API
docker stop odras-mock-api

# Remove test files
rm -rf test_data/cad/*.stl test_data/cad/*.json
```

## Best Practices

1. **Isolation**: Run test data in separate schema/namespace
2. **Versioning**: Tag test data versions with releases
3. **Documentation**: Keep test scenarios documented
4. **Automation**: Include in CI/CD pipeline
5. **Monitoring**: Log all test data operations

## Test Data Maintenance

### Weekly Tasks
- Refresh time-series data to keep timestamps current
- Rotate API test logs
- Update component prices/costs

### Monthly Tasks
- Review and update test scenarios
- Add new edge cases based on bugs found
- Performance baseline updates

### Release Tasks
- Ensure test data compatible with schema changes
- Update API mock responses for new features
- Document any new test data requirements

## Contact

For questions or issues with test data:
- Create issue in ODRAS repository
- Tag with `test-data` label
- Include logs and configuration used


