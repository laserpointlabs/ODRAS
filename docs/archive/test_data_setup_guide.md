# ODRAS Test Data Setup Guide<br>
<br>
## Overview<br>
<br>
This guide provides comprehensive instructions for setting up and using the ODRAS synthesized test data environment. The test data covers all supported data source types for the Data Manager Workbench, enabling thorough testing without external dependencies.<br>
<br>
## Prerequisites<br>
<br>
- PostgreSQL 13+ with superuser access<br>
- Python 3.9+ with pip<br>
- Docker (for running test services)<br>
- Node.js 16+ (for mock API server alternative)<br>
- Basic knowledge of SQL and REST APIs<br>
<br>
## Quick Start<br>
<br>
```bash<br>
# Clone the ODRAS repository<br>
git clone https://github.com/your-org/odras.git<br>
cd odras<br>
<br>
# Run the complete test data setup<br>
./scripts/setup_test_data.sh<br>
<br>
# Verify test data is loaded<br>
./scripts/verify_test_data.sh<br>
```<br>
<br>
## Component Setup<br>
<br>
### 1. Database Test Data<br>
<br>
#### Create Test Schema<br>
```bash<br>
# Connect to PostgreSQL<br>
psql -U postgres -d odras_db<br>
<br>
# Run schema creation script<br>
\i test_data/sql/create_test_schema.sql<br>
```<br>
<br>
#### Load Sample Data<br>
```sql<br>
-- Insert aerospace components<br>
\i test_data/sql/insert_aerospace_components.sql<br>
<br>
-- Generate time-series sensor data<br>
\i test_data/sql/generate_sensor_data.sql<br>
<br>
-- Create compliance records<br>
\i test_data/sql/create_compliance_records.sql<br>
```<br>
<br>
#### Verify Data<br>
```sql<br>
-- Check component count<br>
SELECT COUNT(*) FROM odras_test.aircraft_components;<br>
-- Expected: 4 base components + any additional test data<br>
<br>
-- Check sensor readings<br>
SELECT COUNT(*), MIN(timestamp), MAX(timestamp)<br>
FROM odras_test.sensor_readings;<br>
-- Expected: ~1,344 readings (4 components × 2 sensors × 168 hours)<br>
```<br>
<br>
### 2. Mock API Server<br>
<br>
#### Option A: Python FastAPI<br>
```bash<br>
# Install dependencies<br>
pip install fastapi uvicorn pydantic<br>
<br>
# Start mock API server<br>
cd test_data/api<br>
uvicorn test_api_server:app --host 0.0.0.0 --port 8888 --reload<br>
```<br>
<br>
#### Option B: Docker Container<br>
```bash<br>
# Build and run mock API container<br>
docker build -t odras-mock-api test_data/api/<br>
docker run -p 8888:8888 odras-mock-api<br>
```<br>
<br>
#### Test API Endpoints<br>
```bash<br>
# Test maintenance history endpoint<br>
curl http://localhost:8888/api/v1/maintenance/GPS-NAV-001<br>
<br>
# Test weather conditions<br>
curl "http://localhost:8888/api/v1/weather/conditions?lat=37.7749&lon=-122.4194"<br>
<br>
# Test supply chain data<br>
curl http://localhost:8888/api/v1/supply-chain/GPS-NAV-001<br>
```<br>
<br>
### 3. CAD Test Files<br>
<br>
#### Generate STL Files<br>
```bash<br>
# Install Python STL library<br>
pip install numpy-stl<br>
<br>
# Generate test CAD files<br>
python test_data/cad/generate_test_stl.py<br>
<br>
# Verify files created<br>
ls -la test_data/cad/<br>
# Expected: 4 STL files + 4 JSON metadata files<br>
```<br>
<br>
#### CAD File Structure<br>
Each component has:<br>
- `.stl` file - 3D geometry data<br>
- `.json` file - Metadata (material, weight, dimensions)<br>
<br>
Example metadata:<br>
```json<br>
{<br>
  "file": "bracket_GPS-NAV-001.stl",<br>
  "part_number": "GPS-NAV-001",<br>
  "material": "Aluminum 6061-T6",<br>
  "volume_cm3": 24.5,<br>
  "weight_g": 66.15,<br>
  "bounding_box": {<br>
    "x": 100, "y": 20, "z": 80<br>
  }<br>
}<br>
```<br>
<br>
### 4. Test Ontology Setup<br>
<br>
#### Load Data Properties<br>
```bash<br>
# Load test ontology with data properties<br>
curl -X POST http://localhost:3030/odras/data \<br>
     -H "Content-Type: text/turtle" \<br>
     -d @test_data/ontology/aerospace_data_properties.ttl<br>
<br>
# Verify properties loaded<br>
curl -X POST http://localhost:3030/odras/query \<br>
     -H "Content-Type: application/sparql-query" \<br>
     -d "SELECT ?prop WHERE { ?prop a owl:DatatypeProperty }"<br>
```<br>
<br>
## Data Manager Test Scenarios<br>
<br>
### Scenario 1: Database Integration<br>
<br>
1. **Configure Database Pipe**<br>
```json<br>
{<br>
  "pipe_name": "Component Master Data",<br>
  "pipe_type": "database",<br>
  "source_config": {<br>
    "driver": "postgresql",<br>
    "host": "localhost",<br>
    "database": "odras_db",<br>
    "schema": "odras_test",<br>
    "credentials_ref": "test_db_creds"<br>
  },<br>
  "mapping": {<br>
    "query": "SELECT * FROM aircraft_components WHERE component_type = :type",<br>
    "parameters": {<br>
      "type": "avionics"<br>
    },<br>
    "bindings": {<br>
      "odras:partNumber": "part_number",<br>
      "odras:weight": {<br>
        "column": "weight_kg",<br>
        "transform": "kg_to_g"<br>
      },<br>
      "odras:certificationDate": "certification_date"<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
2. **Execute Sync**<br>
```bash<br>
# Via API<br>
curl -X POST http://localhost:8000/api/data-pipes/execute \<br>
     -H "Authorization: Bearer $TOKEN" \<br>
     -d @pipe_configs/component_master.json<br>
<br>
# Via UI<br>
# Navigate to Data Manager Workbench<br>
# Select "Component Master Data" pipe<br>
# Click "Run Sync"<br>
```<br>
<br>
### Scenario 2: API Integration<br>
<br>
1. **Configure API Pipe**<br>
```json<br>
{<br>
  "pipe_name": "Maintenance History",<br>
  "pipe_type": "api",<br>
  "source_config": {<br>
    "base_url": "http://localhost:8888",<br>
    "endpoints": {<br>
      "maintenance": "/api/v1/maintenance/{component_id}"<br>
    }<br>
  },<br>
  "mapping": {<br>
    "iterate_over": "components",<br>
    "response_path": "$[*]",<br>
    "bindings": {<br>
      "odras:maintenanceDate": "performed_date",<br>
      "odras:maintenanceCost": "cost",<br>
      "odras:maintenanceType": "maintenance_type"<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
### Scenario 3: File-Based Integration<br>
<br>
1. **Configure File Pipe**<br>
```json<br>
{<br>
  "pipe_name": "CAD Metadata Import",<br>
  "pipe_type": "file",<br>
  "source_config": {<br>
    "directory": "test_data/cad",<br>
    "pattern": "*.json",<br>
    "watch": false<br>
  },<br>
  "mapping": {<br>
    "format": "json",<br>
    "bindings": {<br>
      "odras:cadVolume": "volume_cm3",<br>
      "odras:cadWeight": "weight_g",<br>
      "odras:cadMaterial": "material",<br>
      "odras:cadTolerance": "tolerance"<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
## Performance Testing<br>
<br>
### Generate Large Dataset<br>
```python<br>
# Run performance data generator<br>
python test_data/generate_performance_data.py \<br>
    --components 10000 \<br>
    --sensors-per-component 10 \<br>
    --readings-per-sensor 1000<br>
```<br>
<br>
### Load Test Configuration<br>
```yaml<br>
# load_test_config.yaml<br>
scenarios:<br>
  - name: "Bulk Component Sync"<br>
    pipe_type: "database"<br>
    records: 10000<br>
    batch_size: 1000<br>
<br>
  - name: "High-Frequency Sensor Data"<br>
    pipe_type: "database"<br>
    records: 1000000<br>
    batch_size: 5000<br>
<br>
  - name: "Concurrent API Calls"<br>
    pipe_type: "api"<br>
    concurrent_requests: 50<br>
    duration_seconds: 300<br>
```<br>
<br>
## Troubleshooting<br>
<br>
### Common Issues<br>
<br>
1. **Database Connection Failed**<br>
```bash<br>
# Check PostgreSQL is running<br>
pg_isready -h localhost -p 5432<br>
<br>
# Verify test schema exists<br>
psql -U postgres -d odras_db -c "\dn odras_test.*"<br>
```<br>
<br>
2. **Mock API Not Responding**<br>
```bash<br>
# Check if port 8888 is in use<br>
lsof -i :8888<br>
<br>
# View API logs<br>
docker logs odras-mock-api<br>
```<br>
<br>
3. **STL Generation Errors**<br>
```bash<br>
# Ensure numpy-stl is installed<br>
pip show numpy-stl<br>
<br>
# Check Python version (requires 3.9+)<br>
python --version<br>
```<br>
<br>
## Cleanup<br>
<br>
```bash<br>
# Remove all test data<br>
./scripts/cleanup_test_data.sh<br>
<br>
# Or manually:<br>
# Drop test schema<br>
psql -U postgres -d odras_db -c "DROP SCHEMA odras_test CASCADE;"<br>
<br>
# Stop mock API<br>
docker stop odras-mock-api<br>
<br>
# Remove test files<br>
rm -rf test_data/cad/*.stl test_data/cad/*.json<br>
```<br>
<br>
## Best Practices<br>
<br>
1. **Isolation**: Run test data in separate schema/namespace<br>
2. **Versioning**: Tag test data versions with releases<br>
3. **Documentation**: Keep test scenarios documented<br>
4. **Automation**: Include in CI/CD pipeline<br>
5. **Monitoring**: Log all test data operations<br>
<br>
## Test Data Maintenance<br>
<br>
### Weekly Tasks<br>
- Refresh time-series data to keep timestamps current<br>
- Rotate API test logs<br>
- Update component prices/costs<br>
<br>
### Monthly Tasks<br>
- Review and update test scenarios<br>
- Add new edge cases based on bugs found<br>
- Performance baseline updates<br>
<br>
### Release Tasks<br>
- Ensure test data compatible with schema changes<br>
- Update API mock responses for new features<br>
- Document any new test data requirements<br>
<br>
## Contact<br>
<br>
For questions or issues with test data:<br>
- Create issue in ODRAS repository<br>
- Tag with `test-data` label<br>
- Include logs and configuration used<br>
<br>
<br>

